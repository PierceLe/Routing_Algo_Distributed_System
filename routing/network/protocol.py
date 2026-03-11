"""Message serialisation for STDIN/STDOUT and UDP socket communication.

STDOUT format (spec-mandated, immediate neighbours only):
    UPDATE <Node-ID> <N1>:<Cost1>:<Port1>,<N2>:<Cost2>:<Port2>,...

Socket format (link-state, full topology as JSON):
    {"source": "A", "topology": {...}, "failed": [...], "merged": [...]}
"""

import json

from ..utils import format_cost


class Protocol:

    # ── STDOUT / STDIN ───────────────────────────────────────────

    @staticmethod
    def format_stdout_update(node_id, neighbours):
        """Build the spec-mandated UPDATE line for STDOUT.

        neighbours: {nid: (cost, port)} — only active immediate neighbours.
        """
        parts = []
        for nid in sorted(neighbours):
            cost, port = neighbours[nid]
            parts.append(f"{nid}:{format_cost(cost)}:{port}")
        if parts:
            return f"UPDATE {node_id} {','.join(parts)}"
        return f"UPDATE {node_id}"

    @staticmethod
    def parse_stdin_update(line):
        """Parse an UPDATE packet from STDIN.

        Returns (source, [(nid, cost, port), ...]).
        Raises ValueError with the spec error message on bad format.
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

    # ── Socket (JSON, link-state topology) ───────────────────────

    @staticmethod
    def serialize_topology(
        source,
        graph,
        failed_nodes,
        merged_nodes=None,
        merged_into=None,
        split=False,
    ):
        """Encode full known topology as JSON bytes for socket."""
        if merged_nodes is None:
            merged_nodes = set()
        if merged_into is None:
            merged_into = {}
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
            "merged": list(merged_nodes),
            "merged_into": merged_into,
            "split": bool(split),
        }
        return json.dumps(payload).encode("utf-8")

    @staticmethod
    def deserialize_topology(data):
        """Decode JSON bytes from socket."""
        return json.loads(data.decode("utf-8"))
