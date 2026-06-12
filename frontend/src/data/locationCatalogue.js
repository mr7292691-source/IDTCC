// Location catalogue — ported from notebook Cell 0c
// Source: IMD / NDMA / Census 2011 / IRDAI public records

export const LOCATION_CATALOGUE = {
  CHN: {
    key: 'CHN',
    name: 'Chennai, Tamil Nadu',
    event: 'Cyclone Michaung + Urban Flooding (Dec 2023)',
    eventType: 'Severe Cyclonic Storm + Urban Flood',
    eventYear: 2023,
    damageCr: 8600,
    homesDamaged: 165000,
    deaths: 31,
    source: 'IMD Post-Season Report 2023 / SDMA Tamil Nadu',
    center: [13.0827, 80.2707],
    bbox: [12.85, 80.07, 13.25, 80.32],
    zoom: 11,
    population: 7088000,
    households: 1854000,
    areas: [
      'Adyar','Velachery','Tambaram','Anna Nagar','T. Nagar',
      'Mylapore','Perambur','Royapuram','Besant Nagar','Chromepet',
      'Sholinganallur','Porur','Ambattur','Avadi','Madhavaram',
      'Kodambakkam','Nungambakkam','Egmore','Triplicane','Washermanpet',
    ],
    floodZonesHigh:   ['Adyar','Velachery','Perambur','Royapuram','Washermanpet','Triplicane'],
    floodZonesMedium: ['T. Nagar','Kodambakkam','Egmore','Chromepet','Tambaram'],
    floodZonesLow:    ['Anna Nagar','Nungambakkam','Porur','Ambattur','Avadi','Madhavaram','Sholinganallur','Mylapore','Besant Nagar'],
    cycloneTrack: [
      { lat: 12.00, lng: 81.50, wind_kmh: 120, hours_out: 48 },
      { lat: 12.30, lng: 81.10, wind_kmh: 140, hours_out: 36 },
      { lat: 12.60, lng: 80.80, wind_kmh: 165, hours_out: 24 },
      { lat: 12.90, lng: 80.50, wind_kmh: 180, hours_out: 12 },
      { lat: 13.10, lng: 80.28, wind_kmh: 165, hours_out: 6  },
    ],
    maxWindKmh: 165,
    cycloneName: 'NIVAR',
    cycloneCategory: 'Very Severe Cyclonic Storm',
    radiusKm: 120,
    landfallEtaH: 48,
    safeSpaces: [
      { id: 'SS-001', name: 'Anna Nagar Community Hall',  lat: 13.0860, lng: 80.2101, capacity: 500 },
      { id: 'SS-002', name: 'T. Nagar Govt School',       lat: 13.0418, lng: 80.2341, capacity: 350 },
      { id: 'SS-003', name: 'Tambaram Railway Ground',    lat: 12.9249, lng: 80.1000, capacity: 600 },
      { id: 'SS-004', name: 'Velachery Lake Grounds',     lat: 12.9815, lng: 80.2209, capacity: 400 },
      { id: 'SS-005', name: 'Adyar Lions Club Hall',      lat: 13.0012, lng: 80.2565, capacity: 300 },
      { id: 'SS-006', name: 'Perambur Loco Works Ground', lat: 13.1142, lng: 80.2318, capacity: 700 },
    ],
  },
  WYD: {
    key: 'WYD',
    name: 'Wayanad, Kerala',
    event: 'Mundakkai Landslide + Flash Flood (July 2024)',
    eventType: 'Landslide + Flash Flood',
    eventYear: 2024,
    damageCr: 4200,
    homesDamaged: 12000,
    deaths: 231,
    source: 'NDMA Situation Report / Kerala SDMA 2024',
    center: [11.6, 76.0],
    bbox: [11.3, 75.7, 11.9, 76.4],
    zoom: 11,
    population: 817420,
    households: 218000,
    areas: [
      'Kalpetta','Mananthavady','Sulthan Bathery','Vythiri',
      'Ambalavayal','Panamaram','Meenangadi','Nenmeni',
      'Mundakkai','Chooralmala','Meppadi','Pulpally',
    ],
    floodZonesHigh:   ['Mundakkai','Chooralmala','Meppadi'],
    floodZonesMedium: ['Kalpetta','Vythiri','Panamaram'],
    floodZonesLow:    ['Mananthavady','Sulthan Bathery','Ambalavayal','Meenangadi','Nenmeni','Pulpally'],
    cycloneTrack: [
      { lat: 10.8, lng: 76.2, wind_kmh: 60,  hours_out: 48 },
      { lat: 11.1, lng: 76.0, wind_kmh: 80,  hours_out: 36 },
      { lat: 11.4, lng: 75.9, wind_kmh: 95,  hours_out: 24 },
      { lat: 11.6, lng: 76.0, wind_kmh: 100, hours_out: 12 },
      { lat: 11.8, lng: 76.1, wind_kmh: 90,  hours_out: 6  },
    ],
    maxWindKmh: 100,
    cycloneName: 'MONSOON FLOOD',
    cycloneCategory: 'Extreme Rainfall + Flash Flood',
    radiusKm: 80,
    landfallEtaH: 48,
    safeSpaces: [
      { id: 'SS-001', name: 'Kalpetta Govt College',    lat: 11.608, lng: 76.082, capacity: 600 },
      { id: 'SS-002', name: 'Sulthan Bathery Stadium',  lat: 11.668, lng: 76.259, capacity: 450 },
      { id: 'SS-003', name: 'Mananthavady School',      lat: 11.804, lng: 76.001, capacity: 400 },
      { id: 'SS-004', name: 'Vythiri Resort Ground',    lat: 11.554, lng: 75.995, capacity: 300 },
    ],
  },
  VZG: {
    key: 'VZG',
    name: 'Visakhapatnam, Andhra Pradesh',
    event: 'Cyclone Hudhud + Flooding (Oct 2014)',
    eventType: 'Very Severe Cyclonic Storm',
    eventYear: 2014,
    damageCr: 21908,
    homesDamaged: 330000,
    deaths: 61,
    source: 'NOAA IBTrACS / ANDMA 2014',
    center: [17.7, 83.3],
    bbox: [17.4, 83.0, 18.0, 83.6],
    zoom: 11,
    population: 2035922,
    households: 530000,
    areas: [
      'Gajuwaka','Seethammadhara','Dwaraka Nagar','MVP Colony',
      'Madhurawada','Rushikonda','Bheemunipatnam','Kommadi',
      'Pendurthi','Kapuluppada','Ukkunagaram','Pedagantyada',
    ],
    floodZonesHigh:   ['Gajuwaka','Rushikonda','Bheemunipatnam'],
    floodZonesMedium: ['Dwaraka Nagar','MVP Colony','Madhurawada'],
    floodZonesLow:    ['Seethammadhara','Kommadi','Pendurthi','Kapuluppada','Ukkunagaram','Pedagantyada'],
    cycloneTrack: [
      { lat: 15.5, lng: 84.5, wind_kmh: 140, hours_out: 48 },
      { lat: 16.2, lng: 84.1, wind_kmh: 180, hours_out: 36 },
      { lat: 16.8, lng: 83.8, wind_kmh: 210, hours_out: 24 },
      { lat: 17.4, lng: 83.5, wind_kmh: 225, hours_out: 12 },
      { lat: 17.7, lng: 83.3, wind_kmh: 200, hours_out: 6  },
    ],
    maxWindKmh: 225,
    cycloneName: 'HUDHUD',
    cycloneCategory: 'Very Severe Cyclonic Storm',
    radiusKm: 130,
    landfallEtaH: 48,
    safeSpaces: [
      { id: 'SS-001', name: 'GITAM University Ground',    lat: 17.745, lng: 83.355, capacity: 800 },
      { id: 'SS-002', name: 'MVP Colony Sports Complex',  lat: 17.738, lng: 83.316, capacity: 500 },
      { id: 'SS-003', name: 'Pendurthi Multipurpose Hall',lat: 17.810, lng: 83.237, capacity: 400 },
      { id: 'SS-004', name: 'Gajuwaka Civic Centre',      lat: 17.673, lng: 83.222, capacity: 600 },
    ],
  },
};

