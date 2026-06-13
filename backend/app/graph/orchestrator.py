"""LangGraph multi-agent orchestration with LangSmith tracing."""
from __future__ import annotations

import os
import pandas as pd
from typing import Any, Dict

from langgraph.graph import StateGraph, START, END

from app.graph.state import IDTCCState
from app.core import simulation as sim_core
from app.core.llm import call_llm_simple
from app.agents import weather as wa
from app.agents import risk as ra
from app.agents import claims as ca
from app.agents import fraud as fa
from app.agents import reserve as rv
from app.agents import resource as rs
from app.agents import alerts as al
from app.agents import judge as jg


# ── Helper to restore DataFrame from stored records ──────────────────────────

def _df(state: IDTCCState) -> pd.DataFrame:
    return pd.DataFrame(state["twins_records"])


# ── Node implementations ──────────────────────────────────────────────────────

def node_generate_twins(state: IDTCCState) -> Dict[str, Any]:
    loc_code   = state["location_code"]
    n_twins    = state.get("twin_count", 50_000)
    cyclone    = state["cyclone_params"]

    df = sim_core.generate_twins(loc_code, n=n_twins)
    df = sim_core.run_cyclone_simulation(df, cyclone)

    safe_spaces = sim_core.build_safe_spaces(loc_code)
    df = sim_core.assign_safe_spaces(df, safe_spaces)

    # Convert to list of dicts for LangGraph serialisation
    records = df.where(pd.notnull(df), None).to_dict("records")
    return {"twins_records": records, "errors": []}


def node_weather(state: IDTCCState) -> Dict[str, Any]:
    try:
        out = wa.run(state["cyclone_params"], state["location_name"])
        return {"weather_output": out}
    except Exception as exc:
        return {"weather_output": {}, "errors": [f"weather: {exc}"]}


def node_risk(state: IDTCCState) -> Dict[str, Any]:
    try:
        out = ra.run(_df(state), state["cyclone_params"])
        return {"risk_output": out}
    except Exception as exc:
        return {"risk_output": {}, "errors": [f"risk: {exc}"]}


def node_claims(state: IDTCCState) -> Dict[str, Any]:
    try:
        out = ca.run(_df(state))
        return {"claims_output": out}
    except Exception as exc:
        return {"claims_output": {}, "errors": [f"claims: {exc}"]}


def node_fraud(state: IDTCCState) -> Dict[str, Any]:
    try:
        out = fa.run(_df(state))
        return {"fraud_output": out}
    except Exception as exc:
        return {"fraud_output": {}, "errors": [f"fraud: {exc}"]}


def node_reserve(state: IDTCCState) -> Dict[str, Any]:
    try:
        out = rv.run(_df(state), state.get("claims_output", {}))
        return {"reserve_output": out}
    except Exception as exc:
        return {"reserve_output": {}, "errors": [f"reserve: {exc}"]}


def node_resource(state: IDTCCState) -> Dict[str, Any]:
    try:
        out = rs.run(_df(state))
        return {"resource_output": out}
    except Exception as exc:
        return {"resource_output": {}, "errors": [f"resource: {exc}"]}


def node_alerts(state: IDTCCState) -> Dict[str, Any]:
    try:
        out = al.run(_df(state), max_alerts=20)
        return {"alerts_output": out}
    except Exception as exc:
        return {"alerts_output": {}, "errors": [f"alerts: {exc}"]}


def node_judge(state: IDTCCState) -> Dict[str, Any]:
    cyclone = state["cyclone_params"]
    context = {
        "location": state["location_name"],
        "cyclone":  cyclone.get("name", "NIVAR"),
        "wind_kmh": cyclone.get("max_wind_kmh", 180),
    }
    scores: Dict[str, Any] = {}
    for pred_type, pred_data in [
        ("weather",   state.get("weather_output", {})),
        ("claims",    state.get("claims_output",  {})),
        ("resource",  state.get("resource_output",{})),
    ]:
        try:
            scores[pred_type] = jg.evaluate(pred_type, pred_data, context)
        except Exception as exc:
            scores[pred_type] = {"error": str(exc)}
    return {"judge_scores": scores}


