"""Static user-equilibrium traffic assignment: Frank-Wolfe with line search, BPR costs.

The equilibrium link flow is a weighted mix of all-or-nothing loadings. When a subarea is given,
each loading's paths are cut at the subarea edge and the pieces inside are recorded with the
same weights, so the subarea trip table reproduces the equilibrium link flow inside the subarea
exactly (see extract.py).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra


@dataclass
class Result:
    volume: np.ndarray
    time: np.ndarray                         # minutes
    gaps: list                               # relative gap by iteration
    unassigned: float = 0.0                  # demand with no path
    pieces: dict = field(default_factory=dict)   # {(entry key, exit key): vehicles} inside the subarea

    @property
    def gap(self):
        return self.gaps[-1] if self.gaps else float("nan")


class _Graph:
    """Search graph. A blocked centroid gets a separate arrival copy, so no path passes it."""

    def __init__(self, net):
        n = net.n_nodes
        self.arrive = {c: n + k for k, c in enumerate(sorted(net.blocked))}
        self.N = n + len(self.arrive)
        self.tail = net.tail.copy()
        self.head = np.array([self.arrive.get(int(h), int(h)) for h in net.head], dtype=np.int64)
        self.real = np.arange(self.N)
        for c, k in self.arrive.items():
            self.real[k] = c

    def dest(self, i):
        return self.arrive.get(i, i)


def _aon(net, g, cost, pairs, inside=None, origin_zone=None, dest_zone=None):
    """All-or-nothing loading. Returns (link volumes, lost demand, pieces or None)."""
    tail, head = g.tail, g.head
    order = np.lexsort((cost, head, tail))                    # cheapest of any parallel links
    key = tail[order] * g.N + head[order]
    keep = np.ones(len(order), bool)
    keep[1:] = key[1:] != key[:-1]
    best = order[keep]
    link_of = np.full((g.N,), -1, dtype=np.int64)              # filled per origin below
    mat = csr_matrix((cost[best] + 1e-12, (tail[best], head[best])), shape=(g.N, g.N))
    lk = {(int(tail[b]), int(head[b])): int(b) for b in best}
    origins = sorted(pairs)
    dist, pred = dijkstra(mat, directed=True, indices=origins, return_predecessors=True)
    y = np.zeros(net.n_links)
    lost = 0.0
    pieces = {} if inside is not None else None
    for r, o in enumerate(origins):
        flow = np.zeros(g.N)
        for dn, v in pairs[o]:
            if np.isfinite(dist[r, dn]):
                flow[dn] += v
            else:
                lost += v
        reach = np.where(np.isfinite(dist[r]))[0]
        # each node's incoming tree link
        for v in reach:
            u = pred[r, v]
            link_of[v] = lk[(int(u), int(v))] if u >= 0 else -1
        for v in reach[np.argsort(-dist[r, reach])]:
            f = flow[v]
            if f > 0 and link_of[v] >= 0:
                y[link_of[v]] += f
                flow[pred[r, v]] += f
        if pieces is not None:
            for dn, v in pairs[o]:
                if not np.isfinite(dist[r, dn]):
                    continue
                seq, c = [], dn
                while c != o:
                    seq.append(link_of[c])
                    c = pred[r, c]
                seq.reverse()
                _cut_path(net, seq, inside, origin_zone[o], dest_zone[(o, dn)], v, pieces)
    return y, lost, pieces


def _cut_path(net, seq, inside, oz, dz, v, pieces):
    """Record the runs of `seq` that lie inside the subarea as (entry key, exit key)."""
    run = None
    for k, a in enumerate(seq):
        if inside[a]:
            if run is None:
                run = k
        if run is not None and (not inside[a] or k == len(seq) - 1):
            last = k if inside[a] else k - 1
            first_node = int(net.tail[seq[run]])
            last_node = int(net.head[seq[last]])
            ek = ("Z", oz) if run == 0 else ("B", first_node)
            xk = ("Z", dz) if last == len(seq) - 1 else ("B", last_node)
            pieces[(ek, xk)] = pieces.get((ek, xk), 0.0) + v
            run = None


def assign(net, demand, hours=1.0, iterations=50, gap=1e-4, subarea_links=None, verbose=False):
    """User equilibrium for {(o_zone, d_zone): vehicles} over a period of `hours`.

    subarea_links: optional boolean mask of links inside a subarea. When given, the result's
    `pieces` holds the equilibrium trips inside the subarea, keyed by entry and exit:
    ("Z", zone_id) where a trip starts or ends at a zone inside, ("B", node index) where it
    crosses the subarea edge.
    """
    g = _Graph(net)
    zn = net.zone_node()
    pairs, missing = {}, 0.0
    origin_zone, dest_zone = {}, {}
    for (o, d), v in demand.items():
        if o not in zn or d not in zn:
            missing += v
            continue
        on, dn = zn[o], g.dest(zn[d])
        pairs.setdefault(on, []).append((dn, v))
        origin_zone[on] = o
        dest_zone[(on, dn)] = d
    sub = None if subarea_links is None else np.asarray(subarea_links, bool)
    t = net.travel_time(np.zeros(net.n_links), hours)
    x, lost, P = _aon(net, g, t, pairs, sub, origin_zone, dest_zone)
    gaps = []
    for k in range(1, iterations + 1):
        t = net.travel_time(x, hours)
        y, lost, Py = _aon(net, g, t, pairs, sub, origin_zone, dest_zone)
        tstt, sptt = float(t @ x), float(t @ y)
        rg = (tstt - sptt) / tstt if tstt > 0 else 0.0
        gaps.append(rg)
        if verbose and (k <= 3 or k % 10 == 0):
            print("  iteration %3d  relative gap %.6f" % (k, rg))
        if rg < gap:
            break
        d = y - x
        lo, hi = 0.0, 1.0                                      # bisection on the Beckmann derivative
        for _ in range(40):
            mid = (lo + hi) / 2
            if float(d @ net.travel_time(x + mid * d, hours)) > 0:
                hi = mid
            else:
                lo = mid
        lam = (lo + hi) / 2
        x = x + lam * d
        if sub is not None:
            P = {key: (1 - lam) * val for key, val in P.items()}
            for key, val in Py.items():
                P[key] = P.get(key, 0.0) + lam * val
    return Result(x, net.travel_time(x, hours), gaps, lost + missing, P or {})


def measures(net, volume, time, mask=None):
    """Vehicle-miles, vehicle-hours and vehicle-hours of delay on the masked links."""
    m = ~net.connector if mask is None else mask
    return dict(VMT=float(np.sum(volume[m] * net.length[m])),
                VHT=float(np.sum(volume[m] * time[m]) / 60.0),
                VHD=float(np.sum(volume[m] * (time[m] - net.fftt[m])) / 60.0))
