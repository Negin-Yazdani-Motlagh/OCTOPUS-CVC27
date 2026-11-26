"""Draw the manuscript Figure 7 from the regenerated shock grid.

The styling follows figure_reproduction/make_figures.py. This script does not
write into the original figure directory.
"""
from pathlib import Path
import csv

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
ROWS = list(csv.DictReader((HERE / "shock_and_policy_grid.csv").open()))
COLORS = {"local": "#477C91", "majority": "#C67D36", "strict": "#4F6EB5", "expert": "#A44765"}
MARKERS = {"local": "o", "majority": "s", "strict": "D", "expert": "^"}
LABELS = {
    "local": "Local",
    "majority": "Majority sharing",
    "strict": "F0 (two supporters)",
    "expert": "Expert override*",
}
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 8.0, "axes.titlesize": 8.3,
    "axes.labelsize": 8.1, "xtick.labelsize": 7.4, "ytick.labelsize": 7.4,
    "legend.fontsize": 7.1, "figure.dpi": 140, "savefig.dpi": 300,
    "axes.spines.top": False, "axes.spines.right": False,
    "pdf.fonttype": 42, "ps.fonttype": 42, "axes.linewidth": 0.6,
    "lines.linewidth": 1.5, "grid.alpha": 0.22,
})
fig, axes = plt.subplots(1, 2, figsize=(4.72, 2.55), sharex=True)
for axis, key, title in zip(axes, ("r_ge_2", "r_all_3"), ("At least two agents wrong", "All three agents wrong")):
    for method in ("local", "majority", "strict", "expert"):
        series = sorted((row for row in ROWS if row["method"] == method), key=lambda row: float(row["shock_probability"]))
        axis.plot(
            [100 * float(row["shock_probability"]) for row in series],
            [100 * float(row[key]) for row in series],
            marker=MARKERS[method], ms=3.3, color=COLORS[method], label=LABELS[method], lw=1.25,
        )
    axis.set_title(title, pad=5)
    axis.set_xlabel("B/C common shock (%)")
    axis.set_ylabel("Error probability (%)")
    axis.grid(lw=0.42)
    axis.set_xlim(-1, 25)
axes[0].legend(fontsize=6.5, frameon=False, loc="upper left")
axes[1].set_ylim(-1, 27)
fig.subplots_adjust(left=0.12, right=0.985, top=0.87, bottom=0.19, wspace=0.32)
for suffix in (".pdf", ".png"):
    fig.savefig(HERE / f"fig3_three_agent_risk_tradeoff{suffix}", bbox_inches="tight", pad_inches=0.05)
print("wrote fig3_three_agent_risk_tradeoff")
