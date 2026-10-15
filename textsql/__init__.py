"""Grounded text-to-SQL evaluation lab.

A small, dependency-free harness that stands up a real analytical SQL warehouse
from generated sample data, builds the schema-grounding context an LLM needs,
and scores candidate SQL by execution match against a gold set.
"""

__all__ = ["warehouse", "grounding", "gold", "baselines", "evaluate"]
