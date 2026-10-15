"""Shared CSV loader for the optional warehouse publishers."""

from __future__ import annotations

import csv
from pathlib import Path

_NUMERIC = {"sales": float, "profit": float, "discount": float, "quantity": int}


def load_table(path: Path) -> tuple[list[str], list[tuple]]:
    if not path.is_file():
        raise SystemExit(f"Missing {path}. Run `python samples/generate.py --out {path.parent}` first.")
    with path.open(newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows: list[tuple] = []
        for raw in reader:
            values = []
            for col, cell in zip(header, raw):
                caster = _NUMERIC.get(col)
                if cell == "":
                    values.append(None)
                elif caster is int:
                    values.append(int(float(cell)))
                elif caster is float:
                    values.append(float(cell))
                else:
                    values.append(cell)
            rows.append(tuple(values))
    return header, rows
