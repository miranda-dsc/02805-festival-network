"""check booking reach against loyalty, tags and wikipedia reach"""
from importlib.util import module_from_spec, spec_from_file_location
from itertools import combinations
from pathlib import Path
import sys

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent
ANALYSIS = OUT.parents[1]
sys.path[:0] = [str(ANALYSIS), str(ANALYSIS / "watts")]
from common import load, same_brand
from genre_profiles import MATCHED, tagged_acts

CIRCUITS = ANALYSIS / "circuits"
SPEC = spec_from_file_location("circuits_run", CIRCUITS / "run.py")
circuits = module_from_spec(SPEC)
SPEC.loader.exec_module(circuits)

REACH = [label for label in circuits.CLASSES if label != circuits.reach_class(1)]
TAG_STATUS = ("untagged", "strict tagged")
TIERS = ["0 foreign", "1 foreign", "2 to 4 foreign", "5 to 9 foreign",
         "10 or more foreign", "Unknown artist country", "Unknown MBID"]


def country_share(bookings, locations, country, n_acts, distinct):
    n_locations = len(country)
    if distinct:
        bookings = np.unique(bookings * n_locations + locations)
        bookings, locations = np.divmod(bookings, n_locations)
    n_countries = int(country.max()) + 1
    counts = np.bincount(bookings * n_countries + country[locations],
                         minlength=n_acts * n_countries).reshape(n_acts, n_countries)
    totals = counts.sum(axis=1)
    return counts.max(axis=1) / totals, totals


def national_shares(lineups, editions, acts):
    editions = editions.set_index("edition").sort_index()
    festival, _ = pd.factorize(editions.festival, sort=True)
    country, _ = pd.factorize(editions.country, sort=True)
    festival_country = np.full(festival.max() + 1, -1)
    for f, c in zip(festival, country):
        if festival_country[f] not in (-1, c):
            raise ValueError("festival country differs across editions")
        festival_country[f] = c

    lineups = lineups.assign(code=acts.index.get_indexer(lineups.act_key))
    observed = lineups.code.to_numpy()
    location = editions.index.get_indexer(lineups.edition)
    drawn = np.empty((circuits.SAMPLES, len(lineups)), dtype=int)
    drawn_location = np.empty(len(lineups), dtype=int)
    tilt_rows = []
    offset = 0
    for year, group in lineups.groupby("year"):
        groups = group.groupby("edition").code.agg(set).sort_index()
        rows = groups.to_list()
        indices = editions.index.get_indexer(groups.index)
        end = offset + len(group)
        drawn_location[offset:end] = np.repeat(indices, [len(row) for row in rows])
        metadata = editions.loc[groups.index]
        pairs = [(i, j) for i, j in combinations(range(len(rows)), 2)
                 if not same_brand(metadata.festival.iloc[i], metadata.festival.iloc[j])]
        pair_bins = np.array([metadata.country.iloc[i] == metadata.country.iloc[j]
                              for i, j in pairs], dtype=int)
        observed_pairs = overlap_counts(rows, pairs, acts.stratum.to_numpy())
        null_pairs = np.zeros_like(observed_pairs)
        for i, draw in enumerate(circuits.curveball_draws(rows, int(year))):
            if i in (0, circuits.SAMPLES - 1):
                circuits.check_margins(draw, rows)
            drawn[i, offset:end] = [code for row in draw for code in row]
            null_pairs += overlap_counts(draw, pairs, acts.stratum.to_numpy())
        for (i, j), same, obs, null in zip(pairs, pair_bins, observed_pairs, null_pairs):
            tilt_rows.append((metadata.festival.iloc[i], metadata.festival.iloc[j],
                              bool(same), obs, null / circuits.SAMPLES))
        offset = end
        print(f"{year} completed", flush=True)

    rows = []
    cohorts = []
    for reach in REACH:
        member = acts.reach.eq(reach)
        no_repeats = member & acts.editions.eq(acts.festivals)
        cohorts.extend([(reach, "all", None, member), (reach, "exact k", None, no_repeats)])
        for k in sorted(acts.loc[no_repeats, "editions"].unique()):
            cohorts.append((reach, "exact k", int(k), no_repeats & acts.editions.eq(k)))
    for weighting in ("distinct festival", "edition"):
        distinct = weighting == "distinct festival"
        obs_location = festival[location] if distinct else location
        null_location = festival[drawn_location] if distinct else drawn_location
        country_codes = festival_country if distinct else country
        obs, _ = country_share(observed, obs_location, country_codes, len(acts), distinct)
        summaries = [country_share(draw, null_location, country_codes, len(acts), distinct)
                     for draw in drawn]
        null, booked_locations = map(np.stack, zip(*summaries))
        for reach, subset, k, member in cohorts:
            values = null[:, member]
            value = obs[member].mean()
            if subset == "exact k":
                if not distinct:
                    continue
                accepted = booked_locations[:, member] == acts.loc[member, "editions"].to_numpy()
                counts = accepted.sum(axis=0)
                if not counts.all():
                    raise ValueError("some exact-k acts have no accepted draws")
                expected = (np.where(accepted, values, 0).sum(axis=0) / counts).mean()
                low = high = np.nan
                min_draws, median_draws = counts.min(), np.median(counts)
            else:
                per_draw = values.mean(axis=1)
                low, high = np.quantile(per_draw, [0.025, 0.975])
                expected = per_draw.mean()
                min_draws = median_draws = circuits.SAMPLES
            rows.append(dict(weighting=weighting, reach=reach, subset=subset, k=k,
                             acts=int(member.sum()), observed=value, null_mean=expected,
                             null_low=low, null_high=high, excess=value - expected,
                             accepted_min=min_draws, accepted_median=median_draws))
    write_tilt(tilt_rows, acts)
    return pd.DataFrame(rows).astype({"k": "Int64"})


