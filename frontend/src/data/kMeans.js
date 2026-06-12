// Simple k-means clustering for adjuster zone planning
// Seeds centroids by evenly sampling input points

export function kMeans(points, k, maxIter = 100) {
  if (points.length === 0 || k <= 0) return { centroids: [], assignments: [] };
  k = Math.min(k, points.length);

  // Initialise centroids by strided sampling (deterministic)
  const stride = Math.floor(points.length / k);
  let centroids = Array.from({ length: k }, (_, i) => ({
    lat: points[i * stride].lat,
    lng: points[i * stride].lng,
  }));

  let assignments = new Array(points.length).fill(0);

  for (let iter = 0; iter < maxIter; iter++) {
    // Assign step
    let changed = false;
    for (let pi = 0; pi < points.length; pi++) {
      let minDist = Infinity, minIdx = 0;
      for (let ci = 0; ci < k; ci++) {
        const d =
          (points[pi].lat - centroids[ci].lat) ** 2 +
          (points[pi].lng - centroids[ci].lng) ** 2;
        if (d < minDist) { minDist = d; minIdx = ci; }
      }
      if (assignments[pi] !== minIdx) { assignments[pi] = minIdx; changed = true; }
    }

    // Update centroids
    const sums = Array.from({ length: k }, () => ({ lat: 0, lng: 0, count: 0 }));
    for (let pi = 0; pi < points.length; pi++) {
      const ci = assignments[pi];
      sums[ci].lat   += points[pi].lat;
      sums[ci].lng   += points[pi].lng;
      sums[ci].count += 1;
    }
    centroids = sums.map((s, i) =>
      s.count > 0
        ? { lat: s.lat / s.count, lng: s.lng / s.count }
        : centroids[i],
    );

    if (!changed) break;
  }

  return { centroids, assignments };
}