def node_assemble_forecast(state: IDTCCState) -> Dict[str, Any]:
    import pandas as _pd
    from app.core.guardrails import check_consistency

    cyclone   = state["cyclone_params"]
    risk      = state.get("risk_output",     {})
    claims    = state.get("claims_output",   {})
    fraud     = state.get("fraud_output",    {})
    reserve   = state.get("reserve_output",  {})
    resource  = state.get("resource_output", {})
    weather   = state.get("weather_output",  {})

    # ── Cross-agent consistency guardrail ────────────────────────────────────
    consistency = check_consistency(state)

    # ── Aggregate per-agent confidence ───────────────────────────────────────
    agent_confidences = {
        name: out.get("confidence")
        for name, out in (
            ("weather",  weather),  ("risk",     risk),
            ("claims",   claims),   ("fraud",    fraud),
            ("reserve",  reserve),  ("resource", resource),
            ("alerts",   state.get("alerts_output", {})),
        )
        if isinstance(out, dict) and out.get("confidence") is not None
    }
    mean_conf = (
        round(sum(agent_confidences.values()) / len(agent_confidences), 3)
        if agent_confidences else 0.0
    )
    # Penalise overall confidence by any cross-agent contradictions.
    overall_confidence = round(mean_conf * consistency["consistency_score"], 3)

    forecast = {
        "event_name":             cyclone.get("name", "NIVAR"),
        "simulation_timestamp":   _pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "location":               state["location_name"],
        "landfall_eta_hours":     cyclone.get("landfall_eta_hours", 48),
        "total_portfolio_twins":  risk.get("total_portfolio_twins", 0),
        "twins_in_impact_radius": risk.get("twins_in_impact_radius", 0),
        "red_twins":              claims.get("red_twin_count", 0),
        "expected_claim_count":   claims.get("expected_claim_count", 0),
        "expected_loss_crore":    claims.get("expected_total_loss_crore", 0.0),
        "reserve_required_crore": reserve.get("total_recommended_reserve_crore", 0.0),
        "adjusters_needed":       resource.get("adjusters_needed", 0),
        "deployment_zones":       resource.get("deployment_zones", 0),
        "fraud_risk_twins":       fraud.get("total_fraud_risk_twins", 0),
        "alerts_to_send":         claims.get("red_twin_count", 0),
        "storm_severity_index":   weather.get("storm_severity_index", 0.0),
        "primary_hazards":        weather.get("primary_hazards", []),
        "top_loss_areas":         claims.get("top_loss_areas_crore", {}),
        # ── Confidence + guardrail summary ───────────────────────────────────
        "overall_confidence":     overall_confidence,
        "agent_confidences":      agent_confidences,
        "consistency":            consistency,
    }

    # Executive summary
    EXEC_SYSTEM = (
        "You are the AI Chief Risk Officer of a major insurance company. "
        "Write a concise 3-sentence executive summary for the board. "
        "Be specific with numbers. Use ₹ for currency. Tone: urgent but controlled."
    )
    summary_prompt = (
        f"Event: Cyclone {forecast['event_name']} | "
        f"ETA: {forecast['landfall_eta_hours']}h | "
        f"Location: {forecast['location']}\n"
        f"Critical properties: {forecast['red_twins']:,} | "
        f"Expected loss: ₹{forecast['expected_loss_crore']:.1f}Cr | "
        f"Reserve: ₹{forecast['reserve_required_crore']:.1f}Cr\n"
        f"Adjusters needed: {forecast['adjusters_needed']} across {forecast['deployment_zones']} zones | "
        f"Fraud-risk: {forecast['fraud_risk_twins']:,}"
    )
    executive_summary = call_llm_simple(EXEC_SYSTEM, summary_prompt, max_tokens=200)

    return {
        "forecast":          forecast,
        "executive_summary": executive_summary,
    }


# ── Build the graph ───────────────────────────────────────────────────────────

def build_graph():
    builder = StateGraph(IDTCCState)

    builder.add_node("generate_twins",     node_generate_twins)
    builder.add_node("weather_agent",      node_weather)
    builder.add_node("risk_agent",         node_risk)
    builder.add_node("claims_agent",       node_claims)
    builder.add_node("fraud_agent",        node_fraud)
    builder.add_node("reserve_agent",      node_reserve)
    builder.add_node("resource_agent",     node_resource)
    builder.add_node("alerts_agent",       node_alerts)
    builder.add_node("judge_agent",        node_judge)
    builder.add_node("assemble_forecast",  node_assemble_forecast)

    # Sequential flow — weather and risk run after twin generation
    builder.add_edge(START,            "generate_twins")
    builder.add_edge("generate_twins", "weather_agent")
    builder.add_edge("weather_agent",  "risk_agent")

    # Claims and fraud run in parallel after risk
    builder.add_edge("risk_agent",     "claims_agent")
    builder.add_edge("risk_agent",     "fraud_agent")

    # Reserve waits for claims
    builder.add_edge("claims_agent",   "reserve_agent")

    # Resource and alerts run in parallel after reserve (need claims data)
    builder.add_edge("reserve_agent",  "resource_agent")
    builder.add_edge("reserve_agent",  "alerts_agent")

    # Fraud also feeds into judge (can join after both claims+fraud done)
    builder.add_edge("fraud_agent",    "judge_agent")
    builder.add_edge("resource_agent", "judge_agent")
    builder.add_edge("alerts_agent",   "judge_agent")

    # Final assembly
    builder.add_edge("judge_agent",    "assemble_forecast")
    builder.add_edge("assemble_forecast", END)

    return builder.compile()


# Singleton graph
_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph
