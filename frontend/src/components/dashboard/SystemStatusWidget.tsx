export default function SystemStatusWidget() {
  const gauges = [
    { label: 'CPU', value: 32, strokeColor: '#00e5ff', trackColor: 'rgba(0,229,255,0.15)' },
    { label: 'RAM', value: 62, strokeColor: '#3b82f6', trackColor: 'rgba(59,130,246,0.15)' },
    { label: 'Storage', value: 48, strokeColor: '#00e5ff', trackColor: 'rgba(0,229,255,0.15)' },
    { label: 'GPU', value: 28, strokeColor: '#38bdf8', trackColor: 'rgba(56,189,248,0.15)' },
  ]

  const radius = 22
  const circ = 2 * Math.PI * radius

  return (
    <div className="relative rounded-2xl border border-cyan-500/40 bg-[#040a18]/95 p-4 transition-all hover:border-[#00e5ff]/70 shadow-[0_0_15px_rgba(0,229,255,0.06)] w-full max-w-[320px]">
      {/* Header */}
      <div className="flex items-center justify-between text-xs font-mono">
        <div className="flex items-center gap-1.5 text-white/95">
          <svg className="h-4 w-4 text-[#00e5ff]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="2" y="2" width="20" height="20" rx="5" />
            <path d="M12 6v12" />
            <path d="M6 12h12" />
          </svg>
          <span className="font-semibold tracking-wider text-[#00e5ff]">SYSTEM STATUS</span>
        </div>

        <div className="flex items-center gap-1 rounded-full border border-cyan-500/40 bg-cyan-500/10 px-2 py-0.5 text-[10px] text-[#00e5ff]">
          <span className="h-1.5 w-1.5 rounded-full bg-[#00e5ff] animate-pulse" />
          <span className="font-bold">HEALTHY</span>
        </div>
      </div>

      {/* 4 Circular Gauges in Navy Card Containers */}
      <div className="mt-4 grid grid-cols-4 gap-2 font-mono">
        {gauges.map((g) => {
          const strokeDashoffset = circ - (g.value / 100) * circ

          return (
            <div key={g.label} className="flex flex-col items-center rounded-xl bg-[#071530] p-1.5 border border-cyan-500/20">
              <div className="relative flex h-14 w-14 items-center justify-center">
                <svg className="h-full w-full -rotate-90" viewBox="0 0 60 60">
                  {/* Track Circle */}
                  <circle
                    cx="30"
                    cy="30"
                    r={radius}
                    fill="none"
                    stroke={g.trackColor}
                    strokeWidth="4"
                  />
                  {/* Progress Arc */}
                  <circle
                    cx="30"
                    cy="30"
                    r={radius}
                    fill="none"
                    stroke={g.strokeColor}
                    strokeWidth="4"
                    strokeDasharray={circ}
                    strokeDashoffset={strokeDashoffset}
                    strokeLinecap="round"
                    style={{
                      transition: 'stroke-dashoffset 1s ease-out',
                    }}
                  />
                </svg>
                {/* Center Percentage */}
                <span className="absolute font-mono text-[11px] font-bold text-white">
                  {g.value}%
                </span>
              </div>
              <span className="mt-1 text-[10px] text-cyan-300/70 font-semibold">{g.label}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
