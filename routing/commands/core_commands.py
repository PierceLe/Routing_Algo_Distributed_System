"""Core dynamic commands: CHANGE, FAIL, RECOVER, QUERY, QUERY PATH,
RESET, and BATCH UPDATE.

Each command follows the Command pattern: encapsulates parameters
and implements execute(node).
"""

from .base import Command
from ..core.dijkstra import Dijkstra
from ..utils import format_cost, error_exit


class ChangeCommand(Command):
    """Update the cost of an existing edge to a neighbour."""

    def __init__(self, neighbour_id, new_cost):
        self.neighbour_id = neighbour_id
        self.new_cost = new_cost

    def execute(self, node):
        with node.lock:
            node.graph.set_edge_cost(node.node_id, self.neighbour_id,
                                     self.new_cost)
            node.has_changes = True
        node.immediate_broadcast()
        node.compute_and_output_routing_table(force=True)


class FailCommand(Command):
    """Mark a node as failed (DOWN)."""

    def __init__(self, target_id):
        self.target_id = target_id

    def execute(self, node):
        if self.target_id == node.node_id:
            with node.lock:
                node.is_up = False
            node.safe_print(f"Node {self.target_id} is now DOWN.")
        else:
            with node.lock:
                node.failed_nodes.add(self.target_id)
                if node.graph.has_edge(node.node_id, self.target_id):
                    node.has_changes = True
            node.compute_and_output_routing_table(force=True)


class RecoverCommand(Command):
    """Mark a node as recovered (UP)."""

    def __init__(self, target_id):
        self.target_id = target_id

    def execute(self, node):
        if self.target_id == node.node_id:
            with node.lock:
                node.is_up = True
                node.has_changes = True
            node.safe_print(f"Node {self.target_id} is now UP.")
        else:
            with node.lock:
                node.failed_nodes.discard(self.target_id)
                if node.graph.has_edge(node.node_id, self.target_id):
                    node.has_changes = True
            node.compute_and_output_routing_table(force=True)


class QueryCommand(Command):
    """Output the least-cost path from this node to a destination."""

    def __init__(self, destination):
        self.destination = destination

    def execute(self, node):
        with node.lock:
            filtered = node.get_filtered_graph()
            routes = Dijkstra.compute(filtered, node.node_id)
        if self.destination in routes:
            cost, path = routes[self.destination]
            node.safe_print(
                f"Least cost path from {node.node_id} to "
                f"{self.destination}: {path}, link cost: "
                f"{format_cost(cost)}"
            )


class QueryPathCommand(Command):
    """Output the least-cost path between any two nodes."""

    def __init__(self, source, destination):
        self.source = source
        self.destination = destination

    def execute(self, node):
        with node.lock:
            filtered = node.get_filtered_graph()
            routes = Dijkstra.compute(filtered, self.source)
        if self.destination in routes:
            cost, path = routes[self.destination]
            node.safe_print(
                f"Least cost path from {self.source} to "
                f"{self.destination}: {path}, link cost: "
                f"{format_cost(cost)}"
            )


class ResetCommand(Command):
    """Reset the node's state to original configuration.

    Rebuilds the graph from scratch so that only the original
    neighbours from the config file are known (Section 5.5).
    """

    def execute(self, node):
        with node.lock:
            node.graph = node._build_initial_graph()
            node.immediate_neighbours = {
                nid for nid, _, _ in node.original_neighbours
            }
            node.failed_nodes.clear()
            node.merged_away_nodes.clear()
            node.merged_preferred_edges.clear()
            node.is_up = True
            node.has_changes = True

        node.immediate_broadcast()
        node.safe_print(f"Node {node.node_id} has been reset.")
        node.compute_and_output_routing_table(force=True)


class BatchUpdateCommand(Command):
    """Process a file of dynamic commands, then output the routing table."""

    def __init__(self, filename):
        self.filename = filename

    def execute(self, node):
        try:
            with open(self.filename, "r") as fh:
                lines = fh.readlines()
        except FileNotFoundError:
            error_exit(f"Error: Batch file {self.filename} not found.")

        prev_suppress = node.suppress_routing_output
        node.suppress_routing_output = True
        for line in lines:
            line = line.strip()
            if line:
                node.process_input(line)
        node.suppress_routing_output = prev_suppress

        node.safe_print("Batch update complete.")
        node.compute_and_output_routing_table(force=True)
