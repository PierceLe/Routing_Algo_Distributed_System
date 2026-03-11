"""Phase 3 integration test: threading, RoutingDelay, UPDATE processing.

Tests:
1. Node A starts, after RoutingDelay outputs initial routing table
2. Receives UPDATE from B via STDIN -> learns B's neighbours -> routing table updates
3. Sending thread outputs UPDATE on schedule if there are changes
"""

import subprocess
import time
import sys
import os

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_node(node_id, port, config, routing_delay, update_interval,
             stdin_lines=None, collect_time=None):
    """Start a node, feed STDIN, wait for output, then kill the process."""
    cmd = [
        sys.executable, "-m", "routing",
        node_id, str(port), config,
        str(routing_delay), str(update_interval),
    ]
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=PROJ,
    )
    if stdin_lines:
        proc.stdin.write("\n".join(stdin_lines) + "\n")
    proc.stdin.close()

    time.sleep(collect_time or (routing_delay + 2))
    proc.kill()
    stdout = proc.stdout.read()
    proc.wait()
    return stdout.strip()


def test_initial_routing_table():
    """After RoutingDelay, the routing table should be output."""
    stdout = run_node("A", 6000, "tests/configs/Aconfig.txt", 1, 30,
                      collect_time=3)
    assert "I am Node A" in stdout, f"Missing header. Got:\n{stdout}"
    assert "Least cost path from A to B: AB, link cost: 5.0" in stdout
    assert "Least cost path from A to C: AC, link cost: 10.0" in stdout
    print("PASS: initial routing table after RoutingDelay")


def test_stdin_update_learning():
    """Node A receives UPDATE from B, learns B-C edge, finds shorter path A->B->C."""
    updates = [
        "UPDATE B A:5.0:6000,C:3.0:6002",
    ]
    stdout = run_node("A", 6000, "tests/configs/Aconfig.txt", 1, 30,
                      stdin_lines=updates, collect_time=4)
    lines = stdout.split("\n")

    routing_tables = [i for i, l in enumerate(lines) if "I am Node A" in l]
    assert len(routing_tables) >= 1, f"No routing table found. Got:\n{stdout}"

    last_table_start = routing_tables[-1]
    table_text = "\n".join(lines[last_table_start:])
    assert "Least cost path from A to C: ABC, link cost: 8.0" in table_text, \
        f"Expected ABC route with cost 8.0. Got:\n{table_text}"
    print("PASS: STDIN UPDATE learning (multi-hop path)")


def test_sending_thread_broadcasts():
    """Sending thread should output UPDATE if there are changes."""
    stdout = run_node("A", 6000, "tests/configs/Aconfig.txt", 0.5, 1,
                      collect_time=3)
    update_lines = [l for l in stdout.split("\n") if l.startswith("UPDATE A")]
    assert len(update_lines) >= 1, f"No UPDATE output. Got:\n{stdout}"
    assert "B:5.0:6001" in update_lines[0]
    assert "C:10.0:6002" in update_lines[0]
    print("PASS: sending thread broadcasts UPDATE")


if __name__ == "__main__":
    test_initial_routing_table()
    test_stdin_update_learning()
    test_sending_thread_broadcasts()
    print("\nAll Phase 3 tests passed!")
