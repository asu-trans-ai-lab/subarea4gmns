# Sioux Falls

```bash
python run_example.py
```

1. Solves the reference model: user equilibrium on the full network.
2. Cuts the 10-node subarea in the middle of the network: nodes 8–11, 14–17, 22 and 23.
3. Extracts its trip table.
4. Assigns the trip table on the subarea and compares with the reference link volumes.

Outputs go to `out/`: the subarea `node.csv`, `link.csv`, `zone.csv`, `demand.csv` and `check_links.csv`, plus `summary.json`.

| | Value |
|---|---|
| Reference model | 24 nodes, 76 links, 24 zones (every node a zone, carrying through traffic), 360,600 trips |
| Subarea | 10 nodes, 26 links; 10 zones inside, 8 boundary zones; 195 OD pairs |
| Check | VMT +0.009%, VHT +0.02%, link WAPE 0.12%, R² 0.99999 |

**Data:** `data/` comes from [TAPLab](https://github.com/asu-trans-ai-lab/TAPLab) TAPBench, originally TNTP TransportationNetworks (LeBlanc, Morlok and Pierskalla, 1975), for research use. `best_known_link_performance.csv` holds the best-known equilibrium flows.

The package's Frank-Wolfe solver reaches a relative gap of about 5e-4 here, with RMSE 559 against those flows (mean flow 11,639). For a tighter reference solution, use TAPLab.
