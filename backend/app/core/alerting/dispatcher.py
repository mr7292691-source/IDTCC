"""Alert dispatcher — turn a scored citizen population into delivered alerts.

For each high-priority citizen it renders a personalized message in their
preferred language with their specific shelter + distance, then fans out across
their chosen channels (SMS always included as the offline-safe floor). Returns a
delivery summary plus a small sample for the UI / demo.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from app.core.alerting.channels import get_channel
from app.core.alerting.templates import render

# Only alert citizens at/above this evacuation band by default.
DEFAULT_BANDS = {"critical", "high"}


def _shelter_lookup(shelters: List[dict]) -> Dict[str, dict]:
    return {s.get("shelter_id", s.get("id", "")): s for s in (shelters or [])}


def dispatch(
    citizens: pd.DataFrame,
    *,
    alert_type: str = "cyclone_warning",
    hazard: Optional[Dict[str, Any]] = None,
    shelters: Optional[List[dict]] = None,
    bands: Optional[set] = None,
    max_alerts: int = 200,
    helpline: str = "108",
    dry_run: bool = True,
    role: str = "dm_authority",
) -> Dict[str, Any]:
    hazard = hazard or {}
    bands = bands or DEFAULT_BANDS
    shelters_by_id = _shelter_lookup(shelters or [])

    if "evacuation_priority" not in citizens.columns:
        return {"total_targeted": 0, "delivered": 0, "denied": 0,
                "by_channel": {}, "by_language": {}, "sample": []}

    targets = citizens[citizens["evacuation_priority"].isin(bands)]
    if "vulnerability_score" in targets.columns:
        targets = targets.sort_values("vulnerability_score", ascending=False)
    targets = targets.head(max_alerts)

    delivered = denied = 0
    by_channel: Dict[str, int] = {}
    by_language: Dict[str, int] = {}
    sample: List[Dict[str, Any]] = []

    eta_hours = hazard.get("landfall_eta_hours", hazard.get("landfall_eta_h", "?"))

    for row in targets.itertuples(index=False):
        lang = getattr(row, "preferred_language", "en")
        sid = getattr(row, "assigned_shelter_id", None)
        shelter = shelters_by_id.get(sid, {})
        body = render(
            alert_type, lang,
            name=str(getattr(row, "citizen_id", "Citizen")),
            hazard=hazard.get("name", "the storm"),
            eta_hours=eta_hours,
            ward=getattr(row, "ward", "your area"),
            district=getattr(row, "district", ""),
            shelter=shelter.get("name", "the nearest shelter"),
            distance_km=_distance_km(row, shelter),
            leave_by=hazard.get("leave_by", "the deadline"),
            helpline=helpline,
        )

        channels = list(getattr(row, "alert_channels", ["sms"]) or ["sms"])
        if "sms" not in channels:
            channels.append("sms")  # offline-safe floor

        token = getattr(row, "pii_token", "")
        first_receipt = None
        for ch_name in channels:
            ch = get_channel(ch_name)
            if ch is None:
                continue
            receipt = ch.send(token, body, role=role, dry_run=dry_run)
            status = receipt["status"]
            if status in ("sent", "simulated"):
                delivered += 1
                by_channel[ch_name] = by_channel.get(ch_name, 0) + 1
            elif status == "denied":
                denied += 1
            first_receipt = first_receipt or receipt

        by_language[lang] = by_language.get(lang, 0) + 1
        if len(sample) < 8:
            sample.append({
                "citizen_id": getattr(row, "citizen_id", ""),
                "ward": getattr(row, "ward", ""),
                "language": lang,
                "priority": getattr(row, "evacuation_priority", ""),
                "channels": channels,
                "message": body,
                "receipt": first_receipt,
            })

    return {
        "alert_type": alert_type,
        "total_targeted": int(len(targets)),
        "delivered": delivered,
        "denied": denied,
        "by_channel": by_channel,
        "by_language": by_language,
        "dry_run": dry_run,
        "sample": sample,
    }


def _distance_km(row, shelter: dict):
    """Best-effort distance from a precomputed column or haversine on the fly."""
    if hasattr(row, "ss_distance_km") and getattr(row, "ss_distance_km") is not None:
        return getattr(row, "ss_distance_km")
    if shelter and hasattr(row, "lat"):
        from app.core.geo import haversine_km
        return round(float(haversine_km(row.lat, row.lng, shelter["lat"], shelter["lng"])), 1)
    return "?"
