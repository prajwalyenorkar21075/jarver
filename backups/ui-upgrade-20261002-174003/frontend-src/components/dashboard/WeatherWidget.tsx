import { useEffect, useState } from 'react'

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
  if (type === 'rain') {
    return (
      <svg className="h-4 w-4 text-blue-300" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M16 13v6M8 13v6M12 15v6" />
        <path d="M20 16.58A5 5 0 0 0 18 7h-1.26A8 8 0 1 0 4 15.25" />
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

interface ForecastSlot {
  hour_label: string
  temp: number
  code: number
  label: string
}

interface WeatherData {
  temperature: number
  condition: string
  humidity: number
  high: number | null
  low: number | null
  forecast: ForecastSlot[]
}

function iconForCode(code: number): ForecastIcon {
  if (code >= 51 && code <= 67) return 'rain'
  if (code >= 71 && code <= 86) return 'rain'
  if (code >= 95) return 'rain'
  if (code === 0 || code === 1) return 'sun'
  return 'cloud'
}

export default function WeatherWidget() {
  const [dateStr, setDateStr] = useState('')
  const [weather, setWeather] = useState<WeatherData | null>(null)
  const [status, setStatus] = useState<'loading' | 'ok' | 'unavailable'>('loading')

  useEffect(() => {
    const now = new Date()
    setDateStr(
      now.toLocaleDateString([], { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' })
    )
  }, [])

  useEffect(() => {
    let cancelled = false
    fetch('/api/weather')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((data) => {
        if (cancelled) return
        if (data && data.available && typeof data.temperature === 'number') {
          setWeather(data)
          setStatus('ok')
        } else if (!cancelled) {
          setStatus('unavailable')
        }
      })
      .catch(() => {
        if (!cancelled) setStatus('unavailable')
      })
    return () => {
      cancelled = true
    }
  }, [])

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
        <span className="text-[10px] text-cyan-300/50">{dateStr || 'Loading...'}</span>
      </div>

      {/* Main Temperature & Weather State */}
      {status === 'ok' && weather ? (
        <>
          <div className="mt-3 flex items-center justify-between">
            <div>
              <div className="font-mono text-3xl font-extrabold tracking-tight text-white">
                {Math.round(weather.temperature)}°C
              </div>
              <div className="text-xs font-mono text-cyan-300/80">{weather.condition}</div>
              <div className="mt-0.5 text-[10px] font-mono text-white/40">
                {weather.high != null && weather.low != null
                  ? `H: ${Math.round(weather.high)}°   L: ${Math.round(weather.low)}°`
                  : `Humidity: ${weather.humidity}%`}
              </div>
            </div>

            {/* Status Icon */}
            <div className="relative flex h-14 w-14 items-center justify-center">
              <div className="absolute top-1 right-2 h-7 w-7 rounded-full bg-gradient-to-tr from-cyan-400 to-[#00e5ff] shadow-[0_0_12px_rgba(0,229,255,0.6)]" />
              <svg className="relative z-10 h-10 w-12 text-white/95" viewBox="0 0 24 24" fill="currentColor">
                <path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96z" />
              </svg>
            </div>
          </div>

          {weather.forecast.length > 0 && (
            <div className="mt-4 grid grid-cols-4 gap-2 border-t border-cyan-500/20 pt-3 text-center font-mono">
              {weather.forecast.map((f, i) => (
                <div key={i} className="flex flex-col items-center gap-0.5 rounded-lg bg-[#071530] p-1.5 border border-cyan-500/20">
                  <span className="text-[10px] text-white/50">{f.hour_label}</span>
                  <span className="my-0.5"><WeatherIcon type={iconForCode(f.code)} /></span>
                  <span className="text-xs font-semibold text-white/90">{Math.round(f.temp)}°</span>
                </div>
              ))}
            </div>
          )}
        </>
      ) : (
        <div className="mt-3 flex items-center justify-between">
          <div className="font-mono text-xs text-white/50">
            {status === 'loading' ? 'Fetching live weather…' : 'Weather unavailable'}
          </div>
          <div className="relative flex h-14 w-14 items-center justify-center text-cyan-300/40">
            <svg className="h-10 w-10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96z" />
            </svg>
          </div>
        </div>
      )}
    </div>
  )
}
