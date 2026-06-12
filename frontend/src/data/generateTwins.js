// Property twin generation — ported from notebook Cell 2
// 50,000 synthetic property digital twins seeded for reproducibility

import {
  mulberry32, weightedChoice, randInt, randFloat,
} from './seededRandom.js';
import {
  CONSTRUCTION_TYPES, CONSTRUCTION_WEIGHTS,
  ROOF_TYPES, ROOF_WEIGHTS,
  FLOOD_ZONES,
  ROAD_NAMES, FIRST_NAMES, LAST_NAMES,
} from './locationCatalogue.js';

const FLOOD_ZONE_MAP = { Zone_A: 0, Zone_B: 1, Zone_C: 2 };

function floodZoneForArea(area, loc) {
  if (loc.floodZonesHigh.includes(area))   return 'Zone_A';
  if (loc.floodZonesMedium.includes(area)) return 'Zone_B';
  return 'Zone_C';
}

function computeVulnerability(twin) {
  let s = 0;
  s += Math.max(0, (2 - twin.floor_elevation_m) / 2) * 0.30;
  const fz = { Zone_A: 0.9, Zone_B: 0.5, Zone_C: 0.2 };
  s += (fz[twin.flood_zone] ?? 0.5) * 0.25;
  s += Math.max(0, (3 - twin.proximity_water_km) / 3) * 0.20;
  s += Math.min((2024 - twin.year_built) / 80, 1) * 0.15;
  const ct = {
    wood_frame: 0.9, thatched: 1.0, asbestos_sheet: 0.7,
    brick_mortar: 0.5, load_bearing_masonry: 0.4,
    concrete_frame: 0.2, steel_frame: 0.1,
  };
  s += (ct[twin.construction_type] ?? 0.5) * 0.10;
  return Math.min(Math.max(s, 0.01), 0.99);
}

function yearWeights(range) {
  return range.map(y => (y < 1970 ? 1 : y < 1990 ? 2 : y < 2010 ? 3 : 2));
}

function makeName(rng) {
  const first = FIRST_NAMES[Math.floor(rng() * FIRST_NAMES.length)];
  const last  = LAST_NAMES[Math.floor(rng() * LAST_NAMES.length)];
  return `${first} ${last}`;
}

function latLngForArea(rng, area, loc) {
  const [latMin, lngMin, latMax, lngMax] = loc.bbox;
  // Slight area-based bias within bbox
  const areaIdx = loc.areas.indexOf(area);
  const cols = 5;
  const col = areaIdx % cols;
  const row = Math.floor(areaIdx / cols);
  const latRange = latMax - latMin;
  const lngRange = lngMax - lngMin;
  const sectorW = lngRange / cols;
  const sectorH = latRange / Math.ceil(loc.areas.length / cols);
  const baseLat = latMin + row * sectorH;
  const baseLng = lngMin + col * sectorW;
  return {
    lat: parseFloat((baseLat + rng() * sectorH).toFixed(6)),
    lng: parseFloat((baseLng + rng() * sectorW).toFixed(6)),
  };
}

export function generateTwins(loc, count = 50000) {
  const rng = mulberry32(42);
  const rngNames = mulberry32(1234);
  const rngVuln = mulberry32(99);

  const yearRange = [];
  for (let y = 1940; y <= 2023; y++) yearRange.push(y);
  const yrWts = yearWeights(yearRange);
  const yrTotal = yrWts.reduce((a, b) => a + b, 0);

  const twins = [];

  for (let i = 0; i < count; i++) {
    const area = loc.areas[Math.floor(rng() * loc.areas.length)];
    const { lat, lng } = latLngForArea(rng, area, loc);
    const construction_type = weightedChoice(rng, CONSTRUCTION_TYPES, CONSTRUCTION_WEIGHTS);
    const roof_type         = weightedChoice(rng, ROOF_TYPES, ROOF_WEIGHTS);
    const flood_zone        = floodZoneForArea(area, loc);

    // Year built — weighted distribution
    let yr = rng() * yrTotal;
    let year_built = yearRange[0];
    for (let k = 0; k < yearRange.length; k++) {
      yr -= yrWts[k];
      if (yr <= 0) { year_built = yearRange[k]; break; }
    }

    // Floor elevation: Zone_A lower, Zone_C higher
    const elevBase = flood_zone === 'Zone_A' ? 0.3 : flood_zone === 'Zone_B' ? 1.0 : 2.0;
    const floor_elevation_m = parseFloat((elevBase + rng() * 3.0).toFixed(2));

    // Water proximity: Zone_A closest
    const waterBase = flood_zone === 'Zone_A' ? 0.1 : flood_zone === 'Zone_B' ? 0.5 : 1.5;
    const proximity_water_km = parseFloat((waterBase + rng() * 3.0).toFixed(3));

    // Sum insured
    const si_base = construction_type === 'concrete_frame' || construction_type === 'steel_frame' ? 3000000 : 1200000;
    const sum_insured_inr = Math.round((si_base + rng() * 7000000) / 50000) * 50000;

    // Prior claims
    const has_prior_claim  = rngVuln() < 0.20;
    const prior_claim_year = has_prior_claim ? randInt(rngVuln, 2018, 2023) : null;
    const prior_fraud_flag = has_prior_claim && rngVuln() < 0.05;

    const twin = {
      twin_id:            `${loc.key}-${String(i + 1).padStart(5, '0')}`,
      lat, lng,
      address:            `${randInt(rng, 1, 999)} ${ROAD_NAMES[Math.floor(rng() * ROAD_NAMES.length)]}, ${area}, ${loc.name.split(',')[0]}`,
      area,
      construction_type,
      roof_type,
      flood_zone,
      year_built,
      floor_elevation_m,
      proximity_water_km,
      sum_insured_inr,
      policyholder:       makeName(rngNames),
      policy_id:          `POL-${year_built + Math.floor(rngNames() * 10)}-${String(i + 1).padStart(5, '0')}`,
      has_prior_claim,
      prior_claim_year,
      prior_fraud_flag,
    };

    twin.vulnerability_index = parseFloat(computeVulnerability(twin).toFixed(3));

    // Vulnerable population (Census 2011 calibrated)
    twin.has_infants  = rngVuln() < 0.10;
    twin.has_elderly  = rngVuln() < 0.28;
    twin.has_disabled = rngVuln() < 0.08;
    twin.social_vuln  = parseFloat((
      (twin.has_infants  ? 0.40 : 0) +
      (twin.has_elderly  ? 0.35 : 0) +
      (twin.has_disabled ? 0.25 : 0)
    ).toFixed(2));

    // Decade label
    twin.decade = `${Math.floor(year_built / 10) * 10}s`;

    twins.push(twin);
  }

  return twins;
}
