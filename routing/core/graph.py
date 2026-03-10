"""Directed weighted graph representing the network topology."""


class Graph:
    """Adjacency-list directed graph with per-node port metadata.

    Each edge u→v is stored only in ``_adj[u][v]``; there is no
    automatic reverse edge.
    """

    def __init__(self):
        self._adj = {}      # node_id -> {target_id: cost}
        self._ports = {}    # node_id -> port (int)

    # ── node operations ──────────────────────────────────────────

    def add_node(self, node_id, port=None):
        if node_id not in self._adj:
            self._adj[node_id] = {}
        if port is not None:
            self._ports[node_id] = port

    def remove_node(self, node_id):
        self._adj.pop(node_id, None)
        for nid in self._adj:
            self._adj[nid].pop(node_id, None)
        self._ports.pop(node_id, None)

    def has_node(self, node_id):
        return node_id in self._adj

    def get_nodes(self):
        return set(self._adj.keys())

    def get_port(self, node_id):
        return self._ports.get(node_id)

    def set_port(self, node_id, port):
        self._ports[node_id] = port

    # ── edge operations ──────────────────────────────────────────

    def add_edge(self, u, v, cost):
        """Add a **directed** edge u→v with the given *cost*."""
        self.add_node(u)
        self.add_node(v)
        self._adj[u][v] = cost

    def remove_edge(self, u, v):
        """Remove edges in **both** directions (u→v and v→u)."""
        if u in self._adj:
            self._adj[u].pop(v, None)
        if v in self._adj:
            self._adj[v].pop(u, None)

    def set_edge_cost(self, u, v, cost):
        """Update the cost of the directed edge u→v."""
        if u in self._adj and v in self._adj[u]:
            self._adj[u][v] = cost
            return True
        return False

    def has_edge(self, u, v):
        return u in self._adj and v in self._adj.get(u, {})

    def get_cost(self, u, v):
        return self._adj.get(u, {}).get(v, None)

    def get_neighbours(self, node_id):
        """Return a *copy* of the outgoing-neighbour dict {target: cost}."""
        return dict(self._adj.get(node_id, {}))

    # ── graph algorithms ─────────────────────────────────────────

    def detect_cycle(self):
        """Return True if the graph contains at least one directed cycle."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {n: WHITE for n in self._adj}
        for node in self._adj:
            if color[node] == WHITE:
                if self._dfs_has_cycle(node, color, WHITE, GRAY, BLACK):
                    return True
        return False

    def _dfs_has_cycle(self, node, color, WHITE, GRAY, BLACK):
        color[node] = GRAY
        for neighbour in self._adj.get(node, {}):
            if color[neighbour] == GRAY:
                return True
            if color[neighbour] == WHITE:
                if self._dfs_has_cycle(neighbour, color, WHITE, GRAY, BLACK):
                    return True
        color[node] = BLACK
        return False

    def get_component(self, node_id):
        """Return the set of nodes reachable from *node_id* via outgoing edges."""
        if node_id not in self._adj:
            return set()
        visited = set()
        stack = [node_id]
        while stack:
            n = stack.pop()
            if n in visited:
                continue
            visited.add(n)
            for neighbour in self._adj.get(n, {}):
                if neighbour not in visited:
                    stack.append(neighbour)
        return visited

    # ── copy ─────────────────────────────────────────────────────

    def copy(self):
        g = Graph()
        g._adj = {k: dict(v) for k, v in self._adj.items()}
        g._ports = dict(self._ports)
        return g
