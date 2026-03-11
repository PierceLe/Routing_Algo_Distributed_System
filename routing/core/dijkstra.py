"""Shortest-path computation using Dijkstra's algorithm.

Implements the Strategy pattern: the routing algorithm is a pluggable
component that can be swapped (e.g. to Bellman-Ford) without changing
the rest of the system.
"""

import heapq


class Dijkstra:
    """Stateless shortest-path calculator.

    Computes single-source shortest paths on a Graph.
    Ties at equal cost are broken alphabetically by node ID.
    """

    @staticmethod
    def compute(graph, source):
        """Return {dest: (cost, path_str)} for every reachable node.

        path_str is the concatenated node IDs (e.g. "ABCD").
        The source node itself is excluded from the results.
        """
        nodes = graph.get_nodes()
        if source not in nodes:
            return {}

        dist = {n: float("inf") for n in nodes}
        prev = {n: None for n in nodes}
        dist[source] = 0.0

        pq = [(0.0, source)]
        visited = set()

        while pq:
            d, u = heapq.heappop(pq)
            if u in visited:
                continue
            visited.add(u)
            for v, cost in graph.get_neighbours(u).items():
                if v in visited:
                    continue
                new_dist = d + cost
                if new_dist < dist[v] or (
                    new_dist == dist[v] and u < (prev[v] or "")
                ):
                    dist[v] = new_dist
                    prev[v] = u
                    heapq.heappush(pq, (new_dist, v))

        results = {}
        for dest in sorted(nodes):
            if dest == source or dist[dest] == float("inf"):
                continue
            path = []
            cur = dest
            while cur is not None:
                path.append(cur)
                cur = prev[cur]
            path.reverse()
            results[dest] = (dist[dest], "".join(path))

        return results
