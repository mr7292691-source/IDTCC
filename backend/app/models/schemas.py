from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
from typing import Any, Dict, List, Optional


# ── Shared envelope models ────────────────────────────────────────────────────

class Explainability(BaseModel):
    """Why a decision was made, what fed it, and the supporting evidence."""
    why: str
    inputs_used: List[str] = []
    evidence: Dict[str, Any] = {}


class _AgentOutput(BaseModel):
    """Base for agent outputs.

    `extra="allow"` is deliberate: agent payloads evolve faster than the schema,
    and FastAPI's response_model filtering would otherwise silently drop fields
    the frontend relies on (the historical source of schema drift). Every agent
    output therefore carries the full envelope plus any domain extras.
    """
    model_config = ConfigDict(extra="allow")

    confidence: float = Field(0.0, ge=0.0, le=1.0)
    explainability: Optional[Explainability] = None
    narrative: Optional[str] = None


class SimulationRequest(BaseModel):
    location_code: str = Field("CHN", description="City code from LOCATION_CATALOGUE")
    twin_count: int = Field(50_000, ge=100, le=100_000)
    cyclone_name: str = "NIVAR"
    max_wind_kmh: float = Field(180.0, ge=60, le=300)
    landfall_eta_hours: int = Field(48, ge=6, le=120)
    radius_km: float = Field(120.0, ge=20, le=300)
    track_shift_km: float = Field(0.0, description="Counterfactual track shift northward")


class PropertyTwin(BaseModel):
    twin_id: str
    lat: float
    lng: float
    address: str
    area: str
    construction_type: str
    flood_zone: str
    vulnerability_index: float
    claim_probability: float
    expected_loss_inr: float
    risk_color: str
    sum_insured_inr: float
    year_built: int


class ZoneStats(BaseModel):
    count: int
    avg_prob: float
    total_loss: float


class RiskOutput(_AgentOutput):
    twins_in_impact_radius: int
    total_portfolio_twins: int
    exposure_pct: float
    top10_highest_vulnerability: List[Dict[str, Any]]
    by_flood_zone: Dict[str, Any]
    by_flood_zone_loss_crore: Dict[str, float] = {}
    total_exposure_bn_inr: float = 0.0


class ClaimsOutput(_AgentOutput):
    expected_claim_count: int
    expected_total_loss_crore: float
    red_twin_count: int
    avg_loss_per_claim_inr: int
    top_loss_areas_crore: Dict[str, float]


class FraudOutput(_AgentOutput):
    total_fraud_risk_twins: int
    known_fraud_flags: int
    suspicious_profiles: int
    faiss_anomaly_count: int = 0
    estimated_fraud_exposure_crore: float
    top_suspicious: List[Dict[str, Any]]


class ReserveOutput(_AgentOutput):
    base_reserve_crore: float
    ibnr_crore: float
    cat_buffer_crore: float
    total_recommended_reserve_crore: float
    reserve_adequacy_ratio: float
    scenarios: Dict[str, float] = {}


class DeploymentZone(BaseModel):
    zone_id: str
    center_lat: float
    center_lng: float
    twin_count: int
    avg_claim_prob: float
    top_area: str


class ResourceOutput(_AgentOutput):
    adjusters_needed: int
    deployment_zones: int
    adjusters_per_zone: float
    red_twins_clustered: int
    zone_details: List[DeploymentZone]
    deployment_strategy: str


class AlertOutput(_AgentOutput):
    total_alerts: int
    critical_alerts: int
    alerts: List[Dict[str, Any]]


class JudgeScore(BaseModel):
    model_config = ConfigDict(extra="allow")

    factual_accuracy: float
    completeness: float
    actionability: float
    vulnerable_population_safety: float
    financial_soundness: float
    overall_score: float
    verdict: str
    approved: bool
    critique: str
    improvements: List[str] = []
    confidence: float = Field(0.0, ge=0.0, le=1.0)


class JudgeOutput(BaseModel):
    model_config = ConfigDict(extra="allow")

    weather: Optional[JudgeScore] = None
    claims: Optional[JudgeScore] = None
    resource: Optional[JudgeScore] = None
    executive: Optional[JudgeScore] = None


class ConsistencyReport(BaseModel):
    consistent: bool
    consistency_score: float
    issues: List[str] = []


class ForecastResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    event_name: str
    simulation_timestamp: str
    location: str
    landfall_eta_hours: int
    total_portfolio_twins: int
    twins_in_impact_radius: int
    red_twins: int
    expected_claim_count: int
    expected_loss_crore: float
    reserve_required_crore: float
    adjusters_needed: int
    deployment_zones: int
    fraud_risk_twins: int
    alerts_to_send: int
    storm_severity_index: float
    primary_hazards: List[str]
    top_loss_areas: Dict[str, float]
    executive_summary: str
    # Confidence + guardrail summary
    overall_confidence: float = Field(0.0, ge=0.0, le=1.0)
    agent_confidences: Dict[str, float] = {}
    consistency: Optional[ConsistencyReport] = None
    # Full nested agent outputs
    risk: Optional[RiskOutput] = None
    claims: Optional[ClaimsOutput] = None
    fraud: Optional[FraudOutput] = None
    reserve: Optional[ReserveOutput] = None
    resource: Optional[ResourceOutput] = None
    alerts: Optional[AlertOutput] = None
    judge_scores: Optional[JudgeOutput] = None
    graph_trace_url: Optional[str] = None


class SafeSpace(BaseModel):
    id: str
    name: str
    lat: float
    lng: float
    capacity: int
    resources: Dict[str, Any]
    assigned_count: int = 0


class TwinsResponse(BaseModel):
    total: int
    twins: List[PropertyTwin]
    safe_spaces: List[SafeSpace] = []


class AgentStatusEvent(BaseModel):
    agent: str
    status: str  # running | done | error
    message: str = ""
    output: Optional[Dict[str, Any]] = None