export const BASE_RESOURCES = {
  baby_formula_units: 250,
  elderly_medicine_packs: 180,
  water_liters: 8000,
  food_rations: 700,
  wheelchair_spaces: 30,
  oxygen_cylinders: 20,
  generator_kw: 15,
  medical_kits: 50,
};

export const CONSTRUCTION_TYPES   = ['brick_mortar','concrete_frame','load_bearing_masonry','wood_frame','steel_frame'];
export const CONSTRUCTION_WEIGHTS = [0.40, 0.30, 0.15, 0.10, 0.05];
export const ROOF_TYPES   = ['terracotta_tile','rcc_slab','asbestos_sheet','metal_sheet','thatched'];
export const ROOF_WEIGHTS = [0.35, 0.30, 0.15, 0.12, 0.08];
export const FLOOD_ZONES  = ['Zone_A','Zone_B','Zone_C'];

export const ROAD_NAMES = [
  'Main Road','Cross Street','Bazaar Road','Tank Road',
  'Temple Street','Gandhi Road','Nehru Street','Anna Salai',
  'Rajaji Road','MG Road','Beach Road','Market Street',
];

export const FIRST_NAMES = [
  'Ramesh','Suresh','Priya','Kavitha','Arjun','Deepa','Karthik','Meena',
  'Vijay','Anita','Murugan','Lalitha','Senthil','Rekha','Bala','Usha',
  'Rajan','Geetha','Arun','Sujatha','Ganesh','Hema','Dinesh','Padma',
  'Vinod','Saranya','Kumar','Nirmala','Selvam','Radha','Ashok','Sumathi',
  'Venkat','Kamala','Siva','Malathi','Mani','Thenmozhi','Ravi','Vasantha',
  'Muthu','Vijayalakshmi','Mohan','Saraswathi','Gopi','Ambika','Sundar','Chitra',
];
export const LAST_NAMES = [
  'Krishnan','Rajan','Murugesan','Chandrasekaran','Subramaniam','Venkataraman',
  'Narayanan','Balasubramanian','Ramaswamy','Sundaram','Iyer','Pillai',
  'Nair','Menon','Sharma','Patel','Reddy','Rao','Kumar','Singh',
  'Pandian','Natarajan','Thirumaran','Selvakumar','Arumugam','Palanivel',
];
