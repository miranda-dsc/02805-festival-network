"""draw paper figures from saved analysis results"""

from pathlib import Path

import matplotlib as mpl
import pandas as pd
from matplotlib import font_manager

mpl.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parent
ANALYSIS = OUT.parent
REACH = ANALYSIS / "watts" / "reach"
WIKITEXT = ANALYSIS / "newman" / "wikitext"
COMPARISON = ANALYSIS / "erdos" / "reconcile" / "comparison.csv"
WIDTH = 8.7 / 2.54
TIERS = ["0 foreign", "1 foreign", "2 to 4 foreign", "5 to 9 foreign", "10 or more foreign"]
TIER_LABELS = ["0", "1", "2 to 4", "5 to 9", "10 or more"]
OBSERVED = "#174859"
NULL = "#839da3"
NULL_BAND = "#d5d5d5"
WHISKER = "#343434"
REFERENCE = "#a3aaad"


def style_axes(ax, title):
    ax.set_title(title, loc="left", pad=6)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["bottom", "left"]].set_color(REFERENCE)
    ax.tick_params(length=3, color=REFERENCE)


def save(fig, name):
    for suffix in ("pdf", "png"):
        fig.savefig(OUT / f"{name}.{suffix}", dpi=600)
    plt.close(fig)
    print(f"wrote {name}.pdf and {name}.png")


def plot_reach(ax, results, observed, low, high, ylabel):
    x = range(len(TIERS))
    marks = ax.scatter(x, results[observed], color=OBSERVED, s=22,
                       edgecolors="white", linewidths=0.65, zorder=3)
    bands = ax.vlines(x, results[low], results[high], color=NULL, linewidth=8)
    ax.set_xticks(x, TIER_LABELS)
    ax.set(ylabel=ylabel, xlim=(-0.42, 4.42))
    return marks, bands


def plot_excess(ax, rows, labels, title, xlabel):
    style_axes(ax, title)
    x = range(len(rows))
    low, high = rows["r_null_low"], rows["r_null_high"]
    band = ax.bar(x, high - low, bottom=low, width=0.9, color=NULL_BAND, zorder=0)
    ax.axhline(0, color=REFERENCE, linewidth=0.6, zorder=0)
    low, high = rows["r_deletion_min"], rows["r_deletion_max"]
    whiskers = ax.errorbar(x, (low + high) / 2, yerr=(high - low) / 2, fmt="none",
                           ecolor=WHISKER, elinewidth=0.7, capsize=2, capthick=0.7)
    ax.scatter(x, rows["r_excess"], color=OBSERVED, s=22,
               edgecolors="white", linewidths=0.65, zorder=3)
    ax.set_xticks(x, labels, rotation=35, ha="right", rotation_mode="anchor", fontsize=8)
    ax.set(xlabel=xlabel, xlim=(-0.42, len(rows) - 0.58), ylim=(-0.04, 0.38),
           yticks=[0, 0.1, 0.2, 0.3])
    return whiskers, band


def main():
    font_manager.findfont("Georgia", fallback_to_default=False)
    mpl.rcParams.update({
        "font.family": "Georgia",
        "font.size": 9,
        "axes.titlesize": 11,
        "axes.unicode_minus": False,
        "legend.fontsize": 8,
        "legend.frameon": False,
        "pdf.fonttype": 42,
    })

    comparison = pd.read_csv(COMPARISON).set_index(["scheme", "reach"])
    wiki = comparison.loc["foreign_wikipedia"].loc[TIERS]
    count = comparison.loc["festival_count"].dropna(subset=["r_excess"])
    count_labels = (count.index.str.replace(r" festivals?$", "", regex=True)
                    .str.replace("-", " to ").str.replace("+", " or more", regex=False))
    share = pd.read_csv(REACH / "national_share.csv")
    share = share.loc[share["control"].eq("2 or more festivals")].set_index("tier").loc[TIERS]

    fig = plt.figure(figsize=(WIDTH, 4.15), layout="constrained")
    grid = fig.add_gridspec(3, 2, width_ratios=[1.35, 1], height_ratios=[1, 0.16, 1])
    ax = fig.add_subplot(grid[0, 0])
    by_count = fig.add_subplot(grid[0, 1], sharey=ax)
    key = fig.add_subplot(grid[1, :])
    national = fig.add_subplot(grid[2, :])
    marks = plot_excess(ax, wiki, TIER_LABELS, "A   Wikipedia reach", "Foreign editions")
    plot_excess(by_count, count, count_labels, "B   Festivals", "Distinct festivals")
    key.set_axis_off()
    key.legend(marks, ["Range after dropping one festival", "Central 95% of null"],
               loc="center", ncols=2, columnspacing=1.1, handlelength=1.3)
    ax.set_ylabel("Excess assortativity, r")
    by_count.tick_params(axis="y", labelleft=False)
    style_axes(national, "C   National booking concentration")
    marks = plot_national(national, share)
    national.legend(marks, ["Observed", "Central 95% of null"], loc="upper right")
    save(fig, "fig1")

    sound = pd.read_csv(WIKITEXT / "sound_effect.csv")
    years = ["all", *sorted(sound.loc[sound["year"].ne("all"), "year"].unique())]
    y = pd.Series(range(len(years)))
    fig, ax = plt.subplots(figsize=(WIDTH, 3.05), layout="constrained")
    style_axes(ax, "Lineup similarity and overlap")
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.vlines(0, -0.5, len(years) - 0.55, color=REFERENCE, linewidth=0.6, zorder=0)
    ax.axhline(0.5, color=REFERENCE, linewidth=0.5, zorder=0)
    for measure, label, marker, color, offset in [
        ("wiki_cosine", "Wikipedia intros", "o", OBSERVED, -0.16),
        ("genre_similarity_strict", "MusicBrainz tags", "s", "#9c543d", 0.16),
    ]:
        rows = sound.loc[sound["measure"].eq(measure)].set_index("year").loc[years]
        ax.hlines(y + offset, rows["deletion_min"], rows["deletion_max"],
                  color=color, linewidth=1, alpha=0.65)
        ax.scatter(rows["acts_per_0_10"], y + offset, color=color, marker=marker,
                   s=14, label=label, zorder=3)
    ax.set_yticks(y, ["Pooled", *years[1:]])
    ax.set(xlabel="Excess shared acts per 0.10 cosine", xlim=(-0.23, 3.35),
           ylim=(len(years) - 0.55, -1.55), xticks=[0, 1, 2, 3])
    ax.legend(loc="upper left", ncols=2, borderaxespad=0.2, columnspacing=1.0)
    save(fig, "fig3")


def plot_national(ax, share):
    marks = plot_reach(ax, share, "one_country_distinct", "one_country_distinct_null_low",
                       "one_country_distinct_null_high", "Share in top country")
    ax.set(xlabel="Foreign Wikipedia editions", ylim=(0.54, 0.90),
           yticks=[0.55, 0.65, 0.75, 0.85])
    ax.yaxis.set_major_formatter(mpl.ticker.PercentFormatter(xmax=1, decimals=0))
    return marks


if __name__ == "__main__":
    main()
