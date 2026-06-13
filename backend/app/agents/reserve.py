"""Agent 5 — Reserve Calculation."""
from __future__ import annotations
from typing import Any, Dict
import pandas as pd
from app.core.llm import call_llm_simple
from app.core.agent_base import instrument, attach, compute_confidence


SYSTEM = (
    "You are a Chief Actuarial Officer. State the reserve recommendation in 2 sentences. "
    "Use ₹ for currency. Include the adequacy ratio."
)


@instrument("reserve")
def run(df: pd.DataFrame, claims_output: Dict[str, Any]) -> Dict[str, Any]:
    expected_loss = claims_output.get("expected_total_loss_crore", 0.0)

    # IBNR: 18% of expected loss (standard P&C cat reserve loading)
    ibnr           = round(expected_loss * 0.18, 2)
    # Catastrophe buffer: 25%
    cat_buffer     = round(expected_loss * 0.25, 2)
    total_reserve  = round(expected_loss + ibnr + cat_buffer, 2)
    # Adequacy ratio: reserve / expected
    adequacy       = round(total_reserve / expected_loss, 3) if expected_loss > 0 else 1.0

    # Sensitivity scenarios (±30% wind)
    scenarios = {
        "base":      total_reserve,
        "mild_(-30% wind)": round(total_reserve * 0.60, 2),
        "severe_(+30% wind)": round(total_reserve * 1.45, 2),
    }

    prompt = (
        f"Expected loss: ₹{expected_loss:.1f} Crore\n"
        f"IBNR (18%): ₹{ibnr:.1f} Crore\n"
        f"Cat buffer (25%): ₹{cat_buffer:.1f} Crore\n"
        f"Total reserve: ₹{total_reserve:.1f} Crore\n"
        f"Adequacy ratio: {adequacy:.3f}\n"
        "State the reserve recommendation."
    )
    narrative = call_llm_simple(SYSTEM, prompt, max_tokens=150, agent="reserve")

    out = {
        "base_reserve_crore":               expected_loss,
        "ibnr_crore":                       ibnr,
        "cat_buffer_crore":                 cat_buffer,
        "total_recommended_reserve_crore":  total_reserve,
        "reserve_adequacy_ratio":           adequacy,
        "scenarios":                        scenarios,
        "narrative":                        narrative,
    }

    has_narrative = not narrative.startswith("[LLM unavailable")
    # If upstream claims produced no expected loss, reserve is undefined → low confidence.
    has_input = expected_loss > 0
    confidence = compute_confidence(
        data_coverage=1.0 if has_input else 0.3,
        has_narrative=has_narrative,
        within_expected_range=total_reserve >= expected_loss,
    )
    return attach(
        out,
        confidence=confidence,
        why=(
            f"Total reserve ₹{total_reserve:.1f}Cr = expected loss ₹{expected_loss:.1f}Cr "
            f"+ 18% IBNR + 25% catastrophe buffer (adequacy ratio {adequacy:.2f})."
        ),
        inputs_used=["claims_output.expected_total_loss_crore"],
        evidence={
            "ibnr_loading_pct": 18,
            "cat_buffer_pct": 25,
            "adequacy_ratio": adequacy,
            "sensitivity_scenarios": scenarios,
        },
    )
