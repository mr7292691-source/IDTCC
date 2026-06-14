import { useEffect, useRef, useState } from 'react';
import { useIDTCC } from '../../context/IDTCCContext.jsx';
import api from '../../api/client.js';

// Maps a LangGraph node name → the agent output key it writes + a display label.
const AGENT_FLOW = [
  { node: 'ingest',               label: 'Ingest Twins',        layer: 'Substrate' },
  { node: 'sensor_agent',         label: 'Sensor Intelligence', key: 'sensor_output',         layer: 'L1' },
  { node: 'infrastructure_agent', label: 'Infrastructure Risk', key: 'infrastructure_output', layer: 'L2' },
  { node: 'damage_agent',         label: 'Damage Assessment',   key: 'damage_output',         layer: 'L2' },
  { node: 'vulnerable_agent',     label: 'Vulnerable Pop.',     key: 'vulnerable_output',     layer: 'L3' },
  { node: 'shelter_agent',        label: 'Shelter Allocation',  key: 'shelter_output',        layer: 'L4' },
  { node: 'evacuation_agent',     label: 'Evacuation Plan',     key: 'evacuation_output',     layer: 'L4' },
  { node: 'rescue_agent',         label: 'Rescue Priority',     key: 'rescue_output',         layer: 'L4' },
  { node: 'judge_agent',          label: 'LLM Judge',           key: 'judge_scores',          layer: 'L6' },
  { node: 'assemble',             label: 'Assemble Plan',       key: 'response_plan',         layer: 'L6' },
  { node: 'dispatch_alerts',      label: 'Alert Dispatch',      key: 'dispatched_alerts',     layer: 'L7' },
];

const PRIORITY_COLOR = { critical: '#DC2626', high: '#EA580C', medium: '#F59E0B', low: '#16A34A' };
const fmt = (n) => (n ?? 0).toLocaleString('en-IN');

function Kpi({ value, label, sub, color }) {
  return (
    <div className="spec-cell">
      <div className="spec-cell__value" style={{ color: color || '#fff' }}>{value}</div>
      <div className="spec-cell__label">{label}</div>
      {sub && <div className="caption">{sub}</div>}
    </div>
  );
}

