"""Candidate SQL providers backed by a real model.

The core lab ships offline baselines in ``textsql.baselines``. This package adds
an optional provider that calls any OpenAI-compatible chat API. It is imported
lazily so the lab still runs with no network and no third-party packages.
"""

__all__ = ["openai_compatible"]
