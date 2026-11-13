"""Chicago Sketch: a larger reference model (933 nodes, 2,950 links, 387 zones, 1.1 million trips).

    python run_example.py             # downloads the network from TAPLab on first run
    python run_example.py --iterations 30

Data: TAPLab TAPBench chicago_sketch (https://github.com/asu-trans-ai-lab/TAPLab; TNTP
TransportationNetworks, Eash et al. 1979, research use). Zones are centroids joined by connectors.

The reference model is solved here with the package's own Frank-Wolfe solver (about a minute).
For a tighter equilibrium, solve it with TAPLab, TAPLite/DTALite or Path4GMNS and cut their
route_assignment.csv with subarea4gmns.extract_from_routes.
"""
import argparse
import csv
import json
import time
import urllib.request
from pathlib import Path

import numpy as np

from subarea4gmns import check, extract, read_demand, read_network, select_nodes, write_csv, write_demand

HERE = Path(__file__).resolve().parent
DATA, OUT = HERE / "data", HERE / "out"
RAW = "https://raw.githubusercontent.com/asu-trans-ai-lab/TAPLab/main/tapbench/chicago_sketch/"
FILES = {"node.csv": "node.csv", "link.csv": "link.csv", "demand.csv": "demand.csv",
         "best_known_link_performance.csv": "reference/link_performance.csv"}
BBOX = (-87.85, 41.75, -87.55, 42.00)          # central Chicago

ap = argparse.ArgumentParser()
ap.add_argument("--iterations", type=int, default=60)
a = ap.parse_args()

DATA.mkdir(exist_ok=True)
for local, remote in FILES.items():
    if not (DATA / local).exists():
        print("downloading", remote)
        urllib.request.urlretrieve(RAW + remote, DATA / local)

net = read_network(DATA)
od = read_demand(DATA / "demand.csv")
print("reference model: %d nodes, %d links, %d zones, %d OD pairs, %.0f trips"
      % (net.n_nodes, net.n_links, len(net.zone_of), len(od), sum(od.values())))
t0 = time.time()
inside = select_nodes(net, bbox=BBOX)
sod, summary, res = extract(net, od, inside, OUT / "subarea", iterations=a.iterations, gap=1e-6)
best = {(r["from_node_id"], r["to_node_id"]): float(r["volume"])
        for r in csv.DictReader(open(DATA / "best_known_link_performance.csv"))}
bk = np.array([best[(net.node_ids[t], net.node_ids[h])] for t, h in zip(net.tail, net.head)])
summary["reference_vs_best_known_RMSE"] = round(float(np.sqrt(np.mean((res.volume - bk) ** 2))), 2)
summary["best_known_mean_flow"] = round(float(bk.mean()), 1)
print("reference run: %.0f s, relative gap %.1e, RMSE against best-known flows %.1f (mean flow %.0f)"
      % (time.time() - t0, res.gap, summary["reference_vs_best_known_RMSE"], bk.mean()))
print("subarea: %(nodes)d nodes, %(links)d links, %(internal_zones)d zones inside, %(boundary_zones)d boundary zones" % summary)
write_demand(sod, OUT / "subarea" / "demand.csv")
print("subarea trip table: %d OD pairs, %.0f trips" % (len(sod), sum(sod.values())))
s, rows = check(OUT / "subarea", sod, iterations=200, gap=1e-6)
write_csv(rows, OUT / "subarea" / "check_links.csv")
summary["check"] = s
(OUT / "summary.json").write_text(json.dumps(summary, indent=1))
print("check: VMT %(VMT).0f vs %(VMT_ref).0f (%(VMT_diff_pct)+.3f%%), VHT %(VHT).0f vs %(VHT_ref).0f "
      "(%(VHT_diff_pct)+.3f%%), link WAPE %(link_WAPE_pct).3f%%, R2 %(link_R2).5f" % s)
