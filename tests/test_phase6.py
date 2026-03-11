"""Phase 6 tests: Appendix B error handling for dynamic commands.

Every error message must match the spec EXACTLY and the program
must exit with a non-zero exit code.
"""

import subprocess
import sys
import os

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_next_port = 8000


def next_port():
    global _next_port
    p = _next_port
    _next_port += 1
    return p


def run_command(command_line, expected_error):
    """Run a node that receives a single bad command, verify error and exit code."""
    port = next_port()
    proc = subprocess.run(
        [sys.executable, "-m", "routing",
         "A", str(port), "tests/configs/Aconfig.txt", "0", "9999"],
        input=command_line + "\n",
        capture_output=True,
        text=True,
        timeout=5,
        cwd=PROJ,
    )
    stdout = proc.stdout.strip()
    assert proc.returncode != 0, \
        f"Expected non-zero exit for '{command_line}', got 0. Output:\n{stdout}"
    assert expected_error in stdout, \
        f"For '{command_line}':\n  Expected: {expected_error}\n  Got: {stdout}"


def test_malformed_update_packet():
    run_command(
        "UPD8 A A:2.3:6000",
        "Error: Invalid update packet format."
    )
    print("PASS: Malformed update packet")


def test_change_non_numeric():
    run_command(
        "CHANGE A two",
        "Error: Invalid command format. Expected numeric cost value."
    )
    print("PASS: CHANGE non-numeric cost")


def test_change_extra_tokens():
    run_command(
        "CHANGE A 2.5 extra",
        "Error: Invalid command format. Expected exactly two tokens after CHANGE."
    )
    print("PASS: CHANGE extra tokens")


def test_fail_invalid_id():
    run_command(
        "FAIL AB",
        "Error: Invalid command format. Expected a valid Node-ID."
    )
    print("PASS: FAIL invalid Node-ID")


def test_fail_missing_arg():
    run_command(
        "FAIL",
        "Error: Invalid command format. Expected: FAIL <Node-ID>."
    )
    print("PASS: FAIL missing argument")


def test_recover_invalid_id():
    run_command(
        "RECOVER ab",
        "Error: Invalid command format. Expected a valid Node-ID."
    )
    print("PASS: RECOVER invalid Node-ID")


def test_query_invalid_dest():
    run_command(
        "QUERY AB",
        "Error: Invalid command format. Expected a valid Destination."
    )
    print("PASS: QUERY invalid destination")


def test_query_path_invalid():
    run_command(
        "QUERY PATH A b",
        "Error: Invalid command format. Expected two valid identifiers for Source and Destination."
    )
    print("PASS: QUERY PATH invalid identifiers")


def test_merge_invalid():
    run_command(
        "MERGE A b",
        "Error: Invalid command format. Expected two valid identifiers for MERGE."
    )
    print("PASS: MERGE invalid identifiers")


def test_split_extra():
    run_command(
        "SPLIT extra",
        "Error: Invalid command format. Expected exactly: SPLIT."
    )
    print("PASS: SPLIT extra tokens")


def test_reset_extra():
    run_command(
        "RESET now",
        "Error: Invalid command format. Expected exactly: RESET."
    )
    print("PASS: RESET extra tokens")


def test_cycle_detect_extra():
    run_command(
        "CYCLE DETECT extra",
        "Error: Invalid command format. Expected exactly: CYCLE DETECT."
    )
    print("PASS: CYCLE DETECT extra tokens")


def test_batch_update_missing_filename():
    run_command(
        "BATCH UPDATE",
        "Error: Invalid command format. Expected: BATCH UPDATE <Filename>."
    )
    print("PASS: BATCH UPDATE missing filename")


def test_unknown_command():
    run_command(
        "SET COST A B abc",
        "Error: Invalid command format. Expected numeric cost value."
    )
    print("PASS: Unknown command (SET COST)")


if __name__ == "__main__":
    test_malformed_update_packet()
    test_change_non_numeric()
    test_change_extra_tokens()
    test_fail_invalid_id()
    test_fail_missing_arg()
    test_recover_invalid_id()
    test_query_invalid_dest()
    test_query_path_invalid()
    test_merge_invalid()
    test_split_extra()
    test_reset_extra()
    test_cycle_detect_extra()
    test_batch_update_missing_filename()
    test_unknown_command()
    print("\nAll Phase 6 tests passed!")
