"""Offline tests for the OpenAI-compatible provider (no network).

The HTTP call is monkeypatched, so these never touch a real API or need a key.
"""

import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from textsql.evaluate import evaluate  # noqa: E402
from textsql.gold import GoldItem  # noqa: E402
from textsql.providers.openai_compatible import (  # noqa: E402
    MissingApiKey,
    OpenAICompatibleProvider,
    _extract_sql,
)


def _fixture() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE orders (order_id TEXT, sales REAL)")
    conn.executemany("INSERT INTO orders VALUES (?,?)", [("OR-1", 100.0), ("OR-2", 50.0)])
    conn.commit()
    return conn


class ExtractSqlTests(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(_extract_sql("SELECT 1"), "SELECT 1")

    def test_sql_fence(self):
        self.assertEqual(_extract_sql("```sql\nSELECT 1;\n```"), "SELECT 1")

    def test_bare_fence_and_label(self):
        self.assertEqual(_extract_sql("```\nSQL: SELECT 1\n```"), "SELECT 1")


class ProviderTests(unittest.TestCase):
    def test_missing_key_raises(self):
        with self.assertRaises(MissingApiKey):
            OpenAICompatibleProvider(model="m", api_key="")

    def test_evaluate_with_mocked_model(self):
        provider = OpenAICompatibleProvider(model="m", api_key="test-key")
        # Replace the network call with a canned, correct answer.
        provider._chat = lambda messages: "```sql\nSELECT ROUND(SUM(sales),2) FROM orders\n```"
        conn = _fixture()
        gold = [GoldItem("q", "total sales", "SELECT ROUND(SUM(sales),2) FROM orders")]
        report = evaluate(conn, provider, gold=gold)
        self.assertEqual(report.accuracy, 1.0)
        conn.close()

    def test_wrong_model_answer_scored_wrong(self):
        provider = OpenAICompatibleProvider(model="m", api_key="test-key")
        provider._chat = lambda messages: "SELECT 0"
        conn = _fixture()
        gold = [GoldItem("q", "total sales", "SELECT ROUND(SUM(sales),2) FROM orders")]
        report = evaluate(conn, provider, gold=gold)
        self.assertEqual(report.passed, 0)
        conn.close()


if __name__ == "__main__":
    unittest.main()
