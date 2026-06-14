"""LifeShield life-safety LangGraph (Lens B).

Built with the same primitives as the insurance orchestrator: a StateGraph over
a TypedDict, nodes that wrap agents in try/except so one failure degrades
instead of crashing, parallel fan-out where dependencies allow, and a final
assembly node that aggregates confidence + a cross-agent consistency check.

Only `node_ingest`, `node_vulnerable` and `node_shelter` write `citizen_records`,
and they run in strictly sequential super-steps, so there is no concurrent write
to that channel.
"""
from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd
from langgraph.graph import END, START, StateGraph

from app.agents import judge as jg
from app.agents.safety import (
    damage as dmg,
    evacuation as ev,
    infrastructure as infra,
    rescue as rsc,
    sensor as sns,
    shelter as shl,
    vulnerable as vln,
)
from app.core import simulation as sim_core
from app.core.alerting.dispatcher import dispatch as dispatch_alerts
from app.core.llm import call_llm_simple
from app.core.twins.citizen import synthesize_citizens
from app.core.twins.shelter import build_shelter_twins
from app.graph.state import SafetyState


def _cdf(state: SafetyState) -> pd.DataFrame:
    return pd.DataFrame(state["citizen_records"])


# ── Nodes ─────────────────────────────────────────────────────────────────────

def node_ingest(state: SafetyState) -> Dict[str, Any]:
    loc_code = state["location_code"]
    n = state.get("twin_count", 20_000)
    hazard = state["hazard_params"]

    # Reuse the property engine, then explode households into citizens.
    pdf = sim_core.generate_twins(loc_code, n=n)
    pdf = sim_core.run_cyclone_simulation(pdf, hazard)
    citizens = synthesize_citizens(
        pdf, location_name=state.get("location_name", ""),
        state_code=state.get("state_code", ""),
    )
    shelters = build_shelter_twins(loc_code)

    return {
        "citizen_records": citizens.where(pd.notnull(citizens), None).to_dict("records"),
        "shelter_records": shelters,
        "infra_records": [],
        "errors": [],
    }


def node_sensor(state: SafetyState) -> Dict[str, Any]:
    try:
        out = sns.run(state.get("sensor_snapshot") or None, state["hazard_params"])
        return {"sensor_output": out}
    except Exception as exc:  # noqa: BLE001
        return {"sensor_output": {}, "errors": [f"sensor: {exc}"]}


def node_infrastructure(state: SafetyState) -> Dict[str, Any]:
    try:
        center = tuple(state.get("center") or (13.08, 80.27))
        out = infra.run(state.get("infra_records") or None, state["hazard_params"], center=center)
        return {"infrastructure_output": out}
    except Exception as exc:  # noqa: BLE001
        return {"infrastructure_output": {}, "errors": [f"infrastructure: {exc}"]}


def node_damage(state: SafetyState) -> Dict[str, Any]:
    try:
        center = tuple(state.get("center") or (13.08, 80.27))
        out = dmg.run(None, state["hazard_params"], center=center)
        return {"damage_output": out}
    except Exception as exc:  # noqa: BLE001
        return {"damage_output": {}, "errors": [f"damage: {exc}"]}


def node_vulnerable(state: SafetyState) -> Dict[str, Any]:
    try:
        df = vln.assign(_cdf(state))          # writes vulnerability + priority cols
        out = vln.run(df, state["hazard_params"])
        records = df.where(pd.notnull(df), None).to_dict("records")
        return {"vulnerable_output": out, "citizen_records": records}
    except Exception as exc:  # noqa: BLE001
        return {"vulnerable_output": {}, "errors": [f"vulnerable: {exc}"]}


def node_shelter(state: SafetyState) -> Dict[str, Any]:
    try:
        df = _cdf(state)
        shelters = state["shelter_records"]
        out = shl.run(df, shelters)
        # Write assignments back onto the citizen twins for downstream agents.
        assignments = out.get("assignments", {})
        df["assigned_shelter_id"] = df["citizen_id"].map(assignments).fillna(
            df.get("assigned_shelter_id"))
        records = df.where(pd.notnull(df), None).to_dict("records")
        # Drop the bulky assignments map from the streamed output.
        out_clean = {k: v for k, v in out.items() if k != "assignments"}
        return {"shelter_output": out_clean, "citizen_records": records}
    except Exception as exc:  # noqa: BLE001
        return {"shelter_output": {}, "errors": [f"shelter: {exc}"]}


