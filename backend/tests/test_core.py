"""Tests for metrics, confidence scoring, and schema integrity."""
from app.core.agent_base import attach, compute_confidence
from app.core.metrics import _Metrics
from app.models import schemas


def test_compute_confidence_bounds():
    assert compute_confidence(data_coverage=1.0, has_narrative=True,
                              within_expected_range=True) == 1.0
    low = compute_confidence(data_coverage=0.0, has_narrative=False,
                             within_expected_range=False)
    assert 0.0 <= low <= 0.2
    # penalty never pushes below zero
    assert compute_confidence(data_coverage=0.0, has_narrative=False,
                              within_expected_range=False, penalty=1.0) == 0.0


def test_attach_envelope():
    out = attach({"x": 1}, confidence=0.9, why="because",
                 inputs_used=["a"], evidence={"k": "v"})
    assert out["confidence"] == 0.9
    assert out["explainability"]["why"] == "because"
    assert out["explainability"]["inputs_used"] == ["a"]


def test_metrics_counter_and_histogram():
    m = _Metrics()
    m.inc("idtcc_agent_runs_total", agent="weather")
    m.inc("idtcc_agent_runs_total", agent="weather")
    m.observe("idtcc_agent_latency_seconds", 0.5, agent="weather")
    snap = m.snapshot()
    assert snap["agents"]["weather"]["runs"] == 2
    assert snap["agents"]["weather"]["avg_latency_ms"] == 500.0
    text = m.render()
    assert "idtcc_agent_runs_total{agent=\"weather\"} 2" in text
    assert "idtcc_agent_latency_seconds_bucket" in text


def test_metrics_success_rate():
    m = _Metrics()
    m.inc("idtcc_agent_runs_total", agent="risk")
    m.inc("idtcc_agent_runs_total", agent="risk")
    m.inc("idtcc_agent_errors_total", agent="risk")
    snap = m.snapshot()
    assert snap["agents"]["risk"]["success_rate"] == 0.5


def test_agent_output_allows_extra_fields():
    # The whole point of the schema-drift fix: extra fields survive validation.
    risk = schemas.RiskOutput(
        twins_in_impact_radius=10, total_portfolio_twins=100, exposure_pct=10.0,
        top10_highest_vulnerability=[], by_flood_zone={}, confidence=0.9,
        narrative="ok", some_future_field=123,
    )
    dumped = risk.model_dump()
    assert dumped["some_future_field"] == 123
    assert dumped["confidence"] == 0.9


def test_forecast_response_has_confidence_fields():
    fields = schemas.ForecastResponse.model_fields
    assert "overall_confidence" in fields
    assert "agent_confidences" in fields
    assert "consistency" in fields
