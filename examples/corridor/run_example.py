"""Corridor: trip table from link volumes alone (no reference trip table or paths).

    python run_example.py

data/ is a small corridor (the one in docs/demo.html): two entries E1 and E2, two exits X1 and
X2, and a zone Z beside the corridor, all centroids with connectors; link.csv carries the
reference volume of every link in ref_volume. The rebuild splits those volumes into trip
movements; the check assigns them and compares.
"""
import json
from pathlib import Path

from subarea4gmns import check, rebuild, write_demand

HERE = Path(__file__).resolve().parent
od, rep = rebuild(HERE / "data")
write_demand(od, HERE / "demand_rebuilt.csv")
print("rebuilt trip table (%.1f%% of the reference volume explained):" % rep["explained_pct"])
for (o, d), v in sorted(od.items(), key=lambda kv: -kv[1]):
    print("  %s -> %s  %.0f" % (o, d, v))
s, _ = check(HERE / "data", od)
print(json.dumps({k: s[k] for k in ("VMT", "VMT_ref", "link_WAPE_pct", "max_abs_link_diff")}, indent=1))
print("Zone Z shows a net 70 trips leaving: trips into and out of Z through one access node "
      "cannot be told apart from link volumes alone.")
