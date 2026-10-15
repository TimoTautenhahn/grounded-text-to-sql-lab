"""Build a local SQLite warehouse from CSVs so the lab runs fully offline.

The same ``orders / returns / people`` schema is used by the optional cloud
publishers in ``warehouse_targets/``. Keeping a SQLite mirror means evaluation
needs no credentials, no network, and no third-party database to be reproducible.
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

# Column -> SQLite affinity. Everything else is TEXT.
_NUMERIC = {"sales": "REAL", "profit": "REAL", "discount": "REAL", "quantity": "INTEGER"}

_TABLES = {
    "orders": None,  # columns inferred from CSV header
    "returns": ["order_id", "returned"],
    "people": ["region", "person"],
}


def _column_type(name: str) -> str:
    return _NUMERIC.get(name, "TEXT")


def _load_csv(path: Path) -> tuple[list[str], list[tuple]]:
    with path.open(newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = [tuple(r) for r in reader]
    return header, rows


def _coerce(header: list[str], rows: list[tuple]) -> list[tuple]:
    out = []
    for row in rows:
        values = []
        for col, raw in zip(header, row):
            t = _column_type(col)
            if raw == "":
                values.append(None)
            elif t == "REAL":
                values.append(float(raw))
            elif t == "INTEGER":
                values.append(int(float(raw)))
            else:
                values.append(raw)
        out.append(tuple(values))
    return out


def build(data_dir: Path, db_path: str | Path = ":memory:") -> sqlite3.Connection:
    """Create and populate the warehouse. Returns an open connection."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    for table in _TABLES:
        csv_path = Path(data_dir) / f"{table}.csv"
        if not csv_path.is_file():
            raise FileNotFoundError(
                f"Missing {csv_path}. Run `python samples/generate.py --out {data_dir}` first."
            )
        header, rows = _load_csv(csv_path)
        col_defs = ", ".join(f'"{c}" {_column_type(c)}' for c in header)
        conn.execute(f'DROP TABLE IF EXISTS "{table}"')
        conn.execute(f'CREATE TABLE "{table}" ({col_defs})')
        placeholders = ", ".join("?" for _ in header)
        conn.executemany(
            f'INSERT INTO "{table}" VALUES ({placeholders})', _coerce(header, rows)
        )
    conn.commit()
    return conn
