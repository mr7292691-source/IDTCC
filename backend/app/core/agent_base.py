"""Shared agent contract: confidence, explainability, and instrumentation.

Every agent in IDTCC returns the same envelope on top of its domain payload:

    {
      ... domain fields ...,
      "confidence": 0.94,
      "explainability": {
          "why": "...",
          "inputs_used": [...],
          "evidence": {...}
      }
    }

`confidence` is computed deterministically from data quality signals (sample
coverage, presence of the LLM narrative, agreement of computed vs. expected
ranges) — it is never asked from the LLM, so it cannot be hallucinated.

`@instrument` wraps each agent to record latency / success metrics, emit
structured logs, and convert any exception into a graceful degraded envelope so
one failing agent never crashes the pipeline.
"""
from __future__ import annotations

import functools
import logging
import time
from typing import Any, Callable, Dict, List

from app.core.logging_config import get_logger, log_event
from app.core.metrics import METRICS

log = get_logger("idtcc.agent")


def build_explainability(why: str, inputs_used: List[str],
                         evidence: Dict[str, Any]) -> Dict[str, Any]:
    """Construct the standard explainability block for an agent decision."""
    return {
        "why": why,
        "inputs_used": inputs_used,
        "evidence": evidence,
    }


def compute_confidence(*, data_coverage: float = 1.0,
                       has_narrative: bool = True,
                       within_expected_range: bool = True,
                       penalty: float = 0.0) -> float:
    """Deterministic confidence in [0, 1].

    Weighting:
      0.45  data coverage (fraction of the portfolio actually analysed)
      0.30  computed metrics fell inside expected actuarial ranges
      0.15  the LLM narrative was generated (vs. offline fallback)
      0.10  base floor
    `penalty` (0-1) is subtracted, e.g. for guardrail violations.
    """
    score = (
        0.45 * max(0.0, min(1.0, data_coverage))
        + 0.30 * (1.0 if within_expected_range else 0.0)
        + 0.15 * (1.0 if has_narrative else 0.0)
        + 0.10
    )
    return round(max(0.0, min(1.0, score - penalty)), 3)


def attach(output: Dict[str, Any], *, confidence: float, why: str,
           inputs_used: List[str], evidence: Dict[str, Any]) -> Dict[str, Any]:
    """Attach the confidence + explainability envelope to an agent payload."""
    output["confidence"] = round(float(confidence), 3)
    output["explainability"] = build_explainability(why, inputs_used, evidence)
    return output


def instrument(agent_name: str) -> Callable:
    """Decorator: time the agent, record metrics, log, and never raise."""
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Dict[str, Any]:
            start = time.perf_counter()
            METRICS.inc("idtcc_agent_runs_total", agent=agent_name)
            try:
                result = fn(*args, **kwargs)
                elapsed = time.perf_counter() - start
                METRICS.observe("idtcc_agent_latency_seconds", elapsed, agent=agent_name)
                conf = result.get("confidence") if isinstance(result, dict) else None
                log_event(log, logging.INFO, "agent.done", agent=agent_name,
                          latency_ms=round(elapsed * 1000, 1), confidence=conf)
                return result
            except Exception as exc:  # noqa: BLE001 — agents must degrade, not crash
                elapsed = time.perf_counter() - start
                METRICS.observe("idtcc_agent_latency_seconds", elapsed, agent=agent_name)
                METRICS.inc("idtcc_agent_errors_total", agent=agent_name)
                log_event(log, logging.ERROR, "agent.error", agent=agent_name,
                          latency_ms=round(elapsed * 1000, 1), error=str(exc))
                return attach(
                    {"error": str(exc), "degraded": True},
                    confidence=0.0,
                    why=f"{agent_name} failed: {exc}",
                    inputs_used=[],
                    evidence={"exception": type(exc).__name__},
                )
        return wrapper
    return decorator
