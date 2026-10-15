"""Tests for schema grounding and the SQLite warehouse loader."""

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from samples.generate import write_dataset  # noqa: E402
from textsql import warehouse  # noqa: E402
from textsql.grounding import schema_context  # noqa: E402


class GroundingTests(unittest.TestCase):
    def test_build_from_generated_samples(self):
        with TemporaryDirectory() as d:
            data = Path(d)
            write_dataset(data, rows=100, seed=1)
            conn = warehouse.build(data)
            count = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
            self.assertEqual(count, 100)
            conn.close()

    def test_schema_context_lists_all_tables(self):
        with TemporaryDirectory() as d:
            data = Path(d)
            write_dataset(data, rows=20, seed=2)
            conn = warehouse.build(data)
            ctx = schema_context(conn)
            for table in ("orders", "returns", "people"):
                self.assertIn(f"TABLE {table}:", ctx)
            self.assertIn("sales (REAL)", ctx)
            conn.close()

    def test_missing_data_dir_raises_helpful_error(self):
        with TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError):
                warehouse.build(Path(d))


if __name__ == "__main__":
    unittest.main()