def node_evacuation(state: SafetyState) -> Dict[str, Any]:
    try:
        out = ev.run(_cdf(state), state["shelter_records"], state["hazard_params"])
        return {"evacuation_output": out}
    except Exception as exc:  # noqa: BLE001
        return {"evacuation_output": {}, "errors": [f"evacuation: {exc}"]}


def node_rescue(state: SafetyState) -> Dict[str, Any]:
    try:
        out = rsc.run(_cdf(state), state["hazard_params"])
        return {"rescue_output": out}
    except Exception as exc:  # noqa: BLE001
        return {"rescue_output": {}, "errors": [f"rescue: {exc}"]}


def node_judge(state: SafetyState) -> Dict[str, Any]:
    context = {
        "location": state.get("location_name", ""),
        "hazard": state["hazard_params"].get("name", "event"),
        "wind_kmh": state["hazard_params"].get("max_wind_kmh", 0),
    }
    scores: Dict[str, Any] = {}
    for pred_type, data in [
        ("vulnerable", state.get("vulnerable_output", {})),
        ("shelter",    state.get("shelter_output", {})),
        ("evacuation", state.get("evacuation_output", {})),
    ]:
        try:
            scores[pred_type] = jg.evaluate(pred_type, data, context)
        except Exception as exc:  # noqa: BLE001
            scores[pred_type] = {"error": str(exc)}
    return {"judge_scores": scores}


def _consistency(state: SafetyState) -> Dict[str, Any]:
    """Cheap cross-agent sanity checks specific to the safety lens."""
    issues: List[str] = []
    vuln = state.get("vulnerable_output", {})
    shelter = state.get("shelter_output", {})
    evac = state.get("evacuation_output", {})

    critical = vuln.get("critical", 0)
    assigned = shelter.get("citizens_assigned", 0)
    unmet = shelter.get("unmet_demand", 0)
    if critical and assigned == 0:
        issues.append("Critical vulnerable citizens exist but none were assigned a shelter.")
    if unmet and unmet > assigned:
        issues.append("Unmet shelter demand exceeds assigned — capacity shortfall.")
    if evac.get("total_to_evacuate", 0) and not evac.get("routes"):
        issues.append("Evacuees identified but no routes were generated.")

    score = round(max(0.0, 1.0 - 0.25 * len(issues)), 3)
    return {"consistent": not issues, "consistency_score": score, "issues": issues}


def node_assemble(state: SafetyState) -> Dict[str, Any]:
    import pandas as _pd

    hazard = state["hazard_params"]
    vuln = state.get("vulnerable_output", {})
    shelter = state.get("shelter_output", {})
    rescue = state.get("rescue_output", {})

    consistency = _consistency(state)
    agent_conf = {
        name: out.get("confidence")
        for name, out in (
            ("sensor", state.get("sensor_output", {})),
            ("infrastructure", state.get("infrastructure_output", {})),
            ("damage", state.get("damage_output", {})),
            ("vulnerable", vuln), ("shelter", shelter),
            ("evacuation", state.get("evacuation_output", {})),
            ("rescue", rescue),
        )
        if isinstance(out, dict) and out.get("confidence") is not None
    }
    mean_conf = round(sum(agent_conf.values()) / len(agent_conf), 3) if agent_conf else 0.0
    overall = round(mean_conf * consistency["consistency_score"], 3)

    total = vuln.get("total_citizens", 0)
    at_risk = vuln.get("critical", 0) + vuln.get("high", 0)

    plan = {
        "event_name": hazard.get("name", "event"),
        "timestamp": _pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "location": state.get("location_name", ""),
        "landfall_eta_hours": hazard.get("landfall_eta_hours", 12),
        "total_citizens": total,
        "citizens_at_risk": at_risk,
        "critical_rescues": rescue.get("critical", 0),
        "shelters_activated": shelter.get("shelters_activated", 0),
        "citizens_assigned": shelter.get("citizens_assigned", 0),
        "unmet_demand": shelter.get("unmet_demand", 0),
        "overall_confidence": overall,
        "agent_confidences": agent_conf,
        "consistency": consistency,
    }

    EXEC_SYSTEM = (
        "You are the AI Incident Commander of a city disaster management authority. "
        "Write a concise 3-sentence executive brief for the response team. "
        "Be specific with numbers. Tone: urgent, controlled, action-oriented."
    )
    prompt = (
        f"Event: {plan['event_name']} | ETA: {plan['landfall_eta_hours']}h | "
        f"Location: {plan['location']}\n"
        f"Citizens at risk: {at_risk:,} of {total:,} | "
        f"Critical rescues: {plan['critical_rescues']:,}\n"
        f"Shelters activated: {plan['shelters_activated']} | "
        f"Assigned: {plan['citizens_assigned']:,} | Unmet: {plan['unmet_demand']:,}"
    )
    summary = call_llm_simple(EXEC_SYSTEM, prompt, max_tokens=200, agent="assemble")

    return {"response_plan": plan, "executive_summary": summary}


