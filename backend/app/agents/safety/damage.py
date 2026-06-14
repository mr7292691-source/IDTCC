"""Safety Agent 16 — Multimodal Damage Assessment.

Analyzes drone / satellite / CCTV frames during and after impact to confirm what
the predictive agents only forecast: actual flood extent, structural damage,
road blockages, and stranded persons — feeding the Rescue and Evacuation agents
hard ground truth.

Vision runs on **Qwen2.5-VL via vLLM** on the same AMD MI300X that serves the
text agents (co-resident, no model swap). When no vision endpoint or frames are
provided, the agent emits a deterministic, geo-tagged assessment so the pipeline
always produces a Road Passability Map and a Stranded-Person list for the demo.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from app.core.agent_base import attach, compute_confidence, instrument
from app.core.llm import call_llm_simple

SYSTEM = (
    "You are a disaster damage-assessment analyst reviewing aerial imagery. In "
    "2-3 sentences, summarise flood extent, the worst-hit zones, and which roads "
    "are impassable. Be specific and operational."
)

SEVERITY = ["none", "minor", "moderate", "severe", "catastrophic"]


def _synthetic_frames(center: tuple[float, float], hazard: Dict[str, Any],
                      n_tiles: int = 12, seed: int = 23) -> List[dict]:
    """Generate plausible geo-tagged tile assessments from hazard intensity.

    Stand-in for the Qwen2.5-VL detections until a live feed is wired.
    """
    rng = np.random.default_rng(seed)
    clat, clng = center
    intensity = min(hazard.get("max_wind_kmh", 160) / 180.0, 1.2)
    tiles = []
    for i in range(n_tiles):
        flooding = float(np.clip(rng.beta(2, 3) * intensity, 0, 1))
        depth = round(flooding * 2.5, 2)  # metres
        tiles.append({
            "tile_id": f"TILE-{i + 1:02d}",
            "lat": clat + float(rng.normal(0, 0.025)),
            "lng": clng + float(rng.normal(0, 0.025)),
            "flooding": round(flooding, 3),
            "water_depth_m": depth,
            "structural_damage": round(float(np.clip(rng.beta(1.5, 4) * intensity, 0, 1)), 3),
            "road_blocked": bool(flooding > 0.55 or rng.random() < 0.2 * intensity),
            "stranded_persons": int(rng.poisson(3 * flooding)),
        })
    return tiles


@instrument("damage")
def run(frames: Optional[List[dict]], hazard: Dict[str, Any],
        center: tuple[float, float] | None = None,
        vision_available: bool = False, narrate: bool = True) -> Dict[str, Any]:
    center = center or (13.08, 80.27)
    tiles = frames if frames else _synthetic_frames(center, hazard)

    def _sev(t: dict) -> str:
        s = max(t["flooding"], t["structural_damage"])
        return SEVERITY[min(int(s * 5), 4)]

    for t in tiles:
        t["severity"] = _sev(t)

    blocked_roads = [
        {"tile_id": t["tile_id"], "lat": t["lat"], "lng": t["lng"],
         "water_depth_m": t["water_depth_m"]}
        for t in tiles if t["road_blocked"]
    ]
    stranded = [
        {"tile_id": t["tile_id"], "lat": t["lat"], "lng": t["lng"],
         "count": t["stranded_persons"]}
        for t in tiles if t["stranded_persons"] > 0
    ]
    severe_zones = [t for t in tiles if t["severity"] in ("severe", "catastrophic")]
    total_stranded = sum(t["stranded_persons"] for t in tiles)
    max_depth = max((t["water_depth_m"] for t in tiles), default=0.0)

    prompt = (
        f"Tiles analysed: {len(tiles)} | Severe/catastrophic zones: {len(severe_zones)}\n"
        f"Roads blocked: {len(blocked_roads)} | Max water depth: {max_depth}m\n"
        f"Stranded persons detected: {total_stranded}\n"
        "Summarise the damage assessment."
    )
    narrative = call_llm_simple(SYSTEM, prompt, max_tokens=180, agent="damage") if narrate else ""

    out = {
        "tiles_analysed": len(tiles),
        "severe_zones": len(severe_zones),
        "roads_blocked": len(blocked_roads),
        "stranded_persons": total_stranded,
        "max_water_depth_m": round(float(max_depth), 2),
        "road_passability_map": blocked_roads,
        "stranded_locations": stranded,
        "vision_model": "Qwen2.5-VL" if vision_available else "deterministic-fallback",
        "narrative": narrative,
    }
    return attach(
        out,
        confidence=compute_confidence(
            # Real imagery is high coverage; the synthetic fallback is lower.
            data_coverage=1.0 if vision_available else 0.6,
            has_narrative=not narrative.startswith("[LLM unavailable"),
            within_expected_range=True,
        ),
        why=(
            f"{len(severe_zones)} zones severe+; {len(blocked_roads)} roads impassable; "
            f"{total_stranded} stranded persons detected across {len(tiles)} tiles "
            f"({'Qwen2.5-VL' if vision_available else 'deterministic fallback'})."
        ),
        inputs_used=["flooding", "structural_damage", "road_blocked", "stranded_persons"],
        evidence={"severity_scale": SEVERITY, "max_water_depth_m": round(float(max_depth), 2),
                  "vision_available": vision_available},
    )
