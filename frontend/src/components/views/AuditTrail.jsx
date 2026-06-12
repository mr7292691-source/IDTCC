import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer, Legend,
} from 'recharts';
import { useIDTCC } from '../../context/IDTCCContext.jsx';

const PRED_COLORS = {
  weather:     '#3B82F6',
  claims:      '#F59E0B',
  safe_spaces: '#8B5CF6',
  reserve:     '#10B981',
};
const PRED_LABELS = {
  weather:     'Weather Intel',
  claims:      'Claims Forecast',
  safe_spaces: 'Safe Space Plan',
  reserve:     'Reserve Forecast',
};
const CRITERIA = [
  { key: 'factual_accuracy',           label: 'Factual Accuracy' },
  { key: 'completeness',               label: 'Completeness' },
  { key: 'actionability',              label: 'Actionability' },
  { key: 'vulnerable_population_safety', label: 'Vuln. Safety' },
  { key: 'financial_soundness',        label: 'Financial' },
];

const VERDICT_COLORS = { APPROVED: '#16A34A', REVIEW_NEEDED: '#CA8A04', REJECTED: '#DC2626' };

export default function AuditTrail() {
  const { judgeOut } = useIDTCC();
  if (!judgeOut) return null;

  // Build radar data
  const radarData = CRITERIA.map(c => {
    const entry = { criterion: c.label };
    for (const [key, res] of Object.entries(judgeOut)) {
      entry[PRED_LABELS[key]] = res.scores?.[c.key] ?? 7.5;
    }
    return entry;
  });

  const auditRows = Object.entries(judgeOut).map(([key, res]) => ({
    prediction: PRED_LABELS[key],
    verdict:    res.verdict,
    score:      res.overall_score,
    critique:   res.critique,
    improvements: res.improvements,
    approved:   res.approved,
    timestamp:  res.timestamp,
    color:      PRED_COLORS[key],
  }));

  return (
    <div style={{ maxWidth: 1440, margin: '0 auto', padding: '48px 24px' }}>
      <div style={{ marginBottom: 40 }}>
        <div className="m-stripe" style={{ width: 48, marginBottom: 12 }} />
        <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 4 }}>Governance & Transparency</div>
        <h2 className="display-sm">LLM-as-Judge Audit Trail</h2>
        <p className="body-md" style={{ marginTop: 8, maxWidth: 640 }}>
          An independent evaluator agent critiques every IDTCC prediction on five criteria. Verdicts gate downstream decisions — no output is communicated without an APPROVED verdict.
        </p>
      </div>

      {/* Summary KPIs */}
      <div className="grid-4" style={{ marginBottom: 40 }}>
        {auditRows.map(r => (
          <div key={r.prediction} className="spec-cell" style={{ borderLeft: `3px solid ${r.color}` }}>
            <div className="spec-cell__value" style={{ color: r.color }}>{r.score}/10</div>
            <div className="spec-cell__label">{r.prediction}</div>
            <div className="caption" style={{ color: VERDICT_COLORS[r.verdict] ?? '#7e7e7e', marginTop: 4 }}>
              {r.verdict}
            </div>
          </div>
        ))}
      </div>

      {/* Radar chart */}
      <div className="card" style={{ marginBottom: 40 }}>
        <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 16 }}>
          Prediction Quality Radar — 5 Evaluation Criteria
        </div>
        <ResponsiveContainer width="100%" height={380}>
          <RadarChart data={radarData} cx="50%" cy="50%" outerRadius="70%">
            <PolarGrid stroke="#262626" />
            <PolarAngleAxis
              dataKey="criterion"
              tick={{ fill: '#bbbbbb', fontSize: 12, fontFamily: 'Inter,sans-serif' }}
            />
            <PolarRadiusAxis angle={90} domain={[0, 10]} tick={{ fill: '#7e7e7e', fontSize: 10 }} />
            {auditRows.map(r => (
              <Radar
                key={r.prediction}
                name={r.prediction}
                dataKey={r.prediction}
                stroke={r.color}
                fill={r.color}
                fillOpacity={0.20}
                strokeWidth={2}
              />
            ))}
            <Legend
              formatter={v => <span style={{ color: '#bbbbbb', fontSize: 12 }}>{v}</span>}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      {/* Detailed audit cards */}
      <div className="grid-2" style={{ marginBottom: 40 }}>
        {auditRows.map(r => (
          <div key={r.prediction} className="card" style={{ borderTop: `3px solid ${r.color}` }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
              <div>
                <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 4 }}>{r.prediction}</div>
                <div style={{ fontSize: 24, fontWeight: 700, color: r.color }}>{r.score}/10</div>
              </div>
              <span
                className="badge"
                style={{ background: VERDICT_COLORS[r.verdict] ?? '#7e7e7e', color: '#fff' }}
              >
                {r.verdict}
              </span>
            </div>

            {/* Per-criterion scores */}
            <div style={{ marginBottom: 16 }}>
              {CRITERIA.map(c => {
                const score = judgeOut[Object.keys(PRED_LABELS).find(k => PRED_LABELS[k] === r.prediction)]?.scores?.[c.key] ?? 7.5;
                return (
                  <div key={c.key} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                    <span style={{ fontSize: 11, color: '#7e7e7e', width: 120, flexShrink: 0 }}>{c.label}</span>
                    <div style={{ flex: 1, height: 4, background: '#262626' }}>
                      <div style={{ width: `${score * 10}%`, height: '100%', background: r.color }} />
                    </div>
                    <span style={{ fontSize: 12, color: '#e6e6e6', width: 30, textAlign: 'right' }}>{score}</span>
                  </div>
                );
              })}
            </div>

            <div style={{ marginBottom: 12 }}>
              <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 6, fontSize: 11 }}>Critique</div>
              <p className="body-sm" style={{ lineHeight: 1.6 }}>{r.critique}</p>
            </div>

            <div>
              <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 6, fontSize: 11 }}>Improvements</div>
              {r.improvements.map((imp, i) => (
                <p key={i} className="body-sm" style={{ marginBottom: 4, paddingLeft: 12, borderLeft: `2px solid ${r.color}` }}>
                  {imp}
                </p>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Audit trail table */}
      <div className="card">
        <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 16 }}>Regulatory Audit Trail</div>
        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Prediction</th><th>Verdict</th><th>Score</th>
                <th>Approved</th><th>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {auditRows.map(r => (
                <tr key={r.prediction}>
                  <td style={{ color: r.color, fontWeight: 700 }}>{r.prediction}</td>
                  <td>
                    <span className="badge" style={{ background: VERDICT_COLORS[r.verdict] ?? '#7e7e7e', color: '#fff' }}>
                      {r.verdict}
                    </span>
                  </td>
                  <td style={{ fontWeight: 700 }}>{r.score}/10</td>
                  <td>
                    <span style={{ color: r.approved ? '#22C55E' : '#EF4444', fontWeight: 700, fontSize: 14 }}>
                      {r.approved ? '✓ Yes' : '✗ No'}
                    </span>
                  </td>
                  <td className="caption">{r.timestamp?.slice(0, 19).replace('T', ' ')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Value proposition */}
      <div className="grid-2" style={{ marginTop: 48 }}>
        <div className="card" style={{ borderTop: '3px solid #1c69d4' }}>
          <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 12 }}>Value to Customer</div>
          <div className="title-md" style={{ marginBottom: 16 }}>Policyholder Protection</div>
          {[
            'Personalised risk alerts 48h before landfall — time to evacuate safely',
            'Every prediction verified by independent LLM-as-Judge before communication',
            'Safe shelters pre-stocked with baby formula, medicine, water, and food',
          ].map((b, i) => (
            <div key={i} style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
              <div style={{ width: 4, height: 4, borderRadius: '50%', background: '#1c69d4', marginTop: 9, flexShrink: 0 }} />
              <p className="body-md">{b}</p>
            </div>
          ))}
        </div>
        <div className="card" style={{ borderTop: '3px solid #e22718' }}>
          <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 12 }}>Value to Insurer</div>
          <div className="title-md" style={{ marginBottom: 16 }}>Operational Excellence</div>
          {[
            'Reserve calculated 48h early — capital efficiency and IRDAI compliance',
            'FAISS + rule-based fraud detection before claims are filed',
            'AMD Instinct MI300X scores 50,000 twins in seconds — on-premise sovereignty',
          ].map((b, i) => (
            <div key={i} style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
              <div style={{ width: 4, height: 4, borderRadius: '50%', background: '#e22718', marginTop: 9, flexShrink: 0 }} />
              <p className="body-md">{b}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
