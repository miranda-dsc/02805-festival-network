from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys

from argparse import ArgumentParser

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from numba import njit

OUT = Path(__file__).resolve().parent
SEED = 28305
SAMPLES = 9_999
SWEEPS = 12
KM_EDGES = (0, 100, 250, 500, 1000, np.inf)
KM_LABELS = ("Under 100", "100 to 249", "250 to 499", "500 to 999", "1000 or more")
DAY_EDGES = (0, 8, 15, 31, 61, np.inf)
DAY_LABELS = ("0 to 7", "8 to 14", "15 to 30", "31 to 60", "61 or more")
GB_GROUPS = ("GB with GB", "GB with abroad", "Abroad with abroad")
plt.rcParams["axes.unicode_minus"] = False
sys.path.insert(0, str(OUT.parent))
sys.dont_write_bytecode = True
from common import festival_map, load, same_brand
from genre_profiles import genre_profiles
import sound


def projection(rows, left, right):
    return np.array([len(rows[a] & rows[b]) for a, b in zip(left, right)])


@njit
def trade(rows, sizes, booked, attempts):
    pool = np.empty(2 * rows.shape[1], dtype=np.int32)
    left = np.empty(rows.shape[1], dtype=np.int32)
    right = np.empty(rows.shape[1], dtype=np.int32)
    for _ in range(attempts):
        a = np.random.randint(len(sizes))
        b = np.random.randint(len(sizes) - 1)
        b += b >= a
        n_left = 0
        n_right = 0
        for i in range(sizes[a]):
            act = rows[a, i]
            if not booked[b, act]:
                left[n_left] = i
                pool[n_left] = act
                n_left += 1
        for i in range(sizes[b]):
            act = rows[b, i]
            if not booked[a, act]:
                right[n_right] = i
                pool[n_left + n_right] = act
                n_right += 1
        if n_left == 0 or n_right == 0:
            continue
        for i in range(n_left):
            j = np.random.randint(i, n_left + n_right)
            pool[i], pool[j] = pool[j], pool[i]
        for i in range(n_left):
            booked[a, rows[a, left[i]]] = False
        for i in range(n_right):
            booked[b, rows[b, right[i]]] = False
        for i in range(n_left):
            rows[a, left[i]] = pool[i]
            booked[a, pool[i]] = True
        for i in range(n_right):
            rows[b, right[i]] = pool[n_left + i]
            booked[b, pool[n_left + i]] = True


