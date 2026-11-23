"""build yearly festival networks and compare them with curveball samples"""

import os
import random
import sys
from itertools import combinations
from pathlib import Path
from tempfile import TemporaryDirectory

OUT = Path("analysis/newman")
os.environ.setdefault("MPLBACKEND", "Agg")
if "MPLCONFIGDIR" not in os.environ:
    plot_cache = TemporaryDirectory(dir=OUT)
    os.environ["MPLCONFIGDIR"] = plot_cache.name

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, triu
from sklearn.metrics import normalized_mutual_info_score

sys.path.insert(0, str(OUT.resolve().parent))
sys.dont_write_bytecode = True
from common import SAME_BRAND, load, same_brand
SAMPLES = 200
SEEDS = (19, 23, 31, 41, 53)
GAPS = (5, 10)
BURN_IN = 50
DASHES = dict.fromkeys(map(ord, "\u2010\u2011\u2012\u2013\u2014\u2015\u2212"), "-")

plt.rcParams["axes.unicode_minus"] = False


def curveball(rows, n_acts, year):
    """trade edition rows as in euler, with both margins checked for every draw"""
    sizes = [len(row) for row in rows]
    degrees = np.bincount([a for row in rows for a in row], minlength=n_acts)
    for chain, gap in enumerate(GAPS):
        rng = random.Random(817 + year + 100000 * chain)
        state = [row.copy() for row in rows]
        for draw in range(SAMPLES // len(GAPS) + 1):
            sweeps = BURN_IN if draw == 0 else gap
            for _ in range(sweeps * len(rows)):
                i, j = rng.sample(range(len(rows)), 2)
                left, right = state[i] - state[j], state[j] - state[i]
                if left and right:
                    pool = sorted(left | right)
                    rng.shuffle(pool)
                    common = state[i] & state[j]
                    state[i] = common | set(pool[:len(left)])
                    state[j] = common | set(pool[len(left):])
            if draw:
                assert [len(row) for row in state] == sizes
                assert np.array_equal(
                    np.bincount([a for row in state for a in row], minlength=n_acts), degrees
                )
                yield chain, state


def louvain(weights, seed_agreement=False):
    graph = nx.from_numpy_array(weights)
    labels, scores = [], []
    for seed in SEEDS:
        if graph.number_of_edges():
            groups = nx.community.louvain_communities(graph, seed=seed, weight="weight")
            scores.append(nx.community.modularity(graph, groups, weight="weight"))
        else:
            groups = [{i} for i in graph]
            scores.append(np.nan)
        ids = np.empty(len(graph), dtype=int)
        for group_id, group in enumerate(sorted(groups, key=min)):
            ids[list(group)] = group_id
        labels.append(ids)
    nmi = np.array([normalized_mutual_info_score(a, b) for a, b in combinations(labels, 2)]) if seed_agreement else None
    return np.array(scores), np.stack(labels), nmi


def measure(rows, n_acts, festival_map, seed_agreement=False):
    sizes = np.array([len(row) for row in rows])
    indices = np.array([act for row in rows for act in sorted(row)], dtype=int)
    incidence = csr_matrix(
        (np.ones(len(indices), dtype=np.int32), (np.repeat(np.arange(len(rows)), sizes), indices)),
        shape=(len(rows), n_acts),
    )
    festival_incidence = (festival_map @ incidence).astype(bool).astype(np.int32)
    degrees = np.asarray(festival_incidence.sum(axis=0)).ravel()
    shared = degrees >= 2
    counts = np.asarray(incidence[:, shared].sum(axis=1)).ravel()
    shares = np.divide(counts, sizes, out=np.full(len(rows), np.nan), where=sizes > 0)
    weights = (incidence @ incidence.T).toarray()
    np.fill_diagonal(weights, 0)
    selected = incidence[:, shared]
    act_edges = triu(selected.T @ selected, k=1, format="coo")
    scores, labels, nmi = louvain(weights, seed_agreement)
    stats = {
        "edition_nodes": len(rows),
        "act_nodes": n_acts,
        "bipartite_edges": int(sizes.sum()),
        "edition_edges": np.count_nonzero(np.triu(weights, 1)),
        "edition_weight": np.triu(weights, 1).sum(),
        "shared_act_nodes": shared.sum(),
        "act_edges": act_edges.nnz,
        "act_weight": act_edges.data.sum(),
        "mean_lineup_share": np.nanmean(shares),
        "pooled_lineup_share": counts.sum() / sizes.sum(),
        "modularity": np.mean(scores),
        "communities": np.mean([len(set(ids)) for ids in labels]),
    }
    return stats, shares, degrees, weights, act_edges, scores, labels, nmi, counts


def summarize(observed, null):
    null = np.asarray(null, dtype=float)
    mean = np.mean(null, axis=0)
    sd = np.std(null, axis=0, ddof=1)
    fixed = np.all(null == null[0], axis=0)
    sd = np.where(fixed, 0.0, sd)
    return {"observed": observed, "null_mean": mean[()], "null_sd": sd[()]}


def co_membership(festivals_a, labels_a, festivals_b, labels_b):
    """count pair intersections and unions per draw and seed on common festivals"""
    _, index_a, index_b = np.intersect1d(festivals_a, festivals_b, return_indices=True)
    i, j = np.triu_indices(len(index_a), k=1)
    together_a = labels_a[..., index_a[i]] == labels_a[..., index_a[j]]
    together_b = labels_b[..., index_b[i]] == labels_b[..., index_b[j]]
    intersection = (together_a & together_b).sum(axis=-1)
    union = (together_a | together_b).sum(axis=-1)
    return len(index_a), intersection, union


def jaccard(intersection, union):
    ratios = np.divide(intersection, union, out=np.zeros_like(union, dtype=float),
                       where=union > 0)
    return ratios.mean(axis=-1)


def save(frame, name):
    frame.to_csv(OUT / f"{name}.csv", index=False, float_format="%.10g")


lineups, editions = load()
editions = editions.sort_values("edition").copy()
editions["brand"] = np.where(editions.festival.isin(set().union(*SAME_BRAND)), "tomorrowland", "")
assert not editions.duplicated(["year", "festival"]).any()
print(f"{len(editions)} editions and {len(lineups)} bookings from shared loader", flush=True)

yearly, distributions, lineup_stats, rankings, communities, seed_pairs, null_metrics, edition_nodes = (
    [], [], [], [], [], [], [], []
)
country_stats, country_draws, community_names, brand_pairs = [], [], [], []
year_partitions, deleted_partitions = {}, {}
deletion_stats = []
for year, metadata in editions.groupby("year"):
    ids = metadata.edition.to_numpy()
    year_lineups = lineups.loc[lineups.edition.isin(ids)].sort_values(["edition", "act_key"])
    acts = np.array(sorted(year_lineups.act_key.unique()))
    act_index = {act: i for i, act in enumerate(acts)}
    groups = year_lineups.groupby("edition").act_key.agg(set)
    rows = [{act_index[act] for act in groups.get(edition, set())} for edition in ids]
    festival_codes, festival_names = pd.factorize(metadata.festival, sort=True)
    festival_map = csr_matrix(
        (np.ones(len(ids), dtype=int), (festival_codes, np.arange(len(ids)))),
        shape=(len(festival_names), len(ids)),
    )
    observed, shares, degrees, weights, act_edges, scores, labels, nmi, counts = measure(
        rows, len(acts), festival_map, seed_agreement=True
    )
    act_degrees = year_lineups.groupby("act_key").size().reindex(acts).to_numpy()
    assert observed["bipartite_edges"] == len(year_lineups)
    assert np.array_equal(degrees, act_degrees) or len(festival_names) < len(ids)
    assert observed["edition_weight"] == (act_degrees * (act_degrees - 1) // 2).sum()
    save(year_lineups[["edition", "act_key"]], f"bipartite_{year}")
    i, j = np.nonzero(np.triu(weights, 1))
    brand = metadata.brand.ne("").to_numpy()
    save(pd.DataFrame({
        "edition_a": ids[i], "edition_b": ids[j], "weight": weights[i, j],
        "same_brand": [same_brand(metadata.festival.iloc[a], metadata.festival.iloc[b])
                       for a, b in zip(i, j)],
    }), f"edition_edges_{year}")
    for a, b in combinations(np.flatnonzero(brand), 2):
        if not same_brand(metadata.festival.iloc[a], metadata.festival.iloc[b]):
            continue
        brand_pairs.append({
            "year": year, "edition_a": ids[a], "edition_b": ids[b],
            "festival_a": metadata.festival.iloc[a], "festival_b": metadata.festival.iloc[b],
            "brand": "tomorrowland",
        })
    shared_acts = acts[degrees >= 2]
    save(pd.DataFrame({
        "act_key_a": shared_acts[act_edges.row], "act_key_b": shared_acts[act_edges.col],
        "weight": act_edges.data,
    }).sort_values(["act_key_a", "act_key_b"]), f"act_edges_{year}")
    edition_nodes.append(metadata[["year", "edition", "festival", "country", "lat", "lon", "start_date", "brand"]])

    country = metadata.country.fillna("").to_numpy()
    known_country = country != ""
    country = country[known_country]
    assert len(country)
    country_rng = np.random.default_rng(509 + int(year))
    country_nmi = np.mean([normalized_mutual_info_score(country, ids[known_country])
                           for ids in labels])
    country_null = []
    null_shares, null_degrees, null_stats, null_labels = [], [], [], []
    for draw, (chain, state) in enumerate(curveball(rows, len(acts), int(year)), 1):
        stats, draw_shares, draw_degrees, _, _, _, draw_labels, _, _ = measure(
            state, len(acts), festival_map
        )
        null_labels.append(draw_labels)
        shuffled_country = country_rng.permutation(country)
        shuffled_nmi = np.mean([
            normalized_mutual_info_score(shuffled_country, ids[known_country]) for ids in labels
        ])
        country_null.append(shuffled_nmi)
        country_draws.append({"year": year, "draw": draw, "nmi": shuffled_nmi})
        null_stats.append(stats)
        null_shares.append(draw_shares)
        null_degrees.append(draw_degrees)
        null_metrics.append({"year": year, "draw": draw, "chain": chain, **stats})
    assert len(null_stats) == SAMPLES
    country_stats.append({
        "year": year, "editions": len(country), "countries": len(set(country)),
        **summarize(country_nmi, country_null),
    })
    year_partitions[year] = (metadata.festival.to_numpy(), np.stack([labels, *null_labels]))
    for dropped, festival in enumerate(metadata.festival):
        keep = np.arange(len(ids)) != dropped
        reduced_rows = [row for i, row in enumerate(rows) if i != dropped]
        reduced, _, _, _, _, _, reduced_labels, _, _ = measure(
            reduced_rows, len(acts), festival_map[:, keep]
        )
        deleted_partitions[year, festival] = (metadata.festival.to_numpy()[keep], reduced_labels)
        retained_countries = metadata.country.iloc[np.flatnonzero(keep)]
        known = retained_countries.notna() & retained_countries.ne("")
        reduced["country_nmi"] = np.mean([
            normalized_mutual_info_score(retained_countries[known], ids[known.to_numpy()])
            for ids in reduced_labels
        ])
        metrics = ("edition_edges", "act_edges", "mean_lineup_share", "modularity", "country_nmi")
        deletion_stats.append({"year": year, "festival_removed": festival,
                               **{metric: reduced[metric] for metric in metrics}})
    yearly.extend([
        {"year": year, "metric": "mean_nmi", "observed": nmi.mean()},
        {"year": year, "metric": "min_nmi", "observed": nmi.min()},
    ])
    for metric, value in observed.items():
        yearly.append({
            "year": year, "metric": metric,
            **summarize(value, [stats[metric] for stats in null_stats]),
        })

    n_festivals = len(festival_names)
    bins = np.arange(1, n_festivals + 1)
    null_hist = [np.bincount(draw, minlength=n_festivals + 1)[1:] for draw in null_degrees]
    distributions.append(pd.DataFrame({
        "year": year, "festivals": bins,
        **summarize(np.bincount(degrees, minlength=n_festivals + 1)[1:], null_hist),
    }))
    lineup_stats.append(pd.DataFrame({
        "year": year, "edition": ids, "festival": metadata.festival.to_numpy(),
        "lineup_size": [len(row) for row in rows], "shared_acts": counts,
        **summarize(shares, null_shares),
    }))
    names = year_lineups.drop_duplicates("act_key").set_index("act_key").act
    ranks = pd.DataFrame({
        "year": year, "act_key": acts, "act": [names[act].translate(DASHES) for act in acts],
        "editions": act_degrees,
        **summarize(degrees, null_degrees),
    }).rename(columns={"observed": "festivals"})
    ranks["rank"] = ranks.festivals.rank(method="min", ascending=False).astype(int)
    rankings.append(ranks.loc[ranks.festivals >= 2].sort_values(["rank", "act_key"]))
    for seed, score, assignment in zip(SEEDS, scores, labels):
        communities.append(pd.DataFrame({
            "year": year, "edition": ids, "seed": seed, "community": assignment,
            "modularity": score,
        }))
        for community in np.unique(assignment):
            members = assignment == community
            bookings = year_lineups.loc[year_lineups.edition.isin(ids[members])]
            leaders = (bookings.groupby("act_key").size().rename("bookings").reset_index()
                       .sort_values(["bookings", "act_key"], ascending=[False, True]).head(3))
            member_festivals = sorted(metadata.loc[members, "festival"])
            name = {
                "year": year, "seed": seed, "community": community,
                "festivals": " | ".join(member_festivals),
            }
            for rank, (key, count) in enumerate(leaders.itertuples(index=False, name=None), 1):
                name[f"act_{rank}"] = names[key].translate(DASHES)
                name[f"act_key_{rank}"] = key
                name[f"bookings_{rank}"] = count
            community_names.append(name)
    for (a, b), value in zip(combinations(SEEDS, 2), nmi):
        seed_pairs.append({"year": year, "seed_a": a, "seed_b": b, "nmi": value})
    print(f"{year}: {len(ids)} editions, {len(acts)} acts, "
          f"{observed['edition_edges']} edition edges, {SAMPLES} checked draws", flush=True)

temporal_stats = []
pooled_intersection = np.zeros((SAMPLES + 1, len(SEEDS)), dtype=int)
pooled_union = np.zeros_like(pooled_intersection)
for a, b in combinations(year_partitions, 2):
    festivals_a, labels_a = year_partitions[a]
    festivals_b, labels_b = year_partitions[b]
    common, intersection, union = co_membership(festivals_a, labels_a, festivals_b, labels_b)
    if common < 2:
        continue
    scores = jaccard(intersection, union)
    temporal_stats.append({
        "year_a": a, "year_b": b, "shared_festivals": common,
        **summarize(scores[0], scores[1:]),
    })
    pooled_intersection += intersection
    pooled_union += union

pooled_scores = jaccard(pooled_intersection, pooled_union)
pooled_temporal = summarize(pooled_scores[0], pooled_scores[1:])
temporal_deletions = []
for festival in sorted(editions.festival.unique()):
    intersection_total = np.zeros(len(SEEDS), dtype=int)
    union_total = np.zeros_like(intersection_total)
    for a, b in combinations(year_partitions, 2):
        names_a, labels_a = year_partitions[a]
        names_b, labels_b = year_partitions[b]
        parts_a = deleted_partitions.get((a, festival), (names_a, labels_a[0]))
        parts_b = deleted_partitions.get((b, festival), (names_b, labels_b[0]))
        _, intersection, union = co_membership(*parts_a, *parts_b)
        intersection_total += intersection
        union_total += union
    temporal_deletions.append({"festival_removed": festival,
                               "jaccard": jaccard(intersection_total, union_total)})
deletions = pd.DataFrame(deletion_stats)
temporal_deletions = pd.DataFrame(temporal_deletions)
save(deletions, "festival_deletions")
save(temporal_deletions, "community_consistency_deletions")

country_results = pd.DataFrame(country_stats)
save(country_results, "country_nmi")
save(pd.DataFrame(country_draws), "country_null_samples")
save(pd.DataFrame(temporal_stats), "community_consistency_by_year_pair")
save(pd.DataFrame([pooled_temporal]), "community_consistency")
save(pd.DataFrame({"draw": np.arange(1, SAMPLES + 1), "jaccard": pooled_scores[1:]}),
     "community_consistency_null_samples")
save(pd.DataFrame(community_names), "community_names")
save(pd.DataFrame(brand_pairs), "same_brand_pairs")

stats = pd.DataFrame(yearly)
degrees = pd.concat(distributions, ignore_index=True)
shares = pd.concat(lineup_stats, ignore_index=True)
ranks = pd.concat(rankings, ignore_index=True)
save(stats, "yearly_stats")
save(degrees, "festival_degrees")
save(shares, "lineup_shares")
save(ranks, "shared_acts")
save(pd.concat(communities), "communities")
save(pd.DataFrame(seed_pairs), "seed_nmi")
save(pd.DataFrame(null_metrics), "null_samples")
save(pd.concat(edition_nodes), "edition_nodes")

focus = 2019
focus_degrees = degrees.query("year == @focus and observed > 0")
positions = focus_degrees.festivals.to_numpy()
fig, axes = plt.subplots(1, 2, figsize=(10.5, 4), layout="constrained")
ax = axes[0]
ax.bar(positions, focus_degrees.observed, width=0.65, color="#39748c", label="Observed")
ax.errorbar(positions, focus_degrees.null_mean, yerr=focus_degrees.null_sd,
            fmt="o", color="#ad542b", ms=4, capsize=2, label="Null mean and SD")
ax.set(xlabel="Festivals per act", ylabel="Acts (log scale)", yscale="log",
       xticks=positions, title="Act degrees in 2019")
ax.legend(frameon=False)

ax = axes[1]
years = sorted(shares.year.unique())
for year in years:
    frame = shares.query("year == @year").sort_values("observed")
    ax.scatter(np.repeat(year, len(frame)), frame.observed * 100,
               s=13, alpha=0.58, color="#39748c")
mean = stats.query("metric == 'mean_lineup_share'")
ax.plot(mean.year - 0.15, mean.observed * 100, "D", color="#235268", ms=4,
        label="Observed mean")
ax.errorbar(mean.year + 0.15, mean.null_mean * 100, yerr=mean.null_sd * 100,
            fmt="o", ms=4, color="#ad542b", capsize=2, label="Null mean and SD")
ax.set(xlabel="Year", ylabel="Lineup shared across festivals (%)", title="Shared lineups",
       xticks=years)
ax.tick_params(axis="x", rotation=45)
ax.legend(frameon=False)
fig.savefig(OUT / "act_degrees_and_lineups.png", dpi=180)
plt.close(fig)

fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.8), layout="constrained")
for ax, metric, title, label in zip(
    axes,
    ("edition_edges", "modularity", "mean_nmi"),
    ("Edition links", "Louvain modularity", "Seed agreement"),
    ("Edition pairs sharing acts", "Mean weighted modularity", "Mean pairwise NMI"),
):
    frame = stats.query("metric == @metric")
    if metric != "mean_nmi":
        ax.errorbar(frame.year, frame.null_mean, yerr=frame.null_sd, fmt="o",
                    color="#ad542b", capsize=3, ms=4, label="Null mean and SD")
    ax.plot(frame.year, frame.observed, "o", color="#39748c", ms=5, label="Observed")
    ax.set(xlabel="Year", ylabel=label, title=title, xticks=years)
    ax.tick_params(axis="x", rotation=45)
