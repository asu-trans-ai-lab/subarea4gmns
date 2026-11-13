"""Attach zone centroids to a network.

Synthetic-demand tools such as grid2demand describe zones by a centroid point (zone.csv with
zone_id, x_coord, y_coord). This writes a network folder in which each zone with demand gets a
centroid node joined to its nearest network node by a connector in each direction, so trips can
start and end there but not pass through. Only nodes in the largest strongly connected part of
the network are used, so every centroid can reach every other.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components

from .gmns import LENGTH_TO_MILE, num, read_csv, write_csv


def add_centroids(network_dir, zone_csv, out_dir, demand=None, length_unit="mi", connector_speed=25.0):
    """Returns the number of centroids written. `demand` (optional) limits zones to those used.
    Connector length is written in `length_unit`; `connector_speed` is in the network's speed unit."""
    network_dir, out_dir = Path(network_dir), Path(out_dir)
    nodes = read_csv(network_dir / "node.csv")
    links = read_csv(network_dir / "link.csv")
    used = None if demand is None else {z for od in demand for z in od}
    # attach only to the largest strongly connected part, so every centroid reaches every other
    ix = {r["node_id"]: i for i, r in enumerate(nodes)}
    t = [ix[r["from_node_id"]] for r in links]
    h = [ix[r["to_node_id"]] for r in links]
    g = csr_matrix((np.ones(len(t)), (t, h)), shape=(len(nodes), len(nodes)))
    _, lab = connected_components(g, directed=True, connection="strong")
    big = np.bincount(lab).argmax()
    cand = [r for i, r in enumerate(nodes) if lab[i] == big]
    for r in nodes:
        r["zone_id"] = ""                       # zones live on the centroids only
    nid = max(int(float(r["node_id"])) for r in nodes) + 1
    lid = max(int(float(r["link_id"])) for r in links) + 1 if links else 1
    new_nodes, new_links = [], []
    for z in read_csv(zone_csv):
        zid = z["zone_id"].strip()
        if used is not None and zid not in used:
            continue
        x, y = num(z.get("x_coord")), num(z.get("y_coord"))
        k = math.cos(math.radians(y))
        near = min(cand, key=lambda r: ((num(r["x_coord"]) - x) * k) ** 2 + (num(r["y_coord"]) - y) ** 2)
        dist_mi = math.hypot((num(near["x_coord"]) - x) * k, num(near["y_coord"]) - y) * 69.05
        c = str(nid); nid += 1
        new_nodes.append(dict(node_id=c, x_coord=x, y_coord=y, zone_id=zid, node_type="centroid"))
        for fr, to in ((c, near["node_id"]), (near["node_id"], c)):
            new_links.append(dict(link_id=str(lid), from_node_id=fr, to_node_id=to, link_type="connector",
                                  length=round(dist_mi / LENGTH_TO_MILE[length_unit], 5), lanes=1, capacity=100000, free_speed=connector_speed))
            lid += 1
    out_dir.mkdir(parents=True, exist_ok=True)
    nf = list(dict.fromkeys([k for r in nodes for k in r] + ["node_type"]))
    lf = list(dict.fromkeys([k for r in links for k in r]))
    write_csv(nodes + new_nodes, out_dir / "node.csv", nf)
    write_csv(links + new_links, out_dir / "link.csv", lf)
    return len(new_nodes)
