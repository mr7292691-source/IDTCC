"""LifeShield life-safety agents (Lens B).

Each agent follows the exact same contract as the insurance agents: a plain
``run(...)`` decorated with ``@instrument`` returning the shared
confidence + explainability envelope via ``attach()``. Scoring is deterministic
(auditable, never hallucinated); the LLM only writes the human-readable
narrative.
"""
