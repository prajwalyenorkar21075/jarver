import { useEffect, useRef, useState, useCallback } from 'react'
import { useJarvisStore, playHudChirp, getAudioContext } from '../../store/useJarvisStore'

interface Ember3D {
  x: number
  y: number
  z: number
  baseRadius: number
  color: string
  speed: number
  theta: number
  phi: number
  radius: number
}

export default function JarvisNebulaCore() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const orbState = useJarvisStore((s) => s.orbState)
  const isListening = useJarvisStore((s) => s.isListening)
  const setIsListening = useJarvisStore((s) => s.setIsListening)
  const executeCommand = useJarvisStore((s) => s.executeCommand)
  const setSystemNotice = useJarvisStore((s) => s.setSystemNotice)

  // Speech Recognition Reference
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recognitionRef = useRef<any>(null)
  const [speechSupported, setSpeechSupported] = useState(true)

  // Initialize Web Speech API for voice listening
  useEffect(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const win = window as any
    const SpeechClass = win.SpeechRecognition || win.webkitSpeechRecognition
    if (!SpeechClass) {
      setSpeechSupported(false)
      return
    }

    const recognition = new SpeechClass()
    recognition.continuous = true
    recognition.interimResults = false
    recognition.lang = 'en-US'

    recognition.onstart = () => {
      setIsListening(true)
      setSystemNotice('Microphone online. Listening for voice instruction...')
      setTimeout(() => setSystemNotice(null), 3000)
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    recognition.onresult = (event: any) => {
      const results = event.results
      const last = results[results.length - 1]
      const transcript = last[0].transcript
      if (transcript && transcript.trim()) {
        playHudChirp()
        setSystemNotice(`Voice Input: "${transcript.trim()}"`)
        setTimeout(() => setSystemNotice(null), 3500)
        setIsListening(false)
        try {
          recognition.stop()
        } catch {
          // Ignored
        }
        executeCommand(transcript.trim())
      }
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    recognition.onerror = (e: any) => {
      console.warn('Speech recognition error:', e)
      setIsListening(false)
      if (e.error === 'not-allowed') {
        setSystemNotice('Microphone blocked: Please allow mic access in your browser address bar.')
        setTimeout(() => setSystemNotice(null), 6000)
      } else if (e.error === 'network') {
        setSystemNotice('Voice network error: Chrome speech service unreachable. Try typing your command.')
        setTimeout(() => setSystemNotice(null), 5000)
      }
    }

    recognition.onend = () => {
      setIsListening(false)
    }

    recognitionRef.current = recognition
  }, [setIsListening, executeCommand, setSystemNotice])

  const toggleMic = useCallback(() => {
    getAudioContext()
    playHudChirp()

    if (!speechSupported || !recognitionRef.current) {
      setSystemNotice('Web Speech API not supported in this browser. Please use Chrome/Edge or type below.')
      setTimeout(() => setSystemNotice(null), 4000)
      return
    }

    if (isListening) {
      try {
        recognitionRef.current.stop()
      } catch (err) {
        console.warn('Recognition stop error:', err)
      }
      setIsListening(false)
      setSystemNotice(null)
    } else {
      try {
        recognitionRef.current.start()
        setIsListening(true)
      } catch (err) {
        console.warn('Recognition start error:', err)
        try {
          recognitionRef.current.stop()
          setTimeout(() => {
            recognitionRef.current.start()
            setIsListening(true)
          }, 150)
        } catch {
          // Ignored
        }
      }
    }
  }, [isListening, speechSupported, setIsListening, setSystemNotice])

  // =========================================================================
  // CINEMATIC IRON MAN HOLOGRAPHIC SPHERE ENGINE (Screenshot 2026-09-29 000332)
  // Large Grand Scale Gyroscopic Core with Concentric Wireframe Rings & Electric Blue Arc
  // =========================================================================
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

    // Generate 180 Golden Holographic Embers orbiting the sphere
    const EMBERS: Ember3D[] = []
    const amberPalette = ['#ffd700', '#ffa500', '#ff8c00', '#ff6600', '#ffe8a3', '#ffffff']

    for (let i = 0; i < 180; i++) {
      const radius = 40 + Math.random() * 135
      const theta = Math.random() * Math.PI * 2
      const phi = (Math.random() - 0.5) * Math.PI

      EMBERS.push({
        x: radius * Math.cos(phi) * Math.cos(theta),
        y: radius * Math.sin(phi),
        z: radius * Math.cos(phi) * Math.sin(theta),
        baseRadius: Math.random() * 2.2 + 0.9,
        color: amberPalette[Math.floor(Math.random() * amberPalette.length)],
        speed: (Math.random() * 0.45 + 0.2) * (Math.random() > 0.5 ? 1 : -1),
        theta,
        phi,
        radius,
      })
    }

    const render = () => {
      if (!running) return
      const t = performance.now() / 1000

      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      ctx.clearRect(0, 0, size, size)

      const cx = size / 2
      const cy = size / 2

      // Dynamic rotation matrix
      const rotSpeed = orbState === 'searching' ? 1.7 : orbState === 'solving' ? 0.95 : 0.45
      const yaw = t * rotSpeed
      const pitch = Math.sin(t * 0.3) * 0.25 + 0.1
      const roll = Math.cos(t * 0.25) * 0.15

      const cosY = Math.cos(yaw), sinY = Math.sin(yaw)
      const cosP = Math.cos(pitch), sinP = Math.sin(pitch)
      const cosR = Math.cos(roll), sinR = Math.sin(roll)

      // 3D perspective projection function
      const project = (x: number, y: number, z: number): { x: number; y: number; z: number; scale: number } => {
        const x1 = x * cosY - z * sinY
        const z1 = x * sinY + z * cosY
        const y2 = y * cosP - z1 * sinP
        const z2 = y * sinP + z1 * cosP
        const x3 = x1 * cosR - y2 * sinR
        const y3 = x1 * sinR + y2 * cosR
        const fov = 460
        const scale = fov / (fov + z2 + 200)
        return {
          x: cx + x3 * scale,
          y: cy + y3 * scale,
          z: z2,
          scale,
        }
      }

      ctx.save()

      // 1. Radiant Ambient Volumetric Bloom (Warm Amber Core + Electric Blue Fringe)
      const bloomRadius = 175 + Math.sin(t * 2.5) * 8
      const ambientGlow = ctx.createRadialGradient(cx, cy, 8, cx, cy, bloomRadius)
      ambientGlow.addColorStop(0, 'rgba(255, 240, 180, 0.95)')
      ambientGlow.addColorStop(0.18, 'rgba(255, 160, 20, 0.55)')
      ambientGlow.addColorStop(0.48, 'rgba(235, 90, 0, 0.25)')
      ambientGlow.addColorStop(0.78, 'rgba(0, 229, 255, 0.15)')
      ambientGlow.addColorStop(1, 'transparent')

      ctx.fillStyle = ambientGlow
      ctx.beginPath()
      ctx.arc(cx, cy, bloomRadius, 0, Math.PI * 2)
      ctx.fill()

      // 2. HELPER: Draw 3D Circular Ring with Segmented Ticks & Depth
      const draw3DRing = (
        radius: number,
        tiltAngle: number,
        tiltAxis: 'x' | 'y' | 'z',
        spinOffset: number,
        color: string,
        lineWidth: number,
        dashArray: number[] | null = null,
        drawTicks = false
      ) => {
        const SEGMENTS = 72
        const cosT = Math.cos(tiltAngle)
        const sinT = Math.sin(tiltAngle)

        ctx.save()
        if (dashArray) ctx.setLineDash(dashArray)
        ctx.lineWidth = lineWidth
        ctx.strokeStyle = color

        ctx.beginPath()
        let first = true
        for (let s = 0; s <= SEGMENTS; s++) {
          const phi = (s / SEGMENTS) * Math.PI * 2 + spinOffset
          let rx = radius * Math.cos(phi)
          let ry = radius * Math.sin(phi)
          let rz = 0

          if (tiltAxis === 'x') {
            const yNew = ry * cosT - rz * sinT
            rz = ry * sinT + rz * cosT
            ry = yNew
          } else if (tiltAxis === 'y') {
            const xNew = rx * cosT + rz * sinT
            rz = -rx * sinT + rz * cosT
            rx = xNew
          }

          const pt = project(rx, ry, rz)
          if (first) {
            ctx.moveTo(pt.x, pt.y)
            first = false
          } else {
            ctx.lineTo(pt.x, pt.y)
          }

          // Optional tick marks projecting from ring
          if (drawTicks && s % 3 === 0 && s < SEGMENTS) {
            const outX = rx * 1.07
            const outY = ry * 1.07
            const ptOut = project(outX, outY, rz)
            ctx.moveTo(pt.x, pt.y)
            ctx.lineTo(ptOut.x, ptOut.y)
            ctx.moveTo(pt.x, pt.y)
          }
        }
        ctx.stroke()
        ctx.restore()
      }

      // 3. Render Concentric Iron Man Gyroscope Hologram Rings (Scaled Up)
      // Ring A: Outer Great Equatorial Telemetry Ring with notch ticks
      draw3DRing(155, 0.15, 'x', t * 0.35, 'rgba(255, 175, 0, 0.9)', 2.4, null, true)

      // Ring B: Segmented Outer Orbit Arc
      draw3DRing(146, 0.45, 'x', -t * 0.45, 'rgba(255, 130, 0, 0.8)', 2.0, [20, 10, 40, 10])

      // Ring C: Tilted Gyroscope Gimbal 1 (Golden-Amber)
      draw3DRing(134, 0.85, 'y', t * 0.6, 'rgba(255, 195, 30, 0.85)', 1.6, [28, 8, 12, 8])

      // Ring D: Counter-Rotating Gyroscope Gimbal 2
      draw3DRing(120, -0.75, 'x', -t * 0.75, 'rgba(255, 140, 0, 0.75)', 1.5, [16, 8])

      // Ring E: Polar Vertical Gyro Ring
      draw3DRing(108, 1.45, 'y', t * 0.9, 'rgba(255, 215, 60, 0.85)', 1.7, [32, 12])

      // Ring F: Mid Mantle Circular Frame
      draw3DRing(90, -0.4, 'x', -t * 1.1, 'rgba(255, 160, 20, 0.9)', 1.6)

      // Ring G: High-Speed Inner Reactor Gimbal
      draw3DRing(65, 0.6, 'y', t * 1.4, 'rgba(255, 225, 80, 0.95)', 2.0, [10, 6])

      // Ring H: Dense Core Boundary Ring
      draw3DRing(38, -0.25, 'x', -t * 1.8, 'rgba(255, 255, 210, 0.98)', 2.2)

      // 4. Render 3D Spherical Latitude Wireframe Grid Lines
      const latitudes = [-95, -55, 0, 55, 95]
      latitudes.forEach((latY, idx) => {
        const latR = Math.sqrt(Math.max(0, 135 * 135 - latY * latY))
        if (latR > 12) {
          ctx.save()
          ctx.lineWidth = 1.0
          ctx.strokeStyle = idx === 2 ? 'rgba(255, 180, 0, 0.65)' : 'rgba(255, 130, 0, 0.35)'
          ctx.setLineDash([8, 8])
          ctx.beginPath()
          for (let s = 0; s <= 40; s++) {
            const phi = (s / 40) * Math.PI * 2
            const lx = latR * Math.cos(phi)
            const lz = latR * Math.sin(phi)
            const pt = project(lx, latY, lz)
            if (s === 0) ctx.moveTo(pt.x, pt.y)
            else ctx.lineTo(pt.x, pt.y)
          }
          ctx.stroke()
          ctx.restore()
        }
      })

      // 5. Render 180 3D Orbiting Golden Embers & Sparks
      EMBERS.forEach((p, idx) => {
        p.theta += p.speed * 0.015
        const rCurrent = p.radius + Math.sin(t * 3 + idx) * 3
        const px = rCurrent * Math.cos(p.phi) * Math.cos(p.theta)
        const py = rCurrent * Math.sin(p.phi)
        const pz = rCurrent * Math.cos(p.phi) * Math.sin(p.theta)

        const pt = project(px, py, pz)
        const depth = (pt.z + 160) / 320
        const alpha = Math.max(0.2, Math.min(0.98, 0.35 + depth * 0.6))
        const radius = Math.max(0.8, p.baseRadius * (0.8 + depth * 0.4))

        ctx.globalAlpha = alpha
        ctx.fillStyle = p.color
        ctx.beginPath()
        ctx.arc(pt.x, pt.y, radius, 0, Math.PI * 2)
        ctx.fill()
      })

      ctx.globalAlpha = 1.0

      // 6. Signature Feature: THE ELECTRIC BLUE LIGHTNING ARC (Screenshot exact detail)
      // Crackling from the left directly penetrating into the center of the sphere
      const lightningStartX = cx - 250
      const lightningStartY = cy + Math.sin(t * 3.5) * 8
      const lightningEndX = cx - 32
      const lightningEndY = cy + Math.cos(t * 4.2) * 5

      const numPoints = 16
      const arcPoints: { x: number; y: number }[] = []

      for (let k = 0; k <= numPoints; k++) {
        const prog = k / numPoints
        const baseX = lightningStartX + (lightningEndX - lightningStartX) * prog
        const baseY = lightningStartY + (lightningEndY - lightningStartY) * prog
        // Procedural electrical jitter
        const jitterX = k === 0 || k === numPoints ? 0 : (Math.sin(k * 2.8 + t * 24) * 7) + ((Math.random() - 0.5) * 4)
        const jitterY = k === 0 || k === numPoints ? 0 : (Math.cos(k * 3.2 + t * 28) * 9) + ((Math.random() - 0.5) * 6)
        arcPoints.push({ x: baseX + jitterX, y: baseY + jitterY })
      }

      // Outer Cyan Energy Glow
      ctx.save()
      ctx.strokeStyle = 'rgba(0, 229, 255, 0.5)'
      ctx.lineWidth = 7.5
      ctx.lineCap = 'round'
      ctx.lineJoin = 'round'
      ctx.beginPath()
      arcPoints.forEach((pt, k) => {
        if (k === 0) ctx.moveTo(pt.x, pt.y)
        else ctx.lineTo(pt.x, pt.y)
      })
      ctx.stroke()

      // Mid Intense Laser Core (Cyan-Blue)
      ctx.strokeStyle = 'rgba(56, 189, 248, 0.95)'
      ctx.lineWidth = 3.2
      ctx.beginPath()
      arcPoints.forEach((pt, k) => {
        if (k === 0) ctx.moveTo(pt.x, pt.y)
        else ctx.lineTo(pt.x, pt.y)
      })
      ctx.stroke()

      // Hot White Core Filament
      ctx.strokeStyle = '#ffffff'
      ctx.lineWidth = 1.4
      ctx.beginPath()
      arcPoints.forEach((pt, k) => {
        if (k === 0) ctx.moveTo(pt.x, pt.y)
        else ctx.lineTo(pt.x, pt.y)
      })
      ctx.stroke()

      // Secondary Lightning Crackle Branches
      for (let b = 3; b <= 12; b += 3) {
        const root = arcPoints[b]
        if (root) {
          ctx.strokeStyle = 'rgba(0, 229, 255, 0.8)'
          ctx.lineWidth = 1.3
          ctx.beginPath()
          ctx.moveTo(root.x, root.y)
          ctx.lineTo(root.x + (Math.random() - 0.4) * 24, root.y + (Math.random() - 0.5) * 22)
          ctx.lineTo(root.x + (Math.random() - 0.4) * 40, root.y + (Math.random() - 0.5) * 30)
          ctx.stroke()
        }
      }

      // 7. Impact Plasma Burst Flare (Where the Blue Beam Strikes the Orange Sphere)
      const flareGrad = ctx.createRadialGradient(
        lightningEndX,
        lightningEndY,
        1,
        lightningEndX,
        lightningEndY,
        38
      )
      flareGrad.addColorStop(0, '#ffffff')
      flareGrad.addColorStop(0.25, 'rgba(192, 132, 252, 0.85)')
      flareGrad.addColorStop(0.55, 'rgba(0, 229, 255, 0.7)')
      flareGrad.addColorStop(0.85, 'rgba(255, 140, 0, 0.35)')
      flareGrad.addColorStop(1, 'transparent')

      ctx.fillStyle = flareGrad
      ctx.beginPath()
      ctx.arc(lightningEndX, lightningEndY, 38, 0, Math.PI * 2)
      ctx.fill()

      // Cross flare spokes at contact point
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.95)'
      ctx.lineWidth = 1.6
      ctx.beginPath()
      ctx.moveTo(lightningEndX - 22, lightningEndY)
      ctx.lineTo(lightningEndX + 22, lightningEndY)
      ctx.moveTo(lightningEndX, lightningEndY - 22)
      ctx.lineTo(lightningEndX, lightningEndY + 22)
      ctx.stroke()

      ctx.restore()

      // 8. Core Center Singularity (Molten Golden Reactor Heart)
      const centerPt = project(0, 0, 0)
      const coreGrad = ctx.createRadialGradient(centerPt.x, centerPt.y, 1, centerPt.x, centerPt.y, 26)
      coreGrad.addColorStop(0, '#ffffff')
      coreGrad.addColorStop(0.35, '#ffdd55')
      coreGrad.addColorStop(0.7, '#ff8c00')
      coreGrad.addColorStop(1, 'transparent')

      ctx.fillStyle = coreGrad
      ctx.beginPath()
      ctx.arc(centerPt.x, centerPt.y, 26, 0, Math.PI * 2)
      ctx.fill()

      ctx.restore()

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
        return 'Listening...'
      case 'searching':
        return 'Thinking...'
      case 'solving':
        return 'Speaking...'
      default:
        return 'Ready'
    }
  }

  const getStateBadge = () => {
    switch (orbState) {
      case 'listening':
        return { label: 'STATE: ACOUSTIC LISTENING', color: 'border-cyan-400 text-cyan-300' }
      case 'searching':
        return { label: 'STATE: QUANTUM SEARCHING', color: 'border-amber-400 text-amber-300' }
      case 'solving':
        return { label: 'STATE: NEURAL SYNTHESIS', color: 'border-orange-500 text-orange-400' }
      default:
        return { label: 'STATE: HOLOGRAPHIC ONLINE', color: 'border-amber-500/70 text-amber-400' }
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

            {/* Corner Tech Brackets (Stark Hologram ⌜ ⌝ ⌞ ⌟) */}
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

          {/* Dynamic 3D Iron Man Hologram Sphere Canvas */}
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
            title="Toggle Voice Input"
          >
            <div className="relative flex h-12 w-12 xl:h-14 xl:w-14 items-center justify-center rounded-2xl border-2 border-amber-500 bg-[#0a142e] shadow-[0_0_18px_rgba(255,160,0,0.4)]">
              {/* Dynamic Soundwave Bars */}
              <div className="relative z-10 flex items-center gap-1">
                <span
                  className={`w-0.5 rounded-full bg-amber-400 transition-all ${
                    orbState !== 'composing' ? 'h-3 animate-[pulse_1s_ease-in-out_infinite]' : 'h-1.5 opacity-60'
                  }`}
                />
                <span
                  className={`w-0.5 rounded-full bg-amber-300 transition-all ${
                    orbState !== 'composing' ? 'h-5 animate-[pulse_0.7s_ease-in-out_infinite]' : 'h-2.5 opacity-60'
                  }`}
                />
                <span
                  className={`w-0.5 rounded-full bg-white transition-all ${
                    orbState !== 'composing' ? 'h-7 animate-[pulse_0.5s_ease-in-out_infinite]' : 'h-3.5 opacity-80'
                  }`}
                />
                <span
                  className={`w-0.5 rounded-full bg-amber-300 transition-all ${
                    orbState !== 'composing' ? 'h-5 animate-[pulse_0.8s_ease-in-out_infinite]' : 'h-2.5 opacity-60'
                  }`}
                />
                <span
                  className={`w-0.5 rounded-full bg-amber-400 transition-all ${
                    orbState !== 'composing' ? 'h-3 animate-[pulse_1.1s_ease-in-out_infinite]' : 'h-1.5 opacity-60'
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
      </div>
    </div>
  )
}
