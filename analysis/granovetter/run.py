from functools import lru_cache
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import hypergeom

OUT = Path("analysis/granovetter")
YEARS = (2015, 2016, 2017, 2018, 2019, 2022, 2023, 2024, 2025)
MIN_PANEL_YEARS = 7
SAMPLES = 250
CHAINS = 2
BURN = 30
THIN = 8
SIZE_LIMIT = 30
SEED = 2805

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import load, same_brand

plt.rcParams["axes.unicode_minus"] = False


@lru_cache(maxsize=None)
def rarefied_jaccard(shared, size_a, size_b, size):
    """expected jaccard after independent uniform lineup subsampling"""
    if shared == 0:
        return 0.0
    hits = np.arange(min(shared, size) + 1)
    first = hypergeom.pmf(hits, size_a, shared, size)
    second = hypergeom.pmf(hits[:, None], size_b, hits, size)
    return float((hits / (2 * size - hits)) @ second @ first)


def overlaps(lineups, pairs, sizes, size):
    shared = np.array([len(lineups[i] & lineups[j]) for i, j in pairs])
    raw = shared / (sizes.sum(axis=1) - shared)
    standardized = np.array([
        rarefied_jaccard(int(common), int(a), int(b), size)
        for common, (a, b) in zip(shared, sizes)
    ])
    return raw, standardized


