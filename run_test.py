#!/usr/bin/env python3
"""Side-by-side coding test: Claude Fable 5.2 vs Claude Opus 5.5.

Usage:
    export ANTHROPIC_API_KEY=...        # never commit this
    python run_test.py run              # call the API (skips runs that already exist)
    python run_test.py score            # run hidden pytest suites on extracted code
    python run_test.py judge            # one blind LLM code-quality judge call (optional)
    python run_test.py report           # write results.json, results.md, chart.png
    python run_test.py all              # run + score + judge + report

Settings are identical for both models: same prompt, same max_tokens,
adaptive thinking, effort "medium", default temperature, no tools.
A hard budget guard stops further calls if the worst-case cost of the
next call would push cumulative spend over BUDGET_USD. The running spend
ledger is kept outside the repo (FVO_PRIVATE_DIR) and is never committed.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
TASKS_DIR = ROOT / "tasks"
RUNS_DIR = ROOT / "runs"
# The spend ledger lives OUTSIDE the repo so no spend figures get committed.
PRIVATE_DIR = Path(os.environ.get("FVO_PRIVATE_DIR", Path.home() / ".fable-vs-opus-private"))
LEDGER = PRIVATE_DIR / "ledger.json"

MODELS = {
    "claude-fable-5-2": {"label": "Fable 5.2", "in": 8.0, "out": 40.0},
    "claude-opus-5-5": {"label": "Opus 5.5", "in": 4.0, "out": 20.0},
}
TASKS = ["a_free_slots", "b_invoice_bugfix", "c_ttl_cache"]
RUNS_PER_MODEL = 2
MAX_TOKENS = 6000
EFFORT = "medium"
BUDGET_USD = float(os.environ.get("BUDGET_USD", "4.50"))
API_URL = "https://api.anthropic.com/v1/messages"


def cost(model, usage):
    p = MODELS[model]
    return usage.get("input_tokens", 0) * p["in"] / 1e6 + usage.get("output_tokens", 0) * p["out"] / 1e6


def load_ledger():
    if LEDGER.exists():
        return json.loads(LEDGER.read_text())
    return {"calls": [], "total_usd": 0.0}


def save_ledger(ledger):
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(ledger, indent=2))


def call_model(model, prompt, max_tokens=MAX_TOKENS):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        sys.exit("ANTHROPIC_API_KEY is not set")
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "thinking": {"type": "adaptive"},
        "output_config": {"effort": EFFORT},
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    t0 = time.time()
    r = requests.post(API_URL, headers=headers, json=body, timeout=900)
    wall = time.time() - t0
    data = r.json()
    if r.status_code != 200:
        raise RuntimeError(f"API error {r.status_code}: {json.dumps(data)[:500]}")
    return data, wall, body


def extract_files(text):
    files = {}
    for block in re.findall(r"```(?:python|py)?[ \t]*\n(.*?)```", text, flags=re.S):
        first = block.strip().splitlines()[0] if block.strip() else ""
        m = re.match(r"#\s*file:\s*(\S+\.py)", first)
        if m:
            files[m.group(1)] = block
    return files


def cmd_run():
    ledger = load_ledger()
    for run in range(1, RUNS_PER_MODEL + 1):
        for task in TASKS:
            prompt = (TASKS_DIR / task / "prompt.md").read_text()
            order = list(MODELS) if run % 2 else list(MODELS)[::-1]
            for model in order:
                out = RUNS_DIR / task / model / f"run{run}"
                if (out / "response.json").exists():
                    continue
                est_in = len(prompt) / 3
                worst = est_in * MODELS[model]["in"] / 1e6 + MAX_TOKENS * MODELS[model]["out"] / 1e6
                if ledger["total_usd"] + worst > BUDGET_USD:
                    print(f"BUDGET GUARD: skipping {task}/{model}/run{run} (budget would be exceeded)")
                    continue
                print(f"-> {task} {model} run{run} ...", flush=True)
                data, wall, body = call_model(model, prompt)
                c = cost(model, data["usage"])
                ledger["total_usd"] += c
                ledger["calls"].append({"task": task, "model": model, "run": run, "usd": c,
                                        "usage": data["usage"], "wall_s": wall})
                save_ledger(ledger)
                out.mkdir(parents=True, exist_ok=True)
                text = "".join(b.get("text", "") for b in data["content"] if b["type"] == "text")
                (out / "request.json").write_text(json.dumps(body, indent=2))
                (out / "response.json").write_text(json.dumps(data, indent=2))
                (out / "response.md").write_text(text)
                (out / "meta.json").write_text(json.dumps({"wall_s": wall, "stop_reason": data.get("stop_reason")}, indent=2))
                sol = out / "solution"
                sol.mkdir(exist_ok=True)
                for name, code in extract_files(text).items():
                    (sol / name).write_text(code)
                print(f"   {wall:.1f}s  in={data['usage']['input_tokens']} out={data['usage']['output_tokens']} "
                      f"stop={data.get('stop_reason')}  (budget guard ok)", flush=True)


def pytest_counts(xml_path):
    if not xml_path.exists():
        return 0, 0
    root = ET.parse(xml_path).getroot()
    suite = root if root.tag == "testsuite" else root.find("testsuite")
    tests = int(suite.get("tests", 0))
    bad = int(suite.get("failures", 0)) + int(suite.get("errors", 0))
    skipped = int(suite.get("skipped", 0))
    return tests - bad - skipped, tests


def score_dir(task, sol_dir, work):
    if work.exists():
        shutil.rmtree(work)
    shutil.copytree(sol_dir, work)
    shutil.copytree(TASKS_DIR / task / "tests", work / "hidden_tests")
    xml = work / "junit.xml"
    env = dict(os.environ, PYTHONPATH=str(work), SOLUTION_DIR=str(work))
    env.pop("ANTHROPIC_API_KEY", None)
    try:
        p = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={xml}",
                            "hidden_tests"], cwd=work, env=env, capture_output=True, text=True, timeout=180)
        log = p.stdout + p.stderr
    except subprocess.TimeoutExpired:
        log = "TIMEOUT"
    passed, total = pytest_counts(xml)
    failed = re.findall(r"^FAILED (\S+)", log, flags=re.M) + re.findall(r"^ERROR (\S+)", log, flags=re.M)
    return passed, total, failed, log


def loc(sol_dir):
    n = 0
    for f in sol_dir.glob("*.py"):
        n += sum(1 for line in f.read_text().splitlines() if line.strip())
    return n


def cmd_score():
    rows = []
    for task in TASKS:
        for model in MODELS:
            for run in range(1, RUNS_PER_MODEL + 1):
                out = RUNS_DIR / task / model / f"run{run}"
                if not (out / "response.json").exists():
                    continue
                resp = json.loads((out / "response.json").read_text())
                meta = json.loads((out / "meta.json").read_text())
                sol = out / "solution"
                passed, total, failed, log = score_dir(task, sol, out / "scored")
                (out / "pytest.log").write_text(log)
                if total == 0:  # collection failed (e.g. missing file); count against the full suite
                    ref = score_dir(task, TASKS_DIR / task / "reference", ROOT / ".tmp_ref")
                    total = ref[1]
                    shutil.rmtree(ROOT / ".tmp_ref", ignore_errors=True)
                shutil.rmtree(out / "scored", ignore_errors=True)
                u = resp["usage"]
                rows.append({
                    "task": task, "model": model, "label": MODELS[model]["label"], "run": run,
                    "passed": passed, "total": total, "pass_rate": passed / total if total else 0.0,
                    "all_passed": passed == total and total > 0,
                    "failed_tests": failed, "wall_s": round(meta["wall_s"], 2),
                    "input_tokens": u.get("input_tokens", 0), "output_tokens": u.get("output_tokens", 0),
                    "thinking_tokens": (u.get("output_tokens_details") or {}).get("thinking_tokens"),
                    "list_price_cost_units": round(cost(model, u) * 1e4, 2), "stop_reason": meta.get("stop_reason"),
                    "loc": loc(sol), "files": sorted(p.name for p in sol.glob("*.py")),
                })
                print(f"{task:18} {MODELS[model]['label']:9} run{run}: {passed}/{total}  "
                      f"{meta['wall_s']:.0f}s  loc={loc(sol)}")
    (ROOT / "scores.json").write_text(json.dumps(rows, indent=2))


def cmd_report():
    """Writes results.json, results.md and chart.png. Cost is expressed only as a
    relative index computed from token counts at list prices (Opus 5.5 = 1.00)."""
    rows = json.loads((ROOT / "scores.json").read_text())
    summary = {}
    for model, p in MODELS.items():
        r = [x for x in rows if x["model"] == model]
        if not r:
            continue
        tp, tt = sum(x["passed"] for x in r), sum(x["total"] for x in r)
        units = sum(x["list_price_cost_units"] for x in r)
        full = sum(1 for x in r if x["all_passed"])
        summary[model] = {
            "label": p["label"], "runs": len(r), "tests_passed": tp, "tests_total": tt,
            "pass_rate": tp / tt if tt else 0, "fully_passing_solutions": full,
            "_units": units, "_units_per_full": (units / full) if full else None,
            "mean_wall_s": sum(x["wall_s"] for x in r) / len(r),
            "mean_input_tokens": sum(x["input_tokens"] for x in r) / len(r),
            "mean_output_tokens": sum(x["output_tokens"] for x in r) / len(r),
            "mean_thinking_tokens": sum((x["thinking_tokens"] or 0) for x in r) / len(r),
            "mean_loc": sum(x["loc"] for x in r) / len(r),
            "per_task": {t: {"tests_passed": sum(x["passed"] for x in r if x["task"] == t),
                             "tests_total": sum(x["total"] for x in r if x["task"] == t),
                             "mean_wall_s": sum(x["wall_s"] for x in r if x["task"] == t) / max(1, len([x for x in r if x["task"] == t])),
                             "mean_output_tokens": sum(x["output_tokens"] for x in r if x["task"] == t) / max(1, len([x for x in r if x["task"] == t]))}
                         for t in TASKS},
        }
    base = summary.get("claude-opus-5-5")
    for s in summary.values():
        s["relative_total_cost_vs_opus"] = round(s["_units"] / base["_units"], 3) if base else None
        s["relative_cost_per_fully_passing_solution_vs_opus"] = (
            round(s["_units_per_full"] / base["_units_per_full"], 3)
            if base and s["_units_per_full"] and base["_units_per_full"] else None)
    for s in summary.values():
        s.pop("_units"); s.pop("_units_per_full")
    opus_runs = [y["list_price_cost_units"] for y in rows if y["model"] == "claude-opus-5-5"]
    opus_mean = sum(opus_runs) / len(opus_runs) if opus_runs else None
    for x in rows:
        u = x.pop("list_price_cost_units")
        x["relative_cost_vs_mean_opus_run"] = round(u / opus_mean, 3) if opus_mean else None
    judge = json.loads((ROOT / "judge" / "judge_result.json").read_text()) if (ROOT / "judge" / "judge_result.json").exists() else None
    results = {
        "date": time.strftime("%Y-%m-%d"),
        "settings": {"max_tokens": MAX_TOKENS, "thinking": "adaptive", "effort": EFFORT, "temperature": "default",
                     "runs_per_model_per_task": RUNS_PER_MODEL,
                     "cost_note": "Costs are relative indices from token counts at Anthropic list prices; Opus 5.5 = 1.0"},
        "runs": rows, "summary": summary, "judge": judge,
    }
    (ROOT / "results.json").write_text(json.dumps(results, indent=2))

    md = ["# Results", "", f"Settings: max_tokens={MAX_TOKENS}, adaptive thinking, effort={EFFORT}, default temperature, "
          f"{RUNS_PER_MODEL} runs per model per task. Cost columns are relative indices computed from token counts at list prices (Opus 5.5 = 1.00).", "",
          "| Task | Model | Run | Tests passed | Wall time (s) | Input tok | Output tok | Thinking tok | LOC | Stop |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for x in rows:
        md.append(f"| {x['task']} | {x['label']} | {x['run']} | {x['passed']}/{x['total']} | {x['wall_s']:.1f} | "
                  f"{x['input_tokens']} | {x['output_tokens']} | {x['thinking_tokens']} | {x['loc']} | {x['stop_reason']} |")
    md += ["", "## Summary", "", "| Model | Tests passed | Pass rate | Fully passing solutions | Relative total cost | Relative cost per fully passing solution | Mean wall time (s) | Mean output tokens | Mean LOC |",
           "|---|---|---|---|---|---|---|---|---|"]
    for s in summary.values():
        cpp = s["relative_cost_per_fully_passing_solution_vs_opus"]
        md.append(f"| {s['label']} | {s['tests_passed']}/{s['tests_total']} | {s['pass_rate']*100:.1f}% | "
                  f"{s['fully_passing_solutions']}/{s['runs']} | {s['relative_total_cost_vs_opus']:.2f}x | "
                  f"{(f'{cpp:.2f}x' if cpp else 'n/a')} | {s['mean_wall_s']:.1f} | {s['mean_output_tokens']:.0f} | {s['mean_loc']:.0f} |")
    md += ["", "## Per task", "", "| Task | Model | Tests passed | Mean wall time (s) | Mean output tokens |", "|---|---|---|---|---|"]
    for t in TASKS:
        for s in summary.values():
            pt = s["per_task"][t]
            md.append(f"| {t} | {s['label']} | {pt['tests_passed']}/{pt['tests_total']} | {pt['mean_wall_s']:.1f} | {pt['mean_output_tokens']:.0f} |")
    fails = [x for x in rows if x["failed_tests"]]
    if fails:
        md += ["", "## Failed tests", ""]
        for x in fails:
            md.append(f"- {x['task']} / {x['label']} run {x['run']}: " + ", ".join(t.split('::')[-1] for t in x["failed_tests"]))
    if judge:
        md += ["", "## Blind code-quality judgement (LLM opinion, not a measurement)", "", judge.get("summary_md", "")]
    (ROOT / "results.md").write_text("\n".join(md) + "\n")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    labels = [s["label"] for s in summary.values()]
    colors = ["#d97706", "#2563eb"]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2))
    axes[0].bar(labels, [s["pass_rate"] * 100 for s in summary.values()], color=colors)
    axes[0].set_title("Hidden-test pass rate (%)"); axes[0].set_ylim(0, 105)
    axes[1].bar(labels, [s["relative_total_cost_vs_opus"] for s in summary.values()], color=colors)
    axes[1].set_title("Relative cost at list prices (Opus = 1.0)")
    axes[2].bar(labels, [s["mean_wall_s"] for s in summary.values()], color=colors)
    axes[2].set_title("Mean wall time per answer (s)")
    for ax in axes:
        for p in ax.patches:
            ax.annotate(f"{p.get_height():.3g}", (p.get_x() + p.get_width() / 2, p.get_height()), ha="center", va="bottom")
    fig.suptitle("Claude Fable 5.2 vs Opus 5.5: 3 coding tasks x 2 runs, effort=medium")
    fig.tight_layout()
    fig.savefig(ROOT / "chart.png", dpi=150)
    print((ROOT / "results.md").read_text())

JUDGE_MODEL = "claude-sonnet-5-5"   # a third model, cheaper than both contestants
JUDGE_PRICE = {"in": 2.0, "out": 10.0}


def cmd_judge():
    """One blind judge call. Solutions are shuffled and labelled S1..S4 per task; the
    mapping is saved before the call. The output is an LLM opinion, not a measurement."""
    import random
    ledger = load_ledger()
    jdir = ROOT / "judge"
    jdir.mkdir(exist_ok=True)
    if (jdir / "judge_result.json").exists():
        print("judge already done"); return
    rng = random.Random(20261110)
    mapping, parts = {}, []
    parts.append("You are reviewing anonymous Python solutions to three coding tasks. All of them already pass the same hidden "
                 "test suite, so focus on code quality: spec fidelity in edge cases the tests may not cover, robustness, "
                 "readability, and maintainability. Be strict and specific. Do not guess which model or author wrote what.\n")
    for task in TASKS:
        sols = [(m, r) for m in MODELS for r in range(1, RUNS_PER_MODEL + 1)]
        rng.shuffle(sols)
        parts.append(f"\n==================== TASK {task} ====================\nSPEC:\n" + (TASKS_DIR / task / "prompt.md").read_text())
        for i, (m, r) in enumerate(sols, 1):
            sid = f"{task}:S{i}"
            mapping[sid] = {"model": m, "run": r}
            code = "".join(f.read_text() + "\n" for f in sorted((RUNS_DIR / task / m / f"run{r}" / "solution").glob("*.py")))
            parts.append(f"\n---------- SOLUTION {sid} ----------\n```python\n{code}```\n")
    parts.append("\nReturn ONLY a JSON object (no code fence) of the form "
                 '{"scores": {"<solution id>": {"spec_fidelity": 1-10, "robustness": 1-10, "readability": 1-10, '
                 '"maintainability": 1-10, "overall": 1-10, "note": "one sentence naming the most important strength or weakness"}}, '
                 '"per_task_best": {"<task>": "<solution id>"}}. Score every solution id listed above.')
    prompt = "".join(parts)
    (jdir / "mapping.json").write_text(json.dumps(mapping, indent=2))
    (jdir / "judge_prompt.md").write_text(prompt)
    worst = len(prompt) / 3 * JUDGE_PRICE["in"] / 1e6 + MAX_TOKENS * JUDGE_PRICE["out"] / 1e6
    if ledger["total_usd"] + worst > BUDGET_USD:
        print("BUDGET GUARD: skipping judge"); return
    data, wall, body = call_model(JUDGE_MODEL, prompt)
    u = data["usage"]
    ledger["total_usd"] += u["input_tokens"] * JUDGE_PRICE["in"] / 1e6 + u["output_tokens"] * JUDGE_PRICE["out"] / 1e6
    ledger["calls"].append({"task": "judge", "model": JUDGE_MODEL, "usage": u, "wall_s": wall})
    save_ledger(ledger)
    (jdir / "judge_response.json").write_text(json.dumps(data, indent=2))
    text = "".join(b.get("text", "") for b in data["content"] if b["type"] == "text").strip()
    text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    parsed = json.loads(text)
    agg = {}
    for sid, sc in parsed["scores"].items():
        m = mapping[sid]["model"]
        agg.setdefault(m, []).append(sc)
    summary = {MODELS[m]["label"]: {k: round(sum(x[k] for x in v) / len(v), 2) for k in
               ("spec_fidelity", "robustness", "readability", "maintainability", "overall")} for m, v in agg.items()}
    best = {t: {"solution": sid, **mapping.get(sid, {})} for t, sid in parsed.get("per_task_best", {}).items()}
    md = ["| Model | Spec fidelity | Robustness | Readability | Maintainability | Overall |", "|---|---|---|---|---|---|"]
    for lab, s in summary.items():
        md.append(f"| {lab} | {s['spec_fidelity']} | {s['robustness']} | {s['readability']} | {s['maintainability']} | {s['overall']} |")
    md.append("")
    md.append(f"Judge model: {JUDGE_MODEL}, one call, solutions anonymised and shuffled. Per-task pick: " +
              ", ".join(f"{t} -> {MODELS[b['model']]['label']} run {b['run']}" for t, b in best.items() if "model" in b))
    result = {"judge_model": JUDGE_MODEL, "is_llm_opinion": True, "mean_scores_by_model": summary,
              "per_task_best": best, "raw_scores": parsed["scores"], "mapping": mapping, "summary_md": "\n".join(md)}
    (jdir / "judge_result.json").write_text(json.dumps(result, indent=2))
    print("\n".join(md))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd in ("run", "all"):
        cmd_run()
    if cmd in ("score", "all"):
        cmd_score()
    if cmd in ("judge", "all"):
        cmd_judge()
    if cmd in ("report", "all"):
        cmd_report()
