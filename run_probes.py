#!/usr/bin/env python3
"""Run the post-hoc robustness probes (probes/) against every saved solution and the reference."""
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROBES = {"a_free_slots": "probe_a.py", "b_invoice_bugfix": "probe_b.py", "c_ttl_cache": "probe_c.py"}
LABELS = {"claude-fable-5-2": "Fable 5.2", "claude-opus-5-5": "Opus 5.5", "reference": "Reference"}


def run_one(task, sol_dir, work):
    shutil.rmtree(work, ignore_errors=True)
    shutil.copytree(sol_dir, work)
    shutil.copy(ROOT / "probes" / PROBES[task], work / ("test_" + PROBES[task]))
    xml = work / "j.xml"
    env = dict(os.environ, PYTHONPATH=str(work), SOLUTION_DIR=str(work))
    env.pop("ANTHROPIC_API_KEY", None)
    subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={xml}", "test_" + PROBES[task]],
                   cwd=work, env=env, capture_output=True, text=True, timeout=600)
    out = {"passed": 0, "total": 0, "failed": [], "timings_s": {}}
    root = ET.parse(xml).getroot()
    for tc in root.iter("testcase"):
        out["total"] += 1
        name = tc.get("name")
        if tc.find("failure") is None and tc.find("error") is None:
            out["passed"] += 1
        else:
            out["failed"].append(name)
        for p in tc.iter("property"):
            if p.get("name") == "seconds":
                out["timings_s"][name] = float(p.get("value"))
    shutil.rmtree(work, ignore_errors=True)
    return out


def main():
    rows = []
    for task in PROBES:
        targets = [("reference", 0, ROOT / "tasks" / task / "reference")]
        for model in ("claude-fable-5-2", "claude-opus-5-5"):
            for run in (1, 2):
                d = ROOT / "runs" / task / model / f"run{run}" / "solution"
                if d.exists():
                    targets.append((model, run, d))
        for model, run, d in targets:
            r = run_one(task, d, ROOT / ".probe_work")
            r.update(task=task, model=model, label=LABELS[model], run=run)
            rows.append(r)
            print(f"{task:18} {LABELS[model]:9} run{run}: {r['passed']}/{r['total']} failed={r['failed']} timings={r['timings_s']}")
    (ROOT / "probes" / "probe_results.json").write_text(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
