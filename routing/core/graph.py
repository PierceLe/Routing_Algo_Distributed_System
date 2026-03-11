"""Undirected weighted graph representing the network topology.

The graph is simple (no self-loops, no parallel edges) and undirected:
every add_edge(u, v, cost) stores both u->v and v->u symmetrically.
"""


class Graph:
    __slots__ = ("_adj", "_ports")

    def __init__(self):
        self._adj = {}      # node_id -> {neighbour_id: cost}
        self._ports = {}    # node_id -> port (int)

    # ── node operations ──────────────────────────────────────────

    def add_node(self, node_id, port=None):
        if node_id not in self._adj:
            self._adj[node_id] = {}
        if port is not None:
            self._ports[node_id] = port

    def remove_node(self, node_id):
        neighbours = self._adj.pop(node_id, {})
        for nid in neighbours:
            if nid in self._adj:
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

    # ── edge operations (undirected) ─────────────────────────────

    def add_edge(self, u, v, cost):
        """Add an undirected edge {u, v} with the given cost."""
        self.add_node(u)
        self.add_node(v)
        self._adj[u][v] = cost
        self._adj[v][u] = cost

    def remove_edge(self, u, v):
        """Remove the undirected edge {u, v}."""
        if u in self._adj:
            self._adj[u].pop(v, None)
        if v in self._adj:
            self._adj[v].pop(u, None)

    def set_edge_cost(self, u, v, cost):
        """Update cost of existing undirected edge. Returns True if edge existed."""
        exists = (u in self._adj and v in self._adj.get(u, {}))
        if exists:
            self._adj[u][v] = cost
            self._adj[v][u] = cost
        return exists

    def has_edge(self, u, v):
        return u in self._adj and v in self._adj.get(u, {})

    def get_cost(self, u, v):
        return self._adj.get(u, {}).get(v, None)

    def get_neighbours(self, node_id):
        """Return a copy of the neighbour dict {neighbour_id: cost}."""
        return dict(self._adj.get(node_id, {}))

    # ── graph algorithms ─────────────────────────────────────────

    def detect_cycle(self):
        """Return True if the undirected graph contains at least one cycle.

        Uses DFS with parent tracking. An edge to an already-visited node
        that is not the parent indicates a cycle.
        """
        visited = set()
        for start in self._adj:
            if start not in visited:
                if self._dfs_cycle(start, None, visited):
                    return True
        return False

    def _dfs_cycle(self, node, parent, visited):
        visited.add(node)
        for neighbour in self._adj.get(node, {}):
            if neighbour not in visited:
                if self._dfs_cycle(neighbour, node, visited):
                    return True
            elif neighbour != parent:
                return True
        return False

    def get_component(self, node_id):
        """Return the set of all nodes reachable from node_id."""
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

    # ── bulk operations ─────────────────────────────────────────

    def clear(self):
        """Remove all nodes and edges."""
        self._adj.clear()
        self._ports.clear()

    # ── copy ─────────────────────────────────────────────────────

    def copy(self):
        g = Graph()
        g._adj = {k: dict(v) for k, v in self._adj.items()}
        g._ports = dict(self._ports)
        return g

    def __repr__(self):
        edges = set()
        for u, nbrs in self._adj.items():
            for v, c in nbrs.items():
                key = (min(u, v), max(u, v))
                edges.add((*key, c))
        return f"Graph(nodes={sorted(self._adj)}, edges={sorted(edges)})"
