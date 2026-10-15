"""Candidate SQL providers.

A provider maps a natural-language question (plus the schema-grounding context)
to a SQL string. This is the seam where a real LLM plugs in. The lab ships two
offline providers so the evaluation runs end-to-end with no API key:

* ``GoldReplayProvider`` returns the reference SQL. It is a harness self-test:
  execution accuracy must be 1.0, otherwise the evaluator itself is broken.
* ``KeywordHeuristicProvider`` is a deliberately naive rule-based baseline. It
  gets the easy aggregates right and misses the harder joins/filters, which is
  what makes it useful: it shows the metric discriminates.

To evaluate a real model, implement the ``CandidateProvider`` protocol with a
function that calls your LLM, passing ``grounding.schema_context(conn)``.
"""

from __future__ import annotations

import re
from typing import Protocol

from .gold import GOLD


class CandidateProvider(Protocol):
    def __call__(self, question: str, schema: str) -> str: ...


class GoldReplayProvider:
    """Returns the gold SQL for a known question (harness self-test)."""

    def __init__(self) -> None:
        self._by_question = {item.question: item.sql for item in GOLD}

    def __call__(self, question: str, schema: str) -> str:
        return self._by_question.get(question, "SELECT 1 WHERE 0")


class KeywordHeuristicProvider:
    """A naive, LLM-free baseline driven by keyword matching."""

    def __call__(self, question: str, schema: str) -> str:
        q = question.lower()
        if "how many orders" in q:
            return "SELECT COUNT(DISTINCT order_id) FROM orders"
        if "total sales" in q and "2023" not in q and "category" not in q:
            return "SELECT ROUND(SUM(sales), 2) FROM orders"
        if "profit per region" in q:
            return "SELECT region, ROUND(SUM(profit), 2) FROM orders GROUP BY region ORDER BY region"
        if "highest total sales" in q and "category" in q:
            return "SELECT category FROM orders GROUP BY category ORDER BY SUM(sales) DESC LIMIT 1"
        if "returned" in q and "how many" in q:
            return "SELECT COUNT(*) FROM returns WHERE returned = 'Yes'"
        if "average discount" in q:
            m = re.search(r"in the (\w+) category", q)
            cat = m.group(1).title() if m else "Technology"
            return f"SELECT ROUND(AVG(discount), 4) FROM orders WHERE category = '{cat}'"
        # Everything else: a plausible-but-wrong guess, so the metric can catch it.
        return "SELECT COUNT(*) FROM orders"
