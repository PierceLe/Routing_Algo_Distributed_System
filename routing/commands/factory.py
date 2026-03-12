"""CommandFactory: parses raw input lines into Command objects (Factory pattern).

Validates command format and produces spec-compliant error messages
for malformed input (Appendix B).
"""

from ..utils import validate_node_id, error_exit
from .core_commands import (
    ChangeCommand,
    FailCommand,
    RecoverCommand,
    QueryCommand,
    QueryPathCommand,
    ResetCommand,
    BatchUpdateCommand,
)


class CommandFactory:
    """Parse a raw input line into the appropriate Command object."""

    @staticmethod
    def parse(line):
        tokens = line.strip().split()
        if not tokens:
            error_exit("Error: Invalid command format.")

        if len(tokens) >= 2:
            pair = f"{tokens[0]} {tokens[1]}"
            if pair == "QUERY PATH":
                return CommandFactory._parse_query_path(tokens)
            if pair == "CYCLE DETECT":
                return CommandFactory._parse_cycle_detect(tokens)
            if pair == "BATCH UPDATE":
                return CommandFactory._parse_batch_update(tokens)

        cmd = tokens[0]
        dispatch = {
            "CHANGE": CommandFactory._parse_change,
            "FAIL": CommandFactory._parse_fail,
            "RECOVER": CommandFactory._parse_recover,
            "QUERY": CommandFactory._parse_query,
            "RESET": CommandFactory._parse_reset,
            "MERGE": CommandFactory._parse_merge,
        }
        if cmd in dispatch:
            return dispatch[cmd](tokens)

        error_exit("Error: Invalid command format.")

    # ── individual parsers ───────────────────────────────────────

    @staticmethod
    def _parse_change(tokens):
        if len(tokens) < 3:
            error_exit(
                "Error: Invalid command format. "
                "Expected numeric cost value."
            )
        if len(tokens) > 3:
            error_exit(
                "Error: Invalid command format. "
                "Expected exactly two tokens after CHANGE."
            )
        if not validate_node_id(tokens[1]):
            error_exit(
                "Error: Invalid command format. "
                "Expected numeric cost value."
            )
        try:
            cost = float(tokens[2])
        except ValueError:
            error_exit(
                "Error: Invalid command format. "
                "Expected numeric cost value."
            )
        return ChangeCommand(tokens[1], cost)

    @staticmethod
    def _parse_fail(tokens):
        if len(tokens) < 2:
            error_exit(
                "Error: Invalid command format. "
                "Expected: FAIL <Node-ID>."
            )
        if len(tokens) > 2:
            error_exit(
                "Error: Invalid command format. "
                "Expected a valid Node-ID."
            )
        if not validate_node_id(tokens[1]):
            error_exit(
                "Error: Invalid command format. "
                "Expected a valid Node-ID."
            )
        return FailCommand(tokens[1])

    @staticmethod
    def _parse_recover(tokens):
        if len(tokens) < 2:
            error_exit(
                "Error: Invalid command format. "
                "Expected: RECOVER <Node-ID>."
            )
        if len(tokens) > 2:
            error_exit(
                "Error: Invalid command format. "
                "Expected a valid Node-ID."
            )
        if not validate_node_id(tokens[1]):
            error_exit(
                "Error: Invalid command format. "
                "Expected a valid Node-ID."
            )
        return RecoverCommand(tokens[1])

    @staticmethod
    def _parse_query(tokens):
        if len(tokens) != 2:
            error_exit(
                "Error: Invalid command format. "
                "Expected a valid Destination."
            )
        if not validate_node_id(tokens[1]):
            error_exit(
                "Error: Invalid command format. "
                "Expected a valid Destination."
            )
        return QueryCommand(tokens[1])

    @staticmethod
    def _parse_query_path(tokens):
        if len(tokens) != 4:
            error_exit(
                "Error: Invalid command format. "
                "Expected two valid identifiers for "
                "Source and Destination."
            )
        if not validate_node_id(tokens[2]) or not validate_node_id(tokens[3]):
            error_exit(
                "Error: Invalid command format. "
                "Expected two valid identifiers for "
                "Source and Destination."
            )
        return QueryPathCommand(tokens[2], tokens[3])

    @staticmethod
    def _parse_reset(tokens):
        if len(tokens) != 1:
            error_exit(
                "Error: Invalid command format. "
                "Expected exactly: RESET."
            )
        return ResetCommand()

    @staticmethod
    def _parse_batch_update(tokens):
        if len(tokens) != 3:
            error_exit(
                "Error: Invalid command format. "
                "Expected: BATCH UPDATE <Filename>."
            )
        return BatchUpdateCommand(tokens[2])

    @staticmethod
    def _parse_merge(tokens):
        if len(tokens) != 3:
            error_exit(
                "Error: Invalid command format. "
                "Expected two valid identifiers for MERGE."
            )
        if not validate_node_id(tokens[1]) or not validate_node_id(tokens[2]):
            error_exit(
                "Error: Invalid command format. "
                "Expected two valid identifiers for MERGE."
            )
        from .bonus_commands import MergeCommand
        return MergeCommand(tokens[1], tokens[2])

    @staticmethod
    def _parse_cycle_detect(tokens):
        if len(tokens) != 2:
            error_exit(
                "Error: Invalid command format. "
                "Expected exactly: CYCLE DETECT."
            )
        from .bonus_commands import CycleDetectCommand
        return CycleDetectCommand()
