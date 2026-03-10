"""Required dynamic commands: CHANGE, FAIL, RECOVER, QUERY, QUERY PATH,
RESET, and BATCH UPDATE."""

from .base import Command
from ..core.router import Router
from ..utils import format_cost, error_exit


class ChangeCommand(Command):
    def __init__(self, neighbour_id, new_cost):
        self.neighbour_id = neighbour_id
        self.new_cost = new_cost

    def execute(self, node):
        with node.lock:
            node.graph.set_edge_cost(node.node_id, self.neighbour_id, self.new_cost)
            node.has_changes = True
            node.seq_num += 1
        node.immediate_broadcast()
        node.compute_and_output_routing_table(force=True)


class FailCommand(Command):
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
    def __init__(self, destination):
        self.destination = destination

    def execute(self, node):
        with node.lock:
            filtered = node.get_filtered_graph()
            routes = Router.compute_shortest_paths(filtered, node.node_id)
        if self.destination in routes:
            cost, path = routes[self.destination]
            node.safe_print(
                f"Least cost path from {node.node_id} to "
                f"{self.destination}: {path}, link cost: "
                f"{format_cost(cost)}"
            )


class QueryPathCommand(Command):
    def __init__(self, source, destination):
        self.source = source
        self.destination = destination

    def execute(self, node):
        with node.lock:
            filtered = node.get_filtered_graph()
            routes = Router.compute_shortest_paths(filtered, self.source)
        if self.destination in routes:
            cost, path = routes[self.destination]
            node.safe_print(
                f"Least cost path from {self.source} to "
                f"{self.destination}: {path}, link cost: "
                f"{format_cost(cost)}"
            )


class ResetCommand(Command):
    def execute(self, node):
        with node.lock:
            node.graph = node.create_initial_graph()
            node.immediate_neighbours = {nid for nid, _, _ in node.original_neighbours}
            node.failed_nodes.clear()
            node.split_my_partition = None
            node.merged_away_nodes.clear()
            node.is_up = True
            node.has_changes = True
            node.seq_num += 1
        node.immediate_broadcast()
        node.safe_print(f"Node {node.node_id} has been reset.")
        node.compute_and_output_routing_table(force=True)


class BatchUpdateCommand(Command):
    def __init__(self, filename):
        self.filename = filename

    def execute(self, node):
        try:
            with open(self.filename, "r") as fh:
                lines = fh.readlines()
        except FileNotFoundError:
            error_exit(f"Error: Batch file {self.filename} not found.")

        prev = node.suppress_routing_output
        node.suppress_routing_output = True
        for line in lines:
            line = line.strip()
            if line:
                node.process_input(line)
        node.suppress_routing_output = prev

        node.safe_print("Batch update complete.")
        node.compute_and_output_routing_table(force=True)
