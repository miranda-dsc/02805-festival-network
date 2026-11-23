import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

COEFFICIENTS = ("country_before_genre", "country_after_genre", "genre_per_0_1")
SIMILARITY = {True: "genre_similarity", False: "genre_similarity_strict"}


def fit(frame, key):
    columns = ["excess", "same_country", key]
    values = frame[columns].astype(float)
    values -= values.groupby([frame["year"], frame["days_bin"]], observed=True).transform("mean")
    y, country, genre = values.to_numpy().T
    x = np.column_stack((country, 10 * genre))
    baseline = (country @ y) / (country @ country) if (country @ country) > 1e-12 else np.nan
    beta, _, rank, _ = np.linalg.lstsq(x, y, rcond=None)
    return np.r_[baseline, beta if rank == 2 else [np.nan, np.nan]]


def tests(pairs):
    estimates, deletions = [], []
    for ambiguous, key in SIMILARITY.items():
        for include_brand in (True, False):
            keep = pairs[key].notna() & (include_brand | ~pairs["same_brand"])
            data = pairs[keep]
            scope = dict(include_ambiguous=ambiguous, include_brand=include_brand)
            yearly = {year: fit(group, key) for year, group in data.groupby("year")}
            festivals = sorted(set(data["festival_a"]) | set(data["festival_b"]))
            omitted = {}
            for festival in festivals:
                retained = data[data["festival_a"].ne(festival) & data["festival_b"].ne(festival)]
                omitted[festival] = fit(retained, key)
            for period, group in [("pooled", data), *data.groupby("year")]:
                values = fit(group, key) if period == "pooled" else yearly[period]
                for i, (term, estimate) in enumerate(zip(COEFFICIENTS, values)):
                    row = dict(scope, period=period, term=term, n_pairs=len(group), estimate=estimate)
                    if period == "pooled":
                        by_year = np.array([v[i] for v in yearly.values()])
                        available = np.array([v[i] for v in omitted.values()])
                        available = available[np.isfinite(available)]
                        row.update(
                            positive_years=int((by_year > 0).sum()),
                            estimated_years=int(np.isfinite(by_year).sum()),
                            deletion_min=available.min() if len(available) else np.nan,
                            deletion_max=available.max() if len(available) else np.nan,
                        )
                        deletions.extend(dict(scope, term=term, omitted_festival=festival, estimate=v[i])
                                         for festival, v in omitted.items())
                    estimates.append(row)
    return pd.DataFrame(estimates), pd.DataFrame(deletions)


def plot(pairs, output):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharex=True, sharey=True, layout="constrained")
    for ax, (ambiguous, key) in zip(axes, SIMILARITY.items()):
        data = pairs.loc[~pairs["same_brand"] & pairs[key].notna()]
        for same, label, color in ((False, "Different country", "#39749a"),
                                   (True, "Same country", "#a64c30")):
            group = data[data["same_country"].eq(same)]
            ax.scatter(group[key], group["excess"], s=8, color=color, alpha=0.23, linewidths=0)
            bins = pd.cut(group[key], np.linspace(0, 1, 11), include_lowest=True)
            binned = group.groupby(bins, observed=True)
            means = binned[[key, "excess"]].mean().where(binned.size().ge(10))
            ax.plot(means[key], means["excess"], "o-", color=color, ms=3, label=label)
        ax.axhline(0, color="0.55", lw=0.8, zorder=0)
        ax.set_title("With ambiguous matches" if ambiguous else "Without ambiguous matches")
        ax.set_xlabel("Genre similarity (cosine)")
    axes[0].set_ylabel("Excess shared acts")
    axes[1].legend(title="Bin means (10+ pairs)", frameon=False)
    fig.savefig(output, dpi=180)
    plt.close(fig)


def findings(estimates, coverage):
    pooled = estimates[estimates["period"].eq("pooled") & ~estimates["include_brand"]]
    cases = pooled.set_index(["include_ambiguous", "term"])
    def effect(ambiguous, term):
        row = cases.loc[(ambiguous, term)]
        return (f"{row.estimate:+.2f} ({row.deletion_min:+.2f} to {row.deletion_max:+.2f} "
                f"after festival deletions, positive in {int(row.positive_years)} "
                f"of {int(row.estimated_years)} years)")

    before = [cases.loc[(case, "country_before_genre"), "estimate"] for case in SIMILARITY]
    sizes = [int(cases.loc[(case, "country_before_genre"), "n_pairs"]) for case in SIMILARITY]
    return f"""We flagged {coverage.low_coverage.sum()} of {len(coverage)} editions below 50% tag coverage with ambiguous matches and {coverage.low_coverage_strict.sum()} without them, and kept them when both sides had tags after removing shared acts. Median full-lineup coverage was {coverage.coverage.median():.0%} and {coverage.coverage_strict.median():.0%}, respectively. The models compare excess shared acts within year and day-gap bins on {sizes[0]:,} and {sizes[1]:,} pairs, excluding same-brand pairs. The country comparisons before and after adjustment use the same pairs within each match policy.

1. The same-country gap moved from {before[0]:+.2f} to {effect(True, "country_after_genre")} with ambiguous matches and from {before[1]:+.2f} to {effect(False, "country_after_genre")} without them.
   This measures the country gap at the same genre similarity within year and date-gap bins.
   It misses finer timing, touring routes and untagged acts.

2. Each 0.10 higher cosine similarity corresponded to {effect(True, "genre_per_0_1")} excess acts with ambiguous matches and {effect(False, "genre_per_0_1")} without them.
   This measures the association between overlap and the sound of the acts unique to each lineup after accounting for country.
   It misses shifts in an act's sound over time and underrepresents acts booked at only one festival.
"""
