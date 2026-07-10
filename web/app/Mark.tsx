/**
 * The TimeSense mark — a blue→violet glowing clock ring with a sparkle core,
 * an SVG recreation of the app icon. Crisp at any size and theme-independent.
 */
export default function Mark({ size = 22, glow = true }: { size?: number; glow?: boolean }) {
  // Stable-but-unique ids so multiple marks on a page don't collide.
  const uid = `m${Math.round(size)}`;
  const ticks = Array.from({ length: 12 }, (_, i) => {
    const angle = (i * 30 * Math.PI) / 180;
    const r1 = 15.5;
    const r2 = i % 3 === 0 ? 12.5 : 13.5;
    return (
      <line
        key={i}
        x1={20 + r1 * Math.sin(angle)} y1={20 - r1 * Math.cos(angle)}
        x2={20 + r2 * Math.sin(angle)} y2={20 - r2 * Math.cos(angle)}
        stroke={`url(#ring-${uid})`} strokeWidth={i % 3 === 0 ? 1.1 : 0.7} strokeLinecap="round" opacity={0.55}
      />
    );
  });

  return (
    <svg
      width={size} height={size} viewBox="0 0 40 40" aria-hidden
      style={{ flex: "none", filter: glow ? "drop-shadow(0 0 6px rgba(124,108,255,.55))" : undefined }}
    >
      <defs>
        <linearGradient id={`ring-${uid}`} x1="4" y1="8" x2="36" y2="34" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#4c8dff" />
          <stop offset="0.55" stopColor="#7c6cff" />
          <stop offset="1" stopColor="#9a6bff" />
        </linearGradient>
        <radialGradient id={`spark-${uid}`} cx="0.5" cy="0.5" r="0.5">
          <stop offset="0" stopColor="#ffffff" />
          <stop offset="0.5" stopColor="#cfd8ff" />
          <stop offset="1" stopColor="#9a6bff" />
        </radialGradient>
      </defs>
      {/* Use the gradient via a shared id reference */}
      <g>
        <circle cx="20" cy="20" r="16" fill="none" stroke={`url(#ring-${uid})`} strokeWidth="3.4" />
        {ticks.map((t) => t)}
        <path
          d="M20 10 L21.6 18.4 L30 20 L21.6 21.6 L20 30 L18.4 21.6 L10 20 L18.4 18.4 Z"
          fill={`url(#spark-${uid})`}
        />
      </g>
    </svg>
  );
}
