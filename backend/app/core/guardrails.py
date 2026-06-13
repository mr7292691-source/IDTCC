"""Hallucination guardrails for agent outputs.

Three layers, matching the hackathon requirement:

1. Structured output validation — robustly extract + coerce JSON from LLM text.
2. Fact verification          — sanity-bound numeric outputs against ground truth
                                computed from the digital-twin DataFrame.
3. Cross-agent consistency    — detect contradictions between agents (e.g. claims
                                count exceeding twins in the impact radius).

These run deterministically on top of the LLM so a confident-but-wrong model
cannot silently corrupt the forecast.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional


# ── 1. Structured output validation ──────────────────────────────────────────

def extract_json(raw: str) -> Optional[Dict[str, Any]]:
    """Pull the first balanced JSON object out of an LLM response.

    Handles ```json fenced blocks, leading prose, and trailing commentary.
    Returns None if nothing parseable is found (caller supplies a fallback).
    """
    if not raw:
        return None

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    candidate = fenced.group(1) if fenced else None

    if candidate is None:
        start = raw.find("{")
        if start == -1:
            return None
        depth = 0
        for i in range(start, len(raw)):
            if raw[i] == "{":
                depth += 1
            elif raw[i] == "}":
                depth -= 1
                if depth == 0:
                    candidate = raw[start : i + 1]
                    break
    if candidate is None:
        return None
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        # Tolerate trailing commas, which small models emit frequently.
        cleaned = re.sub(r",\s*([}\]])", r"\1", candidate)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return None


def coerce_float(value: Any, default: float, lo: float = float("-inf"),
                 hi: float = float("inf")) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return default
    if v != v:  # NaN
        return default
    return max(lo, min(hi, v))


# ── 2. Fact verification ─────────────────────────────────────────────────────

def verify_numeric_bounds(value: float, lo: float, hi: float, label: str,
                          violations: List[str]) -> float:
    """Clamp a value to plausible bounds and record any violation."""
    if value < lo or value > hi:
        violations.append(f"{label}={value} outside [{lo}, {hi}] — clamped")
        return max(lo, min(hi, value))
    return value


# ── 3. Cross-agent consistency ───────────────────────────────────────────────

def check_consistency(state: Dict[str, Any]) -> Dict[str, Any]:
    """Compare agent outputs for logical contradictions.

    Returns a report: list of issues + a 0-1 consistency score used to gate the
    overall forecast confidence.
    """
    issues: List[str] = []

    risk     = state.get("risk_output", {})    or {}
    claims   = state.get("claims_output", {})  or {}
    fraud    = state.get("fraud_output", {})   or {}
    reserve  = state.get("reserve_output", {}) or {}
    resource = state.get("resource_output", {}) or {}

    total_twins   = risk.get("total_portfolio_twins", 0) or 0
    in_radius     = risk.get("twins_in_impact_radius", 0) or 0
    red_twins     = claims.get("red_twin_count", 0) or 0
    exp_claims    = claims.get("expected_claim_count", 0) or 0
    exp_loss      = claims.get("expected_total_loss_crore", 0.0) or 0.0
    total_reserve = reserve.get("total_recommended_reserve_crore", 0.0) or 0.0
    fraud_twins   = fraud.get("total_fraud_risk_twins", 0) or 0

    # Containment: subsets cannot exceed their parents.
    if in_radius > total_twins and total_twins:
        issues.append(f"twins_in_impact_radius ({in_radius}) > total portfolio ({total_twins})")
    if red_twins > total_twins and total_twins:
        issues.append(f"red_twin_count ({red_twins}) > total portfolio ({total_twins})")
    if exp_claims > total_twins and total_twins:
        issues.append(f"expected_claim_count ({exp_claims}) > total portfolio ({total_twins})")
    if fraud_twins > total_twins and total_twins:
        issues.append(f"fraud_risk_twins ({fraud_twins}) > total portfolio ({total_twins})")

    # Monotonicity: reserve must cover expected loss.
    if exp_loss > 0 and 0 < total_reserve < exp_loss:
        issues.append(f"reserve ({total_reserve}Cr) < expected loss ({exp_loss}Cr)")

    # Coverage: red properties should attract adjuster capacity.
    adjusters = resource.get("adjusters_needed", 0) or 0
    if red_twins > 0 and adjusters == 0 and not resource.get("error"):
        issues.append("red twins present but zero adjusters allocated")

    n_checks = 7
    score = round(max(0.0, (n_checks - len(issues)) / n_checks), 3)
    return {
        "consistent": len(issues) == 0,
        "consistency_score": score,
        "issues": issues,
    }