axes[0].legend(frameon=False)
fig.savefig(OUT / "edition_structure.png", dpi=180)
plt.close(fig)


def count_against_null(frame, above=True):
    delta = frame.observed - frame.null_mean
    return int((delta > 0 if above else delta < 0).sum())


def deletion_range(values, precision=3, scale=1):
    return (f"{values.min() * scale:,.{precision}f} to "
            f"{values.max() * scale:,.{precision}f}")


example = stats.loc[stats.year == focus].set_index("metric").observed
one = int(focus_degrees.loc[focus_degrees.festivals == 1, "observed"].iloc[0])
leaders = ranks.query("year == @focus and rank == 1")
leader_names = ", ".join(leaders.act)
leader_degree = int(leaders.festivals.iloc[0])
n_years = len(years)
focus_deletions = deletions.query("year == @focus")
edition_deficits = count_against_null(stats.query("metric == 'edition_edges'"), above=False)
act_deficits = count_against_null(stats.query("metric == 'act_edges'"), above=False)
modularity_excesses = count_against_null(stats.query("metric == 'modularity'"))
share_excesses = count_against_null(stats.query("metric == 'mean_lineup_share'"))
country_above = count_against_null(country_results)
country_focus = country_results.query("year == @focus").observed.iloc[0]
temporal_above = count_against_null(pd.DataFrame(temporal_stats))

