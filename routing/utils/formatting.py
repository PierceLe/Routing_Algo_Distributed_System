"""Output formatting and error-exit helpers."""

import sys


def format_cost(cost):
    """Format a cost value for display, handling floating-point noise.

    Rounds to 4 decimal places, strips trailing zeros but always keeps
    at least one digit after the decimal point (e.g. 5 -> '5.0').
    """
    rounded = round(cost, 4)
    if rounded == 0.0:
        return "0.0"
    if rounded == int(rounded):
        return f"{int(rounded)}.0"
    s = f"{rounded:.4f}".rstrip("0")
    if s.endswith("."):
        s += "0"
    return s


def error_exit(message):
    """Print *message* to stdout and terminate with exit-code 1."""
    print(message, flush=True)
    sys.exit(1)
