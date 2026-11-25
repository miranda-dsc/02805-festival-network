"""draw paper figures from saved analysis results"""

from pathlib import Path

import matplotlib as mpl
import pandas as pd
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

mpl.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parent
ANALYSIS = OUT.parent
REACH = ANALYSIS / "watts" / "reach"
WIKITEXT = ANALYSIS / "newman" / "wikitext"
COMPARISON = ANALYSIS / "erdos" / "reconcile" / "comparison.csv"
WIDTH = 8.7 / 2.54
FULL = 17.8 / 2.54
TIERS = ["0 foreign", "1 foreign", "2 to 4 foreign", "5 to 9 foreign", "10 or more foreign"]
TIER_LABELS = ["0", "1", "2 to 4", "5 to 9", "10+"]
OBSERVED = "#174859"
SECOND = "#9c543d"
NULL_BAND = "#dcdcdc"
WHISKER = "#343434"
REFERENCE = "#a3aaad"


def style_axes(ax, title):
    ax.set_title(title, loc="left", pad=4)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["bottom", "left"]].set_color(REFERENCE)
    ax.tick_params(length=2.5, color=REFERENCE)


def save(fig, name):
    for suffix in ("pdf", "png"):
        fig.savefig(OUT / f"{name}.{suffix}", dpi=600)
    plt.close(fig)
    print(f"wrote {name}.pdf and {name}.png")


def draw_points(ax, x, observed, null_low, null_high, deletion_low=None, deletion_high=None):
    ax.bar(x, null_high - null_low, bottom=null_low, width=0.62, color=NULL_BAND, zorder=0)
    if deletion_low is not None:
        ax.errorbar(x, (deletion_low + deletion_high) / 2, yerr=(deletion_high - deletion_low) / 2,
                    fmt="none", ecolor=WHISKER, elinewidth=0.7, capsize=1.8, capthick=0.7, zorder=2)
    ax.scatter(x, observed, color=OBSERVED, s=16, edgecolors="white", linewidths=0.5, zorder=3)


def plot_excess(ax, rows, labels, title, xlabel):
    style_axes(ax, title)
    x = range(len(rows))
    ax.axhline(0, color=REFERENCE, linewidth=0.5, zorder=1)
    draw_points(ax, x, rows["r_excess"], rows["r_null_low"], rows["r_null_high"],
                rows["r_deletion_min"], rows["r_deletion_max"])
    ax.set_xticks(x, labels)
    ax.set(xlabel=xlabel, xlim=(-0.6, len(rows) - 0.4), ylim=(-0.04, 0.37),
           yticks=[0, 0.1, 0.2, 0.3])


def plot_national(ax, share):
    style_axes(ax, "C   National booking concentration")
    x = range(len(share))
    draw_points(ax, x, share["one_country_distinct"], share["one_country_distinct_null_low"],
                share["one_country_distinct_null_high"])
    ax.set_xticks(x, TIER_LABELS)
    ax.set(xlabel="Foreign Wikipedia editions", ylabel="Share of festivals in top country",
           xlim=(-0.6, len(share) - 0.4), ylim=(0.55, 0.85), yticks=[0.6, 0.7, 0.8])
    ax.yaxis.set_major_formatter(mpl.ticker.PercentFormatter(xmax=1, decimals=0))


def main():
    font_manager.findfont("Georgia", fallback_to_default=False)
    mpl.rcParams.update({
        "font.family": "Georgia",
        "font.size": 7.5,
        "axes.titlesize": 8,
        "axes.labelsize": 7.5,
        "axes.linewidth": 0.6,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "axes.unicode_minus": False,
        "legend.fontsize": 7,
        "legend.frameon": False,
        "pdf.fonttype": 42,
    })

    comparison = pd.read_csv(COMPARISON).set_index(["scheme", "reach"])
    wiki = comparison.loc["foreign_wikipedia"].loc[TIERS]
    count = comparison.loc["festival_count"].dropna(subset=["r_excess"])
    count_labels = (count.index.str.replace(r" festivals?$", "", regex=True)
                    .str.replace("-", " to ").str.replace("+", "+", regex=False))
    share = pd.read_csv(REACH / "national_share.csv")
    share = share.loc[share["control"].eq("2 or more festivals")].set_index("tier").loc[TIERS]

    fig = plt.figure(figsize=(FULL, 2.25), layout="constrained")
    grid = fig.add_gridspec(1, 3, width_ratios=[5, 3.4, 5], wspace=0.06)
    ax = fig.add_subplot(grid[0])
    by_count = fig.add_subplot(grid[1], sharey=ax)
    national = fig.add_subplot(grid[2])
    plot_excess(ax, wiki, TIER_LABELS, "A   By Wikipedia reach", "Foreign Wikipedia editions")
    plot_excess(by_count, count, count_labels, "B   By festival count", "Distinct festivals")
    ax.set_ylabel("Country assortativity above null")
    by_count.tick_params(axis="y", labelleft=False)
    plot_national(national, share)
    key = [
        Line2D([], [], marker="o", linestyle="none", color=OBSERVED, markeredgecolor="white",
               markersize=5, label="Observed"),
        Line2D([], [], marker="|", linestyle="none", color=WHISKER, markersize=7,
               label="Range after dropping one festival"),
        Patch(color=NULL_BAND, label="Central 95% of null"),
    ]
    fig.legend(handles=key, loc="outside upper center", ncols=3, columnspacing=1.6,
               handlelength=1.2, handletextpad=0.5)
    save(fig, "fig1")

    sound = pd.read_csv(WIKITEXT / "sound_effect.csv")
    years = ["all", *sorted(sound.loc[sound["year"].ne("all"), "year"].unique())]
    y = pd.Series(range(len(years)))
    fig, ax = plt.subplots(figsize=(WIDTH, 2.7), layout="constrained")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color(REFERENCE)
    ax.tick_params(length=2.5, color=REFERENCE)
    ax.tick_params(axis="y", length=0)
    ax.axvline(0, color=REFERENCE, linewidth=0.5, zorder=0)
    ax.axhline(0.5, color=REFERENCE, linewidth=0.4, linestyle=(0, (2, 2)), zorder=0)
    for measure, label, marker, color, offset in [
        ("genre_similarity_strict", "MusicBrainz tags", "s", SECOND, -0.17),
        ("wiki_cosine", "Wikipedia intros", "o", OBSERVED, 0.17),
    ]:
        rows = sound.loc[sound["measure"].eq(measure)].set_index("year").loc[years]
        ax.hlines(y + offset, rows["deletion_min"], rows["deletion_max"],
                  color=color, linewidth=0.9, alpha=0.55)
        ax.scatter(rows["acts_per_0_10"], y + offset, color=color, marker=marker,
                   s=11, label=label, zorder=3, edgecolors="white", linewidths=0.4)
    ax.set_yticks(y, ["Pooled", *years[1:]])
    ax.set(xlabel="Excess shared acts per 0.10 cosine", xlim=(-0.2, 3.3),
           ylim=(len(years) - 0.5, -0.6), xticks=[0, 1, 2, 3])
    fig.legend(loc="outside upper center", ncols=2, columnspacing=1.6, handletextpad=0.3)
    save(fig, "fig3")


if __name__ == "__main__":
    main()
