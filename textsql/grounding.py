"""Build the schema-grounding context a text-to-SQL model needs.

Grounding is the difference between a model that guesses column names and one
that writes runnable SQL. This module introspects the live warehouse and emits
a compact, deterministic schema description (tables, columns, types, a few
example values) that can be dropped straight into a prompt.
"""

from __future__ import annotations

import sqlite3


def _tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]


def _columns(conn: sqlite3.Connection, table: str) -> list[tuple[str, str]]:
    rows = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
    # cid, name, type, notnull, dflt_value, pk
    return [(r[1], r[2] or "TEXT") for r in rows]


def _sample_values(conn: sqlite3.Connection, table: str, column: str, limit: int = 3) -> list[str]:
    rows = conn.execute(
        f'SELECT DISTINCT "{column}" FROM "{table}" WHERE "{column}" IS NOT NULL LIMIT ?',
        (limit,),
    ).fetchall()
    return [str(r[0]) for r in rows]


def schema_context(conn: sqlite3.Connection, include_samples: bool = True) -> str:
    """Return a prompt-ready description of the warehouse schema."""
    lines: list[str] = []
    for table in _tables(conn):
        cols = _columns(conn, table)
        lines.append(f"TABLE {table}:")
        for name, ctype in cols:
            suffix = ""
            if include_samples and ctype.upper() == "TEXT":
                samples = _sample_values(conn, table, name)
                if samples:
                    suffix = "  e.g. " + ", ".join(repr(s) for s in samples)
            lines.append(f"  - {name} ({ctype}){suffix}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
