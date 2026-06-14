"""Safety router — LifeShield life-safety pipeline (Lens B).

Mirrors the insurance simulation router: a synchronous `/run` and an SSE
`/stream` driven by `graph.stream(stream_mode="updates")`, plus sub-resource
reads scoped for the disaster-management UI.
"""
from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.agents.safety import damage as dmg
from app.agents.safety import vulnerable as vln
from app.core import simulation as sim_core
from app.core.geo import nearest_facility
from app.core.locations import get_location
from app.core.twins.citizen import synthesize_citizens
from app.core.twins.shelter import build_shelter_twins
from app.graph.safety_orchestrator import get_safety_graph
from app.models.twin_schemas import ResponsePlan, SafetyRunRequest

router = APIRouter(prefix="/safety", tags=["safety"])


def _build_hazard(req: SafetyRunRequest, loc: dict) -> dict:
    return {
        "name": req.hazard_name,
        "hazard_type": req.hazard_type,
        "max_wind_kmh": req.max_wind_kmh,
        "radius_km": req.radius_km,
        "landfall_eta_hours": req.landfall_eta_hours,
        "track": loc["cyclone_track"],
    }


def _initial_state(req: SafetyRunRequest, loc: dict) -> dict:
    return {
        "location_code": req.location_code,
        "location_name": loc["name"],
        "state_code": loc.get("state_code", ""),
        "center": list(loc.get("center", (13.08, 80.27))),
        "twin_count": req.twin_count,
        "hazard_params": _build_hazard(req, loc),
        "sensor_snapshot": req.sensor_snapshot or {},
        "citizen_records": [], "shelter_records": [], "infra_records": [],
        "sensor_output": {}, "infrastructure_output": {}, "damage_output": {},
        "vulnerable_output": {}, "shelter_output": {},
        "evacuation_output": {}, "rescue_output": {},
        "judge_scores": {}, "response_plan": {}, "executive_summary": "",
        "dispatched_alerts": {}, "errors": [],
    }


@router.post("/run", response_model=ResponsePlan)
async def run_safety(req: SafetyRunRequest):
    """Run the full life-safety pipeline and return the response plan."""
    try:
        loc = get_location(req.location_code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    graph = get_safety_graph()
    result = await asyncio.to_thread(graph.invoke, _initial_state(req, loc))

    plan = result.get("response_plan", {})
    plan["executive_summary"] = result.get("executive_summary", "")
    plan["vulnerable"] = result.get("vulnerable_output")
    plan["shelter"] = result.get("shelter_output")
    plan["evacuation"] = result.get("evacuation_output")
    plan["rescue"] = result.get("rescue_output")
    plan["sensor"] = result.get("sensor_output")
    plan["infrastructure"] = result.get("infrastructure_output")
    plan["damage"] = result.get("damage_output")
    plan["dispatched_alerts"] = result.get("dispatched_alerts")
    plan["judge_scores"] = result.get("judge_scores")
    return ResponsePlan(**plan)


@router.post("/stream")
async def stream_safety(req: SafetyRunRequest):
    """Stream each safety agent's completion via Server-Sent Events."""
    try:
        loc = get_location(req.location_code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    initial_state = _initial_state(req, loc)

    async def event_generator() -> AsyncGenerator[str, None]:
        graph = get_safety_graph()
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()
        _SENTINEL = object()

        def _produce():
            try:
                for event in graph.stream(initial_state, stream_mode="updates"):
                    loop.call_soon_threadsafe(queue.put_nowait, ("event", event))
            except Exception as exc:  # noqa: BLE001
                loop.call_soon_threadsafe(queue.put_nowait, ("error", str(exc)))
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, ("done", _SENTINEL))

        producer = asyncio.create_task(asyncio.to_thread(_produce))
        yield f"data: {json.dumps({'agent': 'system', 'status': 'start'})}\n\n"

        try:
            while True:
                kind, data = await queue.get()
                if kind == "done":
                    break
                if kind == "error":
                    yield f"data: {json.dumps({'agent': 'system', 'status': 'error', 'message': data})}\n\n"
                    continue
                for node_name, node_output in data.items():
                    payload = json.dumps({
                        "agent": node_name,
                        "status": "done",
                        "output": {k: v for k, v in node_output.items()
                                   if k not in ("citizen_records", "shelter_records",
                                                "infra_records")},
                    }, default=str)
                    yield f"data: {payload}\n\n"
        finally:
            await producer
            yield "data: {\"agent\": \"system\", \"status\": \"complete\"}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/citizens")
async def safety_citizens(
    location: str = Query("CHN"),
    n: int = Query(4000, ge=100, le=20_000, description="Citizen sample size for the map"),
    max_wind: float = Query(180.0),
    radius_km: float = Query(120.0),
):
    """Scored citizen-twin sample + shelters + stranded persons for the City Twin map.

    Lightweight: synthesizes citizens, scores vulnerability, assigns each a nearest
    shelter, and runs the damage agent for stranded-person markers — without
    invoking the full LangGraph pipeline.
    """
    try:
        loc = get_location(location)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    hazard = {"name": "NIVAR", "max_wind_kmh": max_wind, "radius_km": radius_km,
              "landfall_eta_hours": 12, "track": loc["cyclone_track"]}

    def _work():
        n_props = max(200, n // 4)   # ~3.8 citizens per property
        pdf = sim_core.generate_twins(location, n=n_props)
        pdf = sim_core.run_cyclone_simulation(pdf, hazard)
        citizens = synthesize_citizens(pdf, location_name=loc["name"],
                                       state_code=loc.get("state_code", ""))
        citizens = vln.assign(citizens).head(n)
        shelters = build_shelter_twins(location)

        if shelters:
            idx, dist = nearest_facility(citizens["lat"].values, citizens["lng"].values, shelters)
            citizens = citizens.assign(
                nearest_shelter_id=[shelters[i]["shelter_id"] for i in idx],
                nearest_shelter_km=[round(float(d), 2) for d in dist],
            )

        cols = ["citizen_id", "lat", "lng", "ward", "age", "vulnerability_score",
                "evacuation_priority", "rescue_priority", "disability_status",
                "medical_dependency", "preferred_language", "nearest_shelter_id",
                "nearest_shelter_km"]
        cols = [c for c in cols if c in citizens.columns]
        sample = citizens[cols].where(citizens[cols].notnull(), None).to_dict("records")

        dmg_out = dmg.run(None, hazard, center=tuple(loc.get("center", (13.08, 80.27))),
                          narrate=False)  # map needs markers, not the LLM narrative
        return sample, shelters, dmg_out

    sample, shelters, dmg_out = await asyncio.to_thread(_work)
    return {
        "location": loc["name"],
        "center": list(loc.get("center", (13.08, 80.27))),
        "zoom": loc.get("zoom", 11),
        "total": len(sample),
        "citizens": sample,
        "shelters": shelters,
        "stranded": dmg_out.get("stranded_locations", []),
        "roads_blocked": dmg_out.get("road_passability_map", []),
    }
