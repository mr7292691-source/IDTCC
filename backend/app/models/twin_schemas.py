"""LifeShield digital-twin & safety-agent response schemas.

Kept separate from the insurance `schemas.py` so the two product lenses evolve
independently. All models use `extra="allow"` to match the existing convention
(agent payloads outpace the schema; we never want FastAPI to silently drop a
field the frontend relies on).
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.schemas import _AgentOutput  # reuse envelope (confidence + explainability)

Priority = Literal["critical", "high", "medium", "low"]


# ── Digital twins ─────────────────────────────────────────────────────────────

class CitizenTwin(BaseModel):
    model_config = ConfigDict(extra="allow")

    citizen_id: str
    pii_token: str                     # opaque vault key — never raw PII
    household_id: str
    age: int
    gender: Literal["M", "F", "O"]
    lat: float
    lng: float
    ward: str = ""
    district: str = ""
    state: str = ""
    disability_status: bool = False
    chronic_diseases: List[str] = []
    medical_dependency: Optional[str] = None
    pregnancy_status: bool = False
    owns_vehicle: bool = False
    can_walk_unassisted: bool = True
    transport_access: Literal["none", "public", "private"] = "public"
    preferred_language: str = "en"
    alert_channels: List[str] = ["sms"]
    # Emergency intelligence (agent-written)
    hazard_exposure: float = 0.0
    vulnerability_score: float = 0.0
    evacuation_priority: Priority = "low"
    rescue_priority: Priority = "low"
    assigned_shelter_id: Optional[str] = None


class ShelterTwin(BaseModel):
    model_config = ConfigDict(extra="allow")
    shelter_id: str
    name: str
    lat: float
    lng: float
    capacity: int
    current_occupancy: int = 0
    wheelchair_accessible: bool = True
    medical_capable: bool = False


# ── Safety-agent outputs ──────────────────────────────────────────────────────

class VulnerableOutput(_AgentOutput):
    total_citizens: int
    critical: int
    high: int
    medium: int
    low: int
    by_ward: Dict[str, float] = {}
    top_vulnerable: List[Dict[str, Any]] = []


class ShelterAllocationOutput(_AgentOutput):
    shelters_activated: int
    citizens_assigned: int
    unmet_demand: int
    occupancy_forecast: List[Dict[str, Any]] = []


class EvacuationOutput(_AgentOutput):
    routes: List[Dict[str, Any]] = []
    timeline: List[Dict[str, Any]] = []
    bottlenecks: List[str] = []
    total_to_evacuate: int = 0


class RescueOutput(_AgentOutput):
    critical: int
    high: int
    medium: int
    low: int
    rescue_queue: List[Dict[str, Any]] = []


class SensorOutput(_AgentOutput):
    overall_risk_score: float
    flood_forecast: Dict[str, Any] = {}
    breaches: List[Dict[str, Any]] = []


class InfrastructureOutput(_AgentOutput):
    at_risk_assets: int
    cascade_chains: List[Dict[str, Any]] = []
    asset_details: List[Dict[str, Any]] = []


class DamageOutput(_AgentOutput):
    tiles_analysed: int
    severe_zones: int
    roads_blocked: int
    stranded_persons: int
    max_water_depth_m: float = 0.0
    road_passability_map: List[Dict[str, Any]] = []
    stranded_locations: List[Dict[str, Any]] = []
    vision_model: str = "deterministic-fallback"


class DispatchSummary(BaseModel):
    model_config = ConfigDict(extra="allow")
    alert_type: str = ""
    total_targeted: int = 0
    delivered: int = 0
    denied: int = 0
    by_channel: Dict[str, int] = {}
    by_language: Dict[str, int] = {}
    dry_run: bool = True
    sample: List[Dict[str, Any]] = []


# ── Request / assembled plan ──────────────────────────────────────────────────

class SafetyRunRequest(BaseModel):
    location_code: str = Field("CHN", description="City code from CITY_CATALOGUE")
    twin_count: int = Field(20_000, ge=100, le=100_000,
                            description="Number of PROPERTY twins; citizens are exploded from these")
    hazard_name: str = "NIVAR"
    hazard_type: Literal["cyclone", "flood"] = "cyclone"
    max_wind_kmh: float = Field(180.0, ge=60, le=300)
    radius_km: float = Field(120.0, ge=20, le=300)
    landfall_eta_hours: int = Field(12, ge=1, le=120)
    # Optional live sensor snapshot injected by the sensor bus.
    sensor_snapshot: Dict[str, Any] = {}


class ResponsePlan(BaseModel):
    model_config = ConfigDict(extra="allow")

    event_name: str
    timestamp: str
    location: str
    landfall_eta_hours: int
    total_citizens: int
    citizens_at_risk: int
    critical_rescues: int
    shelters_activated: int
    citizens_assigned: int
    unmet_demand: int
    overall_confidence: float = 0.0
    agent_confidences: Dict[str, float] = {}
    consistency: Optional[Dict[str, Any]] = None
    executive_summary: str = ""
    # nested agent outputs
    vulnerable: Optional[VulnerableOutput] = None
    shelter: Optional[ShelterAllocationOutput] = None
    evacuation: Optional[EvacuationOutput] = None
    rescue: Optional[RescueOutput] = None
    sensor: Optional[SensorOutput] = None
    infrastructure: Optional[InfrastructureOutput] = None
    damage: Optional[DamageOutput] = None
    dispatched_alerts: Optional[DispatchSummary] = None
