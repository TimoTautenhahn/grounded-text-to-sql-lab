#!/usr/bin/env python3
"""End-to-end entry point: build the warehouse, run an evaluation, print the score.

    python samples/generate.py --out data              # once, to create the sample data
    python run_eval.py                                  # naive keyword baseline
    python run_eval.py --provider gold                  # harness self-test (must be 100%)
    python run_eval.py --provider llm --model gpt-4o-mini          # a real model (needs a key)
    python run_eval.py --provider llm --model A --model B          # compare models -> results/latest.md

For the llm provider, configure the API only through the environment
(OPENAI_API_KEY, optional OPENAI_BASE_URL for an OpenAI-compatible endpoint).
Without a key the command prints a clear message and exits without a traceback.
"""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

from textsql import warehouse
from textsql.baselines import GoldReplayProvider, KeywordHeuristicProvider
from textsql.evaluate import EvalReport, evaluate

OFFLINE_PROVIDERS = {
    "keyword": KeywordHeuristicProvider,
    "gold": GoldReplayProvider,
}


def _write_results_md(path: Path, rows: list[tuple[str, EvalReport]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Text-to-SQL evaluation ({dt.datetime.now():%Y-%m-%d %H:%M})",
        "",
        "| Model | Passed | Total | Execution accuracy |",
        "|---|---|---|---|",
    ]
    for model, report in rows:
        lines.append(f"| {model} | {report.passed} | {report.total} | {report.accuracy:.1%} |")
    lines.append("")
    path.write_text("\n".join(lines))


def _run_llm(args) -> int:
    # Imported lazily so the offline lab never needs this module.
    from textsql.providers.openai_compatible import MissingApiKey, OpenAICompatibleProvider

    models = args.model or []
    if not models:
        print("Provide at least one --model for --provider llm.")
        return 2

    conn = warehouse.build(args.data)
    results: list[tuple[str, EvalReport]] = []
    try:
        for model in models:
            try:
                provider = OpenAICompatibleProvider(model=model, base_url=args.base_url)
            except MissingApiKey as exc:
                print(str(exc))
                return 1
            report = evaluate(conn, provider)
            print(f"Provider: llm  Model: {model}")
            print(report.table())
            print()
            results.append((model, report))
    finally:
        conn.close()

    if len(results) >= 1:
        out = Path(args.results)
        _write_results_md(out, results)
        print(f"Wrote comparison table to {out}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, default=Path("data"), help="directory with the CSVs")
    ap.add_argument("--provider", choices=[*sorted(OFFLINE_PROVIDERS), "llm"], default="keyword")
    ap.add_argument("--model", action="append",
                    help="model id for --provider llm; repeat to compare models")
    ap.add_argument("--base-url", default=None,
                    help="OpenAI-compatible base URL (else OPENAI_BASE_URL)")
    ap.add_argument("--results", default="results/latest.md",
                    help="markdown comparison output for --provider llm")
    args = ap.parse_args()

    if args.provider == "llm":
        return _run_llm(args)

    conn = warehouse.build(args.data)
    try:
        report = evaluate(conn, OFFLINE_PROVIDERS[args.provider]())
    finally:
        conn.close()
    print(f"Provider: {args.provider}")
    print(report.table())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
