"""Safety Agent 1 — Vulnerable Population.

Identifies citizens needing priority protection (elderly, children, disabled,
pregnant, medically dependent) and assigns each a deterministic vulnerability
score plus evacuation / rescue priority bands.
"""
from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd

from app.core.agent_base import attach, compute_confidence, instrument
from app.core.llm import call_llm_simple

SYSTEM = (
    "You are an emergency-management triage officer. In 2-3 sentences, summarise "
    "which population groups need priority protection and why. Be specific with "
    "numbers. Calm, authoritative tone."
)

# Deterministic, auditable weights — the LLM never produces these.
WEIGHTS = {
    "elderly":     0.25,   # age >= 65
    "child":       0.15,   # age <= 12
    "disability":  0.25,
    "pregnancy":   0.15,
    "medical_dep": 0.20,
}
# How much live spatial hazard exposure modulates the intrinsic frailty score.
HAZARD_BLEND = 0.30
BANDS = [(0.75, "critical"), (0.50, "high"), (0.25, "medium")]


def _band(score: float) -> str:
    for threshold, label in BANDS:
        if score >= threshold:
            return label
    return "low"


def vulnerability_series(df: pd.DataFrame) -> pd.Series:
    """Per-citizen vulnerability in [0, 1]. Pure function of the twin columns."""
    age = df["age"].astype(float)
    frailty = (
        (age >= 65).astype(float) * WEIGHTS["elderly"]
        + (age <= 12).astype(float) * WEIGHTS["child"]
        + df["disability_status"].astype(float) * WEIGHTS["disability"]
        + df["pregnancy_status"].astype(float) * WEIGHTS["pregnancy"]
        + df["medical_dependency"].notna().astype(float) * WEIGHTS["medical_dep"]
    ).clip(0, 1)
    hazard = df.get("hazard_exposure", pd.Series(0.0, index=df.index)).astype(float)
    score = ((1 - HAZARD_BLEND) * frailty + HAZARD_BLEND * hazard).clip(0, 1)
    return score.round(4)


def assign(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with vulnerability_score / evacuation_priority / rescue_priority."""
    out = df.copy()
    score = vulnerability_series(out)
    out["vulnerability_score"] = score
    out["evacuation_priority"] = score.map(_band)
    # Rescue priority is harsher for those who cannot self-evacuate.
    immobile = (~out["can_walk_unassisted"]) | (out["transport_access"] == "none")
    rescue = np.where(immobile, (score + 0.15).clip(0, 1), score)
    out["rescue_priority"] = pd.Series(rescue, index=out.index).map(_band)
    return out


@instrument("vulnerable")
def run(citizens: pd.DataFrame, hazard: Dict[str, Any] | None = None) -> Dict[str, Any]:
    scored = assign(citizens)
    bands = scored["evacuation_priority"]
    counts = {b: int((bands == b).sum()) for b in ("critical", "high", "medium", "low")}

    by_ward = (
        scored.groupby("ward")["vulnerability_score"].mean().round(3)
        .sort_values(ascending=False).head(15).to_dict()
    )
    top = scored.nlargest(20, "vulnerability_score")[
        ["citizen_id", "ward", "age", "medical_dependency",
         "disability_status", "vulnerability_score", "rescue_priority"]
    ].to_dict("records")

    prompt = (
        f"Total citizens: {len(scored):,}\n"
        f"Critical: {counts['critical']:,} | High: {counts['high']:,}\n"
        f"Elderly (65+): {(scored['age'] >= 65).sum():,} | "
        f"Children (<=12): {(scored['age'] <= 12).sum():,} | "
        f"Disabled: {scored['disability_status'].sum():,} | "
        f"Medically dependent: {scored['medical_dependency'].notna().sum():,}\n"
        "Summarise the priority protection picture."
    )
    narrative = call_llm_simple(SYSTEM, prompt, max_tokens=180, agent="vulnerable")

    out = {
        "total_citizens": int(len(scored)),
        "critical": counts["critical"], "high": counts["high"],
        "medium": counts["medium"], "low": counts["low"],
        "by_ward": by_ward,
        "top_vulnerable": top,
        "narrative": narrative,
    }
    return attach(
        out,
        confidence=compute_confidence(
            data_coverage=1.0,
            has_narrative=not narrative.startswith("[LLM unavailable"),
            within_expected_range=len(scored) > 0,
        ),
        why=(
            f"{counts['critical']:,} of {len(scored):,} citizens scored CRITICAL on a "
            f"weighted frailty model (age/disability/pregnancy/medical dependency) "
            f"blended with live hazard exposure."
        ),
        inputs_used=["age", "disability_status", "pregnancy_status",
                     "medical_dependency", "hazard_exposure", "can_walk_unassisted"],
        evidence={"weights": WEIGHTS, "hazard_blend": HAZARD_BLEND,
                  "band_thresholds": dict((l, t) for t, l in BANDS)},
    )
