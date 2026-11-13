"""Assign a subarea trip table and compare with the reference link volumes."""
from __future__ import annotations

import numpy as np

from .assign import assign, measures
from .gmns import read_network


def compare(net, volume, time, ref, hours=1.0):
    """Fit statistics of `volume` against `ref` on physical (non-connector) links."""
    m = ~net.connector
    err = volume[m] - ref[m]
    ss_tot = float(np.sum((ref[m] - ref[m].mean()) ** 2))
    a, b = measures(net, volume, time), measures(net, ref, net.travel_time(ref, hours))
    pct = lambda x, y: 100.0 * (x / y - 1.0) if y else 0.0
    return dict(links=int(m.sum()),
                VMT=round(a["VMT"], 1), VMT_ref=round(b["VMT"], 1), VMT_diff_pct=round(pct(a["VMT"], b["VMT"]), 4),
                VHT=round(a["VHT"], 2), VHT_ref=round(b["VHT"], 2), VHT_diff_pct=round(pct(a["VHT"], b["VHT"]), 4),
                link_WAPE_pct=round(100.0 * float(np.abs(err).sum()) / float(ref[m].sum()), 4) if ref[m].sum() else 0.0,
                link_R2=round(1.0 - float(np.sum(err ** 2)) / ss_tot, 6) if ss_tot else 1.0,
                max_abs_link_diff=round(float(np.abs(err).max()), 3))


def check(folder, od, ref_col="ref_volume", hours=1.0, iterations=100, gap=1e-5, **read_kw):
    """Assign `od` on the subarea in `folder` to equilibrium; compare with its ref_volume column.
    Returns (summary, per-link rows)."""
    net = read_network(folder, **read_kw)
    ref = net.column(ref_col)
    res = assign(net, od, hours=hours, iterations=iterations, gap=gap)
    s = dict(od_pairs=len(od), trips=round(sum(od.values()), 3), relative_gap=round(res.gap, 8),
             unassigned=round(res.unassigned, 3))
    s.update(compare(net, res.volume, res.time, ref, hours))
    rows = [dict(link_id=r["link_id"], from_node_id=r["from_node_id"], to_node_id=r["to_node_id"],
                 ref_volume=round(float(ref[a]), 3), volume=round(float(res.volume[a]), 3),
                 diff=round(float(res.volume[a] - ref[a]), 3), travel_time_min=round(float(res.time[a]), 4))
            for a, r in enumerate(net.link_rows)]
    return s, rows
