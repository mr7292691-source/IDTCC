/**
 * LifeShield AI mark — a shield (protection) carrying a heartbeat pulse (life),
 * with a location notch at the base (geospatial / digital-twin city scale).
 * Replaces the legacy BMW-M tricolor badge.
 *
 * `idSuffix` keeps gradient ids unique when the logo is rendered more than once
 * on a page (SVG gradient ids are global).
 */
export default function ShieldLogo({ size = 36, idSuffix = 'a' }) {
  const gid = `ls-grad-${idSuffix}`;
  return (
    <svg width={size} height={size} viewBox="0 0 36 36" fill="none"
         xmlns="http://www.w3.org/2000/svg" role="img" aria-label="LifeShield AI">
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#2f8bff" />
          <stop offset="1" stopColor="#0a2a5e" />
        </linearGradient>
      </defs>
      {/* Shield body */}
      <path
        d="M18 2.5 L30.5 7 V17.5 C30.5 25.5 25 30.5 18 33.5 C11 30.5 5.5 25.5 5.5 17.5 V7 Z"
        fill={`url(#${gid})`} stroke="#2f8bff" strokeWidth="1.4" />
      {/* Heartbeat / life pulse */}
      <path
        d="M9.5 19 H14 L16 13.5 L19.5 24 L21.5 19 H26.5"
        stroke="#ffffff" strokeWidth="2.1"
        strokeLinecap="round" strokeLinejoin="round" fill="none" />
      {/* Location dot at base */}
      <circle cx="18" cy="28.5" r="1.6" fill="#34d399" />
    </svg>
  );
}
