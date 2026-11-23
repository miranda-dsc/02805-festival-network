"""musicbrainz profiles and festival bridges"""

import os
import sys
from itertools import pairwise
from pathlib import Path
from tempfile import TemporaryDirectory

import networkx as nx
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import cut_tree, linkage
from scipy.sparse import csr_matrix
from scipy.stats import rankdata
from sklearn.metrics import normalized_mutual_info_score, silhouette_score
from sklearn.preprocessing import normalize

OUT = Path(__file__).resolve().parent
PARENT = OUT.parent
sys.path.insert(0, str(PARENT.parent))
sys.dont_write_bytecode = True
from common import PROCESSED, load

os.environ.setdefault("MPLBACKEND", "Agg")
if "MPLCONFIGDIR" not in os.environ:
    cache = TemporaryDirectory(dir=OUT)
    os.environ["MPLCONFIGDIR"] = cache.name
    os.environ.setdefault("XDG_CACHE_HOME", cache.name)

import matplotlib.pyplot as plt

SEEDS = (19, 23, 31, 41, 53)
DRAWS = 499
TOP_TAGS = 3
STRICT = {"clashfinder id", "name", "alias"}
DASHES = dict.fromkeys(map(ord, "\u2010\u2011\u2012\u2013\u2014\u2015\u2212"), "-")
plt.rcParams["axes.unicode_minus"] = False


def save(rows, name):
    pd.DataFrame(rows).to_csv(OUT / f"{name}.csv", index=False, float_format="%.8g")


def edition_idf(counts):
    return 1 + np.log((1 + len(counts)) / (1 + (counts > 0).sum(axis=0)))


def top_tags(counts, partition, vocab):
    groups, ids = np.unique(partition, return_inverse=True)
    docs = np.zeros((len(groups), counts.shape[1]))
    np.add.at(docs, ids, counts)
    result = {}
    for group, row in zip(groups, normalize(docs * edition_idf(counts))):
        top = np.argsort(-row, kind="stable")[:TOP_TAGS]
        result[group] = [(vocab[i], row[i]) for i in top if row[i] > 0]
    return result


def tag_partition(counts):
    profiles = normalize(counts * edition_idf(counts))
    distances = np.clip(1 - profiles @ profiles.T, 0, 2)
    np.fill_diagonal(distances, 0)
    tree = linkage(distances[np.triu_indices(len(profiles), 1)], method="average")
    sizes = range(2, min(6, len(profiles) - 1) + 1)
    candidates = cut_tree(tree, n_clusters=list(sizes)).T
    scores = [silhouette_score(distances, labels, metric="precomputed") for labels in candidates]
    return candidates[np.argmax(scores)], max(scores)


def nmi_draws(labels, target, draws):
    a = np.eye(len(np.unique(labels)))[np.unique(labels, return_inverse=True)[1]]
    b = np.eye(len(np.unique(target)))[np.unique(target, return_inverse=True)[1]]
    marginal = a.mean(axis=0)[:, None] * b.mean(axis=0)
    joint = (a.T @ b[draws]) / len(labels)
    with np.errstate(divide="ignore", invalid="ignore"):
        mi = np.where(joint > 0, joint * np.log(joint / marginal), 0).sum(axis=(1, 2))
    ha = -sum(a.mean(axis=0) * np.log(a.mean(axis=0)))
    hb = -sum(b.mean(axis=0) * np.log(b.mean(axis=0)))
    return 2 * mi / (ha + hb) if ha + hb else np.ones(len(draws))


def compare(counts, countries, partitions, seed, include_country=True):
    tagged = counts.sum(axis=1) > 0
    labels, silhouette = tag_partition(counts[tagged])
    rng = np.random.default_rng(seed)
    order = np.arange(len(labels))
    draws = np.stack([order, *(rng.permutation(order) for _ in range(DRAWS))])
    network = np.mean([nmi_draws(labels, p[tagged], draws) for p in partitions], axis=0)
    if not include_country:
        return tagged, labels, silhouette, {"Louvain": network}
    known = pd.notna(countries[tagged]) & (countries[tagged] != "")
    country_order = np.arange(known.sum())
    country_draws = np.stack([country_order, *(rng.permutation(country_order) for _ in range(DRAWS))])
    country = nmi_draws(labels[known], countries[tagged][known], country_draws)
    return tagged, labels, silhouette, {"Louvain": network, "Country": country}


