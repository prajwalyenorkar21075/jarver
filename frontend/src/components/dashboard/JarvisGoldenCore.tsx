import { useEffect, useRef, useCallback } from 'react'
import { useJarvisStore, playHudChirp } from '../../store/useJarvisStore'
import { voiceController } from '../../services/voiceController'

interface CrackNode {
  angle: number
  r0: number
  segs: { r: number; a: number }[]
  bright: boolean
  spinMul: number
}

interface Dot3 {
  theta: number
  phi: number
  radius: number
  pr: number
  sp: number
  bright: boolean
}

// ============================================================================
// GOLDEN CRACKED HOLOGRAPHIC SPHERE (00-MASTER-golden-cracked-sphere.png)
// Dark interior + amber crack network + orbit arcs + horizon streaks.
// First UI prototype — built for the audience video.
// ============================================================================
export default function JarvisNebulaCore() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const orbState = useJarvisStore((s) => s.orbState)
  const isListening = useJarvisStore((s) => s.isListening)
  const audioLevel = useJarvisStore((s) => s.audioLevel)
  const isVoiceActive = useJarvisStore((s) => s.isVoiceActive)
  const speechLanguage = useJarvisStore((s) => s.speechLanguage)
  const setSpeechLanguage = useJarvisStore((s) => s.setSpeechLanguage)
  const detectedLanguage = useJarvisStore((s) => s.detectedLanguage)
  const setSystemNotice = useJarvisStore((s) => s.setSystemNotice)
  const speechSupported = voiceController.isSpeechSupported()

  const toggleMic = useCallback(async () => {
    await voiceController.toggleListening()
  }, [])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const dpr = Math.min(3, window.devicePixelRatio || 1)
    const size = 440
    canvas.width = Math.round(size * dpr)
    canvas.height = Math.round(size * dpr)

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let animId = 0
    let running = true

    const rand = (seed: number) => {
      let s = seed
      return () => {
        s = (s * 16807) % 2147483647
        return (s - 1) / 2147483646
      }
    }

    // ---- crack network: jagged polylines radiating from the inner ring ----
    const CRACKS: CrackNode[] = []
    {
      const r = rand(1337)
      const N = 15
      const parents: CrackNode[] = []
      for (let i = 0; i < N; i++) {
        const angle = (i / N) * Math.PI * 2 + (r() - 0.5) * 0.5
        const r0 = 30 + r() * 8
        const r1 = 120 + r() * 48
        const segs: { r: number; a: number }[] = []
        const steps = 5 + Math.floor(r() * 4)
        for (let k = 0; k <= steps; k++) {
          segs.push({ r: r0 + (r1 - r0) * (k / steps), a: (r() - 0.5) * 0.34 })
        }
        const c: CrackNode = { angle, r0, segs, bright: r() > 0.5, spinMul: 1 }
        parents.push(c)
        CRACKS.push(c)
      }
      for (let i = 0; i < 11; i++) {
        const parent = parents[Math.floor(r() * N)]
        const startIdx = 1 + Math.floor(r() * (parent.segs.length - 2))
        const baseR = parent.segs[startIdx].r
        const segs: { r: number; a: number }[] = [{ r: baseR, a: 0 }]
        const steps = 3 + Math.floor(r() * 3)
        const dir = r() > 0.5 ? 1 : -1
        for (let k = 1; k <= steps; k++) {
          segs.push({ r: baseR + k * (13 + r() * 10), a: dir * k * (0.1 + r() * 0.12) })
        }
        CRACKS.push({
          angle: parent.angle + (r() - 0.5) * 0.1,
          r0: baseR,
          segs,
          bright: false,
          spinMul: 1.18,
        })
      }
    }

    // ---- ember dots + shard flecks on the shell ----
    const DOTS: Dot3[] = []
    {
      const r = rand(4242)
      for (let i = 0; i < 220; i++) {
        DOTS.push({
          theta: r() * Math.PI * 2,
          phi: Math.acos(2 * r() - 1) - Math.PI / 2,
          radius: 52 + r() * 122,
          pr: 0.7 + r() * 2.1,
          sp: (0.25 + r() * 0.6) * (r() > 0.5 ? 1 : -1),
          bright: r() > 0.72,
        })
      }
    }

    const render = () => {
      if (!running) return
      const t = performance.now() / 1000

      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      ctx.clearRect(0, 0, size, size)

      const cx = size / 2
      const cy = size / 2

      const rotSpeed = orbState === 'searching' ? 0.9 : orbState === 'solving' ? 0.5 : 0.22
      const baseSpin = t * rotSpeed
      const breathe = 1 + Math.sin(t * 1.6) * 0.012
      const shimmer = 0.75 + Math.sin(t * 2.3) * 0.15 + Math.sin(t * 5.7) * 0.1

      // 1. deep dark interior with a hot heart (light hugs the cracks, not a wash)
      const inner = ctx.createRadialGradient(cx, cy, 2, cx, cy, 185)
      inner.addColorStop(0, 'rgba(255,196,90,0.85)')
      inner.addColorStop(0.1, 'rgba(200,110,25,0.45)')
      inner.addColorStop(0.28, 'rgba(80,42,10,0.28)')
      inner.addColorStop(0.62, 'rgba(20,12,6,0.30)')
      inner.addColorStop(1, 'rgba(0,0,0,0)')
      ctx.fillStyle = inner
      ctx.beginPath()
      ctx.arc(cx, cy, 185, 0, Math.PI * 2)
      ctx.fill()

      // 2. inner bright ring — the glowing circle around the dark core
      const R_IN = 30 * breathe
      const ringGlow = ctx.createRadialGradient(cx, cy, R_IN - 8, cx, cy, R_IN + 16)
      ringGlow.addColorStop(0, 'rgba(255,220,140,0)')
      ringGlow.addColorStop(0.42, `rgba(255,190,90,${0.55 * shimmer})`)
      ringGlow.addColorStop(0.55, `rgba(255,240,200,${0.85 * shimmer})`)
      ringGlow.addColorStop(0.68, `rgba(255,150,40,${0.45 * shimmer})`)
      ringGlow.addColorStop(1, 'rgba(255,140,30,0)')
      ctx.fillStyle = ringGlow
      ctx.beginPath()
      ctx.arc(cx, cy, R_IN + 16, 0, Math.PI * 2)
      ctx.fill()

      ctx.save()
      ctx.strokeStyle = `rgba(255,226,160,${0.9 * shimmer})`
      ctx.lineWidth = 3.2
      ctx.beginPath()
      ctx.arc(cx, cy, R_IN, 0, Math.PI * 2)
      ctx.stroke()
      ctx.strokeStyle = `rgba(255,150,50,${0.4 * shimmer})`
      ctx.lineWidth = 7
      ctx.beginPath()
      ctx.arc(cx, cy, R_IN, 0, Math.PI * 2)
      ctx.stroke()
      ctx.restore()

      // dark hole inside the ring
      const hole = ctx.createRadialGradient(cx, cy, 1, cx, cy, R_IN - 2)
      hole.addColorStop(0, 'rgba(5,3,2,0.98)')
      hole.addColorStop(1, 'rgba(5,3,2,0)')
      ctx.fillStyle = hole
      ctx.beginPath()
      ctx.arc(cx, cy, R_IN - 1, 0, Math.PI * 2)
      ctx.fill()

      // 3. crack network
      ctx.save()
      ctx.lineCap = 'round'
      ctx.lineJoin = 'round'
      CRACKS.forEach((c) => {
        const aBase = c.angle + baseSpin * c.spinMul
        const pts: { x: number; y: number }[] = []
        let acc = 0
        c.segs.forEach((s) => {
          acc += s.a
          const a = aBase + acc
          const rr = s.r * breathe
          pts.push({ x: cx + Math.cos(a) * rr, y: cy + Math.sin(a) * rr * 0.94 })
        })
        const passes = c.bright
          ? [
              { w: 5.5, col: 'rgba(255,120,20,0.20)' },
              { w: 2.2, col: `rgba(255,${170 + Math.floor(40 * shimmer)},90,0.85)` },
            ]
          : [
              { w: 3.4, col: 'rgba(200,100,25,0.16)' },
              { w: 1.4, col: 'rgba(235,150,55,0.6)' },
            ]
        passes.forEach((p) => {
          ctx.strokeStyle = p.col
          ctx.lineWidth = p.w
          ctx.beginPath()
          pts.forEach((pt, k) => {
            if (k === 0) ctx.moveTo(pt.x, pt.y)
            else ctx.lineTo(pt.x, pt.y)
          })
          ctx.stroke()
        })
      })
      ctx.restore()

      // 4. orbit arcs (tilted ellipses like the reference)
      const arcs = [
        { rx: 158, ry: 60, rot: -0.42, sp: 0.3, dash: null as number[] | null, alpha: 0.5, w: 1.8 },
        { rx: 168, ry: 52, rot: 0.35, sp: -0.22, dash: [26, 14] as number[], alpha: 0.42, w: 1.6 },
        { rx: 138, ry: 128, rot: 0.1, sp: 0.24, dash: [10, 18] as number[], alpha: 0.3, w: 1.3 },
      ]
      arcs.forEach((A, ai) => {
        ctx.save()
        ctx.translate(cx, cy)
        ctx.rotate(A.rot + baseSpin * A.sp * (ai === 2 ? 2 : 1))
        ctx.strokeStyle = `rgba(255,170,70,${A.alpha * shimmer})`
        ctx.lineWidth = A.w
        if (A.dash) ctx.setLineDash(A.dash)
        ctx.beginPath()
        ctx.ellipse(0, 0, A.rx * breathe, A.ry * breathe, 0, 0, Math.PI * 2)
        ctx.stroke()
        ctx.restore()
      })

      // 5. horizon streaks (bright horizontal light bars left + right)
      const streakY = cy + Math.sin(t * 0.9) * 3
      const streak = (dir: 1 | -1, yOff: number, len: number, alpha: number) => {
        const g = ctx.createLinearGradient(cx, streakY + yOff, cx + dir * len, streakY + yOff)
        g.addColorStop(0, `rgba(255,220,150,${alpha * shimmer})`)
        g.addColorStop(1, 'rgba(255,160,60,0)')
        ctx.strokeStyle = g
        ctx.lineWidth = 2.4
        ctx.beginPath()
        ctx.moveTo(cx + dir * 60, streakY + yOff)
        ctx.lineTo(cx + dir * len, streakY + yOff + dir * 4)
        ctx.stroke()
      }
      streak(1, -6, 205, 0.55)
      streak(-1, 10, 195, 0.45)
      streak(1, 22, 150, 0.25)

      // 6. ember dots riding on the shell
      DOTS.forEach((d) => {
        const a = d.theta + baseSpin * d.sp * 0.4
        const rr = d.radius * breathe
        const x = cx + Math.cos(a) * rr
        const y = cy + Math.sin(a) * rr * 0.94
        const tw = 0.5 + 0.5 * Math.sin(t * 3 + d.theta * 7)
        ctx.globalAlpha = (d.bright ? 0.9 : 0.5) * tw
        ctx.fillStyle = d.bright ? '#ffd9a0' : '#e8933a'
        ctx.beginPath()
        ctx.arc(x, y, d.pr, 0, Math.PI * 2)
        ctx.fill()
      })
      ctx.globalAlpha = 1

      animId = requestAnimationFrame(render)
    }

    render()

    return () => {
      running = false
      cancelAnimationFrame(animId)
    }
  }, [orbState])

  const getButtonText = () => {
    switch (orbState) {
      case 'listening':
        return isVoiceActive ? 'Voice Active...' : 'Listening...'
      case 'searching':
        return 'Thinking...'
      case 'solving':
        return 'Speaking...'
      default:
        return isListening ? 'Standby (Hey Jarvis)' : 'Ready'
    }
  }

  const getStateBadge = () => {
    switch (orbState) {
      case 'listening':
        return {
          label: isVoiceActive ? 'VOICE DETECTED (VAD ACTIVE)' : 'STATE: ACOUSTIC LISTENING',
          color: 'border-cyan-400 text-cyan-300',
        }
      case 'searching':
        return { label: 'STATE: QUANTUM SEARCHING', color: 'border-amber-400 text-amber-300' }
      case 'solving':
        return { label: 'STATE: JARVIS SPEAKING (MIC PAUSED)', color: 'border-orange-500 text-orange-400' }
      default:
        return {
          label: isListening ? 'STATE: WAKE WORD STANDBY (HEY JARVIS)' : 'STATE: HOLOGRAPHIC ONLINE',
          color: isListening ? 'border-cyan-500/70 text-cyan-400' : 'border-amber-500/70 text-amber-400',
        }
    }
  }

  const badge = getStateBadge()

  return (
    <div className="relative flex flex-col items-center justify-center select-none">
      {/* Precision Engineered Hologram Projection Stage */}
      <div className="relative flex flex-col items-center justify-center">
        {/* Holographic Projection Frame with Stark Tech Corner Brackets */}
        <div className="relative h-[370px] w-[350px] xl:h-[430px] xl:w-[410px] flex items-center justify-center">
          {/* Outer Hologram SVG HUD Reticles */}
          <svg className="absolute inset-0 h-full w-full pointer-events-none" viewBox="0 0 420 440" fill="none">
            {/* Outer Circular Hologram Gauge */}
            <circle
              cx="210"
              cy="215"
              r="195"
              stroke="rgba(255, 160, 0, 0.28)"
              strokeWidth="1.2"
              strokeDasharray="18 8 52 8"
            />
            <circle
              cx="210"
              cy="215"
              r="204"
              stroke="rgba(0, 229, 255, 0.25)"
              strokeWidth="1"
              strokeDasharray="6 20"
            />

            {/* Corner Tech Brackets (Stark Hologram corners) */}
            <path d="M 25 50 L 25 25 L 50 25" stroke="#ff9e0b" strokeWidth="1.6" />
            <path d="M 395 50 L 395 25 L 370 25" stroke="#ff9e0b" strokeWidth="1.6" />
            <path d="M 25 380 L 25 405 L 50 405" stroke="#00e5ff" strokeWidth="1.6" />
            <path d="M 395 380 L 395 405 L 370 405" stroke="#00e5ff" strokeWidth="1.6" />

            {/* Subtle Horizon Datum Lines */}
            <line x1="15" y1="215" x2="38" y2="215" stroke="#00e5ff" strokeWidth="1.5" />
            <line x1="382" y1="215" x2="405" y2="215" stroke="#ff9e0b" strokeWidth="1.5" />
          </svg>

          {/* Top Hologram Telemetry Badge */}
          <div className="absolute top-2 left-1/2 -translate-x-1/2 flex items-center gap-1.5 font-mono text-[9px] font-bold tracking-widest uppercase">
            <span className={`rounded-full border px-3 py-0.5 bg-[#040711]/90 shadow-[0_0_12px_rgba(255,160,0,0.25)] ${badge.color}`}>
              {badge.label}
            </span>
          </div>

          {/* Golden cracked-sphere canvas */}
          <div className="relative flex items-center justify-center">
            <canvas ref={canvasRef} className="h-[350px] w-[350px] xl:h-[410px] xl:w-[410px]" />
          </div>

          {/* Holographic Title Base */}
          <div className="absolute bottom-1 left-1/2 -translate-x-1/2 flex flex-col items-center text-center">
            <h2 className="font-mono text-base font-black tracking-[0.35em] text-white drop-shadow-[0_0_10px_rgba(255,160,0,0.6)]">
              J.A.R.V.I.S.
            </h2>
            <span className="font-mono text-[9px] tracking-[0.25em] text-amber-400 font-semibold uppercase">
              STARK INDUSTRIES HOLOGRAPHIC CORE
            </span>
          </div>
        </div>

        {/* 3 Precision Control Buttons Below Reactor */}
        <div className="mt-2 flex items-center gap-3">
          {/* 1. Voice Button */}
          <button
            type="button"
            onClick={toggleMic}
            className="group flex flex-col items-center cursor-pointer transition-transform hover:scale-105 active:scale-95"
            title={isListening ? 'Stop Listening' : 'Enable Microphone'}
          >
            <div className="relative flex h-10 w-10 xl:h-11 xl:w-11 items-center justify-center rounded-xl border border-amber-500/40 bg-[#070d1e] text-amber-400 group-hover:border-amber-400 group-hover:text-amber-300 transition-all shadow-[0_0_10px_rgba(255,160,0,0.15)]">
              <svg
                className={`h-4 w-4 transition-colors ${
                  isListening ? 'text-amber-300 animate-pulse' : 'text-amber-400'
                }`}
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M12 2a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
                <path d="M19 10v1a7 7 0 0 1-14 0v-1" />
                <line x1="12" y1="19" x2="12" y2="22" />
              </svg>
            </div>
            <span className="mt-0.5 font-mono text-[9px] text-white/60 group-hover:text-amber-300">Voice</span>
          </button>

          {/* 2. Active Center Button: Shows Current State with Animated Audio Waves */}
          <button
            type="button"
            onClick={toggleMic}
            className="group flex flex-col items-center cursor-pointer transition-transform hover:scale-105 active:scale-95"
            title={speechSupported ? 'Toggle Voice Input (Web Speech + Whisper)' : 'Toggle Voice Input (Neural Whisper Active)'}
          >
            <div className="relative flex h-12 w-12 xl:h-14 xl:w-14 items-center justify-center rounded-2xl border-2 border-amber-500 bg-[#0a142e] shadow-[0_0_18px_rgba(255,160,0,0.4)]">
              {/* Dynamic Soundwave Bars */}
              <div className="relative z-10 flex items-center gap-1">
                <span
                  style={{
                    height: orbState !== 'composing'
                      ? undefined
                      : `${Math.max(6, Math.min(26, (audioLevel || 0) * 36))}px`,
                  }}
                  className={`w-0.5 rounded-full bg-amber-400 transition-all ${
                    orbState !== 'composing' ? 'h-3 animate-[pulse_1s_ease-in-out_infinite]' : ''
                  }`}
                />
                <span
                  style={{
                    height: orbState !== 'composing'
                      ? undefined
                      : `${Math.max(10, Math.min(34, (audioLevel || 0) * 48))}px`,
                  }}
                  className={`w-0.5 rounded-full bg-amber-300 transition-all ${
                    orbState !== 'composing' ? 'h-5 animate-[pulse_0.7s_ease-in-out_infinite]' : ''
                  }`}
                />
                <span
                  style={{
                    height: orbState !== 'composing'
                      ? undefined
                      : `${Math.max(14, Math.min(42, (audioLevel || 0) * 60))}px`,
                  }}
                  className={`w-0.5 rounded-full bg-white transition-all ${
                    orbState !== 'composing' ? 'h-7 animate-[pulse_0.5s_ease-in-out_infinite]' : ''
                  }`}
                />
                <span
                  style={{
                    height: orbState !== 'composing'
                      ? undefined
                      : `${Math.max(10, Math.min(34, (audioLevel || 0) * 48))}px`,
                  }}
                  className={`w-0.5 rounded-full bg-amber-300 transition-all ${
                    orbState !== 'composing' ? 'h-5 animate-[pulse_0.8s_ease-in-out_infinite]' : ''
                  }`}
                />
                <span
                  style={{
                    height: orbState !== 'composing'
                      ? undefined
                      : `${Math.max(6, Math.min(26, (audioLevel || 0) * 36))}px`,
                  }}
                  className={`w-0.5 rounded-full bg-amber-400 transition-all ${
                    orbState !== 'composing' ? 'h-3 animate-[pulse_1.1s_ease-in-out_infinite]' : ''
                  }`}
                />
              </div>
            </div>
            <div className="mt-0.5 flex items-center gap-1 font-mono text-[9px] font-bold text-amber-300">
              <span>{getButtonText()}</span>
            </div>
          </button>

          {/* 3. Keyboard Button */}
          <button
            type="button"
            onClick={() => {
              const inputEl = document.getElementById('jarvis-main-input')
              inputEl?.focus()
            }}
            className="group flex flex-col items-center cursor-pointer transition-transform hover:scale-105 active:scale-95"
            title="Focus Keyboard Input"
          >
            <div className="relative flex h-10 w-10 xl:h-11 xl:w-11 items-center justify-center rounded-xl border border-cyan-500/40 bg-[#070d1e] text-cyan-400 group-hover:border-[#00e5ff] group-hover:text-cyan-300 transition-all shadow-[0_0_10px_rgba(0,229,255,0.15)]">
              <svg
                className="relative z-10 h-4 w-4 text-cyan-400 group-hover:text-cyan-300"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <rect x="2" y="4" width="20" height="16" rx="2" />
                <path d="M6 8h.001" />
                <path d="M10 8h.001" />
                <path d="M14 8h.001" />
                <path d="M18 8h.001" />
                <path d="M6 12h.001" />
                <path d="M10 12h.001" />
                <path d="M14 12h.001" />
                <path d="M18 12h.001" />
                <path d="M8 16h8" />
              </svg>
            </div>
            <span className="mt-0.5 font-mono text-[9px] text-white/60 group-hover:text-cyan-300">Keyboard</span>
          </button>
        </div>

        {/* Holographic Multilingual Speech Engine Selector */}
        <div className="mt-2.5 flex items-center justify-center gap-1.5 rounded-full border border-cyan-500/30 bg-[#040817]/90 px-2 py-1 shadow-[0_0_12px_rgba(0,229,255,0.15)]">
          <span className="font-mono text-[9px] text-cyan-400/80 mr-1 flex items-center gap-1">
            <span className="h-1.5 w-1.5 rounded-full bg-[#00e5ff] animate-ping" />
            LANG:
          </span>
          {[
            { id: 'auto', label: speechLanguage === 'auto' ? `AUTO · ${detectedLanguage.toUpperCase()}` : 'AUTO' },
            { id: 'en-IN', label: 'EN-IN / Hinglish' },
            { id: 'mr-IN', label: 'मराठी' },
            { id: 'hi-IN', label: 'हिंदी' },
            { id: 'en-US', label: 'EN-US' },
          ].map((l) => (
            <button
              key={l.id}
              type="button"
              onClick={() => {
                playHudChirp()
                setSpeechLanguage(l.id)
                setSystemNotice(
                  l.id === 'auto'
                    ? `Auto language detection active (${detectedLanguage.toUpperCase()})`
                    : `Speech Recognition set to: ${l.label}`
                )
                setTimeout(() => setSystemNotice(null), 2500)
              }}
              className={`rounded-full px-2.5 py-0.5 font-mono text-[9px] font-bold transition-all cursor-pointer ${
                speechLanguage === l.id
                  ? 'border border-[#00e5ff] bg-[#00e5ff]/20 text-[#00e5ff] shadow-[0_0_8px_rgba(0,229,255,0.4)]'
                  : 'text-white/60 hover:text-white hover:bg-white/5 border border-transparent'
              }`}
            >
              {l.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
