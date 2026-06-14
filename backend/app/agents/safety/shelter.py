"""Safety Agent 2 — Shelter Allocation.

Assigns citizens to shelters using a capacity-constrained, vulnerability-first
greedy match: the most vulnerable are placed first, each to the nearest shelter
that still has capacity and meets their accessibility / medical needs.
"""
from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd

from app.core.agent_base import attach, compute_confidence, instrument
from app.core.geo import haversine_km
from app.core.llm import call_llm_simple

SYSTEM = (
    "You are a disaster shelter logistics coordinator. In 2-3 sentences, summarise "
    "the shelter allocation: how many citizens placed, occupancy pressure, and any "
    "unmet demand. Be specific with numbers."
)

# Only evacuate citizens at/above this band — others shelter in place.
EVAC_BANDS = {"critical", "high", "medium"}


def allocate(citizens: pd.DataFrame, shelters: List[dict]) -> Dict[str, Any]:
    """Greedy vulnerability-first nearest-shelter assignment with capacity caps."""
    if not shelters:
        return {"assignments": {}, "occupancy": {}, "assigned": 0,
                "unmet": int(len(citizens))}

    # Live mutable capacity ledger.
    cap = {s["shelter_id"]: int(s["capacity"]) for s in shelters}
    occ = {s["shelter_id"]: 0 for s in shelters}
    s_lat = np.array([s["lat"] for s in shelters], dtype=float)
    s_lng = np.array([s["lng"] for s in shelters], dtype=float)
    s_wheel = np.array([bool(s.get("wheelchair_accessible", True)) for s in shelters])
    s_med = np.array([bool(s.get("medical_capable", False)) for s in shelters])
    s_ids = [s["shelter_id"] for s in shelters]

    to_evac = citizens[citizens["evacuation_priority"].isin(EVAC_BANDS)]
    # Most vulnerable get first pick of capacity.
    to_evac = to_evac.sort_values("vulnerability_score", ascending=False)

    assignments: Dict[str, str] = {}
    assigned = 0
    for row in to_evac.itertuples(index=False):
        needs_wheel = (not row.can_walk_unassisted) or row.disability_status
        needs_med = row.medical_dependency is not None
        dists = haversine_km(row.lat, row.lng, s_lat, s_lng)
        order = np.argsort(dists)
        placed = False
        for j in order:
            sid = s_ids[j]
            if cap[sid] - occ[sid] <= 0:
                continue
            if needs_wheel and not s_wheel[j]:
                continue
            if needs_med and not s_med[j]:
                continue
            occ[sid] += 1
            assignments[row.citizen_id] = sid
            assigned += 1
            placed = True
            break
        if not placed:
            # Fallback: nearest shelter with ANY space, ignoring soft constraints.
            for j in order:
                sid = s_ids[j]
                if cap[sid] - occ[sid] > 0:
                    occ[sid] += 1
                    assignments[row.citizen_id] = sid
                    assigned += 1
                    placed = True
                    break

    unmet = int(len(to_evac) - assigned)
    return {"assignments": assignments, "occupancy": occ,
            "assigned": assigned, "unmet": unmet, "to_evac": int(len(to_evac))}


@instrument("shelter")
def run(citizens: pd.DataFrame, shelters: List[dict]) -> Dict[str, Any]:
    result = allocate(citizens, shelters)
    occ = result["occupancy"]
    cap_by_id = {s["shelter_id"]: int(s["capacity"]) for s in shelters}
    name_by_id = {s["shelter_id"]: s["name"] for s in shelters}

    forecast = [
        {
            "shelter_id": sid,
            "name": name_by_id.get(sid, sid),
            "capacity": cap_by_id.get(sid, 0),
            "assigned": occ.get(sid, 0),
            "utilisation_pct": round(100 * occ.get(sid, 0) / max(cap_by_id.get(sid, 1), 1), 1),
        }
        for sid in cap_by_id
    ]
    forecast.sort(key=lambda x: x["utilisation_pct"], reverse=True)
    activated = sum(1 for f in forecast if f["assigned"] > 0)

    prompt = (
        f"Citizens needing evacuation: {result['to_evac']:,}\n"
        f"Assigned: {result['assigned']:,} | Unmet demand: {result['unmet']:,}\n"
        f"Shelters activated: {activated} of {len(shelters)}\n"
        f"Highest utilisation: {forecast[0]['utilisation_pct'] if forecast else 0}%\n"
        "Summarise the shelter allocation outcome."
    )
    narrative = call_llm_simple(SYSTEM, prompt, max_tokens=180, agent="shelter")

    # Penalise confidence proportionally to unmet demand.
    unmet_ratio = result["unmet"] / max(result["to_evac"], 1)
    out = {
        "shelters_activated": activated,
        "citizens_assigned": result["assigned"],
        "unmet_demand": result["unmet"],
        "occupancy_forecast": forecast,
        "assignments": result["assignments"],   # citizen_id -> shelter_id
        "narrative": narrative,
    }
    return attach(
        out,
        confidence=compute_confidence(
            data_coverage=1.0,
            has_narrative=not narrative.startswith("[LLM unavailable"),
            within_expected_range=True,
            penalty=round(0.4 * unmet_ratio, 3),
        ),
        why=(
            f"{result['assigned']:,} of {result['to_evac']:,} evacuees placed across "
            f"{activated} shelters (vulnerability-first, capacity & accessibility "
            f"constrained); {result['unmet']:,} unmet."
        ),
        inputs_used=["vulnerability_score", "evacuation_priority", "lat", "lng",
                     "disability_status", "medical_dependency", "can_walk_unassisted"],
        evidence={"unmet_ratio": round(unmet_ratio, 3),
                  "policy": "vulnerability-first greedy nearest-with-capacity"},
    )
