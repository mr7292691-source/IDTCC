/**
 * BackendView — triggers the FastAPI + LangGraph backend simulation
 * and streams agent events via SSE. Displays LangSmith trace link.
 */
import { useState, useCallback, useRef, useEffect } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, Cell,
} from 'recharts';
import api from '../../api/client.js';

// ── Agent metadata ──────────────────────────────────────────────────────────

const AGENTS = [
  { key: 'generate_twins',    label: 'Twin Generator',     color: '#6366F1', icon: '⬡' },
  { key: 'weather_agent',     label: 'Agent 1 · Weather',  color: '#60A5FA', icon: '🌪' },
  { key: 'risk_agent',        label: 'Agent 2 · Risk',     color: '#EA580C', icon: '⚠' },
  { key: 'claims_agent',      label: 'Agent 3 · Claims',   color: '#DC2626', icon: '📋' },
  { key: 'fraud_agent',       label: 'Agent 4 · Fraud',    color: '#7C3AED', icon: '🔍' },
  { key: 'reserve_agent',     label: 'Agent 5 · Reserve',  color: '#1c69d4', icon: '🏦' },
  { key: 'resource_agent',    label: 'Agent 6 · Resource', color: '#0fa336', icon: '📍' },
  { key: 'alerts_agent',      label: 'Agent 7 · Alerts',   color: '#f4b400', icon: '📱' },
  { key: 'judge_agent',       label: 'LLM-as-Judge',       color: '#e22718', icon: '⚖' },
  { key: 'assemble_forecast', label: 'Forecast Assembly',  color: '#ffffff', icon: '📊' },
];

const STATUS_STYLE = {
  idle:      { border: '#3c3c3c', bg: '#0d0d0d',  label: 'IDLE',    color: '#7e7e7e' },
  running:   { border: '#1c69d4', bg: '#0a1a30',  label: 'RUNNING', color: '#60A5FA' },
  done:      { border: '#0fa336', bg: '#041a0d',  label: 'DONE',    color: '#4ADE80' },
  error:     { border: '#DC2626', bg: '#1a0505',  label: 'ERROR',   color: '#F87171' },
};

const TOOLTIP_STYLE = {
  contentStyle: { background: '#1a1a1a', border: '1px solid #3c3c3c', borderRadius: 0, color: '#fff' },
  labelStyle:   { color: '#bbbbbb', fontSize: 12 },
  itemStyle:    { color: '#e6e6e6', fontSize: 13 },
};

// ── Sub-components ───────────────────────────────────────────────────────────

function AgentCard({ agent, status, output, elapsed }) {
  const s = STATUS_STYLE[status] ?? STATUS_STYLE.idle;
  return (
    <div style={{
      border: `1px solid ${s.border}`,
      background: s.bg,
      padding: '14px 16px',
      display: 'flex', alignItems: 'flex-start', gap: 12,
      transition: 'border-color 0.3s, background 0.3s',
    }}>
      <span style={{ fontSize: 20, flexShrink: 0, marginTop: 2 }}>{agent.icon}</span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
          <span style={{ fontSize: 12, fontWeight: 700, letterSpacing: 1.2, textTransform: 'uppercase', color: agent.color }}>
            {agent.label}
          </span>
          <span style={{
            fontSize: 9, fontWeight: 700, letterSpacing: 1.5, textTransform: 'uppercase',
            padding: '2px 6px', border: `1px solid ${s.border}`, color: s.color,
          }}>
            {s.label}
          </span>
          {elapsed && status === 'done' && (
            <span style={{ fontSize: 10, color: '#7e7e7e' }}>{elapsed}ms</span>
          )}
        </div>
        {status === 'running' && (
          <div style={{ display: 'flex', gap: 3, alignItems: 'center', marginTop: 4 }}>
            {[0, 0.15, 0.3].map(d => (
              <span key={d} style={{
                width: 4, height: 4, borderRadius: '50%', background: '#1c69d4',
                animation: `pulse 1s ${d}s infinite`,
              }} />
            ))}
          </div>
        )}
        {status === 'done' && output && (
          <div style={{ marginTop: 4 }}>
            <AgentOutputSummary agentKey={agent.key} output={output} />
          </div>
        )}
      </div>
    </div>
  );
}

