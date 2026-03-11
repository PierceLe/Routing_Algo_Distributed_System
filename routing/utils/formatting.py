import sys


def format_cost(cost):
    """Format a cost for display.

    Round to 4 decimal places, strip trailing zeros,
    always keep at least one digit after the decimal point.
    """
    rounded = round(cost, 4)
    if rounded == int(rounded):
        return f"{int(rounded)}.0"
    s = f"{rounded:.4f}".rstrip("0")
    if s.endswith("."):
        s += "0"
    return s


def error_exit(message):
    """Print error message to stdout and exit with code 1."""
    print(message, flush=True)
    sys.exit(1)