@njit(nogil=True)
def curveball(rows, sizes, degrees, seed, pair_index, samples):
    # reversible paths from a shared hub
    np.random.seed(seed)
    booked = np.zeros((len(sizes), len(degrees)), dtype=np.bool_)
    for edition, size in enumerate(sizes):
        for act in rows[edition, :size]:
            booked[edition, act] = True
    attempts = SWEEPS * len(sizes)
    trade(rows, sizes, booked, attempts)
    shuffled = np.zeros((samples, len(sizes) * (len(sizes) - 1) // 2), dtype=np.int16)
    counts = np.empty_like(degrees)
    sites = np.empty((len(degrees), max(degrees)), dtype=np.int32)
    for k in range(samples):
        draw = rows.copy()
        membership = booked.copy()
        trade(draw, sizes, membership, attempts)
        counts[:] = 0
        for edition, size in enumerate(sizes):
            for act in draw[edition, :size]:
                n = counts[act]
                if n >= degrees[act] or (n > 0 and sites[act, n - 1] == edition):
                    raise ValueError("act degree or binary lineup changed")
                for j in range(n):
                    shuffled[k, pair_index[sites[act, j], edition]] += 1
                sites[act, n] = edition
                counts[act] += 1
        if not np.array_equal(counts, degrees):
            raise ValueError("act degree changed")
    return shuffled


def distance_km(editions, left, right):
    lat = np.radians(editions["latitude"].to_numpy())
    lon = np.radians(editions["longitude"].to_numpy())
    h = (np.sin((lat[left] - lat[right]) / 2) ** 2 +
         np.cos(lat[left]) * np.cos(lat[right]) * np.sin((lon[left] - lon[right]) / 2) ** 2)
    return 6371.0088 * 2 * np.arcsin(np.sqrt(np.clip(h, 0, 1)))


def country_groups(pairs, field):
    a, b = pairs[f"{field}_a"], pairs[f"{field}_b"]
    count = a.eq("GB").astype(int) + b.eq("GB")
    return pairs.assign(same_country=a.eq(b), gb_group=count.map(dict(enumerate(reversed(GB_GROUPS)))))


def pair_data(editions, lineups, samples):
    left, right = np.triu_indices(len(editions), k=1)
    act_codes, acts = pd.factorize(lineups["act_key"], sort=True)
    booked = lineups.assign(code=act_codes).groupby("edition")["code"].agg(set)
    rows = [booked.get(edition, set()) for edition in editions["edition"]]
    year = int(editions["year"].iloc[0])
    pairs = pd.DataFrame({"year": year}, index=np.arange(len(left)))
    for col in ("edition", "festival", "country", "site_country", "tz_country", "start_date"):
        pairs[f"{col}_a"] = editions[col].to_numpy()[left]
        pairs[f"{col}_b"] = editions[col].to_numpy()[right]
    sizes = np.array([len(row) for row in rows])
    pairs["lineup_size_a"], pairs["lineup_size_b"] = sizes[left], sizes[right]
    pairs["days_apart"] = (pairs["start_date_a"] - pairs["start_date_b"]).abs().dt.days
    pairs["days_bin"] = pd.cut(pairs["days_apart"], DAY_EDGES, labels=DAY_LABELS, right=False)
    pairs["distance_km"] = distance_km(editions, left, right)
    pairs["distance_bin"] = pd.cut(pairs["distance_km"], KM_EDGES, labels=KM_LABELS, right=False)
    pairs["same_brand"] = [
        same_brand(a, b) for a, b in zip(pairs["festival_a"], pairs["festival_b"])
    ]
    pairs = country_groups(pairs, "country")
    pairs["shared_acts"] = projection(rows, left, right)
    union = pairs["lineup_size_a"] + pairs["lineup_size_b"] - pairs["shared_acts"]
    pairs["jaccard"] = pairs["shared_acts"] / union.where(union > 0)
    slots = np.full((len(rows), sizes.max()), -1, dtype=np.int32)
    for i, row in enumerate(rows):
        slots[i, :sizes[i]] = sorted(row)
    degrees = np.bincount([act for row in rows for act in row], minlength=len(acts))
    pair_index = np.full((len(rows), len(rows)), -1, dtype=np.int32)
    pair_index[left, right] = np.arange(len(left))
    null = curveball(slots, sizes, degrees, SEED + year, pair_index, samples)
    if not (null.sum(axis=1) == pairs["shared_acts"].sum()).all():
        raise ValueError("total pair overlap changed")
    pairs["null_mean"] = null.mean(axis=0)
    pairs["null_sd"] = null.std(axis=0, ddof=1)
    pairs["excess"] = pairs["shared_acts"] - pairs["null_mean"]
    pairs["z"] = pairs["excess"] / pairs["null_sd"].where(pairs["null_sd"] > 0)
    null_union = sizes[left] + sizes[right] - null
    null_jaccard = null / np.where(null_union > 0, null_union, np.nan)
    pairs["jaccard_null_mean"] = null_jaccard.mean(axis=0)
    pairs["jaccard_null_sd"] = null_jaccard.std(axis=0, ddof=1)
    pairs["jaccard_z"] = (pairs["jaccard"] - pairs["jaccard_null_mean"]) / pairs[
        "jaccard_null_sd"
    ].where(pairs["jaccard_null_sd"] > 0)
    print(f"{year}: {len(editions)} editions, {len(pairs)} pairs, {len(null)} checked shuffles", flush=True)
    return pairs, null


def describe(observed, null, **labels):
    mean = null.mean()
    sd = null.std(ddof=1)
    excess = observed - mean
    tail = min(np.count_nonzero(null >= observed - 1e-9),
               np.count_nonzero(null <= observed + 1e-9))
    return dict(
        labels, observed=observed, null_mean=mean, null_sd=sd, excess=excess,
        z=excess / sd if sd > 0 else np.nan,
        tail_hits=tail, shuffles=len(null),
        p_null=min(1.0, 2 * (tail + 1) / (len(null) + 1)),
        p_mc_upper_95=min(1.0, 2 * (1 - 0.05 ** (1 / len(null)))) if tail == 0 else np.nan,
        null_low=np.quantile(null, 0.025) - mean,
        null_high=np.quantile(null, 0.975) - mean,
    )


def within(values, strata):
    return values - values.groupby(strata, observed=True).transform("mean")


def influence(frame, predictor, strata, labels):
    outcome = frame["excess"]
    festivals = sorted(set(frame["festival_a"]) | set(frame["festival_b"]))
    if predictor is None:
        full = outcome.mean()
        deleted = (outcome.sum() - outcome) / (len(outcome) - 1)
    else:
        x = within(predictor, strata)
        y = within(outcome, strata)
        xy = x * y
        xx = x * x
        full = xy.sum() / xx.sum() if xx.sum() > 1e-12 else np.nan
        n = x.groupby(strata, observed=True).transform("size")
        factor = n / (n - 1).where(n > 1)
        numerator = xy.sum() - (factor * xy).fillna(0)
        denominator = xx.sum() - (factor * xx).fillna(0)
        deleted = numerator / denominator.where(denominator > 1e-12)

    results = []
    for festival in festivals:
        keep = ~frame["festival_a"].eq(festival) & ~frame["festival_b"].eq(festival)
        if predictor is None:
            value = outcome[keep].mean()
        else:
            subset_strata = [col[keep] for col in strata]
            x = within(predictor[keep], subset_strata)
            denominator = (x * x).sum()
            value = (x * outcome[keep]).sum() / denominator if denominator > 1e-12 else np.nan
        results.append(dict(labels, omitted_festival=festival, n_pairs=int(keep.sum()),
                            full_excess=full, excess=value, change=value - full))

    pairs = frame[["edition_a", "edition_b"]].assign(full_excess=full, excess=deleted)
    pairs["change"] = pairs["excess"] - full
    if pairs["change"].notna().any():
        worst = pairs.loc[pairs["change"].abs().idxmax()]
        pair_result = dict(labels, **worst.to_dict(), excess_min=deleted.min(), excess_max=deleted.max(),
                           n_defined=int(deleted.notna().sum()), n_pairs=len(frame))
    else:
        pair_result = dict(labels, full_excess=full, n_defined=0, n_pairs=len(frame))
    return results, pair_result


def contrasts(pairs):
    gb = pairs[pairs["gb_group"].isin(GB_GROUPS[:2])]
    abroad = pairs[pairs["gb_group"].eq(GB_GROUPS[2])]
    for label, group, x in (
        ("same country", pairs, pairs["same_country"]),
        ("GB with GB", gb, gb["gb_group"].eq("GB with GB")),
        ("Same country abroad", abroad, abroad["same_country"]),
    ):
        yield label, "year", group, x, [group["year"]]
        yield label, "year and days", group, x, [group["year"], group["days_bin"]]
        yield label, "year, days and distance", group, x, [
            group["year"], group["days_bin"], group["distance_bin"],
        ]
    yield "distance per doubling", "year, days and country", pairs, np.log2(
        1 + pairs["distance_km"]
    ), [pairs["year"], pairs["days_bin"], pairs["same_country"]]


def fit_contrast(group, x, strata, draws, labels):
    residual = within(x.astype(float), strata).to_numpy()
    denominator = residual @ residual
    sizes = dict(n_pairs=len(group), n_informative=int(np.count_nonzero(abs(residual) > 1e-12)))
    if denominator <= 1e-12:
        return dict(labels, **sizes, observed=np.nan)
    weights = residual / denominator
    observed = weights @ group["shared_acts"].to_numpy()
    simulated = np.einsum("ij,j->i", draws[:, group.index], weights)
    return describe(observed, simulated, **labels, **sizes)


def analyze(yearly):
    summary, tests, festivals, pair_checks = [], [], [], []
    for period, (frame, draws) in yearly.items():
        print(f"Summarizing {period}", flush=True)
        for include_brand in (True, False):
            pairs = frame if include_brand else frame[~frame["same_brand"]]
            scope = dict(period=period, include_brand=include_brand)
            for column in ("days_bin", "distance_bin", "same_country", "gb_group", "same_brand"):
                for label, group in pairs.groupby(column, observed=True):
                    if column == "same_brand" and not label:
                        continue
                    labels = dict(scope, statistic=column, group=str(label))
                    summary.append(describe(
                        group["shared_acts"].mean(), draws[:, group.index].mean(axis=1),
                        **labels, n_pairs=len(group),
                    ))
                    if period == "pooled":
                        detail, pair_detail = influence(group, None, None, labels)
                        festivals.extend(detail)
                        pair_checks.append(pair_detail)
            country_specs = {"site": pairs}
            if period == "pooled":
                country_specs["metadata"] = country_groups(pairs, "tz_country")
            for basis, country_pairs in country_specs.items():
                for label, controls, group, x, strata in contrasts(country_pairs):
                    labels = dict(scope, contrast=label, controls=controls, country_basis=basis)
                    result = fit_contrast(group, x, strata, draws, labels)
                    tests.append(result)
                    if period == "pooled" and pd.notna(result["observed"]):
                        detail, pair_detail = influence(
                            group, x.astype(float), strata, dict(labels, statistic="contrast", group=label),
                        )
                        festivals.extend(detail)
                        pair_checks.append(pair_detail)
    return pd.DataFrame(summary), pd.DataFrame(tests), pd.DataFrame(festivals), pd.DataFrame(pair_checks)


def plot_days(summary):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), layout="constrained",
                            gridspec_kw={"width_ratios": (3, 2)})
    days = summary[summary["statistic"].eq("days_bin") & ~summary["include_brand"]]
    pooled = days[days["period"].eq("pooled")].set_index("group").reindex(DAY_LABELS)
    x = np.arange(len(DAY_LABELS))
    axes[0].fill_between(x, pooled["null_low"], pooled["null_high"], color="#e1e8ec",
                         label="95% shuffle range")
    axes[0].plot(x, pooled["excess"], "o-", color="#155a77", label="Observed minus null mean")
    axes[0].set_title("Pooled")
    axes[0].legend(frameon=False)
    for period, yearly in days[~days["period"].eq("pooled")].groupby("period"):
        values = yearly.set_index("group").reindex(DAY_LABELS)["excess"]
        axes[1].plot(x, values, "o-", alpha=0.72, markersize=3, label=period)
    axes[1].set_title("By year")
    axes[1].legend(frameon=False, ncols=2, fontsize=8)
    for ax in axes:
        ax.axhline(0, color="0.45", linewidth=0.8)
        ax.set_xticks(x, DAY_LABELS, rotation=20, ha="right")
        ax.set_xlabel("Days between edition starts")
    axes[0].set_ylabel("Excess shared acts per pair")
    fig.savefig(OUT / "days.png", dpi=180)
    plt.close(fig)