def louvain(weights):
    graph = nx.from_numpy_array(weights)
    partitions = []
    for seed in SEEDS:
        labels = np.empty(len(graph), dtype=int)
        groups = (nx.community.louvain_communities(graph, weight="weight", seed=seed)
                  if graph.number_of_edges() else [{i} for i in graph])
        for i, group in enumerate(sorted(groups, key=min)):
            labels[list(group)] = i
        partitions.append(labels)
    return np.stack(partitions)


def participation(weights, partitions):
    strength = weights.sum(axis=1)
    scores = []
    for labels in partitions:
        community_weights = weights @ (labels[:, None] == np.unique(labels))
        fractions = np.divide(community_weights, strength[:, None],
                              out=np.zeros_like(community_weights, dtype=float),
                              where=strength[:, None] > 0)
        scores.append(np.where(strength > 0, np.clip(1 - (fractions ** 2).sum(axis=1), 0, 1), 0))
    return np.stack(scores)


def summarize(values):
    return {"observed": values[0], "null_mean": values[1:].mean(), "null_sd": values[1:].std(ddof=1),
            "null_95": np.quantile(values[1:], 0.95),
            "p_upper": (1 + (values[1:] >= values[0]).sum()) / len(values)}


def bridge_check(first, second, draws=None):
    names, a, b = np.intersect1d(first[0], second[0], return_indices=True)
    x, y = rankdata(first[1][a]), rankdata(second[1][b])
    x, y = x - x.mean(), y - y.mean()
    scale = np.linalg.norm(x) * np.linalg.norm(y)
    if not scale:
        return len(names), np.full(DRAWS + 1, np.nan) if draws else np.nan
    if draws:
        rng = np.random.default_rng(draws)
        y = np.stack([y, *(rng.permutation(y) for _ in range(DRAWS))])
    return len(names), y @ x / scale


lineups, editions = load()
matches = pd.read_csv(PROCESSED / "act_matches.csv", keep_default_na=False, dtype=str)
matches = matches.loc[matches.method.isin(STRICT) & matches.mbid.ne(""), ["act_key", "mbid"]]
tags = pd.read_csv(PROCESSED / "act_tags.csv", dtype={"act_key": str, "mbid": str})
tags = tags.merge(matches.drop_duplicates(), on=["act_key", "mbid"], validate="many_to_one")
tags["weight"] = tags.genre_count.fillna(tags.tag_count)
tags = tags.loc[tags.tag.notna() & tags.weight.gt(0) & tags.act_key.isin(lineups.act_key)].copy()
tags["weight"] /= tags.groupby("act_key").weight.transform("sum")
act_keys = pd.Index(sorted(tags.act_key.unique()))
vocab = pd.Index(sorted(tags.tag.unique()))
act_tags = csr_matrix((tags.weight, (act_keys.get_indexer(tags.act_key), vocab.get_indexer(tags.tag))),
                      shape=(len(act_keys), len(vocab)))
assignments = pd.read_csv(PARENT / "communities.csv")
assert tuple(sorted(assignments.seed.unique())) == SEEDS
assert set(zip(assignments.year, assignments.edition)) == set(zip(editions.year, editions.edition))

