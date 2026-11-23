from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.text import Text
import numpy as np
import pandas as pd


def write_figures(OUT):
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
    YEARS = (2019, 2023)
    BAD = "\u2014\u2013\u2212\u2012\u2015\u2010\u2011"
    changes = pd.read_csv(OUT / "projection_changes.csv").to_dict("records")
    projections = pd.read_csv(OUT / "projection_summary.csv")

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.4), layout="constrained")
    for ax, year in zip(axes, YEARS):
        rows = pd.DataFrame(changes)
        rows = rows[(rows.year == year) & (rows.metric == "weight_net")]
        labels = ["All shared IDs", "All spellings", "Short-name bound", "ID conflict split", "Proposed fix"]
        bars = ax.barh(labels, rows.observed, color=["#777777", "#3e7c9b", "#b56c54", "#8977a6", "#35734c"])
        ax.bar_label(bars, labels=[f"{int(value):+d}" for value in rows.observed], padding=3)
        ax.margins(x=.18)
        ax.axvline(0, color="black", linewidth=.8)
        ax.set_title(str(year))
        ax.set_xlabel("Change in shared-act links")
    fig.canvas.draw()
    assert not any(ch in text.get_text() for text in fig.findobj(Text) for ch in BAD)
    fig.savefig(OUT / "identity_changes.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(9, 4), layout="constrained")
    for ax, year in zip(axes, YEARS):
        draws = np.load(OUT / f"nulls_{year}.npz")
        n = draws["baseline"].shape[1]
        mask = np.triu(np.ones((n, n), dtype=bool), 1)
        observed_counts = []
        for scenario, color, label in [("baseline", "#777777", "Original"), ("proposed_fix", "#35734c", "Proposed fix")]:
            values = np.count_nonzero(draws[scenario][:, mask], axis=1)
            observed = projections[(projections.year == year) & (projections.scenario == scenario) & (projections.metric == "positive_pairs")].iloc[0].observed
            ax.hist(values, bins=12, alpha=.5, color=color, label=label)
            observed_counts.append(observed)
        original, proposed = observed_counts
        if original == proposed:
            ax.axvline(original, color="#222222", linewidth=1.8, label="Observed")
        else:
            ax.axvline(original, color="#222222", linewidth=1.8, label="Observed original")
            ax.axvline(proposed, color="#222222", linewidth=1.8, linestyle="--",
                       label="Observed proposed")
        ax.set_title(str(year))
        ax.set_xlabel("Festival pairs sharing an act")
        ax.set_ylabel("Null graphs")
        ax.legend(fontsize=9)
    fig.canvas.draw()
    assert not any(ch in text.get_text() for text in fig.findobj(Text) for ch in BAD)
    fig.savefig(OUT / "projection_check.png", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    write_figures(Path("analysis/euler"))
