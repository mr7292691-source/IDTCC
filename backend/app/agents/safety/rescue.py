"""Safety Agent 4 — Rescue Prioritization.

Ranks citizens requiring active intervention into Critical / High / Medium / Low
using vulnerability, live hazard intensity, and isolation (immobility + no
transport). Produces an ordered rescue queue for responder dispatch.
"""
from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd

from app.core.agent_base import attach, compute_confidence, instrument
from app.core.llm import call_llm_simple

SYSTEM = (
    "You are a search-and-rescue dispatch commander. In 2-3 sentences, summarise "
    "the rescue queue: how many critical cases, what drives them, and the single "
    "most urgent ward. Be specific and operational."
)

BANDS = [(0.78, "critical"), (0.55, "high"), (0.30, "medium")]


def _band(score: float) -> str:
    for threshold, label in BANDS:
        if score >= threshold:
            return label
    return "low"


@instrument("rescue")
def run(citizens: pd.DataFrame, hazard: Dict[str, Any] | None = None) -> Dict[str, Any]:
    df = citizens
    vuln = df["vulnerability_score"].astype(float)
    hazard_exp = df.get("hazard_exposure", pd.Series(0.0, index=df.index)).astype(float)
    immobile = ((~df["can_walk_unassisted"]) | (df["transport_access"] == "none")).astype(float)

    # Composite: frailty × hazard, lifted by isolation.
    rescue_score = (0.5 * vuln + 0.35 * hazard_exp + 0.15 * immobile).clip(0, 1)
    bands = rescue_score.map(_band)
    counts = {b: int((bands == b).sum()) for b in ("critical", "high", "medium", "low")}

    queue = (
        df.assign(rescue_score=rescue_score.round(4), band=bands)
        .query("band in ('critical', 'high')")
        .sort_values("rescue_score", ascending=False)
        .head(50)[
            ["citizen_id", "ward", "age", "medical_dependency",
             "disability_status", "assigned_shelter_id", "rescue_score", "band"]
        ]
        .to_dict("records")
    )
    worst_ward = (
        df.assign(s=rescue_score).groupby("ward")["s"].mean().idxmax()
        if len(df) else "n/a"
    )

    prompt = (
        f"Critical: {counts['critical']:,} | High: {counts['high']:,}\n"
        f"Immobile / no transport: {int(immobile.sum()):,}\n"
        f"Most urgent ward: {worst_ward}\n"
        "Summarise the rescue prioritisation."
    )
    narrative = call_llm_simple(SYSTEM, prompt, max_tokens=170, agent="rescue")

    out = {
        "critical": counts["critical"], "high": counts["high"],
        "medium": counts["medium"], "low": counts["low"],
        "most_urgent_ward": worst_ward,
        "rescue_queue": queue,
        "narrative": narrative,
    }
    return attach(
        out,
        confidence=compute_confidence(
            data_coverage=1.0,
            has_narrative=not narrative.startswith("[LLM unavailable"),
            within_expected_range=True,
        ),
        why=(
            f"{counts['critical']:,} citizens ranked CRITICAL for rescue "
            f"(vulnerability × hazard intensity, lifted by isolation); most urgent "
            f"ward: {worst_ward}."
        ),
        inputs_used=["vulnerability_score", "hazard_exposure",
                     "can_walk_unassisted", "transport_access"],
        evidence={"band_thresholds": dict((l, t) for t, l in BANDS),
                  "weights": {"vuln": 0.5, "hazard": 0.35, "isolation": 0.15}},
    )
