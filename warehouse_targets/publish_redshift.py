"""Publish the sample CSVs to an Amazon Redshift target.

Optional, same role as publish_postgres.py. Configuration is environment-only;
no credentials are stored in files. Connection uses the Postgres wire protocol.

    REDSHIFT_HOST, REDSHIFT_USER, REDSHIFT_PASSWORD    required
    REDSHIFT_PORT         default 5439
    REDSHIFT_DB           default "superstore"
    REDSHIFT_BOOTSTRAP_DB default "dev"
    DATA_DIR              directory with the CSVs (default "data")
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    import psycopg2
    from psycopg2 import sql
    from psycopg2.extras import execute_values
except ImportError as exc:  # pragma: no cover - optional dependency
    raise SystemExit("This optional target needs psycopg2: pip install psycopg2-binary") from exc

from _csvload import load_table  # noqa: E402

NUMERIC = {"sales": "DOUBLE PRECISION", "profit": "DOUBLE PRECISION",
           "discount": "DOUBLE PRECISION", "quantity": "BIGINT"}


def _column_type(col: str) -> str:
    return NUMERIC.get(col, "VARCHAR(65535)")


def main() -> None:
    host = os.environ.get("REDSHIFT_HOST", "").strip()
    user = os.environ.get("REDSHIFT_USER", "").strip()
    password = os.environ.get("REDSHIFT_PASSWORD", "").strip()
    if not host or not user or not password:
        raise SystemExit("Set REDSHIFT_HOST, REDSHIFT_USER and REDSHIFT_PASSWORD.")
    port = int(os.environ.get("REDSHIFT_PORT", "5439"))
    target_db = os.environ.get("REDSHIFT_DB", "superstore").lower()
    bootstrap_db = os.environ.get("REDSHIFT_BOOTSTRAP_DB", "dev")
    data_dir = Path(os.environ.get("DATA_DIR", "data"))

    base = dict(host=host, port=port, user=user, password=password, connect_timeout=30)

    admin = psycopg2.connect(dbname=bootstrap_db, **base)
    admin.autocommit = True
    with admin.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_db,))
        if cur.fetchone() is None:
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(target_db)))
    admin.close()

    conn = psycopg2.connect(dbname=target_db, **base)
    try:
        with conn.cursor() as cur:
            for table in ("orders", "returns", "people"):
                header, rows = load_table(data_dir / f"{table}.csv")
                col_defs = sql.SQL(", ").join(
                    sql.SQL("{} {}").format(sql.Identifier(c), sql.SQL(_column_type(c)))
                    for c in header
                )
                cur.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(sql.Identifier(table)))
                cur.execute(sql.SQL("CREATE TABLE {} ({})").format(sql.Identifier(table), col_defs))
                cols = sql.SQL(", ").join(sql.Identifier(c) for c in header)
                insert = sql.SQL("INSERT INTO {} ({}) VALUES %s").format(
                    sql.Identifier(table), cols
                )
                execute_values(cur, insert.as_string(conn), rows, page_size=500)
        conn.commit()
        print(f"Published orders/returns/people to Redshift database '{target_db}'.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
