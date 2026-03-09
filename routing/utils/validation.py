"""Input validation helpers."""


def validate_node_id(node_id):
    """A valid Node-ID is exactly one uppercase ASCII letter A-Z."""
    return len(node_id) == 1 and node_id.isascii() and node_id.isupper()
