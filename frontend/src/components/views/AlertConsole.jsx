import { useEffect, useState } from 'react';
import { useIDTCC } from '../../context/IDTCCContext.jsx';
import api from '../../api/client.js';

const LANG_LABEL = { en: 'English', ta: 'தமிழ் Tamil', hi: 'हिन्दी Hindi', te: 'తెలుగు Telugu', kn: 'ಕನ್ನಡ Kannada' };
const ALERT_TYPES = [
  { key: 'cyclone_warning', label: 'Cyclone Warning' },
  { key: 'flood_warning', label: 'Flood Warning' },
  { key: 'rescue_confirmation', label: 'Rescue Confirmation' },
];
const fmt = (n) => (n ?? 0).toLocaleString('en-IN');

export default function AlertConsole() {
  const { locationKey } = useIDTCC();
  const [meta, setMeta]       = useState({ languages: ['en', 'ta', 'hi', 'te', 'kn'], channels: [] });
  const [lang, setLang]       = useState('ta');
  const [alertType, setType]  = useState('cyclone_warning');
  const [preview, setPreview] = useState(null);
  const [name, setName]       = useState('Ravi Kumar');
  const [campaign, setCampaign] = useState(null);
  const [sending, setSending] = useState(false);

  useEffect(() => { api.alertMeta().then(setMeta).catch(() => {}); }, []);

  // Live preview on any change.
  useEffect(() => {
    let cancelled = false;
    api.previewAlert({
      alert_type: alertType, language: lang, name,
      hazard: 'NIVAR', eta_hours: 12, ward: 'Adyar',
      shelter: 'Govt School, GST Road', distance_km: 1.2, leave_by: '4 PM', helpline: '108',
    }).then((r) => { if (!cancelled) setPreview(r); }).catch(() => {});
    return () => { cancelled = true; };
  }, [lang, alertType, name]);

  async function dispatch() {
    setSending(true); setCampaign(null);
    try {
      const r = await api.dispatchAlerts({
        location_code: locationKey, twin_count: 5000, alert_type: alertType,
        max_alerts: 200, dry_run: true,
      });
      setCampaign(r);
    } catch { /* ignore */ } finally { setSending(false); }
  }

  const langPct = campaign?.by_language
    ? Object.entries(campaign.by_language).sort((a, b) => b[1] - a[1])
    : [];
  const maxLang = langPct.length ? Math.max(...langPct.map(([, v]) => v)) : 1;

  return (
    <div style={{ maxWidth: 1440, margin: '0 auto', padding: '48px 24px' }}>
      <div style={{ marginBottom: 32 }}>
        <div className="m-stripe" style={{ width: 48, marginBottom: 12 }} />
        <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 4 }}>LifeShield AI · Communication Layer</div>
        <h2 className="display-sm">Personalized Alert Console</h2>
        <p className="body-sm" style={{ marginTop: 6 }}>One named citizen. Their language. Their shelter. On a basic phone — no internet needed.</p>
      </div>

      <div className="grid-2" style={{ marginBottom: 40, alignItems: 'start' }}>
        {/* Composer */}
        <div className="card">
          <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 16 }}>Composer</div>

          <label className="caption" style={{ display: 'block', marginBottom: 6 }}>Citizen name</label>
          <input value={name} onChange={(e) => setName(e.target.value)}
            style={{ width: '100%', background: '#1a1a1a', color: '#fff', border: '1px solid #3c3c3c', padding: '8px 12px', marginBottom: 16, fontFamily: 'Inter,sans-serif' }} />

          <label className="caption" style={{ display: 'block', marginBottom: 6 }}>Alert type</label>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
            {ALERT_TYPES.map((t) => (
              <button key={t.key} onClick={() => setType(t.key)}
                className={`btn-ghost${alertType === t.key ? ' active' : ''}`}
                style={{ padding: '6px 12px', border: `1px solid ${alertType === t.key ? '#1c69d4' : '#3c3c3c'}`, color: alertType === t.key ? '#fff' : '#9a9a9a' }}>
                {t.label}
              </button>
            ))}
          </div>

          <label className="caption" style={{ display: 'block', marginBottom: 6 }}>Language</label>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {(meta.languages || []).map((l) => (
              <button key={l} onClick={() => setLang(l)}
                className={`btn-ghost${lang === l ? ' active' : ''}`}
                style={{ padding: '6px 12px', border: `1px solid ${lang === l ? '#1c69d4' : '#3c3c3c'}`, color: lang === l ? '#fff' : '#9a9a9a' }}>
                {LANG_LABEL[l] || l}
              </button>
            ))}
          </div>
        </div>

        {/* Phone preview */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 16, alignSelf: 'flex-start' }}>Live Preview</div>
          <div style={{ width: 280, border: '2px solid #3c3c3c', borderRadius: 24, padding: 16, background: '#0a0a0a' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
              <div style={{ width: 28, height: 28, borderRadius: '50%', background: '#1c69d4', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, fontWeight: 700 }}>🛡</div>
              <div>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#fff' }}>LifeShield</div>
                <div style={{ fontSize: 10, color: '#7e7e7e' }}>SMS · now</div>
              </div>
            </div>
            <div style={{ background: '#1a1a1a', borderRadius: 12, padding: 12, fontSize: 13, lineHeight: 1.5, color: '#e6e6e6', minHeight: 90, whiteSpace: 'pre-wrap' }}>
              {preview?.message || '…'}
            </div>
            <div className="caption" style={{ marginTop: 8, textAlign: 'right' }}>{preview?.chars ?? 0} chars · {LANG_LABEL[lang] || lang}</div>
          </div>
          <button className="btn-primary" onClick={dispatch} disabled={sending}
            style={{ marginTop: 24, padding: '0 24px', height: 44, background: sending ? '#3c3c3c' : '#1c69d4', color: '#fff', border: 'none', fontWeight: 700, letterSpacing: 1, textTransform: 'uppercase', cursor: sending ? 'default' : 'pointer' }}>
            {sending ? 'Dispatching…' : `Dispatch Campaign · ${locationKey}`}
          </button>
          <div className="caption" style={{ marginTop: 8 }}>Simulated delivery — no live gateway, no real numbers</div>
        </div>
      </div>

      {/* Campaign results */}
      {campaign && (
        <>
          <div className="grid-4" style={{ marginBottom: 24 }}>
            <div className="spec-cell"><div className="spec-cell__value">{fmt(campaign.total_targeted)}</div><div className="spec-cell__label">Citizens Targeted</div></div>
            <div className="spec-cell"><div className="spec-cell__value" style={{ color: '#16A34A' }}>{fmt(campaign.delivered)}</div><div className="spec-cell__label">Deliveries</div><div className="caption">across channels</div></div>
            <div className="spec-cell"><div className="spec-cell__value" style={{ color: campaign.denied ? '#DC2626' : '#16A34A' }}>{fmt(campaign.denied)}</div><div className="spec-cell__label">Access Denied</div><div className="caption">RBAC enforced</div></div>
            <div className="spec-cell"><div className="spec-cell__value" style={{ color: '#1c69d4' }}>{Object.keys(campaign.by_channel || {}).length}</div><div className="spec-cell__label">Channels Used</div></div>
          </div>

          <div className="grid-2" style={{ marginBottom: 40 }}>
            <div className="card">
              <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 16 }}>Delivery by Channel</div>
              {Object.entries(campaign.by_channel || {}).map(([ch, v]) => (
                <div key={ch} style={{ marginBottom: 12 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span className="body-sm" style={{ textTransform: 'capitalize' }}>{ch}{['sms', 'voice'].includes(ch) ? ' · offline-safe' : ''}</span>
                    <span className="body-sm">{fmt(v)}</span>
                  </div>
                  <div style={{ height: 4, background: '#262626' }}>
                    <div style={{ width: `${Math.min(100, (v / (campaign.delivered || 1)) * 100)}%`, height: '100%', background: ['sms', 'voice'].includes(ch) ? '#16A34A' : '#1c69d4' }} />
                  </div>
                </div>
              ))}
            </div>
            <div className="card">
              <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 16 }}>Targeted by Language</div>
              {langPct.map(([l, v]) => (
                <div key={l} style={{ marginBottom: 12 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span className="body-sm">{LANG_LABEL[l] || l}</span>
                    <span className="body-sm">{fmt(v)}</span>
                  </div>
                  <div style={{ height: 4, background: '#262626' }}>
                    <div style={{ width: `${(v / maxLang) * 100}%`, height: '100%', background: '#EA580C' }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="card">
            <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 16 }}>Sample Delivered Messages (masked receipts · privacy vault)</div>
            <div style={{ overflowX: 'auto' }}>
              <table className="data-table">
                <thead><tr><th>Citizen</th><th>Ward</th><th>Lang</th><th>Channels</th><th>To</th><th>Message</th></tr></thead>
                <tbody>
                  {(campaign.sample || []).map((s, i) => (
                    <tr key={i}>
                      <td style={{ fontSize: 12 }}>{s.citizen_id}</td>
                      <td style={{ fontSize: 12 }}>{s.ward}</td>
                      <td><span className="badge badge-blue">{s.language}</span></td>
                      <td style={{ fontSize: 11 }}>{(s.channels || []).join(', ')}</td>
                      <td style={{ fontSize: 11, fontFamily: 'monospace' }}>{s.receipt?.to || '—'}</td>
                      <td style={{ fontSize: 11, maxWidth: 360 }}>{s.message}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
