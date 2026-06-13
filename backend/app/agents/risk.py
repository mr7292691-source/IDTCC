"""Agent 2 — Risk Exposure."""
from __future__ import annotations
from typing import Any, Dict
import pandas as pd
from app.core.llm import call_llm_simple
from app.core.agent_base import instrument, attach, compute_confidence


SYSTEM = (
    "You are a Chief Risk Officer at a major P&C insurer. "
    "Summarise the portfolio risk exposure in 2-3 sentences. "
    "Be specific with numbers. Use ₹ for currency."
)


@instrument("risk")
def run(df: pd.DataFrame, cyclone: Dict[str, Any]) -> Dict[str, Any]:
    radius = cyclone.get("radius_km", 120)
    impact = df[df["dist_from_storm_km"] <= radius]

    top10 = df.nlargest(10, "vulnerability_index")[
        ["twin_id", "address", "vulnerability_index", "flood_zone", "claim_probability"]
    ].to_dict("records")

    by_zone = (
        df.groupby("flood_zone")["claim_probability"]
        .agg(count="count", avg_prob="mean")
        .round(3)
        .to_dict()
    )
    by_zone_loss = (
        df.groupby("flood_zone")["expected_loss_inr"]
        .sum()
        .apply(lambda x: round(x / 1e7, 2))
        .to_dict()
    )

    exposure_pct = round(len(impact) / len(df) * 100, 1)
    total_exposure_bn = round(df["sum_insured_inr"].sum() / 1e9, 2)

    prompt = (
        f"Portfolio: {len(df):,} twins\n"
        f"In radius: {len(impact):,} ({exposure_pct}%)\n"
        f"Zone A twins: {(df['flood_zone']=='Zone_A').sum():,}\n"
        f"Total exposure: ₹{total_exposure_bn}Bn\n"
        f"Max vulnerability: {df['vulnerability_index'].max():.3f}\n"
        "Summarise the key risk exposure metrics."
    )
    narrative = call_llm_simple(SYSTEM, prompt, max_tokens=200, agent="risk")

    out = {
        "twins_in_impact_radius":      int(len(impact)),
        "total_portfolio_twins":       int(len(df)),
        "exposure_pct":                exposure_pct,
        "top10_highest_vulnerability": top10,
        "by_flood_zone":               by_zone,
        "by_flood_zone_loss_crore":    by_zone_loss,
        "total_exposure_bn_inr":       total_exposure_bn,
        "narrative":                   narrative,
    }

    has_narrative = not narrative.startswith("[LLM unavailable")
    in_range = 0.0 <= exposure_pct <= 100.0 and len(df) > 0
    confidence = compute_confidence(
        data_coverage=1.0,  # whole portfolio is scanned
        has_narrative=has_narrative,
        within_expected_range=in_range,
    )
    return attach(
        out,
        confidence=confidence,
        why=(
            f"{len(impact):,} of {len(df):,} properties ({exposure_pct}%) fall within "
            f"the {radius} km impact radius; ₹{total_exposure_bn}Bn total sum insured."
        ),
        inputs_used=["dist_from_storm_km", "vulnerability_index", "flood_zone",
                     "expected_loss_inr", "sum_insured_inr"],
        evidence={
            "impact_radius_km": radius,
            "zone_a_twins": int((df["flood_zone"] == "Zone_A").sum()),
            "max_vulnerability_index": round(float(df["vulnerability_index"].max()), 4),
            "loss_by_zone_crore": by_zone_loss,
        },
    )