def plot_country(summary):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True, layout="constrained")
    pooled = summary[summary["period"].eq("pooled") & ~summary["include_brand"]]
    for ax, column, groups, title in (
        (axes[0], "same_country", ("False", "True"), "Same country"),
        (axes[1], "gb_group", GB_GROUPS, "GB and abroad"),
    ):
        values = pooled[pooled["statistic"].eq(column)].set_index("group").reindex(groups)
        x = np.arange(len(groups))
        ax.vlines(x, values["null_low"], values["null_high"], color="#829aa8",
                  lw=3, label="95% shuffle range")
        ax.scatter(x, values["excess"], color="#155a77", zorder=3,
                   label="Observed minus null mean")
        ax.axhline(0, color="0.45", linewidth=0.8)
        ax.set_xticks(x, ("Different", "Same") if column == "same_country" else groups)
        ax.set_title(title)
    axes[0].set_ylabel("Excess shared acts per pair")
    axes[0].legend(frameon=False)
    fig.savefig(OUT / "country.png", dpi=180)
    plt.close(fig)


def plot_distance(summary):
    fig, ax = plt.subplots(figsize=(7, 4), layout="constrained")
    values = summary[summary["period"].eq("pooled") & summary["statistic"].eq("distance_bin")]
    x = np.arange(len(KM_LABELS))
    for include_brand, label, color, offset in (
        (True, "All pairs", "#829aa8", -0.10),
        (False, "Without Tomorrowland pair", "#155a77", 0.10),
    ):
        view = values[values["include_brand"].eq(include_brand)].set_index("group").reindex(KM_LABELS)
        ax.vlines(x + offset, view["null_low"], view["null_high"], color=color, lw=2,
                  label="95% shuffle range" if include_brand else None)
        ax.scatter(x + offset, view["excess"], color=color, label=label)
    ax.axhline(0, color="0.45", linewidth=0.8)
    ax.set_xticks(x, KM_LABELS)
    ax.set(xlabel="Distance between sites (km)", ylabel="Excess shared acts per pair",
           title="Distance between sites")
    ax.legend(frameon=False)
    fig.savefig(OUT / "distance.png", dpi=180)
    plt.close(fig)


