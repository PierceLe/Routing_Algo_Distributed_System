from ..utils import validate_node_id, error_exit


class ConfigParser:
    """Parse and validate the neighbour configuration file.

    Returns a list of (node_id, cost, port) tuples.
    Exits with spec-compliant error messages on any invalid input.
    """

    @staticmethod
    def parse(filepath):
        try:
            with open(filepath, "r") as fh:
                lines = fh.readlines()
        except FileNotFoundError:
            error_exit(f"Error: Configuration file {filepath} not found.")

        if not lines:
            error_exit(
                "Error: Invalid configuration file format. "
                "(First line must be an integer.)"
            )

        try:
            n = int(lines[0].strip())
        except ValueError:
            error_exit(
                "Error: Invalid configuration file format. "
                "(First line must be an integer.)"
            )

        neighbours = []
        for i in range(1, n + 1):
            if i >= len(lines):
                error_exit(
                    "Error: Invalid configuration file format. "
                    "(Each neighbour entry must have exactly three "
                    "tokens; cost must be numeric.)"
                )

            tokens = lines[i].strip().split()

            if len(tokens) > 3:
                error_exit("Error: Invalid configuration file format.")

            if len(tokens) != 3:
                error_exit(
                    "Error: Invalid configuration file format. "
                    "(Each neighbour entry must have exactly three "
                    "tokens; cost must be numeric.)"
                )

            nid = tokens[0]
            if not validate_node_id(nid):
                error_exit(
                    "Error: Invalid configuration file format. "
                    "(Each neighbour entry must have exactly three "
                    "tokens; cost must be numeric.)"
                )

            try:
                cost = float(tokens[1])
            except ValueError:
                error_exit(
                    "Error: Invalid configuration file format. "
                    "(Each neighbour entry must have exactly three "
                    "tokens; cost must be numeric.)"
                )

            try:
                port = int(tokens[2])
            except ValueError:
                error_exit(
                    "Error: Invalid configuration file format. "
                    "(Each neighbour entry must have exactly three "
                    "tokens; cost must be numeric.)"
                )

            neighbours.append((nid, cost, port))

        return neighbours
