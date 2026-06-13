"""Agent 6 — Resource Planning (K-Means adjuster deployment)."""
from __future__ import annotations
import math
from typing import Any, Dict, List
import numpy as np
import pandas as pd
from app.core.llm import call_llm_simple
from app.core.agent_base import instrument, attach, compute_confidence


SYSTEM = (
    "You are an insurance operations director. "
    "In 2 sentences describe the adjuster deployment strategy."
)


@instrument("resource")
def run(df: pd.DataFrame) -> Dict[str, Any]:
    red_twins = df[df["risk_color"] == "red"].copy()
    if len(red_twins) < 10:
        return attach(
            {"error": "Insufficient red twins for clustering",
             "adjusters_needed": 0, "deployment_zones": 0,
             "adjusters_per_zone": 0.0, "red_twins_clustered": int(len(red_twins)),
             "zone_details": [], "deployment_strategy": "No critical clusters detected"},
            confidence=0.5,
            why="Fewer than 10 red-zone properties — clustering not statistically meaningful.",
            inputs_used=["risk_color"],
            evidence={"red_twins": int(len(red_twins))},
        )

    expected_claims  = float(red_twins["claim_probability"].sum())
    adjusters_needed = max(5, int(math.ceil(expected_claims / 120)))

    n_clusters = min(adjusters_needed, 15, len(red_twins))
    coords     = red_twins[["lat", "lng"]].values

    kmeans_used = False
    try:
        from sklearn.cluster import KMeans
        km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        red_twins = red_twins.copy()
        red_twins["zone"] = km.fit_predict(coords)
        centers = km.cluster_centers_
        kmeans_used = True
    except Exception:
        # Fallback: assign random zones
        red_twins = red_twins.copy()
        red_twins["zone"] = np.random.randint(0, n_clusters, size=len(red_twins))
        centers = np.array([coords[red_twins["zone"] == z].mean(axis=0) if (red_twins["zone"] == z).any()
                            else coords.mean(axis=0)
                            for z in range(n_clusters)])

    zone_details: List[Dict] = []
    for z in range(n_clusters):
        zt = red_twins[red_twins["zone"] == z]
        if len(zt) == 0:
            continue
        zone_details.append({
            "zone_id":        f"ZONE-{z+1:02d}",
            "center_lat":     round(float(centers[z][0]), 4),
            "center_lng":     round(float(centers[z][1]), 4),
            "twin_count":     int(len(zt)),
            "avg_claim_prob": round(float(zt["claim_probability"].mean()), 3),
            "top_area":       str(zt["area"].mode().iloc[0]) if len(zt) > 0 else "N/A",
        })

    prompt = (
        f"Red-zone properties: {len(red_twins):,}\n"
        f"Expected claims: {expected_claims:.0f}\n"
        f"Adjusters needed: {adjusters_needed}\n"
        f"Deployment zones: {n_clusters}\n"
        "Describe the optimal adjuster deployment."
    )
    narrative = call_llm_simple(SYSTEM, prompt, max_tokens=150, agent="resource")

    out = {
        "adjusters_needed":    adjusters_needed,
        "deployment_zones":    n_clusters,
        "adjusters_per_zone":  round(adjusters_needed / n_clusters, 1),
        "red_twins_clustered": int(len(red_twins)),
        "zone_details":        zone_details,
        "deployment_strategy": "Stage adjusters at zone centres T-24h before landfall",
        "narrative":           narrative,
    }

    has_narrative = not narrative.startswith("[LLM unavailable")
    confidence = compute_confidence(
        data_coverage=1.0 if kmeans_used else 0.5,  # random fallback is far less trustworthy
        has_narrative=has_narrative,
        within_expected_range=adjusters_needed > 0 and n_clusters > 0,
    )
    return attach(
        out,
        confidence=confidence,
        why=(
            f"{adjusters_needed} adjusters across {n_clusters} K-Means zones, sized at "
            f"~120 claims/adjuster against {expected_claims:.0f} expected red-zone claims."
        ),
        inputs_used=["risk_color", "claim_probability", "lat", "lng", "area"],
        evidence={
            "clustering": "kmeans" if kmeans_used else "random_fallback",
            "claims_per_adjuster": 120,
            "expected_red_claims": round(expected_claims, 1),
        },
    )
