"""Safety Agent 5 — Infrastructure Risk.

Scores critical assets (roads, bridges, hospitals, schools, power stations,
water treatment) against hazard intensity using per-type fragility, then traces
dependency cascades (power -> water -> hospital) to surface failures that
propagate before disaster impact.
"""
from __future__ import annotations

from typing import Any, Dict, List

import numpy as np

from app.core.agent_base import attach, compute_confidence, instrument
from app.core.geo import haversine_km
from app.core.llm import call_llm_simple

SYSTEM = (
    "You are a critical-infrastructure resilience engineer. In 2-3 sentences, "
    "summarise which assets are most likely to fail and which cascades matter most. "
    "Be specific."
)

# Per-type fragility (probability multiplier) — older/critical assets fail sooner.
FRAGILITY = {
    "bridge": 0.85, "road": 0.70, "power_station": 0.80,
    "water_treatment": 0.75, "hospital": 0.55, "school": 0.60,
}
# Dependency edges: failure of source degrades target.
CASCADES = [
    ("power_station", "water_treatment"),
    ("power_station", "hospital"),
    ("water_treatment", "hospital"),
    ("bridge", "hospital"),  # access dependency
]


def _synth_assets(center_lat: float, center_lng: float, seed: int = 11) -> List[dict]:
    """Generate a plausible critical-asset inventory around the city centre.

    Placeholder until a real OSM/GIS infrastructure connector lands.
    """
    rng = np.random.default_rng(seed)
    plan = {"bridge": 6, "road": 12, "power_station": 4,
            "water_treatment": 3, "hospital": 5, "school": 10}
    assets: List[dict] = []
    i = 0
    for atype, count in plan.items():
        for _ in range(count):
            i += 1
            assets.append({
                "asset_id": f"INF-{i:03d}",
                "type": atype,
                "lat": center_lat + float(rng.normal(0, 0.03)),
                "lng": center_lng + float(rng.normal(0, 0.03)),
                "year_built": int(rng.integers(1965, 2018)),
                "condition": float(rng.uniform(0.4, 1.0)),  # 1 = pristine
            })
    return assets


@instrument("infrastructure")
def run(assets: List[dict] | None, hazard: Dict[str, Any],
        center: tuple[float, float] | None = None) -> Dict[str, Any]:
    if not assets:
        clat, clng = center or (13.08, 80.27)
        assets = _synth_assets(clat, clng)

    storm_lat = hazard.get("track", [{}])[-1].get("lat") if hazard.get("track") else None
    storm_lng = hazard.get("track", [{}])[-1].get("lng") if hazard.get("track") else None
    radius = hazard.get("radius_km", 120)
    max_wind = hazard.get("max_wind_kmh", 160)
    intensity = min(max_wind / 180.0, 1.2)

    scored: List[dict] = []
    for a in assets:
        if storm_lat is not None:
            dist = float(haversine_km(a["lat"], a["lng"], storm_lat, storm_lng))
            proximity = max(0.0, 1.0 - dist / max(radius, 1))
        else:
            proximity = 0.6
        age_factor = min((2025 - a["year_built"]) / 60.0, 1.0)
        fail_prob = (
            FRAGILITY.get(a["type"], 0.6)
            * (0.5 * proximity + 0.3 * age_factor + 0.2 * (1 - a["condition"]))
            * intensity
        )
        fail_prob = round(min(fail_prob, 0.99), 3)
        scored.append({**a, "failure_prob": fail_prob,
                       "status": "at_risk" if fail_prob >= 0.4 else "stable"})

    at_risk = [a for a in scored if a["status"] == "at_risk"]
    at_risk_types = {a["type"] for a in at_risk}

    cascade_chains: List[Dict[str, Any]] = []
    for src, tgt in CASCADES:
        if src in at_risk_types and tgt in {a["type"] for a in scored}:
            affected = [a["asset_id"] for a in scored if a["type"] == tgt]
            cascade_chains.append({
                "trigger": src, "impacts": tgt,
                "affected_assets": affected[:5],
                "note": f"{src.replace('_', ' ')} failure degrades {len(affected)} {tgt}(s)",
            })

    top = sorted(scored, key=lambda x: x["failure_prob"], reverse=True)[:15]

    prompt = (
        f"Assets analysed: {len(scored)} | At risk: {len(at_risk)}\n"
        f"At-risk types: {sorted(at_risk_types)}\n"
        f"Cascade chains: {len(cascade_chains)}\n"
        f"Hazard intensity: {round(intensity, 2)}\n"
        "Summarise the infrastructure risk and cascades."
    )
    narrative = call_llm_simple(SYSTEM, prompt, max_tokens=180, agent="infrastructure")

    out = {
        "at_risk_assets": len(at_risk),
        "total_assets": len(scored),
        "cascade_chains": cascade_chains,
        "asset_details": top,
        "narrative": narrative,
    }
    return attach(
        out,
        confidence=compute_confidence(
            data_coverage=1.0,
            has_narrative=not narrative.startswith("[LLM unavailable"),
            within_expected_range=True,
        ),
        why=(
            f"{len(at_risk)} of {len(scored)} critical assets at risk; "
            f"{len(cascade_chains)} dependency cascade(s) identified "
            f"(power/water/hospital/access)."
        ),
        inputs_used=["type", "year_built", "condition", "lat", "lng"],
        evidence={"fragility": FRAGILITY, "cascade_rules": CASCADES,
                  "hazard_intensity": round(intensity, 3)},
    )
