# Chicago Sketch

```bash
python run_example.py              # the first run downloads the network from TAPLab
```

The reference model has 933 nodes, 2,950 links, 387 centroid zones and 1.14 million trips. The subarea is central Chicago, bounding box (−87.85, 41.75, −87.55, 42.00).

| | Value |
|---|---|
| Reference run | 60 Frank-Wolfe iterations, about 1 minute; relative gap 1.5e-4; RMSE 27 against the best-known flows (mean flow 2,399) |
| Subarea | 98 nodes, 308 links; 37 zones inside, 21 boundary zones; 2,778 OD pairs, 436,825 trips |
| Check | VMT −0.015%, VHT +0.03%, link WAPE 0.39%, R² 0.99992 |

**Data:** [TAPLab](https://github.com/asu-trans-ai-lab/TAPLab) TAPBench, originally TNTP TransportationNetworks (Eash, Chon, Lee and Boyce, 1979), for research use. It is downloaded on first run and not stored in this repository.

**Using another solver.** To solve the reference model with TAPLab, TAPLite/DTALite or Path4GMNS, cut that solver's route file instead:

```python
from subarea4gmns import extract_from_routes
od, summary = extract_from_routes(net, "route_assignment.csv", inside, ref_volume, "out/subarea")
```
