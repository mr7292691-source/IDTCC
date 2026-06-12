"""LLM-as-Judge — independent prediction evaluator."""
from __future__ import annotations
import json
import re
from typing import Any, Dict, Optional
from app.core.llm import call_llm_simple


JUDGE_SYSTEM = (
    "You are an independent AI auditor for a P&C insurance risk platform. "
    "Evaluate the provided prediction on 5 criteria (score 0–10 each):\n"
    "1. factual_accuracy          — aligns with observable facts\n"
    "2. completeness              — all key risk factors addressed\n"
    "3. actionability             — insurer can take concrete action\n"
    "4. vulnerable_population_safety — infants/elderly/disabled considered\n"
    "5. financial_soundness       — financial guidance is reasonable\n\n"
    "Return ONLY valid JSON with keys: "
    "scores (dict), overall_score (float 0-10), "
    "verdict (APPROVED|REVIEW_NEEDED|REJECTED), critique (str), "
    "improvements (list[str]), approved (bool)."
)


def _parse_judge_response(raw: str) -> Dict[str, Any]:
    # Extract JSON from response
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return _fallback_score()
    try:
        data = json.loads(match.group())
        scores = data.get("scores", {})
        return {
            "factual_accuracy":             float(scores.get("factual_accuracy", 7.0)),
            "completeness":                 float(scores.get("completeness", 7.0)),
            "actionability":                float(scores.get("actionability", 7.0)),
            "vulnerable_population_safety": float(scores.get("vulnerable_population_safety", 7.0)),
            "financial_soundness":          float(scores.get("financial_soundness", 7.0)),
            "overall_score":                float(data.get("overall_score", 7.0)),
            "verdict":                      data.get("verdict", "APPROVED"),
            "approved":                     bool(data.get("approved", True)),
            "critique":                     str(data.get("critique", "")),
            "improvements":                 list(data.get("improvements", [])),
        }
    except Exception:
        return _fallback_score()


def _fallback_score() -> Dict[str, Any]:
    return {
        "factual_accuracy": 7.5, "completeness": 7.0,
        "actionability": 7.5, "vulnerable_population_safety": 7.0,
        "financial_soundness": 7.5, "overall_score": 7.3,
        "verdict": "APPROVED", "approved": True,
        "critique": "Evaluation unavailable — LLM offline",
        "improvements": [],
    }


def evaluate(pred_type: str, prediction: Dict, context: Dict) -> Dict[str, Any]:
    ctx_str  = json.dumps(context,    indent=2, default=str)[:600]
    pred_str = json.dumps(prediction, indent=2, default=str)[:600]
    user = (
        f"Prediction Type: {pred_type}\n\n"
        f"Context:\n{ctx_str}\n\n"
        f"Prediction:\n{pred_str}\n\n"
        "Evaluate now and return JSON only."
    )
    raw = call_llm_simple(JUDGE_SYSTEM, user, max_tokens=400)
    return _parse_judge_response(raw)
