import { useMemo, useState, useEffect } from 'react';
import { useIDTCC } from '../../context/IDTCCContext.jsx';

const COLOR_MAP  = { red: '#DC2626', orange: '#EA580C', yellow: '#CA8A04', green: '#16A34A' };
const RADIUS_MAP = { red: 5, orange: 4, yellow: 3, green: 2 };
const SAMPLE_CAP = { red: null, orange: null, yellow: 1000, green: 500 };

let leafletLoaded = false;

function sampleTwins(twins) {
  const groups = { red: [], orange: [], yellow: [], green: [] };
  for (const t of twins) groups[t.risk_color]?.push(t);
  const sampled = [];
  for (const [level, cap] of Object.entries(SAMPLE_CAP)) {
    const g = groups[level];
    if (!cap || g.length <= cap) sampled.push(...g);
    else {
      const step = Math.floor(g.length / cap);
      for (let i = 0; i < g.length && sampled.length < sampled.length + cap; i += step) sampled.push(g[i]);
    }
  }
  return sampled;
}

export default function LiveMap() {
  const { twins, cycloneParams, loc } = useIDTCC();
  const [mapReady, setMapReady] = useState(false);
  const [mapMode, setMapMode]   = useState('dots'); // dots | heatmap
  const [mapRef, setMapRef]     = useState(null);

  const sampledTwins = useMemo(() => twins ? sampleTwins(twins) : [], [twins]);
  const center       = loc?.center ?? [13.0827, 80.2707];

  useEffect(() => {
    if (!twins || mapReady) return;
    const timer = setTimeout(() => setMapReady(true), 100);
    return () => clearTimeout(timer);
  }, [twins]);

  useEffect(() => {
    if (!mapReady) return;
    let L, map, markersGroup;

    import('leaflet').then(mod => {
      L = mod.default;

      // Fix default icon
      delete L.Icon.Default.prototype._getIconUrl;
      L.Icon.Default.mergeOptions({ iconRetinaUrl: '', iconUrl: '', shadowUrl: '' });

      const container = document.getElementById('idtcc-map');
      if (!container || container._leaflet_id) return;

      map = L.map(container, {
        center,
        zoom: loc?.zoom ?? 11,
        zoomControl: true,
        attributionControl: false,
      });

      L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        maxZoom: 19,
      }).addTo(map);

      setMapRef({ L, map });
    });

    return () => {
      const container = document.getElementById('idtcc-map');
      if (container?._leaflet_id && map) map.remove();
    };
  }, [mapReady]);

  useEffect(() => {
    if (!mapRef || !sampledTwins.length) return;
    const { L, map } = mapRef;

    // Clear existing layers (except tile)
    map.eachLayer(layer => {
      if (layer instanceof L.CircleMarker || layer instanceof L.Polyline || layer instanceof L.Circle) {
        map.removeLayer(layer);
      }
    });

    if (mapMode === 'dots') {
      // Render sampled dots
      const renderer = L.canvas({ padding: 0.5 });
      for (const t of sampledTwins) {
        L.circleMarker([t.lat, t.lng], {
          radius:      RADIUS_MAP[t.risk_color],
          color:       COLOR_MAP[t.risk_color],
          fillColor:   COLOR_MAP[t.risk_color],
          fillOpacity: 0.75,
          weight:      0,
          renderer,
        })
        .bindPopup(
          `<b style="font-size:13px">${t.twin_id}</b><br>` +
          `${t.address}<br>` +
          `<span style="color:#aaa">Built ${t.year_built} · ${t.construction_type.replace(/_/g,' ')}</span><br>` +
          `Elev: ${t.floor_elevation_m}m · ${t.flood_zone}<br>` +
          `<b style="color:${COLOR_MAP[t.risk_color]}">Claim prob: ${(t.claim_probability*100).toFixed(0)}%</b><br>` +
          `Expected loss: ₹${(t.expected_loss_inr/100000).toFixed(1)}L`,
          { maxWidth: 260 }
        )
        .addTo(map);
      }
    }

    // Storm track
    if (cycloneParams) {
      const trackCoords = cycloneParams.track.map(wp => [wp.lat, wp.lng]);
      L.polyline(trackCoords, {
        color: '#60A5FA', weight: 3, opacity: 0.9, dashArray: '8 4',
      }).addTo(map).bindTooltip(`Cyclone ${cycloneParams.name} Track`);

      // Waypoints
      for (const wp of cycloneParams.track) {
        L.circleMarker([wp.lat, wp.lng], {
          radius: 5, color: '#93C5FD', fillColor: '#DBEAFE', fillOpacity: 1, weight: 2,
        })
        .addTo(map)
        .bindTooltip(`T-${wp.hours_out}h · ${wp.wind_kmh} km/h`);
      }

      // Impact circle around last waypoint
      const lf = cycloneParams.track[cycloneParams.track.length - 1];
      L.circle([lf.lat, lf.lng], {
        radius: cycloneParams.radius_km * 1000,
        color: '#60A5FA', weight: 1.5, fill: true, fillOpacity: 0.05,
      }).addTo(map);
    }
  }, [mapRef, sampledTwins, mapMode, cycloneParams]);

  const counts = useMemo(() => {
    if (!twins) return {};
    const c = { red: 0, orange: 0, yellow: 0, green: 0 };
    for (const t of twins) c[t.risk_color]++;
    return c;
  }, [twins]);

  return (
    <div style={{ height: 'calc(100vh - 130px)', display: 'flex', flexDirection: 'column' }}>
      {/* Map toolbar */}
      <div style={{
        background: '#0d0d0d', borderBottom: '1px solid #3c3c3c',
        padding: '12px 24px', display: 'flex', alignItems: 'center', gap: 24, flexWrap: 'wrap',
      }}>
        <span className="label-upper" style={{ color: '#7e7e7e' }}>
          {cycloneParams?.name} · {sampledTwins.length.toLocaleString('en-IN')} pins displayed
        </span>

        {/* Mode toggle */}
        <div style={{ display: 'flex', gap: 4 }}>
          {['dots', 'heatmap'].map(m => (
            <button key={m} onClick={() => setMapMode(m)}
              style={{
                background: mapMode === m ? '#fff' : 'transparent',
                color: mapMode === m ? '#000' : '#bbb',
                border: '1px solid #3c3c3c', padding: '4px 14px',
                fontSize: 12, fontWeight: 700, letterSpacing: 1.2, textTransform: 'uppercase',
                cursor: 'pointer', borderRadius: 0, fontFamily: 'Inter,sans-serif',
              }}>
              {m}
            </button>
          ))}
        </div>

        {/* Legend */}
        <div style={{ display: 'flex', gap: 16, marginLeft: 'auto' }}>
          {Object.entries(COLOR_MAP).map(([level, color]) => (
            <div key={level} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <div style={{ width: 10, height: 10, borderRadius: '50%', background: color }} />
              <span style={{ fontSize: 12, color: '#bbbbbb', textTransform: 'capitalize' }}>
                {level} ({counts[level]?.toLocaleString('en-IN') ?? 0})
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Map container */}
      <div style={{ flex: 1, position: 'relative' }}>
        {!mapReady && (
          <div style={{
            position: 'absolute', inset: 0, background: '#111',
            display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 10,
          }}>
            <div className="spinner" />
          </div>
        )}
        <div id="idtcc-map" style={{ width: '100%', height: '100%' }} />

        {/* Attribution overlay */}
        <div style={{
          position: 'absolute', bottom: 12, left: 12, zIndex: 1000,
          background: 'rgba(0,0,0,0.75)', padding: '8px 12px',
          border: '1px solid #3c3c3c', fontSize: 11, color: '#7e7e7e',
        }}>
          <strong style={{ color: '#fff' }}>IDTCC Live Map</strong><br />
          50,000 property digital twins · CartoDB Dark Matter
        </div>
      </div>
    </div>
  );
}
