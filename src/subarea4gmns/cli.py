"""Command line:

  subarea4gmns extract  <reference_gmns> <out_dir> (--bbox XMIN YMIN XMAX YMAX | --nodes FILE)
                        [--demand demand.csv] [--hours 1] [--iterations 100]
  subarea4gmns rebuild  <subarea_gmns> [--out demand.csv]
  subarea4gmns check    <subarea_gmns> <demand.csv> [--hours 1]
  subarea4gmns assign   <gmns> [--demand demand.csv] [--hours 1] [--out link_performance.csv]

Common options: --length-unit mi|m|km|ft, --speed-unit mph|kph, --capacity-per-lane.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .assign import assign, measures
from .check import check
from .cut import select_nodes
from .extract import extract
from .gmns import read_demand, read_network, write_csv, write_demand
from .rebuild import rebuild


def _net_kw(a):
    return dict(length_unit=a.length_unit, speed_unit=a.speed_unit, capacity_per_lane=a.capacity_per_lane)


def main(argv=None):
    p = argparse.ArgumentParser(prog="subarea4gmns", description="Subarea network and trip table from a reference model.")
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("--length-unit", default="mi", choices=["mi", "m", "km", "ft"])
        sp.add_argument("--speed-unit", default="mph", choices=["mph", "kph"])
        sp.add_argument("--capacity-per-lane", action="store_true")
        sp.add_argument("--hours", type=float, default=1.0, help="length of the demand period")

    e = sub.add_parser("extract", help="cut a subarea and extract its trip table from the reference model")
    e.add_argument("network"); e.add_argument("out")
    e.add_argument("--demand"); e.add_argument("--bbox", type=float, nargs=4); e.add_argument("--nodes")
    e.add_argument("--iterations", type=int, default=100); common(e)
    r = sub.add_parser("rebuild", help="trip table from link volumes alone (corridor cuts)")
    r.add_argument("subarea"); r.add_argument("--out", default="demand.csv"); common(r)
    c = sub.add_parser("check", help="assign a subarea trip table and compare with ref_volume")
    c.add_argument("subarea"); c.add_argument("demand"); common(c)
    s = sub.add_parser("assign", help="user-equilibrium assignment")
    s.add_argument("network"); s.add_argument("--demand"); s.add_argument("--out", default="link_performance.csv")
    s.add_argument("--iterations", type=int, default=100); common(s)
    a = p.parse_args(argv)

    if a.cmd == "extract":
        net = read_network(a.network, **_net_kw(a))
        od = read_demand(a.demand or Path(a.network) / "demand.csv")
        ids = [l.strip() for l in open(a.nodes) if l.strip()] if a.nodes else None
        inside = select_nodes(net, bbox=a.bbox, node_ids=ids)
        sod, summary, _ = extract(net, od, inside, a.out, hours=a.hours, iterations=a.iterations)
        write_demand(sod, Path(a.out) / "demand.csv")
        print(json.dumps(summary, indent=1))
    elif a.cmd == "rebuild":
        sod, rep = rebuild(a.subarea, **_net_kw(a))
        write_demand(sod, a.out)
        print(json.dumps({k: v for k, v in rep.items() if k != "unbalanced_nodes"}, indent=1))
        if rep["unbalanced_nodes"]:
            print("unbalanced nodes:", rep["unbalanced_nodes"][:20])
    elif a.cmd == "check":
        s, rows = check(a.subarea, read_demand(a.demand), hours=a.hours, **_net_kw(a))
        write_csv(rows, Path(a.subarea) / "check_links.csv")
        print(json.dumps(s, indent=1))
    elif a.cmd == "assign":
        net = read_network(a.network, **_net_kw(a))
        res = assign(net, read_demand(a.demand or Path(a.network) / "demand.csv"), hours=a.hours, iterations=a.iterations)
        rows = [dict(link_id=r["link_id"], from_node_id=r["from_node_id"], to_node_id=r["to_node_id"],
                     volume=round(float(res.volume[i]), 4), travel_time=round(float(res.time[i]), 5))
                for i, r in enumerate(net.link_rows)]
        write_csv(rows, a.out)
        print(json.dumps(dict(relative_gap=res.gap, iterations=len(res.gaps), **measures(net, res.volume, res.time)), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
