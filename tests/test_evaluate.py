"""Tests for the execution-match evaluator, using a small in-memory warehouse."""

import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from textsql.baselines import GoldReplayProvider, KeywordHeuristicProvider  # noqa: E402
from textsql.evaluate import evaluate  # noqa: E402
from textsql.gold import GOLD, GoldItem  # noqa: E402


def _fixture() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE orders (order_id TEXT, order_date TEXT, ship_mode TEXT, "
        "customer_id TEXT, segment TEXT, region TEXT, category TEXT, "
        "sales REAL, quantity INTEGER, discount REAL, profit REAL)"
    )
    rows = [
        ("OR-1", "2023-02-01", "Standard Class", "CU-1", "Consumer", "West", "Technology", 100.0, 2, 0.1, 20.0),
        ("OR-2", "2023-03-01", "First Class", "CU-2", "Corporate", "Central", "Furniture", 200.0, 1, 0.0, 50.0),
        ("OR-3", "2022-05-01", "Standard Class", "CU-1", "Consumer", "West", "Technology", 50.0, 3, 0.2, -5.0),
    ]
    conn.executemany("INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
    conn.execute("CREATE TABLE returns (order_id TEXT, returned TEXT)")
    conn.executemany(
        "INSERT INTO returns VALUES (?,?)",
        [("OR-1", "Yes"), ("OR-2", "No"), ("OR-3", "Yes")],
    )
    conn.execute("CREATE TABLE people (region TEXT, person TEXT)")
    conn.executemany(
        "INSERT INTO people VALUES (?,?)",
        [("West", "Robin Diaz"), ("Central", "Alex Rivera")],
    )
    conn.commit()
    return conn


class EvaluateTests(unittest.TestCase):
    def test_gold_provider_is_perfect(self):
        conn = _fixture()
        report = evaluate(conn, GoldReplayProvider())
        self.assertEqual(report.passed, report.total)
        self.assertEqual(report.accuracy, 1.0)
        conn.close()

    def test_keyword_baseline_is_partial(self):
        conn = _fixture()
        report = evaluate(conn, KeywordHeuristicProvider())
        # The naive baseline should get some right but not all; that is the point.
        self.assertGreater(report.passed, 0)
        self.assertLess(report.passed, report.total)
        conn.close()

    def test_wrong_sql_is_counted_wrong(self):
        conn = _fixture()
        wrong = GoldItem("x", "dummy", "SELECT 999")
        report = evaluate(conn, GoldReplayProvider(), gold=[wrong])
        self.assertEqual(report.passed, 0)
        conn.close()

    def test_order_sensitivity(self):
        conn = _fixture()
        # Gold has ORDER BY region; a reversed order must NOT match.
        gold = GoldItem(
            "o", "profit by region",
            "SELECT region, SUM(profit) FROM orders GROUP BY region ORDER BY region",
        )

        class Reversed:
            def __call__(self, q, s):
                return "SELECT region, SUM(profit) FROM orders GROUP BY region ORDER BY region DESC"

        report = evaluate(conn, Reversed(), gold=[gold])
        self.assertEqual(report.passed, 0)
        conn.close()

    def test_all_gold_sql_executes(self):
        # Every gold query must run against the real generated schema shape.
        conn = _fixture()
        for item in GOLD:
            try:
                conn.execute(item.sql).fetchall()
            except sqlite3.Error as exc:  # pragma: no cover
                self.fail(f"gold {item.id} failed: {exc}")
        conn.close()


if __name__ == "__main__":
    unittest.main()
