"""Execution-match evaluation for text-to-SQL.

Comparing SQL strings is brittle: many different queries return the same answer.
This evaluator instead runs both the candidate SQL and the gold SQL against the
warehouse and compares their *result sets*. That is the metric that matters for
a text-to-SQL system: does the query return the right data?

Result sets are compared order-insensitively unless the gold SQL contains an
ORDER BY, in which case row order is significant.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from .baselines import CandidateProvider
from .gold import GOLD, GoldItem
from .grounding import schema_context


@dataclass
class CaseResult:
    id: str
    question: str
    correct: bool
    error: str | None
    candidate_sql: str


@dataclass
class EvalReport:
    results: list[CaseResult]

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.correct)

    @property
    def accuracy(self) -> float:
        return self.passed / self.total if self.total else 0.0

    def table(self) -> str:
        lines = [f"{'id':<5} {'ok':<3} question", "-" * 60]
        for r in self.results:
            mark = "ok" if r.correct else ("ERR" if r.error else "x")
            lines.append(f"{r.id:<5} {mark:<3} {r.question}")
        lines.append("-" * 60)
        lines.append(f"Execution accuracy: {self.passed}/{self.total} = {self.accuracy:.1%}")
        return "\n".join(lines)


def _run(conn: sqlite3.Connection, sql: str) -> list[tuple]:
    return conn.execute(sql).fetchall()


def _ordered(sql: str) -> bool:
    return "order by" in sql.lower()


def _matches(gold_sql: str, gold_rows: list[tuple], cand_rows: list[tuple]) -> bool:
    if _ordered(gold_sql):
        return gold_rows == cand_rows
    return sorted(map(repr, gold_rows)) == sorted(map(repr, cand_rows))


def evaluate(
    conn: sqlite3.Connection,
    provider: CandidateProvider,
    gold: list[GoldItem] | None = None,
) -> EvalReport:
    gold = gold if gold is not None else GOLD
    schema = schema_context(conn)
    results: list[CaseResult] = []
    for item in gold:
        candidate_sql = provider(item.question, schema)
        error: str | None = None
        correct = False
        try:
            gold_rows = _run(conn, item.sql)
            cand_rows = _run(conn, candidate_sql)
            correct = _matches(item.sql, gold_rows, cand_rows)
        except sqlite3.Error as exc:
            error = str(exc)
        results.append(CaseResult(item.id, item.question, correct, error, candidate_sql))
    return EvalReport(results)
