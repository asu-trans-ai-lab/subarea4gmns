"""Subarea trip table from link volumes alone (no reference paths or trip table).

Use when all you have is a loaded network: a subarea whose zones are centroids joined by
connectors, with the reference volume on every link (ref_volume), connectors included.
Each centroid's supply is the volume on its outgoing connectors and its demand the volume on
its incoming connectors. Repeat until no volume is left: take the link with the most volume
still unassigned; find the fewest-link path from a centroid with supply left, through that link,
to another centroid with demand left, on links with volume left and never through a centroid;
assign the smallest of those amounts as one trip movement and subtract it.

On a corridor, where trips between two points share one route, this reproduces every link volume
exactly. On a grid of alternative routes, link volumes do not determine the paths: part of the
volume can stay unexplained, and the trip table is one of many that fit. The report gives the
share explained; use extract.py when the reference model's trip table or paths are available.
"""
from __future__ import annotations

from collections import deque

import numpy as np

from .gmns import read_network

TOL = 1e-6


def rebuild(folder, ref_col="ref_volume", **read_kw):
    """Returns (od, report)."""
    net = read_network(folder, **read_kw)
    ref = net.column(ref_col)
    open_zones = [net.node_ids[i] for i in net.zone_of if i not in net.blocked]
    if open_zones:
        raise ValueError("zones on through nodes have unknown trip ends: %s. Give every zone a centroid "
                         "with connectors, or use extract.py with the reference trip table." % open_zones[:10])
    sup = {i: float(ref[net.tail == i].sum()) for i in net.blocked}
    dem = {i: float(ref[net.head == i].sum()) for i in net.blocked}
    out_links = [[] for _ in range(net.n_nodes)]
    for a in range(net.n_links):
        out_links[net.tail[a]].append(a)
    resid = ref.copy()

    def path(src, must):
        prev, q = {src: None}, deque([src])
        while q:
            u = q.popleft()
            if u != src and dem.get(u, 0.0) > TOL:
                seq, c = [], u
                while prev[c] is not None:
                    seq.append(prev[c])
                    c = int(net.tail[prev[c]])
                seq.reverse()
                if must is None or must in seq:
                    return seq
            if u != src and u in net.blocked:
                continue
            for a in out_links[u]:
                v = int(net.head[a])
                if resid[a] > TOL and v not in prev:
                    prev[v] = a
                    q.append(v)
        return None

    od, paths = {}, 0
    for _ in range(20 * net.n_links + 1000):
        top = int(np.argmax(resid))
        if resid[top] <= TOL:
            break
        seq = None
        for must in (top, None):
            for s in sorted(sup, key=lambda i: -sup[i]):
                if sup[s] > TOL:
                    seq = path(s, must)
                    if seq:
                        break
            if seq:
                break
        if not seq:
            break
        o, d = int(net.tail[seq[0]]), int(net.head[seq[-1]])
        f = min(float(resid[seq].min()), sup[o], dem[d])
        resid[seq] -= f
        sup[o] -= f
        dem[d] -= f
        key = (net.zone_of[o], net.zone_of[d])
        od[key] = od.get(key, 0.0) + f
        paths += 1
    m = ~net.connector
    total = float(ref[m].sum())
    left = float(np.clip(resid[m], 0, None).sum())
    vin = np.bincount(net.head, weights=ref, minlength=net.n_nodes)
    vout = np.bincount(net.tail, weights=ref, minlength=net.n_nodes)
    unbalanced = [net.node_ids[i] for i in range(net.n_nodes) if i not in net.zone_of
                  and abs(vin[i] - vout[i]) > 1e-4 * max(vin[i], vout[i], 1.0)]
    report = dict(links=int(m.sum()), centroids=len(net.blocked), unbalanced_nodes=unbalanced, paths=paths,
                  od_pairs=len(od), trips=sum(od.values()),
                  explained_pct=100.0 * (total - left) / total if total else 100.0,
                  links_left=int((resid[m] > 1e-3).sum()))
    return od, report
