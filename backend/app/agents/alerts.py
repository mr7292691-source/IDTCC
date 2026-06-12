"""Agent 7 — Customer Alerts."""
from __future__ import annotations
from typing import Any, Dict, List
import pandas as pd
from app.core.llm import call_llm_simple


SYSTEM = (
    "You are an insurance customer communication specialist. "
    "Write a concise, empathetic SMS alert (max 160 characters). "
    "Mention the specific property risk. End with the policy ID. No hashtags."
)


def _generate_alert(twin: pd.Series) -> str:
    prompt = (
        f"Policyholder: {twin['policyholder']}\n"
        f"Address: {twin['address']}\n"
        f"Construction: {twin['construction_type']} built {twin['year_built']}\n"
        f"Flood zone: {twin['flood_zone']} | Claim probability: {twin['claim_probability']:.0%}\n"
        f"Policy ID: {twin['policy_id']}\n"
        "Write the SMS alert now."
    )
    return call_llm_simple(SYSTEM, prompt, max_tokens=80)


def run(df: pd.DataFrame, max_alerts: int = 20) -> Dict[str, Any]:
    critical = df[df["risk_color"] == "red"].nlargest(max_alerts, "claim_probability")
    alert_list: List[Dict] = []

    for _, twin in critical.iterrows():
        msg = _generate_alert(twin)
        alert_list.append({
            "twin_id":      twin["twin_id"],
            "policy_id":    twin["policy_id"],
            "policyholder": twin["policyholder"],
            "address":      twin["address"][:60],
            "flood_zone":   twin["flood_zone"],
            "claim_prob":   round(float(twin["claim_probability"]), 3),
            "risk_color":   twin["risk_color"],
            "message":      msg[:160],
        })

    total_alerted = int((df["risk_color"].isin(["red", "orange"])).sum())

    return {
        "total_alerts": total_alerted,
        "critical_alerts": int(len(df[df["risk_color"] == "red"])),
        "alerts": alert_list,
    }
