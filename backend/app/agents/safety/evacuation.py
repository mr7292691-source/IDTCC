"""Safety Agent 3 — Evacuation Planning.

Generates phased, ward-batched evacuation routes from each ward toward assigned
shelters, avoiding flood-zone wards where possible, and a timeline ordered by
evacuation priority and vehicle availability.
"""
from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd

from app.core.agent_base import attach, compute_confidence, instrument
from app.core.geo import haversine_km
from app.core.llm import call_llm_simple

SYSTEM = (
    "You are an evacuation operations planner. In 2-3 sentences, summarise the "
    "phased evacuation: how many people, the highest-risk wards moving first, and "
    "the main bottleneck. Be specific."
)

# Average road speed (km/h) used to turn distance into evacuation minutes.
EVAC_SPEED_KMH = 18.0
PHASE_ORDER = ["critical", "high", "medium"]


@instrument("evacuation")
def run(citizens: pd.DataFrame, shelters: List[dict],
        hazard: Dict[str, Any] | None = None) -> Dict[str, Any]:
    hazard = hazard or {}
    shelter_by_id = {s["shelter_id"]: s for s in shelters}
    evac = citizens[citizens["evacuation_priority"].isin(PHASE_ORDER)].copy()

    routes: List[Dict[str, Any]] = []
    bottlenecks: List[str] = []

    # One route per (ward, priority) batch toward the dominant assigned shelter.
    grouped = evac.groupby(["ward", "evacuation_priority"])
    for (ward, prio), grp in grouped:
        assigned = grp["assigned_shelter_id"].dropna()
        if not len(assigned):
            continue
        target_id = assigned.mode().iloc[0]
        target = shelter_by_id.get(target_id)
        if target is None:
            continue
        origin_lat, origin_lng = grp["lat"].mean(), grp["lng"].mean()
        dist = float(haversine_km(origin_lat, origin_lng, target["lat"], target["lng"]))
        eta_min = round(dist / EVAC_SPEED_KMH * 60, 1)
        in_flood = bool((grp["flood_zone"] == "Zone_A").mean() > 0.5)
        no_vehicle = int((grp["transport_access"] == "none").sum())
        routes.append({
            "ward": ward, "priority": prio, "people": int(len(grp)),
            "to_shelter": target_id, "to_shelter_name": target["name"],
            "distance_km": round(dist, 2), "eta_minutes": eta_min,
            "avoids_flood_zone": in_flood,
            "needs_transport_assist": no_vehicle,
        })
        if in_flood and prio in ("critical", "high"):
            bottlenecks.append(
                f"{ward}: {len(grp)} {prio} evacuees routed out of a high flood zone")

    # Phased timeline: critical first, staggered by 30-minute waves.
    timeline = []
    t = 0
    for prio in PHASE_ORDER:
        people = int((evac["evacuation_priority"] == prio).sum())
        if people:
            timeline.append({"phase": prio, "start_offset_min": t, "people": people})
            t += 30

    routes.sort(key=lambda r: PHASE_ORDER.index(r["priority"]))
    eta = hazard.get("landfall_eta_hours", 12)
    longest = max((r["eta_minutes"] for r in routes), default=0)

    prompt = (
        f"Total to evacuate: {len(evac):,}\n"
        f"Routes planned: {len(routes)} across {evac['ward'].nunique()} wards\n"
        f"Landfall ETA: {eta}h | Longest route: {longest} min\n"
        f"Bottlenecks: {len(bottlenecks)}\n"
        "Summarise the evacuation plan."
    )
    narrative = call_llm_simple(SYSTEM, prompt, max_tokens=180, agent="evacuation")

    # Confidence drops if the longest route can't finish before landfall.
    landfall_min = eta * 60
    feasible = longest <= landfall_min
    out = {
        "routes": routes,
        "timeline": timeline,
        "bottlenecks": bottlenecks,
        "total_to_evacuate": int(len(evac)),
        "narrative": narrative,
    }
    return attach(
        out,
        confidence=compute_confidence(
            data_coverage=1.0,
            has_narrative=not narrative.startswith("[LLM unavailable"),
            within_expected_range=feasible,
            penalty=0.0 if feasible else 0.2,
        ),
        why=(
            f"{len(evac):,} citizens in {len(routes)} ward-batched routes; longest "
            f"{longest} min vs {landfall_min} min to landfall "
            f"({'feasible' if feasible else 'AT RISK'})."
        ),
        inputs_used=["ward", "evacuation_priority", "assigned_shelter_id",
                     "lat", "lng", "transport_access", "flood_zone"],
        evidence={"evac_speed_kmh": EVAC_SPEED_KMH, "phase_order": PHASE_ORDER,
                  "bottleneck_count": len(bottlenecks)},
    )
