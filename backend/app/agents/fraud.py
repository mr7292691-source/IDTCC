"""Agent 4 — Fraud Detection (rule-based + FAISS embedding similarity)."""
from __future__ import annotations
from typing import Any, Dict, List
import numpy as np
import pandas as pd
from app.core.llm import call_llm_simple
from app.core.agent_base import instrument, attach, compute_confidence


SYSTEM = (
    "You are a fraud analytics specialist at a P&C insurer. "
    "Summarise the fraud risk in 2 sentences. Be specific."
)


def _build_feature_vector(row: pd.Series) -> np.ndarray:
    constr_enc = {"brick_mortar": 0, "concrete_frame": 1, "load_bearing_masonry": 2,
                  "wood_frame": 3, "steel_frame": 4}
    zone_enc   = {"Zone_A": 0, "Zone_B": 1, "Zone_C": 2}
    return np.array([
        row["vulnerability_index"],
        row["claim_probability"],
        row["sum_insured_inr"] / 2_500_000,
        float(row["has_prior_claim"]),
        (row["prior_claim_year"] - 2015) / 10.0 if row["prior_claim_year"] > 0 else 0.0,
        float(row["prior_fraud_flag"]),
        constr_enc.get(row["construction_type"], 2) / 4.0,
        zone_enc.get(row["flood_zone"], 1) / 2.0,
    ], dtype=np.float32)


@instrument("fraud")
def run(df: pd.DataFrame) -> Dict[str, Any]:
    # 1. Known fraud flags
    known = df[df["prior_fraud_flag"]].copy()
    known["fraud_reason"] = "Prior fraud flag on record"

    # 2. Suspicious: high claim prob + recent prior claim (no prior flag)
    suspicious = df[
        (~df["prior_fraud_flag"]) &
        (df["has_prior_claim"]) &
        (df["claim_probability"] >= 0.65) &
        (df["prior_claim_year"].fillna(0) >= 2021)
    ].copy()
    suspicious["fraud_reason"] = "High claim probability + recent prior claim"

    # 3. FAISS nearest-neighbour anomaly — requires faiss-cpu
    nn_flagged: List[str] = []
    faiss_used = False
    sample_size = 0
    try:
        import faiss
        sample = df.sample(min(5000, len(df)), random_state=42)
        sample_size = len(sample)
        vecs   = np.stack([_build_feature_vector(r) for _, r in sample.iterrows()])
        vecs  /= (np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-9)
        index  = faiss.IndexFlatL2(vecs.shape[1])
        index.add(vecs)
        D, _ = index.search(vecs, k=5)
        avg_dist   = D[:, 1:].mean(axis=1)
        threshold  = float(np.percentile(avg_dist, 95))
        outlier_mask = avg_dist > threshold
        nn_flagged = sample.iloc[outlier_mask]["twin_id"].tolist()
        faiss_used = True
    except Exception:
        pass  # faiss optional

    all_fraud_ids = set(known["twin_id"].tolist()) | set(suspicious["twin_id"].tolist()) | set(nn_flagged)
    total_fraud   = len(all_fraud_ids)

    # Top 10 suspicious — combine known + suspicious
    combined = pd.concat([known, suspicious]).drop_duplicates("twin_id")
    top10 = combined.nlargest(10, "claim_probability")[
        ["twin_id", "address", "claim_probability", "flood_zone", "fraud_reason"]
    ].to_dict("records")

    fraud_exposure = combined["expected_loss_inr"].sum() / 1e7

    prompt = (
        f"Total fraud-risk twins flagged: {total_fraud:,}\n"
        f"Known prior fraud flags: {len(known):,}\n"
        f"Suspicious (high risk + recent claim): {len(suspicious):,}\n"
        f"FAISS anomaly detections: {len(nn_flagged):,}\n"
        f"Estimated fraud exposure: ₹{fraud_exposure:.1f} Crore\n"
        "Summarise the fraud risk in 2 sentences."
    )
    narrative = call_llm_simple(SYSTEM, prompt, max_tokens=150, agent="fraud")

    out = {
        "total_fraud_risk_twins":         total_fraud,
        "known_fraud_flags":              int(len(known)),
        "suspicious_profiles":            int(len(suspicious)),
        "faiss_anomaly_count":            len(nn_flagged),
        "estimated_fraud_exposure_crore": round(fraud_exposure, 2),
        "top_suspicious":                 top10,
        "narrative":                      narrative,
    }

    has_narrative = not narrative.startswith("[LLM unavailable")
    # Coverage is high for rule-based flags (whole portfolio) but the FAISS layer
    # only samples; reflect that honestly in the confidence.
    coverage = 1.0 if not faiss_used else min(1.0, 0.7 + 0.3 * (sample_size / max(len(df), 1)))
    confidence = compute_confidence(
        data_coverage=coverage,
        has_narrative=has_narrative,
        within_expected_range=total_fraud <= len(df),
    )
    return attach(
        out,
        confidence=confidence,
        why=(
            f"{total_fraud:,} properties flagged: {len(known):,} prior-fraud records, "
            f"{len(suspicious):,} suspicious patterns, {len(nn_flagged):,} FAISS anomalies."
        ),
        inputs_used=["prior_fraud_flag", "has_prior_claim", "claim_probability",
                     "prior_claim_year", "vulnerability_index", "sum_insured_inr"],
        evidence={
            "faiss_enabled": faiss_used,
            "faiss_sample_size": sample_size,
            "anomaly_percentile_threshold": 95,
            "estimated_exposure_crore": round(fraud_exposure, 2),
        },
    )
