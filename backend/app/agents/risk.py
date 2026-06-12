"""Agent 2 — Risk Exposure."""
from __future__ import annotations
from typing import Any, Dict
import pandas as pd
from app.core.llm import call_llm_simple


SYSTEM = (
    "You are a Chief Risk Officer at a major P&C insurer. "
    "Summarise the portfolio risk exposure in 2-3 sentences. "
    "Be specific with numbers. Use ₹ for currency."
)


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

    prompt = (
        f"Portfolio: {len(df):,} twins\n"
        f"In radius: {len(impact):,} ({len(impact)/len(df)*100:.1f}%)\n"
        f"Zone A twins: {(df['flood_zone']=='Zone_A').sum():,}\n"
        f"Total exposure: ₹{df['sum_insured_inr'].sum()/1e9:.1f}Bn\n"
        f"Max vulnerability: {df['vulnerability_index'].max():.3f}\n"
        "Summarise the key risk exposure metrics."
    )
    narrative = call_llm_simple(SYSTEM, prompt, max_tokens=200)

    return {
        "twins_in_impact_radius":      int(len(impact)),
        "total_portfolio_twins":       int(len(df)),
        "exposure_pct":                round(len(impact) / len(df) * 100, 1),
        "top10_highest_vulnerability": top10,
        "by_flood_zone":               by_zone,
        "by_flood_zone_loss_crore":    by_zone_loss,
        "total_exposure_bn_inr":       round(df["sum_insured_inr"].sum() / 1e9, 2),
        "narrative":                   narrative,
    }
