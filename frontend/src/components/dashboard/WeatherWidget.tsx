type ForecastIcon = 'cloud' | 'moon' | 'sun' | 'rain'

function WeatherIcon({ type }: { type: ForecastIcon }) {
  if (type === 'moon') {
    return (
      <svg className="h-4 w-4 text-cyan-300" viewBox="0 0 24 24" fill="currentColor">
        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
      </svg>
    )
  }
  if (type === 'sun') {
    return (
      <svg className="h-4 w-4 text-[#00e5ff]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="5" />
        <line x1="12" y1="1" x2="12" y2="3" />
        <line x1="12" y1="21" x2="12" y2="23" />
        <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
        <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
        <line x1="1" y1="12" x2="3" y2="12" />
        <line x1="21" y1="12" x2="23" y2="12" />
        <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
        <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
      </svg>
    )
  }
  // cloud
  return (
    <svg className="h-4 w-4 text-cyan-200/80" viewBox="0 0 24 24" fill="currentColor">
      <path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96z" />
    </svg>
  )
}

export default function WeatherWidget() {
  const forecast: { time: string; temp: string; icon: ForecastIcon }[] = [
    { time: '6 PM', temp: '28°', icon: 'cloud' },
    { time: '9 PM', temp: '26°', icon: 'moon' },
    { time: '12 AM', temp: '24°', icon: 'cloud' },
    { time: '3 AM', temp: '23°', icon: 'cloud' },
  ]

  return (
    <div className="relative rounded-2xl border border-cyan-500/40 bg-[#040a18]/95 p-4 transition-all hover:border-[#00e5ff]/70 shadow-[0_0_15px_rgba(0,229,255,0.06)] w-full max-w-[320px]">
      {/* Top Location & Date */}
      <div className="flex items-center justify-between text-xs font-mono text-white/70">
        <div className="flex items-center gap-1.5 text-[#00e5ff]">
          <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
            <circle cx="12" cy="10" r="3" />
          </svg>
          <span className="font-semibold text-white/95">Nagpur, Maharashtra</span>
        </div>
        <span className="text-[10px] text-cyan-300/50">Mon, 29 Sep 2025</span>
      </div>

      {/* Main Temperature & Weather State */}
      <div className="mt-3 flex items-center justify-between">
        <div>
          <div className="font-mono text-3xl font-extrabold tracking-tight text-white">28°C</div>
          <div className="text-xs font-mono text-cyan-300/80">Partly Cloudy</div>
          <div className="mt-0.5 text-[10px] font-mono text-white/40">H: 34° &nbsp; L: 24°</div>
        </div>

        {/* Sun Behind Cloud Graphic */}
        <div className="relative flex h-14 w-14 items-center justify-center">
          {/* Cyan Glow Sun */}
          <div className="absolute top-1 right-2 h-7 w-7 rounded-full bg-gradient-to-tr from-cyan-400 to-[#00e5ff] shadow-[0_0_12px_rgba(0,229,255,0.6)]" />
          {/* Stylized White Cloud */}
          <svg className="relative z-10 h-10 w-12 text-white/95" viewBox="0 0 24 24" fill="currentColor">
            <path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96z" />
          </svg>
        </div>
      </div>

      {/* 4-Slot Hourly Forecast in Navy Fill Cards */}
      <div className="mt-4 grid grid-cols-4 gap-2 border-t border-cyan-500/20 pt-3 text-center font-mono">
        {forecast.map((f, i) => (
          <div key={i} className="flex flex-col items-center gap-0.5 rounded-lg bg-[#071530] p-1.5 border border-cyan-500/20">
            <span className="text-[10px] text-white/50">{f.time}</span>
            <span className="my-0.5"><WeatherIcon type={f.icon} /></span>
            <span className="text-xs font-semibold text-white/90">{f.temp}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
