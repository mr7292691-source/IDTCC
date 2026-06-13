/**
 * Shared API type definitions — the single source of truth for the
 * frontend⇄backend contract. These mirror the Pydantic models in
 * backend/app/models/schemas.py one-to-one. When you change a backend schema,
 * update this file in the same PR (CI checks the field list — see
 * .github/workflows/ci.yml → schema-parity).
 *
 * JS files reference these via JSDoc:  @param {import('../types/api').ForecastResponse}
 */

export interface SimulationRequest {
  location_code: string;
  twin_count: number;
  cyclone_name: string;
  max_wind_kmh: number;
  landfall_eta_hours: number;
  radius_km: number;
  track_shift_km: number;
}

export interface Explainability {
  why: string;
  inputs_used: string[];
  evidence: Record<string, unknown>;
}

/** Every agent output carries this envelope on top of its domain fields. */
export interface AgentEnvelope {
  confidence: number;                 // 0..1
  explainability?: Explainability | null;
  narrative?: string | null;
}

export interface RiskOutput extends AgentEnvelope {
  twins_in_impact_radius: number;
  total_portfolio_twins: number;
  exposure_pct: number;
  top10_highest_vulnerability: Array<Record<string, unknown>>;
  by_flood_zone: Record<string, unknown>;
  by_flood_zone_loss_crore: Record<string, number>;
  total_exposure_bn_inr: number;
}

export interface ClaimsOutput extends AgentEnvelope {
  expected_claim_count: number;
  expected_total_loss_crore: number;
  red_twin_count: number;
  avg_loss_per_claim_inr: number;
  top_loss_areas_crore: Record<string, number>;
}

export interface FraudOutput extends AgentEnvelope {
  total_fraud_risk_twins: number;
  known_fraud_flags: number;
  suspicious_profiles: number;
  faiss_anomaly_count: number;
  estimated_fraud_exposure_crore: number;
  top_suspicious: Array<Record<string, unknown>>;
}

export interface ReserveOutput extends AgentEnvelope {
  base_reserve_crore: number;
  ibnr_crore: number;
  cat_buffer_crore: number;
  total_recommended_reserve_crore: number;
  reserve_adequacy_ratio: number;
  scenarios: Record<string, number>;
}

export interface DeploymentZone {
  zone_id: string;
  center_lat: number;
  center_lng: number;
  twin_count: number;
  avg_claim_prob: number;
  top_area: string;
}

export interface ResourceOutput extends AgentEnvelope {
  adjusters_needed: number;
  deployment_zones: number;
  adjusters_per_zone: number;
  red_twins_clustered: number;
  zone_details: DeploymentZone[];
  deployment_strategy: string;
}

export interface AlertOutput extends AgentEnvelope {
  total_alerts: number;
  critical_alerts: number;
  alerts: Array<Record<string, unknown>>;
}

export interface JudgeScore {
  factual_accuracy: number;
  completeness: number;
  actionability: number;
  vulnerable_population_safety: number;
  financial_soundness: number;
  overall_score: number;
  verdict: 'APPROVED' | 'REVIEW_NEEDED' | 'REJECTED' | string;
  approved: boolean;
  critique: string;
  improvements: string[];
  confidence: number;
}

export interface JudgeOutput {
  weather?: JudgeScore | null;
  claims?: JudgeScore | null;
  resource?: JudgeScore | null;
  executive?: JudgeScore | null;
}

export interface ConsistencyReport {
  consistent: boolean;
  consistency_score: number;
  issues: string[];
}

export interface ForecastResponse {
  event_name: string;
  simulation_timestamp: string;
  location: string;
  landfall_eta_hours: number;
  total_portfolio_twins: number;
  twins_in_impact_radius: number;
  red_twins: number;
  expected_claim_count: number;
  expected_loss_crore: number;
  reserve_required_crore: number;
  adjusters_needed: number;
  deployment_zones: number;
  fraud_risk_twins: number;
  alerts_to_send: number;
  storm_severity_index: number;
  primary_hazards: string[];
  top_loss_areas: Record<string, number>;
  executive_summary: string;
  overall_confidence: number;
  agent_confidences: Record<string, number>;
  consistency?: ConsistencyReport | null;
  risk?: RiskOutput | null;
  claims?: ClaimsOutput | null;
  fraud?: FraudOutput | null;
  reserve?: ReserveOutput | null;
  resource?: ResourceOutput | null;
  alerts?: AlertOutput | null;
  judge_scores?: JudgeOutput | null;
  graph_trace_url?: string | null;
}

export interface PropertyTwin {
  twin_id: string;
  lat: number;
  lng: number;
  address: string;
  area: string;
  construction_type: string;
  flood_zone: string;
  vulnerability_index: number;
  claim_probability: number;
  expected_loss_inr: number;
  risk_color: 'red' | 'orange' | 'yellow' | 'green' | string;
  sum_insured_inr: number;
  year_built: number;
}

export interface SafeSpace {
  id: string;
  name: string;
  lat: number;
  lng: number;
  capacity: number;
  resources: Record<string, unknown>;
  assigned_count: number;
}

export interface TwinsResponse {
  total: number;
  twins: PropertyTwin[];
  safe_spaces: SafeSpace[];
}

/** SSE event shape from POST /api/v1/simulation/stream */
export interface AgentStreamEvent {
  agent: string;                                  // node name or "system"
  status: 'start' | 'done' | 'error' | 'complete';
  message?: string;
  output?: Record<string, unknown>;
}
