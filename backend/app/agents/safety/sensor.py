"""Safety Agent 6 — Sensor Intelligence.

Consumes a real-time sensor snapshot (river level, rainfall, wind, water level)
and turns it into an overall risk score, threshold breaches, and a short-horizon
flood forecast. Falls back to deriving a snapshot from the hazard parameters
when no live feed is attached, so the pipeline always runs.
"""
from __future__ import annotations

from typing import Any, Dict, List

from app.core.agent_base import attach, compute_confidence, instrument
from app.core.llm import call_llm_simple

SYSTEM = (
    "You are a flood-monitoring duty officer. In 2-3 sentences, give a plain-language "
    "situational brief from the sensor readings: current risk and what to watch."
)

# (warning, danger) thresholds per sensor type.
THRESHOLDS = {
    "river_level_m":     (4.5, 6.0),
    "rainfall_mm_hr":    (30.0, 60.0),
    "wind_kmh":          (90.0, 130.0),
    "water_level_m":     (1.0, 2.0),
    "aqi":               (200.0, 350.0),
}


def _derive_snapshot(hazard: Dict[str, Any]) -> Dict[str, float]:
    """Synthetic-but-plausible readings from hazard params for demo continuity."""
    wind = float(hazard.get("max_wind_kmh", 120))
    intensity = min(wind / 180.0, 1.2)
    return {
        "river_level_m":  round(3.5 + 3.0 * intensity, 2),
        "rainfall_mm_hr": round(20 + 50 * intensity, 1),
        "wind_kmh":       round(wind, 1),
        "water_level_m":  round(0.5 + 1.8 * intensity, 2),
        "aqi":            round(120 + 80 * intensity, 0),
    }


@instrument("sensor")
def run(snapshot: Dict[str, Any] | None,
        hazard: Dict[str, Any] | None = None) -> Dict[str, Any]:
    hazard = hazard or {}
    live = bool(snapshot)
    readings = dict(snapshot) if snapshot else _derive_snapshot(hazard)

    breaches: List[Dict[str, Any]] = []
    severities: List[float] = []
    for key, (warn, danger) in THRESHOLDS.items():
        val = readings.get(key)
        if val is None:
            continue
        val = float(val)
        if val >= danger:
            level, sev = "danger", min(1.0, val / danger)
        elif val >= warn:
            level, sev = "warning", 0.5 * val / warn
        else:
            level, sev = "normal", 0.2 * val / warn
        severities.append(sev)
        if level != "normal":
            breaches.append({"sensor": key, "value": val, "level": level,
                             "warn": warn, "danger": danger})

    overall = round(min(1.0, sum(severities) / max(len(severities), 1)), 3)

    # Simple flood extrapolation from river + rainfall.
    river = float(readings.get("river_level_m", 0))
    rain = float(readings.get("rainfall_mm_hr", 0))
    rise_rate = round(rain / 100.0, 3)  # m/hr, crude
    danger_level = THRESHOLDS["river_level_m"][1]
    breach_eta_h = (
        round((danger_level - river) / rise_rate, 1)
        if rise_rate > 0 and river < danger_level else None
    )
    flood_forecast = {
        "river_level_m": river, "rise_rate_m_per_hr": rise_rate,
        "danger_level_m": danger_level, "breach_eta_hours": breach_eta_h,
    }

    prompt = (
        f"Readings: {readings}\n"
        f"Breaches: {len(breaches)} | Overall risk: {overall}\n"
        f"River breach ETA: {breach_eta_h}h\n"
        "Give the situational brief."
    )
    narrative = call_llm_simple(SYSTEM, prompt, max_tokens=160, agent="sensor")

    out = {
        "overall_risk_score": overall,
        "readings": readings,
        "live_feed": live,
        "breaches": breaches,
        "flood_forecast": flood_forecast,
        "narrative": narrative,
    }
    return attach(
        out,
        confidence=compute_confidence(
            data_coverage=1.0 if live else 0.7,   # derived snapshot is lower-coverage
            has_narrative=not narrative.startswith("[LLM unavailable"),
            within_expected_range=True,
        ),
        why=(
            f"{len(breaches)} sensor threshold breach(es); overall real-time risk "
            f"{overall}. "
            + (f"River danger level in ~{breach_eta_h}h." if breach_eta_h else
               "No imminent river breach projected.")
        ),
        inputs_used=list(readings.keys()),
        evidence={"thresholds": THRESHOLDS, "live_feed": live},
    )
