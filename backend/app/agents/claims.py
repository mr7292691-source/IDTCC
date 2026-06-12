"""Agent 3 — Claims Forecast."""
from __future__ import annotations
from typing import Any, Dict
import pandas as pd
from app.core.llm import call_llm_simple


SYSTEM = (
    "You are a Chief Claims Officer. Forecast claims in 2 sentences. "
    "Use ₹ for currency. Be specific with numbers."
)


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

    prompt = (
        f"Expected claims: {int(df['claim_probability'].sum()):,}\n"
        f"Total expected loss: ₹{df['expected_loss_inr'].sum()/1e7:.1f} Crore\n"
        f"Critical (red) properties: {len(red):,}\n"
        f"Top loss area: {list(top5.keys())[0] if top5 else 'N/A'} "
        f"(₹{list(top5.values())[0] if top5 else 0}Cr)\n"
        "Provide a claims forecast."
    )
    narrative = call_llm_simple(SYSTEM, prompt, max_tokens=200)

    return {
        "expected_claim_count":      int(round(df["claim_probability"].sum())),
        "expected_total_loss_crore": round(df["expected_loss_inr"].sum() / 1e7, 2),
        "red_twin_count":            int(len(red)),
        "avg_loss_per_claim_inr":    avg_loss,
        "top_loss_areas_crore":      top5,
        "narrative":                 narrative,
    }
