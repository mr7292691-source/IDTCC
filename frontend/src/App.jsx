import { useIDTCC } from './context/IDTCCContext.jsx';
import TopNav from './components/Layout/TopNav.jsx';
import Footer from './components/Layout/Footer.jsx';
import CommandCenter from './components/views/CommandCenter.jsx';
import Portfolio from './components/views/Portfolio.jsx';
import LiveMap from './components/views/LiveMap.jsx';
import AgentsView from './components/views/AgentsView.jsx';
import Simulator from './components/views/Simulator.jsx';
import SafeZones from './components/views/SafeZones.jsx';
import AuditTrail from './components/views/AuditTrail.jsx';
import BackendView from './components/views/BackendView.jsx';
import LifeShield from './components/views/LifeShield.jsx';
import AlertConsole from './components/views/AlertConsole.jsx';

function LoadingScreen({ message }) {
  return (
    <div className="loading-screen">
      {/* M Stripe at top */}
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0 }}>
        <div className="m-stripe" />
      </div>

      {/* BMW M Logo */}
      <svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect width="21.3" height="64" fill="#0066b1"/>
        <rect x="21.3" width="21.3" height="64" fill="#1c69d4"/>
        <rect x="42.6" width="21.4" height="64" fill="#e22718"/>
        <text x="32" y="42" textAnchor="middle" fontSize="32" fontWeight="700" fill="#fff" fontFamily="Inter,sans-serif">M</text>
      </svg>

      <div style={{ textAlign: 'center' }}>
        <div className="label-upper" style={{ color: '#7e7e7e', marginBottom: 8 }}>AMD AI Hackathon</div>
        <h1 className="display-sm" style={{ marginBottom: 4 }}>LifeShield AI</h1>
        <p className="body-sm">Before The Storm Hits, We Already Know</p>
      </div>

      <div className="spinner" />

      <p className="body-sm" style={{ maxWidth: 360, textAlign: 'center' }}>
        {message}
      </p>

      <div className="caption" style={{ position: 'absolute', bottom: 24 }}>
        Citizen + property digital twins · 16 agents · AMD Instinct MI300X · vLLM · LangGraph
      </div>
    </div>
  );
}

const VIEW_COMPONENTS = {
  command:    CommandCenter,
  lifeshield: LifeShield,
  alerts:     AlertConsole,
  portfolio:  Portfolio,
  map:        LiveMap,
  agents:     AgentsView,
  simulator:  Simulator,
  safezones:  SafeZones,
  audit:      AuditTrail,
  backend:    BackendView,
};

export default function App() {
  const { isLoading, loadingMsg, activeView } = useIDTCC();

  if (isLoading) return <LoadingScreen message={loadingMsg} />;

  const ViewComponent = VIEW_COMPONENTS[activeView] ?? CommandCenter;
  const isMapView     = activeView === 'map';

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <TopNav />
      <main style={{ flex: 1 }}>
        <ViewComponent />
      </main>
      {!isMapView && <Footer />}
    </div>
  );
}
