import { useEffect } from 'react'
import { useJarvisStore } from '../../store/useJarvisStore'

export default function SystemStatusWidget() {
  const telemetry = useJarvisStore((s) => s.telemetry)
  const fetchTelemetry = useJarvisStore((s) => s.fetchTelemetry)

  useEffect(() => {
    fetchTelemetry()
    const timer = setInterval(() => {
      fetchTelemetry()
    }, 4000)
    return () => clearInterval(timer)
  }, [fetchTelemetry])

  const cpuVal = telemetry ? Math.round(telemetry.cpu_percent) : 24
  const ramVal = telemetry ? Math.round(telemetry.ram_percent) : 45
  const diskVal = telemetry ? Math.round(telemetry.disk_percent) : 60
  const battVal = telemetry?.battery ? Math.round(telemetry.battery.percent) : null

  const gauges = [
    {
      label: 'CPU',
      value: cpuVal,
      detail: `${cpuVal}% load`,
      strokeColor: cpuVal > 85 ? '#ef4444' : cpuVal > 60 ? '#f59e0b' : '#00e5ff',
      trackColor: 'rgba(0,229,255,0.15)',
    },
    {
      label: 'RAM',
      value: ramVal,
      detail: telemetry ? `${telemetry.ram_used_gb}G/${telemetry.ram_total_gb}G` : `${ramVal}%`,
      strokeColor: ramVal > 85 ? '#ef4444' : '#3b82f6',
      trackColor: 'rgba(59,130,246,0.15)',
    },
    {
      label: 'SSD',
      value: diskVal,
      detail: telemetry ? `${telemetry.disk_free_gb}G free` : `${diskVal}%`,
      strokeColor: diskVal > 90 ? '#ef4444' : '#00e5ff',
      trackColor: 'rgba(0,229,255,0.15)',
    },
    {
      label: battVal !== null ? (telemetry?.battery?.power_plugged ? 'PWR ⚡' : 'BATT') : 'PROCS',
      value: battVal !== null ? battVal : Math.min(100, Math.round(((telemetry?.active_processes || 150) / 300) * 100)),
      detail: battVal !== null ? `${battVal}%` : `${telemetry?.active_processes || 0} tasks`,
      strokeColor: battVal !== null && telemetry?.battery?.power_plugged ? '#22c55e' : '#38bdf8',
      trackColor: 'rgba(56,189,248,0.15)',
    },
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
          <span className="font-semibold tracking-wider text-[#00e5ff]">REALTIME TELEMETRY</span>
        </div>

        <div className="flex items-center gap-1 rounded-full border border-cyan-500/40 bg-cyan-500/10 px-2 py-0.5 text-[10px] text-[#00e5ff]">
          <span className="h-1.5 w-1.5 rounded-full bg-[#00e5ff] animate-pulse" />
          <span className="font-bold">LIVE PSUTIL</span>
        </div>
      </div>

      {/* 4 Circular Gauges in Navy Card Containers */}
      <div className="mt-3.5 grid grid-cols-4 gap-2 font-mono">
        {gauges.map((g) => {
          const strokeDashoffset = circ - (Math.min(100, Math.max(0, g.value)) / 100) * circ

          return (
            <div
              key={g.label}
              className="flex flex-col items-center rounded-xl bg-[#071530] p-1.5 border border-cyan-500/20 hover:border-cyan-400/40 transition-colors"
              title={`${g.label}: ${g.detail}`}
            >
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
                      transition: 'stroke-dashoffset 0.8s ease-out, stroke 0.3s ease',
                    }}
                  />
                </svg>
                {/* Center Percentage */}
                <span className="absolute font-mono text-[11px] font-bold text-white">
                  {g.value}%
                </span>
              </div>
              <span className="mt-1 text-[10px] text-cyan-300/80 font-bold truncate max-w-full px-0.5">{g.label}</span>
              <span className="text-[8px] text-cyan-400/50 truncate max-w-full">{g.detail}</span>
            </div>
          )
        })}
      </div>

      {/* Telemetry Process Status Bar */}
      <div className="mt-2.5 flex items-center justify-between border-t border-cyan-500/20 pt-2 font-mono text-[10px] text-cyan-300/60">
        <span>Active Tasks: <strong className="text-white">{telemetry?.active_processes || '---'}</strong></span>
        <span>OS: <strong className="text-cyan-400">WIN-64</strong></span>
        <button
          type="button"
          onClick={() => fetchTelemetry()}
          className="cursor-pointer text-[#00e5ff] hover:underline"
          title="Refresh Telemetry"
        >
          ↻ Sync
        </button>
      </div>
    </div>
  )
}
