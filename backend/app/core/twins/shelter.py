"""Shelter & hospital twin builders.

Wraps the existing `build_safe_spaces()` (core/simulation.py) and enriches each
shelter with the capacity / accessibility / medical attributes the Shelter
Allocation and Evacuation agents reason over.
"""
from __future__ import annotations

from typing import List

import numpy as np

from app.core.simulation import build_safe_spaces


def build_shelter_twins(location_code: str, seed: int = 42) -> List[dict]:
    """Return shelter twins for a city: capacity, accessibility, medical flags."""
    rng = np.random.default_rng(seed)
    spaces = build_safe_spaces(location_code)
    twins: List[dict] = []
    for i, s in enumerate(spaces):
        cap = int(s.get("capacity", 1000))
        twins.append({
            "shelter_id":          s["id"],
            "name":                s["name"],
            "lat":                 s["lat"],
            "lng":                 s["lng"],
            "capacity":            cap,
            "current_occupancy":   0,
            "wheelchair_accessible": bool(rng.random() < 0.7),
            "medical_capable":     bool(rng.random() < 0.5),
            "has_generator":       bool(rng.random() < 0.6),
            "resources":           s.get("resources", {}),
        })
    return twins


def build_hospital_twins(shelters: List[dict], seed: int = 7) -> List[dict]:
    """Derive a small set of hospital twins co-located with medical shelters.

    Placeholder until a real OSM hospital connector lands — uses the
    medical-capable shelters as anchor points so the geography stays plausible.
    """
    rng = np.random.default_rng(seed)
    hospitals: List[dict] = []
    medical = [s for s in shelters if s.get("medical_capable")] or shelters
    for i, s in enumerate(medical):
        hospitals.append({
            "hospital_id":   f"HOSP-{i + 1:02d}",
            "name":          f"{s['name'].split(' ')[0]} General Hospital",
            "lat":           s["lat"] + float(rng.normal(0, 0.004)),
            "lng":           s["lng"] + float(rng.normal(0, 0.004)),
            "beds":          int(rng.integers(80, 600)),
            "icu_beds":      int(rng.integers(8, 60)),
            "has_dialysis":  bool(rng.random() < 0.6),
            "has_oxygen":    True,
        })
    return hospitals
