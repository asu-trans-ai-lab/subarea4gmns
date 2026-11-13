"""subarea4gmns: build a subarea network and trip table from a reference model, and check them.

    from subarea4gmns import read_network, read_demand, select_nodes, extract, check

Workflow: reference network + trip table (an MPO model, or OpenStreetMap + synthetic demand)
-> cut a subarea -> extract its trip table -> assign it -> compare with the reference volumes.
"""
from .assign import assign, measures
from .check import check, compare
from .cut import cut, inside_links, select_nodes
from .extract import extract, extract_from_routes
from .gmns import read_demand, read_network, write_csv, write_demand
from .rebuild import rebuild

__version__ = "0.1.0"
__all__ = ["assign", "measures", "check", "compare", "cut", "inside_links", "select_nodes", "extract",
           "extract_from_routes", "read_demand", "read_network", "write_csv", "write_demand", "rebuild"]
