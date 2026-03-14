"""Node: the central orchestrator that owns the graph, threads, and I/O.

Thread Safety
-------------
All mutable state is protected by ``self.lock`` (an RLock).
Any code reading or writing these attributes must hold the lock:

    graph, immediate_neighbours, failed_nodes, is_up,
    has_changes, last_routing_table, suppress_routing_output,
    merged_away_nodes

Threading Model
---------------
Four threads as required by the spec:

1. **Main thread** — reads STDIN (Listening Thread, part 1)
2. **Socket listener** — reads UDP socket (Listening Thread, part 2)
3. **Sending thread** — periodic UPDATE broadcast every ``update_interval``
4. **Routing calculator** — event-driven via ``routing_event`` (no polling)

Synchronisation Primitives
--------------------------
- ``lock`` (RLock): protects all shared mutable state
- ``routing_event`` (Event): signals routing thread to recompute
- ``_print_lock`` (Lock): serialises multi-line STDOUT output

No hardcoded sleep/buffer times. The only sleeps use CLI-provided
``routing_delay`` and ``update_interval``.
"""

import sys
import threading
import time

from .graph import Graph
from .dijkstra import Dijkstra
from ..network.protocol import Protocol
from ..network.udp_socket import UDPSocket
from ..utils import format_cost, error_exit


