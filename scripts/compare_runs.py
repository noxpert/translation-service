#!/usr/bin/env python3
"""Compare 2-3 integration/performance result files.

Each input is a ``results_*.json`` produced by the integration suite. Use it to
compare two runs of the *same* model (e.g. before/after a code change, to spot
performance regressions) or runs of *different* models against the same cases.

Usage:
    scripts/compare_runs.py RUN_A.json RUN_B.json [RUN_C.json] [--md OUT.md]

Output is a Markdown report (printed to stdout; also written to OUT.md when
``--md`` is given). Dependency-free — runs with plain python3.
"""

import argparse
import json
import sys
from pathlib import Path


def _ollama_total_ms(calls) -> float:
    if isinstance(calls, dict):
        return sum(calls.values())
    if isinstance(calls, list):
        return sum(calls)
    return 0.0


def load_run(path: str) -> dict:
    data = json.loads(Path(path).read_text())
    records = {(r["endpoint"], r["case_id"]): r for r in data.get("records", [])}
    generated = (data.get("generated") or "")[:19]
    return {
        "path": path,
        "model": data.get("model", "?"),
        "generated": generated,
        "label": f'{data.get("model", "?")} @ {generated or "?"}',
        "records": records,
    }


def _cell(rec: dict | None) -> str:
    if rec is None:
        return "—"
    mark = "✅" if rec.get("passed") else "❌"
    return f"{mark} {_ollama_total_ms(rec.get('ollama_calls_ms')):.0f}ms"


def build_report(runs: list[dict]) -> str:
    n = len(runs)
    lines: list[str] = ["# Integration run comparison", ""]
    for i, run in enumerate(runs, 1):
        gen = run["generated"] or "?"
        lines.append(f"- **[{i}]** `{run['model']}` — {gen}  ·  `{run['path']}`")
    lines.append("")
    lines.append(
        "Cells show pass/fail and total Ollama time per case. "
        f"Δ is run [{n}] minus run [1] (negative = faster/improved)."
    )
    lines.append("")

    all_keys = sorted({k for run in runs for k in run["records"]})
    endpoints = sorted({ep for ep, _ in all_keys})

    for ep in endpoints:
        header = ["case"] + [f"[{i}]" for i in range(1, n + 1)]
        if n >= 2:
            header.append("Δ ms")
        lines.append(f"## `{ep}`")
        lines.append("")
        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + "|".join(["---"] * len(header)) + "|")

        for ep2, case_id in [k for k in all_keys if k[0] == ep]:
            recs = [run["records"].get((ep2, case_id)) for run in runs]
            row = [case_id] + [_cell(r) for r in recs]
            if n >= 2:
                first, last = recs[0], recs[-1]
                if first and last:
                    delta = _ollama_total_ms(last.get("ollama_calls_ms")) - _ollama_total_ms(
                        first.get("ollama_calls_ms")
                    )
                    row.append(f"{delta:+.0f}")
                else:
                    row.append("—")
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")

    # Summary across all cases.
    lines.append("## Summary")
    lines.append("")
    lines.append("| run | model | passed | mean ollama ms | mean wall ms |")
    lines.append("|---|---|---|---|---|")
    for i, run in enumerate(runs, 1):
        recs = list(run["records"].values())
        passed = sum(1 for r in recs if r.get("passed"))
        ollama = [_ollama_total_ms(r.get("ollama_calls_ms")) for r in recs]
        walls = [r.get("wall_ms", 0.0) for r in recs]
        mean_o = sum(ollama) / len(ollama) if ollama else 0.0
        mean_w = sum(walls) / len(walls) if walls else 0.0
        lines.append(
            f"| [{i}] | {run['model']} | {passed}/{len(recs)} | {mean_o:.0f} | {mean_w:.0f} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("runs", nargs="+", help="2-3 results_*.json files")
    parser.add_argument("--md", metavar="OUT.md", help="also write the report to this file")
    args = parser.parse_args()

    if not 2 <= len(args.runs) <= 3:
        parser.error("provide 2 or 3 result files to compare")

    runs = [load_run(p) for p in args.runs]
    report = build_report(runs)
    print(report)
    if args.md:
        Path(args.md).write_text(report)
        print(f"\nWrote {args.md}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
