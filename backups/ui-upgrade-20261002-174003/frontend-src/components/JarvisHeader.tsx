import { useEffect, useState } from 'react'
import { useJarvisStore } from '../store/useJarvisStore'

export default function JarvisHeader() {
  const [timeStr, setTimeStr] = useState('')
  const [dateStr, setDateStr] = useState('')
  const panelOpen = useJarvisStore((s) => s.panelOpen)
  const openPanel = useJarvisStore((s) => s.openPanel)
  const closePanel = useJarvisStore((s) => s.closePanel)
  const togglePanelZoom = useJarvisStore((s) => s.togglePanelZoom)

  useEffect(() => {
    const updateTime = () => {
      const now = new Date()
      setTimeStr(now.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }))
      setDateStr(now.toLocaleDateString([], { month: 'short', day: '2-digit', year: 'numeric' }).toUpperCase())
    }
    updateTime()
    const timer = setInterval(updateTime, 1000)
    return () => clearInterval(timer)
  }, [])

  return (
    <header className="fixed top-0 left-0 right-0 z-30 flex items-center justify-between border-b border-cyan-500/30 bg-[#060b18]/95 px-6 py-3 select-none">
      {/* Brand & Status */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <div className="h-3 w-3 rounded-full bg-cyan-400" />
          <h1 className="font-mono text-base font-bold tracking-[0.25em] text-white">
            JARVIS<span className="text-cyan-400">.AI</span>
          </h1>
        </div>

        <div className="hidden md:flex items-center gap-2 border-l border-white/10 pl-4 font-mono text-[10px] tracking-wider text-white/40">
          <span className="flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            STT: WEB SPEECH
          </span>
          <span className="text-white/20">|</span>
          <span className="flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-sky-400" />
            TTS: POCKET-TTS (STANDBY)
          </span>
          <span className="text-white/20">|</span>
          <span className="flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-[#D4712B]" />
            FASTAPI :8000
          </span>
        </div>
      </div>

      {/* Quick Action Navigation / Choreography Controls */}
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => {
            if (panelOpen) {
              togglePanelZoom()
            } else {
              openPanel(
                {
                  type: 'youtube',
                  title: 'YouTube Stream',
                  videoId: 'jfKfPfyJRdk',
                },
                'center'
              )
            }
          }}
          className="cursor-pointer rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-1.5 font-mono text-xs font-medium text-amber-300 transition-all hover:bg-amber-500/20 active:scale-95"
        >
          {panelOpen ? '⤢ Zoom / Dock Panel' : '▶ Open Panel (Center)'}
        </button>

        <button
          type="button"
          onClick={() => {
            if (panelOpen) {
              closePanel()
            } else {
              openPanel(
                {
                  type: 'youtube',
                  title: 'YouTube Stream',
                  videoId: 'jfKfPfyJRdk',
                },
                'docked-tr'
              )
            }
          }}
          className="cursor-pointer rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 font-mono text-xs text-white/70 transition-all hover:bg-white/10 hover:text-white active:scale-95"
        >
          {panelOpen ? '✕ Dismiss Panel' : '⤡ Dock Top-Right'}
        </button>

        {/* Live Clock HUD */}
        <div className="hidden sm:flex flex-col items-end border-l border-white/10 pl-4 font-mono">
          <span className="text-xs font-semibold tracking-wider text-amber-300/90">{timeStr || '12:00:00'}</span>
          <span className="text-[9px] tracking-widest text-white/30">{dateStr}</span>
        </div>
      </div>
    </header>
  )
}
