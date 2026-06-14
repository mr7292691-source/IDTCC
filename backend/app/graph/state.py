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


class SafetyState(TypedDict):
    """State for the LifeShield life-safety pipeline (Lens B).

    Mirrors IDTCCState's conventions: heavy DataFrames are stored as lists of
    dicts (checkpointer-serialisable) and `errors` is an additive channel so a
    degraded agent appends rather than overwrites.
    """
    # ── Input ──────────────────────────────────────────────────
    location_code:  str
    location_name:  str
    state_code:     str
    center:         List[float]
    twin_count:     int
    hazard_params:  Dict[str, Any]
    sensor_snapshot: Dict[str, Any]

    # ── Substrate (serialised twins) ───────────────────────────
    citizen_records: List[Dict[str, Any]]
    shelter_records: List[Dict[str, Any]]
    infra_records:   List[Dict[str, Any]]

    # ── Agent outputs ──────────────────────────────────────────
    sensor_output:         Dict[str, Any]
    infrastructure_output: Dict[str, Any]
    damage_output:         Dict[str, Any]
    vulnerable_output:     Dict[str, Any]
    shelter_output:        Dict[str, Any]
    evacuation_output:     Dict[str, Any]
    rescue_output:         Dict[str, Any]
    judge_scores:          Dict[str, Any]

    # ── Final ──────────────────────────────────────────────────
    response_plan:     Dict[str, Any]
    executive_summary: str
    dispatched_alerts: Dict[str, Any]

    # ── Meta ───────────────────────────────────────────────────
    errors: Annotated[List[str], operator.add]
