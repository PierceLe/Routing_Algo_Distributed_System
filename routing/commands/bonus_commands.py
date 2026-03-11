"""Optional bonus commands: MERGE, SPLIT, CYCLE DETECT.

MERGE <A> <B>: absorb node B into node A (edges with lower cost win).
SPLIT: partition graph into two halves alphabetically, remove cross-edges.
CYCLE DETECT: report whether the graph contains a cycle.
"""

from .base import Command
from ..core.dijkstra import Dijkstra
from ..network.protocol import Protocol


class MergeCommand(Command):
    """Merge the subgraph of node_id2 into node_id1."""

    def __init__(self, node_id1, node_id2):
        self.node_id1 = node_id1
        self.node_id2 = node_id2

    def execute(self, node):
        # absorbed node still prints its own table, but informs others
        if node.node_id == self.node_id2:
            node.safe_print("Graph merged successfully.")
            node.compute_and_output_routing_table(force=True)
            node.broadcast_merged_into({self.node_id2: self.node_id1})
            return

        with node.lock:
            # 1) Redirect outgoing edges: B -> X  becomes  A -> X
            out_neighbours = node.graph.get_neighbours(self.node_id2)
            for nid, cost in out_neighbours.items():
                if nid == self.node_id1:
                    continue
                existing = node.graph.get_cost(self.node_id1, nid)
                if existing is None or cost < existing:
                    node.graph.add_edge(self.node_id1, nid, cost)

            # 2) Redirect incoming edges: X -> B  becomes  X -> A
            for src in list(node.graph.get_nodes()):
                if src == self.node_id1 or src == self.node_id2:
                    continue
                incoming_cost = node.graph.get_cost(src, self.node_id2)
                if incoming_cost is None:
                    continue

                existing = node.graph.get_cost(src, self.node_id1)
                if existing is None or incoming_cost < existing:
                    node.graph.add_edge(src, self.node_id1, incoming_cost)

            # 3) Remove absorbed node completely
            node.graph.remove_node(self.node_id2)
            node.merged_away_nodes.add(self.node_id2)

            # 4) Update immediate neighbours
            if self.node_id2 in node.immediate_neighbours:
                node.immediate_neighbours.discard(self.node_id2)

            if node.node_id == self.node_id1:
                # absorber inherits absorbed node's outgoing neighbours
                for nid in out_neighbours:
                    if nid != self.node_id1 and nid != node.node_id:
                        node.immediate_neighbours.add(nid)
            else:
                # other nodes should now point to node_id1 instead of node_id2 if needed
                if node.graph.get_cost(node.node_id, self.node_id1) is not None:
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
        node.broadcast_merged_into({self.node_id2: self.node_id1})


class SplitCommand(Command):
    """Partition the graph into two halves alphabetically."""

    def execute(self, node):
        with node.lock:
            # Broadcast a one-off SPLIT notification to all current
            # immediate neighbours (including those that will be cut
            # by the partition), so the split propagates across the
            # connected component.
            original_neighbours = list(node.immediate_neighbours)
            split_payload = Protocol.serialize_topology(
                node.node_id,
                node.graph,
                node.failed_nodes,
                merged_nodes=node.merged_away_nodes,
                merged_into={},
                split=True,
            )
            for nid in original_neighbours:
                if nid not in node.failed_nodes:
                    port = node.graph.get_port(nid)
                    if port is not None:
                        node._socket.send(split_payload, port)

            changed = node._apply_split_partition()

            if changed:
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