def overlap_counts(lineups, pairs, strata):
    width = 1 + len(REACH) * len(TAG_STATUS)
    return np.array([np.bincount(strata[list(lineups[i] & lineups[j])], minlength=width)
                     for i, j in pairs])


def write_tilt(pair_rows, acts):
    festival_a, festival_b, same, obs, null = map(np.asarray, zip(*pair_rows))
    results = []
    for i, reach in enumerate(REACH):
        for j, tag in enumerate(TAG_STATUS):
            code = 1 + i * len(TAG_STATUS) + j

            def ratios(keep):
                counts = [array[keep & mask, code].sum()
                          for mask in (same, ~same) for array in (obs, null)]
                same_obs, same_exp, diff_obs, diff_exp = counts
                same_ratio = same_obs / same_exp
                diff_ratio = diff_obs / diff_exp
                return (*counts, same_ratio, diff_ratio, same_ratio / diff_ratio)

            pooled = ratios(np.ones(len(same), dtype=bool))
            deletes = [ratios((festival_a != f) & (festival_b != f))[-1]
                       for f in np.union1d(festival_a, festival_b)]
            results.append(dict(reach=reach, tag=tag, acts=int(acts.stratum.eq(code).sum()),
                                same_observed=int(pooled[0]), same_expected=pooled[1],
                                different_observed=int(pooled[2]), different_expected=pooled[3],
                                same_ratio=pooled[4], different_ratio=pooled[5], tilt=pooled[6],
                                tilt_deletion_low=min(deletes), tilt_deletion_high=max(deletes)))
    pd.DataFrame(results).to_csv(OUT / "tilt_by_tags.csv", index=False)


def cross_tabs(acts):
    tags = acts.tag
    tiers = pd.read_csv(ANALYSIS / "watts/reach/tiers.csv", keep_default_na=False)
    tiers = tiers.set_index("act_key", verify_integrity=True).tier
    eligible = acts.loc[acts.festivals.ge(2), "reach"]
    if set(tiers.index) != set(eligible.index) or set(tiers) != set(TIERS):
        raise ValueError("Wikipedia tiers differ from the repeat-festival cohort")
    for name, labels, columns in (
        ("tags", pd.Series(tags, index=acts.index), ["strict tagged", "untagged"]),
        ("wikipedia", tiers, TIERS),
    ):
        table = pd.crosstab(eligible, labels.reindex(eligible.index))
        table = table.reindex(index=REACH, columns=columns, fill_value=0)
        table["total"] = table.sum(axis=1)
        if not table.total.eq(eligible.value_counts()).all():
            raise ValueError("cross-tab lost eligible acts")
        table.to_csv(OUT / f"reach_by_{name}.csv")


