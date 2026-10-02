import { useEffect, useState } from 'react'
import { useJarvisStore, ORB_STATES } from '../store/useJarvisStore'
import type { OrbState } from 'thinking-orbs'

const HINT: Record<OrbState, string> = {
  working: 'particles on tilted orbits',
  searching: 'a scan meridian sweeps the dotted globe',
  solving: 'bands scramble, then click back solved',
  listening: 'a waveform rolls through the rings',
  connecting: 'a constellation wires itself',
  weaving: 'three strands plait around the sphere',
  composing: 'an undulating multi-band sash',
  breathing: 'a ring slowly morphing',
  shaping: 'circle → triangle → square',
}

export default function OrbSwitcher() {
  const orbState = useJarvisStore((s) => s.orbState)
  const setOrbState = useJarvisStore((s) => s.setOrbState)
  const [collapsed, setCollapsed] = useState(true)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      // Don't intercept if user is typing into an input
      if (['INPUT', 'TEXTAREA'].includes((e.target as HTMLElement)?.tagName)) return
      const i = Number(e.key) - 1
      if (i >= 0 && i < ORB_STATES.length) setOrbState(ORB_STATES[i])
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [setOrbState])

  return (
    <div className="fixed top-16 left-6 z-20 flex flex-col items-start gap-1 select-none">
      <button
        type="button"
        onClick={() => setCollapsed(!collapsed)}
        className="cursor-pointer flex items-center gap-2 rounded-full border border-cyan-500/30 bg-[#060b18]/95 px-3 py-1 text-[11px] font-mono text-white/70 hover:text-white transition-colors"
      >
        <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
        <span>STATES (1-9)</span>
        <svg
          className={`h-2.5 w-2.5 text-white/40 transition-transform ${collapsed ? '' : 'rotate-180'}`}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {!collapsed && (
        <div className="mt-1 flex flex-col gap-1 rounded-xl border border-cyan-500/35 bg-[#060b18]/98 p-2">
          <div className="flex flex-col gap-1">
            {ORB_STATES.map((s, i) => {
              const active = s === orbState
              return (
                <button
                  key={s}
                  type="button"
                  onClick={() => setOrbState(s)}
                  className={[
                    'flex items-center justify-between gap-4 cursor-pointer rounded-lg px-2.5 py-1 text-left font-mono text-[11px] transition-colors',
                    active
                      ? 'bg-[#D4712B] text-black font-semibold'
                      : 'text-white/60 hover:bg-white/10 hover:text-white',
                  ].join(' ')}
                >
                  <span>
                    <span className="mr-2 opacity-50">{i + 1}</span>
                    {s}
                  </span>
                  <span className="text-[9px] opacity-40 uppercase tracking-wider">
                    {active ? 'ACTIVE' : ''}
                  </span>
                </button>
              )
            })}
          </div>
          <p className="mt-1 px-1 text-[10px] font-mono text-white/30 max-w-[180px] leading-tight">
            {HINT[orbState]}
          </p>
        </div>
      )}
    </div>
  )
}
