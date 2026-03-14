"""Entry point: validate CLI arguments, parse config, and launch the node."""

import sys

from .utils import validate_node_id, error_exit
from .config import ConfigParser


def main():
    args = sys.argv[1:]

    if len(args) < 3:
        error_exit(
            "Error: Insufficient arguments provided. "
            "Usage: ./Routing.sh <Node-ID> <Port-NO> <Node-Config-File>"
        )

    node_id = args[0]
    if not validate_node_id(node_id):
        error_exit("Error: Invalid Node-ID.")

    try:
        port = int(args[1])
    except ValueError:
        error_exit("Error: Invalid Port number. Must be an integer.")

    config_file = args[2]

    # Optional: RoutingDelay and UpdateInterval (defaults if not provided)
    if len(args) >= 5:
        try:
            routing_delay = float(args[3])
        except ValueError:
            error_exit("Error: Invalid RoutingDelay. Must be a number.")
        try:
            update_interval = float(args[4])
        except ValueError:
            error_exit("Error: Invalid UpdateInterval. Must be a number.")
    else:
        routing_delay = 60.0
        update_interval = 10.0

    original_neighbours = ConfigParser.parse(config_file)

    from .core import Node
    node = Node(node_id, port, config_file, original_neighbours,
                routing_delay, update_interval)
    node.start()
