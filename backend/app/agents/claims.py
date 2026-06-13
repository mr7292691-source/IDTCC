"""Agent 3 — Claims Forecast."""
from __future__ import annotations
from typing import Any, Dict
import pandas as pd
from app.core.llm import call_llm_simple
from app.core.agent_base import instrument, attach, compute_confidence


SYSTEM = (
    "You are a Chief Claims Officer. Forecast claims in 2 sentences. "
    "Use ₹ for currency. Be specific with numbers."
)


@instrument("claims")
def run(df: pd.DataFrame) -> Dict[str, Any]:
    red = df[df["risk_color"] == "red"]
    top5 = (
        df.groupby("area")["expected_loss_inr"]
        .sum()
        .nlargest(5)
        .apply(lambda x: round(x / 1e7, 2))
        .to_dict()
    )
    avg_loss = 0
    prob_above = df[df["claim_probability"] > 0.3]
    if len(prob_above) > 0:
        avg_loss = int(prob_above["expected_loss_inr"].mean())

    expected_claims = int(round(df["claim_probability"].sum()))
    total_loss_crore = round(df["expected_loss_inr"].sum() / 1e7, 2)

    prompt = (
        f"Expected claims: {expected_claims:,}\n"
        f"Total expected loss: ₹{total_loss_crore:.1f} Crore\n"
        f"Critical (red) properties: {len(red):,}\n"
        f"Top loss area: {list(top5.keys())[0] if top5 else 'N/A'} "
        f"(₹{list(top5.values())[0] if top5 else 0}Cr)\n"
        "Provide a claims forecast."
    )
    narrative = call_llm_simple(SYSTEM, prompt, max_tokens=200, agent="claims")

    out = {
        "expected_claim_count":      expected_claims,
        "expected_total_loss_crore": total_loss_crore,
        "red_twin_count":            int(len(red)),
        "avg_loss_per_claim_inr":    avg_loss,
        "top_loss_areas_crore":      top5,
        "narrative":                 narrative,
    }

    has_narrative = not narrative.startswith("[LLM unavailable")
    in_range = 0 <= expected_claims <= len(df) and total_loss_crore >= 0
    confidence = compute_confidence(
        data_coverage=1.0,
        has_narrative=has_narrative,
        within_expected_range=in_range,
    )
    return attach(
        out,
        confidence=confidence,
        why=(
            f"Expected {expected_claims:,} claims (₹{total_loss_crore:.1f}Cr) summing "
            f"per-property claim probabilities; {len(red):,} red (critical) properties."
        ),
        inputs_used=["claim_probability", "expected_loss_inr", "risk_color", "area"],
        evidence={
            "method": "expected_claims = Σ claim_probability; loss = Σ expected_loss_inr",
            "top_loss_areas_crore": top5,
            "avg_loss_per_claim_inr": avg_loss,
        },
    )
