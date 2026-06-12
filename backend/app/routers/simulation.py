"""Simulation router — runs the full LangGraph pipeline."""
from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models.schemas import SimulationRequest, ForecastResponse
from app.core.locations import LOCATION_CATALOGUE, get_location
from app.graph.orchestrator import get_graph

router = APIRouter(prefix="/simulation", tags=["simulation"])


def _build_cyclone(req: SimulationRequest) -> dict:
    loc = get_location(req.location_code)
    track = [
        {**wp, "lat": wp["lat"] + req.track_shift_km / 111.0}
        for wp in loc["cyclone_track"]
    ]
    return {
        "name":              req.cyclone_name,
        "category":         "Very Severe Cyclonic Storm",
        "max_wind_kmh":     req.max_wind_kmh,
        "landfall_eta_hours": req.landfall_eta_hours,
        "landfall_eta_h":   req.landfall_eta_hours,
        "radius_km":        req.radius_km,
        "track":            track,
    }


@router.post("/run", response_model=ForecastResponse)
async def run_simulation(req: SimulationRequest):
    """Run the full 7-agent simulation pipeline and return the forecast."""
    try:
        loc = get_location(req.location_code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    cyclone = _build_cyclone(req)
    initial_state = {
        "location_code":  req.location_code,
        "location_name":  loc["name"],
        "twin_count":     req.twin_count,
        "cyclone_params": cyclone,
        "twins_records":  [],
        "weather_output": {},
        "risk_output":    {},
        "claims_output":  {},
        "fraud_output":   {},
        "reserve_output": {},
        "resource_output":{},
        "alerts_output":  {},
        "judge_scores":   {},
        "forecast":       {},
        "executive_summary": "",
        "errors":         [],
    }

    graph = get_graph()
    result = await asyncio.to_thread(graph.invoke, initial_state)

    forecast = result.get("forecast", {})
    forecast["executive_summary"] = result.get("executive_summary", "")
    forecast["risk"]          = result.get("risk_output")
    forecast["claims"]        = result.get("claims_output")
    forecast["fraud"]         = result.get("fraud_output")
    forecast["reserve"]       = result.get("reserve_output")
    forecast["resource"]      = result.get("resource_output")
    forecast["alerts"]        = result.get("alerts_output")
    forecast["judge_scores"]  = result.get("judge_scores")

    return ForecastResponse(**forecast)


@router.post("/stream")
async def stream_simulation(req: SimulationRequest):
    """Stream agent events via Server-Sent Events."""
    try:
        loc = get_location(req.location_code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    cyclone = _build_cyclone(req)
    initial_state = {
        "location_code":  req.location_code,
        "location_name":  loc["name"],
        "twin_count":     req.twin_count,
        "cyclone_params": cyclone,
        "twins_records":  [],
        "weather_output": {}, "risk_output":    {},
        "claims_output":  {}, "fraud_output":   {},
        "reserve_output": {}, "resource_output":{},
        "alerts_output":  {}, "judge_scores":   {},
        "forecast":       {}, "executive_summary": "",
        "errors":         [],
    }

    async def event_generator() -> AsyncGenerator[str, None]:
        graph = get_graph()

        def _stream():
            events = []
            for event in graph.stream(initial_state, stream_mode="updates"):
                events.append(event)
            return events

        try:
            events = await asyncio.to_thread(_stream)
            for event in events:
                for node_name, node_output in event.items():
                    payload = json.dumps({
                        "agent": node_name,
                        "status": "done",
                        "output": {k: v for k, v in node_output.items()
                                   if k not in ("twins_records",)}
                    }, default=str)
                    yield f"data: {payload}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'agent': 'system', 'status': 'error', 'message': str(exc)})}\n\n"
        finally:
            yield "data: {\"agent\": \"system\", \"status\": \"complete\"}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/locations")
async def list_locations():
    return [
        {
            "code":  code,
            "name":  loc["name"],
            "event": loc["event"],
            "center": loc["center"],
            "damage_cr": loc.get("damage_cr", 0),
        }
        for code, loc in LOCATION_CATALOGUE.items()
    ]
