"""Sioux Falls: reference model -> subarea -> trip table -> check.

    python run_example.py

The reference model is the classic Sioux Falls network and trip table (data/, from TAPLab's
TAPBench; TNTP TransportationNetworks, LeBlanc et al. 1975, research use). Every node is a zone
and carries through traffic.

  1 solve the reference model (user equilibrium) and compare with the best-known flows
  2 cut a 10-node subarea in the middle of the network
  3 extract the subarea trip table from the reference paths
  4 assign it on the subarea and compare with the reference link volumes
Writes out/subarea/ (node.csv, link.csv, zone.csv, demand.csv, check_links.csv) and out/summary.json.
"""
import csv
import json
from pathlib import Path

import numpy as np

from subarea4gmns import check, extract, read_demand, read_network, select_nodes, write_csv, write_demand

HERE = Path(__file__).resolve().parent
DATA, OUT = HERE / "data", HERE / "out"
SUBAREA = ["8", "9", "10", "11", "14", "15", "16", "17", "22", "23"]

net = read_network(DATA)
od = read_demand(DATA / "demand.csv")
print("reference model: %d nodes, %d links, %d zones, %.0f trips" % (net.n_nodes, net.n_links, len(net.zone_of), sum(od.values())))

inside = select_nodes(net, node_ids=SUBAREA)
sod, summary, res = extract(net, od, inside, OUT / "subarea", iterations=300, gap=1e-6)
best = {(r["from_node_id"], r["to_node_id"]): float(r["volume"])
        for r in csv.DictReader(open(DATA / "best_known_link_performance.csv"))}
bk = np.array([best[(net.node_ids[t], net.node_ids[h])] for t, h in zip(net.tail, net.head)])
summary["reference_vs_best_known_RMSE"] = round(float(np.sqrt(np.mean((res.volume - bk) ** 2))), 2)
summary["best_known_mean_flow"] = round(float(bk.mean()), 1)
print("reference run: relative gap %.1e, RMSE against best-known flows %.1f (mean flow %.0f)"
      % (res.gap, summary["reference_vs_best_known_RMSE"], bk.mean()))
print("subarea: %(nodes)d nodes, %(links)d links, %(internal_zones)d zones inside, %(boundary_zones)d boundary zones" % summary)
write_demand(sod, OUT / "subarea" / "demand.csv")
print("subarea trip table: %d OD pairs, %.0f trips" % (len(sod), sum(sod.values())))

s, rows = check(OUT / "subarea", sod, iterations=300, gap=1e-6)
write_csv(rows, OUT / "subarea" / "check_links.csv")
summary["check"] = s
(OUT / "summary.json").write_text(json.dumps(summary, indent=1))
print("check: VMT %(VMT).0f vs %(VMT_ref).0f (%(VMT_diff_pct)+.3f%%), VHT %(VHT).0f vs %(VHT_ref).0f "
      "(%(VHT_diff_pct)+.3f%%), link WAPE %(link_WAPE_pct).3f%%, R2 %(link_R2).5f" % s)
