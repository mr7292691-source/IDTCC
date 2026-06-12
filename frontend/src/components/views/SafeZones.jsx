import { useEffect, useState, useMemo } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Cell,
} from 'recharts';
import { useIDTCC } from '../../context/IDTCCContext.jsx';

const TOOLTIP_STYLE = {
  contentStyle: { background: '#1a1a1a', border: '1px solid #3c3c3c', borderRadius: 0, color: '#fff' },
  labelStyle:   { color: '#bbbbbb', fontSize: 12 },
  itemStyle:    { color: '#e6e6e6', fontSize: 13 },
};

export default function SafeZones() {
  const { twins, safeSpaces, ssReport, loc } = useIDTCC();
  const [mapReady, setMapReady] = useState(false);
  const [mapRef, setMapRef]     = useState(null);

  const critical = useMemo(() => twins ? twins.filter(t => t.risk_color === 'red') : [], [twins]);
  const vuln = useMemo(() => critical.filter(t => t.social_vuln > 0), [critical]);
  const ssData = useMemo(() => safeSpaces ? safeSpaces.map(ss => {
    const rep = ssReport?.[ss.id] ?? {};
    return { ...ss, ...rep };
  }) : [], [safeSpaces, ssReport]);

  // KPIs
  const totalVuln      = vuln.length;
  const infantCount    = twins ? twins.filter(t => t.has_infants && t.risk_color === 'red').length : 0;
  const elderlyCount   = twins ? twins.filter(t => t.has_elderly && t.risk_color === 'red').length : 0;
  const disabledCount  = twins ? twins.filter(t => t.has_disabled && t.risk_color === 'red').length : 0;
  const shelterCoverage= critical.length ? (critical.filter(t => t.ss_id).length / critical.length * 100).toFixed(1) : 0;

  // Resource adequacy chart
  const resourceChart = ssData.map(ss => ({
    name: ss.name?.split(' ').slice(0, 2).join(' ') ?? ss.id,
    cap_pct: ss.cap_pct ?? 0,
    shortages: ss.shortages?.length ?? 0,
  }));

  useEffect(() => {
    if (!twins || mapReady) return;
    const t = setTimeout(() => setMapReady(true), 100);
    return () => clearTimeout(t);
  }, [twins]);

  useEffect(() => {
    if (!mapReady) return;
    let map;
    import('leaflet').then(({ default: L }) => {
      delete L.Icon.Default.prototype._getIconUrl;
      L.Icon.Default.mergeOptions({ iconRetinaUrl: '', iconUrl: '', shadowUrl: '' });

      const container = document.getElementById('safe-zone-map');
      if (!container || container._leaflet_id) return;

      const center = loc?.center ?? [13.0, 80.2];
      map = L.map(container, { center, zoom: loc?.zoom ?? 11, zoomControl: true, attributionControl: false });
      L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', { maxZoom: 19 }).addTo(map);

      const renderer = L.canvas({ padding: 0.5 });

      // Vulnerable twins (sample 2000 for perf)
      const vulnSample = vuln.slice(0, 2000);
      for (const t of vulnSample) {
        const col = t.has_infants ? '#F59E0B' : '#8B5CF6';
        L.circleMarker([t.lat, t.lng], {
          radius: 2, color: col, fillColor: col, fillOpacity: 0.55, weight: 0, renderer,
        })
        .bindTooltip(`Infant:${t.has_infants} Elderly:${t.has_elderly} — ${t.area}`)
        .addTo(map);
      }

      // Safe spaces
      for (const ss of ssData) {
        const capPct = ss.cap_pct ?? 0;
        const col = capPct > 100 ? '#DC2626' : capPct > 60 ? '#EA580C' : '#16A34A';
        const shorts = ss.shortages ?? [];
        const popHtml =
          `<b style="font-size:13px">${ss.name}</b><br>` +
          `Capacity: ${capPct.toFixed(0)}% (${ss.occupancy ?? 0}/${ss.capacity})<br>` +
          `Medical team: ${ss.has_medical_team ? 'Yes' : 'No'}<br>` +
          (shorts.length
            ? `<span style="color:#F59E0B">⚠ Shortage: ${shorts.join(', ')}</span>`
            : `<span style="color:#16A34A">✓ Resources OK</span>`);

        L.circleMarker([ss.lat, ss.lng], {
          radius: 14, color: col, fillColor: col, fillOpacity: 0.75, weight: 3,
        })
        .bindPopup(popHtml, { maxWidth: 280 })
        .bindTooltip(ss.name)
        .addTo(map);

        // Evacuation lines to sample of assigned critical twins
        const assigned = critical.filter(t => t.ss_id === ss.id).slice(0, 30);
        for (const t of assigned) {
          L.polyline([[t.lat, t.lng], [ss.lat, ss.lng]], {
            color: '#fff', weight: 0.5, opacity: 0.15,
          }).addTo(map);
        }
      }

      setMapRef(map);
    });

    return () => {
      const container = document.getElementById('safe-zone-map');
      if (container?._leaflet_id && map) map.remove();
    };
  }, [mapReady]);

  return (
    <div style={{ maxWidth: 1440, margin: '0 auto', padding: '48px 24px' }}>
      <div style={{ marginBottom: 40 }}>
        <div className="m-stripe" style={{ width: 48, marginBottom: 12 }} />
        <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 4 }}>Humanitarian Response</div>
        <h2 className="display-sm">Safe Zones & Vulnerable Population</h2>
      </div>

      {/* KPIs */}
      <div className="grid-4" style={{ marginBottom: 40 }}>
        <div className="spec-cell">
          <div className="spec-cell__value" style={{ color: '#F59E0B' }}>{totalVuln.toLocaleString('en-IN')}</div>
          <div className="spec-cell__label">Vulnerable in Red Zone</div>
        </div>
        <div className="spec-cell">
          <div className="spec-cell__value" style={{ color: '#F59E0B' }}>{infantCount.toLocaleString('en-IN')}</div>
          <div className="spec-cell__label">Infant Households</div>
          <div className="caption">red zone only</div>
        </div>
        <div className="spec-cell">
          <div className="spec-cell__value" style={{ color: '#8B5CF6' }}>{elderlyCount.toLocaleString('en-IN')}</div>
          <div className="spec-cell__label">Elderly Households</div>
          <div className="caption">Census 2011 calibrated</div>
        </div>
        <div className="spec-cell">
          <div className="spec-cell__value" style={{ color: '#22C55E' }}>{shelterCoverage}%</div>
          <div className="spec-cell__label">Shelter Coverage</div>
          <div className="caption">{safeSpaces?.length ?? 0} safe spaces active</div>
        </div>
      </div>

      {/* Map */}
      <div style={{ marginBottom: 40, position: 'relative' }}>
        <div style={{ background: '#0d0d0d', border: '1px solid #3c3c3c', padding: '12px 16px', marginBottom: 0,
          display: 'flex', gap: 24, flexWrap: 'wrap', alignItems: 'center' }}>
          <span className="label-upper" style={{ color: '#7e7e7e' }}>Evacuation Map — {vuln.length.toLocaleString('en-IN')} vulnerable twins</span>
          <div style={{ display: 'flex', gap: 16, marginLeft: 'auto' }}>
            {[
              { color: '#F59E0B', label: 'Infant household' },
              { color: '#8B5CF6', label: 'Elderly household' },
              { color: '#16A34A', label: 'Safe space (<60%)' },
              { color: '#EA580C', label: 'Safe space (60-100%)' },
              { color: '#DC2626', label: 'Safe space (overcapacity)' },
            ].map(l => (
              <div key={l.label} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                <div style={{ width: 10, height: 10, borderRadius: '50%', background: l.color }} />
                <span style={{ fontSize: 11, color: '#bbbbbb' }}>{l.label}</span>
              </div>
            ))}
          </div>
        </div>
        <div id="safe-zone-map" style={{ width: '100%', height: 450, background: '#111' }}>
          {!mapReady && (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
              <div className="spinner" />
            </div>
          )}
        </div>
      </div>

      {/* Resource adequacy chart */}
      <div className="grid-2" style={{ marginBottom: 40 }}>
        <div className="card">
          <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 16 }}>Safe Space Capacity %</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={resourceChart} barCategoryGap="30%">
              <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
              <XAxis dataKey="name" tick={{ fill: '#bbbbbb', fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#bbbbbb', fontSize: 11 }} axisLine={false} tickLine={false}
                tickFormatter={v => `${v}%`} />
              <Tooltip {...TOOLTIP_STYLE} formatter={v => [`${v}%`, 'Capacity Used']} />
              <Bar dataKey="cap_pct" radius={[0,0,0,0]}>
                {resourceChart.map((d, i) => (
                  <Cell key={i} fill={d.cap_pct > 100 ? '#DC2626' : d.cap_pct > 60 ? '#EA580C' : '#16A34A'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 16 }}>Safe Space Resource Report</div>
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr><th>Shelter</th><th>Occupancy</th><th>Cap%</th><th>Shortages</th></tr>
              </thead>
              <tbody>
                {ssData.map(ss => (
                  <tr key={ss.id}>
                    <td style={{ fontSize: 12 }}>{ss.name}</td>
                    <td>{ss.occupancy ?? 0} / {ss.capacity}</td>
                    <td>
                      <span className={`badge badge-${(ss.cap_pct ?? 0) > 100 ? 'red' : (ss.cap_pct ?? 0) > 60 ? 'orange' : 'green'}`}>
                        {(ss.cap_pct ?? 0).toFixed(0)}%
                      </span>
                    </td>
                    <td>
                      {(ss.shortages?.length ?? 0) === 0
                        ? <span style={{ color: '#22C55E', fontSize: 12 }}>OK</span>
                        : <span style={{ color: '#F59E0B', fontSize: 12 }}>{ss.shortages?.join(', ')}</span>
                      }
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Vulnerable coverage summary */}
      <div className="card">
        <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 16 }}>Demographic Coverage Summary</div>
        {[
          { label: 'Infant households assigned shelter', count: twins ? twins.filter(t => t.has_infants && t.ss_id).length : 0, total: infantCount, color: '#F59E0B' },
          { label: 'Elderly households assigned shelter', count: twins ? twins.filter(t => t.has_elderly && t.ss_id).length : 0, total: elderlyCount, color: '#8B5CF6' },
          { label: 'Disabled households assigned shelter', count: twins ? twins.filter(t => t.has_disabled && t.ss_id).length : 0, total: disabledCount, color: '#3B82F6' },
        ].map(m => {
          const pct = m.total ? (m.count / m.total * 100).toFixed(1) : 0;
          return (
            <div key={m.label} style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                <span className="body-sm">{m.label}</span>
                <span className="body-sm">{m.count.toLocaleString('en-IN')} / {m.total.toLocaleString('en-IN')} ({pct}%)</span>
              </div>
              <div style={{ height: 4, background: '#262626' }}>
                <div style={{ width: `${Math.min(100, pct)}%`, height: '100%', background: m.color }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
