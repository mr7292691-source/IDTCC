"""Real-time data fetchers — OSM Overpass (neighborhoods + shelters) and GDACS (cyclones).

All functions cache results for CACHE_TTL_SECONDS (30 min) so repeated calls within
a simulation session are instant.  Every fetch fails gracefully: callers receive an
empty list / None and fall back to the static city catalogue.
"""
from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Optional, Tuple

import requests

# ── API endpoints ─────────────────────────────────────────────────────────────
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
GDACS_TC_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/GDACS"

CACHE_TTL_SECONDS = 1_800  # 30 minutes

# Simple time-keyed in-process cache: {key: (data, epoch_ts)}
_CACHE: Dict[str, Tuple[Any, float]] = {}


# ── Cache helper ──────────────────────────────────────────────────────────────

def _cached(key: str, fetch_fn, *args, **kwargs) -> Any:
    """Return cached value if fresh; otherwise call fetch_fn and cache the result.
    On network failure, returns stale data if available, else None."""
    now = time.time()
    if key in _CACHE:
        data, ts = _CACHE[key]
        if now - ts < CACHE_TTL_SECONDS:
            return data
    try:
        data = fetch_fn(*args, **kwargs)
        _CACHE[key] = (data, now)
        return data
    except Exception:
        # Serve stale rather than crashing the pipeline
        if key in _CACHE:
            return _CACHE[key][0]
        return None


def invalidate_cache(prefix: str | None = None) -> None:
    """Remove all (or prefix-matching) cache entries — useful for testing."""
    keys = list(_CACHE.keys())
    for k in keys:
        if prefix is None or k.startswith(prefix):
            del _CACHE[k]


# ── OSM: real neighborhood names ──────────────────────────────────────────────

def fetch_osm_neighborhoods(
    bbox: Tuple[float, float, float, float],
    max_results: int = 25,
) -> List[str]:
    """Return real suburb / neighbourhood names from OpenStreetMap for a bounding box.

    bbox: (lat_min, lng_min, lat_max, lng_max)
    Returns at most *max_results* unique English names.
    """
    lat_min, lng_min, lat_max, lng_max = bbox

    def _fetch() -> List[str]:
        query = f"""
[out:json][timeout:28];
(
  node["place"~"suburb|neighbourhood|quarter|village"]["name"]
      ({lat_min},{lng_min},{lat_max},{lng_max});
  way["place"~"suburb|neighbourhood|quarter"]["name"]
     ({lat_min},{lng_min},{lat_max},{lng_max});
  relation["admin_level"~"8|9|10"]["name"]
          ({lat_min},{lng_min},{lat_max},{lng_max});
);
out body;
"""
        resp = requests.post(
            OVERPASS_URL,
            data={"data": query},
            timeout=35,
            headers={"User-Agent": "IDTCC-Hackathon/2.0"},
        )
        resp.raise_for_status()
        elements = resp.json().get("elements", [])

        names: List[str] = []
        seen: set = set()
        for el in elements:
            tags = el.get("tags", {})
            name = tags.get("name:en") or tags.get("name")
            if name and len(name) > 2 and name not in seen:
                seen.add(name)
                names.append(name)
            if len(names) >= max_results:
                break
        return names

    return _cached(f"osm_nh_{bbox}", _fetch) or []


# ── OSM: real hospitals / schools / stadiums as safe spaces ───────────────────