labels_out, clusters, bridges, annual, coverage, subset_checks = [], [], [], [], [], []
deleted_bridge, bridge_by_year = {}, {}
for year, meta in editions.sort_values("edition").groupby("year"):
    ids = pd.Index(meta.edition)
    festivals = meta.festival.to_numpy()
    countries = meta.country.to_numpy()
    bookings = lineups.loc[lineups.year.eq(year)]
    codes = act_keys.get_indexer(bookings.act_key)
    tagged_bookings = codes >= 0
    incidence = csr_matrix((np.ones(tagged_bookings.sum()),
                           (ids.get_indexer(bookings.edition[tagged_bookings]), codes[tagged_bookings])),
                           shape=(len(ids), len(act_keys)))
    counts = (incidence @ act_tags).toarray()
    lineup_size = bookings.groupby("edition").size().reindex(ids, fill_value=0).to_numpy()
    tagged_count = np.asarray(incidence.sum(axis=1)).ravel().astype(int)
    np.testing.assert_allclose(counts.sum(axis=1), tagged_count)
    one_edition = bookings.act_key.map(bookings.groupby("act_key").edition.nunique()).eq(1)
    subsets = {}
    for scope, mask in (("one edition", one_edition), ("multiple editions", ~one_edition)):
        selected = tagged_bookings & mask.to_numpy()
        subset = csr_matrix(
            (np.ones(selected.sum()), (ids.get_indexer(bookings.edition[selected]), codes[selected])),
            shape=incidence.shape,
        )
        subset_counts = (subset @ act_tags).toarray()
        subsets[scope] = subset_counts
    shares = np.divide(tagged_count, lineup_size, out=np.zeros(len(ids)), where=lineup_size > 0)
    coverage.extend(zip(ids, shares))
    part = (assignments.loc[assignments.year.eq(year)]
            .pivot(index="seed", columns="edition", values="community").reindex(columns=ids).to_numpy())
    weights = np.zeros((len(ids), len(ids)), dtype=int)
    edges = pd.read_csv(PARENT / f"edition_edges_{year}.csv")
    i, j = ids.get_indexer(edges.edition_a), ids.get_indexer(edges.edition_b)
    assert (i >= 0).all() and (j >= 0).all()
    weights[i, j] = weights[j, i] = edges.weight
    _, full_codes = np.unique(bookings.act_key, return_inverse=True)
    full = csr_matrix((np.ones(len(bookings), dtype=int), (ids.get_indexer(bookings.edition), full_codes)))
    check = (full @ full.T).toarray()
    np.fill_diagonal(check, 0)
    np.testing.assert_array_equal(weights, check)
    for scope, subset_counts in subsets.items():
        included, subset_labels, _, subset_results = compare(
            subset_counts, countries, part, int(year), include_country=False
        )
        subset_checks.append({
            "year": year, "scope": scope, "editions": included.sum(),
            "cluster_sizes": " | ".join(map(str, sorted(np.unique(subset_labels, return_counts=True)[1]))),
            **summarize(subset_results["Louvain"]),
        })
    tag_mask, tags_labels, silhouette, results = compare(counts, countries, part, int(year))
    np.testing.assert_array_equal(part, louvain(weights))
    observed_nmi = np.mean([normalized_mutual_info_score(tags_labels, p[tag_mask]) for p in part])
    np.testing.assert_allclose(results["Louvain"][0], observed_nmi)
    clusters.extend({"year": year, "edition": edition, "festival": festival,
                     "tagged_acts": n, "lineup_size": size, "tag_cluster": label}
                    for edition, festival, n, size, label in zip(
                        ids, festivals, tagged_count, lineup_size,
                        pd.Series(tags_labels, index=ids[tag_mask]).reindex(ids)))
    community_tags = [top_tags(counts, partition, vocab) for partition in part]
    scores = participation(weights, part)
    avg = scores.mean(axis=0)
    ranks = rankdata(avg) / len(ids)
    bridge_by_year[year] = (festivals, avg)
    deleted_alignment, deleted_scores, tag_checks = [], [], {}
    for dropped, festival in enumerate(festivals):
        keep = np.arange(len(ids)) != dropped
        subweights = weights[np.ix_(keep, keep)]
        subpart = louvain(subweights)
        *_, comparisons = compare(counts[keep], countries[keep], subpart, int(year) + dropped + 1)
        deleted_alignment.append({key: value[0] - value[1:].mean() for key, value in comparisons.items()})
        subavg = participation(subweights, subpart).mean(axis=0)
        deleted_bridge[year, festival] = (festivals[keep], subavg)
        deleted_scores.append(pd.Series(rankdata(subavg) / keep.sum(), index=ids[keep]))
        for seed, partition, original in zip(SEEDS, part, community_tags):
            for group, ranked_tags in top_tags(counts[keep], partition[keep], vocab).items():
                a = {tag for tag, _ in original[group]}
                b = {tag for tag, _ in ranked_tags}
                if a | b:
                    tag_checks.setdefault((seed, group), []).append(len(a & b) / len(a | b))

    for seed, partition, ranked in zip(SEEDS, part, community_tags):
        for group, terms in ranked.items():
            stability = tag_checks.get((seed, group), [np.nan])
            members = partition == group
            labels_out.append({
                "year": year, "seed": seed, "community": group,
                "festivals": " | ".join(sorted(festivals[members])),
                "tag_coverage": tagged_count[members].sum() / lineup_size[members].sum(),
                "tags": " | ".join(tag.translate(DASHES) for tag, _ in terms),
                "tfidf": " | ".join(f"{weight:.4f}" for _, weight in terms),
                "tag_deletion_min_jaccard": np.min(stability),
            })
    deleted_ranks = pd.concat(deleted_scores, axis=1).reindex(ids)
    for k, (edition, festival) in enumerate(zip(ids, festivals)):
        bridges.append({"year": year, "edition": edition, "festival": festival,
                        "participation": avg[k], "seed_min": scores[:, k].min(),
                        "seed_max": scores[:, k].max(), "percentile": ranks[k],
                        "deletion_percentile_min": deleted_ranks.iloc[k].min(),
                        "deletion_percentile_max": deleted_ranks.iloc[k].max()})
    sizes = sorted(np.unique(tags_labels, return_counts=True)[1])
    for target, values in results.items():
        sensitivity = [row[target] for row in deleted_alignment]
        annual.append({"year": year, "target": target, "editions": tag_mask.sum(),
                       "tag_clusters": len(sizes), "cluster_sizes": " | ".join(map(str, sizes)),
                       "silhouette": silhouette, "deletions_above_null": sum(x > 0 for x in sensitivity),
                       "deletions_total": len(sensitivity),
                       **summarize(values), "deletion_min_excess": min(sensitivity),
                       "deletion_max_excess": max(sensitivity)})
    print(f"{year}: {tag_mask.sum()} tagged editions, {len(set(tags_labels))} tag clusters", flush=True)