def shuffle(lineups, rng):
    for i, j in rng.permutation(len(lineups))[:2 * (len(lineups) // 2)].reshape(-1, 2):
        only_i = lineups[i] - lineups[j]
        only_j = lineups[j] - lineups[i]
        pool = sorted(only_i | only_j)
        rng.shuffle(pool)
        common = lineups[i] & lineups[j]
        lineups[i] = common.union(pool[:len(only_i)])
        lineups[j] = common.union(pool[len(only_i):])


def degrees(lineups, n_acts):
    return np.bincount([act for lineup in lineups for act in lineup], minlength=n_acts)


def summary(observed, draws):
    mean = draws.mean()
    sd = draws.std(ddof=1)
    return dict(observed=observed, null_mean=mean, null_sd=sd,
                excess=observed - mean, z=(observed - mean) / sd if sd > 0 else np.nan,
                null_low=np.quantile(draws, 0.025), null_high=np.quantile(draws, 0.975))


def analyze_year(lineups, n_acts, rng, size, count):
    n = len(lineups)
    sizes = np.array([len(lineup) for lineup in lineups])
    degree = degrees(lineups, n_acts)
    pairs = np.array(list(zip(*np.triu_indices(n, k=1))))
    pair_sizes = sizes[pairs]
    raw, standardized = overlaps(lineups, pairs, pair_sizes, size)
    draws = np.empty((SAMPLES, 3))
    count_observed = np.empty(SAMPLES)
    pair_null = np.empty((SAMPLES, len(pairs), 2))
    count_masks = np.empty((SAMPLES, len(pairs)), dtype=bool)
    shuffled = []

    for sample in range(SAMPLES):
        if sample % (SAMPLES // CHAINS) == 0:
            state = lineups.copy()
            for _ in range(BURN):
                shuffle(state, rng)
        for _ in range(THIN):
            shuffle(state, rng)
        if not np.array_equal(degrees(state, n_acts), degree) or any(
            len(lineup) != length for lineup, length in zip(state, sizes)
        ):
            raise RuntimeError("shuffle changed the degree margins")
        shuffled.append(state.copy())
        null_raw, null_standardized = overlaps(state, pairs, pair_sizes, size)
        subset = np.zeros(n, dtype=bool)
        subset[rng.choice(n, size=count, replace=False)] = True
        pair_mask = subset[pairs].all(axis=1)
        draws[sample] = null_raw.mean(), null_standardized.mean(), null_raw[pair_mask].mean()
        count_observed[sample] = raw[pair_mask].mean()
        pair_null[sample, :, 0] = null_raw
        pair_null[sample, :, 1] = null_standardized
        count_masks[sample] = pair_mask

    active = np.sort(degree[degree > 0])
    n_top = int(np.ceil(0.01 * len(active)))
    return {
        "n_editions": n,
        "mean_lineup_size": sizes.mean(),
        "n_acts": len(active),
        "n_bookings": active.sum(),
        "share_three_plus": (active >= 3).mean(),
        "top_1pct_share": active[-n_top:].sum() / active.sum(),
        "gini": (2 * np.arange(1, len(active) + 1) @ active / active.sum()
                 - len(active) - 1) / len(active),
    }, [raw.mean(), standardized.mean(), raw.mean()], draws, count_observed, shuffled, (
        pairs, np.column_stack((raw, standardized)), pair_null, count_masks
    )


def fixed_effect_weights(year, pair_id):
    counts = np.bincount(pair_id)
    totals = np.bincount(pair_id, weights=year)
    centered = year - totals[pair_id] / counts[pair_id]
    return centered / (centered @ centered)


def trend_row(dataset, model, metric, observed, draws):
    result = summary(observed, draws)
    result.pop("z")
    return dict(dataset=dataset, model=model, metric=metric, **result)


bookings, editions = load()
editions = editions.loc[editions["year"].isin(YEARS)].sort_values(["year", "festival"])
bookings["act_id"], acts = pd.factorize(bookings["act_key"], sort=True)
if editions.duplicated(["festival", "year"]).any():
    raise ValueError("multiple editions for a festival in one year")
lineups = bookings.groupby("edition")["act_id"].agg(set)
editions["lineup"] = editions["edition"].map(lineups)
if editions["lineup"].isna().any():
    raise ValueError("edition missing a lineup after rebroadcast removal")
print(f"Loaded {len(editions)} editions in {len(YEARS)} years")

coverage = editions.groupby("festival")["year"].nunique()
panel_names = coverage[coverage >= MIN_PANEL_YEARS].index
panel = editions[editions["festival"].isin(panel_names)]
print(f"Panel has {len(panel_names)} festivals in {panel['year'].nunique()} years")
same_size = min(SIZE_LIMIT, int(editions["lineup"].map(len).min()))
rng = np.random.default_rng(SEED)
annual_rows, trend_rows, returns, return_draws = [], [], [], []
metrics = ("jaccard", "size_matched", "count_matched")
for dataset, selection in (("panel", panel), ("full", editions)):
    same_count = selection.groupby("year").size().min()
    previous = {}
    yearly_draws, yearly_observed, count_draws = [], [], []
    pair_rows, pair_observed, pair_draws, pair_masks = [], [], [], []
    years = sorted(selection["year"].unique())
    for year, group in selection.groupby("year"):
        current = list(group["lineup"])
        booking_stats, observed, draws, observed_count, shuffled, pair_data = analyze_year(
            current, len(acts), rng, same_size, same_count
        )
        pairs, observed_pairs, null_pairs, masks = pair_data
        names = group["festival"].to_numpy()
        pair_rows.extend((year, names[i], names[j]) for i, j in pairs)
        pair_observed.append(observed_pairs)
        pair_draws.append(null_pairs)
        pair_masks.append(masks)
        yearly_observed.append(observed)
        yearly_draws.append(draws)
        count_draws.append(observed_count)
        for index, metric in enumerate(metrics):
            annual_rows.append(dict(dataset=dataset, year=year, metric=metric, **booking_stats,
                                    **summary(observed[index], draws[:, index])))
        if dataset == "full":
            for i, row in enumerate(group.itertuples()):
                null_current = [state[i] for state in shuffled]
                if row.festival in previous:
                    prior, prior_null = previous[row.festival]
                    observed_return = len(prior.lineup & row.lineup) / len(row.lineup)
                    null_return = np.array([
                        len(a & b) / len(row.lineup) for a, b in zip(prior_null, null_current)
                    ])
                    return_draws.append(null_return)
                    returns.append(dict(festival=row.festival, edition=row.edition, year=year,
                                        prior_edition=prior.edition, prior_year=prior.year,
                                        gap_years=year - prior.year, **summary(observed_return, null_return)))
                previous[row.festival] = row, null_current
        print(f"{dataset} {year}: {len(group)} editions, {SAMPLES} null draws", flush=True)

    centered = np.asarray(years) - np.mean(years)
    weights = centered / (centered @ centered)
    slopes = np.tensordot(weights, yearly_draws, axes=1)
    observed_slopes = weights @ yearly_observed
    count_slopes = weights @ count_draws
    for index, metric in enumerate(metrics):
        observed = count_slopes.mean() if metric == "count_matched" else observed_slopes[index]
        row = trend_row(dataset, "annual_mean", metric, observed, slopes[:, index])
        if metric == "count_matched":
            row["subset_low"], row["subset_high"] = np.quantile(count_slopes, [0.025, 0.975])
            row["paired_excess_low"], row["paired_excess_high"] = np.quantile(
                count_slopes - slopes[:, index], [0.025, 0.975]
            )
        trend_rows.append(row)

    pair_frame = pd.DataFrame(pair_rows, columns=["year", "festival_a", "festival_b"])
    pair_id = pair_frame.groupby(["festival_a", "festival_b"]).ngroup().to_numpy()
    pair_year = pair_frame["year"].to_numpy()
    recurring = np.bincount(pair_id)[pair_id] >= 2
    n_pairs = np.unique(pair_id[recurring]).size
    n_festivals = pd.unique(pair_frame.loc[recurring, ["festival_a", "festival_b"]].to_numpy().ravel()).size
    support = dict(n_pairs=n_pairs, n_festivals=n_festivals, n_pair_years=int(recurring.sum()))
    print(f"{dataset}: {n_pairs} recurring pairs across {n_festivals} festivals")
    weights = fixed_effect_weights(pair_year, pair_id)
    observed_pairs = np.concatenate(pair_observed)
    null_pairs = np.concatenate(pair_draws, axis=1)
    slopes = np.einsum("i,sim->sm", weights, null_pairs)
    observed_slopes = weights @ observed_pairs
    same_brand_pair = np.array([same_brand(a, b) for a, b in zip(pair_frame.festival_a, pair_frame.festival_b)])
    excess_pairs = observed_pairs - null_pairs.mean(axis=0)
    leave_one_out = []
    for festival in selection["festival"].unique():
        keep = ~(pair_frame["festival_a"].eq(festival) | pair_frame["festival_b"].eq(festival)).to_numpy()
        reduced_weights = fixed_effect_weights(pair_year[keep], pair_id[keep])
        leave_one_out.append(reduced_weights @ excess_pairs[keep])
    for index, metric in enumerate(metrics[:2]):
        row = trend_row(dataset, "pair_fixed_effects", metric, observed_slopes[index], slopes[:, index])
        row["leave_one_out_low"] = np.min(leave_one_out, axis=0)[index]
        row["leave_one_out_high"] = np.max(leave_one_out, axis=0)[index]
        keep = ~same_brand_pair
        reduced_weights = fixed_effect_weights(pair_year[keep], pair_id[keep])
        row["excess_without_same_brand"] = reduced_weights @ excess_pairs[keep, index]
        trend_rows.append(dict(**row, **support))

    observed_slopes = np.empty(SAMPLES)
    null_slopes = np.empty(SAMPLES)
    for sample, mask in enumerate(np.concatenate(pair_masks, axis=1)):
        weights = fixed_effect_weights(pair_year[mask], pair_id[mask])
        observed_slopes[sample] = weights @ observed_pairs[mask, 0]
        null_slopes[sample] = weights @ null_pairs[sample, mask, 0]
    row = trend_row(dataset, "pair_fixed_effects", "count_matched",
                    observed_slopes.mean(), null_slopes)
    row["subset_low"], row["subset_high"] = np.quantile(observed_slopes, [0.025, 0.975])
    row["paired_excess_low"], row["paired_excess_high"] = np.quantile(
        observed_slopes - null_slopes, [0.025, 0.975]
    )
    trend_rows.append(row)
    print(f"{dataset}: {same_count} editions per count sample, {same_size} acts per size sample")

annual = pd.DataFrame(annual_rows)
trends = pd.DataFrame(trend_rows)
returns = pd.DataFrame(returns)
annual.to_csv(OUT / "annual.csv", index=False)
trends.to_csv(OUT / "trends.csv", index=False)
returns.to_csv(OUT / "returns.csv", index=False)
return_stats = []
for label, include in (
    ("all_gaps", np.ones(len(returns), dtype=bool)),
    ("one_year", returns["gap_years"] == 1),
):
    result = summary(returns.loc[include, "observed"].median(),
                     np.median(np.asarray(return_draws)[include], axis=0))
    return_stats.append(dict(gap=label, n=int(include.sum()), **result))
return_stats = pd.DataFrame(return_stats).set_index("gap")
return_stats.to_csv(OUT / "return_summary.csv")
print(f"Saved {len(annual)} annual rows and {len(returns)} return comparisons")

fig, axes = plt.subplots(2, 1, figsize=(8, 6.7), sharex=True, sharey=True, layout="constrained")
for ax, dataset, title in zip(axes, ("panel", "full"), ("Coverage panel", "All editions")):
    series = annual[(annual["dataset"] == dataset) & (annual["metric"] == "jaccard")]
    ax.axvspan(2019.5, 2021.5, color="0.93", zorder=0)
    for period, segment in series.groupby(series["year"] > 2021):
        year = segment["year"]
        ax.fill_between(year, 100 * segment["null_low"], 100 * segment["null_high"],
                        color="#e6a65d", alpha=0.5, label=None if period else "95% null interval")
        ax.plot(year, 100 * segment["null_mean"], color="#a75618", linestyle="--",
                label=None if period else "Null mean")
        ax.plot(year, 100 * segment["observed"], color="#235582", marker="o",
                label=None if period else "Observed")
    ax.set_title(title, loc="left")
    ax.grid(axis="y", alpha=0.2)
axes[0].legend(frameon=False, ncol=3, loc="upper right")
axes[-1].set_xticks(range(2015, 2026))
axes[-1].set_xlabel("Year (pandemic years shaded)")
fig.supylabel("Mean pairwise Jaccard (%)")
fig.savefig(OUT / "overlap.png", dpi=180)
plt.close(fig)

year_stats = annual[annual["metric"] == "jaccard"].set_index(["dataset", "year"])
pair_stats = trends[trends["model"] == "pair_fixed_effects"].set_index(["dataset", "metric"])
panel_trend = pair_stats.loc["panel", "jaccard"]
full_trend = pair_stats.loc["full", "jaccard"]
panel_count = pair_stats.loc["panel", "count_matched"]
full_count = pair_stats.loc["full", "count_matched"]
panel_size = pair_stats.loc["panel", "size_matched"]
full_size = pair_stats.loc["full", "size_matched"]
full_start = year_stats.loc["full", YEARS[0]]
full_end = year_stats.loc["full", YEARS[-1]]
panel_start = year_stats.loc["panel", YEARS[0]]
panel_end = year_stats.loc["panel", YEARS[-1]]
panel_min_count = int(year_stats.loc["panel", "n_editions"].min())
full_min_count = int(year_stats.loc["full", "n_editions"].min())
return_all = return_stats.loc["all_gaps"]
return_one = return_stats.loc["one_year"]
panel_labels = ", ".join(panel_names)
positive_full = int(year_stats.loc["full", "excess"].gt(0).sum())
positive_panel = int(year_stats.loc["panel", "excess"].gt(0).sum())

report = f"""We kept Reading, dropped Leeds, and excluded 2020 and 2021. The panel includes festivals seen in at least {MIN_PANEL_YEARS} of the {len(YEARS)} remaining years ({panel_labels}). Each year has {SAMPLES} Curveball draws that preserve lineup sizes and act degrees. We fit the same festival-pair fixed effects to observed and shuffled Jaccard across calendar years.

1. Overlap changed by {100 * panel_trend.observed:+.3f} percentage points per year within {int(panel_trend.n_pairs)} panel pairs across {int(panel_trend.n_festivals)} festivals and {int(panel_trend.n_pair_years)} pair-years.
   The panel null slope was {100 * panel_trend.null_mean:+.3f}, and the full set gave {100 * full_trend.observed:+.3f} versus {100 * full_trend.null_mean:+.3f} across {int(full_trend.n_pairs)} pairs and {int(full_trend.n_festivals)} festivals.
   Annual means exceeded the null in {positive_panel} of {len(YEARS)} panel years and {positive_full} full years, and dropping one panel festival at a time gave excess slopes of {100 * panel_trend.leave_one_out_low:+.3f} to {100 * panel_trend.leave_one_out_high:+.3f}.
   This measures changes in shared acts within the same festival pairs.
   It misses pairs observed only once and changes in act prominence.

2. Matching edition counts to {panel_min_count} in the panel and {full_min_count} in the full set gave central 95% ranges for excess slopes of {100 * panel_count.paired_excess_low:+.3f} to {100 * panel_count.paired_excess_high:+.3f} and {100 * full_count.paired_excess_low:+.3f} to {100 * full_count.paired_excess_high:+.3f} percentage points per year.
   At {same_size} acts per lineup, observed slopes were {100 * panel_size.observed:+.3f} and {100 * full_size.observed:+.3f}, with excess slopes of {100 * panel_size.excess:+.3f} and {100 * full_size.excess:+.3f}, respectively.
   These checks measure sensitivity to the number of editions and acts observed.
   They miss changes in which acts Clashfinder captures.

3. From 2015 to 2025, the full set's share playing at least three festivals changed from {full_start.share_three_plus:.1%} to {full_end.share_three_plus:.1%}, the top 1% booking share from {full_start.top_1pct_share:.1%} to {full_end.top_1pct_share:.1%}, and Gini from {full_start.gini:.3f} to {full_end.gini:.3f}.
   The panel endpoints were {panel_start.share_three_plus:.1%} to {panel_end.share_three_plus:.1%}, {panel_start.top_1pct_share:.1%} to {panel_end.top_1pct_share:.1%}, and {panel_start.gini:.3f} to {panel_end.gini:.3f}, respectively.
   These measures describe how bookings are spread across acts.
   These descriptive values depend on edition coverage and miss which festivals shared the acts.

4. The median share returning from the previous observed edition was {return_all.observed:.1%} across {int(return_all.n)} comparisons.
   The null median averaged {return_all.null_mean:.1%}, and one-year gaps gave {return_one.observed:.1%} observed versus {return_one.null_mean:.1%} expected.
   This measures the share of the current lineup made up of returning acts.
   It misses returns from editions outside our data.

Overlap fell less than the null predicted, and the edition-count check left the direction of the excess trend uncertain.

Open problems

Check whether lineup completeness changed within festivals and whether trends differ by genre.
"""
(OUT / "findings.md").write_text(report, encoding="utf-8")
