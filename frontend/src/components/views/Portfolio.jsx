import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, CartesianGrid, Legend,
} from 'recharts';
import { useIDTCC } from '../../context/IDTCCContext.jsx';

const PIE_COLORS = ['#3B82F6','#10B981','#F59E0B','#EF4444','#8B5CF6'];
const TOOLTIP_STYLE = {
  contentStyle: { background: '#1a1a1a', border: '1px solid #3c3c3c', borderRadius: 0, color: '#fff' },
  labelStyle:   { color: '#bbbbbb', fontSize: 12 },
  itemStyle:    { color: '#e6e6e6', fontSize: 13 },
};

function SectionTitle({ children }) {
  return (
    <div style={{ marginBottom: 32 }}>
      <div className="m-stripe" style={{ width: 48, marginBottom: 12 }} />
      <h2 className="display-sm">{children}</h2>
    </div>
  );
}

export default function Portfolio() {
  const { baseTwins } = useIDTCC();
  if (!baseTwins) return null;

  // 1. Vulnerability histogram (30 bins)
  const vulnMin = 0, vulnMax = 1, bins = 20;
  const binSize = (vulnMax - vulnMin) / bins;
  const vulnBins = Array.from({ length: bins }, (_, i) => ({
    range: `${(vulnMin + i * binSize).toFixed(2)}`,
    count: 0,
  }));
  for (const t of baseTwins) {
    const idx = Math.min(Math.floor((t.vulnerability_index - vulnMin) / binSize), bins - 1);
    vulnBins[idx].count++;
  }

  // 2. Construction type pie
  const ctCount = {};
  for (const t of baseTwins) ctCount[t.construction_type] = (ctCount[t.construction_type] || 0) + 1;
  const ctData = Object.entries(ctCount).map(([name, value]) => ({
    name: name.replace(/_/g, ' '),
    value,
  })).sort((a, b) => b.value - a.value);

  // 3. Flood zone exposure (total sum insured)
  const zoneExposure = { Zone_A: 0, Zone_B: 0, Zone_C: 0 };
  for (const t of baseTwins) zoneExposure[t.flood_zone] = (zoneExposure[t.flood_zone] || 0) + t.sum_insured_inr;
  const zoneData = Object.entries(zoneExposure).map(([zone, total]) => ({
    zone, total_cr: parseFloat((total / 1e7).toFixed(1)),
  }));

  // 4. Median sum insured by area (top 10)
  const areaValues = {};
  for (const t of baseTwins) {
    if (!areaValues[t.area]) areaValues[t.area] = [];
    areaValues[t.area].push(t.sum_insured_inr);
  }
  const medianData = Object.entries(areaValues)
    .map(([area, vals]) => {
      const sorted = [...vals].sort((a, b) => a - b);
      const mid = Math.floor(sorted.length / 2);
      return { area, median_L: parseFloat((sorted[mid] / 1e5).toFixed(1)) };
    })
    .sort((a, b) => b.median_L - a.median_L)
    .slice(0, 10);

  // 5. Decade distribution
  const decadeCount = {};
  for (const t of baseTwins) decadeCount[t.decade] = (decadeCount[t.decade] || 0) + 1;
  const decadeData = Object.entries(decadeCount)
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([decade, count]) => ({ decade, count }));

  // 6. Top 15 most vulnerable
  const top15 = [...baseTwins]
    .sort((a, b) => b.vulnerability_index - a.vulnerability_index)
    .slice(0, 15);

  // Stats summary
  const avgVuln = (baseTwins.reduce((s, t) => s + t.vulnerability_index, 0) / baseTwins.length).toFixed(3);
  const totalExposureCr = (baseTwins.reduce((s, t) => s + t.sum_insured_inr, 0) / 1e7).toFixed(0);
  const zoneACount = baseTwins.filter(t => t.flood_zone === 'Zone_A').length;

  return (
    <div style={{ maxWidth: 1440, margin: '0 auto', padding: '48px 24px' }}>
      <SectionTitle>Portfolio Baseline — Pre-Event</SectionTitle>

      {/* Summary KPIs */}
      <div className="grid-4" style={{ marginBottom: 48 }}>
        <div className="spec-cell">
          <div className="spec-cell__value">{baseTwins.length.toLocaleString('en-IN')}</div>
          <div className="spec-cell__label">Total Twins</div>
        </div>
        <div className="spec-cell">
          <div className="spec-cell__value">₹{totalExposureCr}Cr</div>
          <div className="spec-cell__label">Total Exposure</div>
        </div>
        <div className="spec-cell">
          <div className="spec-cell__value">{avgVuln}</div>
          <div className="spec-cell__label">Avg Vulnerability Score</div>
        </div>
        <div className="spec-cell">
          <div className="spec-cell__value">{zoneACount.toLocaleString('en-IN')}</div>
          <div className="spec-cell__label">High-Risk Zone A</div>
          <div className="caption">{(zoneACount / baseTwins.length * 100).toFixed(1)}% of portfolio</div>
        </div>
      </div>

      {/* Row 1: Vulnerability + Construction */}
      <div className="grid-2" style={{ marginBottom: 48 }}>
        <div className="card">
          <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 16 }}>Vulnerability Score Distribution</div>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={vulnBins} barCategoryGap="5%">
              <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
              <XAxis dataKey="range" tick={{ fill: '#bbbbbb', fontSize: 9 }} axisLine={false} tickLine={false}
                interval={4} />
              <YAxis tick={{ fill: '#bbbbbb', fontSize: 11 }} axisLine={false} tickLine={false}
                tickFormatter={v => (v/1000).toFixed(0)+'K'} />
              <Tooltip {...TOOLTIP_STYLE} formatter={v => [v.toLocaleString('en-IN'), 'Properties']} />
              <Bar dataKey="count" fill="#6366F1" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card" style={{ display: 'flex', flexDirection: 'column' }}>
          <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 16 }}>Construction Type Breakdown</div>
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie data={ctData} cx="50%" cy="50%" innerRadius={60} outerRadius={100}
                dataKey="value" nameKey="name" label={({ name, percent }) => `${(percent*100).toFixed(0)}%`}
                labelLine={false} fontSize={11} fill="#fff">
                {ctData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
              </Pie>
              <Legend formatter={v => <span style={{ color: '#bbbbbb', fontSize: 12 }}>{v}</span>} />
              <Tooltip {...TOOLTIP_STYLE} formatter={v => [v.toLocaleString('en-IN'), 'Properties']} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Row 2: Zone Exposure + Median SI */}
      <div className="grid-2" style={{ marginBottom: 48 }}>
        <div className="card">
          <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 16 }}>Total Exposure by Flood Zone (₹ Crore)</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={zoneData} barCategoryGap="40%">
              <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
              <XAxis dataKey="zone" tick={{ fill: '#bbbbbb', fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#bbbbbb', fontSize: 11 }} axisLine={false} tickLine={false}
                tickFormatter={v => `₹${v}`} />
              <Tooltip {...TOOLTIP_STYLE} formatter={v => [`₹${v}Cr`, 'Total Exposure']} />
              <Bar dataKey="total_cr" fill="#3B82F6" radius={[0,0,0,0]}>
                {zoneData.map((d, i) => (
                  <Cell key={i} fill={d.zone === 'Zone_A' ? '#EF4444' : d.zone === 'Zone_B' ? '#F97316' : '#22C55E'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 16 }}>Median Sum Insured by Area (₹ Lakh)</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={medianData} barCategoryGap="20%">
              <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
              <XAxis dataKey="area" tick={{ fill: '#bbbbbb', fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#bbbbbb', fontSize: 11 }} axisLine={false} tickLine={false}
                tickFormatter={v => `${v}L`} />
              <Tooltip {...TOOLTIP_STYLE} formatter={v => [`₹${v}L`, 'Median SI']} />
              <Bar dataKey="median_L" fill="#3B82F6" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Row 3: Age distribution */}
      <div className="card" style={{ marginBottom: 48 }}>
        <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 16 }}>Property Age Distribution (by Decade Built)</div>
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={decadeData} barCategoryGap="25%">
            <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
            <XAxis dataKey="decade" tick={{ fill: '#bbbbbb', fontSize: 12 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: '#bbbbbb', fontSize: 11 }} axisLine={false} tickLine={false}
              tickFormatter={v => v.toLocaleString('en-IN')} />
            <Tooltip {...TOOLTIP_STYLE} formatter={v => [v.toLocaleString('en-IN'), 'Properties']} />
            <Bar dataKey="count" fill="#8B5CF6" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Top 15 vulnerable table */}
      <div className="card">
        <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 16 }}>Top 15 Most Vulnerable Properties</div>
        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Twin ID</th><th>Area</th><th>Construction</th>
                <th>Flood Zone</th><th>Vuln. Score</th><th>Year Built</th>
              </tr>
            </thead>
            <tbody>
              {top15.map(t => (
                <tr key={t.twin_id}>
                  <td><code style={{ fontSize: 12, color: '#6366F1' }}>{t.twin_id}</code></td>
                  <td>{t.area}</td>
                  <td style={{ textTransform: 'capitalize' }}>{t.construction_type.replace(/_/g,' ')}</td>
                  <td><span className={`badge badge-${t.flood_zone === 'Zone_A' ? 'red' : t.flood_zone === 'Zone_B' ? 'orange' : 'green'}`}>{t.flood_zone}</span></td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <div style={{ width: 60, height: 6, background: '#262626', borderRadius: 0, overflow: 'hidden' }}>
                        <div style={{ width: `${t.vulnerability_index * 100}%`, height: '100%', background: t.vulnerability_index > 0.7 ? '#DC2626' : t.vulnerability_index > 0.5 ? '#EA580C' : '#CA8A04' }} />
                      </div>
                      <span style={{ fontSize: 13 }}>{t.vulnerability_index}</span>
                    </div>
                  </td>
                  <td>{t.year_built}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