def write_findings(pairs, summary, genre, coverage, samples):
    pooled = summary[summary["period"].eq("pooled") & ~summary["include_brand"]]
    days = pooled[pooled["statistic"].eq("days_bin")].set_index("group")["excess"]
    report = f"""We kept Reading, dropped Leeds and rebroadcasts before shuffling, and excluded 2020 and 2021. The {len(pairs):,} pairs use venue countries and a baseline of {samples:,} degree-preserving draws per year. The excess was {days[DAY_LABELS[0]]:+.2f} acts at 0 to 7 days and {days[DAY_LABELS[1]]:+.2f} at 8 to 14 days. We gave each tagged act equal total weight, used genre counts where present and tag counts otherwise, and removed shared acts before comparing the two edition TF-IDF profiles.

{sound.findings(genre, coverage)}
### Open problems

Audit ambiguous artist matches and test whether broader tag coverage changes the estimates. Genre profiles use the available MusicBrainz tags for each act across the full study period.
"""
    (OUT / "findings.md").write_text(report)


def load_editions(editions):
    names = festival_map()
    editions = editions.rename(columns={"lat": "latitude", "lon": "longitude"})
    editions = editions.assign(start_date=pd.to_datetime(editions["start_date"]),
                               site_country=editions["country"])
    coords = pd.read_csv(OUT / "festival_coords.csv")
    if coords["festival"].duplicated().any() or set(coords["festival"]) != set(names.values()):
        raise ValueError("coordinate keys must match festival headers")
    columns = ["latitude", "longitude"]
    overrides = OUT / "edition_coords.csv"
    if overrides.exists():
        edits = pd.read_csv(overrides).set_index("edition")
        if not edits.index.is_unique or not edits.index.isin(names).all():
            raise ValueError("invalid edition coordinate overrides")
        editions = editions.set_index("edition")
        editions.update(edits[columns])
        editions = editions.reset_index()
    required = ["festival", "start_date", "country", "site_country", *columns]
    if editions[required].isna().any().any():
        raise ValueError("missing festival, start date, country or coordinates")
    if not editions["latitude"].between(-90, 90).all() or not editions["longitude"].between(-180, 180).all():
        raise ValueError("out-of-range coordinates")
    return editions


