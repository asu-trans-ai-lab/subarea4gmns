"""OpenStreetMap -> GMNS network -> synthetic trips -> reference model -> subarea -> check.

    pip install osm2gmns grid2demand
    python run_example.py map.osm [--bbox XMIN YMIN XMAX YMAX] [--cell 0.5]

map.osm: any OpenStreetMap extract, for example from https://www.openstreetmap.org/export
(map data (c) OpenStreetMap contributors, ODbL). Without --bbox the subarea is the middle
third of the network in each direction.

Steps
  1 osm2gmns builds the driving network (length in meters, speed in km/h, capacity per link)
  2 grid2demand builds grid zones (--cell km) and a gravity-model trip table from points of interest
  3 subarea4gmns attaches a centroid to each zone and solves the reference model
  4 cut the subarea, extract its trip table, assign it and compare with the reference
"""
import argparse
import json
import sys
from pathlib import Path

import osm2gmns as og
import grid2demand as gd

from subarea4gmns import extract, check, read_demand, read_network, select_nodes, write_demand
from subarea4gmns.zones import add_centroids

ap = argparse.ArgumentParser()
ap.add_argument("osm")
ap.add_argument("--bbox", type=float, nargs=4)
ap.add_argument("--cell", type=float, default=0.5, help="grid zone size, km")
ap.add_argument("--out", default="out")
a = ap.parse_args()
out = Path(a.out)
(out / "network").mkdir(parents=True, exist_ok=True)
(out / "demand").mkdir(parents=True, exist_ok=True)

print("1 network from OpenStreetMap")
net = og.getNetFromFile(a.osm, mode_types="auto", POI=True)
og.consolidateComplexIntersections(net, auto_identify=True)
og.fillLinkAttributesWithDefaultValues(net, default_lanes=True, default_speed=True, default_capacity=True)
og.generateNodeActivityInfo(net)
og.outputNetToCSV(net, str(out / "network"))

print("2 synthetic trips (grid2demand)")
g = gd.GRID2DEMAND(input_dir=str(out / "network"), output_dir=str(out / "demand"), mode_type="auto")
g.load_network()
g.net2grid(cell_width=a.cell, cell_height=a.cell, unit="km")
g.taz2zone()
g.map_zone_node_poi()
g.calc_zone_od_distance()
g.run_gravity_model()
g.save_results_to_csv()
od = read_demand(out / "demand" / "demand.csv")

print("3 reference model")
n = add_centroids(out / "network", out / "demand" / "zone.csv", out / "reference", demand=od,
                  length_unit="m", connector_speed=40)
units = dict(length_unit="m", speed_unit="kph", capacity_per_lane=False)
ref = read_network(out / "reference", **units)
write_demand(od, out / "reference" / "demand.csv")
print("   %d nodes, %d links, %d zones, %d OD pairs, %.0f trips" % (ref.n_nodes, ref.n_links, n, len(od), sum(od.values())))

if a.bbox:
    bbox = a.bbox
else:
    xs = [float(r["x_coord"]) for r in ref.node_rows]
    ys = [float(r["y_coord"]) for r in ref.node_rows]
    dx, dy = (max(xs) - min(xs)) / 3, (max(ys) - min(ys)) / 3
    bbox = (min(xs) + dx, min(ys) + dy, max(xs) - dx, max(ys) - dy)

print("4 subarea", [round(v, 5) for v in bbox])
inside = select_nodes(ref, bbox=bbox)
sod, summary, res = extract(ref, od, inside, out / "subarea", hours=1.0, iterations=300)
write_demand(sod, out / "subarea" / "demand.csv")
print("   reference relative gap %.2e, demand without a path %.1f" % (res.gap, res.unassigned))
s, _ = check(out / "subarea", sod, **units)
summary.update(check=s)
(out / "summary.json").write_text(json.dumps(summary, indent=1))
print(json.dumps(s, indent=1))
sys.exit(0)