class Node:

    def __init__(self, node_id, port, config_file, original_neighbours,
                 routing_delay, update_interval):
        # ── immutable configuration ──────────────────────────────
        self.node_id = node_id
        self.port = port
        self.config_file = config_file
        self.original_neighbours = original_neighbours
        self.routing_delay = routing_delay
        self.update_interval = update_interval

        # ── mutable state (protected by self.lock) ───────────────
        self.graph = self._build_initial_graph()
        self.immediate_neighbours = {nid for nid, _, _ in original_neighbours}
        self.failed_nodes = set()
        self.is_up = True
        self.has_changes = True
        self.last_routing_table = None
        self.suppress_routing_output = False
        self.merged_away_nodes = set()
        # Edges whose current cost was created/updated by a MERGE
        # operation. For these, we never allow an older, higher-cost
        # advertisement from the network to overwrite the cheaper cost.
        # Stored as undirected pairs (min(u,v), max(u,v)).
        self.merged_preferred_edges = set()
        # After SPLIT: (v1, v2) partition sets. Reject any socket update
        # that would re-add a cross-partition edge.
        self.split_partitions = None  # (v1, v2) or None

        # ── synchronisation ──────────────────────────────────────
        self.lock = threading.RLock()
        self.routing_event = threading.Event()
        self._print_lock = threading.Lock()
        self._running = True
        self._shutdown = threading.Event()

        # ── networking ───────────────────────────────────────────
        self._socket = UDPSocket(port)

    # ── graph helpers ────────────────────────────────────────────

    def _build_initial_graph(self):
        g = Graph()
        g.add_node(self.node_id, self.port)
        for nid, cost, nport in self.original_neighbours:
            g.add_edge(self.node_id, nid, cost)
            g.set_port(nid, nport)
        return g

    def get_filtered_graph(self):
        """Return a copy of the graph with failed nodes removed.

        Must be called while holding ``self.lock``.
        """
        g = self.graph.copy()
        for nid in self.failed_nodes:
            g.remove_node(nid)
        return g

    # ── thread-safe output ───────────────────────────────────────

    def safe_print(self, message):
        """Atomic multi-line print to STDOUT."""
        with self._print_lock:
            print(message, flush=True)

    # ── public interface for commands ────────────────────────────

    def immediate_broadcast(self):
        """Send the UPDATE packet right now (STDOUT + sockets)."""
        with self.lock:
            if self.is_up:
                self._broadcast_update()
                self.has_changes = False

    def broadcast_merged_into(self, merged_into):
        """Broadcast merge info via socket only (no STDOUT).

        Used when the absorbed node receives MERGE to propagate edge-transfer
        info so other nodes can apply the merge.
        """
        with self.lock:
            payload = Protocol.serialize_topology(
                self.node_id,
                self.graph,
                self.failed_nodes,
                merged_nodes=set(),
                merged_into=merged_into,
            )
            for nid in self.immediate_neighbours:
                if nid not in self.failed_nodes:
                    port = self.graph.get_port(nid)
                    if port is not None:
                        self._socket.send(payload, port)

    def compute_and_output_routing_table(self, *, force=False):
        """Compute shortest paths and print the routing table.

        force=True: always print (used by commands).
        force=False: only print if table changed (used by routing thread).

        Respects ``suppress_routing_output`` for BATCH UPDATE.
        """
        with self.lock:
            if self.suppress_routing_output:
                return
            filtered = self.get_filtered_graph()
            routes = Dijkstra.compute(filtered, self.node_id)
            changed = routes != self.last_routing_table
            self.last_routing_table = routes
            # Print while holding the lock so the routing table is
            # consistent with the current graph (avoids timing races).
            if force or changed:
                self._output_routing_table(routes)

    _KNOWN_COMMANDS = frozenset({
        "CHANGE", "FAIL", "RECOVER", "QUERY", "RESET",
        "MERGE", "SPLIT", "BATCH", "CYCLE",
    })

    @staticmethod
    def _looks_like_update_packet(line):
        """Heuristic: line contains colon-separated neighbor entries."""
        for token in line.split():
            if token.count(":") >= 2:
                return True
        return False

    def process_input(self, line):
        """Dispatch a single STDIN line to the right handler."""
        if line.startswith("UPDATE "):
            self._process_stdin_update(line)
            return

        first_token = line.split(maxsplit=1)[0] if line else ""
        if first_token not in self._KNOWN_COMMANDS:
            if self._looks_like_update_packet(line):
                error_exit("Error: Invalid update packet format.")
            error_exit("Error: Invalid command format. "
                       "Expected numeric cost value.")

        from ..commands.factory import CommandFactory
        command = CommandFactory.parse(line)
        command.execute(self)

    # ── starting the node ────────────────────────────────────────

    def start(self):
        """Launch background threads, then read STDIN in the main thread."""
        for target in (self._socket_listener,
                       self._sending_loop,
                       self._routing_loop):
            t = threading.Thread(target=target, daemon=True)
            t.start()

        self._stdin_loop()

        try:
            self._shutdown.wait()
        except KeyboardInterrupt:
            pass
        finally:
            self._running = False
            self.routing_event.set()

    # ── thread bodies ────────────────────────────────────────────

    def _stdin_loop(self):
        """Main thread: read STDIN lines and dispatch."""
        try:
            for line in sys.stdin:
                line = line.strip()
                if line:
                    self.process_input(line)
        except EOFError:
            pass

    def _socket_listener(self):
        """Read UDP messages from neighbouring nodes."""
        while self._running:
            data = self._socket.receive()
            if data is not None:
                self._process_socket_data(data)

    def _sending_loop(self):
        """Periodically broadcast UPDATE to immediate neighbours.

        STDOUT UPDATE is printed only when immediate-neighbour config
        changes (has_changes).  Socket topology is ALWAYS sent so that
        learned link-state information propagates across multiple hops.
        """
        while self._running:
            time.sleep(self.update_interval)
            with self.lock:
                if not self.is_up:
                    continue
                if self.has_changes:
                    self._broadcast_update()
                    self.has_changes = False
                else:
                    self._send_topology_via_socket()

    def _routing_loop(self):
        """Event-driven routing table computation.

        1. Sleep for RoutingDelay, then output initial routing table.
        2. Block on routing_event.wait() — wakes ONLY when signalled
           by UPDATE handlers (no polling, no hardcoded timeout).
        3. Recompute and output only if the table actually changed.
        """
        time.sleep(self.routing_delay)
        self.routing_event.clear()
        self.compute_and_output_routing_table(force=True)

        while self._running:
            self.routing_event.wait()
            if not self._running:
                break
            self.routing_event.clear()
            self.compute_and_output_routing_table(force=False)

    # ── internal helpers ─────────────────────────────────────────

    def _broadcast_update(self):
        """Print UPDATE to STDOUT and send topology to neighbours.

        Must be called while holding ``self.lock``.
        """
        active = {}
        for nid in sorted(self.immediate_neighbours):
            if nid not in self.failed_nodes:
                cost = self.graph.get_cost(self.node_id, nid)
                port = self.graph.get_port(nid)
                if cost is not None and port is not None:
                    active[nid] = (cost, port)

        stdout_msg = Protocol.format_stdout_update(self.node_id, active)
        self.safe_print(stdout_msg)

        payload = Protocol.serialize_topology(
            self.node_id,
            self.graph,
            self.failed_nodes,
            self.merged_away_nodes,
            merged_into={},
        )
        for nid in self.immediate_neighbours:
            if nid not in self.failed_nodes:
                port = self.graph.get_port(nid)
                if port is not None:
                    self._socket.send(payload, port)

    def _send_topology_via_socket(self):
        """Send full topology to neighbours via socket only (no STDOUT).

        Used by the sending loop to propagate learned link-state info
        even when the immediate-neighbour list hasn't changed.
        Must be called while holding ``self.lock``.
        """
        payload = Protocol.serialize_topology(
            self.node_id,
            self.graph,
            self.failed_nodes,
            self.merged_away_nodes,
            merged_into={},
        )
        for nid in self.immediate_neighbours:
            if nid not in self.failed_nodes:
                port = self.graph.get_port(nid)
                if port is not None:
                    self._socket.send(payload, port)

    def _process_stdin_update(self, line):
        """Handle an UPDATE packet arriving via STDIN."""
        try:
            source, neighbours = Protocol.parse_stdin_update(line)
        except ValueError as exc:
            error_exit(str(exc))
            return

        changed = False
        with self.lock:
            if not self._accept_node(source):
                return
            if not self.graph.has_node(source):
                self.graph.add_node(source)
                changed = True
            for nid, cost, port in neighbours:
                if not self._accept_node(nid):
                    continue
                self.graph.add_node(nid, port)
                old_cost = self.graph.get_cost(source, nid)
                if old_cost is None or old_cost != cost:
                    self.graph.add_edge(source, nid, cost)
                    changed = True

        if changed:
            self.routing_event.set()

    def _process_socket_data(self, data):
        """Handle topology data received on the UDP socket.

        Merges received topology into local graph.
        Signals routing thread only if graph actually changed.
        """
        try:
            msg = Protocol.deserialize_topology(data)
        except Exception:
            return

        changed = False
        with self.lock:
            topology = msg.get("topology", {})
            remote_failed = set(msg.get("failed", []))

            for nid, info in topology.items():
                if not self._accept_node(nid):
                    continue
                port = info.get("port")
                self.graph.add_node(nid, port)

                for n, ninfo in info.get("neighbours", {}).items():
                    if not self._accept_node(n):
                        continue
                    # Reject cross-partition edges after SPLIT (prevents
                    # old topology from other nodes re-adding removed edges)
                    if self.split_partitions is not None:
                        v1, v2 = self.split_partitions
                        if (nid in v1 and n in v2) or (nid in v2 and n in v1):
                            continue
                    ncost = ninfo["cost"]
                    nport = ninfo.get("port")
                    self.graph.add_node(n, nport)
                    old = self.graph.get_cost(nid, n)
                    key = tuple(sorted((nid, n)))

                    if old is None:
                        # Edge unknown locally → always accept.
                        self.graph.add_edge(nid, n, ncost)
                        changed = True
                    else:
                        if key in self.merged_preferred_edges:
                            # Edge cost was created by MERGE: only accept
                            # strictly cheaper advertisements, never higher.
                            if ncost < old:
                                self.graph.add_edge(nid, n, ncost)
                                changed = True
                        else:
                            # Normal edge: CHANGE / UPDATE may raise or lower
                            # the cost, so accept any different value.
                            if ncost != old:
                                self.graph.add_edge(nid, n, ncost)
                                changed = True

            for nid in remote_failed:
                if nid not in self.failed_nodes:
                    self.failed_nodes.add(nid)
                    changed = True

            for nid in msg.get("merged", []):
                if nid not in self.merged_away_nodes:
                    self.merged_away_nodes.add(nid)
                    if self.graph.has_node(nid):
                        self.graph.remove_node(nid)
                        changed = True

            for absorbed, into in msg.get("merged_into", {}).items():
                if absorbed in self.merged_away_nodes:
                    continue
                if not self.graph.has_node(absorbed):
                    self.merged_away_nodes.add(absorbed)
                    continue
                out = self.graph.get_neighbours(absorbed)
                for nid, cost in out.items():
                    if nid == into:
                        continue
                    existing = self.graph.get_cost(into, nid)
                    if existing is None or cost < existing:
                        self.graph.add_edge(into, nid, cost)
                        key = tuple(sorted((into, nid)))
                        self.merged_preferred_edges.add(key)
                        changed = True
                self.graph.remove_node(absorbed)
                self.merged_away_nodes.add(absorbed)
                changed = True

        if changed:
            self.routing_event.set()

    def _accept_node(self, nid):
        """Filter nodes based on merge state.

        Must be called while holding ``self.lock``.
        """
        if nid in self.merged_away_nodes:
            return False
        return True

    def _output_routing_table(self, routes):
        """Format and print the routing table."""
        lines = [f"I am Node {self.node_id}"]
        for dest in sorted(routes):
            cost, path = routes[dest]
            lines.append(
                f"Least cost path from {self.node_id} to {dest}: "
                f"{path}, link cost: {format_cost(cost)}"
            )
        self.safe_print("\n".join(lines))