stability = []
for first, second in pairwise(bridge_by_year):
    common, values = bridge_check(bridge_by_year[first], bridge_by_year[second], int(second))
    festivals = np.union1d(bridge_by_year[first][0], bridge_by_year[second][0])
    sensitivity = [bridge_check(deleted_bridge.get((first, f), bridge_by_year[first]),
                                deleted_bridge.get((second, f), bridge_by_year[second]))[1]
                   for f in festivals]
    stability.append({"year_a": first, "year_b": second, "festivals": common, **summarize(values),
                      "deletion_min": np.nanmin(sensitivity), "deletion_max": np.nanmax(sensitivity)})

annual = pd.DataFrame(annual)
stability = pd.DataFrame(stability)
labels_out = pd.DataFrame(labels_out)
bridges = pd.DataFrame(bridges)
leaderboard = (bridges.assign(top_quartile=bridges.percentile.gt(0.75))
               .groupby("festival").agg(years=("year", "size"), top_years=("top_quartile", "sum"),
                                        mean_percentile=("percentile", "mean")).reset_index())
leaderboard = leaderboard.sort_values(["top_years", "mean_percentile", "festival"],
                                      ascending=[False, False, True])
save(labels_out, "community_tags")
save(clusters, "tag_clusters")
save(annual, "tag_agreement")
subsets = pd.DataFrame(subset_checks)
save(subsets, "tag_agreement_by_act_frequency")
save(bridges, "bridge_editions")
save(leaderboard, "bridge_festivals")
save(stability, "bridge_stability")

fig, axes = plt.subplots(1, 2, figsize=(10.8, 4), layout="constrained")
ax = axes[0]
for (target, frame), offset, color in zip(annual.groupby("target"), (-0.15, 0.15), ("#a9522b", "#2b6f86")):
    x = frame.year + offset
    ax.vlines(x, frame.deletion_min_excess, frame.deletion_max_excess, color=color, alpha=0.5)
    ax.scatter(x, frame.observed - frame.null_mean, label=target, color=color, s=22)
