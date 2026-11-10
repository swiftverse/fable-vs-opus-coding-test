import json
import os
import subprocess
import sys
import time

HERE = os.environ.get("SOLUTION_DIR", os.getcwd())


def run(stdin, *args):
    p = subprocess.run([sys.executable, os.path.join(HERE, "cache_cli.py"), *args], input=stdin,
                       capture_output=True, text=True, timeout=20, cwd=HERE)
    return p


def test_basic_session():
    p = run("SET a hello\nGET a\nGET b\nLEN\nDEL a\nDEL a\nLEN\n")
    assert p.returncode == 0
    assert p.stdout.splitlines() == ["OK", "hello", "(nil)", "1", "1", "0", "0"]


def test_commands_case_insensitive_keys_case_sensitive():
    p = run("set K v\nget K\nGeT k\n")
    assert p.stdout.splitlines() == ["OK", "v", "(nil)"]


def test_stats_json_sorted():
    p = run("SET a 1\nGET a\nGET x\nSTATS\n")
    last = p.stdout.splitlines()[-1]
    assert json.loads(last) == {"evictions": 0, "expirations": 0, "hits": 1, "misses": 1}
    assert last.index("evictions") < last.index("expirations") < last.index("hits") < last.index("misses")


def test_maxsize_flag_evicts():
    p = run("SET a 1\nSET b 2\nSET c 3\nGET a\nSTATS\n", "--maxsize", "2")
    lines = p.stdout.splitlines()
    assert lines[3] == "(nil)"
    assert json.loads(lines[4])["evictions"] == 1


def test_blank_lines_ignored_and_errors_continue():
    p = run("\n   \nFOO bar\nGET\nSET a\nSET a 1 notanumber\nSET a 1 -3\nSET a ok\nGET a\n")
    lines = p.stdout.splitlines()
    assert p.returncode == 0
    assert len(lines) == 7
    assert all(l.startswith("ERR") for l in lines[:5])
    assert lines[5:] == ["OK", "ok"]


def test_per_entry_ttl_real_clock():
    script = "SET a 1 0.3\nSET b 2\n"
    p = subprocess.Popen([sys.executable, os.path.join(HERE, "cache_cli.py")], stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, text=True, cwd=HERE)
    p.stdin.write(script)
    p.stdin.flush()
    time.sleep(0.6)
    out, _ = p.communicate("GET a\nGET b\n", timeout=20)
    assert out.splitlines() == ["OK", "OK", "(nil)", "2"]
    assert p.returncode == 0


def test_invalid_flags_nonzero_exit():
    assert run("", "--maxsize", "0").returncode != 0
    assert run("", "--ttl", "-1").returncode != 0
