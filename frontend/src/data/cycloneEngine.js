// Cyclone simulation engine — ported from notebook Cell 3
// Vectorised distance + probabilistic risk scoring for 50K property twins

function haversineKm(lat1, lng1, lat2, lng2) {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLng = ((lng2 - lng1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.asin(Math.sqrt(Math.max(0, a)));
}

export function runSimulation(twins, cyclone) {
  const maxWind  = cyclone.max_wind_kmh;
  const radiusKm = cyclone.radius_km;

  return twins.map(twin => {
    // Min distance to any track waypoint
    let minDist = Infinity;
    for (const wp of cyclone.track) {
      const d = haversineKm(twin.lat, twin.lng, wp.lat, wp.lng);
      if (d < minDist) minDist = d;
    }

    const windFactor =
      minDist <= radiusKm
        ? 1.0 - (minDist / radiusKm) * 0.4
        : Math.max(0, 0.6 - (minDist - radiusKm) / 200);

    const prob = Math.min(
      twin.vulnerability_index * windFactor * (maxWind / 200) * 1.8,
      0.99,
    );

    const risk_color =
      prob >= 0.70 ? 'red' :
      prob >= 0.45 ? 'orange' :
      prob >= 0.20 ? 'yellow' : 'green';

    return {
      ...twin,
      dist_from_storm_km:   parseFloat(minDist.toFixed(2)),
      claim_probability:    parseFloat(prob.toFixed(4)),
      expected_loss_inr:    Math.round(prob * twin.sum_insured_inr * 0.45),
      risk_color,
    };
  });
}

// Safe space assignment (nearest safe shelter within max_km)
export function assignSafeSpaces(twins, safeSpaces, maxKm = 15) {
  return twins.map(twin => {
    if (twin.risk_color !== 'red') return { ...twin, ss_id: null, ss_name: null, ss_dist_km: null };
    let bestId = null, bestName = null, bestDist = Infinity;
    for (const ss of safeSpaces) {
      const d = haversineKm(twin.lat, twin.lng, ss.lat, ss.lng);
      if (d < bestDist && d <= maxKm) {
        bestDist = d;
        bestId   = ss.id;
        bestName = ss.name;
      }
    }
    return {
      ...twin,
      ss_id:       bestId,
      ss_name:     bestName,
      ss_dist_km:  bestId ? parseFloat(bestDist.toFixed(2)) : null,
    };
  });
}

// Build per-safe-space report (capacity %, resource adequacy)
export function buildSafeSpaceReport(simulatedTwins, safeSpaces, baseResources) {
  const report = {};
  for (const ss of safeSpaces) {
    const assigned = simulatedTwins.filter(t => t.ss_id === ss.id);
    const infantCount   = assigned.filter(t => t.has_infants).length;
    const elderlyCount  = assigned.filter(t => t.has_elderly).length;
    const disabledCount = assigned.filter(t => t.has_disabled).length;
    const occupancy     = assigned.length;
    const capPct        = (occupancy / ss.capacity) * 100;

    const resources = { ...baseResources };
    const adequacy  = {};
    adequacy.baby_formula_units      = infantCount  * 5 > resources.baby_formula_units    ? 'SHORTAGE' : 'OK';
    adequacy.elderly_medicine_packs  = elderlyCount * 2 > resources.elderly_medicine_packs ? 'SHORTAGE' : 'OK';
    adequacy.wheelchair_spaces       = disabledCount   > resources.wheelchair_spaces       ? 'SHORTAGE' : 'OK';
    adequacy.water_liters            = occupancy * 10  > resources.water_liters            ? 'SHORTAGE' : 'OK';
    adequacy.food_rations            = occupancy       > resources.food_rations            ? 'SHORTAGE' : 'OK';

    report[ss.id] = {
      ss_id:          ss.id,
      ss_name:        ss.name,
      occupancy,
      capacity:       ss.capacity,
      cap_pct:        parseFloat(capPct.toFixed(1)),
      infant_count:   infantCount,
      elderly_count:  elderlyCount,
      disabled_count: disabledCount,
      resources,
      adequacy,
      shortages:      Object.entries(adequacy).filter(([, v]) => v === 'SHORTAGE').map(([k]) => k),
    };
  }
  return report;
}

export function makeCycloneParams(loc) {
  return {
    name:           loc.cycloneName,
    category:       loc.cycloneCategory,
    max_wind_kmh:   loc.maxWindKmh,
    landfall_eta_h: loc.landfallEtaH,
    radius_km:      loc.radiusKm,
    track:          loc.cycloneTrack,
  };
}

export function shiftTrack(baseTrack, shiftKm) {
  const degPerKm = 1 / 111;
  return baseTrack.map(wp => ({
    ...wp,
    lat: parseFloat((wp.lat + shiftKm * degPerKm).toFixed(5)),
  }));
}