def fetch_osm_safe_spaces(
    bbox: Tuple[float, float, float, float],
    max_results: int = 8,
) -> List[Dict]:
    """Return real evacuation-capable facilities from OSM (hospitals, schools, stadiums).

    Returns list of dicts compatible with the safe_spaces schema:
      {id, name, lat, lng, capacity, type}
    """
    lat_min, lng_min, lat_max, lng_max = bbox

    # Capacity heuristic per amenity type
    CAPACITY: Dict[str, int] = {
        "hospital": 2000,
        "government": 1500,
        "school": 800,
        "college": 1200,
        "community_centre": 600,
        "stadium": 5000,
        "sports_centre": 2500,
        "civic": 1000,
        "shelter": 400,
    }

    def _fetch() -> List[Dict]:
        query = f"""
[out:json][timeout:28];
(
  node["amenity"~"hospital|school|college|community_centre"]["name"]
      ({lat_min},{lng_min},{lat_max},{lng_max});
  way["amenity"~"hospital|school|college|community_centre"]["name"]
     ({lat_min},{lng_min},{lat_max},{lng_max});
  node["leisure"~"stadium|sports_centre"]["name"]
      ({lat_min},{lng_min},{lat_max},{lng_max});
  way["leisure"~"stadium|sports_centre"]["name"]
     ({lat_min},{lng_min},{lat_max},{lng_max});
  node["building"~"stadium|civic|government"]["name"]
      ({lat_min},{lng_min},{lat_max},{lng_max});
  way["building"~"stadium|civic|government"]["name"]
     ({lat_min},{lng_min},{lat_max},{lng_max});
);
out center;
"""
        resp = requests.post(
            OVERPASS_URL,
            data={"data": query},
            timeout=35,
            headers={"User-Agent": "IDTCC-Hackathon/2.0"},
        )
        resp.raise_for_status()
        elements = resp.json().get("elements", [])

        spaces: List[Dict] = []
        seen_names: set = set()

        for i, el in enumerate(elements):
            tags = el.get("tags", {})
            name = tags.get("name:en") or tags.get("name")
            if not name or name in seen_names:
                continue
            seen_names.add(name)

            # Coordinates: node → direct; way → center
            if el["type"] == "node":
                lat, lng = el.get("lat"), el.get("lon")
            else:
                center = el.get("center", {})
                lat, lng = center.get("lat"), center.get("lon")

            if lat is None or lng is None:
                continue

            amenity = (
                tags.get("amenity")
                or tags.get("leisure")
                or tags.get("building", "shelter")
            )
            capacity = CAPACITY.get(amenity, 500)

            spaces.append({
                "id": f"SS-{len(spaces)+1:02d}",
                "name": name,
                "lat": float(lat),
                "lng": float(lng),
                "capacity": capacity,
                "type": amenity,
            })

            if len(spaces) >= max_results:
                break

        return spaces

    return _cached(f"osm_ss_{bbox}", _fetch) or []


# ── GDACS: active tropical cyclone near a location ────────────────────────────

def fetch_active_cyclone_gdacs(
    center_lat: float,
    center_lng: float,
    search_radius_km: float = 1500,
) -> Optional[Dict]:
    """Check GDACS for any active tropical cyclone within *search_radius_km* of center.

    Returns a minimal dict:
      {name, gdacs_id, alert_level, max_wind_kmh, lat, lng, dist_km}
    or None if no active storm is found.
    """
    cache_key = f"gdacs_tc_{center_lat:.2f}_{center_lng:.2f}"

    def _fetch() -> Optional[Dict]:
        resp = requests.get(
            GDACS_TC_URL,
            params={"eventlist": "TC", "alertlevel": "Green,Orange,Red"},
            timeout=20,
            headers={"User-Agent": "IDTCC-Hackathon/2.0"},
        )
        resp.raise_for_status()
        features = resp.json().get("features", [])

        best: Optional[Dict] = None
        best_dist = float("inf")

        for feat in features:
            props = feat.get("properties", {})
            geom = feat.get("geometry", {})
            if not geom or geom.get("type") != "Point":
                continue

            tc_lng, tc_lat = geom["coordinates"][:2]
            dist = _haversine(center_lat, center_lng, tc_lat, tc_lng)

            if dist < search_radius_km and dist < best_dist:
                best_dist = dist
                # maxwind in GDACS is in knots → convert to km/h
                wind_kt = float(props.get("maxwind", 0) or 0)
                best = {
                    "name": props.get("eventname") or props.get("name") or "UNNAMED",
                    "gdacs_id": props.get("eventid"),
                    "alert_level": props.get("alertlevel", "Orange"),
                    "max_wind_kmh": round(wind_kt * 1.852, 1),
                    "lat": tc_lat,
                    "lng": tc_lng,
                    "dist_km": round(dist, 1),
                }

        return best

    return _cached(cache_key, _fetch)


def build_cyclone_track_from_gdacs(
    cyclone: Dict,
    city_lat: float,
    city_lng: float,
    n_points: int = 6,
) -> List[Dict]:
    """Interpolate a track from the GDACS storm position toward the city center."""
    tc_lat, tc_lng = cyclone["lat"], cyclone["lng"]
    max_wind = cyclone["max_wind_kmh"] or 120.0

    lats = [tc_lat + (city_lat - tc_lat) * i / (n_points - 1) for i in range(n_points)]
    lngs = [tc_lng + (city_lng - tc_lng) * i / (n_points - 1) for i in range(n_points)]

    # Wind peaks at ~70% of the track then decays
    peak = int(n_points * 0.6)
    winds = []
    for i in range(n_points):
        if i <= peak:
            w = max_wind * (0.6 + 0.4 * i / peak)
        else:
            w = max_wind * (1.0 - 0.5 * (i - peak) / (n_points - peak))
        winds.append(round(w, 0))

    return [{"lat": lats[i], "lng": lngs[i], "wind_kmh": winds[i]} for i in range(n_points)]


# ── Internal math ─────────────────────────────────────────────────────────────

def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6_371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(max(0.0, min(1.0, a))))