report = f"""We used the shared loader with site countries, excluding Leeds, rebroadcasts, 2020 and 2021.
We checked both margins in {SAMPLES} curveball draws per year and used {len(SEEDS)} fixed Louvain seeds.
Deletion ranges give observed values after dropping one festival at a time and refitting. The flagged Tomorrowland pair stays in the graphs.

1. In 2019, {int(example.act_nodes):,} acts and {int(example.edition_nodes)} editions made {int(example.bipartite_edges):,} bookings, with both margins checked against the input and every draw.
This counts the scale of the sampled lineups.
It misses repeated sets within an edition.

2. In 2019, {one:,} acts played one festival and the highest count was {leader_degree} for {leader_names}, with every degree bin matching its null mean exactly and SD 0 because each festival has one edition per year.
This measures how widely acts were booked across sampled festivals.
It misses bookings outside the sample.

3. The mean shared lineup fraction exceeded the null mean in {share_excesses} of {n_years} years, with 2019 at {example.mean_lineup_share:.1%} and a deletion range of {deletion_range(focus_deletions.mean_lineup_share, 1, 100)}%.
It measures repeat bookings, weighting editions equally.
It misses which other festivals share those acts.

4. Edition links fell below the null mean in {edition_deficits} of {n_years} years and act links in {act_deficits} of {n_years}, with 2019 deletion ranges of {deletion_range(focus_deletions.edition_edges, 0)} and {deletion_range(focus_deletions.act_edges, 0)} links.
These counts measure how broadly bookings connect editions and acts.
They miss how often individual pairs recur, which the edge weights record.

5. Modularity exceeded the null mean in {modularity_excesses} of {n_years} years, with a 2019 deletion range of {deletion_range(focus_deletions.modularity)} and mean seed agreement of {example.mean_nmi:.3f} NMI.
They measure within-community concentration and agreement across runs.
They miss why editions cluster.

6. Country NMI exceeded the mean of {SAMPLES} country label shuffles in {country_above} of {n_years} years, with 2019 at {country_focus:.3f} and a deletion range of {deletion_range(focus_deletions.country_nmi)}.
It measures how much the edition partitions align with host countries.
It misses the separate effects of geography, calendar and genre.

7. Co-membership exceeded the curveball mean in {temporal_above} of {len(temporal_stats)} year pairs, with pooled Jaccard {pooled_scores[0]:.3f} versus {pooled_temporal["null_mean"]:.3f} and a deletion range of {deletion_range(temporal_deletions.jaccard)}.
It measures repeat co-membership among pairs together at least once, using common festivals and matching seeds.
It misses festivals observed once and leaves repeat bookings as a possible explanation.

Open problems

Check country, calendar, genre, ownership and act identity as explanations for recurrence.
"""
(OUT / "findings.md").write_text(report)
print(f"{n_years} years saved to {OUT}")
