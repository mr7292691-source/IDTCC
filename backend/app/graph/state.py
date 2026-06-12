"""LangGraph state definition for the IDTCC pipeline."""
from __future__ import annotations
from typing import Annotated, Any, Dict, List, Optional
from typing_extensions import TypedDict
import operator


class IDTCCState(TypedDict):
    # ── Input ──────────────────────────────────────────────────
    location_code:   str
    location_name:   str
    twin_count:      int
    cyclone_params:  Dict[str, Any]

    # ── Intermediate ───────────────────────────────────────────
    # Stored as list of dicts (JSON-serialisable) because LangGraph
    # checkpointers must be able to serialise state.
    twins_records:   List[Dict[str, Any]]

    # ── Agent outputs ──────────────────────────────────────────
    weather_output:  Dict[str, Any]
    risk_output:     Dict[str, Any]
    claims_output:   Dict[str, Any]
    fraud_output:    Dict[str, Any]
    reserve_output:  Dict[str, Any]
    resource_output: Dict[str, Any]
    alerts_output:   Dict[str, Any]
    judge_scores:    Dict[str, Any]

    # ── Final ──────────────────────────────────────────────────
    forecast:          Dict[str, Any]
    executive_summary: str

    # ── Meta ───────────────────────────────────────────────────
    errors: Annotated[List[str], operator.add]
