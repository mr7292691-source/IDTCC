"""Alerts router — personalized multilingual alert preview & dispatch.

Lets the disaster-management UI preview an alert in any supported language and
dispatch a (simulated by default) omni-channel campaign to a freshly scored
citizen population — the "Ravi Kumar gets a Tamil SMS on a basic phone" moment.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agents.safety import vulnerable as vln
from app.core import simulation as sim_core
from app.core.alerting.channels import available_channels
from app.core.alerting.dispatcher import dispatch as dispatch_alerts
from app.core.alerting.templates import SUPPORTED_LANGUAGES, render
from app.core.locations import get_location
from app.core.twins.citizen import synthesize_citizens

router = APIRouter(prefix="/alerts", tags=["alerts"])


class PreviewRequest(BaseModel):
    alert_type: str = Field("cyclone_warning",
                            description="cyclone_warning | flood_warning | rescue_confirmation")
    language: str = Field("ta", description="en|ta|hi|te|kn")
    name: str = "Ravi Kumar"
    hazard: str = "NIVAR"
    eta_hours: int = 12
    ward: str = "Adyar"
    shelter: str = "Government School, GST Road"
    distance_km: float = 1.2
    leave_by: str = "4 PM"
    helpline: str = "108"


class DispatchRequest(BaseModel):
    location_code: str = "CHN"
    twin_count: int = Field(5_000, ge=100, le=50_000)
    alert_type: str = "cyclone_warning"
    max_wind_kmh: float = 180.0
    radius_km: float = 120.0
    landfall_eta_hours: int = 12
    max_alerts: int = Field(200, ge=1, le=2_000)
    dry_run: bool = True


@router.get("/meta")
async def alert_meta():
    """Supported languages + channels for the alert composer UI."""
    return {"languages": SUPPORTED_LANGUAGES, "channels": available_channels()}


@router.post("/preview")
async def preview_alert(req: PreviewRequest):
    """Render a single personalized alert without sending it."""
    body = render(
        req.alert_type, req.language,
        name=req.name, hazard=req.hazard, eta_hours=req.eta_hours,
        ward=req.ward, shelter=req.shelter, distance_km=req.distance_km,
        leave_by=req.leave_by, helpline=req.helpline,
    )
    return {"alert_type": req.alert_type, "language": req.language,
            "message": body, "chars": len(body)}


@router.post("/dispatch")
async def dispatch_campaign(req: DispatchRequest):
    """Score a citizen population and dispatch a (simulated) alert campaign."""
    try:
        loc = get_location(req.location_code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    hazard = {"name": "NIVAR", "max_wind_kmh": req.max_wind_kmh,
              "radius_km": req.radius_km, "landfall_eta_hours": req.landfall_eta_hours,
              "track": loc["cyclone_track"]}

    def _work():
        pdf = sim_core.generate_twins(req.location_code, n=req.twin_count)
        pdf = sim_core.run_cyclone_simulation(pdf, hazard)
        spaces = sim_core.build_safe_spaces(req.location_code)
        pdf = sim_core.assign_safe_spaces(pdf, spaces)
        citizens = synthesize_citizens(pdf, location_name=loc["name"],
                                       state_code=loc.get("state_code", ""))
        citizens = vln.assign(citizens)
        shelters = [{**s, "shelter_id": s["id"]} for s in spaces]
        return dispatch_alerts(
            citizens, alert_type=req.alert_type, hazard=hazard,
            shelters=shelters, max_alerts=req.max_alerts, dry_run=req.dry_run,
        )

    return await asyncio.to_thread(_work)
