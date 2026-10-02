import { useEffect, useState } from 'react'

interface CityTime {
  name: string
  time: string
  color: string
  timezone: string
}

export default function WorldClockWidget() {
  const [timeStr, setTimeStr] = useState('')
  const [dateStr, setDateStr] = useState('')
  const [cities, setCities] = useState<CityTime[]>([
    { name: 'New York', time: '--:--', color: 'bg-cyan-400', timezone: 'America/New_York' },
    { name: 'London', time: '--:--', color: 'bg-blue-400', timezone: 'Europe/London' },
    { name: 'Tokyo', time: '--:--', color: 'bg-[#00e5ff]', timezone: 'Asia/Tokyo' },
    { name: 'Sydney', time: '--:--', color: 'bg-sky-400', timezone: 'Australia/Sydney' },
  ])

  useEffect(() => {
    const update = () => {
      const now = new Date()
      setTimeStr(
        now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: true })
      )
      setDateStr(
        now.toLocaleDateString([], { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' })
      )

      // Update city times
      setCities(prev => prev.map(city => ({
        ...city,
        time: now.toLocaleTimeString('en-US', {
          hour: '2-digit',
          minute: '2-digit',
          hour12: true,
          timeZone: city.timezone
        })
      })))
    }
    update()
    const t = setInterval(update, 1000)
    return () => clearInterval(t)
  }, [])

  return (
    <div className="relative rounded-2xl border border-cyan-500/40 bg-[#040a18]/95 p-4 transition-all hover:border-[#00e5ff]/70 shadow-[0_0_15px_rgba(0,229,255,0.06)] w-full max-w-[320px]">
      <div className="flex items-center justify-between">
        {/* Analog/Digital Icon & Main Time */}
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-cyan-400/50 bg-[#071530] text-[#00e5ff]">
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
          </div>
          <div>
            <div className="font-mono text-xl font-bold tracking-tight text-white">{timeStr}</div>
            <div className="text-[10px] font-mono text-cyan-300/50">{dateStr}</div>
          </div>
        </div>

        {/* World Cities List */}
        <div className="flex flex-col gap-1 font-mono text-xs border-l border-cyan-500/20 pl-3">
          {cities.map((c) => (
            <div key={c.name} className="flex items-center justify-between gap-3 text-[11px]">
              <span className="flex items-center gap-1.5 text-white/60">
                <span className={`h-1.5 w-1.5 rounded-full ${c.color}`} />
                {c.name}
              </span>
              <span className="font-semibold text-white/95">{c.time}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
