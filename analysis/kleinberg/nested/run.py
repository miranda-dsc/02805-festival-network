"""measure yearly lineup nestedness and concentration"""
import random
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from numba import njit

OUT = Path(__file__).resolve().parent
SAMPLES = 400
DELETION_SAMPLES = 200
SEED = 28305
METRICS = ("nodf", "edition_nodf", "core_share", "core_share_all")

sys.dont_write_bytecode = True
sys.path.insert(0, str(OUT.parents[1]))
from common import load


@njit
def trade(booked, sizes, rows, attempts):
    pool = np.empty(2 * rows.shape[1], dtype=np.int32)
    for _ in range(attempts):
        a = np.random.randint(len(sizes))
        b = np.random.randint(len(sizes) - 1)
        b += b >= a
        left = 0
        for i in range(sizes[a]):
            act = rows[a, i]
            if not booked[b, act]:
                pool[left] = act
                left += 1
        count = left
        for i in range(sizes[b]):
            act = rows[b, i]
            if not booked[a, act]:
                pool[count] = act
                count += 1
        if left == 0 or left == count:
            continue
        for i in range(count):
            booked[a, pool[i]] = False
            booked[b, pool[i]] = False
        for i in range(left):
            j = np.random.randint(i, count)
            pool[i], pool[j] = pool[j], pool[i]
        for i in range(count):
            edition = a if i < left else b
            booked[edition, pool[i]] = True
        for edition in (a, b):
            index = 0
            for act in range(booked.shape[1]):
                if booked[edition, act]:
                    rows[edition, index] = act
                    index += 1


@njit
def nodf(booked, sizes, rows, degree):
    n = len(sizes)
    repeat_sizes = np.zeros(n, dtype=np.int32)
    overlap = np.zeros((n, n), dtype=np.int32)
    edition_pairs = n * (n - 1) // 2
    repeats = np.sum(degree >= 2)
    act_pairs = repeats * (repeats - 1) // 2
    act_score = 0.0
    for i in range(n):
        degree_counts = np.zeros(n + 1, dtype=np.int32)
        for act in rows[i, :sizes[i]]:
            d = degree[act]
            if d < 2:
                continue
            degree_counts[d] += 1
            repeat_sizes[i] += 1
            for j in range(i):
                overlap[i, j] += booked[j, act]
        higher_count = 0
        for d in range(n, 1, -1):
            act_score += degree_counts[d] * higher_count / d
            higher_count += degree_counts[d]

    edition_score = 0.0
    for i in range(n):
        for j in range(i):
            small = min(repeat_sizes[i], repeat_sizes[j])
            if small > 0 and repeat_sizes[i] != repeat_sizes[j]:
                edition_score += overlap[i, j] / small
    return (100 * (edition_score + act_score) / (edition_pairs + act_pairs),
            100 * edition_score / edition_pairs)


@njit
def core_share(degree, n_top):
    weights = degree * (degree - 1) // 2
    return 100 * weights[:n_top].sum() / weights.sum()


@njit
def measure(booked, sizes, rows, degree, n_top, n_top_all):
    total, edition = nodf(booked, sizes, rows, degree)
    return total, edition, core_share(degree, n_top), core_share(degree, n_top_all)


@njit
def simulate(matrix, sizes, rows, degree, n_top, n_top_all, draws, sweeps, seed):
    np.random.seed(seed)
    booked = matrix.copy()
    rows = rows.copy()
    values = np.empty((draws, 4))
    trade(booked, sizes, rows, 30 * len(sizes))
    for k in range(draws):
        trade(booked, sizes, rows, sweeps * len(sizes))
        shuffled_degree = booked.sum(axis=0)
        if not np.array_equal(shuffled_degree, degree) or not np.array_equal(booked.sum(axis=1), sizes):
            raise ValueError("curveball margins changed")
        values[k, :] = np.array(measure(booked, sizes, rows, shuffled_degree, n_top, n_top_all))
    return values