def abroad_summary(lineups, editions):
    pairs = pd.read_csv(CIRCUITS / "pairs_by_reach.csv")
    pairs = pairs[pairs.reach.isin(REACH)].copy()
    bookings = lineups.groupby("edition").act_key.agg(set)
    classes = lineups.groupby("act_key").festival.nunique().map(circuits.reach_class).to_dict()
    for row in pairs.itertuples():
        shared = bookings[row.edition_a] & bookings[row.edition_b]
        if sum(classes[a] == row.reach for a in shared) != row.observed:
            raise ValueError("circuits observed overlap differs from the shared loader")

    def stats(frame):
        same = frame[frame.same_country & ~frame.uk_pair]
        different = frame[~frame.same_country]
        obs = int(same.observed.sum())
        expected = same.null_mean.sum()
        by_year = same.groupby("year").excess.mean() - different.groupby("year").excess.mean()
        distinct = len({tuple(sorted(pair)) for pair in zip(same.festival_a, same.festival_b)})
        return dict(pair_years=len(same), distinct_festival_pairs=distinct,
                    observed=obs, expected=expected, ratio=obs / expected,
                    gap=by_year.mean(), years=int(by_year.notna().sum()),
                    positive_years=int(by_year.gt(0).sum()))

    rows = []
    deletions = []
    countries = []
    for reach, group in pairs.groupby("reach", sort=False):
        abroad = group[group.same_country & ~group.uk_pair]
        for country in sorted(abroad.country_a.unique()):
            keep = ~((group.country_a == country) & (group.country_b == country))
            countries.append(dict(reach=reach, country_removed=country, **stats(group[keep])))
        summary = stats(group)
        results = []
        for festival in sorted(editions.festival.unique()):
            keep = group.festival_a.ne(festival) & group.festival_b.ne(festival)
            result = stats(group[keep])
            results.append(result)
            deletions.append(dict(reach=reach, festival_removed=festival, **result))
        for column in ("observed", "expected", "ratio", "gap"):
            values = [result[column] for result in results]
            summary[f"{column}_deletion_low"] = min(values)
            summary[f"{column}_deletion_high"] = max(values)
        rows.append(dict(reach=reach, **summary))
    for name, records in (("outside_gb", rows), ("outside_gb_deletions", deletions),
                          ("outside_gb_country_deletions", countries)):
        pd.DataFrame(records).to_csv(OUT / f"{name}.csv", index=False)


def edition_audit(lineups, editions):
    coverage = pd.read_csv(ANALYSIS / "newman/wikitext/edition_coverage.csv")
    sizes = lineups.groupby("edition").size()
    if not coverage.set_index("edition").lineup_size.sort_index().equals(sizes.sort_index()):
        raise ValueError("Wikipedia coverage lineup sizes differ from the shared loader")
    edition = sizes.idxmax()
    year = editions.set_index("edition").at[edition, "year"]
    pairs = pd.read_csv(ANALYSIS / "watts/pairs.csv")
    pairs = pairs[~pairs.same_brand]
    bookings = lineups.groupby("edition").act_key.agg(set)
    incident = pairs[pairs.edition_a.eq(edition) | pairs.edition_b.eq(edition)]
    for row in incident.itertuples():
        if len(bookings[row.edition_a] & bookings[row.edition_b]) != row.shared_acts:
            raise ValueError("edition overlap differs from the shared loader")
    result = []
    for period, frame in (("all retained years", pairs), (str(year), pairs[pairs.year.eq(year)])):
        for country, group in (("all pairs", frame), ("same country", frame[frame.same_country]),
                               ("different countries", frame[~frame.same_country])):
            affected = group[group.index.isin(incident.index)]
            others = group[~group.index.isin(incident.index)]
            result.append(dict(edition=edition, period=period, country=country,
                               pairs=len(group), edition_pairs=len(affected),
                               observed=group.shared_acts.sum(),
                               edition_observed=affected.shared_acts.sum(),
                               expected=group.null_mean.sum(), edition_expected=affected.null_mean.sum(),
                               mean_excess=group.excess.mean(),
                               mean_excess_without_edition=others.excess.mean()))
    pd.DataFrame(result).to_csv(OUT / "largest_edition_pairs.csv", index=False)


def main():
    lineups, editions = load()
    acts = lineups.groupby("act_key").agg(festivals=("festival", "nunique"),
                                         editions=("edition", "nunique"))
    acts["reach"] = acts.festivals.map(circuits.reach_class)
    tags = tagged_acts()
    strict = tags.loc[tags.method.isin(MATCHED), "act_key"]
    acts["tag"] = np.where(acts.index.isin(strict), TAG_STATUS[1], TAG_STATUS[0])
    acts["stratum"] = 0
    for i, reach in enumerate(REACH):
        for j, tag in enumerate(TAG_STATUS):
            acts.loc[acts.reach.eq(reach) & acts.tag.eq(tag), "stratum"] = 1 + i * len(TAG_STATUS) + j
    national_shares(lineups, editions, acts).to_csv(OUT / "national_share.csv", index=False)
    cross_tabs(acts)
    abroad_summary(lineups, editions)
    edition_audit(lineups, editions)


if __name__ == "__main__":
    main()
