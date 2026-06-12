"""Twin generation and cyclone simulation engine — adapted from IDTCC notebook."""
from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from faker import Faker

from app.core.locations import get_location

fake = Faker("en_IN")
rng = np.random.default_rng(42)

CONSTRUCTION_TYPES   = ["brick_mortar", "concrete_frame", "load_bearing_masonry", "wood_frame", "steel_frame"]
CONSTRUCTION_WEIGHTS = [0.40, 0.30, 0.15, 0.10, 0.05]
ROOF_TYPES           = ["terracotta_tile", "rcc_slab", "asbestos_sheet", "metal_sheet", "thatched"]
ROOF_WEIGHTS         = [0.35, 0.30, 0.15, 0.12, 0.08]

FLOOD_ZONE_MAP   = {"Zone_A": 0, "Zone_B": 1, "Zone_C": 2}
CONSTRUCTION_MAP = {"brick_mortar": 0, "concrete_frame": 1, "load_bearing_masonry": 2, "wood_frame": 3, "steel_frame": 4}

ROAD_NAMES = [
    "Main Road", "Cross Street", "Bazaar Road", "Tank Road",
    "Temple Street", "Gandhi Road", "Nehru Street", "Anna Salai",
]


def _flood_zone_for_area(area: str, loc: dict) -> str:
    if area in loc.get("flood_zones_high", []):
        return "Zone_A"
    if area in loc.get("flood_zones_medium", []):
        return "Zone_B"
    return "Zone_C"


def _compute_vulnerability(row: pd.Series) -> float:
    s = 0.0
    s += max(0.0, (2.0 - row["floor_elevation_m"]) / 2.0) * 0.30
    s += max(0.0, (3.0 - row["proximity_water_km"]) / 3.0) * 0.20
    age = 2025 - row["year_built"]
    s += min(age / 50.0, 1.0) * 0.20
    constr_scores = {"brick_mortar": 0.7, "load_bearing_masonry": 0.8, "wood_frame": 0.9,
                     "concrete_frame": 0.4, "steel_frame": 0.2}
    s += constr_scores.get(row["construction_type"], 0.5) * 0.20
    zone_scores = {"Zone_A": 1.0, "Zone_B": 0.6, "Zone_C": 0.3}
    s += zone_scores.get(row["flood_zone"], 0.5) * 0.10
    return round(min(max(s, 0.0), 1.0), 4)


def generate_twins(location_code: str, n: int = 50_000, seed: int = 42) -> pd.DataFrame:
    loc = get_location(location_code)
    lat_min, lng_min, lat_max, lng_max = loc["bbox"]
    areas = loc["areas"]

    np.random.seed(seed)
    random.seed(seed)

    n_areas = len(areas)
    area_idx = np.random.randint(0, n_areas, size=n)
    area_arr = [areas[i] for i in area_idx]

    lats = np.random.uniform(lat_min, lat_max, n)
    lngs = np.random.uniform(lng_min, lng_max, n)

    construction = np.random.choice(CONSTRUCTION_TYPES, size=n, p=CONSTRUCTION_WEIGHTS)
    roof         = np.random.choice(ROOF_TYPES, size=n, p=ROOF_WEIGHTS)
    flood_zones  = [_flood_zone_for_area(a, loc) for a in area_arr]

    year_built          = np.random.randint(1960, 2023, size=n)
    floors              = np.random.randint(1, 8, size=n)
    floor_elevation     = np.random.uniform(0.3, 5.0, size=n)
    proximity_water     = np.random.uniform(0.1, 8.0, size=n)
    sum_insured         = np.random.uniform(15, 250, size=n) * 100_000  # INR
    has_prior_claim     = np.random.random(n) < 0.18
    prior_claim_year    = np.where(has_prior_claim, np.random.randint(2015, 2025, size=n), 0)
    prior_fraud_flag    = np.random.random(n) < 0.02
    has_infants         = np.random.random(n) < 0.10
    has_elderly         = np.random.random(n) < 0.28
    has_disabled        = np.random.random(n) < 0.08

    twin_ids      = [f"T-{i+1:06d}" for i in range(n)]
    policyholders = [fake.name() for _ in range(n)]
    road_names    = [random.choice(ROAD_NAMES) for _ in range(n)]
    addresses     = [f"{np.random.randint(1,999)}, {road_names[i]}, {area_arr[i]}" for i in range(n)]
    policy_ids    = [f"POL-{np.random.randint(100000,999999)}" for _ in range(n)]

    df = pd.DataFrame({
        "twin_id":           twin_ids,
        "lat":               lats,
        "lng":               lngs,
        "address":           addresses,
        "area":              area_arr,
        "policyholder":      policyholders,
        "policy_id":         policy_ids,
        "construction_type": construction,
        "roof_type":         roof,
        "flood_zone":        flood_zones,
        "year_built":        year_built,
        "floors":            floors,
        "floor_elevation_m": floor_elevation,
        "proximity_water_km": proximity_water,
        "sum_insured_inr":   sum_insured,
        "has_prior_claim":   has_prior_claim,
        "prior_claim_year":  prior_claim_year,
        "prior_fraud_flag":  prior_fraud_flag,
        "has_infants":       has_infants,
        "has_elderly":       has_elderly,
        "has_disabled":      has_disabled,
    })

    df["vulnerability_index"] = df.apply(_compute_vulnerability, axis=1)
    df["social_vuln"] = (
        df["has_infants"].astype(int)  * 0.40 +
        df["has_elderly"].astype(int)  * 0.35 +
        df["has_disabled"].astype(int) * 0.25
    )
    return df