def analyze(matrix, samples, seed):
    active = matrix.sum(axis=0) > 0
    matrix = matrix[:, active]
    order = np.argsort(-matrix.sum(axis=0), kind="stable")
    matrix = np.ascontiguousarray(matrix[:, order])
    degree = matrix.sum(axis=0)
    sizes = matrix.sum(axis=1)
    rows = np.full((len(sizes), max(sizes)), -1, dtype=np.int32)
    for i, row in enumerate(matrix):
        rows[i, :sizes[i]] = np.flatnonzero(row)

    repeats = np.count_nonzero(degree >= 2)
    n_top = (repeats + 19) // 20
    n_top_all = (len(degree) + 19) // 20
    observed = measure(matrix, sizes, rows, degree, n_top, n_top_all)
    chains = [simulate(matrix, sizes, rows, degree, n_top, n_top_all, samples // 2, sweeps, seed + i)
              for i, sweeps in enumerate((2, 4))]
    null = np.concatenate(chains)
    results = []
    for i, metric in enumerate(METRICS):
        center = null[:, i].mean()
        sd = null[:, i].std(ddof=1)
        excess = observed[i] - center if sd > 1e-10 else 0.0
        results.append(dict(metric=metric, observed=observed[i], null_mean=center, null_sd=sd,
                            excess=excess, z=excess / sd if sd > 1e-10 else np.nan,
                            null_low=np.quantile(null[:, i], .025), null_high=np.quantile(null[:, i], .975),
                            chain_gap=abs(chains[0][:, i].mean() - chains[1][:, i].mean())))
    return pd.DataFrame(results).assign(editions=len(sizes), active=len(degree), repeated=repeats,
                                        top=n_top, top_all=n_top_all, samples=samples)


def write_report(results, festivals):
    full = results.query("deleted == '' and null == 'full'")
    deleted = results.query("deleted != ''")
    base = full.query("metric == 'nodf'").set_index("year")
    editions = full.query("metric == 'edition_nodf'").set_index("year")
    chain_gap = deleted.loc[deleted.metric.isin(("nodf", "edition_nodf")), "chain_gap"].max()

    def below(metric, model="full"):
        rows = results.loc[results.deleted.eq("") & results.metric.eq(metric) & results["null"].eq(model)]
        return f"{rows.excess.lt(0).sum()} of {len(rows)} years"

    def deletion_range(metric):
        original = full.loc[full.metric.eq(metric)].set_index("year").excess
        changes = deleted.loc[deleted.metric.eq(metric)]
        counts = []
        for festival in festivals:
            affected = changes.loc[changes.deleted.eq(festival)].set_index("year").excess
            scores = original.copy()
            scores.loc[affected.index] = affected
            counts.append(scores.lt(0).sum())
        return f"{min(counts)} to {max(counts)}"

    def share_range(rows):
        values = rows.loc[rows.metric.eq("core_share"), "observed"]
        return f"{values.min():.1f}% to {values.max():.1f}%"

    def cells(row):
        return " / ".join(f"{row[key]:.2f}" for key in ("observed", "null_mean", "null_sd", "z"))

    table = ["| Year | Editions | Repeat acts | Matrix NODF obs / null mean / SD / z | Edition NODF obs / null mean / SD / z |",
             "| --- | ---: | ---: | --- | --- |"]
    for year, row in base.iterrows():
        table.append(f"| {year} | {int(row.editions)} | {int(row.repeated)} | {cells(row)} | {cells(editions.loc[year])} |")
    report = f"""# Lineup nestedness

We used {base.editions.sum()} editions across {len(base)} years, excluding 2020 and 2021. NODF uses acts booked at two or more editions in the same year. We compared observed scores with {SAMPLES} curveball draws per year that preserve full lineup sizes and act booking counts, then applied the same act filter to each draw. Each festival deletion used {DELETION_SAMPLES} new draws for each affected year and kept the original result for unaffected years. The largest gap between deletion-chain means was {chain_gap:.2f} NODF points, so some small differences are sensitive to Monte Carlo variation. We retained Tomorrowland Winter and Weekend 1 as separate editions of the same brand. [NODF](https://doi.org/10.1111/j.0030-1299.2008.16644.x) [curveball](https://doi.org/10.1038/ncomms5114)

The yearly samples range from {base.editions.min()} to {base.editions.max()} editions, so the observed scores should not be read as a time trend.

{chr(10).join(table)}

1. The matrix was less nested than the shuffle in {below("nodf")}, or {deletion_range("nodf")} years after deleting any one of {len(festivals)} festivals across all its editions. The count was {below("nodf", "repeat")} when the null fixed repeat-act lineup sizes. Matrix NODF measures how often the smaller of two lineups, or the less booked of two acts, shares its partners with the larger one. It misses one-off acts and gives little weight to edition pairs.

2. Edition NODF was below the null mean in {below("edition_nodf")}, or {deletion_range("edition_nodf")} after festival deletion, and in {below("edition_nodf", "repeat")} when the null fixed each edition's repeat-act lineup size. Lower scores indicate less nesting than expected under the shuffle. Edition NODF measures the fraction of the smaller repeat-act lineup contained in the larger one, giving equal-size pairs a score of zero. It leaves out one-off acts and cannot identify what drives the booking differences.

The top 5% of repeat acts accounted for {share_range(full)} of shared-act counts across edition pairs, or {share_range(deleted)} after festival deletion, a descriptive share fixed by act booking counts.

Open problems

Test whether the most booked acts disproportionately connect festivals across countries or genres given their booking counts.
"""
    (OUT / "findings.md").write_text(report)


def main():
    lineups, editions = load()
    print(f"{len(editions)} editions, {len(lineups)} bookings", flush=True)
    seed = random.Random(SEED)
    results = []
    for year, group in editions.groupby("year"):
        bookings = lineups[lineups["year"] == year]
        matrix = pd.crosstab(bookings["edition"], bookings["act_key"]).reindex(group["edition"], fill_value=0)
        matrix = matrix.to_numpy(dtype=bool)
        results.append(analyze(matrix, SAMPLES, seed.randrange(2**32 - 1)).assign(
            year=year, deleted="", null="full"))
        repeat_matrix = matrix[:, matrix.sum(axis=0) >= 2]
        results.append(analyze(repeat_matrix, SAMPLES, seed.randrange(2**32 - 1)).assign(
            year=year, deleted="", null="repeat"))
        for festival in group["festival"].unique():
            keep = group["festival"].ne(festival).to_numpy()
            results.append(analyze(matrix[keep], DELETION_SAMPLES, seed.randrange(2**32 - 1)).assign(
                year=year, deleted=festival, null="full"))
        print(f"{year}, {len(group)} editions, {group['festival'].nunique()} festival deletions", flush=True)
    results = pd.concat(results, ignore_index=True)
    results.to_csv(OUT / "yearly.csv", index=False)
    write_report(results, editions.festival.unique())


if __name__ == "__main__":
    main()
