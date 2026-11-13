"""Draws docs/workflow.png.  python make_workflow_figure.py"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon

NAVY, NAVY_BG = "#1F3B63", "#E3EAF4"
RUST, RUST_BG = "#A84A14", "#FBEBDD"
GREEN, GREEN_BG = "#1F6B4A", "#D6E8DD"
GRAY, GRAY_BG = "#5E6878", "#EEEEEE"

fig = plt.figure(figsize=(10, 6.6))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 10); ax.set_ylim(-0.4, 6.2); ax.axis("off")


def box(x, y, w, h, title, lines, ec, fc):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fc, ec=ec, lw=1.4))
    n = len(lines) + 1
    top = y + 0.16 * (n - 1) / 2
    ax.text(x, top, title, ha="center", va="center", fontsize=10, weight="bold", color=ec)
    for i, ln in enumerate(lines, 1):
        ax.text(x, top - 0.16 * i * 1.05, ln, ha="center", va="center", fontsize=8.3, color="#222222")


def data(x, y, w, h, text):
    s = 0.12
    ax.add_patch(Polygon([(x - w / 2 + s, y + h / 2), (x + w / 2 + s, y + h / 2), (x + w / 2 - s, y - h / 2), (x - w / 2 - s, y - h / 2)],
                         closed=True, fc=GRAY_BG, ec=GRAY, lw=1.2))
    ax.text(x, y, text, ha="center", va="center", fontsize=8.6, color="#222222", linespacing=1.3)


def arrow(p, q, label=None, dashed=False):
    ax.annotate("", xy=q, xytext=p, arrowprops=dict(arrowstyle="-|>", color="#333333", lw=1.2, ls="--" if dashed else "-", mutation_scale=11))
    if label:
        ax.text((p[0] + q[0]) / 2, (p[1] + q[1]) / 2 + 0.12, label, ha="center", fontsize=7.6, color="#333333")


ax.text(0.25, 5.95, "subarea4gmns workflow", fontsize=12.5, weight="bold", color=NAVY)
data(1.6, 5.15, 2.6, 0.62, "OpenStreetMap\nosm2gmns  +  grid2demand")
data(4.95, 5.15, 2.6, 0.62, "Reference model\n(MPO or regional model, GMNS)")
data(8.3, 5.15, 2.6, 0.62, "Benchmark networks\nTAPLab: Sioux Falls, Chicago")
box(4.95, 3.95, 5.2, 0.8, "1  Reference network and trip table", ["node.csv, link.csv, demand.csv  ·  zones are centroids or network nodes"], NAVY, NAVY_BG)
for x in (1.6, 4.95, 8.3):
    arrow((x, 4.83), (4.95 + (x - 4.95) * 0.45, 4.36))
box(2.6, 2.6, 3.9, 0.95, "2  Reference model run", ["assign: user equilibrium (Frank-Wolfe, BPR)", "or TAPLab / TAPLite / Path4GMNS routes"], NAVY, NAVY_BG)
box(7.3, 2.6, 3.9, 0.95, "3  Cut the subarea", ["bounding box or node list", "boundary centroid at every edge crossing"], RUST, RUST_BG)
arrow((4.2, 3.55), (2.9, 3.08)); arrow((5.7, 3.55), (7.0, 3.08))
arrow((4.55, 2.6), (5.35, 2.6), "link volumes")
box(2.6, 1.15, 3.9, 0.95, "4a  extract", ["cut the reference paths at the edge", "exact; needs the trip table or routes"], GREEN, GREEN_BG)
box(7.3, 1.15, 3.9, 0.95, "4b  rebuild", ["split link volumes into trip movements", "volumes only; exact on corridors"], GREEN, GREEN_BG)
arrow((2.6, 2.12), (2.6, 1.63)); arrow((7.3, 2.12), (7.3, 1.63))
box(4.95, -0.02, 6.6, 0.62, "5  check", ["assign the subarea trip table; compare VMT, VHT and link volumes with the reference"], NAVY, "#FFFFFF")
arrow((2.6, 0.67), (3.4, 0.30)); arrow((7.3, 0.67), (6.5, 0.30))
out = Path(__file__).resolve().parent / "workflow.png"
fig.savefig(out, dpi=200)
print("wrote", out)
