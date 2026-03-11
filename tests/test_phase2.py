"""Phase 2 unit tests for Graph and Dijkstra."""

import sys
sys.path.insert(0, ".")

from routing.core.graph import Graph
from routing.core.dijkstra import Dijkstra
from routing.utils import format_cost


def test_undirected_edges():
    g = Graph()
    g.add_edge("A", "B", 5.0)
    assert g.get_cost("A", "B") == 5.0
    assert g.get_cost("B", "A") == 5.0
    g.set_edge_cost("A", "B", 3.0)
    assert g.get_cost("A", "B") == 3.0
    assert g.get_cost("B", "A") == 3.0
    print("PASS: undirected edges")


def test_remove_node():
    g = Graph()
    g.add_edge("A", "B", 1.0)
    g.add_edge("B", "C", 2.0)
    g.remove_node("B")
    assert not g.has_node("B")
    assert g.get_neighbours("A") == {}
    assert g.get_neighbours("C") == {}
    print("PASS: remove node cleans all edges")


def test_dijkstra_simple():
    g = Graph()
    g.add_edge("A", "B", 5.0)
    g.add_edge("A", "C", 10.0)
    g.add_edge("B", "C", 3.0)
    routes = Dijkstra.compute(g, "A")
    assert routes["B"] == (5.0, "AB")
    assert routes["C"] == (8.0, "ABC")
    print("PASS: Dijkstra multi-hop shortest path")


def test_dijkstra_alphabetical_tiebreak():
    g = Graph()
    g.add_edge("A", "B", 1.0)
    g.add_edge("A", "C", 1.0)
    g.add_edge("B", "D", 1.0)
    g.add_edge("C", "D", 1.0)
    routes = Dijkstra.compute(g, "A")
    assert routes["D"][0] == 2.0
    assert routes["D"][1] == "ABD", f"Expected ABD, got {routes['D'][1]}"
    print("PASS: Dijkstra alphabetical tiebreak")


def test_cycle_detect():
    g = Graph()
    g.add_edge("A", "B", 1.0)
    g.add_edge("B", "C", 1.0)
    assert not g.detect_cycle(), "Tree should have no cycle"
    g.add_edge("C", "A", 1.0)
    assert g.detect_cycle(), "Triangle should have cycle"
    print("PASS: cycle detection")


def test_component():
    g = Graph()
    g.add_edge("A", "B", 1.0)
    g.add_edge("C", "D", 1.0)
    assert g.get_component("A") == {"A", "B"}
    assert g.get_component("C") == {"C", "D"}
    print("PASS: connected components")


def test_format_cost():
    assert format_cost(5.0) == "5.0"
    assert format_cost(7.2) == "7.2"
    assert format_cost(0.0) == "0.0"
    assert format_cost(3.14159) == "3.1416"
    assert format_cost(2.30) == "2.3"
    assert format_cost(10.1000) == "10.1"
    print("PASS: format_cost")


def test_graph_copy():
    g = Graph()
    g.add_edge("A", "B", 5.0)
    g.set_port("A", 6000)
    g2 = g.copy()
    g2.set_edge_cost("A", "B", 99.0)
    assert g.get_cost("A", "B") == 5.0, "Original should not change"
    assert g2.get_cost("A", "B") == 99.0
    print("PASS: graph copy is independent")


if __name__ == "__main__":
    test_undirected_edges()
    test_remove_node()
    test_dijkstra_simple()
    test_dijkstra_alphabetical_tiebreak()
    test_cycle_detect()
    test_component()
    test_format_cost()
    test_graph_copy()
    print("\nAll Phase 2 tests passed!")
