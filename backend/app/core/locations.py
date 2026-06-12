"""Location service — 35 disaster-prone Indian cities across 14 states.

Each entry ships curated static baseline data (areas, flood zones, cyclone track,
safe spaces).  At runtime, `get_location()` enriches the record with:

  1. Real neighbourhood names from OSM Overpass API (30-min TTL cache)
  2. Real hospitals / schools / stadiums as evacuation safe spaces (OSM)
  3. Active tropical cyclone track from GDACS if a storm is currently
     within 1,500 km of the city

Callers see a plain dict with the same keys as before — the simulation engine
and all agent nodes require zero changes.
"""
from __future__ import annotations

from typing import Dict, List, Optional

# ── Static city catalogue ─────────────────────────────────────────────────────
# bbox: (lat_min, lng_min, lat_max, lng_max)
# cyclone_track: list of {lat, lng, wind_kmh} — historical / typical approach
# safe_spaces: list of {id, name, lat, lng, capacity}  ← OSM enriches at runtime

CITY_CATALOGUE: Dict[str, dict] = {

    # ══════════════════════════════════════════════════════════════════════════
    # TAMIL NADU
    # ══════════════════════════════════════════════════════════════════════════
    "CHN": {
        "name": "Chennai", "state": "Tamil Nadu", "state_code": "TN",
        "event": "Cyclone Michaung + Urban Flooding (Dec 2023)",
        "disaster_type": "cyclone",
        "center": (13.0827, 80.2707),
        "bbox": (12.85, 80.07, 13.25, 80.32),
        "zoom": 11,
        "population": 7_088_000, "households": 1_854_000,
        "damage_cr": 8_600, "homes_damaged": 165_000, "deaths": 31,
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
            {"id": "SS-02", "name": "IIT Madras Evacuation Hub",         "lat": 12.9916, "lng": 80.2336, "capacity": 3000},
            {"id": "SS-03", "name": "Tambaram Military Area Relief",     "lat": 12.9249, "lng": 80.1000, "capacity": 1500},
            {"id": "SS-04", "name": "Nehru Stadium Relief Centre",       "lat": 13.0700, "lng": 80.2700, "capacity": 4000},
        ],
    },

    "MDU": {
        "name": "Madurai", "state": "Tamil Nadu", "state_code": "TN",
        "event": "Vaigai River Flooding (Nov 2021)",
        "disaster_type": "flood",
        "center": (9.9252, 78.1198),
        "bbox": (9.84, 78.04, 10.02, 78.22),
        "zoom": 12,
        "population": 1_468_000, "households": 378_000,
        "damage_cr": 1_200, "homes_damaged": 28_000, "deaths": 9,
        "areas": [
            "Goripalayam", "Koodal Nagar", "Anna Nagar", "TVS Nagar", "Vilangudi",
            "Thirunagar", "Teppakulam", "Tallakulam", "Simmakkal", "K.K. Nagar",
            "Arappalayam", "Subramaniyapuram", "Sellur", "Nagamalai Pudukottai", "Surveyor Colony",
        ],
        "flood_zones_high": ["Goripalayam", "Teppakulam", "Tallakulam"],
        "flood_zones_medium": ["Anna Nagar", "TVS Nagar", "Thirunagar"],
        "cyclone_track": [
            {"lat": 8.0, "lng": 80.5, "wind_kmh": 90},
            {"lat": 8.8, "lng": 79.5, "wind_kmh": 120},
            {"lat": 9.4, "lng": 78.8, "wind_kmh": 145},
            {"lat": 9.9, "lng": 78.2, "wind_kmh": 160},
            {"lat": 10.3, "lng": 77.8, "wind_kmh": 130},
        ],
        "safe_spaces": [
            {"id": "SS-01", "name": "Madurai Medical College",    "lat": 9.9195, "lng": 78.1175, "capacity": 2000},
            {"id": "SS-02", "name": "Tamukkam Grounds Shelter",   "lat": 9.9440, "lng": 78.1276, "capacity": 3000},
        ],
    },

    "TRY": {
        "name": "Tiruchirappalli", "state": "Tamil Nadu", "state_code": "TN",
        "event": "Cauvery River Flooding (Nov 2023)",
        "disaster_type": "flood",
        "center": (10.7905, 78.7047),
        "bbox": (10.72, 78.63, 10.87, 78.78),
        "zoom": 12,
        "population": 916_000, "households": 235_000,
        "damage_cr": 950, "homes_damaged": 18_000, "deaths": 6,
        "areas": [
            "Srirangam", "Thillai Nagar", "K.K. Nagar", "Ariyamangalam", "Puthur",
            "Golden Rock", "Woraiyur", "Kattur", "Palakkarai", "Manachanallur",
            "Aranarai", "Ponmalaipatti", "Crawford",
        ],
        "flood_zones_high": ["Srirangam", "Woraiyur", "Crawford"],
        "flood_zones_medium": ["Thillai Nagar", "Puthur", "Palakkarai"],
        "cyclone_track": [
            {"lat": 8.5, "lng": 80.5, "wind_kmh": 85},
            {"lat": 9.5, "lng": 79.8, "wind_kmh": 120},
            {"lat": 10.3, "lng": 79.0, "wind_kmh": 140},
            {"lat": 10.8, "lng": 78.7, "wind_kmh": 155},
            {"lat": 11.2, "lng": 78.3, "wind_kmh": 110},
        ],
        "safe_spaces": [
            {"id": "SS-01", "name": "NIT Trichy Evacuation Hub",   "lat": 10.7600, "lng": 78.8100, "capacity": 2500},
            {"id": "SS-02", "name": "Srirangam Temple Relief Camp","lat": 10.8620, "lng": 78.6920, "capacity": 5000},
        ],
    },

    "CDL": {
        "name": "Cuddalore", "state": "Tamil Nadu", "state_code": "TN",
        "event": "Cyclone Gaja Landfall (Nov 2018)",
        "disaster_type": "cyclone",
        "center": (11.7480, 79.7714),
        "bbox": (11.68, 79.70, 11.83, 79.85),
        "zoom": 12,
        "population": 173_000, "households": 45_000,
        "damage_cr": 2_100, "homes_damaged": 38_000, "deaths": 14,
        "areas": [
            "Thiruvennainallur", "Parangipettai", "Panruti", "Chidambaram",
            "Kattumannarkoil", "Bhuvanagiri", "Virudhachalam", "Sankarapuram",
            "Cuddalore Old Town", "Semmandalam",
        ],
        "flood_zones_high": ["Cuddalore Old Town", "Parangipettai", "Semmandalam"],
        "flood_zones_medium": ["Thiruvennainallur", "Chidambaram"],
        "cyclone_track": [
            {"lat": 9.5, "lng": 82.0, "wind_kmh": 110},
            {"lat": 10.5, "lng": 81.3, "wind_kmh": 155},
            {"lat": 11.2, "lng": 80.5, "wind_kmh": 180},
            {"lat": 11.7, "lng": 79.8, "wind_kmh": 165},
            {"lat": 12.0, "lng": 79.3, "wind_kmh": 120},
        ],
        "safe_spaces": [
            {"id": "SS-01", "name": "Cuddalore Government Hospital",  "lat": 11.7480, "lng": 79.7680, "capacity": 1500},
            {"id": "SS-02", "name": "Annamalai University Shelter",   "lat": 11.3994, "lng": 79.6942, "capacity": 3000},
        ],
    },

    "NGL": {
        "name": "Nagapattinam", "state": "Tamil Nadu", "state_code": "TN",
        "event": "Cyclone Nivar + Coastal Surge (Nov 2020)",
        "disaster_type": "cyclone",
        "center": (10.7660, 79.8450),
        "bbox": (10.70, 79.79, 10.84, 79.91),
        "zoom": 12,
        "population": 96_000, "households": 25_000,
        "damage_cr": 1_500, "homes_damaged": 30_000, "deaths": 7,
        "areas": [
            "Sirkazhi", "Mayiladuthurai", "Poompuhar", "Vedaranyam",
            "Sembanarkoil", "Kollidam", "Keelaiyur", "Thalaignayar",
        ],
        "flood_zones_high": ["Poompuhar", "Vedaranyam", "Thalaignayar"],
        "flood_zones_medium": ["Sirkazhi", "Kollidam"],
        "cyclone_track": [
            {"lat": 9.0, "lng": 82.5, "wind_kmh": 100},
            {"lat": 9.8, "lng": 81.5, "wind_kmh": 145},
            {"lat": 10.3, "lng": 80.7, "wind_kmh": 175},
            {"lat": 10.8, "lng": 79.9, "wind_kmh": 185},
            {"lat": 11.2, "lng": 79.4, "wind_kmh": 130},
        ],
        "safe_spaces": [
            {"id": "SS-01", "name": "Nagapattinam Relief Centre",      "lat": 10.7660, "lng": 79.8440, "capacity": 2000},
            {"id": "SS-02", "name": "Mayiladuthurai Govt Hospital",     "lat": 11.1026, "lng": 79.6527, "capacity": 1200},
        ],
    },

    "TUT": {
        "name": "Thoothukudi", "state": "Tamil Nadu", "state_code": "TN",
        "event": "Cyclone Ockhi Coastal Surge (Dec 2017)",
        "disaster_type": "cyclone",
        "center": (8.7642, 78.1348),
        "bbox": (8.70, 78.07, 8.84, 78.21),
        "zoom": 12,
        "population": 237_000, "households": 61_000,
        "damage_cr": 1_800, "homes_damaged": 22_000, "deaths": 19,
        "areas": [
            "Tiruchendur", "Sattankulam", "Ettayapuram", "Kayalpattinam",
            "Kovilpatti", "Vilathikulam", "Thoothukudi Port", "Punnakayal",
        ],
        "flood_zones_high": ["Thoothukudi Port", "Punnakayal", "Tiruchendur"],
        "flood_zones_medium": ["Kayalpattinam", "Sattankulam"],
        "cyclone_track": [
            {"lat": 7.0, "lng": 80.0, "wind_kmh": 120},
            {"lat": 7.8, "lng": 79.2, "wind_kmh": 160},
            {"lat": 8.4, "lng": 78.6, "wind_kmh": 185},
            {"lat": 8.8, "lng": 78.1, "wind_kmh": 170},
            {"lat": 9.2, "lng": 77.7, "wind_kmh": 120},
        ],
        "safe_spaces": [
            {"id": "SS-01", "name": "Thoothukudi Medical College",     "lat": 8.7550, "lng": 78.1250, "capacity": 1800},
            {"id": "SS-02", "name": "Tiruchendur Temple Relief Shed",  "lat": 8.4983, "lng": 78.1200, "capacity": 4000},
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # ANDHRA PRADESH
    # ══════════════════════════════════════════════════════════════════════════
    "VIJ": {
        "name": "Vijayawada", "state": "Andhra Pradesh", "state_code": "AP",
        "event": "Cyclone Michaung Landfall (Dec 2023)",
        "disaster_type": "cyclone",
        "center": (16.5062, 80.6480),
        "bbox": (16.30, 80.45, 16.65, 80.85),
        "zoom": 11,
        "population": 1_048_000, "households": 280_000,
        "damage_cr": 2_800, "homes_damaged": 45_000, "deaths": 8,
        "areas": [
            "Benz Circle", "Governorpet", "Suryaraopet", "Patamata",
            "Moghalrajpuram", "Vijayawada Rural", "Krishnalanka", "Auto Nagar",
            "Nunna", "Ibrahimpatnam", "Jakkampudi", "Kondapalli", "Ramavarappadu",
        ],
        "flood_zones_high": ["Krishnalanka", "Governorpet", "Suryaraopet"],
        "flood_zones_medium": ["Patamata", "Moghalrajpuram", "Benz Circle"],
        "cyclone_track": [
            {"lat": 14.0, "lng": 82.5, "wind_kmh": 100},
            {"lat": 15.0, "lng": 81.5, "wind_kmh": 150},
            {"lat": 15.8, "lng": 80.8, "wind_kmh": 175},
            {"lat": 16.3, "lng": 80.5, "wind_kmh": 155},
            {"lat": 16.8, "lng": 80.2, "wind_kmh": 100},
        ],
        "safe_spaces": [
            {"id": "SS-01", "name": "Indira Gandhi Stadium",        "lat": 16.5160, "lng": 80.6320, "capacity": 3000},
            {"id": "SS-02", "name": "Krishnalanka Relief Hub",      "lat": 16.4850, "lng": 80.6100, "capacity": 2000},
            {"id": "SS-03", "name": "Vijayawada Govt Hospital",     "lat": 16.5105, "lng": 80.6289, "capacity": 1500},
        ],
    },

    "VIZ": {
        "name": "Visakhapatnam", "state": "Andhra Pradesh", "state_code": "AP",
        "event": "Cyclone Hudhud Direct Hit (Oct 2014)",
        "disaster_type": "cyclone",
        "center": (17.6868, 83.2185),
        "bbox": (17.58, 83.10, 17.80, 83.36),
        "zoom": 11,
        "population": 2_035_000, "households": 525_000,
        "damage_cr": 22_000, "homes_damaged": 120_000, "deaths": 61,
        "areas": [
            "Rushikonda", "Waltair", "Gajuwaka", "Bheemunipatnam", "Kommadi",
            "Pendurthi", "MVP Colony", "Maharanipet", "Dwaraka Nagar",
            "Seethammadhara", "Madhurawada", "Vizag Steel",
        ],
        "flood_zones_high": ["Bheemunipatnam", "Gajuwaka", "Rushikonda"],
        "flood_zones_medium": ["Waltair", "Kommadi", "MVP Colony"],
        "cyclone_track": [
            {"lat": 14.5, "lng": 86.0, "wind_kmh": 120},
            {"lat": 15.5, "lng": 85.2, "wind_kmh": 165},
            {"lat": 16.5, "lng": 84.3, "wind_kmh": 195},
            {"lat": 17.7, "lng": 83.2, "wind_kmh": 215},
            {"lat": 18.3, "lng": 82.5, "wind_kmh": 140},
        ],
        "safe_spaces": [
            {"id": "SS-01", "name": "Vizag NDA Campus Relief",       "lat": 17.7170, "lng": 83.2270, "capacity": 4000},
            {"id": "SS-02", "name": "GITAM University Shelter",       "lat": 17.7330, "lng": 83.2020, "capacity": 2500},
            {"id": "SS-03", "name": "King George Hospital",           "lat": 17.7211, "lng": 83.2985, "capacity": 2000},
        ],
    },

    "GNT": {
        "name": "Guntur", "state": "Andhra Pradesh", "state_code": "AP",
        "event": "Krishna River Flash Floods (Oct 2022)",
        "disaster_type": "flood",
        "center": (16.3067, 80.4365),
        "bbox": (16.24, 80.37, 16.38, 80.51),
        "zoom": 12,
        "population": 742_000, "households": 191_000,
        "damage_cr": 1_100, "homes_damaged": 21_000, "deaths": 5,
        "areas": [
            "Brodipet", "Arundelpet", "Nallakunta", "Pattabhipuram",
            "Nagarampalem", "Old Town", "Nallapadu", "Pedakakani", "Mangalagiri",
        ],
        "flood_zones_high": ["Brodipet", "Old Town", "Nallakunta"],
        "flood_zones_medium": ["Arundelpet", "Nallapadu"],
        "cyclone_track": [
            {"lat": 14.0, "lng": 82.0, "wind_kmh": 90},
            {"lat": 15.0, "lng": 81.3, "wind_kmh": 130},
            {"lat": 15.8, "lng": 80.8, "wind_kmh": 155},
            {"lat": 16.3, "lng": 80.4, "wind_kmh": 140},
            {"lat": 16.7, "lng": 80.0, "wind_kmh": 95},
        ],
        "safe_spaces": [
            {"id": "SS-01", "name": "GGH Guntur Evacuation Hub",    "lat": 16.3030, "lng": 80.4370, "capacity": 1500},
            {"id": "SS-02", "name": "Mangalagiri Govt School",       "lat": 16.4318, "lng": 80.5572, "capacity": 600},
        ],
    },

    "NLR": {
        "name": "Nellore", "state": "Andhra Pradesh", "state_code": "AP",
        "event": "Cyclone Nivar Coastal Surge (Nov 2020)",
        "disaster_type": "cyclone",
        "center": (14.4426, 79.9865),
        "bbox": (14.38, 79.91, 14.51, 80.06),
        "zoom": 12,
        "population": 505_000, "households": 130_000,
        "damage_cr": 900, "homes_damaged": 17_000, "deaths": 4,
        "areas": [
            "Vedayapalem", "Podalakur", "Kovur", "Gudur", "Allipuram",
            "Pinakini Nagar", "Potluru", "Muthukur", "Nellore Old Town",
        ],
        "flood_zones_high": ["Vedayapalem", "Potluru", "Nellore Old Town"],
        "flood_zones_medium": ["Gudur", "Muthukur"],
        "cyclone_track": [
            {"lat": 12.5, "lng": 82.5, "wind_kmh": 100},
            {"lat": 13.2, "lng": 81.7, "wind_kmh": 140},
            {"lat": 13.8, "lng": 81.0, "wind_kmh": 165},
            {"lat": 14.4, "lng": 80.0, "wind_kmh": 175},
            {"lat": 14.9, "lng": 79.5, "wind_kmh": 120},
        ],
        "safe_spaces": [
            {"id": "SS-01", "name": "Nellore Dist Collectorate Shelter","lat": 14.4434,"lng": 79.9900,"capacity": 1200},
            {"id": "SS-02", "name": "Sri Venkateswara College",         "lat": 14.4420,"lng": 79.9830,"capacity": 800},
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # TELANGANA
    # ══════════════════════════════════════════════════════════════════════════
    "HYD": {
        "name": "Hyderabad", "state": "Telangana", "state_code": "TG",
        "event": "Urban Flash Floods (Oct 2020)",
        "disaster_type": "urban_flood",
        "center": (17.3850, 78.4867),
        "bbox": (17.24, 78.33, 17.55, 78.65),
        "zoom": 11,
        "population": 10_534_000, "households": 2_780_000,
        "damage_cr": 5_000, "homes_damaged": 90_000, "deaths": 72,
        "areas": [
            "Banjara Hills", "Jubilee Hills", "Kukatpally", "Secunderabad",
            "Hitech City", "Gachibowli", "LB Nagar", "Uppal", "Dilsukhnagar",
            "Madhapur", "Begumpet", "Ameerpet", "Mehdipatnam", "Tolichowki",
            "Attapur", "Malakpet", "Nampally", "Himayatnagar", "Abids", "Charminar",
        ],
        "flood_zones_high": ["LB Nagar", "Attapur", "Malakpet", "Charminar", "Nampally"],
        "flood_zones_medium": ["Dilsukhnagar", "Mehdipatnam", "Uppal", "Tolichowki"],
        "cyclone_track": [
            {"lat": 15.0, "lng": 80.5, "wind_kmh": 80},
            {"lat": 15.8, "lng": 80.0, "wind_kmh": 110},
            {"lat": 16.5, "lng": 79.3, "wind_kmh": 130},
            {"lat": 17.2, "lng": 78.8, "wind_kmh": 120},
            {"lat": 17.8, "lng": 78.2, "wind_kmh": 80},
        ],
        "safe_spaces": [
            {"id": "SS-01", "name": "Gachibowli Indoor Stadium",     "lat": 17.4287, "lng": 78.3489, "capacity": 5000},
            {"id": "SS-02", "name": "LB Stadium Relief Hub",         "lat": 17.3948, "lng": 78.4767, "capacity": 3500},
            {"id": "SS-03", "name": "GHMC Malakpet Relief Centre",   "lat": 17.3790, "lng": 78.5000, "capacity": 1200},
        ],
    },

    "WGL": {
        "name": "Warangal", "state": "Telangana", "state_code": "TG",
        "event": "Godavari Flood Event (Aug 2022)",
        "disaster_type": "flood",
        "center": (17.9689, 79.5941),
        "bbox": (17.90, 79.52, 18.04, 79.67),
        "zoom": 12,
        "population": 812_000, "households": 210_000,
        "damage_cr": 680, "homes_damaged": 14_000, "deaths": 3,
        "areas": [
            "Hanamkonda", "Kazipet", "Balasamudram", "Subedari",
            "Dharmasagar", "Jangaon", "Nallabelli", "Mulugu",
        ],
        "flood_zones_high": ["Kazipet", "Balasamudram", "Nallabelli"],
        "flood_zones_medium": ["Dharmasagar", "Hanamkonda"],
        "cyclone_track": [
            {"lat": 16.0, "lng": 82.0, "wind_kmh": 80},
            {"lat": 16.8, "lng": 81.2, "wind_kmh": 110},
            {"lat": 17.4, "lng": 80.4, "wind_kmh": 130},
            {"lat": 18.0, "lng": 79.6, "wind_kmh": 120},
            {"lat": 18.4, "lng": 78.9, "wind_kmh": 80},
        ],
        "safe_spaces": [
            {"id": "SS-01", "name": "NIT Warangal Evacuation Hub",   "lat": 17.9860, "lng": 79.5305, "capacity": 2000},
            {"id": "SS-02", "name": "Hanamkonda Sports Complex",     "lat": 18.0100, "lng": 79.5700, "capacity": 1500},
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # ODISHA
    # ══════════════════════════════════════════════════════════════════════════
    "BHU": {
        "name": "Bhubaneswar", "state": "Odisha", "state_code": "OD",
        "event": "Cyclone Fani (Cat 5) Near-Miss (May 2019)",
        "disaster_type": "cyclone",
        "center": (20.2961, 85.8245),
        "bbox": (20.20, 85.74, 20.39, 85.92),
        "zoom": 11,
        "population": 837_000, "households": 220_000,
        "damage_cr": 12_000, "homes_damaged": 200_000, "deaths": 89,
        "areas": [
            "Nayapalli", "Saheed Nagar", "Kharavela Nagar", "Chandrasekharpur",
            "Mancheswar", "Rasulgarh", "Patia", "Dumduma", "Airfield",
            "Nandankanan", "Dera", "Tamando", "Unit 4", "Unit 9",
        ],
        "flood_zones_high": ["Mancheswar", "Rasulgarh", "Dumduma"],
        "flood_zones_medium": ["Patia", "Nayapalli", "Chandrasekharpur"],
        "cyclone_track": [
            {"lat": 16.0, "lng": 88.0, "wind_kmh": 120},
            {"lat": 17.5, "lng": 87.2, "wind_kmh": 180},
            {"lat": 18.8, "lng": 86.5, "wind_kmh": 220},
            {"lat": 20.0, "lng": 85.9, "wind_kmh": 240},
            {"lat": 21.0, "lng": 85.5, "wind_kmh": 160},
        ],
        "safe_spaces": [
            {"id": "SS-01", "name": "Kalinga Stadium Relief Hub",    "lat": 20.3210, "lng": 85.8200, "capacity": 8000},
            {"id": "SS-02", "name": "AIIMS Bhubaneswar",             "lat": 20.2388, "lng": 85.8154, "capacity": 2000},
            {"id": "SS-03", "name": "KIIT Campus Shelter",           "lat": 20.3551, "lng": 85.8197, "capacity": 5000},
        ],
    },

    "PRI": {
        "name": "Puri", "state": "Odisha", "state_code": "OD",
        "event": "Cyclone Fani Landfall (May 2019)",
        "disaster_type": "cyclone",
        "center": (19.8135, 85.8312),
        "bbox": (19.76, 85.78, 19.86, 85.89),
        "zoom": 12,
        "population": 201_000, "households": 53_000,
        "damage_cr": 6_000, "homes_damaged": 65_000, "deaths": 45,
        "areas": [
            "Sea Beach Area", "Chakratirtha", "Grand Road", "Mochi Sahi",
            "Bali Sahi", "Old Town", "Swargadwar", "Harachandi Sahi",
        ],
        "flood_zones_high": ["Sea Beach Area", "Swargadwar", "Harachandi Sahi"],
        "flood_zones_medium": ["Chakratirtha", "Grand Road", "Old Town"],
        "cyclone_track": [
            {"lat": 16.0, "lng": 88.0, "wind_kmh": 130},
            {"lat": 17.5, "lng": 87.2, "wind_kmh": 190},
            {"lat": 18.8, "lng": 86.5, "wind_kmh": 235},
            {"lat": 19.8, "lng": 85.8, "wind_kmh": 250},
            {"lat": 20.5, "lng": 85.3, "wind_kmh": 160},
        ],
        "safe_spaces": [
            {"id": "SS-01", "name": "Puri Cyclone Shelter Network",  "lat": 19.8135, "lng": 85.8312, "capacity": 6000},
            {"id": "SS-02", "name": "Puri Dist Headquarters",        "lat": 19.8100, "lng": 85.8280, "capacity": 2000},
        ],
    },

    "CTK": {
        "name": "Cuttack", "state": "Odisha", "state_code": "OD",
        "event": "Mahanadi River Overflow (Sep 2022)",
        "disaster_type": "flood",
        "center": (20.4625, 85.8830),
        "bbox": (20.40, 85.82, 20.53, 85.95),
        "zoom": 12,
        "population": 610_000, "households": 158_000,
        "damage_cr": 1_800, "homes_damaged": 35_000, "deaths": 11,
        "areas": [
            "Badambadi", "Buxi Bazaar", "Malgodown", "Tulsipur", "Cantonment",
            "Chauliaganj", "Dolamundai", "Ranihat", "Khannagar", "Mangalabag",
        ],
        "flood_zones_high": ["Badambadi", "Malgodown", "Tulsipur"],
        "flood_zones_medium": ["Buxi Bazaar", "Dolamundai", "Ranihat"],
        "cyclone_track": [
            {"lat": 17.0, "lng": 88.0, "wind_kmh": 100},
            {"lat": 18.0, "lng": 87.2, "wind_kmh": 140},
            {"lat": 19.2, "lng": 86.5, "wind_kmh": 165},
            {"lat": 20.4, "lng": 85.9, "wind_kmh": 150},
            {"lat": 21.2, "lng": 85.4, "wind_kmh": 100},
        ],
        "safe_spaces": [
            {"id": "SS-01", "name": "SCB Medical College Cuttack",   "lat": 20.4777, "lng": 85.8793, "capacity": 2000},
            {"id": "SS-02", "name": "Barabati Stadium Relief",       "lat": 20.4728, "lng": 85.8836, "capacity": 5000},
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # WEST BENGAL
    # ══════════════════════════════════════════════════════════════════════════
    "KOL": {
        "name": "Kolkata", "state": "West Bengal", "state_code": "WB",
        "event": "Cyclone Amphan (May 2020)",
        "disaster_type": "cyclone",
        "center": (22.5726, 88.3639),
        "bbox": (22.44, 88.25, 22.70, 88.48),
        "zoom": 11,
        "population": 14_850_000, "households": 3_900_000,
        "damage_cr": 100_000, "homes_damaged": 2_860_000, "deaths": 98,
        "areas": [
            "Park Street", "Salt Lake", "Dum Dum", "Jadavpur", "Tollygunge",
            "Ballygunge", "New Alipore", "Garden Reach", "Cossipore", "Bagbazar",
            "Shyambazar", "Maniktala", "Beliaghata", "Tiljala", "Santragachi",
            "Kasba", "Lake Gardens", "Regent Park", "Behala", "Maheshtala",
        ],
        "flood_zones_high": ["Garden Reach", "Cossipore", "Tiljala", "Santragachi", "Behala"],
        "flood_zones_medium": ["Tollygunge", "Jadavpur", "Beliaghata", "Maheshtala"],
        "cyclone_track": [
            {"lat": 16.0, "lng": 88.5, "wind_kmh": 110},
            {"lat": 18.0, "lng": 88.3, "wind_kmh": 160},
            {"lat": 20.0, "lng": 88.1, "wind_kmh": 195},
            {"lat": 22.0, "lng": 88.3, "wind_kmh": 185},
            {"lat": 23.5, "lng": 88.4, "wind_kmh": 120},
        ],
        "safe_spaces": [
            {"id": "SS-01", "name": "Salt Lake Stadium",             "lat": 22.5782, "lng": 88.3985, "capacity": 85000},
            {"id": "SS-02", "name": "Netaji Indoor Stadium",         "lat": 22.5774, "lng": 88.3435, "capacity": 10000},
            {"id": "SS-03", "name": "SSKM Hospital Relief Centre",   "lat": 22.5347, "lng": 88.3451, "capacity": 2000},
        ],
    },

    "MDP": {
        "name": "Midnapore", "state": "West Bengal", "state_code": "WB",
        "event": "Cyclone Amphan Inland Impact (May 2020)",
        "disaster_type": "cyclone",
        "center": (22.4235, 87.3244),
        "bbox": (22.36, 87.25, 22.50, 87.40),
        "zoom": 12,
        "population": 420_000, "households": 108_000,
        "damage_cr": 8_000, "homes_damaged": 150_000, "deaths": 32,
        "areas": [
            "Panskura", "Contai", "Egra", "Haldia", "Tamluk",
            "Nandakumar", "Mahishadal", "Nandigram", "Ghatal", "Chandrakona",
        ],
        "flood_zones_high": ["Nandigram", "Contai", "Haldia"],
        "flood_zones_medium": ["Tamluk", "Mahishadal", "Egra"],
        "cyclone_track": [
            {"lat": 19.0, "lng": 88.5, "wind_kmh": 110},
            {"lat": 20.5, "lng": 88.0, "wind_kmh": 160},
            {"lat": 21.5, "lng": 87.8, "wind_kmh": 180},
            {"lat": 22.4, "lng": 87.3, "wind_kmh": 155},
            {"lat": 23.0, "lng": 86.8, "wind_kmh": 100},
        ],
        "safe_spaces": [
            {"id": "SS-01", "name": "Midnapore Medical College",     "lat": 22.4268, "lng": 87.3249, "capacity": 1500},
            {"id": "SS-02", "name": "Contai Relief Cyclone Shelter", "lat": 21.7809, "lng": 87.7481, "capacity": 3000},
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # MAHARASHTRA
    # ══════════════════════════════════════════════════════════════════════════
    "MUM": {
        "name": "Mumbai", "state": "Maharashtra", "state_code": "MH",
        "event": "Cyclone Tauktae + Coastal Flooding (May 2021)",
        "disaster_type": "cyclone",
        "center": (19.0760, 72.8777),
        "bbox": (18.85, 72.75, 19.35, 72.98),
        "zoom": 11,
        "population": 12_478_000, "households": 3_100_000,
        "damage_cr": 4_200, "homes_damaged": 82_000, "deaths": 12,
        "areas": [
            "Dharavi", "Bandra", "Andheri", "Kurla", "Dadar",
            "Worli", "Colaba", "Chembur", "Ghatkopar", "Malad",
            "Borivali", "Kandivali", "Jogeshwari", "Goregaon", "Vikhroli",
        ],
        "flood_zones_high": ["Dharavi", "Kurla", "Dadar", "Chembur"],
        "flood_zones_medium": ["Andheri", "Ghatkopar", "Malad", "Vikhroli"],
        "cyclone_track": [
            {"lat": 17.0, "lng": 73.5, "wind_kmh": 120},
            {"lat": 18.0, "lng": 73.0, "wind_kmh": 160},
            {"lat": 18.8, "lng": 72.9, "wind_kmh": 185},
            {"lat": 19.2, "lng": 72.8, "wind_kmh": 150},
            {"lat": 19.8, "lng": 72.6, "wind_kmh": 100},
        ],
        "safe_spaces": [
            {"id": "SS-01", "name": "BKC Emergency Hub",             "lat": 19.0660, "lng": 72.8680, "capacity": 5000},
            {"id": "SS-02", "name": "Andheri Sports Complex",        "lat": 19.1136, "lng": 72.8697, "capacity": 3000},
            {"id": "SS-03", "name": "Azad Maidan Relief Centre",     "lat": 18.9395, "lng": 72.8327, "capacity": 8000},
        ],
    },

    "PUN": {
        "name": "Pune", "state": "Maharashtra", "state_code": "MH",
        "event": "Mutha River Flash Floods (Jul 2021)",
        "disaster_type": "urban_flood",
        "center": (18.5204, 73.8567),
        "bbox": (18.43, 73.75, 18.62, 73.96),
        "zoom": 11,
        "population": 7_276_000, "households": 1_890_000,
        "damage_cr": 2_200, "homes_damaged": 32_000, "deaths": 25,
        "areas": [
            "Kothrud", "Hadapsar", "Wanowrie", "Kondhwa", "Shivajinagar",
            "Pimpri-Chinchwad", "Hinjewadi", "Baner", "Aundh", "Kharadi",
            "Viman Nagar", "Deccan", "Camp", "Sinhagad Road", "Katraj",
        ],
        "flood_zones_high": ["Kondhwa", "Hadapsar", "Katraj"],
        "flood_zones_medium": ["Wanowrie", "Shivajinagar", "Sinhagad Road"],
        "cyclone_track": [
            {"lat": 16.5, "lng": 75.0, "wind_kmh": 80},
            {"lat": 17.2, "lng": 74.6, "wind_kmh": 110},
            {"lat": 17.9, "lng": 74.2, "wind_kmh": 130},
            {"lat": 18.5, "lng": 73.9, "wind_kmh": 120},
            {"lat": 19.0, "lng": 73.5, "wind_kmh": 80},
        ],
        "safe_spaces": [
            {"id": "SS-01", "name": "Shiv Chhatrapati Sports Complex","lat": 18.5569, "lng": 73.9098, "capacity": 6000},
            {"id": "SS-02", "name": "Pune University Shelter Zone",  "lat": 18.5251, "lng": 73.8535, "capacity": 4000},
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # KERALA
    # ══════════════════════════════════════════════════════════════════════════
    "COK": {
        "name": "Kochi", "state": "Kerala", "state_code": "KL",
        "event": "Extreme Monsoon Flooding (Aug 2018)",
        "disaster_type": "flood",
        "center": (9.9312, 76.2673),
        "bbox": (9.86, 76.19, 10.01, 76.36),
        "zoom": 12,
        "population": 677_000, "households": 175_000,
        "damage_cr": 31_000, "homes_damaged": 520_000, "deaths": 483,
        "areas": [
            "Ernakulam", "Aluva", "Edapally", "Vytilla", "Tripunithura",
            "Kalamassery", "Kakkanad", "Fort Kochi", "Mattancherry",
            "Thevara", "Palarivattom", "Vyttila Junction",
        ],
        "flood_zones_high": ["Fort Kochi", "Mattancherry", "Ernakulam"],
        "flood_zones_medium": ["Edapally", "Kalamassery", "Thevara"],
        "cyclone_track": [
            {"lat": 8.0, "lng": 75.0, "wind_kmh": 90},
            {"lat": 8.8, "lng": 75.5, "wind_kmh": 130},
            {"lat": 9.4, "lng": 76.0, "wind_kmh": 155},
            {"lat": 9.9, "lng": 76.3, "wind_kmh": 145},
            {"lat": 10.5, "lng": 76.6, "wind_kmh": 100},
        ],
        "safe_spaces": [
            {"id": "SS-01", "name": "Jawaharlal Nehru Stadium",      "lat": 9.9840, "lng": 76.2930, "capacity": 75000},
            {"id": "SS-02", "name": "Ernakulam Dist Relief Hub",     "lat": 9.9816, "lng": 76.2999, "capacity": 3000},
        ],
    },

    "TVM": {
        "name": "Thiruvananthapuram", "state": "Kerala", "state_code": "KL",
        "event": "Cyclone Ockhi + Coastal Flooding (Nov 2017)",
        "disaster_type": "cyclone",
        "center": (8.5241, 76.9366),
        "bbox": (8.44, 76.88, 8.61, 77.00),
        "zoom": 12,
        "population": 752_000, "households": 193_000,
        "damage_cr": 2_500, "homes_damaged": 42_000, "deaths": 28,
        "areas": [
            "Kazhakuttam", "Peroorkada", "Kowdiar", "Kesavadasapuram",
            "Vattiyoorkavu", "Enchakkal", "Pattom", "Sasthamangalam",
            "Sreekaryam", "Vizhinjam", "Nemom", "Vanchiyoor",
        ],
        "flood_zones_high": ["Vizhinjam", "Vanchiyoor", "Enchakkal"],
        "flood_zones_medium": ["Peroorkada", "Nemom", "Kazhakuttam"],
        "cyclone_track": [
            {"lat": 7.0, "lng": 76.0, "wind_kmh": 100},
            {"lat": 7.6, "lng": 76.4, "wind_kmh": 145},
            {"lat": 8.1, "lng": 76.7, "wind_kmh": 170},
            {"lat": 8.5, "lng": 76.9, "wind_kmh": 155},
            {"lat": 9.0, "lng": 77.2, "wind_kmh": 110},
        ],
        "safe_spaces": [
            {"id": "SS-01", "name": "Central Stadium TVM",           "lat": 8.5018, "lng": 76.9502, "capacity": 20000},
            {"id": "SS-02", "name": "Kerala University Campus",      "lat": 8.5583, "lng": 76.8998, "capacity": 3000},
        ],
    },

    "KZD": {
        "name": "Kozhikode", "state": "Kerala", "state_code": "KL",
        "event": "Heavy Monsoon Landslides (Aug 2019)",
        "disaster_type": "landslide",
        "center": (11.2588, 75.7804),
        "bbox": (11.19, 75.70, 11.33, 75.86),
        "zoom": 12,
        "population": 609_000, "households": 158_000,
        "damage_cr": 1_800, "homes_damaged": 30_000, "deaths": 55,
        "areas": [
            "Calicut Beach", "Malaparamba", "Chevayur", "Feroke",
            "Ramanattukara", "Beypore", "Elathur", "Nadakkavu",
            "Kunnamangalam", "Panniyankara", "East Hill",
        ],
        "flood_zones_high": ["Calicut Beach", "Beypore", "Feroke"],
        "flood_zones_medium": ["Malaparamba", "Elathur", "Nadakkavu"],
        "cyclone_track": [
            {"lat": 9.5, "lng": 74.5, "wind_kmh": 90},
            {"lat": 10.2, "lng": 74.9, "wind_kmh": 130},
            {"lat": 10.8, "lng": 75.4, "wind_kmh": 150},
            {"lat": 11.3, "lng": 75.8, "wind_kmh": 140},
            {"lat": 11.8, "lng": 76.2, "wind_kmh": 95},
        ],
        "safe_spaces": [
            {"id": "SS-01", "name": "Calicut Medical College",       "lat": 11.1279, "lng": 75.9239, "capacity": 2000},
            {"id": "SS-02", "name": "EMS Stadium Kozhikode",         "lat": 11.2513, "lng": 75.7855, "capacity": 15000},
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # GUJARAT
    # ══════════════════════════════════════════════════════════════════════════
    "SRT": {
        "name": "Surat", "state": "Gujarat", "state_code": "GJ",
        "event": "Cyclone Tauktae + Tapi River Flooding (May 2021)",
        "disaster_type": "cyclone",
        "center": (21.1702, 72.8311),
        "bbox": (21.10, 72.75, 21.25, 72.92),
        "zoom": 12,
        "population": 8_200_000, "households": 2_110_000,
        "damage_cr": 3_800, "homes_damaged": 60_000, "deaths": 5,
        "areas": [
            "Adajan", "Katargam", "Udhna", "Athwa", "Rander",
            "Varachha", "Kapodara", "Limbayat", "Laskana", "Olpad",
        ],
        "flood_zones_high": ["Katargam", "Udhna", "Limbayat"],
        "flood_zones_medium": ["Adajan", "Rander", "Varachha"],
        "cyclone_track": [
            {"lat": 18.5, "lng": 71.5, "wind_kmh": 120},
            {"lat": 19.5, "lng": 72.0, "wind_kmh": 160},
            {"lat": 20.4, "lng": 72.4, "wind_kmh": 185},
            {"lat": 21.2, "lng": 72.8, "wind_kmh": 175},
            {"lat": 22.0, "lng": 73.0, "wind_kmh": 110},
        ],
        "safe_spaces": [
            {"id": "SS-01", "name": "Surat Municipal Stadium",       "lat": 21.1910, "lng": 72.8345, "capacity": 15000},
            {"id": "SS-02", "name": "South Gujarat Univ Campus",     "lat": 21.1597, "lng": 72.7846, "capacity": 3000},
        ],
    },

    "AMD": {
        "name": "Ahmedabad", "state": "Gujarat", "state_code": "GJ",
        "event": "Cyclone Biparjoy + Urban Heatwave (Jun 2023)",
        "disaster_type": "cyclone",
        "center": (23.0225, 72.5714),
        "bbox": (22.95, 72.48, 23.11, 72.67),
        "zoom": 11,
        "population": 8_450_000, "households": 2_180_000,
        "damage_cr": 2_600, "homes_damaged": 45_000, "deaths": 3,
        "areas": [
            "Navrangpura", "Satellite", "Bopal", "Gota", "Chandkheda",
            "Vastrapur", "Maninagar", "Naranpura", "Paldi", "Shahibaug",
            "Bapunagar", "Vatwa", "Odhav", "Naroda",
        ],
        "flood_zones_high": ["Bapunagar", "Vatwa", "Odhav"],
        "flood_zones_medium": ["Naranpura", "Paldi", "Maninagar"],
        "cyclone_track": [
            {"lat": 20.0, "lng": 70.0, "wind_kmh": 110},
            {"lat": 21.0, "lng": 70.8, "wind_kmh": 150},
            {"lat": 22.0, "lng": 71.5, "wind_kmh": 175},
            {"lat": 23.0, "lng": 72.6, "wind_kmh": 160},
            {"lat": 24.0, "lng": 73.2, "wind_kmh": 110},
        ],
        "safe_spaces": [
            {"id": "SS-01", "name": "Narendra Modi Stadium",         "lat": 23.0935, "lng": 72.5953, "capacity": 132000},
            {"id": "SS-02", "name": "AMC Sports Complex",            "lat": 23.0400, "lng": 72.5600, "capacity": 4000},
        ],
    },

    "RJK": {
        "name": "Rajkot", "state": "Gujarat", "state_code": "GJ",
        "event": "Cyclone Biparjoy (Jun 2023)",
        "disaster_type": "cyclone",
        "center": (22.3039, 70.8022),
        "bbox": (22.24, 70.73, 22.38, 70.89),
        "zoom": 12,
        "population": 1_753_000, "households": 452_000,
        "damage_cr": 1_500, "homes_damaged": 27_000, "deaths": 2,
        "areas": [
            "Raiya Road", "Kalawad Road", "Mavdi", "Bhavnagar Road",
            "150 Feet Ring Road", "Pedak Road", "Gondal Road", "Rajkot Rural",
        ],
        "flood_zones_high": ["Mavdi", "Pedak Road"],
        "flood_zones_medium": ["Gondal Road", "Rajkot Rural"],
        "cyclone_track": [
            {"lat": 19.5, "lng": 68.5, "wind_kmh": 120},
            {"lat": 20.5, "lng": 69.3, "wind_kmh": 155},
            {"lat": 21.4, "lng": 70.0, "wind_kmh": 175},
            {"lat": 22.3, "lng": 70.8, "wind_kmh": 160},
            {"lat": 23.0, "lng": 71.5, "wind_kmh": 105},
        ],
        "safe_spaces": [
            {"id": "SS-01", "name": "Rajkot Municipal Corporation",  "lat": 22.3010, "lng": 70.8050, "capacity": 2000},
            {"id": "SS-02", "name": "Saurashtra Cricket Stadium",    "lat": 22.2977, "lng": 70.7806, "capacity": 28000},
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # KARNATAKA
    # ══════════════════════════════════════════════════════════════════════════
    "MNG": {
        "name": "Mangalore", "state": "Karnataka", "state_code": "KA",
        "event": "Coastal Flooding + Landslides (Aug 2020)",
        "disaster_type": "landslide",
        "center": (12.9141, 74.8560),
        "bbox": (12.84, 74.79, 12.99, 74.93),
        "zoom": 12,
        "population": 623_000, "households": 161_000,
        "damage_cr": 1_400, "homes_damaged": 25_000, "deaths": 19,
        "areas": [
            "Hampankatta", "Kodialbail", "Bejai", "Kankanady", "Balmatta",
            "Kadri", "Pandeshwar", "Falnir", "Attavar", "Bondel",
            "Kuloor", "Surathkal",
        ],
        "flood_zones_high": ["Hampankatta", "Kodialbail", "Kuloor"],
        "flood_zones_medium": ["Bejai", "Kankanady", "Pandeshwar"],
        "cyclone_track": [
            {"lat": 10.5, "lng": 73.5, "wind_kmh": 90},
            {"lat": 11.3, "lng": 74.0, "wind_kmh": 130},
            {"lat": 12.1, "lng": 74.4, "wind_kmh": 150},
            {"lat": 12.9, "lng": 74.8, "wind_kmh": 140},
            {"lat": 13.5, "lng": 75.2, "wind_kmh": 95},
        ],
        "safe_spaces": [
            {"id": "SS-01", "name": "Wenlock Hospital Mangalore",    "lat": 12.8719, "lng": 74.8439, "capacity": 1500},
            {"id": "SS-02", "name": "NITK Surathkal Campus",         "lat": 13.0101, "lng": 74.7942, "capacity": 2500},
        ],
    },

    "BLR": {
        "name": "Bengaluru", "state": "Karnataka", "state_code": "KA",
        "event": "Varthur Lake Urban Flooding (Sep 2022)",
        "disaster_type": "urban_flood",
        "center": (12.9716, 77.5946),
        "bbox": (12.86, 77.47, 13.09, 77.74),
        "zoom": 11,
        "population": 12_764_000, "households": 3_290_000,
        "damage_cr": 3_700, "homes_damaged": 55_000, "deaths": 16,
        "areas": [
            "Whitefield", "Koramangala", "Jayanagar", "Indiranagar", "HSR Layout",
            "Electronic City", "Marathahalli", "Yeshwanthpur", "Hebbal", "Bellandur",
            "Varthur", "Bannerghatta Road", "BTM Layout", "JP Nagar", "Rajajinagar",
        ],
        "flood_zones_high": ["Varthur", "Bellandur", "Whitefield"],
        "flood_zones_medium": ["HSR Layout", "Marathahalli", "Electronic City"],
        "cyclone_track": [
            {"lat": 11.0, "lng": 77.0, "wind_kmh": 70},
            {"lat": 11.7, "lng": 77.2, "wind_kmh": 95},
            {"lat": 12.3, "lng": 77.4, "wind_kmh": 115},
            {"lat": 12.9, "lng": 77.6, "wind_kmh": 105},
            {"lat": 13.4, "lng": 77.8, "wind_kmh": 75},
        ],
        "safe_spaces": [
            {"id": "SS-01", "name": "Kanteerava Indoor Stadium",     "lat": 12.9741, "lng": 77.6045, "capacity": 12000},
            {"id": "SS-02", "name": "IISc Campus Relief Hub",        "lat": 13.0219, "lng": 77.5671, "capacity": 3000},
            {"id": "SS-03", "name": "Electronic City Expo Centre",   "lat": 12.8482, "lng": 77.6621, "capacity": 5000},
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # BIHAR
    # ══════════════════════════════════════════════════════════════════════════
    "PAT": {
        "name": "Patna", "state": "Bihar", "state_code": "BR",
        "event": "Ganga River Overflow + Urban Flooding (Sep 2019)",
        "disaster_type": "flood",
        "center": (25.5941, 85.1376),
        "bbox": (25.54, 85.06, 25.66, 85.22),
        "zoom": 12,
        "population": 2_047_000, "households": 528_000,
        "damage_cr": 1_600, "homes_damaged": 34_000, "deaths": 73,
        "areas": [
            "Rajendra Nagar", "Boring Road", "Kankarbagh", "Danapur",
            "Patna Sahib", "Phulwari Sharif", "Fatwa", "Bailey Road",
            "Gardanibagh", "Kadamkuan", "Patliputra Colony", "Anisabad",
        ],
        "flood_zones_high": ["Phulwari Sharif", "Fatwa", "Gardanibagh"],
        "flood_zones_medium": ["Rajendra Nagar", "Danapur", "Anisabad"],
        "cyclone_track": [
            {"lat": 23.5, "lng": 88.0, "wind_kmh": 70},
            {"lat": 24.2, "lng": 87.2, "wind_kmh": 95},
            {"lat": 24.9, "lng": 86.2, "wind_kmh": 110},
            {"lat": 25.6, "lng": 85.1, "wind_kmh": 100},
            {"lat": 26.1, "lng": 84.2, "wind_kmh": 70},
        ],
        "safe_spaces": [
            {"id": "SS-01", "name": "PMCH Patna Govt Hospital",      "lat": 25.6120, "lng": 85.1401, "capacity": 2000},
            {"id": "SS-02", "name": "Patna Science College Ground",  "lat": 25.6024, "lng": 85.1440, "capacity": 5000},
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # ASSAM
    # ══════════════════════════════════════════════════════════════════════════
    "GHY": {
        "name": "Guwahati", "state": "Assam", "state_code": "AS",
        "event": "Brahmaputra Flooding + Landslides (Jun 2022)",
        "disaster_type": "flood",
        "center": (26.1445, 91.7362),
        "bbox": (26.08, 91.65, 26.22, 91.83),
        "zoom": 12,
        "population": 968_000, "households": 248_000,
        "damage_cr": 1_800, "homes_damaged": 35_000, "deaths": 48,
        "areas": [
            "Dispur", "Paltan Bazaar", "Silpukhuri", "Ulubari", "Chandmari",
            "Narengi", "Beltola", "Kalapahar", "Ganeshguri", "Noonmati",
            "Hatigaon", "Khanapara", "Adabari", "Sixmile",
        ],
        "flood_zones_high": ["Paltan Bazaar", "Noonmati", "Adabari"],
        "flood_zones_medium": ["Dispur", "Beltola", "Ulubari"],
        "cyclone_track": [
            {"lat": 24.0, "lng": 94.0, "wind_kmh": 80},
            {"lat": 24.8, "lng": 93.2, "wind_kmh": 105},
            {"lat": 25.5, "lng": 92.4, "wind_kmh": 120},
            {"lat": 26.1, "lng": 91.7, "wind_kmh": 110},
            {"lat": 26.7, "lng": 91.0, "wind_kmh": 75},
        ],
        "safe_spaces": [
            {"id": "SS-01", "name": "GMCH Guwahati Medical College", "lat": 26.1819, "lng": 91.7479, "capacity": 2000},
            {"id": "SS-02", "name": "Sarusajai Stadium",             "lat": 26.1534, "lng": 91.7527, "capacity": 30000},
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # UTTARAKHAND
    # ══════════════════════════════════════════════════════════════════════════
    "DED": {
        "name": "Dehradun", "state": "Uttarakhand", "state_code": "UK",
        "event": "Flash Floods + Cloudburst (Aug 2022)",
        "disaster_type": "flood",
        "center": (30.3165, 78.0322),
        "bbox": (30.26, 77.97, 30.38, 78.11),
        "zoom": 12,
        "population": 803_000, "households": 208_000,
        "damage_cr": 1_200, "homes_damaged": 22_000, "deaths": 34,
        "areas": [
            "Patel Nagar", "Vasant Vihar", "Rajpur Road", "Dalanwala",
            "Gandhi Road", "Raipur Road", "Sahastradhara", "Mussoorie Road",
            "Rispana", "Bindal", "Chakrata Road",
        ],
        "flood_zones_high": ["Raipur Road", "Rispana", "Bindal"],
        "flood_zones_medium": ["Dalanwala", "Vasant Vihar", "Gandhi Road"],
        "cyclone_track": [
            {"lat": 28.5, "lng": 80.0, "wind_kmh": 65},
            {"lat": 29.2, "lng": 79.2, "wind_kmh": 85},
            {"lat": 29.8, "lng": 78.6, "wind_kmh": 100},
            {"lat": 30.3, "lng": 78.0, "wind_kmh": 95},
            {"lat": 30.7, "lng": 77.5, "wind_kmh": 65},
        ],
        "safe_spaces": [
            {"id": "SS-01", "name": "IMA Dehradun Evacuation Hub",   "lat": 30.3399, "lng": 78.0423, "capacity": 3000},
            {"id": "SS-02", "name": "ISBT Dehradun Relief Centre",   "lat": 30.3141, "lng": 78.0543, "capacity": 2000},
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # HIMACHAL PRADESH
    # ══════════════════════════════════════════════════════════════════════════
    "SML": {
        "name": "Shimla", "state": "Himachal Pradesh", "state_code": "HP",
        "event": "Cloudburst + Landslide (Aug 2023)",
        "disaster_type": "landslide",
        "center": (31.1048, 77.1734),
        "bbox": (31.07, 77.12, 31.14, 77.23),
        "zoom": 13,
        "population": 171_000, "households": 44_000,
        "damage_cr": 800, "homes_damaged": 12_000, "deaths": 22,
        "areas": [
            "Mall Road", "Lakkar Bazaar", "Chhota Shimla", "Boileauganj",
            "Kanlog", "Summerhill", "Kufri", "Mashobra", "Lower Bazaar", "Kasumpti",
        ],
        "flood_zones_high": ["Lower Bazaar", "Kasumpti", "Summerhill"],
        "flood_zones_medium": ["Chhota Shimla", "Kufri", "Boileauganj"],
        "cyclone_track": [
            {"lat": 29.5, "lng": 78.5, "wind_kmh": 55},
            {"lat": 30.0, "lng": 78.0, "wind_kmh": 75},
            {"lat": 30.6, "lng": 77.7, "wind_kmh": 90},
            {"lat": 31.1, "lng": 77.2, "wind_kmh": 85},
            {"lat": 31.5, "lng": 76.8, "wind_kmh": 60},
        ],
        "safe_spaces": [
            {"id": "SS-01", "name": "IGMC Shimla Govt Hospital",     "lat": 31.1018, "lng": 77.1719, "capacity": 1200},
            {"id": "SS-02", "name": "Rivoli Bus Stand Relief Area",  "lat": 31.1038, "lng": 77.1686, "capacity": 1500},
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # RAJASTHAN
    # ══════════════════════════════════════════════════════════════════════════
    "JAI": {
        "name": "Jaipur", "state": "Rajasthan", "state_code": "RJ",
        "event": "Extreme Monsoon Flash Floods (Sep 2022)",
        "disaster_type": "urban_flood",
        "center": (26.9124, 75.7873),
        "bbox": (26.84, 75.71, 26.99, 75.87),
        "zoom": 12,
        "population": 3_073_000, "households": 794_000,
        "damage_cr": 1_100, "homes_damaged": 19_000, "deaths": 11,
        "areas": [
            "Malviya Nagar", "Vaishali Nagar", "C-Scheme", "Mansarovar",
            "Pratap Nagar", "Sanganer", "Raja Park", "Adarsh Nagar",
            "Jagatpura", "Sitapura", "Jhotwara", "Sodala",
        ],
        "flood_zones_high": ["Sanganer", "Jagatpura", "Sitapura"],
        "flood_zones_medium": ["Mansarovar", "Malviya Nagar", "Sodala"],
        "cyclone_track": [
            {"lat": 25.0, "lng": 77.5, "wind_kmh": 65},
            {"lat": 25.6, "lng": 77.0, "wind_kmh": 85},
            {"lat": 26.2, "lng": 76.4, "wind_kmh": 100},
            {"lat": 26.9, "lng": 75.8, "wind_kmh": 90},
            {"lat": 27.4, "lng": 75.3, "wind_kmh": 65},
        ],
        "safe_spaces": [
            {"id": "SS-01", "name": "SMS Stadium Jaipur",            "lat": 26.9100, "lng": 75.7965, "capacity": 30000},
            {"id": "SS-02", "name": "Sawai Man Singh Hospital",      "lat": 26.9157, "lng": 75.8077, "capacity": 2000},
        ],
    },
}


# ── Runtime enrichment ────────────────────────────────────────────────────────

def get_location(code: str) -> dict:
    """Return a fully-enriched location dict.

    Enrichments (all cached 30 min, all fail-safe):
    1. Real neighbourhood names from OSM Overpass
    2. Real safe spaces (hospitals / schools / stadiums) from OSM
    3. Active cyclone track from GDACS if a storm is within 1,500 km
    """
    entry = CITY_CATALOGUE.get(code.upper())
    if not entry:
        valid = list(CITY_CATALOGUE.keys())
        raise ValueError(f"Unknown location code '{code}'. Valid codes: {valid}")

    loc = dict(entry)  # shallow copy so we don't mutate the catalogue

    try:
        from app.core.realtime_data import (
            fetch_osm_neighborhoods,
            fetch_osm_safe_spaces,
            fetch_active_cyclone_gdacs,
            build_cyclone_track_from_gdacs,
        )

        bbox = loc["bbox"]
        city_lat, city_lng = loc["center"]

        # 1. Real neighbourhood names
        osm_areas = fetch_osm_neighborhoods(bbox)
        if len(osm_areas) >= 8:
            loc["areas"] = osm_areas
            loc["areas_source"] = "osm_live"
        else:
            loc["areas_source"] = "static_catalogue"

        # 2. Real safe spaces — merge OSM results with static fallback
        osm_ss = fetch_osm_safe_spaces(bbox)
        if len(osm_ss) >= 2:
            # Assign sequential IDs, keep at most 8
            for i, s in enumerate(osm_ss):
                s["id"] = f"SS-{i+1:02d}"
            loc["safe_spaces"] = osm_ss[:8]
            loc["safe_spaces_source"] = "osm_live"
        else:
            loc["safe_spaces_source"] = "static_catalogue"

        # 3. Active GDACS cyclone near city
        active_tc = fetch_active_cyclone_gdacs(city_lat, city_lng)
        if active_tc:
            loc["cyclone_track"] = build_cyclone_track_from_gdacs(active_tc, city_lat, city_lng)
            loc["active_cyclone"] = active_tc
        else:
            loc["active_cyclone"] = None

    except Exception:
        # Any import or network issue → serve from static catalogue
        loc.setdefault("areas_source", "static_catalogue")
        loc.setdefault("safe_spaces_source", "static_catalogue")
        loc.setdefault("active_cyclone", None)

    return loc


def list_locations() -> list:
    """Return all cities grouped by state, sorted alphabetically."""
    by_state: dict = {}
    for code, entry in CITY_CATALOGUE.items():
        state = entry["state"]
        by_state.setdefault(state, []).append({
            "code":          code,
            "name":          entry["name"],
            "state":         state,
            "state_code":    entry["state_code"],
            "event":         entry["event"],
            "disaster_type": entry["disaster_type"],
            "center":        entry["center"],
            "population":    entry.get("population", 0),
            "damage_cr":     entry.get("damage_cr", 0),
        })
    return [
        {"state": state, "cities": sorted(cities, key=lambda c: c["name"])}
        for state, cities in sorted(by_state.items())
    ]


def list_states() -> list:
    """Return unique state names present in the catalogue."""
    return sorted({e["state"] for e in CITY_CATALOGUE.values()})


# Legacy alias so old callers that imported LOCATION_CATALOGUE don't break
LOCATION_CATALOGUE = CITY_CATALOGUE
