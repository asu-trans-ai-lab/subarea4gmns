# Changelog

## 0.1.0 (2026-11-13)

First release.

- `cut`: subarea by bounding box or node list, with a boundary centroid at every edge crossing.
- `extract`: path-based subarea trip table from a reference model; exact against the equilibrium.
- `extract_from_routes`: the same, from a solver's route file.
- `rebuild`: subarea trip table from link volumes alone (corridor cuts).
- `assign`: static user equilibrium (Frank-Wolfe, BPR); `check`: VMT, VHT and link volumes against the reference.
- `zones.add_centroids`: attach grid2demand zones to an OpenStreetMap network.
- Examples: Sioux Falls, Chicago Sketch, OpenStreetMap (osm2gmns + grid2demand), corridor.
