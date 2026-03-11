"""Phase 4 integration tests: dynamic commands.

Tests CHANGE, FAIL, RECOVER, QUERY, QUERY PATH, RESET, BATCH UPDATE.
"""

import subprocess
import time
import sys
import os

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_node(node_id, port, config, routing_delay, update_interval,
             stdin_lines=None, collect_time=None):
    cmd = [
        sys.executable, "-m", "routing",
        node_id, str(port), config,
        str(routing_delay), str(update_interval),
    ]
    proc = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, cwd=PROJ,
    )
    if stdin_lines:
        proc.stdin.write("\n".join(stdin_lines) + "\n")
    proc.stdin.close()
    time.sleep(collect_time or (routing_delay + 2))
    proc.kill()
    stdout = proc.stdout.read()
    proc.wait()
    return stdout.strip()


def test_change():
    """CHANGE B 3.0 should update the edge cost and output new routing table."""
    stdout = run_node("A", 6000, "tests/configs/Aconfig.txt", 1, 30,
                      stdin_lines=["CHANGE B 3.0"], collect_time=4)
    lines = stdout.split("\n")
    tables = [i for i, l in enumerate(lines) if "I am Node A" in l]
    assert len(tables) >= 2, f"Expected at least 2 routing tables. Got:\n{stdout}"
    last = "\n".join(lines[tables[-1]:])
    assert "Least cost path from A to B: AB, link cost: 3.0" in last, \
        f"Expected cost 3.0 for B. Got:\n{last}"
    print("PASS: CHANGE command")


def test_fail_self():
    """FAIL A on node A should output 'Node A is now DOWN.'"""
    stdout = run_node("A", 6000, "tests/configs/Aconfig.txt", 1, 30,
                      stdin_lines=["FAIL A"], collect_time=4)
    assert "Node A is now DOWN." in stdout, f"Missing DOWN message. Got:\n{stdout}"
    print("PASS: FAIL self")


def test_fail_other():
    """FAIL B on node A should remove B from routing and output new table."""
    stdout = run_node("A", 6000, "tests/configs/Aconfig.txt", 1, 30,
                      stdin_lines=["FAIL B"], collect_time=4)
    lines = stdout.split("\n")
    tables = [i for i, l in enumerate(lines) if "I am Node A" in l]
    assert len(tables) >= 2, f"Expected at least 2 routing tables. Got:\n{stdout}"
    last = "\n".join(lines[tables[-1]:])
    assert "to B:" not in last, f"B should be unreachable. Got:\n{last}"
    assert "Least cost path from A to C: AC, link cost: 10.0" in last
    print("PASS: FAIL other node")


def test_recover_self():
    """FAIL then RECOVER on self should output UP message."""
    stdout = run_node("A", 6000, "tests/configs/Aconfig.txt", 1, 30,
                      stdin_lines=["FAIL A", "RECOVER A"], collect_time=4)
    assert "Node A is now DOWN." in stdout
    assert "Node A is now UP." in stdout
    print("PASS: RECOVER self")


def test_recover_other():
    """FAIL then RECOVER B should restore B in routing table."""
    stdout = run_node("A", 6000, "tests/configs/Aconfig.txt", 1, 30,
                      stdin_lines=["FAIL B", "RECOVER B"], collect_time=4)
    lines = stdout.split("\n")
    tables = [i for i, l in enumerate(lines) if "I am Node A" in l]
    last = "\n".join(lines[tables[-1]:])
    assert "Least cost path from A to B: AB, link cost: 5.0" in last, \
        f"B should be restored. Got:\n{last}"
    print("PASS: RECOVER other node")


def test_query():
    """QUERY C should output the path to C."""
    stdout = run_node("A", 6000, "tests/configs/Aconfig.txt", 1, 30,
                      stdin_lines=["QUERY C"], collect_time=4)
    assert "Least cost path from A to C: AC, link cost: 10.0" in stdout, \
        f"Missing query result. Got:\n{stdout}"
    print("PASS: QUERY command")


def test_query_path():
    """QUERY PATH B C on node A (knowing B-C=3.0 via UPDATE) should show B->C."""
    stdout = run_node("A", 6000, "tests/configs/Aconfig.txt", 1, 30,
                      stdin_lines=[
                          "UPDATE B A:5.0:6000,C:3.0:6002",
                          "QUERY PATH B C",
                      ], collect_time=4)
    assert "Least cost path from B to C: BC, link cost: 3.0" in stdout, \
        f"Missing query path result. Got:\n{stdout}"
    print("PASS: QUERY PATH command")


def test_reset():
    """After CHANGE and RESET, routing table should match original config."""
    stdout = run_node("A", 6000, "tests/configs/Aconfig.txt", 1, 30,
                      stdin_lines=["CHANGE B 1.0", "RESET"], collect_time=4)
    assert "Node A has been reset." in stdout, f"Missing reset message. Got:\n{stdout}"
    lines = stdout.split("\n")
    tables = [i for i, l in enumerate(lines) if "I am Node A" in l]
    last = "\n".join(lines[tables[-1]:])
    assert "Least cost path from A to B: AB, link cost: 5.0" in last, \
        f"Cost should be back to 5.0. Got:\n{last}"
    print("PASS: RESET command")


def test_batch_update():
    """BATCH UPDATE with CHANGE commands should produce one routing table at end."""
    batch_file = os.path.join(PROJ, "tests", "batch_test.txt")
    with open(batch_file, "w") as f:
        f.write("CHANGE B 2.0\n")
        f.write("CHANGE C 3.0\n")

    stdout = run_node("A", 6000, "tests/configs/Aconfig.txt", 1, 30,
                      stdin_lines=[f"BATCH UPDATE {batch_file}"],
                      collect_time=4)
    assert "Batch update complete." in stdout, \
        f"Missing batch complete message. Got:\n{stdout}"
    lines = stdout.split("\n")
    tables = [i for i, l in enumerate(lines) if "I am Node A" in l]
    last = "\n".join(lines[tables[-1]:])
    assert "Least cost path from A to B: AB, link cost: 2.0" in last
    assert "Least cost path from A to C: AC, link cost: 3.0" in last
    print("PASS: BATCH UPDATE command")


if __name__ == "__main__":
    test_change()
    test_fail_self()
    test_fail_other()
    test_recover_self()
    test_recover_other()
    test_query()
    test_query_path()
    test_reset()
    test_batch_update()
    print("\nAll Phase 4 tests passed!")
