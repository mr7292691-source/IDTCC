"""Citizen twin synthesis — explode property households into citizen twins.

The existing property engine (`core/simulation.py`) already models households
with `has_infants` / `has_elderly` / `has_disabled` flags and a `social_vuln`
score. We *derive* citizen twins from those property rows so the human layer is
guaranteed spatially and demographically coherent with the risk layer — a
50,000-property city yields ~180,000 citizen twins.

Privacy-first by construction: no real PII is generated here. Each citizen
carries an opaque ``pii_token`` (a deterministic pseudonym) instead of a name /
phone / address. Contact details, if ever attached, live only in the privacy
vault keyed by that token — analytic agents never see them.
"""
from __future__ import annotations

import hashlib
from typing import Optional

import numpy as np
import pandas as pd

# Indicative language mix by state code; falls back to English. Drives the
# personalised multilingual alert templates downstream.
LANG_BY_STATE = {
    "TN": ["ta", "en"], "AP": ["te", "en"], "TS": ["te", "en"],
    "KL": ["ml", "en"], "KA": ["kn", "en"], "MH": ["mr", "hi", "en"],
    "GJ": ["gu", "hi", "en"], "WB": ["bn", "hi", "en"], "OD": ["or", "hi", "en"],
    "MP": ["hi", "en"], "UP": ["hi", "en"], "BR": ["hi", "en"],
}

MEDICAL_DEPENDENCIES = ["dialysis", "oxygen", "insulin", "mobility_aid", "ventilator"]
CHRONIC_POOL = ["hypertension", "diabetes", "cardiac", "respiratory", "renal"]


def _pii_token(citizen_id: str, seed: int) -> str:
    """Deterministic opaque pseudonym — stands in for a privacy-vault key."""
    h = hashlib.sha256(f"{seed}:{citizen_id}".encode()).hexdigest()
    return f"tok_{h[:20]}"


def synthesize_citizens(
    property_df: pd.DataFrame,
    *,
    location_name: str = "",
    state_code: str = "",
    seed: int = 42,
    mean_household: float = 3.8,
) -> pd.DataFrame:
    """Explode each PropertyTwin into CitizenTwins.

    `property_df` is expected post-`run_cyclone_simulation` so `claim_probability`
    is present and used as each citizen's spatial `hazard_exposure`. Returns a
    DataFrame of citizen twins (one row per person).
    """
    rng = np.random.default_rng(seed)
    n_p = len(property_df)
    if n_p == 0:
        return pd.DataFrame()

    pdf = property_df.reset_index(drop=True)

    # Household size 1..7, Poisson-ish around the mean, clipped.
    hh_size = np.clip(rng.poisson(mean_household, size=n_p), 1, 7).astype(int)
    # If the property already carries a household_size, honour it.
    if "household_size" in pdf.columns:
        hh_size = np.clip(pdf["household_size"].fillna(0).astype(int).values, 1, 7)

    idx = np.repeat(np.arange(n_p), hh_size)          # property row per citizen
    member_ord = np.concatenate([np.arange(s) for s in hh_size])  # 0..size-1
    n = len(idx)

    base = pdf.iloc[idx].reset_index(drop=True)
    langs = LANG_BY_STATE.get(state_code, ["hi", "en"]) if state_code else ["en"]

    # ── Ages ────────────────────────────────────────────────────────────────
    # Base adult-skewed distribution, then inject the household's known minors /
    # elders so vulnerability flags stay consistent with the property layer.
    age = rng.integers(6, 80, size=n)
    has_inf = base.get("has_infants", pd.Series(False, index=base.index)).fillna(False).values
    has_eld = base.get("has_elderly", pd.Series(False, index=base.index)).fillna(False).values
    has_dis = base.get("has_disabled", pd.Series(False, index=base.index)).fillna(False).values

    first_member = member_ord == 0
    second_member = member_ord == 1
    age = np.where(second_member & has_inf, rng.integers(0, 5, size=n), age)
    age = np.where(first_member & has_eld, rng.integers(65, 92, size=n), age)

    gender = rng.choice(["M", "F", "O"], size=n, p=[0.49, 0.49, 0.02])

    # ── Health ──────────────────────────────────────────────────────────────
    disability_status = first_member & has_dis
    pregnancy_status = (
        (gender == "F") & (age >= 18) & (age <= 40) & (rng.random(n) < 0.05)
    )
    med_dep_mask = (disability_status | (age >= 70)) & (rng.random(n) < 0.35)
    medical_dependency = np.where(
        med_dep_mask, rng.choice(MEDICAL_DEPENDENCIES, size=n), None
    )
    chronic_mask = (age >= 45) & (rng.random(n) < 0.4)
    chronic = [
        [rng.choice(CHRONIC_POOL)] if chronic_mask[i] else [] for i in range(n)
    ]

    # ── Mobility ──────────────────────────────────────────────────────────────
    owns_vehicle = rng.random(n) < 0.32
    can_walk = ~(disability_status | (age >= 80) | (age <= 3))
    transport_access = np.where(
        owns_vehicle, "private",
        np.where(rng.random(n) < 0.6, "public", "none"),
    )

    # ── Identity / location ───────────────────────────────────────────────────
    citizen_ids = [f"CT-{i + 1:07d}" for i in range(n)]
    household_ids = base["twin_id"].values if "twin_id" in base.columns else idx.astype(str)
    # Small jitter so co-household members don't perfectly overlap on the map.
    lat = base["lat"].values + rng.normal(0, 0.0006, size=n)
    lng = base["lng"].values + rng.normal(0, 0.0006, size=n)

    preferred_language = rng.choice(langs, size=n)
    # Channel preference: everyone gets SMS; some add whatsapp / voice / email.
    channels = []
    for i in range(n):
        ch = ["sms"]
        if rng.random() < 0.55:
            ch.append("whatsapp")
        if disability_status[i] or age[i] >= 70:
            ch.append("voice")           # accessibility default
        if rng.random() < 0.25:
            ch.append("email")
        channels.append(ch)

    hazard_exposure = (
        base["claim_probability"].values
        if "claim_probability" in base.columns
        else np.zeros(n)
    )

    out = pd.DataFrame({
        "citizen_id":         citizen_ids,
        "pii_token":          [_pii_token(c, seed) for c in citizen_ids],
        "household_id":       household_ids,
        "property_twin_id":   household_ids,
        "member_ord":         member_ord,
        "age":                age.astype(int),
        "gender":             gender,
        "lat":                lat,
        "lng":                lng,
        "ward":               base.get("area", pd.Series("", index=base.index)).values,
        "district":           location_name,
        "state":              state_code,
        "flood_zone":         base.get("flood_zone", pd.Series("Zone_C", index=base.index)).values,
        "disability_status":  disability_status,
        "chronic_diseases":   chronic,
        "medical_dependency": medical_dependency,
        "pregnancy_status":   pregnancy_status,
        "owns_vehicle":       owns_vehicle,
        "can_walk_unassisted": can_walk,
        "transport_access":   transport_access,
        "preferred_language": preferred_language,
        "alert_channels":     channels,
        "hazard_exposure":    np.round(hazard_exposure, 4),
        # Emergency-intelligence columns are written by the safety agents.
        "vulnerability_score": 0.0,
        "evacuation_priority": "low",
        "rescue_priority":     "low",
        "assigned_shelter_id": None,
    })
    return out
