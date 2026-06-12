import { useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Cell, PieChart, Pie,
} from 'recharts';
import { useIDTCC } from '../../context/IDTCCContext.jsx';

const TOOLTIP_STYLE = {
  contentStyle: { background: '#1a1a1a', border: '1px solid #3c3c3c', borderRadius: 0, color: '#fff' },
  labelStyle:   { color: '#bbbbbb', fontSize: 12 },
  itemStyle:    { color: '#e6e6e6', fontSize: 13 },
};

const AGENT_TABS = [
  { key: 'weather',   label: 'Agent 1 · Weather' },
  { key: 'risk',      label: 'Agent 2 · Risk' },
  { key: 'claims',    label: 'Agent 3 · Claims' },
  { key: 'fraud',     label: 'Agent 4 · Fraud' },
  { key: 'reserve',   label: 'Agent 5 · Reserve' },
  { key: 'resources', label: 'Agent 6 · Resources' },
  { key: 'alerts',    label: 'Agent 7 · Alerts' },
];

function AgentHeader({ number, title, color = '#1c69d4' }) {
  return (
    <div style={{ marginBottom: 32 }}>
      <div className="m-stripe" style={{ width: 48, marginBottom: 12 }} />
      <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 4 }}>Agent {number}</div>
      <h2 className="display-sm">{title}</h2>
    </div>
  );
}

// ─── Agent 1: Weather ─────────────────────────────────────────────────────────
function WeatherAgent({ data }) {
  const alertColors = { EXTREME: '#DC2626', SEVERE: '#EA580C', HIGH: '#CA8A04', MODERATE: '#16A34A' };
  return (
    <div>
      <AgentHeader number={1} title="Weather Intelligence" />
      <div className="grid-4" style={{ marginBottom: 32 }}>
        <div className="spec-cell">
          <div className="spec-cell__value" style={{ color: '#60A5FA' }}>{data.max_wind_kmh}</div>
          <div className="spec-cell__label">Max Wind (km/h)</div>
        </div>
        <div className="spec-cell">
          <div className="spec-cell__value">{data.landfall_eta_h}h</div>
          <div className="spec-cell__label">Landfall ETA</div>
        </div>
        <div className="spec-cell">
          <div className="spec-cell__value">{data.radius_km}km</div>
          <div className="spec-cell__label">Impact Radius</div>
        </div>
        <div className="spec-cell">
          <div className="spec-cell__value" style={{ color: alertColors[data.alert_level] ?? '#fff' }}>{data.alert_level}</div>
          <div className="spec-cell__label">Alert Level</div>
          <div className="caption">Severity {data.storm_severity_index}/10</div>
        </div>
      </div>
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 12 }}>Primary Hazards</div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {data.primary_hazards.map(h => (
            <span key={h} className="badge badge-red">{h}</span>
          ))}
        </div>
      </div>
      <div className="card">
        <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 12 }}>Agent Recommendation</div>
        <p className="body-md">{data.recommendation}</p>
      </div>
    </div>
  );
}

