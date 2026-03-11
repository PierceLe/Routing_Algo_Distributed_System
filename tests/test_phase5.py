"""Phase 5 tests: MERGE, SPLIT, CYCLE DETECT."""

import subprocess
import time
import sys
import os

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_next_port = 7000


def next_port():
    global _next_port
    p = _next_port
    _next_port += 1
    return p


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


def test_cycle_detect_with_cycle():
    """A-B, A-C, B-C forms a triangle -> cycle detected."""
    port = next_port()
    stdout = run_node("A", port, "tests/configs/Aconfig.txt", 1, 30,
                      stdin_lines=[
                          "UPDATE B A:5.0:6000,C:3.0:6002",
                          "CYCLE DETECT",
                      ], collect_time=4)
    assert "Cycle detected." in stdout, f"Expected cycle. Got:\n{stdout}"
    print("PASS: CYCLE DETECT with cycle")


def test_cycle_detect_no_cycle():
    """A-B, A-C with no B-C edge -> no cycle (tree)."""
    port = next_port()
    stdout = run_node("A", port, "tests/configs/Aconfig.txt", 1, 30,
                      stdin_lines=["CYCLE DETECT"], collect_time=4)
    assert "No cycle found." in stdout, f"Expected no cycle. Got:\n{stdout}"
    print("PASS: CYCLE DETECT without cycle")


def test_merge():
    """MERGE A C: node C absorbed into A. C's edges become A's edges."""
    port = next_port()
    stdout = run_node("A", port, "tests/configs/Aconfig.txt", 1, 30,
                      stdin_lines=[
                          "UPDATE B A:5.0:6000,C:3.0:6002",
                          "MERGE A C",
                      ], collect_time=4)
    assert "Graph merged successfully." in stdout, \
        f"Missing merge message. Got:\n{stdout}"
    lines = stdout.split("\n")
    tables = [i for i, l in enumerate(lines) if "I am Node A" in l]
    last = "\n".join(lines[tables[-1]:])
    assert "to C:" not in last, f"C should not appear after merge. Got:\n{last}"
    assert "Least cost path from A to B: AB, link cost: 3.0" in last, \
        f"A-B should use merged cost 3.0. Got:\n{last}"
    print("PASS: MERGE command")


def test_split():
    """SPLIT on {A, B, C} -> V1={A}, V2={B,C}. Cross-edges removed."""
    port = next_port()
    stdout = run_node("A", port, "tests/configs/Aconfig.txt", 1, 30,
                      stdin_lines=[
                          "UPDATE B A:5.0:6000,C:3.0:6002",
                          "SPLIT",
                      ], collect_time=4)
    assert "Graph partitioned successfully." in stdout, \
        f"Missing split message. Got:\n{stdout}"
    lines = stdout.split("\n")
    tables = [i for i, l in enumerate(lines) if "I am Node A" in l]
    last = "\n".join(lines[tables[-1]:])
    assert "to B:" not in last, f"A should be isolated. Got:\n{last}"
    assert "to C:" not in last, f"A should be isolated. Got:\n{last}"
    print("PASS: SPLIT command")


if __name__ == "__main__":
    test_cycle_detect_with_cycle()
    test_cycle_detect_no_cycle()
    test_merge()
    test_split()
    print("\nAll Phase 5 tests passed!")
