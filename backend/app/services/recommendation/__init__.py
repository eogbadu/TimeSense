"""Deterministic recommendation engine (recommendation-engine-build-spec.md).

Pipeline: normalize context → generate candidates → score → rank → select. The LLM is never the
decision-maker; it only explains the selected recommendation (added in a later phase)."""
