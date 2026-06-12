import { useIDTCC } from '../../context/IDTCCContext.jsx';
import { LOCATION_CATALOGUE } from '../../data/locationCatalogue.js';
import MStripe from './MStripe.jsx';

const NAV_ITEMS = [
  { key: 'command',   label: 'Command Center' },
  { key: 'portfolio', label: 'Portfolio' },
  { key: 'map',       label: 'Live Map' },
  { key: 'agents',    label: 'Agents' },
  { key: 'simulator', label: 'Simulator' },
  { key: 'safezones', label: 'Safe Zones' },
  { key: 'audit',     label: 'Audit' },
  { key: 'backend',   label: '⬡ Backend API' },
];

// BMW M logo as inline SVG (tricolor + M wordmark)
function BMWMLogo() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
      {/* M Tricolor badge */}
      <svg width="36" height="36" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect width="12" height="36" fill="#0066b1"/>
        <rect x="12" width="12" height="36" fill="#1c69d4"/>
        <rect x="24" width="12" height="36" fill="#e22718"/>
        <text x="18" y="24" textAnchor="middle" fontSize="18" fontWeight="700" fill="#fff" fontFamily="Inter,sans-serif">M</text>
      </svg>
      <div>
        <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: 2, textTransform: 'uppercase', color: '#7e7e7e', lineHeight: 1 }}>IDTCC</div>
        <div style={{ fontSize: 13, fontWeight: 700, letterSpacing: 1.5, textTransform: 'uppercase', color: '#fff', lineHeight: 1.2 }}>Insurance Digital Twin</div>
      </div>
    </div>
  );
}

export default function TopNav() {
  const { activeView, setActiveView, locationKey, changeLocation, isLoading, locations } = useIDTCC();

  return (
    <nav style={{
      position: 'sticky', top: 0, zIndex: 1000,
      background: '#000', borderBottom: '1px solid #3c3c3c',
    }}>
      <MStripe />
      <div style={{
        maxWidth: 1440, margin: '0 auto',
        padding: '0 24px',
        display: 'flex', alignItems: 'center', gap: 8,
        height: 64,
      }}>
        <BMWMLogo />

        {/* Nav links */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, flex: 1, marginLeft: 32, overflowX: 'auto' }}>
          {NAV_ITEMS.map(item => (
            <button
              key={item.key}
              onClick={() => setActiveView(item.key)}
              className={`btn-ghost${activeView === item.key ? ' active' : ''}`}
              style={{ padding: '0 12px', height: 64, flexShrink: 0 }}
            >
              {item.label}
            </button>
          ))}
        </div>

        {/* Location selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
          <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: 1.5, textTransform: 'uppercase', color: '#7e7e7e' }}>Location</span>
          <select
            value={locationKey}
            onChange={e => changeLocation(e.target.value)}
            disabled={isLoading}
            style={{
              background: '#1a1a1a', color: '#fff', border: '1px solid #3c3c3c',
              padding: '6px 12px', fontSize: 13, fontWeight: 700,
              letterSpacing: 1, textTransform: 'uppercase',
              cursor: 'pointer', outline: 'none', borderRadius: 0,
              fontFamily: 'Inter,sans-serif',
            }}
          >
            {locations?.groups?.length > 0
              ? locations.groups.map(group => (
                <optgroup key={group.state} label={group.state}>
                  {group.cities.map(city => (
                    <option key={city.code} value={city.code}>{city.name}</option>
                  ))}
                </optgroup>
              ))
              : Object.values(LOCATION_CATALOGUE).map(loc => (
                <option key={loc.key} value={loc.key}>{loc.name}</option>
              ))
            }
          </select>
        </div>
      </div>
    </nav>
  );
}
