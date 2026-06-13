"""Tests for the hallucination guardrails (no GPU/LLM required)."""
from app.core.guardrails import (
    check_consistency,
    coerce_float,
    extract_json,
    verify_numeric_bounds,
)


def test_extract_json_bare():
    assert extract_json('noise {"a": 1, "b": 2} trailing') == {"a": 1, "b": 2}


def test_extract_json_fenced():
    raw = 'Here:\n```json\n{"score": 8.5}\n```\nthanks'
    assert extract_json(raw) == {"score": 8.5}


def test_extract_json_trailing_comma_recovered():
    assert extract_json('{"a": 1, "b": [1, 2,],}') == {"a": 1, "b": [1, 2]}


def test_extract_json_nested():
    assert extract_json('{"x": {"y": {"z": 3}}}') == {"x": {"y": {"z": 3}}}


def test_extract_json_none_when_absent():
    assert extract_json("no json here") is None
    assert extract_json("") is None


def test_coerce_float_clamps_and_defaults():
    assert coerce_float("abc", 5.0) == 5.0
    assert coerce_float("99", 0.0, 0.0, 10.0) == 10.0
    assert coerce_float(float("nan"), 1.0) == 1.0


def test_verify_numeric_bounds_records_violation():
    violations = []
    out = verify_numeric_bounds(150.0, 0.0, 100.0, "exposure_pct", violations)
    assert out == 100.0
    assert len(violations) == 1


def test_consistency_flags_contradictions():
    state = {
        "risk_output": {"total_portfolio_twins": 1000, "twins_in_impact_radius": 1200},
        "claims_output": {"red_twin_count": 50, "expected_claim_count": 80,
                          "expected_total_loss_crore": 100},
        "reserve_output": {"total_recommended_reserve_crore": 80},
        "resource_output": {"adjusters_needed": 0},
        "fraud_output": {"total_fraud_risk_twins": 10},
    }
    report = check_consistency(state)
    assert report["consistent"] is False
    assert report["consistency_score"] < 1.0
    assert any("impact_radius" in i for i in report["issues"])
    assert any("reserve" in i for i in report["issues"])


def test_consistency_clean_state():
    state = {
        "risk_output": {"total_portfolio_twins": 1000, "twins_in_impact_radius": 400},
        "claims_output": {"red_twin_count": 50, "expected_claim_count": 80,
                          "expected_total_loss_crore": 100},
        "reserve_output": {"total_recommended_reserve_crore": 143},
        "resource_output": {"adjusters_needed": 5},
        "fraud_output": {"total_fraud_risk_twins": 10},
    }
    report = check_consistency(state)
    assert report["consistent"] is True
    assert report["consistency_score"] == 1.0
