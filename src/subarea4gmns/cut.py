"""Cut a subarea from a reference network.

Links with both ends inside the subarea are kept. Every node where a reference link crosses the
subarea edge gets a boundary centroid: a new zone node joined to it by a connector in each
direction that traffic crosses. Zones inside the subarea keep their zone_id. Each subarea link,
connectors included, carries the reference volume in `ref_volume`; a connector's reference
volume is the total reference volume crossing the edge at its node in that direction.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from .gmns import write_csv


def select_nodes(net, bbox=None, node_ids=None):
    """Node indices inside bbox = (xmin, ymin, xmax, ymax), or listed in node_ids."""
    if node_ids is not None:
        want = {str(n) for n in node_ids}
        return {i for i, n in enumerate(net.node_ids) if n in want}
    xmin, ymin, xmax, ymax = bbox
    out = set()
    for i, r in enumerate(net.node_rows):
        try:
            x, y = float(r["x_coord"]), float(r["y_coord"])
        except (KeyError, TypeError, ValueError):
            continue
        if xmin <= x <= xmax and ymin <= y <= ymax:
            out.add(i)
    return out


def inside_links(net, inside):
    return np.array([int(t) in inside and int(h) in inside for t, h in zip(net.tail, net.head)])


def _next_id(ids):
    vals = [int(float(s)) for s in ids if str(s).replace(".", "", 1).isdigit()]
    return (max(vals) + 1) if vals else 1


def cut(net, ref_volume, inside, out_dir=None, boundary_flows=None):
    """Build the subarea. Returns (summary, keymap); writes node.csv, link.csv, zone.csv if out_dir.

    keymap maps ("Z", zone_id) and ("B", node index) entry/exit keys (see assign.py) to the
    subarea zone_id.

    boundary_flows: optional {node index: (entering, leaving)} trips that cross the edge at that
    node and use subarea links (extract.py supplies these from the reference paths). Without it,
    traffic that crosses in and straight back out at the same node is removed as far as flow
    conservation allows: entering = min(crossing in, volume on subarea links leaving the node),
    leaving = entering - (subarea volume out - subarea volume in) at that node.
    """
    keep = inside_links(net, inside)
    if not keep.any():
        raise ValueError("no link has both ends inside the subarea; enlarge the bounding box or node list")
    ref_volume = np.asarray(ref_volume, float)
    t_in = np.array([int(t) in inside for t in net.tail])
    h_in = np.array([int(h) in inside for h in net.head])
    used = set(net.tail[keep].tolist()) | set(net.head[keep].tolist())
    cin, cout = {}, {}
    for a in np.where(~t_in & h_in)[0]:
        b = int(net.head[a])
        if b in used:
            cin[b] = cin.get(b, 0.0) + float(ref_volume[a])
    for a in np.where(t_in & ~h_in)[0]:
        b = int(net.tail[a])
        if b in used:
            cout[b] = cout.get(b, 0.0) + float(ref_volume[a])
    enter, leave = {}, {}
    if boundary_flows is not None:
        for b, (e, l) in boundary_flows.items():
            if b in used:
                enter[b], leave[b] = e, l
    else:
        iout = np.bincount(net.tail[keep], weights=ref_volume[keep], minlength=net.n_nodes)
        iin = np.bincount(net.head[keep], weights=ref_volume[keep], minlength=net.n_nodes)
        for b in set(cin) | set(cout):
            e = min(cin.get(b, 0.0), float(iout[b]))
            l = min(max(e - float(iout[b] - iin[b]), 0.0), cout.get(b, 0.0))
            enter[b], leave[b] = e, l
    bnodes = sorted(b for b in set(enter) | set(leave) if enter.get(b, 0.0) > 1e-9 or leave.get(b, 0.0) > 1e-9)
    enter = {b: v for b, v in enter.items() if v > 1e-9}
    leave = {b: v for b, v in leave.items() if v > 1e-9}
    nid, zid = _next_id(net.node_ids), _next_id(net.zone_of.values())
    keymap, zones = {}, []
    node_rows = []
    for i in sorted(used):
        r = dict(net.node_rows[i])
        if i in net.zone_of:
            keymap[("Z", net.zone_of[i])] = net.zone_of[i]
            zones.append(dict(zone_id=net.zone_of[i], node_id=net.node_ids[i], kind="internal",
                              entering=0.0, leaving=0.0))
        node_rows.append(r)
    link_rows = []
    for a in np.where(keep)[0]:
        r = dict(net.link_rows[a])
        r["ref_volume"] = round(float(ref_volume[a]), 6)
        link_rows.append(r)
    for k, b in enumerate(bnodes):
        c_id, c_zone = str(nid + k), str(zid + k)
        base = net.node_rows[b]
        node_rows.append(dict(node_id=c_id, node_type="centroid", zone_id=c_zone,
                              x_coord=base.get("x_coord", ""), y_coord=base.get("y_coord", "")))
        keymap[("B", b)] = c_zone
        zones.append(dict(zone_id=c_zone, node_id=c_id, kind="boundary", boundary_node=net.node_ids[b],
                          entering=round(enter.get(b, 0.0), 6), leaving=round(leave.get(b, 0.0), 6)))
        for fr, to, v, tag in ((c_id, net.node_ids[b], enter.get(b), "in"), (net.node_ids[b], c_id, leave.get(b), "out")):
            if v is None:
                continue
            link_rows.append(dict(link_id="c%s_%s" % (net.node_ids[b], tag), from_node_id=fr, to_node_id=to,
                                  link_type="connector", length=0.0, lanes=1, capacity=1e9, free_speed=60,
                                  vdf_fftt=0.0001, vdf_alpha=0.15, vdf_beta=4, ref_volume=round(v, 6)))
    summary = dict(nodes=len(used), links=int(keep.sum()), boundary_zones=len(bnodes),
                   internal_zones=sum(1 for z in zones if z["kind"] == "internal"),
                   volume_entering=round(sum(enter.values()), 3), volume_leaving=round(sum(leave.values()), 3))
    if out_dir is not None:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        nf = list(dict.fromkeys(k for r in node_rows for k in r))
        lf = list(dict.fromkeys(k for r in link_rows for k in r))
        write_csv(node_rows, out / "node.csv", nf)
        write_csv(link_rows, out / "link.csv", lf)
        write_csv(zones, out / "zone.csv", ["zone_id", "node_id", "kind", "boundary_node", "entering", "leaving"])
    return summary, keymap
