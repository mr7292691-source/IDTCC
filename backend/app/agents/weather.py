"""Agent 1 — Weather Intelligence."""
from __future__ import annotations
from typing import Any, Dict
from app.core.llm import call_llm_simple
from app.core.agent_base import instrument, attach, compute_confidence


SYSTEM = (
    "You are a senior meteorologist specialising in Indian Ocean cyclones. "
    "Analyse the cyclone parameters and return a structured assessment. "
    "Be specific about wind speed, storm surge risk, and rainfall projections. "
    "Keep your response under 200 words."
)


@instrument("weather")
def run(cyclone: Dict[str, Any], location: str) -> Dict[str, Any]:
    name       = cyclone.get("name", "UNKNOWN")
    wind       = cyclone.get("max_wind_kmh", 180)
    eta        = cyclone.get("landfall_eta_hours", 48)
    radius     = cyclone.get("radius_km", 120)
    category   = cyclone.get("category", "Severe Cyclonic Storm")
    track      = cyclone.get("track", [])

    # Compute severity index (0-10)
    severity = round(
        (wind / 250.0) * 4.0
        + max(0.0, (120 - eta) / 120.0) * 3.0
        + min(radius / 150.0, 1.0) * 3.0,
        1
    )

    hazards = []
    if wind >= 160:
        hazards.append("Extreme wind damage")
    if any(wp.get("lat", 0) < 14 for wp in track):
        hazards.append("Coastal storm surge 2–4 m")
    hazards.append("Heavy rainfall (20–30 cm / 24h)")
    if severity > 7:
        hazards.append("Flash flooding in low-lying areas")

    prompt = (
        f"Cyclone: {name} | Category: {category}\n"
        f"Max wind: {wind} km/h | Landfall ETA: {eta}h | Radius: {radius} km\n"
        f"Location: {location}\n"
        f"Provide a tactical weather assessment for insurance response teams."
    )
    narrative = call_llm_simple(SYSTEM, prompt, max_tokens=300, agent="weather")

    out = {
        "storm_name":          name,
        "category":            category,
        "max_wind_kmh":        wind,
        "landfall_eta_hours":  eta,
        "impact_radius_km":    radius,
        "storm_severity_index": severity,
        "primary_hazards":     hazards,
        "rainfall_forecast_mm_24h": 250,
        "storm_surge_m":       2.5 if wind >= 150 else 1.2,
        "narrative":           narrative,
    }

    has_narrative = not narrative.startswith("[LLM unavailable")
    in_range = 0.0 <= severity <= 10.0 and len(track) > 0
    confidence = compute_confidence(
        data_coverage=1.0 if track else 0.7,
        has_narrative=has_narrative,
        within_expected_range=in_range,
    )
    return attach(
        out,
        confidence=confidence,
        why=(
            f"Severity {severity}/10 derived from max wind {wind} km/h, "
            f"landfall ETA {eta}h, and impact radius {radius} km."
        ),
        inputs_used=["max_wind_kmh", "landfall_eta_hours", "radius_km", "cyclone_track"],
        evidence={
            "severity_formula": "0.4*wind/250 + 0.3*(120-eta)/120 + 0.3*min(radius/150,1) scaled to 0-10",
            "track_waypoints": len(track),
            "coastal_surge_triggered": any(wp.get("lat", 0) < 14 for wp in track),
        },
    )
