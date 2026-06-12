import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  Cell, CartesianGrid, LineChart, Line,
} from 'recharts';
import { useIDTCC } from '../../context/IDTCCContext.jsx';

const COLORS = { red: '#DC2626', orange: '#EA580C', yellow: '#CA8A04', green: '#16A34A' };

function KPIBlock({ value, label, color = '#fff', sub }) {
  return (
    <div className="spec-cell" style={{ borderLeft: `3px solid ${color}` }}>
      <div className="spec-cell__value" style={{ color }}>{value}</div>
      <div className="spec-cell__label">{label}</div>
      {sub && <div className="caption" style={{ marginTop: 6 }}>{sub}</div>}
    </div>
  );
}

const TOOLTIP_STYLE = {
  contentStyle: { background: '#1a1a1a', border: '1px solid #3c3c3c', borderRadius: 0, color: '#fff' },
  labelStyle:   { color: '#bbbbbb', fontSize: 12 },
  itemStyle:    { color: '#e6e6e6', fontSize: 13 },
};

export default function CommandCenter() {
  const { forecast, claimsOut, twins, cycloneParams, riskOut, resourceOut, fraudOut, reserveOut } = useIDTCC();
  if (!forecast) return null;

  // Risk breakdown for mini bar chart
  const riskBreakdown = ['red','orange','yellow','green'].map(c => ({
    name: c.charAt(0).toUpperCase() + c.slice(1),
    count: twins.filter(t => t.risk_color === c).length,
    color: COLORS[c],
  }));

  // Top 8 loss areas
  const areaLossData = Object.entries(forecast.top_loss_areas)
    .slice(0, 8)
    .map(([area, loss]) => ({ area, loss }));

  // Zone claim data
  const zoneClaimData = Object.entries(riskOut.by_flood_zone).map(([zone, v]) => ({
    zone, count: v.count, avg_prob: +(v.avg_prob * 100).toFixed(1),
    total_loss: v.total_loss_cr,
  }));

  // Reserve sensitivity (base scenario ±2)
  const sensSample = reserveOut.reserve_sensitivity.filter((_, i) => [0,1,2,3,4,5,6].includes(i));

  const fmtCr = v => `₹${v}Cr`;

  return (
    <div style={{ maxWidth: 1440, margin: '0 auto', padding: '48px 24px 0' }}>

      {/* Hero band */}
      <div style={{ marginBottom: 48 }}>
        <div className="label-upper" style={{ color: '#0066b1', marginBottom: 8 }}>
          AMD AI Hackathon · Insurance Digital Twin Command Center
        </div>
        <h1 className="display-lg" style={{ marginBottom: 8 }}>
          CYCLONE {forecast.event_name}
        </h1>
        <div style={{ display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap', marginBottom: 16 }}>
          <span className="label-upper" style={{ color: '#e22718' }}>⚠ T-{forecast.landfall_eta_hours}H TO LANDFALL</span>
          <span className="caption">Simulation: {forecast.simulation_timestamp}</span>
          <span className="caption">{cycloneParams.category} · {cycloneParams.max_wind_kmh} km/h · {cycloneParams.radius_km} km radius</span>
        </div>
        <div className="m-stripe" style={{ width: 120 }} />
      </div>

      {/* KPI grid */}
      <div className="grid-4" style={{ marginBottom: 48 }}>
        <KPIBlock
          value={forecast.red_twins.toLocaleString('en-IN')}
          label="Critical Twins (p≥70%)"
          color="#DC2626"
          sub={`of ${forecast.total_portfolio_twins.toLocaleString('en-IN')} portfolio`}
        />
        <KPIBlock
          value={`₹${forecast.expected_loss_crore}Cr`}
          label="Expected Loss"
          color="#EA580C"
          sub={`Reserve: ₹${forecast.reserve_required_crore}Cr`}
        />
        <KPIBlock
          value={forecast.adjusters_needed}
          label="Adjusters Needed"
          color="#1c69d4"
          sub={`across ${forecast.deployment_zones} geospatial zones`}
        />
        <KPIBlock
          value={forecast.fraud_risk_twins}
          label="Fraud Risk Flags"
          color="#7C3AED"
          sub={`${forecast.storm_severity_index}/10 severity index`}
        />
      </div>

      {/* Executive Summary */}
      <div style={{ background: '#0d0d0d', border: '1px solid #3c3c3c', padding: 32, marginBottom: 48 }}>
        <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 12 }}>Executive Summary · AI Chief Risk Officer</div>
        <p style={{ fontSize: 16, fontWeight: 300, lineHeight: 1.7, color: '#e6e6e6', maxWidth: 900 }}>
          {forecast.executive_summary}
        </p>
        <div className="m-stripe" style={{ marginTop: 24, width: '100%' }} />
      </div>

      {/* Charts row 1 */}
      <div className="grid-2" style={{ marginBottom: 48 }}>
        {/* Risk Distribution */}
        <div className="card">
          <div className="label-upper" style={{ marginBottom: 16, color: '#7e7e7e' }}>Risk Distribution — 50K Twins</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={riskBreakdown} barCategoryGap="30%">
              <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
              <XAxis dataKey="name" tick={{ fill: '#bbbbbb', fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#bbbbbb', fontSize: 11 }} axisLine={false} tickLine={false}
                tickFormatter={v => v.toLocaleString('en-IN')} />
              <Tooltip {...TOOLTIP_STYLE} formatter={v => [v.toLocaleString('en-IN'), 'Properties']} />
              <Bar dataKey="count" radius={[0,0,0,0]}>
                {riskBreakdown.map(d => <Cell key={d.name} fill={d.color} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Top Loss Areas */}
        <div className="card">
          <div className="label-upper" style={{ marginBottom: 16, color: '#7e7e7e' }}>Expected Loss by Area (₹ Crore)</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={areaLossData} barCategoryGap="25%">
              <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
              <XAxis dataKey="area" tick={{ fill: '#bbbbbb', fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#bbbbbb', fontSize: 11 }} axisLine={false} tickLine={false}
                tickFormatter={v => `₹${v}`} />
              <Tooltip {...TOOLTIP_STYLE} formatter={v => [`₹${v}Cr`, 'Expected Loss']} />
              <Bar dataKey="loss" fill="#DC2626" radius={[0,0,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Charts row 2 */}
      <div className="grid-2" style={{ marginBottom: 48 }}>
        {/* Flood Zone breakdown */}
        <div className="card">
          <div className="label-upper" style={{ marginBottom: 16, color: '#7e7e7e' }}>Claim Count by Flood Zone</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={zoneClaimData} barCategoryGap="30%">
              <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
              <XAxis dataKey="zone" tick={{ fill: '#bbbbbb', fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#bbbbbb', fontSize: 11 }} axisLine={false} tickLine={false}
                tickFormatter={v => v.toLocaleString('en-IN')} />
              <Tooltip {...TOOLTIP_STYLE} formatter={(v, n) => [n === 'count' ? v.toLocaleString('en-IN') : `${v}%`, n]} />
              <Bar dataKey="count" fill="#EF4444" name="count" />
              <Bar dataKey="avg_prob" fill="#1c69d4" name="avg_prob %" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Reserve sensitivity */}
        <div className="card">
          <div className="label-upper" style={{ marginBottom: 16, color: '#7e7e7e' }}>Reserve Sensitivity — Wind Scenarios</div>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={sensSample}>
              <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
              <XAxis dataKey="scenario" tick={{ fill: '#bbbbbb', fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#bbbbbb', fontSize: 11 }} axisLine={false} tickLine={false}
                tickFormatter={v => `₹${v}`} />
              <Tooltip {...TOOLTIP_STYLE} formatter={v => [`₹${v}Cr`]} />
              <Line type="monotone" dataKey="reserve" stroke="#1c69d4" strokeWidth={2} dot={false} name="Reserve" />
              <Line type="monotone" dataKey="reserve_ibnr" stroke="#e22718" strokeWidth={2} dot={false} name="Reserve+IBNR" strokeDasharray="5 3" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Impact stats row */}
      <div className="grid-4" style={{ marginBottom: 48 }}>
        <div className="spec-cell">
          <div className="spec-cell__value">{riskOut.twins_in_impact_radius.toLocaleString('en-IN')}</div>
          <div className="spec-cell__label">In Impact Radius</div>
          <div className="caption">{riskOut.exposure_pct}% of portfolio</div>
        </div>
        <div className="spec-cell">
          <div className="spec-cell__value">{forecast.expected_claim_count.toLocaleString('en-IN')}</div>
          <div className="spec-cell__label">Expected Claims</div>
          <div className="caption">probabilistic count</div>
        </div>
        <div className="spec-cell">
          <div className="spec-cell__value">{`₹${(claimsOut.avg_loss_per_claim_inr/100000).toFixed(1)}L`}</div>
          <div className="spec-cell__label">Avg Loss / Claim</div>
          <div className="caption">high-risk properties (p&gt;30%)</div>
        </div>
        <div className="spec-cell">
          <div className="spec-cell__value">{forecast.primary_hazards[0]}</div>
          <div className="spec-cell__label">Primary Hazard</div>
          <div className="caption">{forecast.primary_hazards.slice(1, 3).join(' · ')}</div>
        </div>
      </div>

      {/* Primary hazards band */}
      <div style={{ borderTop: '1px solid #3c3c3c', paddingTop: 32, marginBottom: 48, display: 'flex', flexWrap: 'wrap', gap: 12 }}>
        <span className="label-upper" style={{ color: '#7e7e7e', alignSelf: 'center' }}>Active Hazards</span>
        {forecast.primary_hazards.map(h => (
          <span key={h} className="badge badge-red">{h}</span>
        ))}
        <span className="badge badge-blue">Severity {forecast.storm_severity_index}/10</span>
        <span className="badge badge-purple">{cycloneParams.category}</span>
      </div>
    </div>
  );
}
