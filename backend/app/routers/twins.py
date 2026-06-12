"""Twins router — generate and query digital twin portfolio."""
from __future__ import annotations

import asyncio
from typing import List, Optional

from fastapi import APIRouter, Query

from app.models.schemas import TwinsResponse, PropertyTwin, SafeSpace
from app.core.simulation import generate_twins, run_cyclone_simulation, build_safe_spaces, assign_safe_spaces
from app.core.locations import get_location

router = APIRouter(prefix="/twins", tags=["twins"])


@router.get("", response_model=TwinsResponse)
async def get_twins(
    location: str = Query("CHN"),
    n: int = Query(1000, ge=10, le=50_000, description="Number of twins to return"),
    max_wind: float = Query(180.0),
    radius_km: float = Query(120.0),
    risk_filter: Optional[str] = Query(None, description="Filter by risk_color: red,orange,yellow,green"),
):
    loc = get_location(location)
    cyclone = {
        "name": "NIVAR", "max_wind_kmh": max_wind,
        "radius_km": radius_km,
        "track": loc["cyclone_track"],
    }

    def _compute():
        df = generate_twins(location, n=min(n * 2, 50_000))
        df = run_cyclone_simulation(df, cyclone)
        spaces = build_safe_spaces(location)
        df = assign_safe_spaces(df, spaces)
        if risk_filter:
            colors = [c.strip() for c in risk_filter.split(",")]
            df = df[df["risk_color"].isin(colors)]
        df = df.head(n)
        return df, spaces

    df, safe_spaces = await asyncio.to_thread(_compute)

    twins = [
        PropertyTwin(
            twin_id=r["twin_id"], lat=r["lat"], lng=r["lng"],
            address=r["address"], area=r["area"],
            construction_type=r["construction_type"],
            flood_zone=r["flood_zone"],
            vulnerability_index=r["vulnerability_index"],
            claim_probability=r["claim_probability"],
            expected_loss_inr=r["expected_loss_inr"],
            risk_color=r["risk_color"],
            sum_insured_inr=r["sum_insured_inr"],
            year_built=int(r["year_built"]),
        )
        for r in df.to_dict("records")
    ]
    spaces = [
        SafeSpace(
            id=s["id"], name=s["name"], lat=s["lat"], lng=s["lng"],
            capacity=s["capacity"], resources=s["resources"],
        )
        for s in safe_spaces
    ]
    return TwinsResponse(total=len(twins), twins=twins, safe_spaces=spaces)
