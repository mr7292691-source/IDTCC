"""Location catalogue — disaster hotspots with pre-configured data."""

LOCATION_CATALOGUE = {
    "CHN": {
        "name": "Chennai, Tamil Nadu",
        "event": "Cyclone Michaung + Urban Flooding (Dec 2023)",
        "center": (13.0827, 80.2707),
        "bbox": (12.85, 80.07, 13.25, 80.32),
        "zoom": 11,
        "population": 7_088_000,
        "households": 1_854_000,
        "damage_cr": 8_600,
        "homes_damaged": 165_000,
        "deaths": 31,
        "areas": [
            "Adyar", "Velachery", "Tambaram", "Anna Nagar", "T. Nagar",
            "Mylapore", "Perambur", "Royapuram", "Besant Nagar", "Chromepet",
            "Sholinganallur", "Porur", "Ambattur", "Avadi", "Madhavaram",
            "Kodambakkam", "Nungambakkam", "Egmore", "Triplicane", "Washermanpet",
        ],
        "flood_zones_high": ["Adyar", "Velachery", "Perambur", "Royapuram", "Washermanpet", "Triplicane"],
        "flood_zones_medium": ["T. Nagar", "Kodambakkam", "Egmore", "Mylapore", "Chromepet"],
        "cyclone_track": [
            {"lat": 11.5, "lng": 82.0, "wind_kmh": 100},
            {"lat": 12.0, "lng": 81.5, "wind_kmh": 140},
            {"lat": 12.5, "lng": 81.0, "wind_kmh": 165},
            {"lat": 13.0, "lng": 80.5, "wind_kmh": 180},
            {"lat": 13.3, "lng": 80.2, "wind_kmh": 160},
            {"lat": 13.6, "lng": 80.0, "wind_kmh": 120},
        ],
        "safe_spaces": [
            {"id": "SS-01", "name": "Anna University Emergency Shelter", "lat": 13.0105, "lng": 80.2337, "capacity": 2000},
            {"id": "SS-02", "name": "IIT Madras Evacuation Hub",       "lat": 12.9916, "lng": 80.2336, "capacity": 3000},
            {"id": "SS-03", "name": "Tambaram Military Area Relief",   "lat": 12.9249, "lng": 80.1000, "capacity": 1500},
            {"id": "SS-04", "name": "Nehru Stadium Relief Centre",     "lat": 13.0700, "lng": 80.2700, "capacity": 4000},
            {"id": "SS-05", "name": "Adyar Flood Relief Camp",         "lat": 13.0069, "lng": 80.2568, "capacity": 1200},
            {"id": "SS-06", "name": "Velachery Community Hall",        "lat": 12.9810, "lng": 80.2209, "capacity": 800},
        ],
    },
    "MUM": {
        "name": "Mumbai, Maharashtra",
        "event": "Cyclone Tauktae + Coastal Flooding (May 2021)",
        "center": (19.0760, 72.8777),
        "bbox": (18.85, 72.75, 19.35, 72.98),
        "zoom": 11,
        "population": 12_478_000,
        "households": 3_100_000,
        "damage_cr": 4_200,
        "homes_damaged": 82_000,
        "deaths": 12,
        "areas": [
            "Dharavi", "Bandra", "Andheri", "Kurla", "Dadar",
            "Worli", "Colaba", "Chembur", "Ghatkopar", "Malad",
        ],
        "flood_zones_high": ["Dharavi", "Kurla", "Dadar", "Chembur"],
        "flood_zones_medium": ["Andheri", "Ghatkopar", "Malad"],
        "cyclone_track": [
            {"lat": 17.0, "lng": 73.5, "wind_kmh": 120},
            {"lat": 18.0, "lng": 73.0, "wind_kmh": 160},
            {"lat": 18.8, "lng": 72.9, "wind_kmh": 185},
            {"lat": 19.2, "lng": 72.8, "wind_kmh": 150},
            {"lat": 19.8, "lng": 72.6, "wind_kmh": 100},
        ],
        "safe_spaces": [
            {"id": "SS-01", "name": "BKC Emergency Hub",     "lat": 19.0660, "lng": 72.8680, "capacity": 5000},
            {"id": "SS-02", "name": "Andheri Sports Complex", "lat": 19.1136, "lng": 72.8697, "capacity": 3000},
        ],
    },
    "VIJ": {
        "name": "Vijayawada, Andhra Pradesh",
        "event": "Cyclone Michaung Landfall (Dec 2023)",
        "center": (16.5062, 80.6480),
        "bbox": (16.30, 80.45, 16.65, 80.85),
        "zoom": 11,
        "population": 1_048_000,
        "households": 280_000,
        "damage_cr": 2_800,
        "homes_damaged": 45_000,
        "deaths": 8,
        "areas": [
            "Benz Circle", "Governorpet", "Suryaraopet", "Patamata",
            "Moghalrajpuram", "Vijayawada Rural", "Krishnalanka", "Auto Nagar",
        ],
        "flood_zones_high": ["Krishnalanka", "Governorpet", "Suryaraopet"],
        "flood_zones_medium": ["Patamata", "Moghalrajpuram"],
        "cyclone_track": [
            {"lat": 14.0, "lng": 82.5, "wind_kmh": 100},
            {"lat": 15.0, "lng": 81.5, "wind_kmh": 150},
            {"lat": 15.8, "lng": 80.8, "wind_kmh": 175},
            {"lat": 16.3, "lng": 80.5, "wind_kmh": 155},
            {"lat": 16.8, "lng": 80.2, "wind_kmh": 100},
        ],
        "safe_spaces": [
            {"id": "SS-01", "name": "Indira Gandhi Stadium",   "lat": 16.5160, "lng": 80.6320, "capacity": 3000},
            {"id": "SS-02", "name": "Krishnalanka Relief Hub", "lat": 16.4850, "lng": 80.6100, "capacity": 2000},
        ],
    },
}


def get_location(code: str) -> dict:
    loc = LOCATION_CATALOGUE.get(code.upper())
    if not loc:
        raise ValueError(f"Unknown location code '{code}'. Valid: {list(LOCATION_CATALOGUE.keys())}")
    return loc
