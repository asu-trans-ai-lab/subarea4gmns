from pathlib import Path

import numpy as np
import pytest

from subarea4gmns import (assign, check, extract, read_demand, read_network, rebuild, select_nodes)

ROOT = Path(__file__).resolve().parents[1]
SF = ROOT / "examples" / "sioux_falls" / "data"
CORRIDOR = ROOT / "examples" / "corridor" / "data"


def two_route(tmp_path):
    """Two parallel routes, one origin and one destination: an equilibrium with a closed form."""
    (tmp_path / "node.csv").write_text(
        "node_id,zone_id,node_type,x_coord,y_coord\n1,1,centroid,0,0\n2,2,centroid,1,0\n3,,,0.5,1\n")
    (tmp_path / "link.csv").write_text(
        "link_id,from_node_id,to_node_id,link_type,length,capacity,free_speed,vdf_fftt,vdf_alpha,vdf_beta\n"
        "1,1,2,connector,1,1000,60,10,0.15,4\n"
        "2,1,3,connector,1,1000,60,6,0.15,4\n"
        "3,3,2,connector,1,1000,60,6,0.15,4\n")
    return tmp_path


def test_two_route_equilibrium(tmp_path):
    net = read_network(two_route(tmp_path))
    res = assign(net, {("1", "2"): 2000.0}, iterations=500, gap=1e-10)
    t = res.time
    assert res.unassigned == 0
    assert abs(res.volume[0] + res.volume[1] - 2000.0) < 1e-6
    assert abs(t[0] - (t[1] + t[2])) / t[0] < 1e-3          # equal travel time on both routes


def test_corridor_rebuild_exact():
    od, rep = rebuild(CORRIDOR)
    assert rep["explained_pct"] == pytest.approx(100.0)
    assert rep["unbalanced_nodes"] == []
    assert od[("101", "104")] == pytest.approx(400.0)
    s, _ = check(CORRIDOR, od)
    assert s["max_abs_link_diff"] < 1e-6


def test_rebuild_refuses_zones_on_through_nodes(tmp_path):
    net = read_network(SF)
    od = read_demand(SF / "demand.csv")
    extract(net, od, select_nodes(net, node_ids=["10", "11", "15", "16"]), tmp_path, iterations=20)
    with pytest.raises(ValueError):
        rebuild(tmp_path)


def test_sioux_falls_extract_reproduces_reference(tmp_path):
    net = read_network(SF)
    od = read_demand(SF / "demand.csv")
    inside = select_nodes(net, node_ids=["8", "9", "10", "11", "14", "15", "16", "17", "22", "23"])
    sod, summary, res = extract(net, od, inside, tmp_path, iterations=200, gap=1e-6)
    assert summary["boundary_zones"] == 8 and summary["internal_zones"] == 10
    # loading the extracted pieces reproduces the reference flow, so trips are conserved per zone
    sub = read_network(tmp_path)
    ref = sub.column("ref_volume")
    out_of = {z: ref[sub.tail == i].sum() for i, z in sub.zone_of.items() if i in sub.blocked}
    produced = {z: sum(v for (o, d), v in sod.items() if o == z) for z in out_of}
    for z in out_of:
        assert produced[z] == pytest.approx(out_of[z], rel=1e-6, abs=1e-6)
    s, _ = check(tmp_path, sod, iterations=200, gap=1e-6)
    assert abs(s["VMT_diff_pct"]) < 0.1
    assert s["link_WAPE_pct"] < 1.0


def test_units(tmp_path):
    (tmp_path / "node.csv").write_text("node_id,zone_id,node_type\n1,1,centroid\n2,2,centroid\n")
    (tmp_path / "link.csv").write_text(
        "link_id,from_node_id,to_node_id,link_type,length,lanes,capacity,free_speed\n1,1,2,connector,1609.344,2,1800,60\n")
    net = read_network(tmp_path, length_unit="m", speed_unit="kph", capacity_per_lane=True)
    assert net.length[0] == pytest.approx(1.0)
    assert net.cap[0] == pytest.approx(3600.0)
    assert net.fftt[0] == pytest.approx(60.0 / (60 / 1.609344))


def test_extract_from_routes_matches_extract(tmp_path):
    """Cutting a route file gives the same subarea trips as cutting the solver's own paths."""
    from subarea4gmns import extract_from_routes
    net = read_network(CORRIDOR)
    # the corridor's four movements as routes over the whole corridor network
    routes = tmp_path / "route_assignment.csv"
    routes.write_text(
        "o_zone_id,d_zone_id,volume,node_sequence\n"
        "101,103,600,101;1;2;3;4;103\n"
        "101,104,400,101;1;2;3;104\n"
        "102,103,300,102;2;3;4;103\n"
        "105,103,70,105;1;2;3;4;103\n")
    inside = select_nodes(net, node_ids=["2", "3"])
    ref = net.column("ref_volume")
    od, summary = extract_from_routes(net, routes, inside, ref, tmp_path / "sub")
    assert sum(od.values()) == pytest.approx(1370.0)       # everything on link 2 -> 3
    assert summary["boundary_zones"] == 2                  # one per edge node: 2 and 3
    s, _ = check(tmp_path / "sub", od)
    assert s["max_abs_link_diff"] < 1e-6
