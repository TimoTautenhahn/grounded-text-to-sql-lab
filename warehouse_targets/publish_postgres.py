"""Publish the sample CSVs to a PostgreSQL / Aurora target.

Optional. The core lab runs on SQLite with no credentials; use this only when
you want the same orders/returns/people schema in a managed warehouse so you can
point BI tools or a hosted model at it.

All configuration is read from the environment. No hostnames, usernames, or
secrets are hard-coded. For Aurora with IAM authentication, set
``PG_USE_IAM_TOKEN=1`` and let boto3 mint a short-lived token (see
``iam_token.sh`` for the equivalent AWS CLI flow).

    PGHOST            writer endpoint, e.g. your-db.cluster-xxxx.<region>.rds.amazonaws.com
    PGPORT            default 5432
    PGUSER            database user
    PGPASSWORD        password OR an IAM auth token (ignored if PG_USE_IAM_TOKEN=1)
    PG_USE_IAM_TOKEN  1 to mint a token via boto3 (needs valid AWS credentials)
    PG_SSLMODE        default "require"
    PG_TARGET_DB      default "superstore"
    PG_BOOTSTRAP_DB   default "postgres" (where CREATE DATABASE runs)
    DATA_DIR          directory with orders.csv/returns.csv/people.csv (default "data")
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

from _csvload import load_table  # noqa: E402  (local helper, see warehouse_targets/_csvload.py)

NUMERIC = {"sales": "DOUBLE PRECISION", "profit": "DOUBLE PRECISION",
           "discount": "DOUBLE PRECISION", "quantity": "BIGINT"}


def _resolve_password(host: str, port: int, user: str) -> str:
    if os.environ.get("PG_USE_IAM_TOKEN", "").strip().lower() in ("1", "true", "yes"):
        import boto3  # imported lazily; only needed for IAM auth
        region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"
        rds = boto3.client("rds", region_name=region)
        return rds.generate_db_auth_token(DBHostname=host, Port=port, DBUsername=user, Region=region)
    pw = os.environ.get("PGPASSWORD", "").strip()
    if not pw:
        raise SystemExit("Set PGPASSWORD, or PG_USE_IAM_TOKEN=1 with valid AWS credentials.")
    return pw


def _column_type(col: str) -> str:
    return NUMERIC.get(col, "TEXT")


def main() -> None:
    host = os.environ.get("PGHOST", "").strip()
    user = os.environ.get("PGUSER", "").strip()
    if not host or not user:
        raise SystemExit("Set PGHOST and PGUSER (writer endpoint and database user).")
    port = int(os.environ.get("PGPORT", "5432"))
    sslmode = os.environ.get("PG_SSLMODE", "require")
    target_db = os.environ.get("PG_TARGET_DB", "superstore").lower()
    bootstrap_db = os.environ.get("PG_BOOTSTRAP_DB", "postgres")
    data_dir = Path(os.environ.get("DATA_DIR", "data"))
    password = _resolve_password(host, port, user)

    base = dict(host=host, port=port, user=user, password=password,
                sslmode=sslmode, connect_timeout=60)

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
        print(f"Published orders/returns/people to database '{target_db}' on {host}.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