def node_dispatch(state: SafetyState) -> Dict[str, Any]:
    """Layer 7 — render + (simulated) deliver personalized multilingual alerts
    to the critical/high citizens the pipeline just identified."""
    try:
        df = _cdf(state)
        hazard = dict(state["hazard_params"])
        hazard.setdefault("landfall_eta_hours", hazard.get("landfall_eta_h", 12))
        alert_type = "flood_warning" if hazard.get("hazard_type") == "flood" else "cyclone_warning"
        result = dispatch_alerts(
            df, alert_type=alert_type, hazard=hazard,
            shelters=state.get("shelter_records", []), dry_run=True,
        )
        return {"dispatched_alerts": result}
    except Exception as exc:  # noqa: BLE001
        return {"dispatched_alerts": {}, "errors": [f"dispatch: {exc}"]}


# ── Graph ─────────────────────────────────────────────────────────────────────

def build_safety_graph():
    b = StateGraph(SafetyState)

    b.add_node("ingest", node_ingest)
    b.add_node("sensor_agent", node_sensor)
    b.add_node("infrastructure_agent", node_infrastructure)
    b.add_node("damage_agent", node_damage)
    b.add_node("vulnerable_agent", node_vulnerable)
    b.add_node("shelter_agent", node_shelter)
    b.add_node("evacuation_agent", node_evacuation)
    b.add_node("rescue_agent", node_rescue)
    b.add_node("judge_agent", node_judge)
    b.add_node("assemble", node_assemble)
    b.add_node("dispatch_alerts", node_dispatch)

    b.add_edge(START, "ingest")
    # Sensor / infra / damage fan out (read-only on twins); vulnerable writes twins.
    b.add_edge("ingest", "sensor_agent")
    b.add_edge("ingest", "infrastructure_agent")
    b.add_edge("ingest", "damage_agent")
    b.add_edge("ingest", "vulnerable_agent")

    # Shelter needs vulnerability scores; it joins after vulnerable.
    b.add_edge("vulnerable_agent", "shelter_agent")

    # Evacuation + rescue run in parallel once shelters are assigned.
    b.add_edge("shelter_agent", "evacuation_agent")
    b.add_edge("shelter_agent", "rescue_agent")

    # Judge waits for the human-safety chain + the sensor/infra/damage context.
    b.add_edge("sensor_agent", "judge_agent")
    b.add_edge("infrastructure_agent", "judge_agent")
    b.add_edge("damage_agent", "judge_agent")
    b.add_edge("evacuation_agent", "judge_agent")
    b.add_edge("rescue_agent", "judge_agent")

    b.add_edge("judge_agent", "assemble")
    # Layer 7 — communication: dispatch personalized alerts as the final step.
    b.add_edge("assemble", "dispatch_alerts")
    b.add_edge("dispatch_alerts", END)
    return b.compile()


_safety_graph = None


def get_safety_graph():
    global _safety_graph
    if _safety_graph is None:
        _safety_graph = build_safety_graph()
    return _safety_graph
