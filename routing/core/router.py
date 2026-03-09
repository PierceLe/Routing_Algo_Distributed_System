"""Shortest-path computation using Dijkstra's algorithm."""

import heapq


class Router:
    """Stateless helper that runs Dijkstra on a Graph."""

    @staticmethod
    def compute_shortest_paths(graph, source):
        """Return {dest: (cost, path_str)} for every reachable node.

        *path_str* is the concatenation of node IDs along the path
        (e.g. ``"ABCD"``).  Ties are broken alphabetically via the
        ``(distance, node_id)`` heap key.
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
                if new_dist < dist[v]:
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
