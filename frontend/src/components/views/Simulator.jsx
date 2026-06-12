import { useState, useMemo } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, LineChart, Line, ReferenceLine,
} from 'recharts';
import { useIDTCC } from '../../context/IDTCCContext.jsx';
import { runSimulation, shiftTrack } from '../../data/cycloneEngine.js';
import { agentClaimsForecast, agentReserveCalculation } from '../../data/agents.js';

const TOOLTIP_STYLE = {
  contentStyle: { background: '#1a1a1a', border: '1px solid #3c3c3c', borderRadius: 0, color: '#fff' },
  labelStyle:   { color: '#bbbbbb', fontSize: 12 },
  itemStyle:    { color: '#e6e6e6', fontSize: 13 },
};

export default function Simulator() {
  const { baseTwins, cycloneParams, forecast } = useIDTCC();
  const [shiftKm, setShiftKm] = useState(0);
  const [isRunning, setIsRunning] = useState(false);
  const [result, setResult] = useState(null);

  const baseRedTwins   = forecast?.red_twins ?? 0;
  const baseLoss       = forecast?.expected_loss_crore ?? 0;

  // Sensitivity grid: pre-compute for chart
  const sensitivityGrid = useMemo(() => {
    if (!baseTwins) return [];
    return [-60, -40, -20, 0, 20, 40, 60].map(km => {
      const newTrack  = shiftTrack(cycloneParams.track, km);
      const newParams = { ...cycloneParams, track: newTrack };
      const simTwins  = runSimulation(baseTwins, newParams);
      const claims    = agentClaimsForecast(simTwins);
      return {
        shift:   `${km >= 0 ? '+' : ''}${km}km`,
        red:     Math.round((simTwins.filter(t => t.risk_color === 'red').length)),
        loss:    claims.expected_total_loss_crore,
        reserve: agentReserveCalculation(simTwins, claims).total_recommended_reserve_crore,
      };
    });
  }, [baseTwins, cycloneParams]);

  function runCounterfactual() {
    setIsRunning(true);
    setTimeout(() => {
      const newTrack  = shiftTrack(cycloneParams.track, shiftKm);
      const newParams = { ...cycloneParams, track: newTrack };
      const simTwins  = runSimulation(baseTwins, newParams);
      const claims    = agentClaimsForecast(simTwins);
      const reserve   = agentReserveCalculation(simTwins, claims);
      setResult({
        shift_km:   shiftKm,
        red_twins:  simTwins.filter(t => t.risk_color === 'red').length,
        loss:       claims.expected_total_loss_crore,
        reserve:    reserve.total_recommended_reserve_crore,
        claims,
        track:      newTrack,
      });
      setIsRunning(false);
    }, 10);
  }

  const delta = result ? result.loss - baseLoss : 0;

  return (
    <div style={{ maxWidth: 1440, margin: '0 auto', padding: '48px 24px' }}>
      <div style={{ marginBottom: 40 }}>
        <div className="m-stripe" style={{ width: 48, marginBottom: 12 }} />
        <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 4 }}>Counterfactual Analysis</div>
        <h2 className="display-sm">Storm Track Simulator</h2>
        <p className="body-md" style={{ marginTop: 8, maxWidth: 640 }}>
          Shift the cyclone track north or south to model alternate impact scenarios. Re-run simulation across all 50,000 property twins to see how the risk distribution and expected losses change.
        </p>
      </div>

      {/* Slider control */}
      <div className="card" style={{ marginBottom: 40 }}>
        <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 16 }}>Storm Track Shift</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 24, flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: 260 }}>
            <input
              type="range" min={-60} max={60} step={5}
              value={shiftKm}
              onChange={e => setShiftKm(Number(e.target.value))}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
              <span className="caption">−60km South</span>
              <span className="label-upper" style={{ color: shiftKm === 0 ? '#7e7e7e' : shiftKm > 0 ? '#1c69d4' : '#DC2626' }}>
                {shiftKm >= 0 ? `+${shiftKm}` : shiftKm}km {shiftKm > 0 ? 'North' : shiftKm < 0 ? 'South' : '(Baseline)'}
              </span>
              <span className="caption">+60km North</span>
            </div>
          </div>
          <button
            className="btn-primary"
            onClick={runCounterfactual}
            disabled={isRunning || !baseTwins}
            style={{ opacity: isRunning ? 0.6 : 1 }}
          >
            {isRunning ? 'Running...' : 'Rerun Simulation'}
          </button>
        </div>
      </div>

      {/* Counterfactual result */}
      {result && (
        <div style={{ marginBottom: 40 }}>
          <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 16 }}>
            Scenario Result — Track {result.shift_km >= 0 ? `+${result.shift_km}` : result.shift_km}km
          </div>
          <div className="grid-4">
            <div className="spec-cell">
              <div className="spec-cell__value" style={{ color: '#60A5FA' }}>
                {result.shift_km >= 0 ? `+${result.shift_km}` : result.shift_km}km
              </div>
              <div className="spec-cell__label">Track Shift</div>
            </div>
            <div className="spec-cell">
              <div className="spec-cell__value" style={{ color: '#DC2626' }}>
                {result.red_twins.toLocaleString('en-IN')}
              </div>
              <div className="spec-cell__label">Critical Twins</div>
              <div className="caption">vs baseline {baseRedTwins.toLocaleString('en-IN')}</div>
            </div>
            <div className="spec-cell">
              <div className="spec-cell__value" style={{ color: '#EA580C' }}>
                ₹{result.loss}Cr
              </div>
              <div className="spec-cell__label">Expected Loss</div>
              <div className="caption">vs baseline ₹{baseLoss}Cr</div>
            </div>
            <div className="spec-cell" style={{ borderColor: delta < 0 ? '#16A34A' : delta > 0 ? '#DC2626' : '#3c3c3c' }}>
              <div className="spec-cell__value" style={{ color: delta < 0 ? '#22C55E' : delta > 0 ? '#EF4444' : '#7e7e7e' }}>
                {delta < 0 ? '▼' : delta > 0 ? '▲' : '—'} ₹{Math.abs(delta).toFixed(1)}Cr
              </div>
              <div className="spec-cell__label">vs Baseline</div>
              <div className="caption">Reserve: ₹{result.reserve}Cr</div>
            </div>
          </div>
        </div>
      )}

      {/* Sensitivity grid */}
      <div className="grid-2" style={{ marginBottom: 48 }}>
        <div className="card">
          <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 16 }}>Red Twins vs Track Shift</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={sensitivityGrid} barCategoryGap="20%">
              <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
              <XAxis dataKey="shift" tick={{ fill: '#bbbbbb', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#bbbbbb', fontSize: 11 }} axisLine={false} tickLine={false}
                tickFormatter={v => v.toLocaleString('en-IN')} />
              <Tooltip {...TOOLTIP_STYLE} formatter={v => [v.toLocaleString('en-IN'), 'Red Twins']} />
              <ReferenceLine x="0km" stroke="#fff" strokeDasharray="4 2" label={{ value: 'Baseline', fill: '#7e7e7e', fontSize: 10 }} />
              <Bar dataKey="red" fill="#DC2626" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 16 }}>Expected Loss (₹Cr) vs Track Shift</div>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={sensitivityGrid}>
              <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
              <XAxis dataKey="shift" tick={{ fill: '#bbbbbb', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#bbbbbb', fontSize: 11 }} axisLine={false} tickLine={false}
                tickFormatter={v => `₹${v}`} />
              <Tooltip {...TOOLTIP_STYLE} formatter={v => [`₹${v}Cr`]} />
              <ReferenceLine x="0km" stroke="#fff" strokeDasharray="4 2" />
              <Line type="monotone" dataKey="loss" stroke="#EA580C" strokeWidth={2} dot={{ fill: '#EA580C', r: 3 }} name="Loss" />
              <Line type="monotone" dataKey="reserve" stroke="#1c69d4" strokeWidth={2} dot={{ fill: '#1c69d4', r: 3 }} strokeDasharray="5 3" name="Reserve" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Cyclone track coordinates */}
      <div className="card">
        <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 16 }}>
          Cyclone Track Waypoints — {result ? `Shifted ${result.shift_km >= 0 ? '+' : ''}${result.shift_km}km` : 'Baseline'}
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr><th>Hours to Landfall</th><th>Latitude</th><th>Longitude</th><th>Wind (km/h)</th></tr>
            </thead>
            <tbody>
              {(result?.track ?? cycloneParams.track).map((wp, i) => (
                <tr key={i}>
                  <td>T-{wp.hours_out}h</td>
                  <td>{wp.lat}°N</td>
                  <td>{wp.lng}°E</td>
                  <td style={{ color: wp.wind_kmh >= 180 ? '#DC2626' : wp.wind_kmh >= 130 ? '#EA580C' : '#F59E0B', fontWeight: 700 }}>
                    {wp.wind_kmh}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
