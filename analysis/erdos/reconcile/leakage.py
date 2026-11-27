"""missed article check on the fig. 2a null: move 22% or 45% of unlinked acts to one foreign edition"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent
ANALYSIS = OUT.parents[1]
sys.path[:0] = [str(ANALYSIS / "circuits"), str(ANALYSIS)]
from run import CLASSES, SAMPLES, check_margins, curveball_draws, reach_class
from common import load, same_brand


def stats(weights, same, endpoints):
    observed = weights[0]
    expected = weights[1:].mean(axis=0)
    excess = observed - expected
    gap = excess[same].mean() - excess[~same].mean()
    mixing = weights @ endpoints
    return gap, mixing


def assortativity(mixing, n_countries):
    mixing = mixing.reshape(-1, n_countries, n_countries)
    with np.errstate(divide="ignore", invalid="ignore"):
        mixing = mixing / mixing.sum(axis=(1, 2), keepdims=True)
        chance = (mixing.sum(axis=1) * mixing.sum(axis=2)).sum(axis=1)
        diagonal = np.trace(mixing, axis1=1, axis2=2)
        return np.divide(diagonal - chance, 1 - chance,
                         out=np.full(len(mixing), np.nan), where=chance < 1 - 1e-12)


def r_stats(r):
    null = r[1:][np.isfinite(r[1:])]
    null_mean = null.mean() if len(null) else np.nan
    return r[0], null_mean, r[0] - null_mean


def main():
    lineups, editions = load()
    reach = lineups.groupby("act_key")["festival"].nunique()
    wiki = pd.read_csv(ANALYSIS / "watts/reach/tiers.csv").set_index("act_key")
    baseline = wiki.tier.reindex(reach.index).fillna("1 festival")
    eligible = wiki.index[wiki.tier.eq("0 foreign") & wiki.n_languages.eq(0)]
    eligible = pd.Series(eligible.sort_values()).sample(frac=1, random_state=2808)
    classes = pd.DataFrame({"baseline": baseline})
    for rate in (22, 45):
        count = (len(eligible) * rate + 50) // 100
        classes[f"move_{rate}"] = baseline.mask(baseline.index.isin(eligible.iloc[:count]), "1 foreign")
    labels = {name: sorted(classes[name].unique()) for name in classes}
    countries = pd.Index(sorted(editions["country"].unique()))
    n_countries = len(countries)
    pairs_by_scheme = {name: [] for name in classes}
    pair_festivals = []

    for year, group in lineups.groupby("year"):
        sites = editions.set_index("edition").loc[sorted(group["edition"].unique())]
        booked = group.groupby("edition")["act_key"].agg(set)
        rows = booked.reindex(sites.index).tolist()
        left, right = np.triu_indices(len(rows), k=1)
        festivals = sites["festival"].to_numpy()
        keep = [not same_brand(festivals[i], festivals[j]) for i, j in zip(left, right)]
        left, right = left[keep], right[keep]
        pair_festivals.append(np.column_stack((festivals[left], festivals[right])))
        country = countries.get_indexer(sites["country"])
        a, b = country[left], country[right]
        pair_ids = list(zip(left, right))
        endpoints = np.zeros((len(left), n_countries ** 2), dtype=np.int64)
        endpoints[np.arange(len(left)), a * n_countries + b] += 1
        endpoints[np.arange(len(left)), b * n_countries + a] += 1

        pairs = {name: np.zeros((len(labels[name]), SAMPLES + 1, len(left)), dtype=np.int64)
                 for name in classes}
        codes = [pd.Categorical(classes[name], categories=labels[name]).codes for name in classes]
        act_codes = dict(zip(classes.index, zip(*codes)))
        assert all((code >= 0).all() for code in codes)
        draws = [rows, *curveball_draws(rows, year)]
        check_margins(draws[1], rows)
        check_margins(draws[-1], rows)
        for d, draw in enumerate(draws):
            for p, (i, j) in enumerate(pair_ids):
                for act in draw[i] & draw[j]:
                    for counts, code in zip(pairs.values(), act_codes[act]):
                        counts[code, d, p] += 1
        assert all(np.array_equal(weights.sum(axis=0), pairs["baseline"].sum(axis=0))
                   for weights in pairs.values())
        for name, weights in pairs.items():
            pairs_by_scheme[name].append((weights, a == b, endpoints))
        print(f"{year}: {len(left)} pairs, {SAMPLES} draws", flush=True)

    pair_festivals = np.concatenate(pair_festivals)
    endpoints = np.concatenate([group[2] for group in pairs_by_scheme["baseline"]])
    deletions = [(pair_festivals == festival).any(axis=1)
                 for festival in np.unique(pair_festivals)]
    result = []
    for name, groups in pairs_by_scheme.items():
        for k, label in enumerate(labels[name]):
            yearly = [stats(weights[k], same, endpoints) for weights, same, endpoints in groups]
            gap = np.mean([value for value, _ in yearly])
            pooled = sum(mixing for _, mixing in yearly)
            pooled_r = assortativity(pooled, n_countries)
            r, null_mean, excess = r_stats(pooled_r)
            null = pooled_r[1:][np.isfinite(pooled_r[1:])]
            null_low, null_high = (np.quantile(null - null_mean, [0.025, 0.975])
                                   if len(null) else (np.nan, np.nan))
            yearly_excess = np.array([
                r_stats(assortativity(mixing, n_countries))[2] for _, mixing in yearly
            ])
            weights = np.concatenate([weights[k] for weights, _, _ in groups], axis=1)
            deletion_excess = np.array([
                r_stats(assortativity(pooled - weights[:, mask] @ endpoints[mask], n_countries))[2]
                for mask in deletions
            ])
            finite_deletions = deletion_excess[np.isfinite(deletion_excess)]
            observed = weights[0]
            expected = weights[1:].mean(axis=0)
            same = np.concatenate([mask for _, mask, _ in groups])
            same_oe = observed[same].sum() / expected[same].sum() if expected[same].sum() else np.nan
            cross_oe = observed[~same].sum() / expected[~same].sum() if expected[~same].sum() else np.nan
            result.append(dict(scheme=name, reach=label, acts=int(classes[name].eq(label).sum()),
                               gap=gap, same_oe=same_oe, cross_oe=cross_oe,
                               tilt=same_oe / cross_oe if cross_oe else np.nan,
                               r=r, r_null_mean=null_mean, r_excess=excess,
                               r_positive_years=int((yearly_excess > 0).sum()),
                               r_defined_years=int(np.isfinite(yearly_excess).sum()),
                               r_deletion_min=min(finite_deletions, default=np.nan),
                               r_deletion_max=max(finite_deletions, default=np.nan),
                               r_null_low=null_low, r_null_high=null_high))
    table = pd.DataFrame(result)
    gap_share = table["gap"] / table.groupby("scheme")["gap"].transform("sum")
    table.insert(table.columns.get_loc("r_null_low"), "gap_share", gap_share)
    table.to_csv(OUT / "leakage_same_null.csv", index=False, float_format="%.9f")
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()
