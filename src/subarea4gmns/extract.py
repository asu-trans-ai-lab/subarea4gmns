"""Subarea trip table from a reference model: the standard path-based extraction.

Given the reference network and its trip table, solve user equilibrium (assign.py) while cutting
every path at the subarea edge. A trip that starts or ends at a zone inside keeps that zone; a
trip that crosses the edge enters or leaves at the boundary centroid of the crossing node. A path
that leaves and re-enters gives two subarea trips. The pieces are weighted exactly as the
equilibrium flow is, so loading them reproduces the reference link volumes inside the subarea.

Paths from another solver (route_assignment.csv from DTALite / TAPLite / Path4GMNS, with a
node_sequence or link_sequence column) can be cut the same way with extract_from_routes.
"""
from __future__ import annotations

import numpy as np

from .assign import _cut_path, assign
from .cut import cut, inside_links
from .gmns import read_csv, num


def extract(net, demand, inside, out_dir=None, hours=1.0, iterations=100, gap=1e-5, verbose=False):
    """Solve the reference model, cut the subarea, and return (subarea_od, summary, result)."""
    sub = inside_links(net, inside)
    res = assign(net, demand, hours=hours, iterations=iterations, gap=gap, subarea_links=sub, verbose=verbose)
    summary, keymap = cut(net, res.volume, inside, out_dir, boundary_flows=_boundary(res.pieces))
    od = _map(res.pieces, keymap)
    summary.update(reference_gap=res.gap, reference_iterations=len(res.gaps), od_pairs=len(od),
                   trips=sum(od.values()))
    return od, summary, res


def extract_from_routes(net, route_csv, inside, ref_volume, out_dir=None):
    """Cut a route file (o_zone_id, d_zone_id, volume, node_sequence or link_sequence)."""
    sub = inside_links(net, inside)
    by_nodes = {(int(t), int(h)): a for a, (t, h) in enumerate(zip(net.tail, net.head))}
    idx = {n: i for i, n in enumerate(net.node_ids)}
    lidx = {r["link_id"]: a for a, r in enumerate(net.link_rows)}
    pieces = {}
    for r in read_csv(route_csv):
        v = num(r.get("volume"))
        if v <= 0:
            continue
        if r.get("link_sequence"):
            seq = [lidx[s] for s in r["link_sequence"].replace(",", ";").split(";") if s.strip()]
        else:
            ns = [idx[s.strip()] for s in r["node_sequence"].replace(",", ";").split(";") if s.strip()]
            seq = [by_nodes[(a, b)] for a, b in zip(ns[:-1], ns[1:])]
        _cut_path(net, seq, sub, r["o_zone_id"].strip(), r["d_zone_id"].strip(), v, pieces)
    summary, keymap = cut(net, np.asarray(ref_volume), inside, out_dir, boundary_flows=_boundary(pieces))
    od = _map(pieces, keymap)
    summary.update(od_pairs=len(od), trips=sum(od.values()))
    return od, summary


def _boundary(pieces):
    """{boundary node: (trips entering there, trips leaving there)} from path pieces."""
    flows = {}
    for (ek, xk), v in pieces.items():
        if ek[0] == "B":
            e, l = flows.get(ek[1], (0.0, 0.0))
            flows[ek[1]] = (e + v, l)
        if xk[0] == "B":
            e, l = flows.get(xk[1], (0.0, 0.0))
            flows[xk[1]] = (e, l + v)
    return flows


def _map(pieces, keymap):
    od = {}
    for (ek, xk), v in pieces.items():
        o, d = keymap.get(ek), keymap.get(xk)
        if o is None or d is None or o == d or v <= 1e-9:
            continue
        od[(o, d)] = od.get((o, d), 0.0) + v
    return od
