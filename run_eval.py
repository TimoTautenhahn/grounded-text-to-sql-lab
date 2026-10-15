#!/usr/bin/env python3
"""End-to-end entry point: build the warehouse, run an evaluation, print the score.

    python samples/generate.py --out data      # once, to create the sample data
    python run_eval.py                          # naive keyword baseline
    python run_eval.py --provider gold          # harness self-test (must be 100%)

Plug in a real model by importing textsql.evaluate.evaluate with your own
CandidateProvider instead of the baselines below.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from textsql import warehouse
from textsql.baselines import GoldReplayProvider, KeywordHeuristicProvider
from textsql.evaluate import evaluate

PROVIDERS = {
    "keyword": KeywordHeuristicProvider,
    "gold": GoldReplayProvider,
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", type=Path, default=Path("data"), help="directory with the CSVs")
    ap.add_argument("--provider", choices=sorted(PROVIDERS), default="keyword")
    args = ap.parse_args()

    conn = warehouse.build(args.data)
    try:
        report = evaluate(conn, PROVIDERS[args.provider]())
    finally:
        conn.close()
    print(f"Provider: {args.provider}")
    print(report.table())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
