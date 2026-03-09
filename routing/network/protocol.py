"""Message serialisation for STDIN/STDOUT and UDP socket communication."""

import json

from ..utils import format_cost


class Protocol:
    """Handles encoding / decoding of update packets and topology data."""

    # ── STDOUT / STDIN update packets ────────────────────────────

    @staticmethod
    def format_stdout_update(node_id, neighbours, failed_nodes=None):
        """Build the STDOUT ``UPDATE`` line.

        *neighbours* is ``{nid: (cost, port)}``.
        Failed neighbours are excluded.
        """
        if failed_nodes is None:
            failed_nodes = set()
        parts = []
        for nid in sorted(neighbours):
            if nid not in failed_nodes:
                cost, port = neighbours[nid]
                parts.append(f"{nid}:{format_cost(cost)}:{port}")
        if parts:
            return f"UPDATE {node_id} {','.join(parts)}"
        return f"UPDATE {node_id}"

    @staticmethod
    def parse_stdin_update(line):
        """Parse ``UPDATE <src> <N1:C1:P1>,…`` from STDIN.

        Returns ``(source, [(nid, cost, port), …])``.
        Raises ``ValueError`` with the spec error message on bad format.
        """
        parts = line.split(maxsplit=2)
        if len(parts) < 2 or parts[0] != "UPDATE":
            raise ValueError("Error: Invalid update packet format.")

        source = parts[1]
        neighbours = []

        if len(parts) == 3 and parts[2].strip():
            for entry in parts[2].strip().split(","):
                tokens = entry.strip().split(":")
                if len(tokens) != 3:
                    raise ValueError("Error: Invalid update packet format.")
                try:
                    cost = float(tokens[1])
                    port = int(tokens[2])
                except ValueError:
                    raise ValueError("Error: Invalid update packet format.")
                neighbours.append((tokens[0], cost, port))

        return source, neighbours

    # ── Socket (JSON) messages ───────────────────────────────────

    @staticmethod
    def serialize_socket_message(source, graph, failed_nodes):
        """Encode the full known topology as a JSON byte string."""
        topology = {}
        for nid in graph.get_nodes():
            topology[nid] = {
                "port": graph.get_port(nid),
                "neighbours": {
                    n: {"cost": c, "port": graph.get_port(n)}
                    for n, c in graph.get_neighbours(nid).items()
                },
            }
        payload = {
            "source": source,
            "topology": topology,
            "failed": list(failed_nodes),
        }
        return json.dumps(payload).encode("utf-8")

    @staticmethod
    def deserialize_socket_message(data):
        """Decode a JSON byte string back to a dict."""
        return json.loads(data.decode("utf-8"))