function AgentOutputSummary({ agentKey, output }) {
  const items = [];
  if (agentKey === 'generate_twins' && output.twins_records) {
    items.push(`${output.twins_records.length?.toLocaleString('en-IN') ?? '50,000'} twins generated`);
  }
  if (agentKey === 'weather_agent' && output.weather_output) {
    const w = output.weather_output;
    if (w.storm_severity_index) items.push(`Severity ${w.storm_severity_index}/10`);
    if (w.max_wind_kmh) items.push(`${w.max_wind_kmh} km/h`);
  }
  if (agentKey === 'risk_agent' && output.risk_output) {
    const r = output.risk_output;
    if (r.twins_in_impact_radius) items.push(`${r.twins_in_impact_radius.toLocaleString('en-IN')} in radius`);
    if (r.exposure_pct != null) items.push(`${r.exposure_pct}% exposed`);
  }
  if (agentKey === 'claims_agent' && output.claims_output) {
    const c = output.claims_output;
    if (c.expected_total_loss_crore) items.push(`₹${c.expected_total_loss_crore}Cr expected loss`);
    if (c.red_twin_count) items.push(`${c.red_twin_count.toLocaleString('en-IN')} critical twins`);
  }
  if (agentKey === 'fraud_agent' && output.fraud_output) {
    const f = output.fraud_output;
    if (f.total_fraud_risk_twins != null) items.push(`${f.total_fraud_risk_twins} fraud flags`);
  }
  if (agentKey === 'reserve_agent' && output.reserve_output) {
    const r = output.reserve_output;
    if (r.total_recommended_reserve_crore) items.push(`₹${r.total_recommended_reserve_crore}Cr reserve`);
  }
  if (agentKey === 'resource_agent' && output.resource_output) {
    const r = output.resource_output;
    if (r.adjusters_needed) items.push(`${r.adjusters_needed} adjusters, ${r.deployment_zones} zones`);
  }
  if (agentKey === 'assemble_forecast' && output.forecast) {
    const f = output.forecast;
    if (f.executive_summary) items.push(f.executive_summary.slice(0, 80) + '…');
  }
  if (!items.length) return null;
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
      {items.map((item, i) => (
        <span key={i} style={{ fontSize: 11, color: '#bbbbbb', background: '#262626', padding: '2px 6px' }}>
          {item}
        </span>
      ))}
    </div>
  );
}

