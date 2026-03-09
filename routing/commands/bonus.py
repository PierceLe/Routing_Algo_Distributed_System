"""Optional bonus commands: MERGE, SPLIT, CYCLE DETECT."""

from .base import Command


class MergeCommand(Command):
    def __init__(self, node_id1, node_id2):
        self.node_id1 = node_id1
        self.node_id2 = node_id2

    def execute(self, node):
        with node.lock:
            neighbours2 = node.graph.get_neighbours(self.node_id2)
            for nid, cost in neighbours2.items():
                if nid == self.node_id1:
                    continue
                existing = node.graph.get_cost(self.node_id1, nid)
                if existing is None or cost < existing:
                    node.graph.add_edge(self.node_id1, nid, cost)
            node.graph.remove_node(self.node_id2)
            node.has_changes = True
        node.safe_print("Graph merged successfully.")
        node.compute_and_output_routing_table(force=True)


class SplitCommand(Command):
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
            node.has_changes = True
        node.safe_print("Graph partitioned successfully.")
        node.compute_and_output_routing_table(force=True)


class CycleDetectCommand(Command):
    def execute(self, node):
        with node.lock:
            has_cycle = node.graph.detect_cycle()
        if has_cycle:
            node.safe_print("Cycle detected.")
        else:
            node.safe_print("No cycle found.")
