"""Shared geospatial helpers — vectorised haversine + nearest-facility search.

Extracted so the new LifeShield safety agents (shelter allocation, evacuation,
rescue) and the existing simulation engine share one well-tested distance core
instead of each re-deriving the haversine formula.
"""
from __future__ import annotations

from typing import List, Sequence, Tuple

import numpy as np

EARTH_RADIUS_KM = 6_371.0


def haversine_km(lat1, lng1, lat2, lng2) -> np.ndarray:
    """Great-circle distance in km. All args broadcast like numpy arrays."""
    lat1 = np.radians(np.asarray(lat1, dtype=float))
    lng1 = np.radians(np.asarray(lng1, dtype=float))
    lat2 = np.radians(np.asarray(lat2, dtype=float))
    lng2 = np.radians(np.asarray(lng2, dtype=float))
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlng / 2) ** 2
    return EARTH_RADIUS_KM * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def nearest_facility(
    lats: Sequence[float],
    lngs: Sequence[float],
    facilities: List[dict],
) -> Tuple[np.ndarray, np.ndarray]:
    """For each point return (index_of_nearest_facility, distance_km).

    `facilities` is a list of dicts each with `lat` / `lng`. Returns two arrays
    aligned with the input points. Empty facility list → (-1, inf) for every
    point so callers can branch without an IndexError.
    """
    pts_lat = np.asarray(lats, dtype=float)
    pts_lng = np.asarray(lngs, dtype=float)
    n = len(pts_lat)
    if not facilities:
        return np.full(n, -1, dtype=int), np.full(n, np.inf)

    f_lat = np.array([f["lat"] for f in facilities], dtype=float)
    f_lng = np.array([f["lng"] for f in facilities], dtype=float)

    # (n_points, n_facilities) distance matrix via broadcasting.
    dmat = haversine_km(
        pts_lat[:, None], pts_lng[:, None], f_lat[None, :], f_lng[None, :]
    )
    nearest_idx = np.argmin(dmat, axis=1)
    nearest_dist = dmat[np.arange(n), nearest_idx]
    return nearest_idx.astype(int), nearest_dist
