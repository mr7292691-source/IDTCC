import MStripe from './MStripe.jsx';

const FOOTER_COLS = [
  {
    title: 'LifeShield Platform',
    links: ['City Command', 'Alert Console', 'Live Map', 'Counterfactual Simulator'],
  },
  {
    title: 'Life-Safety Agents',
    links: ['Vulnerable Population', 'Shelter Allocation', 'Evacuation Planning', 'Rescue Priority'],
  },
  {
    title: 'Intelligence',
    links: ['Sensor Intelligence', 'Infrastructure Risk', 'Damage Assessment', 'LLM-as-Judge'],
  },
  {
    title: 'Technology',
    links: ['AMD Instinct MI300X', 'ROCm + vLLM', 'Qwen3-14B', 'LangGraph'],
  },
];

export default function Footer() {
  return (
    <footer style={{ background: '#000', borderTop: '1px solid #3c3c3c', marginTop: 96 }}>
      <MStripe />
      <div style={{ maxWidth: 1440, margin: '0 auto', padding: '64px 24px 40px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 24, marginBottom: 48 }}>
          {FOOTER_COLS.map(col => (
            <div key={col.title}>
              <p style={{ fontSize: 11, fontWeight: 700, letterSpacing: 1.5, textTransform: 'uppercase', color: '#7e7e7e', marginBottom: 16 }}>{col.title}</p>
              {col.links.map(link => (
                <p key={link} style={{ fontSize: 14, fontWeight: 300, color: '#7e7e7e', marginBottom: 8, lineHeight: 1.5 }}>{link}</p>
              ))}
            </div>
          ))}
        </div>

        <div style={{ borderTop: '1px solid #262626', paddingTop: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
          <p style={{ fontSize: 12, color: '#7e7e7e', letterSpacing: 0.5 }}>
            © 2025 LifeShield AI — Disaster Intelligence Platform. AMD AI Hackathon.
          </p>
          <p style={{ fontSize: 12, color: '#7e7e7e' }}>
            Powered by AMD Instinct MI300X · ROCm · vLLM · Qwen3-14B
          </p>
        </div>
      </div>
    </footer>
  );
}
