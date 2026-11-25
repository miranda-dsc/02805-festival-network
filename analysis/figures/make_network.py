"""draw the 2019 edition projection above the curveball mean"""

import sys
from itertools import combinations
from pathlib import Path

import matplotlib as mpl
import networkx as nx
import numpy as np
import pandas as pd
from matplotlib import font_manager, patheffects
from matplotlib.lines import Line2D

mpl.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parent
ANALYSIS = OUT.parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(ANALYSIS))
from common import load, same_brand

YEAR = 2019
WIDTH = 8.7 / 2.54
SEED = 2805
COLORS = {
    "GB": "#0072b2",
    "BE": "#d55e00",
    "NL": "#009e73",
    "DE": "#cc79a7",
    "ES": "#e8bc54",
    "Other": "#999999",
}
LABELS = {
    "g2019": ("Glastonbury", (-4, 17)),
    "tge2019": ("The Great Escape", (6, 12)),
    "read2019": ("Reading", (-18, -15)),
    "mcf19": ("Mad Cool", (22, 20)),
    "tml2019w1": ("Tomorrowland", (7, 3)),
    "ml2019": ("Mysteryland", (7, -2)),
}
SCALE = 0.12
SIZE_KEY = [100, 500, 1500]


def edition_graph():
    lineups, editions = load()
    sites = editions.loc[editions["year"].eq(YEAR)].sort_values("edition").set_index("edition")
    acts = lineups.loc[lineups["year"].eq(YEAR)].groupby("edition")["act_key"].agg(set)
    pairs = pd.read_csv(ANALYSIS / "watts" / "pairs.csv",
                        usecols=["year", "edition_a", "edition_b", "shared_acts", "null_mean"])
    pairs = pairs.loc[pairs["year"].eq(YEAR)]
    graph = nx.Graph()
    for edition, row in sites.iterrows():
        country = row.country if row.country in COLORS else "Other"
        graph.add_node(edition, size=len(acts[edition]), country=country)

    expectations = {}
    for row in pairs.itertuples(index=False):
        key = tuple(sorted((row.edition_a, row.edition_b)))
        if key in expectations:
            raise ValueError(f"duplicate saved pair {key}")
        expectations[key] = (row.shared_acts, row.null_mean)

    for a, b in combinations(sites.index, 2):
        if same_brand(sites.at[a, "festival"], sites.at[b, "festival"]):
            continue
        shared, expected = expectations[a, b]
        if shared != len(acts[a] & acts[b]) or not np.isfinite(expected):
            raise ValueError(f"saved pair results disagree with loaded lineups for {a}, {b}")
        excess = shared - expected
        if excess > 0:
            graph.add_edge(a, b, excess=excess)
    return graph


def main():
    font_manager.findfont("Georgia", fallback_to_default=False)
    mpl.rcParams.update({
        "font.family": "Georgia",
        "font.size": 8,
        "axes.unicode_minus": False,
        "pdf.fonttype": 42,
    })
    graph = edition_graph()
    pos = nx.spring_layout(graph, weight=None, seed=SEED, iterations=500, k=0.55)
    edges = sorted(graph.edges(data="excess"), key=lambda edge: edge[2])
    fig, ax = plt.subplots(figsize=(WIDTH, 2.55))
    fig.subplots_adjust(left=0.0, right=0.78, top=1.0, bottom=0.0)
    nx.draw_networkx_edges(graph, pos, ax=ax, edgelist=[(a, b) for a, b, _ in edges],
                           width=[0.08 + 0.05 * excess for _, _, excess in edges],
                           edge_color="#6b6b6b", alpha=0.35)
    nx.draw_networkx_nodes(graph, pos, ax=ax,
                           node_size=[SCALE * data["size"] for _, data in graph.nodes(data=True)],
                           node_color=[COLORS[data["country"]] for _, data in graph.nodes(data=True)],
                           edgecolors="white", linewidths=0.5)
    for edition, (label, offset) in LABELS.items():
        ax.annotate(label, pos[edition], xytext=offset, textcoords="offset points",
                    fontsize=6.5, va="center", ha="left" if offset[0] > 0 else "right",
                    arrowprops=dict(arrowstyle="-", color="#555555", lw=0.4, shrinkA=0, shrinkB=2),
                    path_effects=[patheffects.withStroke(linewidth=2, foreground="white")])
    countries = {data["country"] for _, data in graph.nodes(data=True)}
    key = [Line2D([], [], marker="o", linestyle="none", markerfacecolor=color,
                  markeredgecolor="white", markersize=5.5, label=country)
           for country, color in COLORS.items() if country in countries]
    sizes = [Line2D([], [], marker="o", linestyle="none", markerfacecolor="none",
                    markeredgecolor="#6b6b6b", markeredgewidth=0.5,
                    markersize=(SCALE * acts) ** 0.5, label=f"{acts:,} acts")
             for acts in SIZE_KEY]
    first = fig.legend(handles=key, loc="upper left", bbox_to_anchor=(0.77, 0.97),
                       frameon=False, fontsize=6.5, handletextpad=0.3, labelspacing=0.5)
    fig.legend(handles=sizes, loc="lower left", bbox_to_anchor=(0.77, 0.03),
               frameon=False, fontsize=6.5, handletextpad=0.6, labelspacing=1.1)
    ax.set_aspect("equal")
    ax.margins(0.04)
    ax.set_axis_off()
    for suffix in ("pdf", "png"):
        fig.savefig(OUT / f"fig2.{suffix}", dpi=600)
    print(f"{YEAR}: {graph.number_of_nodes()} editions, {graph.number_of_edges()} positive-excess pairs")


if __name__ == "__main__":
    main()
