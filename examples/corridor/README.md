# Corridor: trip table from link volumes alone

```bash
python run_example.py
```

`data/` is a four-link corridor, the same one stepped through in `docs/demo.html`:

- entries E1 (zone 101) and E2 (zone 102);
- exits X1 (zone 103) and X2 (zone 104);
- a side zone Z (zone 105).

All zones are centroids with connectors. `link.csv` carries the reference volume of every link.

`rebuild` splits the volumes into four movements:

| From | To | Trips |
|---|---|---:|
| E1 | X1 | 600 |
| E1 | X2 | 400 |
| E2 | X1 | 300 |
| Z | X1 | 70 |

Assigning them reproduces every link volume exactly. Z appears only as a net 70 trips: trips into and out of Z through one access node cannot be told apart from link volumes alone.
