"""Node: the central orchestrator that owns the graph, threads, and I/O."""

import sys
import threading
import time

from .graph import Graph
from .router import Router
from ..network import NetworkManager, Protocol
from ..config import ConfigParser
from ..commands import CommandFactory
from ..utils import format_cost, error_exit


class Node:
    """Represents a single routing node in the network.

    Responsibilities
    ----------------
    * Maintain the full known topology (link-state database).
    * Run four concurrent threads: STDIN reader, socket listener,
      periodic sender, and routing calculator.
    * Process dynamic commands and UPDATE packets.
    """

    def __init__(self, node_id, port, config_file, routing_delay, update_interval):
        self.node_id = node_id
        self.port = port
        self.config_file = config_file
        self.routing_delay = routing_delay
        self.update_interval = update_interval

        # ── persistent config (for RESET) ────────────────────────
        self.original_neighbours = ConfigParser.parse(config_file)

        # ── mutable state (protected by self.lock) ───────────────
        self.graph = self.create_initial_graph()
        self.failed_nodes: set = set()
        self.is_up: bool = True
        self.has_changes: bool = True
        self.seq_num: int = 0
        self.last_routing_table: dict | None = None
        self.suppress_routing_output: bool = False
        self.running: bool = True

        # ── synchronisation ──────────────────────────────────────
        self.lock = threading.RLock()
        self.routing_event = threading.Event()
        self._print_lock = threading.Lock()

        # ── networking ───────────────────────────────────────────
        self.network = NetworkManager(port)

    # ── graph helpers ────────────────────────────────────────────

    def create_initial_graph(self):
        """Build a graph containing only self and direct neighbours."""
        g = Graph()
        g.add_node(self.node_id, self.port)
        for nid, cost, port in self.original_neighbours:
            g.add_edge(self.node_id, nid, cost)
            g.set_port(nid, port)
        return g

    def get_filtered_graph(self):
        """Return a copy of the graph with failed nodes removed.

        **Must** be called while holding ``self.lock``.
        """
        g = self.graph.copy()
        for nid in self.failed_nodes:
            g.remove_node(nid)
        return g

    # ── thread-safe output ───────────────────────────────────────

    def safe_print(self, message):
        with self._print_lock:
            print(message, flush=True)

    # ── public helpers used by Command objects ───────────────────

    def immediate_broadcast(self):
        """Send the UPDATE packet right now (STDOUT + sockets)."""
        with self.lock:
            if self.is_up:
                self._broadcast_update()
                self.has_changes = False

    def compute_and_output_routing_table(self, *, force=False):
        """Compute shortest paths and print the table.

        With *force=True* the table is always printed (used by commands).
        With *force=False* the table is printed only when it differs from
        the previous output (used by the background routing thread).
        """
        if self.suppress_routing_output:
            return
        with self.lock:
            filtered = self.get_filtered_graph()
            routes = Router.compute_shortest_paths(filtered, self.node_id)
            changed = routes != self.last_routing_table
            self.last_routing_table = routes
        if force or changed:
            self._output_routing_table(routes)

    def process_input(self, line):
        """Dispatch a single STDIN line to the right handler."""
        if line.startswith("UPDATE "):
            self._process_stdin_update(line)
        else:
            command = CommandFactory.parse(line)  # may call error_exit
            command.execute(self)

    # ── starting the node ────────────────────────────────────────

    def start(self):
        """Launch all background threads, then read STDIN in the main thread."""
        for target in (self._socket_listener, self._sending_loop, self._routing_loop):
            t = threading.Thread(target=target, daemon=True)
            t.start()

        self._stdin_loop()  # blocks until EOF

        # Keep the process alive so daemon threads can continue
        # (the test harness will terminate the process when done).
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.running = False

    # ── thread bodies ────────────────────────────────────────────

    def _stdin_loop(self):
        try:
            for line in sys.stdin:
                line = line.strip()
                if line:
                    self.process_input(line)
        except EOFError:
            pass

    def _socket_listener(self):
        while self.running:
            data = self.network.receive()
            if data is not None:
                self._process_socket_data(data)

    def _sending_loop(self):
        while self.running:
            time.sleep(self.update_interval)
            with self.lock:
                if self.has_changes and self.is_up:
                    self._broadcast_update()
                    self.has_changes = False

    def _routing_loop(self):
        time.sleep(self.routing_delay)
        self.compute_and_output_routing_table(force=True)
        while self.running:
            self.routing_event.wait(timeout=1.0)
            if self.routing_event.is_set():
                self.routing_event.clear()
                self.compute_and_output_routing_table(force=False)

    # ── internal helpers ─────────────────────────────────────────

    def _broadcast_update(self):
        """Print UPDATE to STDOUT and send topology to neighbours.

        **Must** be called while holding ``self.lock``.
        """
        neighbours = self.graph.get_neighbours(self.node_id)
        active = {}
        for nid in sorted(neighbours):
            if nid not in self.failed_nodes:
                active[nid] = (neighbours[nid], self.graph.get_port(nid))
        update_str = Protocol.format_stdout_update(
            self.node_id, active, self.failed_nodes
        )
        self.safe_print(update_str)

        payload = Protocol.serialize_socket_message(
            self.node_id, self.graph, self.failed_nodes
        )
        for nid in neighbours:
            if nid not in self.failed_nodes:
                port = self.graph.get_port(nid)
                if port is not None:
                    self.network.send(payload, port)

    def _process_stdin_update(self, line):
        """Handle an ``UPDATE`` packet arriving via STDIN."""
        try:
            source, neighbours = Protocol.parse_stdin_update(line)
        except ValueError as exc:
            error_exit(str(exc))
            return  # unreachable, but keeps linters happy

        changed = False
        with self.lock:
            if not self.graph.has_node(source):
                self.graph.add_node(source)
                changed = True
            for nid, cost, port in neighbours:
                self.graph.add_node(nid, port)
                old_cost = self.graph.get_cost(source, nid)
                if old_cost is None or old_cost != cost:
                    self.graph.add_edge(source, nid, cost)
                    changed = True
        if changed:
            self.routing_event.set()

    def _process_socket_data(self, data):
        """Handle raw bytes received on the UDP socket."""
        try:
            msg = Protocol.deserialize_socket_message(data)
        except Exception:
            return

        changed = False
        with self.lock:
            topology = msg.get("topology", {})
            remote_failed = set(msg.get("failed", []))

            for nid, info in topology.items():
                port = info.get("port")
                if port is not None:
                    self.graph.add_node(nid, port)
                else:
                    self.graph.add_node(nid)

                for n, ninfo in info.get("neighbours", {}).items():
                    ncost = ninfo["cost"]
                    nport = ninfo.get("port")
                    if nport is not None:
                        self.graph.add_node(n, nport)
                    else:
                        self.graph.add_node(n)
                    old = self.graph.get_cost(nid, n)
                    if old is None or old != ncost:
                        self.graph.add_edge(nid, n, ncost)
                        changed = True

            for nid in remote_failed:
                if nid not in self.failed_nodes:
                    self.failed_nodes.add(nid)
                    changed = True

        if changed:
            self.routing_event.set()

    def _output_routing_table(self, routes):
        lines = [f"I am Node {self.node_id}"]
        for dest in sorted(routes):
            cost, path = routes[dest]
            lines.append(
                f"Least cost path from {self.node_id} to {dest}: "
                f"{path}, link cost: {format_cost(cost)}"
            )
        self.safe_print("\n".join(lines))