// ─── Agent 2: Risk ────────────────────────────────────────────────────────────
function RiskAgent({ data }) {
  const zoneData = Object.entries(data.by_flood_zone).map(([zone, v]) => ({
    zone, count: v.count, avg_prob: +(v.avg_prob * 100).toFixed(1), total_loss: v.total_loss_cr,
  }));
  return (
    <div>
      <AgentHeader number={2} title="Risk Exposure Analysis" />
      <div className="grid-3" style={{ marginBottom: 32 }}>
        <div className="spec-cell">
          <div className="spec-cell__value">{data.twins_in_impact_radius.toLocaleString('en-IN')}</div>
          <div className="spec-cell__label">Twins in Impact Radius</div>
          <div className="caption">{data.exposure_pct}% of portfolio</div>
        </div>
        <div className="spec-cell">
          <div className="spec-cell__value">{data.total_portfolio_twins.toLocaleString('en-IN')}</div>
          <div className="spec-cell__label">Total Portfolio</div>
        </div>
        <div className="spec-cell">
          <div className="spec-cell__value">{Object.values(data.by_flood_zone).reduce((s, v) => s + v.count, 0).toLocaleString('en-IN')}</div>
          <div className="spec-cell__label">All Zones Covered</div>
        </div>
      </div>

      <div className="grid-2" style={{ marginBottom: 32 }}>
        <div className="card">
          <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 16 }}>Flood Zone — Avg Claim Prob %</div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={zoneData} barCategoryGap="40%">
              <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
              <XAxis dataKey="zone" tick={{ fill: '#bbbbbb', fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#bbbbbb', fontSize: 11 }} axisLine={false} tickLine={false}
                tickFormatter={v => `${v}%`} />
              <Tooltip {...TOOLTIP_STYLE} formatter={v => [`${v}%`, 'Avg Claim Prob']} />
              <Bar dataKey="avg_prob" radius={[0,0,0,0]}>
                {zoneData.map((d, i) => (
                  <Cell key={i} fill={d.zone === 'Zone_A' ? '#EF4444' : d.zone === 'Zone_B' ? '#F97316' : '#22C55E'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="card">
          <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 16 }}>Total Loss by Flood Zone (₹Cr)</div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={zoneData} barCategoryGap="40%">
              <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
              <XAxis dataKey="zone" tick={{ fill: '#bbbbbb', fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#bbbbbb', fontSize: 11 }} axisLine={false} tickLine={false}
                tickFormatter={v => `₹${v}`} />
              <Tooltip {...TOOLTIP_STYLE} formatter={v => [`₹${v}Cr`, 'Expected Loss']} />
              <Bar dataKey="total_loss" fill="#EF4444">
                {zoneData.map((d, i) => (
                  <Cell key={i} fill={d.zone === 'Zone_A' ? '#EF4444' : d.zone === 'Zone_B' ? '#F97316' : '#22C55E'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="card">
        <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 16 }}>Top 10 Highest Vulnerability Properties</div>
        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr><th>Twin ID</th><th>Area</th><th>Flood Zone</th><th>Vulnerability</th><th>Claim Prob</th></tr>
            </thead>
            <tbody>
              {data.top10_highest_vulnerability.map(t => (
                <tr key={t.twin_id}>
                  <td><code style={{ color: '#6366F1', fontSize: 12 }}>{t.twin_id}</code></td>
                  <td>{t.address?.split(',')[1]?.trim() ?? '—'}</td>
                  <td><span className={`badge badge-${t.flood_zone === 'Zone_A' ? 'red' : t.flood_zone === 'Zone_B' ? 'orange' : 'green'}`}>{t.flood_zone}</span></td>
                  <td>{t.vulnerability_index}</td>
                  <td><span style={{ color: '#DC2626', fontWeight: 700 }}>{(t.claim_probability * 100).toFixed(1)}%</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ─── Agent 3: Claims ──────────────────────────────────────────────────────────
function ClaimsAgent({ data }) {
  const areaData = Object.entries(data.top_loss_areas_crore).map(([area, loss]) => ({ area, loss }));
  return (
    <div>
      <AgentHeader number={3} title="Claims Forecast" />
      <div className="grid-4" style={{ marginBottom: 32 }}>
        <div className="spec-cell">
          <div className="spec-cell__value" style={{ color: '#DC2626' }}>{data.expected_claim_count.toLocaleString('en-IN')}</div>
          <div className="spec-cell__label">Expected Claims</div>
        </div>
        <div className="spec-cell">
          <div className="spec-cell__value">₹{data.expected_total_loss_crore}Cr</div>
          <div className="spec-cell__label">Total Expected Loss</div>
        </div>
        <div className="spec-cell">
          <div className="spec-cell__value" style={{ color: '#DC2626' }}>{data.red_twin_count.toLocaleString('en-IN')}</div>
          <div className="spec-cell__label">Critical Twins</div>
          <div className="caption">Claim prob ≥ 70%</div>
        </div>
        <div className="spec-cell">
          <div className="spec-cell__value">₹{(data.avg_loss_per_claim_inr / 100000).toFixed(1)}L</div>
          <div className="spec-cell__label">Avg Loss / Claim</div>
        </div>
      </div>
      <div className="card">
        <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 16 }}>Top 5 Loss Areas (₹ Crore)</div>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={areaData} barCategoryGap="30%">
            <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
            <XAxis dataKey="area" tick={{ fill: '#bbbbbb', fontSize: 12 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: '#bbbbbb', fontSize: 11 }} axisLine={false} tickLine={false}
              tickFormatter={v => `₹${v}`} />
            <Tooltip {...TOOLTIP_STYLE} formatter={v => [`₹${v}Cr`, 'Expected Loss']} />
            <Bar dataKey="loss" fill="#DC2626" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// ─── Agent 4: Fraud ───────────────────────────────────────────────────────────
function FraudAgent({ data }) {
  const reasonData = Object.entries(data.by_reason).map(([reason, count]) => ({ reason: reason.slice(0, 35), count }));
  return (
    <div>
      <AgentHeader number={4} title="Fraud Detection" />
      <div className="grid-4" style={{ marginBottom: 32 }}>
        <div className="spec-cell">
          <div className="spec-cell__value" style={{ color: '#7C3AED' }}>{data.total_fraud_risk_twins.toLocaleString('en-IN')}</div>
          <div className="spec-cell__label">Total Fraud Risk</div>
        </div>
        <div className="spec-cell">
          <div className="spec-cell__value">{data.known_fraud_flags}</div>
          <div className="spec-cell__label">Known Fraud Flags</div>
        </div>
        <div className="spec-cell">
          <div className="spec-cell__value">{data.suspicious_twins}</div>
          <div className="spec-cell__label">Suspicious (Recent Claim)</div>
        </div>
        <div className="spec-cell">
          <div className="spec-cell__value">{data.anomaly_flags}</div>
          <div className="spec-cell__label">Anomaly Flags</div>
        </div>
      </div>
      <div className="grid-2" style={{ marginBottom: 32 }}>
        <div className="card">
          <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 16 }}>By Fraud Reason</div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={reasonData} layout="vertical" barCategoryGap="30%">
              <CartesianGrid strokeDasharray="3 3" stroke="#262626" horizontal={false} />
              <XAxis type="number" tick={{ fill: '#bbbbbb', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="reason" tick={{ fill: '#bbbbbb', fontSize: 10 }} width={200} axisLine={false} tickLine={false} />
              <Tooltip {...TOOLTIP_STYLE} formatter={v => [v, 'Flags']} />
              <Bar dataKey="count" fill="#7C3AED" />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="card">
          <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 12 }}>Detection Methods</div>
          {[
            { label: 'Prior fraud flag (database)', color: '#DC2626', pct: Math.round(data.known_fraud_flags / data.total_fraud_risk_twins * 100) },
            { label: 'Rule-based: high risk + recent claim', color: '#F59E0B', pct: Math.round(data.suspicious_twins / data.total_fraud_risk_twins * 100) },
            { label: 'FAISS anomaly detection', color: '#8B5CF6', pct: Math.round(data.anomaly_flags / data.total_fraud_risk_twins * 100) },
          ].map(m => (
            <div key={m.label} style={{ marginBottom: 14 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <span className="body-sm">{m.label}</span>
                <span className="body-sm">{m.pct}%</span>
              </div>
              <div style={{ height: 4, background: '#262626' }}>
                <div style={{ width: `${m.pct}%`, height: '100%', background: m.color }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 16 }}>Top 20 Fraud-Risk Cases</div>
        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr><th>Twin ID</th><th>Address</th><th>Reason</th><th>Claim Prob</th><th>Prior Claim Yr</th></tr>
            </thead>
            <tbody>
              {data.top_fraud_cases.slice(0, 15).map(c => (
                <tr key={c.twin_id}>
                  <td><code style={{ color: '#7C3AED', fontSize: 12 }}>{c.twin_id}</code></td>
                  <td style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.address}</td>
                  <td className="body-sm">{c.fraud_reason}</td>
                  <td><span style={{ color: '#DC2626', fontWeight: 700 }}>{(c.claim_probability*100).toFixed(1)}%</span></td>
                  <td>{c.prior_claim_year ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ─── Agent 5: Reserve ─────────────────────────────────────────────────────────
function ReserveAgent({ data }) {
  return (
    <div>
      <AgentHeader number={5} title="Reserve Calculation" />
      <div className="grid-4" style={{ marginBottom: 32 }}>
        <div className="spec-cell">
          <div className="spec-cell__value">₹{data.base_expected_loss_crore}Cr</div>
          <div className="spec-cell__label">Base Expected Loss</div>
        </div>
        <div className="spec-cell">
          <div className="spec-cell__value" style={{ color: '#EA580C' }}>₹{data.base_reserve_crore}Cr</div>
          <div className="spec-cell__label">Cat-Loaded Reserve</div>
          <div className="caption">+{data.cat_load_pct}% cat load</div>
        </div>
        <div className="spec-cell">
          <div className="spec-cell__value">₹{data.ibnr_crore}Cr</div>
          <div className="spec-cell__label">IBNR</div>
          <div className="caption">{data.ibnr_factor_pct}% IBNR factor</div>
        </div>
        <div className="spec-cell" style={{ borderColor: '#1c69d4' }}>
          <div className="spec-cell__value" style={{ color: '#60A5FA' }}>₹{data.total_recommended_reserve_crore}Cr</div>
          <div className="spec-cell__label">Total Recommended Reserve</div>
          <div className="caption">incl. PFAD {data.pfad_pct}%</div>
        </div>
      </div>

      <div className="card">
        <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 16 }}>Reserve Sensitivity — Wind Speed Scenarios</div>
        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Scenario</th>
                <th>Expected Loss (₹Cr)</th>
                <th>Reserve (₹Cr)</th>
                <th>Reserve + IBNR (₹Cr)</th>
              </tr>
            </thead>
            <tbody>
              {data.reserve_sensitivity.map((row, i) => (
                <tr key={i}>
                  <td><span className={`badge ${i === 3 ? 'badge-blue' : ''}`}>{row.scenario}</span></td>
                  <td style={{ color: row.expected_loss > data.base_expected_loss_crore ? '#DC2626' : '#22C55E' }}>
                    ₹{row.expected_loss}
                  </td>
                  <td>₹{row.reserve}</td>
                  <td>₹{row.reserve_ibnr}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ─── Agent 6: Resources ───────────────────────────────────────────────────────
function ResourcesAgent({ data }) {
  if (data.error) return <div className="card"><p className="body-md" style={{ color: '#DC2626' }}>{data.error}</p></div>;
  return (
    <div>
      <AgentHeader number={6} title="Resource Planning" />
      <div className="grid-4" style={{ marginBottom: 32 }}>
        <div className="spec-cell">
          <div className="spec-cell__value" style={{ color: '#1c69d4' }}>{data.adjusters_needed}</div>
          <div className="spec-cell__label">Adjusters Needed</div>
        </div>
        <div className="spec-cell">
          <div className="spec-cell__value">{data.deployment_zones}</div>
          <div className="spec-cell__label">Deployment Zones</div>
        </div>
        <div className="spec-cell">
          <div className="spec-cell__value">{data.adjusters_per_zone}</div>
          <div className="spec-cell__label">Adjusters / Zone</div>
        </div>
        <div className="spec-cell">
          <div className="spec-cell__value">{data.red_twins_clustered.toLocaleString('en-IN')}</div>
          <div className="spec-cell__label">Red Twins Clustered</div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 24 }}>
        <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 8 }}>Deployment Strategy</div>
        <p className="body-md">{data.deployment_strategy}</p>
      </div>

      <div className="card">
        <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 16 }}>Zone Summary</div>
        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr><th>Zone</th><th>Top Area</th><th>Twins</th><th>Avg Claim Prob</th><th>Center (lat,lng)</th></tr>
            </thead>
            <tbody>
              {data.zone_details.map(z => (
                <tr key={z.zone_id}>
                  <td><span className="badge badge-blue">{z.zone_id}</span></td>
                  <td>{z.top_area}</td>
                  <td>{z.twin_count.toLocaleString('en-IN')}</td>
                  <td><span style={{ color: '#DC2626', fontWeight: 700 }}>{(z.avg_claim_prob * 100).toFixed(1)}%</span></td>
                  <td className="caption">{z.center_lat}, {z.center_lng}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ─── Agent 7: Alerts ──────────────────────────────────────────────────────────
function AlertsAgent({ data }) {
  return (
    <div>
      <AgentHeader number={7} title="Customer Alerts" />
      <div className="grid-3" style={{ marginBottom: 32 }}>
        <div className="spec-cell">
          <div className="spec-cell__value" style={{ color: '#1c69d4' }}>{data.length}</div>
          <div className="spec-cell__label">Alerts Shown (Top 20)</div>
        </div>
        <div className="spec-cell">
          <div className="spec-cell__value">160</div>
          <div className="spec-cell__label">Max Message Chars</div>
          <div className="caption">SMS-ready format</div>
        </div>
        <div className="spec-cell">
          <div className="spec-cell__value">100%</div>
          <div className="spec-cell__label">Red-Zone Coverage</div>
        </div>
      </div>
      <div className="card">
        <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 16 }}>Top 20 High-Risk Property Alerts</div>
        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Twin ID</th><th>Policyholder</th><th>Address</th>
                <th>Zone</th><th>Claim %</th><th>Alert Message</th>
              </tr>
            </thead>
            <tbody>
              {data.map(a => (
                <tr key={a.twin_id}>
                  <td><code style={{ color: '#DC2626', fontSize: 12 }}>{a.twin_id}</code></td>
                  <td>{a.policyholder}</td>
                  <td style={{ maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {a.address}
                  </td>
                  <td><span className={`badge badge-${a.flood_zone === 'Zone_A' ? 'red' : a.flood_zone === 'Zone_B' ? 'orange' : 'green'}`}>{a.flood_zone}</span></td>
                  <td><span style={{ color: '#DC2626', fontWeight: 700 }}>{(a.claim_prob * 100).toFixed(0)}%</span></td>
                  <td style={{ fontSize: 12, color: '#bbbbbb', maxWidth: 320, lineHeight: 1.4 }}>{a.alert_message}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ─── Main AgentsView ──────────────────────────────────────────────────────────
export default function AgentsView() {
  const { weatherOut, riskOut, claimsOut, fraudOut, reserveOut, resourceOut, alertsOut } = useIDTCC();
  const [activeTab, setActiveTab] = useState('weather');

  if (!weatherOut) return null;

  const panels = {
    weather:   <WeatherAgent   data={weatherOut} />,
    risk:      <RiskAgent      data={riskOut} />,
    claims:    <ClaimsAgent    data={claimsOut} />,
    fraud:     <FraudAgent     data={fraudOut} />,
    reserve:   <ReserveAgent   data={reserveOut} />,
    resources: <ResourcesAgent data={resourceOut} />,
    alerts:    <AlertsAgent    data={alertsOut} />,
  };

  return (
    <div style={{ maxWidth: 1440, margin: '0 auto', padding: '48px 24px' }}>
      {/* Tab bar */}
      <div style={{
        display: 'flex', gap: 0, overflowX: 'auto',
        borderBottom: '1px solid #3c3c3c', marginBottom: 40,
      }}>
        {AGENT_TABS.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              background: activeTab === tab.key ? '#1a1a1a' : 'transparent',
              color: activeTab === tab.key ? '#fff' : '#7e7e7e',
              border: 'none',
              borderBottom: activeTab === tab.key ? '2px solid #fff' : '2px solid transparent',
              padding: '12px 20px',
              fontSize: 12, fontWeight: 700, letterSpacing: 1.5,
              textTransform: 'uppercase', cursor: 'pointer',
              whiteSpace: 'nowrap', flexShrink: 0,
              fontFamily: 'Inter,sans-serif',
              transition: 'color 0.15s',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Panel */}
      {panels[activeTab]}
    </div>
  );
}