function ForecastResult({ forecast }) {
  if (!forecast) return null;
  const riskBreakdown = [
    { name: 'Critical', value: forecast.red_twins ?? 0,   color: '#DC2626' },
    { name: 'High',     value: Math.round((forecast.twins_in_impact_radius - forecast.red_twins) * 0.4) ?? 0, color: '#EA580C' },
    { name: 'Medium',   value: Math.round((forecast.twins_in_impact_radius - forecast.red_twins) * 0.35) ?? 0, color: '#CA8A04' },
    { name: 'Low',      value: Math.round((forecast.total_portfolio_twins - forecast.twins_in_impact_radius) * 0.5) ?? 0, color: '#16A34A' },
  ];
  const topAreas = Object.entries(forecast.top_loss_areas ?? {}).map(([area, loss]) => ({ area, loss })).slice(0, 6);
  return (
    <div>
      <div style={{ marginBottom: 32 }}>
        <div className="m-stripe" style={{ marginBottom: 16 }} />
        <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 8 }}>Executive Summary · AI Chief Risk Officer</div>
        <p style={{ fontSize: 16, fontWeight: 300, lineHeight: 1.7, color: '#e6e6e6', maxWidth: 900 }}>
          {forecast.executive_summary ?? '—'}
        </p>
      </div>
      <div className="grid-4" style={{ marginBottom: 32 }}>
        {[
          { v: (forecast.red_twins ?? 0).toLocaleString('en-IN'), l: 'Critical Twins',      c: '#DC2626', sub: `of ${(forecast.total_portfolio_twins ?? 0).toLocaleString('en-IN')}` },
          { v: `₹${forecast.expected_loss_crore ?? 0}Cr`,          l: 'Expected Loss',       c: '#EA580C', sub: `Reserve: ₹${forecast.reserve_required_crore ?? 0}Cr` },
          { v: forecast.adjusters_needed ?? 0,                     l: 'Adjusters Needed',   c: '#1c69d4', sub: `${forecast.deployment_zones ?? 0} zones` },
          { v: forecast.fraud_risk_twins ?? 0,                     l: 'Fraud Risk Flags',   c: '#7C3AED', sub: `${forecast.storm_severity_index ?? 0}/10 severity` },
        ].map(kpi => (
          <div key={kpi.l} className="spec-cell" style={{ borderLeft: `3px solid ${kpi.c}` }}>
            <div className="spec-cell__value" style={{ color: kpi.c }}>{kpi.v}</div>
            <div className="spec-cell__label">{kpi.l}</div>
            {kpi.sub && <div className="caption" style={{ marginTop: 6 }}>{kpi.sub}</div>}
          </div>
        ))}
      </div>
      <div className="grid-2">
        <div className="card">
          <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 16 }}>Risk Breakdown</div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={riskBreakdown} barCategoryGap="35%">
              <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
              <XAxis dataKey="name" tick={{ fill: '#bbbbbb', fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#bbbbbb', fontSize: 11 }} axisLine={false} tickLine={false}
                tickFormatter={v => v.toLocaleString('en-IN')} />
              <Tooltip {...TOOLTIP_STYLE} />
              <Bar dataKey="value" radius={[0, 0, 0, 0]}>
                {riskBreakdown.map(d => <Cell key={d.name} fill={d.color} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        {topAreas.length > 0 && (
          <div className="card">
            <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 16 }}>Top Loss Areas (₹Cr)</div>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={topAreas} barCategoryGap="30%">
                <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
                <XAxis dataKey="area" tick={{ fill: '#bbbbbb', fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#bbbbbb', fontSize: 11 }} axisLine={false} tickLine={false}
                  tickFormatter={v => `₹${v}`} />
                <Tooltip {...TOOLTIP_STYLE} formatter={v => [`₹${v}Cr`]} />
                <Bar dataKey="loss" fill="#DC2626" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main component ───────────────────────────────────────────────────────────

export default function BackendView() {
  const [form, setForm] = useState({
    location_code: 'CHN',
    twin_count: 5000,
    cyclone_name: 'NIVAR',
    max_wind_kmh: 180,
    landfall_eta_hours: 48,
    radius_km: 120,
    track_shift_km: 0,
  });
  const [agentStatus, setAgentStatus]   = useState({});
  const [forecast, setForecast]         = useState(null);
  const [running, setRunning]           = useState(false);
  const [error, setError]               = useState(null);
  const [langsmithUrl, setLangsmithUrl] = useState(null);
  const [backendOnline, setBackendOnline] = useState(null);
  const [cityGroups, setCityGroups]     = useState([]);
  const startRef = useRef({});

  // Load 35 cities on mount
  useEffect(() => {
    api.locations()
      .then(res => setCityGroups(res.groups || []))
      .catch(() => {});
  }, []);

  // Check backend health
  const checkBackend = useCallback(async () => {
    try {
      await api.health();
      setBackendOnline(true);
    } catch {
      setBackendOnline(false);
    }
  }, []);

  // Run streaming simulation
  const runSimulation = useCallback(async () => {
    setRunning(true);
    setError(null);
    setForecast(null);
    setLangsmithUrl(null);
    const fresh = {};
    AGENTS.forEach(a => { fresh[a.key] = { status: 'idle', output: null, elapsed: null }; });
    setAgentStatus(fresh);

    try {
      let prevKeys = new Set();
      const onEvent = (event) => {
        const { agent, status, output } = event;
        if (agent === 'system') {
          if (status === 'complete') setRunning(false);
          return;
        }
        const now = Date.now();
        if (status !== 'idle') startRef.current[agent] = startRef.current[agent] ?? now;
        const elapsed = status === 'done' ? now - (startRef.current[agent] ?? now) : null;
        setAgentStatus(prev => ({
          ...prev,
          [agent]: { status, output, elapsed },
        }));
        // When assemble_forecast is done, extract forecast
        if (agent === 'assemble_forecast' && status === 'done' && output?.forecast) {
          setForecast(output.forecast);
          if (output.forecast.graph_trace_url) setLangsmithUrl(output.forecast.graph_trace_url);
        }
      };

      // Mark agents as running as they start
      for await (const event of api.streamSimulation(form, onEvent)) {
        // Mark next predicted agents as "running" when previous completes
        if (event.status === 'done') {
          prevKeys.add(event.agent);
        }
      }
    } catch (err) {
      setError(`Backend error: ${err.message}. Make sure the FastAPI server is running on localhost:8000`);
    } finally {
      setRunning(false);
    }
  }, [form]);

  const allDone = AGENTS.every(a => agentStatus[a.key]?.status === 'done');
  const anyRan  = AGENTS.some(a => agentStatus[a.key]?.status !== 'idle');

  return (
    <div style={{ maxWidth: 1440, margin: '0 auto', padding: '48px 24px' }}>
      {/* Header */}
      <div style={{ marginBottom: 40 }}>
        <div className="label-upper" style={{ color: '#0066b1', marginBottom: 8 }}>
          LangGraph · LangSmith · FastAPI
        </div>
        <h1 className="display-md" style={{ marginBottom: 8 }}>Backend Simulation Pipeline</h1>
        <p className="body-md" style={{ maxWidth: 700 }}>
          Triggers the full 7-agent LangGraph workflow on the FastAPI backend.
          Each agent is traced in LangSmith. Stream real-time status below.
        </p>
      </div>

      {/* Backend status pill */}
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 32, flexWrap: 'wrap' }}>
        <button
          onClick={checkBackend}
          style={{
            background: 'transparent', color: '#bbbbbb', border: '1px solid #3c3c3c',
            padding: '6px 14px', fontSize: 11, fontWeight: 700, letterSpacing: 1.5,
            textTransform: 'uppercase', cursor: 'pointer', borderRadius: 0, fontFamily: 'Inter,sans-serif',
          }}
        >
          Check API
        </button>
        {backendOnline !== null && (
          <span style={{
            fontSize: 11, fontWeight: 700, letterSpacing: 1.5, textTransform: 'uppercase',
            padding: '6px 12px', border: `1px solid ${backendOnline ? '#0fa336' : '#DC2626'}`,
            color: backendOnline ? '#4ADE80' : '#F87171',
          }}>
            {backendOnline ? '● API ONLINE' : '✕ API OFFLINE'}
          </span>
        )}
        {langsmithUrl && (
          <a
            href={langsmithUrl}
            target="_blank"
            rel="noreferrer"
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              fontSize: 11, fontWeight: 700, letterSpacing: 1.5, textTransform: 'uppercase',
              padding: '6px 12px', border: '1px solid #1c69d4', color: '#60A5FA',
              textDecoration: 'none',
            }}
          >
            View LangSmith Trace →
          </a>
        )}
      </div>

      {/* Config form */}
      <div className="card" style={{ marginBottom: 32 }}>
        <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 20 }}>Simulation Parameters</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 16, marginBottom: 24 }}>
          {[
            { key: 'location_code', label: 'Location', type: 'city_select' },
            { key: 'twin_count',          label: 'Twin Count',       type: 'number', min: 100, max: 50000, step: 100 },
            { key: 'cyclone_name',        label: 'Cyclone Name',     type: 'text' },
            { key: 'max_wind_kmh',        label: 'Max Wind (km/h)',  type: 'number', min: 60, max: 300, step: 5 },
            { key: 'landfall_eta_hours',  label: 'Landfall ETA (h)', type: 'number', min: 6, max: 120, step: 1 },
            { key: 'radius_km',           label: 'Radius (km)',      type: 'number', min: 20, max: 300, step: 10 },
            { key: 'track_shift_km',      label: 'Track Shift (km)', type: 'number', min: -60, max: 60, step: 5 },
          ].map(field => (
            <div key={field.key}>
              <div className="label-upper" style={{ color: '#7e7e7e', fontSize: 10, marginBottom: 6 }}>{field.label}</div>
              {field.type === 'city_select' ? (
                <select
                  value={form[field.key]}
                  onChange={e => setForm(p => ({ ...p, [field.key]: e.target.value }))}
                  className="text-input"
                  disabled={running}
                  style={{ height: 40, padding: '0 12px', fontSize: 13 }}
                >
                  {cityGroups.length > 0
                    ? cityGroups.map(group => (
                      <optgroup key={group.state} label={group.state}>
                        {group.cities.map(city => (
                          <option key={city.code} value={city.code}>{city.name}</option>
                        ))}
                      </optgroup>
                    ))
                    : [
                      <option key="CHN" value="CHN">Chennai</option>,
                      <option key="MUM" value="MUM">Mumbai</option>,
                      <option key="VIJ" value="VIJ">Vijayawada</option>,
                    ]
                  }
                </select>
              ) : (
                <input
                  type={field.type}
                  value={form[field.key]}
                  min={field.min} max={field.max} step={field.step}
                  onChange={e => setForm(p => ({
                    ...p,
                    [field.key]: field.type === 'number' ? Number(e.target.value) : e.target.value,
                  }))}
                  className="text-input"
                  disabled={running}
                  style={{ height: 40, padding: '0 12px', fontSize: 13 }}
                />
              )}
            </div>
          ))}
        </div>
        <button
          onClick={runSimulation}
          disabled={running}
          className="btn-primary"
          style={{ opacity: running ? 0.5 : 1 }}
        >
          {running ? 'Running Pipeline...' : 'Run LangGraph Pipeline →'}
        </button>
      </div>

      {error && (
        <div style={{ background: '#1a0505', border: '1px solid #DC2626', padding: 16, marginBottom: 24, color: '#F87171', fontSize: 14 }}>
          {error}
        </div>
      )}

      {/* Agent pipeline grid */}
      {anyRan && (
        <div style={{ marginBottom: 40 }}>
          <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 16 }}>Agent Pipeline Status</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 8 }}>
            {AGENTS.map(agent => (
              <AgentCard
                key={agent.key}
                agent={agent}
                status={agentStatus[agent.key]?.status ?? 'idle'}
                output={agentStatus[agent.key]?.output}
                elapsed={agentStatus[agent.key]?.elapsed}
              />
            ))}
          </div>
        </div>
      )}

      {/* LangGraph diagram */}
      <div style={{ marginBottom: 40 }}>
        <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 16 }}>Pipeline Architecture</div>
        <div className="card" style={{ overflowX: 'auto' }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 0, flexWrap: 'nowrap',
            minWidth: 900, padding: '8px 0',
          }}>
            {[
              { label: 'START',             color: '#3c3c3c' },
              { label: 'Twin Generator',    color: '#6366F1' },
              { label: 'Weather',           color: '#60A5FA' },
              { label: 'Risk',              color: '#EA580C' },
              { label: 'Claims  ∥  Fraud',  color: '#DC2626' },
              { label: 'Reserve',           color: '#1c69d4' },
              { label: 'Resource ∥ Alerts', color: '#0fa336' },
              { label: 'LLM-as-Judge',      color: '#e22718' },
              { label: 'Forecast',          color: '#ffffff' },
              { label: 'END',               color: '#3c3c3c' },
            ].map((node, i, arr) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', flexShrink: 0 }}>
                <div style={{
                  padding: '8px 14px', background: '#1a1a1a', border: `1px solid ${node.color}`,
                  fontSize: 11, fontWeight: 700, letterSpacing: 1.2, color: node.color,
                  textTransform: 'uppercase', whiteSpace: 'nowrap',
                }}>
                  {node.label}
                </div>
                {i < arr.length - 1 && (
                  <div style={{ width: 24, height: 1, background: '#3c3c3c', flexShrink: 0 }}>
                    <div style={{ position: 'relative', top: -4, left: 16, color: '#3c3c3c', fontSize: 12 }}>▶</div>
                  </div>
                )}
              </div>
            ))}
          </div>
          <div style={{ marginTop: 12, display: 'flex', gap: 16, flexWrap: 'wrap' }}>
            {[
              { color: '#1c69d4', label: 'LangGraph node' },
              { color: '#0fa336', label: 'Parallel execution' },
              { color: '#e22718', label: 'LLM-as-Judge gating' },
            ].map(item => (
              <span key={item.label} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#7e7e7e' }}>
                <span style={{ width: 8, height: 8, background: item.color, display: 'inline-block' }} />
                {item.label}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Forecast result */}
      {forecast && <ForecastResult forecast={forecast} />}

      {/* LangSmith info box */}
      <div style={{ marginTop: 48, background: '#0d0d0d', border: '1px solid #3c3c3c', padding: 24 }}>
        <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 12 }}>LangSmith Tracing</div>
        <p className="body-sm" style={{ maxWidth: 700 }}>
          Every agent node, LLM call, and tool invocation in the LangGraph pipeline is
          automatically traced to LangSmith when <code style={{ color: '#60A5FA' }}>LANGCHAIN_TRACING_V2=true</code> and{' '}
          <code style={{ color: '#60A5FA' }}>LANGCHAIN_API_KEY</code> are set in the backend
          <code style={{ color: '#60A5FA' }}>.env</code>. Traces appear in the project{' '}
          <strong style={{ color: '#e6e6e6' }}>idtcc-production</strong> on smith.langchain.com.
        </p>
        <div style={{ marginTop: 16, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {[
            'LANGCHAIN_TRACING_V2=true',
            'LANGCHAIN_API_KEY=<your_key>',
            'LANGCHAIN_PROJECT=idtcc-production',
          ].map(env => (
            <code key={env} style={{
              background: '#1a1a1a', border: '1px solid #3c3c3c',
              padding: '4px 10px', fontSize: 12, color: '#60A5FA',
            }}>
              {env}
            </code>
          ))}
        </div>
      </div>
    </div>
  );
}
