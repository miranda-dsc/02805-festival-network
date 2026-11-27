"""checks on the disparity filter backbone of the festival network"""

import sys
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
from sklearn.metrics import normalized_mutual_info_score

OUT = Path(__file__).resolve().parent
ANALYSIS = OUT.parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(ANALYSIS / "figures"))
from make_backbone import disparity_backbone, festival_graph

SEED = 28305
DRAWS = 1999
ALPHAS = (0.01, 0.05, 0.1)
LOUVAIN_SEEDS = range(20)


def same_country_share(graph, country):
    edges = list(graph.edges)
    return np.mean([country[a] == country[b] for a, b in edges]) if edges else np.nan


def shuffle(nodes, labels, degree, rng):
    """country labels shuffled among festivals with the same backbone degree"""
    out = labels.copy()
    for k in np.unique(degree):
        idx = np.flatnonzero(degree == k)
        out[idx] = rng.permutation(labels[idx])
    return dict(zip(nodes, out))


def label_null(graph, country, rng, by_degree):
    """same country share and country assortativity with country labels shuffled across festivals"""
    nodes = list(graph)
    labels = np.array([country[node] for node in nodes])
    degree = np.array([graph.degree(node) for node in nodes]) if by_degree else np.zeros(len(nodes))
    shares, rs = [], []
    for _ in range(DRAWS):
        shuffled = shuffle(nodes, labels, degree, rng)
        shares.append(same_country_share(graph, shuffled))
        nx.set_node_attributes(graph, shuffled, "shuffled")
        rs.append(nx.attribute_assortativity_coefficient(graph, "shuffled"))
    return np.array(shares), np.array(rs)


def describe(graph, country, rng, **labels):
    graph = graph.copy()
    graph.remove_nodes_from(list(nx.isolates(graph)))
    share = same_country_share(graph, country)
    r = nx.attribute_assortativity_coefficient(graph, "country")
    shares, rs = label_null(graph, country, rng, by_degree=False)
    by_degree, _ = label_null(graph, country, rng, by_degree=True)
    return dict(**labels, festivals=graph.number_of_nodes(), edges=graph.number_of_edges(),
                same_country=share, null_mean=shares.mean(),
                null_low=np.quantile(shares, 0.025), null_high=np.quantile(shares, 0.975),
                p=((shares >= share).sum() + 1) / (DRAWS + 1),
                degree_null_mean=by_degree.mean(), degree_null_high=np.quantile(by_degree, 0.975),
                degree_p=((by_degree >= share).sum() + 1) / (DRAWS + 1),
                r=r, r_null_mean=np.nanmean(rs), r_null_low=np.nanquantile(rs, 0.025),
                r_null_high=np.nanquantile(rs, 0.975))


def communities(graph, country, rng):
    """louvain on the backbone, compared with country by nmi against shuffled labels"""
    graph = graph.copy()
    graph.remove_nodes_from(list(nx.isolates(graph)))
    nodes = list(graph)
    truth = [country[node] for node in nodes]
    rows, best = [], None
    for seed in LOUVAIN_SEEDS:
        parts = nx.community.louvain_communities(graph, weight="weight", seed=seed)
        found = {node: k for k, part in enumerate(parts) for node in part}
        labels = [found[node] for node in nodes]
        nmi = normalized_mutual_info_score(truth, labels)
        null = [normalized_mutual_info_score(rng.permutation(truth), labels) for _ in range(DRAWS)]
        q = nx.community.modularity(graph, parts, weight="weight")
        if best is None or q > best[0]:
            best = q, parts
        rows.append(dict(seed=seed, communities=len(parts), modularity=q,
                         nmi=nmi, nmi_null_mean=np.mean(null),
                         nmi_null_high=np.quantile(null, 0.975),
                         p=((np.array(null) >= nmi).sum() + 1) / (DRAWS + 1)))
    return pd.DataFrame(rows), best[1]


def main():
    rng = np.random.default_rng(SEED)
    pairs = pd.read_csv(ANALYSIS / "watts" / "pairs.csv")
    full = festival_graph(pairs)
    country = nx.get_node_attributes(full, "country")
    print(f"{full.number_of_nodes()} festivals, {full.number_of_edges()} positive pooled pairs")

    rows = [describe(full, country, rng, check="all positive pairs", alpha=np.nan, year="pooled")]
    for alpha in ALPHAS:
        rows.append(describe(disparity_backbone(full, alpha), country, rng,
                             check="backbone", alpha=alpha, year="pooled"))
    for year, group in pairs.groupby("year"):
        rows.append(describe(disparity_backbone(festival_graph(group)), country, rng,
                             check="backbone by year", alpha=0.05, year=str(year)))
    backbone = disparity_backbone(full)
    gb = [festival for festival in full if country[festival] == "GB"]
    without = full.copy()
    without.remove_nodes_from(gb)
    rows.append(describe(disparity_backbone(without), country, rng,
                         check="backbone without GB", alpha=0.05, year="pooled"))
    for festival in sorted(full):
        kept = backbone.copy()
        kept.remove_node(festival)
        rows.append(describe(kept, country, rng, check="drop one festival", alpha=0.05, year=festival))
    checks = pd.DataFrame(rows)
    checks.to_csv(OUT / "checks.csv", index=False, float_format="%.4g")

    louvain, parts = communities(backbone, country, rng)
    louvain.to_csv(OUT / "louvain.csv", index=False, float_format="%.4g")
    groups = pd.DataFrame([dict(community=k + 1, festivals=", ".join(sorted(part)),
                                countries=", ".join(sorted({country[f] for f in part})))
                           for k, part in enumerate(sorted(parts, key=len, reverse=True))])
    groups.to_csv(OUT / "communities.csv", index=False)

    between = nx.betweenness_centrality(
        nx.Graph((a, b, {"distance": 1 / w}) for a, b, w in backbone.edges(data="weight")),
        weight="distance")
    pd.Series(between, name="betweenness").sort_values(ascending=False).rename_axis(
        "festival").to_csv(OUT / "betweenness.csv", float_format="%.4g")

    pooled = checks.loc[checks["check"].ne("drop one festival") & checks["year"].eq("pooled")]
    yearly = checks.loc[checks["check"].eq("backbone by year")]
    deleted = checks.loc[checks["check"].eq("drop one festival")]
    print(pooled.round(3).to_string(index=False))
    print(f"by year: same country above the null mean in "
          f"{(yearly.same_country > yearly.null_mean).sum()} of {len(yearly)}, "
          f"above the 97.5% edge in {(yearly.same_country > yearly.null_high).sum()}, "
          f"shares {yearly.same_country.min():.2f} to {yearly.same_country.max():.2f}")
    print(f"drop one festival: share {deleted.same_country.min():.2f} to {deleted.same_country.max():.2f}, "
          f"p at most {deleted.p.max():.4f}")
    print(louvain.groupby(["modularity", "nmi"]).agg(seeds=("seed", "size"), p=("p", "mean")).round(4).to_string())
    print(groups.to_string(index=False))


if __name__ == "__main__":
    main()
