"""future work sketch: disparity filter backbone of the festival network, sized by betweenness"""

from pathlib import Path

import matplotlib as mpl
import networkx as nx
import pandas as pd
from matplotlib import font_manager, patheffects
from matplotlib.lines import Line2D

mpl.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parent
ANALYSIS = OUT.parent
WIDTH = 8.7 / 2.54
SEED = 2805
ALPHA = 0.05
COLORS = {
    "GB": "#0072b2",
    "BE": "#d55e00",
    "NL": "#cc79a7",
    "DE": "#009e73",
    "ES": "#e8bc54",
    "Other": "#bbbbbb",
}
SCALE = 600
LABELS = {
    "reading": ("Reading", (14, -30)),
    "the great escape": ("The Great Escape", (30, -25)),
    "glastonbury": ("Glastonbury", (20, 8)),
    "bestival": ("Bestival", (15, -25)),
}
GROUPS = {
    "slam dunk": "Slam Dunk, Pohoda\nand two more",
    "les ardentes": "Les Ardentes and two\nFrench festivals",
    "mysteryland": "Tomorrowland,\nMysteryland",
    "download": "Download,\nGraspop",
}


def festival_graph(pairs=None):
    """festivals joined by their excess shared acts summed over years, positive sums only"""
    if pairs is None:
        pairs = pd.read_csv(ANALYSIS / "watts" / "pairs.csv")
    pairs = pairs.loc[~pairs["same_brand"]]
    countries = dict(zip(pairs["festival_a"], pairs["country_a"]))
    countries.update(zip(pairs["festival_b"], pairs["country_b"]))
    # pair order flips between years, so sort before pooling
    ends = pd.DataFrame(sorted(pair) for pair in zip(pairs["festival_a"], pairs["festival_b"]))
    pooled = pairs["excess"].groupby([ends[0].values, ends[1].values]).sum()
    graph = nx.Graph()
    for festival, country in countries.items():
        graph.add_node(festival, country=country, group=country if country in COLORS else "Other")
    for (a, b), excess in pooled.items():
        if excess > 0:
            graph.add_edge(a, b, weight=excess)
    return graph


def disparity_backbone(graph, alpha=ALPHA):
    """keep an edge if it is significant for either end (serrano et al. 2009);
    a leaf's edge is judged at its other end, and a pair of leaves is kept"""
    keep = set()
    for node in graph:
        k = graph.degree(node)
        if k < 2:
            keep.update(tuple(sorted((node, other))) for other in graph[node]
                        if graph.degree(other) == 1)
            continue
        strength = graph.degree(node, weight="weight")
        for other, data in graph[node].items():
            if (1 - data["weight"] / strength) ** (k - 1) < alpha:
                keep.add(tuple(sorted((node, other))))
    backbone = nx.Graph()
    backbone.add_nodes_from(graph.nodes(data=True))
    backbone.add_edges_from((a, b, graph[a][b]) for a, b in keep)
    return backbone


def layout(graph):
    """giant component by kamada kawai, smaller groups stacked on the right"""
    parts = sorted(nx.connected_components(graph), key=len, reverse=True)
    pos = nx.kamada_kawai_layout(graph.subgraph(parts[0]), weight=None)
    for i, part in enumerate(parts[1:]):
        sub = nx.circular_layout(graph.subgraph(part), scale=0.09)
        for node, (x, y) in sub.items():
            pos[node] = (x + 1.1, y + 0.8 - 0.5 * i)
    return pos


def main():
    font_manager.findfont("Georgia", fallback_to_default=False)
    mpl.rcParams.update({
        "font.family": "Georgia",
        "font.size": 8,
        "axes.unicode_minus": False,
        "pdf.fonttype": 42,
    })
    full = festival_graph()
    graph = disparity_backbone(full)
    isolates = list(nx.isolates(graph))
    graph.remove_nodes_from(isolates)
    for a, b, data in graph.edges(data=True):
        data["distance"] = 1 / data["weight"]
    between = nx.betweenness_centrality(graph, weight="distance")
    pos = layout(graph)

    fig, ax = plt.subplots(figsize=(WIDTH, 2.6))
    fig.subplots_adjust(left=0.0, right=1.0, top=1.0, bottom=0.1)
    nx.draw_networkx_edges(graph, pos, ax=ax, width=0.7, edge_color="#6b6b6b", alpha=0.5)
    nx.draw_networkx_nodes(graph, pos, ax=ax,
                           node_size=[12 + SCALE * between[node] for node in graph],
                           node_color=[COLORS[data["group"]] for _, data in graph.nodes(data=True)],
                           edgecolors="white", linewidths=0.5)
    for festival, (label, offset) in LABELS.items():
        ax.annotate(label, pos[festival], xytext=offset, textcoords="offset points", fontsize=6,
                    va="center", ha="left" if offset[0] > 0 else "right",
                    arrowprops=dict(arrowstyle="-", color="#555555", lw=0.4, shrinkA=0, shrinkB=2),
                    path_effects=[patheffects.withStroke(linewidth=2, foreground="white")])
    for part in nx.connected_components(graph):
        member = next((festival for festival in GROUPS if festival in part), None)
        if member:
            x = max(pos[node][0] for node in part) + 0.07
            y = sum(pos[node][1] for node in part) / len(part)
            ax.text(x, y, GROUPS[member], fontsize=6, va="center", linespacing=1.1)
    countries = {data["group"] for _, data in graph.nodes(data=True)}
    key = [Line2D([], [], marker="o", linestyle="none", markerfacecolor=color,
                  markeredgecolor="white", markersize=5.5, label=country)
           for country, color in COLORS.items() if country in countries]
    fig.legend(handles=key, loc="lower center", ncols=len(key), frameon=False, fontsize=6.5,
               handletextpad=0.2, columnspacing=1.0)
    ax.margins(0.06)
    ax.set_xlim(right=max(x for x, _ in pos.values()) + 0.85)
    ax.set_axis_off()
    for suffix in ("pdf", "png"):
        fig.savefig(OUT / f"fig4.{suffix}", dpi=600)

    cross = sum(graph.nodes[a]["country"] != graph.nodes[b]["country"] for a, b in graph.edges)
    print(f"{full.number_of_edges()} positive pooled pairs, {graph.number_of_edges()} in the backbone "
          f"({cross} cross country), {nx.number_connected_components(graph)} components, "
          f"{len(isolates)} festivals left without an edge")
    for festival in sorted(between, key=between.get, reverse=True)[:4]:
        print(f"  {festival} ({graph.nodes[festival]['country']}): betweenness {between[festival]:.2f}")


if __name__ == "__main__":
    main()
