export function PhoenixMark({ className = "h-7 w-7", gradientId = "phx-g" }: { className?: string; gradientId?: string }) {
  // gradient ids must be unique per instance: a hidden duplicate (e.g. the collapsed
  // sidebar on mobile) would otherwise make the flame invisible in Chrome
  const gid = gradientId;
  return (
    <svg viewBox="0 0 64 64" className={className} aria-hidden="true">
      <defs>
        <linearGradient id={gid} x1="0" y1="1" x2="0" y2="0">
          <stop offset="0" stopColor="#e2482b" />
          <stop offset="0.55" stopColor="#ff8a1f" />
          <stop offset="1" stopColor="#ffc46b" />
        </linearGradient>
      </defs>
      {/* punch-card frame */}
      <rect x="6" y="40" width="52" height="16" rx="3" fill="none" stroke="#343d4c" strokeWidth="2" />
      <g fill="#343d4c">
        <rect x="12" y="45" width="3" height="6" rx="1" />
        <rect x="19" y="45" width="3" height="6" rx="1" />
        <rect x="42" y="45" width="3" height="6" rx="1" />
        <rect x="49" y="45" width="3" height="6" rx="1" />
      </g>
      {/* phoenix rising from the card */}
      <path
        fill={`url(#${gid})`}
        d="M32 6c3 6 2 11-1 15 5-2 9-6 10-12 4 8 2 16-4 21 6 0 11-3 15-8-1 10-9 17-19 18l-1 12h-0l-1-12C21 39 13 32 12 22c4 5 9 8 15 8-6-5-8-13-4-21 1 6 5 10 10 12-3-4-4-9-1-15Z"
      />
    </svg>
  );
}

export function Wordmark({ className = "", id = "phx-g" }: { className?: string; id?: string }) {
  return (
    <span className={`flex items-center gap-2 ${className}`}>
      <PhoenixMark gradientId={id} />
      <span className="text-[15px] font-semibold tracking-tight text-fog-50">
        COBOL <span className="text-gradient-phoenix">Phoenix</span>
      </span>
    </span>
  );
}