def run_cyclone_simulation(
    df: pd.DataFrame,
    cyclone: Dict[str, Any],
    use_ml_model: bool = False,
) -> pd.DataFrame:
    """Vectorised cyclone impact engine. Returns df with risk columns."""
    df_out = df.copy()
    lats = df_out["lat"].values
    lngs = df_out["lng"].values
    R = 6_371.0

    min_dists = np.full(len(df_out), np.inf)
    for wp in cyclone["track"]:
        dlat = np.radians(wp["lat"] - lats)
        dlng = np.radians(wp["lng"] - lngs)
        a = (np.sin(dlat / 2) ** 2
             + np.cos(np.radians(lats)) * np.cos(np.radians(wp["lat"]))
             * np.sin(dlng / 2) ** 2)
        d = R * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))
        min_dists = np.minimum(min_dists, d)

    df_out["dist_from_storm_km"] = min_dists

    max_wind  = cyclone.get("max_wind_kmh", 180)
    radius_km = cyclone.get("radius_km", 120)
    dist      = min_dists

    wind_factor = np.where(
        dist <= radius_km,
        1.0 - (dist / radius_km) * 0.4,
        np.maximum(0.0, 1.0 - (dist - radius_km) / 200.0) * 0.6,
    )
    wind_speed = wind_factor * max_wind

    zone_map = {"Zone_A": 1.0, "Zone_B": 0.65, "Zone_C": 0.35}
    zone_mult = df_out["flood_zone"].map(zone_map).fillna(0.65).values

    vuln = df_out["vulnerability_index"].values
    base_claim_prob = np.clip(
        wind_factor * 0.45 + vuln * 0.35 + zone_mult * 0.20, 0.0, 0.97
    )
    df_out["claim_probability"]  = np.round(base_claim_prob, 4)
    df_out["wind_speed_kmh"]     = np.round(wind_speed, 1)
    df_out["expected_loss_inr"]  = np.round(
        df_out["sum_insured_inr"] * base_claim_prob * 0.55, 0
    )

    def _color(p: float) -> str:
        if p >= 0.65: return "red"
        if p >= 0.40: return "orange"
        if p >= 0.20: return "yellow"
        return "green"

    df_out["risk_color"] = [_color(p) for p in base_claim_prob]
    return df_out


def assign_safe_spaces(df: pd.DataFrame, safe_spaces: List[Dict]) -> pd.DataFrame:
    """Assign each high-risk twin to nearest safe shelter (haversine)."""
    if not safe_spaces:
        df["ss_id"] = None
        df["ss_distance_km"] = None
        return df

    ss_lats = np.array([s["lat"] for s in safe_spaces])
    ss_lngs = np.array([s["lng"] for s in safe_spaces])
    R = 6_371.0

    critical = df["risk_color"].isin(["red", "orange"])
    df["ss_id"]          = None
    df["ss_distance_km"] = None

    for idx in df[critical].index:
        lat, lng = df.at[idx, "lat"], df.at[idx, "lng"]
        dlat = np.radians(ss_lats - lat)
        dlng = np.radians(ss_lngs - lng)
        a = (np.sin(dlat / 2) ** 2
             + math.cos(math.radians(lat)) * np.cos(np.radians(ss_lats))
             * np.sin(dlng / 2) ** 2)
        dists = R * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))
        nearest = int(np.argmin(dists))
        df.at[idx, "ss_id"]          = safe_spaces[nearest]["id"]
        df.at[idx, "ss_distance_km"] = round(float(dists[nearest]), 2)

    return df


def build_safe_spaces(location_code: str) -> List[Dict]:
    loc = get_location(location_code)
    base_resources = {
        "baby_formula_units": 250, "elderly_medicine_packs": 180,
        "water_liters": 8000, "food_rations": 700,
        "wheelchair_spaces": 30, "oxygen_cylinders": 20,
    }
    return [
        {**ss, "resources": dict(base_resources), "assigned_count": 0}
        for ss in loc.get("safe_spaces", [])
    ]
