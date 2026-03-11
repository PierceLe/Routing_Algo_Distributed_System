"""Optional bonus commands: MERGE, SPLIT, CYCLE DETECT.

MERGE <A> <B>: absorb node B into node A (edges with lower cost win).
SPLIT: partition graph into two halves alphabetically, remove cross-edges.
CYCLE DETECT: report whether the graph contains a cycle.
"""

from .base import Command
from ..core.dijkstra import Dijkstra


class MergeCommand(Command):
    """Merge the subgraph of node_id2 into node_id1."""

    def __init__(self, node_id1, node_id2):
        self.node_id1 = node_id1
        self.node_id2 = node_id2

    def execute(self, node):
        with node.lock:
            out_neighbours = node.graph.get_neighbours(self.node_id2)

            for nid, cost in out_neighbours.items():
                if nid == self.node_id1:
                    continue
                existing = node.graph.get_cost(self.node_id1, nid)
                if existing is None or cost < existing:
                    node.graph.add_edge(self.node_id1, nid, cost)

            node.graph.remove_node(self.node_id2)
            node.merged_away_nodes.add(self.node_id2)

            if self.node_id2 in node.immediate_neighbours:
                node.immediate_neighbours.discard(self.node_id2)
                if node.node_id == self.node_id1:
                    for nid in out_neighbours:
                        if nid != self.node_id1 and nid != node.node_id:
                            node.immediate_neighbours.add(nid)
                else:
                    node.immediate_neighbours.add(self.node_id1)

            node.has_changes = True

            if not node.suppress_routing_output:
                filtered = node.get_filtered_graph()
                routes = Dijkstra.compute(filtered, node.node_id)
                node.last_routing_table = routes
            else:
                routes = None

        node.safe_print("Graph merged successfully.")
        if routes is not None:
            node._output_routing_table(routes)
        node.immediate_broadcast()


class SplitCommand(Command):
    """Partition the graph into two halves alphabetically."""

    def execute(self, node):
        with node.lock:
            all_nodes = sorted(node.graph.get_nodes())
            k = len(all_nodes) // 2
            v1 = set(all_nodes[:k])
            v2 = set(all_nodes[k:])

            edges_to_remove = []
            for u in v1:
                for v in node.graph.get_neighbours(u):
                    if v in v2:
                        edges_to_remove.append((u, v))

            for u, v in edges_to_remove:
                node.graph.remove_edge(u, v)

            my_partition = v1 if node.node_id in v1 else v2
            other_partition = v2 if my_partition is v1 else v1
            node.immediate_neighbours -= other_partition
            node.split_my_partition = my_partition

            node.has_changes = True

            if not node.suppress_routing_output:
                filtered = node.get_filtered_graph()
                routes = Dijkstra.compute(filtered, node.node_id)
                node.last_routing_table = routes
            else:
                routes = None

        node.safe_print("Graph partitioned successfully.")
        if routes is not None:
            node._output_routing_table(routes)
        node.immediate_broadcast()


class CycleDetectCommand(Command):
    """Check whether the current graph contains a cycle."""

    def execute(self, node):
        with node.lock:
            has_cycle = node.graph.detect_cycle()
        if has_cycle:
            node.safe_print("Cycle detected.")
        else:
            node.safe_print("No cycle found.")