ax.axhline(0, color="0.6", lw=0.8)
ax.set(xlabel="Year", ylabel="NMI minus shuffle mean", title="Tag agreement", xticks=annual.year.unique())
ax.legend(frameon=False)
ax = axes[1]
x = np.arange(len(stability))
ax.vlines(x, stability.deletion_min, stability.deletion_max, color="#2b6f86", alpha=0.5)
ax.scatter(x, stability.observed, color="#2b6f86", s=22, label="Observed")
ax.scatter(x, stability.null_95, marker="_", color="#a9522b", label="Shuffle 95th percentile")
ax.axhline(0, color="0.6", lw=0.8)
ax.set(xlabel="Retained year pair", ylabel="Spearman rank correlation", title="Bridge stability",
       xticks=x, xticklabels=[f"{a}/{str(b)[-2:]}" for a, b in zip(stability.year_a, stability.year_b)])
ax.legend(frameon=False)
for ax in axes:
    ax.tick_params(axis="x", rotation=40)
fig.savefig(OUT / "text_and_bridges.png", dpi=180)
plt.close(fig)

coverage = pd.Series(dict(coverage))
base = labels_out.loc[labels_out.seed.eq(SEEDS[0])]
example = base.loc[base.year.eq(2019)].sort_values("tag_coverage", ascending=False).iloc[0]
country = annual.loc[annual.target.eq("Country")]
network = annual.loc[annual.target.eq("Louvain")]
top = leaderboard.iloc[0]
top_stable = bridges.loc[bridges.festival.eq(top.festival), "deletion_percentile_min"].gt(0.75).sum()


single = subsets.query("scope == 'one edition'")
multiple = subsets.query("scope == 'multiple editions'")
stable_years = network.loc[network.deletions_above_null.eq(network.deletions_total), "year"]
stable_labels = ", ".join(map(str, stable_years))
report = f"""We used positive MusicBrainz tag weights from strict id, name and alias matches, normalized per act. Median edition coverage was {coverage.median():.0%} across {len(coverage)} editions. We excluded 2020 and 2021.

1. In 2019, Louvain community {example.community} at seed {example.seed} had top tags {example.tags.replace(" | ", ", ")}. The median community's worst deletion gave top-three Jaccard {base.tag_deletion_min_jaccard.median():.2f}, equivalent to one swap when both lists have three tags. This captures leading tags after weighting by how often they occur across editions. It misses untagged acts and uses current tags for past editions.

2. Tag clusters agreed with Louvain at permutation p below 0.05 in {(network.p_upper < 0.05).sum()} of {len(network)} years, versus {(single.p_upper < 0.05).sum()} of {len(single)} using only acts booked once that year and {(multiple.p_upper < 0.05).sum()} of {len(multiple)} using only repeat acts that also create network edges. Agreement stayed above the shuffle mean after every deletion in {len(stable_years)} of {len(network)} years ({stable_labels}). Country agreement was below the shuffle mean in {(country.observed < country.null_mean).sum()} of {len(country)} years and reached p below 0.05 in {(country.p_upper < 0.05).sum()}. This captures alignment with booking communities even when profile acts create no network edges. It misses untagged acts, and silhouettes of {network.silhouette.min():.2f} to {network.silhouette.max():.2f} and uneven cluster sizes limit interpretation.

3. Bridge rank agreement reached p below 0.05 in {(stability.p_upper < 0.05).sum()} of {len(stability)} successive retained year pairs. {top.festival.title().replace(' For ', ' for ')} was top quartile in {top.top_years} of {top.years} observed years and stayed there under every deletion of another festival in {top_stable} of {top.years} years. This captures how consistently festivals spread booking links across communities. It misses the acts behind those links and is sensitive to festival deletion, with {int(stability.iloc[0].festivals)} common festivals in the first comparison. The 2022 to 2023 rank correlation was {stability.loc[stability.year_a.eq(2022), 'observed'].iloc[0]:.2f}.

We chose the tag cluster count by silhouette from two to six cosine clusters and used {DRAWS} within-year label permutations for each comparison. For bridge stability, we permuted festival identities in the second year within the common festival set. Vertical lines in the figure show festival deletion ranges.
"""
(OUT / "findings.md").write_text(report)
print(f"{len(editions)} editions, {len(act_keys)} tagged acts, {len(stability)} bridge comparisons")
