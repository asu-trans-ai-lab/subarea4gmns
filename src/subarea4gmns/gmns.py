"""Read and write GMNS network and demand files.

A GMNS folder holds node.csv and link.csv (https://github.com/zephyr-data-specs/GMNS); demand
is a demand.csv with o_zone_id, d_zone_id, volume.

Zones are nodes with a zone_id (or node_type "centroid"). A zone node whose links are all
connectors (link_type contains "connector") is a centroid that trips may start or end at but
not pass through. A zone node on the street network itself, as in Sioux Falls, carries through
traffic.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

LENGTH_TO_MILE = {"mi": 1.0, "m": 1 / 1609.344, "km": 1 / 1.609344, "ft": 1 / 5280.0}
SPEED_TO_MPH = {"mph": 1.0, "kph": 1 / 1.609344}


def num(x, d=0.0):
    try:
        s = str(x).strip()
        return float(s) if s else d
    except (TypeError, ValueError):
        return d


def _clean_id(s):
    s = (s or "").strip()
    return s[:-2] if s.endswith(".0") else s


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def write_csv(rows, path, fields=None):
    fields = fields or list(rows[0])
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def _first(row, names, default=0.0):
    low = {k.lower(): v for k, v in row.items() if k}
    for n in names:
        v = num(low.get(n.lower()), 0.0)
        if v > 0:
            return v
    return default


@dataclass
class Network:
    """A directed GMNS network with BPR link performance."""
    node_ids: list
    node_rows: list
    link_rows: list
    tail: np.ndarray            # node index of each link's from node
    head: np.ndarray            # node index of each link's to node
    length: np.ndarray          # miles
    fftt: np.ndarray            # free-flow travel time, minutes
    cap: np.ndarray             # vehicles per hour, all lanes
    alpha: np.ndarray
    beta: np.ndarray
    connector: np.ndarray       # bool: centroid connector
    zone_of: dict = field(default_factory=dict)    # node index -> zone_id
    blocked: set = field(default_factory=set)      # zone nodes closed to through traffic

    @property
    def n_nodes(self):
        return len(self.node_ids)

    @property
    def n_links(self):
        return len(self.link_rows)

    def zone_node(self):
        return {z: i for i, z in self.zone_of.items()}

    def column(self, name, default=0.0):
        return np.array([num(r.get(name), default) for r in self.link_rows])

    def travel_time(self, volume, hours=1.0):
        """BPR travel time in minutes for link volumes over a period of `hours`."""
        x = np.maximum(volume, 0.0) / (self.cap * hours)
        return self.fftt * (1.0 + self.alpha * np.power(np.minimum(x, 10.0), self.beta))


def read_network(folder, length_unit="mi", speed_unit="mph", capacity_per_lane=False):
    """Read node.csv and link.csv from a GMNS folder.

    length_unit        unit of link.length: "mi", "m", "km" or "ft"
    speed_unit         unit of link.free_speed: "mph" or "kph"
    capacity_per_lane  True when link.capacity is per lane (multiplied by lanes);
                       False when it already covers all lanes
    Free-flow time: VDF_fftt1 or vdf_fftt (minutes) when present, else length / free_speed.
    BPR: VDF_alpha1 / vdf_alpha / alpha and VDF_beta1 / vdf_beta / beta, else 0.15 and 4.
    """
    folder = Path(folder)
    nodes = read_csv(folder / "node.csv")
    links = read_csv(folder / "link.csv")
    node_ids = [_clean_id(r["node_id"]) for r in nodes]
    idx = {n: i for i, n in enumerate(node_ids)}
    lf, sf = LENGTH_TO_MILE[length_unit], SPEED_TO_MPH[speed_unit]
    tail = np.array([idx[_clean_id(r["from_node_id"])] for r in links], dtype=np.int64)
    head = np.array([idx[_clean_id(r["to_node_id"])] for r in links], dtype=np.int64)
    length = np.array([num(r.get("length")) * lf for r in links])
    speed = np.array([num(r.get("free_speed"), 30.0) * sf for r in links])
    speed[speed <= 0] = 30.0
    given = np.array([_first(r, ("VDF_fftt1", "vdf_fftt")) for r in links])
    fftt = np.where(given > 0, given, np.where(length > 0, length / speed * 60.0, 0.01))
    lanes = np.array([max(num(r.get("lanes"), 1.0), 1.0) for r in links])
    cap = np.array([_first(r, ("capacity",), 1800.0) for r in links]) * (lanes if capacity_per_lane else 1.0)
    alpha = np.array([_first(r, ("VDF_alpha1", "vdf_alpha", "alpha"), 0.15) for r in links])
    beta = np.array([_first(r, ("VDF_beta1", "vdf_beta", "beta"), 4.0) for r in links])
    connector = np.array(["connector" in (r.get("link_type") or "").lower() for r in links])
    zone_of = {}
    for i, r in enumerate(nodes):
        z = _clean_id(r.get("zone_id"))
        if (z and z not in ("0", "-1")) or (r.get("node_type") or "").strip().lower() == "centroid":
            zone_of[i] = z or node_ids[i]
    blocked = set()
    touch = {}
    for a in range(len(links)):
        for n in (tail[a], head[a]):
            touch.setdefault(int(n), []).append(bool(connector[a]))
    for i in zone_of:
        if touch.get(i) and all(touch[i]):
            blocked.add(i)
    return Network(node_ids, nodes, links, tail, head, length, fftt, cap, alpha, beta, connector, zone_of, blocked)


def read_demand(path, column="volume"):
    """demand.csv with o_zone_id, d_zone_id, volume -> {(o, d): volume}; o == d dropped."""
    od = {}
    for r in read_csv(path):
        o, d = _clean_id(r["o_zone_id"]), _clean_id(r["d_zone_id"])
        v = num(r.get(column))
        if v > 0 and o != d:
            od[(o, d)] = od.get((o, d), 0.0) + v
    return od


def write_demand(od, path):
    rows = [dict(o_zone_id=o, d_zone_id=d, volume=round(v, 6))
            for (o, d), v in sorted(od.items(), key=lambda kv: -kv[1])]
    write_csv(rows, path, ["o_zone_id", "d_zone_id", "volume"])
