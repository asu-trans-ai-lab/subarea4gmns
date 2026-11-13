# OpenStreetMap: network, synthetic trips, subarea

```bash
pip install osm2gmns grid2demand
python run_example.py map.osm
```

1. [osm2gmns](https://github.com/asu-trans-ai-lab/OSM2GMNS) builds the driving network from an OpenStreetMap extract.
2. [grid2demand](https://github.com/asu-trans-ai-lab/grid2demand) builds grid zones and a gravity-model trip table from points of interest.
3. `subarea4gmns` attaches a centroid to each zone and solves the reference model.
4. It then cuts the middle third of the network, extracts the subarea trip table and checks it.

**Getting `map.osm`.** Export any small area from https://www.openstreetmap.org/export. The tested area is the ASU Tempe campus: longitude −111.9424 to −111.9224, latitude 33.4127 to 33.4312. Map data © OpenStreetMap contributors, ODbL.

**Options.**

- `--cell 0.5`: grid zone size in km.
- `--bbox XMIN YMIN XMAX YMAX`: subarea bounding box.
- `--out out`: output folder.

**Tested result (ASU Tempe campus):**

| | Value |
|---|---|
| Network | 512 nodes, 886 links |
| Synthetic demand | 55 zones, 2,970 OD pairs, 80,866 trips |
| Subarea | 190 nodes, 330 links, 39 zones; 629 OD pairs |
| Check | VMT −0.02%, VHT −0.10%, link WAPE 0.21% |

Synthetic trips depend on the point-of-interest data and grid2demand's default trip rates. They are a starting point for a study, not observed demand.