def main():
    parser = ArgumentParser()
    parser.add_argument("--samples", type=int, default=SAMPLES)
    samples = parser.parse_args().samples
    if samples < 200:
        parser.error("--samples requires at least 200 draws")
    lineups, editions = load()
    editions = load_editions(editions).sort_values(["year", "edition"])
    print(f"Loaded {len(editions)} editions and {len(lineups)} bookings with shared exclusions", flush=True)

    def simulate(group):
        return pair_data(group, lineups[lineups["edition"].isin(group["edition"])], samples)

    groups = list(editions.groupby("year"))
    with ThreadPoolExecutor(max_workers=4) as pool:
        draws = pool.map(simulate, [group for _, group in groups])
        yearly = dict(zip([str(year) for year, _ in groups], draws))
    pairs = pd.concat([frame for frame, _ in yearly.values()], ignore_index=True)
    null = np.concatenate([draws for _, draws in yearly.values()], axis=1)
    yearly["pooled"] = pairs, null
    summary, tests, festivals, pair_checks = analyze(yearly)
    pairs, coverage = genre_profiles(lineups, editions, pairs)
    genre, genre_deletions = sound.tests(pairs)
    coverage.to_csv(OUT / "tag_coverage.csv", index=False)
    genre.to_csv(OUT / "genre_tests.csv", index=False)
    genre_deletions.to_csv(OUT / "genre_leave_one_festival_out.csv", index=False)
    sound.plot(pairs, OUT / "genre.png")
    pairs.to_csv(OUT / "pairs.csv", index=False)
    summary.to_csv(OUT / "summary.csv", index=False)
    tests.to_csv(OUT / "country_tests.csv", index=False)
    festivals.to_csv(OUT / "leave_one_festival_out.csv", index=False)
    pair_checks.to_csv(OUT / "leave_one_pair_out.csv", index=False)
    plot_days(summary)
    plot_country(summary)
    plot_distance(summary)
    write_findings(pairs, summary, genre, coverage, samples)
    print(f"Wrote {len(pairs)} pairs, {len(summary)} group summaries and {len(tests)} contrasts")


if __name__ == "__main__":
    main()