export default function LifeShield() {
  const { locationKey } = useIDTCC();
  const [running, setRunning]   = useState(false);
  const [status, setStatus]     = useState('idle');     // idle | running | done | error
  const [done, setDone]         = useState({});         // node -> true
  const [outputs, setOutputs]   = useState({});         // output_key -> payload
  const [plan, setPlan]         = useState(null);
  const [mapData, setMapData]   = useState(null);
  const [mapReady, setMapReady] = useState(false);
  const mapInstance = useRef(null);

  const sensor   = outputs.sensor_output || {};
  const infra    = outputs.infrastructure_output || {};
  const damage   = outputs.damage_output || {};
  const vuln     = outputs.vulnerable_output || {};
  const shelter  = outputs.shelter_output || {};
  const evac     = outputs.evacuation_output || {};
  const rescue   = outputs.rescue_output || {};
  const dispatch = outputs.dispatched_alerts || {};

  async function runPipeline() {
    setRunning(true); setStatus('running');
    setDone({}); setOutputs({}); setPlan(null);

    // Map data in parallel with the agent stream.
    api.safetyCitizens({ location: locationKey, n: 4000 })
      .then(setMapData).catch(() => {});

    try {
      for await (const ev of api.streamSafety({ location_code: locationKey, twin_count: 12000 })) {
        if (ev.agent === 'system') {
          if (ev.status === 'complete') setStatus('done');
          if (ev.status === 'error')    setStatus('error');
          continue;
        }
        setDone((d) => ({ ...d, [ev.agent]: true }));
        const out = ev.output || {};
        setOutputs((prev) => ({ ...prev, ...out }));
        if (out.response_plan) setPlan({ ...out.response_plan, executive_summary: out.executive_summary });
      }
    } catch {
      setStatus('error');
    } finally {
      setRunning(false);
    }
  }

  // Reset on location change.
  useEffect(() => {
    setStatus('idle'); setDone({}); setOutputs({}); setPlan(null); setMapData(null);
  }, [locationKey]);

  // Render Leaflet city-twin map when citizen data arrives.
  useEffect(() => {
    if (!mapData) return;
    setMapReady(false);
    const t = setTimeout(() => setMapReady(true), 80);
    return () => clearTimeout(t);
  }, [mapData]);

  useEffect(() => {
    if (!mapReady || !mapData) return;
    let map;
    import('leaflet').then(({ default: L }) => {
      const container = document.getElementById('lifeshield-map');
      if (!container) return;
      if (container._leaflet_id && mapInstance.current) { mapInstance.current.remove(); mapInstance.current = null; }

      map = L.map(container, {
        center: mapData.center ?? [13.0, 80.2], zoom: mapData.zoom ?? 11,
        zoomControl: true, attributionControl: false,
      });
      mapInstance.current = map;
      L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', { maxZoom: 19 }).addTo(map);
      const renderer = L.canvas({ padding: 0.5 });

      const shelters = mapData.shelters || [];
      // Citizen dots by evacuation priority.
      for (const c of (mapData.citizens || [])) {
        const col = PRIORITY_COLOR[c.evacuation_priority] || '#16A34A';
        L.circleMarker([c.lat, c.lng], {
          radius: c.evacuation_priority === 'critical' ? 3 : 2,
          color: col, fillColor: col, fillOpacity: 0.6, weight: 0, renderer,
        }).bindTooltip(`${c.ward} · age ${c.age} · ${c.evacuation_priority}`).addTo(map);
      }
      // Evacuation lines for critical citizens → nearest shelter.
      const sById = Object.fromEntries(shelters.map((s) => [s.shelter_id, s]));
      const crit = (mapData.citizens || []).filter((c) => c.evacuation_priority === 'critical').slice(0, 60);
      for (const c of crit) {
        const s = sById[c.nearest_shelter_id];
        if (s) L.polyline([[c.lat, c.lng], [s.lat, s.lng]], { color: '#fff', weight: 0.5, opacity: 0.18 }).addTo(map);
      }
      // Shelters.
      for (const s of shelters) {
        L.circleMarker([s.lat, s.lng], { radius: 9, color: '#1c69d4', fillColor: '#1c69d4', fillOpacity: 0.85, weight: 2 })
          .bindPopup(`<b>${s.name}</b><br>Capacity: ${fmt(s.capacity)}<br>Wheelchair: ${s.wheelchair_accessible ? 'Yes' : 'No'}<br>Medical: ${s.medical_capable ? 'Yes' : 'No'}`)
          .addTo(map);
      }
      // Stranded persons from damage assessment.
      for (const st of (mapData.stranded || [])) {
        L.circleMarker([st.lat, st.lng], { radius: 6, color: '#8B5CF6', fillColor: '#8B5CF6', fillOpacity: 0.9, weight: 1 })
          .bindTooltip(`Stranded: ${st.count}`).addTo(map);
      }
    });
    return () => {
      const container = document.getElementById('lifeshield-map');
      if (container?._leaflet_id && map) { map.remove(); mapInstance.current = null; }
    };
  }, [mapReady, mapData]);

  const conf = plan?.agent_confidences || {};
  const consistency = plan?.consistency;

  return (
    <div style={{ maxWidth: 1440, margin: '0 auto', padding: '48px 24px' }}>
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: 32, flexWrap: 'wrap', gap: 16 }}>
        <div>
          <div className="m-stripe" style={{ width: 48, marginBottom: 12 }} />
          <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 4 }}>LifeShield AI · Life-Safety Lens</div>
          <h2 className="display-sm">City Disaster Command</h2>
          <p className="body-sm" style={{ marginTop: 6 }}>Before the storm hits, we already know — 16 agents on AMD MI300X.</p>
        </div>
        <button className="btn-primary" onClick={runPipeline} disabled={running}
          style={{ padding: '0 24px', height: 44, background: running ? '#3c3c3c' : '#1c69d4', color: '#fff', border: 'none', fontWeight: 700, letterSpacing: 1, textTransform: 'uppercase', cursor: running ? 'default' : 'pointer' }}>
          {running ? 'Running pipeline…' : 'Run Life-Safety Pipeline'}
        </button>
      </div>

      {/* Agent pipeline chips */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 32 }}>
        {AGENT_FLOW.map((a) => {
          const isDone = done[a.node];
          const isActive = running && !isDone;
          const c = isDone ? '#16A34A' : isActive ? '#F59E0B' : '#3c3c3c';
          return (
            <div key={a.node} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 10px', border: `1px solid ${c}`, background: isDone ? 'rgba(22,163,74,0.08)' : '#0d0d0d' }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: c }} />
              <span style={{ fontSize: 11, color: isDone ? '#e6e6e6' : '#9a9a9a' }}>{a.label}</span>
              <span className="caption" style={{ color: '#5a5a5a' }}>{a.layer}</span>
            </div>
          );
        })}
      </div>

      {status === 'idle' && (
        <div className="card" style={{ textAlign: 'center', padding: 48 }}>
          <p className="body-sm">Press <b>Run Life-Safety Pipeline</b> to stream the 16-agent disaster response for <b>{locationKey}</b>.</p>
        </div>
      )}

      {(status !== 'idle') && (
        <>
          {/* KPIs */}
          <div className="grid-4" style={{ marginBottom: 16 }}>
            <Kpi value={fmt(plan?.total_citizens ?? vuln.total_citizens)} label="Citizen Twins" sub="exploded from property twins" />
            <Kpi value={fmt(plan?.citizens_at_risk ?? ((vuln.critical || 0) + (vuln.high || 0)))} label="Citizens At Risk" color="#EA580C" sub="critical + high" />
            <Kpi value={fmt(plan?.critical_rescues ?? rescue.critical)} label="Critical Rescues" color="#DC2626" sub="cannot self-evacuate" />
            <Kpi value={fmt(plan?.shelters_activated ?? shelter.shelters_activated)} label="Shelters Activated" color="#1c69d4" />
          </div>
          <div className="grid-4" style={{ marginBottom: 40 }}>
            <Kpi value={fmt(plan?.citizens_assigned ?? shelter.citizens_assigned)} label="Sheltered" color="#16A34A" />
            <Kpi value={fmt(plan?.unmet_demand ?? shelter.unmet_demand)} label="Unmet Demand" color={(plan?.unmet_demand ?? 0) > 0 ? '#DC2626' : '#16A34A'} />
            <Kpi value={fmt(damage.stranded_persons)} label="Stranded Persons" color="#8B5CF6" sub={`${fmt(damage.roads_blocked)} roads blocked`} />
            <Kpi value={fmt(dispatch.delivered)} label="Alerts Delivered" color="#1c69d4" sub={dispatch.dry_run ? 'simulated' : 'live'} />
          </div>

          {/* City twin map */}
          <div style={{ marginBottom: 40 }}>
            <div style={{ background: '#0d0d0d', border: '1px solid #3c3c3c', padding: '12px 16px', display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'center' }}>
              <span className="label-upper" style={{ color: '#7e7e7e' }}>City Twin Map — {fmt(mapData?.total)} citizen sample</span>
              <div style={{ display: 'flex', gap: 14, marginLeft: 'auto', flexWrap: 'wrap' }}>
                {[['#DC2626', 'Critical'], ['#EA580C', 'High'], ['#F59E0B', 'Medium'], ['#16A34A', 'Low'], ['#1c69d4', 'Shelter'], ['#8B5CF6', 'Stranded']].map(([c, l]) => (
                  <div key={l} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                    <div style={{ width: 10, height: 10, borderRadius: '50%', background: c }} />
                    <span style={{ fontSize: 11, color: '#bbbbbb' }}>{l}</span>
                  </div>
                ))}
              </div>
            </div>
            <div id="lifeshield-map" style={{ width: '100%', height: 460, background: '#111' }}>
              {!mapData && <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}><div className="spinner" /></div>}
            </div>
          </div>

          {/* Rescue queue + Evacuation routes */}
          <div className="grid-2" style={{ marginBottom: 40 }}>
            <div className="card">
              <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 12 }}>Rescue Queue · most urgent ward: {rescue.most_urgent_ward || '—'}</div>
              <div style={{ overflowX: 'auto', maxHeight: 320, overflowY: 'auto' }}>
                <table className="data-table">
                  <thead><tr><th>Citizen</th><th>Ward</th><th>Age</th><th>Need</th><th>Tier</th></tr></thead>
                  <tbody>
                    {(rescue.rescue_queue || []).slice(0, 25).map((r) => (
                      <tr key={r.citizen_id}>
                        <td style={{ fontSize: 12 }}>{r.citizen_id}</td>
                        <td style={{ fontSize: 12 }}>{r.ward}</td>
                        <td>{r.age}</td>
                        <td style={{ fontSize: 11 }}>{r.medical_dependency || (r.disability_status ? 'disability' : '—')}</td>
                        <td><span className={`badge badge-${r.band === 'critical' ? 'red' : 'orange'}`}>{r.band}</span></td>
                      </tr>
                    ))}
                    {!(rescue.rescue_queue || []).length && <tr><td colSpan={5} className="body-sm">Awaiting rescue agent…</td></tr>}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="card">
              <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 12 }}>Evacuation Routes · {fmt(evac.total_to_evacuate)} to move</div>
              <div style={{ overflowX: 'auto', maxHeight: 320, overflowY: 'auto' }}>
                <table className="data-table">
                  <thead><tr><th>Ward</th><th>Tier</th><th>People</th><th>ETA</th><th>Shelter</th></tr></thead>
                  <tbody>
                    {(evac.routes || []).slice(0, 25).map((r, i) => (
                      <tr key={i}>
                        <td style={{ fontSize: 12 }}>{r.ward}{r.avoids_flood_zone ? ' ⚠' : ''}</td>
                        <td><span className={`badge badge-${r.priority === 'critical' ? 'red' : r.priority === 'high' ? 'orange' : 'yellow'}`}>{r.priority}</span></td>
                        <td>{fmt(r.people)}</td>
                        <td>{r.eta_minutes}m</td>
                        <td style={{ fontSize: 11 }}>{r.to_shelter_name}</td>
                      </tr>
                    ))}
                    {!(evac.routes || []).length && <tr><td colSpan={5} className="body-sm">Awaiting evacuation agent…</td></tr>}
                  </tbody>
                </table>
              </div>
              {(evac.bottlenecks || []).length > 0 && (
                <div style={{ marginTop: 12, color: '#F59E0B', fontSize: 12 }}>⚠ {evac.bottlenecks.length} bottleneck(s): {evac.bottlenecks[0]}</div>
              )}
            </div>
          </div>

          {/* Sensor + Infra + Damage + Executive brief */}
          <div className="grid-2" style={{ marginBottom: 40 }}>
            <div className="card">
              <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 12 }}>Real-Time Intelligence</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <Row label="Sensor flood risk" value={`${Math.round((sensor.overall_risk_score ?? 0) * 100)} / 100`} color="#EA580C" />
                <Row label="Sensor breaches" value={fmt((sensor.breaches || []).length)} />
                <Row label="River breach ETA" value={sensor.flood_forecast?.breach_eta_hours != null ? `${sensor.flood_forecast.breach_eta_hours} h` : '—'} />
                <Row label="Infra assets at risk" value={`${fmt(infra.at_risk_assets)} / ${fmt(infra.total_assets)}`} color="#DC2626" />
                <Row label="Cascade chains" value={fmt((infra.cascade_chains || []).length)} />
                <Row label="Damage severe zones" value={fmt(damage.severe_zones)} color="#8B5CF6" />
                <Row label="Vision model" value={damage.vision_model || '—'} />
              </div>
            </div>
            <div className="card">
              <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 12 }}>AI Incident Brief</div>
              <p className="body-sm" style={{ lineHeight: 1.6, minHeight: 80 }}>
                {plan?.executive_summary && !plan.executive_summary.startsWith('[LLM')
                  ? plan.executive_summary
                  : 'Executive brief generated by Qwen3-14B on landfall assembly. (LLM offline in this run — deterministic agent outputs above are unaffected.)'}
              </p>
              {plan && (
                <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid #262626' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <span className="label-upper" style={{ color: '#7e7e7e' }}>Overall confidence</span>
                    <span style={{ color: '#16A34A', fontWeight: 700 }}>{Math.round((plan.overall_confidence ?? 0) * 100)}%</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span className="label-upper" style={{ color: '#7e7e7e' }}>Cross-agent consistency</span>
                    <span style={{ color: consistency?.consistent ? '#16A34A' : '#F59E0B', fontWeight: 700 }}>
                      {consistency ? `${Math.round((consistency.consistency_score ?? 0) * 100)}%` : '—'}
                    </span>
                  </div>
                  {!!(consistency?.issues || []).length && (
                    <div style={{ marginTop: 8, color: '#F59E0B', fontSize: 11 }}>⚠ {consistency.issues[0]}</div>
                  )}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function Row({ label, value, color }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <span className="body-sm" style={{ color: '#bbbbbb' }}>{label}</span>
      <span style={{ fontWeight: 700, color: color || '#fff' }}>{value}</span>
    </div>
  );
}
