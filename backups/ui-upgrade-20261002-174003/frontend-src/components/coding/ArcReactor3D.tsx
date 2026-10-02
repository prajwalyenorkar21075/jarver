import { useEffect, useRef } from 'react'

export type ReactorState = 'idle' | 'listening' | 'thinking' | 'executing' | 'speaking'

interface ArcReactor3DProps {
  state?: ReactorState
  audioLevel?: number
  size?: number
  className?: string
  interactive?: boolean
  onClick?: () => void
}

interface Particle3D {
  x: number
  y: number
  z: number
  baseRadius: number
  color: string
  speed: number
  theta: number
  phi: number
  orbitRadius: number
}

export default function ArcReactor3D({
  state = 'idle',
  audioLevel = 0,
  size = 380,
  className = '',
  interactive = true,
  onClick,
}: ArcReactor3DProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const dpr = Math.min(2.5, window.devicePixelRatio || 1)
    canvas.width = Math.round(size * dpr)
    canvas.height = Math.round(size * dpr)

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let animId = 0
    let running = true

    // Generate 160 3D Quantum Particles
    const PARTICLES: Particle3D[] = []
    const palette = ['#00e5ff', '#38bdf8', '#ffd700', '#ff9900', '#ffffff', '#00f0ff']

    for (let i = 0; i < 160; i++) {
      const orbitRadius = 25 + Math.random() * 115
      const theta = Math.random() * Math.PI * 2
      const phi = (Math.random() - 0.5) * Math.PI
      PARTICLES.push({
        x: orbitRadius * Math.cos(phi) * Math.cos(theta),
        y: orbitRadius * Math.sin(phi),
        z: orbitRadius * Math.cos(phi) * Math.sin(theta),
        baseRadius: Math.random() * 2.0 + 0.8,
        color: palette[Math.floor(Math.random() * palette.length)],
        speed: (Math.random() * 0.6 + 0.2) * (Math.random() > 0.5 ? 1 : -1),
        theta,
        phi,
        orbitRadius,
      })
    }

    const render = () => {
      if (!running) return
      const t = performance.now() / 1000

      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      ctx.clearRect(0, 0, size, size)

      const cx = size / 2
      const cy = size / 2

      // Rotation dynamics based on state
      let rotSpeed = 0.5
      let primaryGlow = 'rgba(0, 229, 255, 0.4)'
      let coreColor = '#00e5ff'

      if (state === 'listening') {
        rotSpeed = 0.8 + audioLevel * 1.5
        primaryGlow = 'rgba(0, 240, 255, 0.6)'
        coreColor = '#38bdf8'
      } else if (state === 'thinking') {
        rotSpeed = 1.8
        primaryGlow = 'rgba(255, 175, 0, 0.65)'
        coreColor = '#ffb300'
      } else if (state === 'executing') {
        rotSpeed = 1.2
        primaryGlow = 'rgba(16, 185, 129, 0.6)'
        coreColor = '#10b981'
      } else if (state === 'speaking') {
        rotSpeed = 0.9 + Math.sin(t * 8) * 0.3
        primaryGlow = 'rgba(255, 120, 0, 0.6)'
        coreColor = '#ff6b00'
      }

      const yaw = t * rotSpeed
      const pitch = Math.sin(t * 0.4) * 0.18 + 0.08
      const roll = Math.cos(t * 0.35) * 0.12

      const cosY = Math.cos(yaw), sinY = Math.sin(yaw)
      const cosP = Math.cos(pitch), sinP = Math.sin(pitch)
      const cosR = Math.cos(roll), sinR = Math.sin(roll)

      // 3D perspective projection
      const project = (x: number, y: number, z: number) => {
        const x1 = x * cosY - z * sinY
        const z1 = x * sinY + z * cosY
        const y2 = y * cosP - z1 * sinP
        const z2 = y * sinP + z1 * cosP
        const x3 = x1 * cosR - y2 * sinR
        const y3 = x1 * sinR + y2 * cosR
        const fov = 420
        const scale = fov / (fov + z2 + 180)
        return {
          x: cx + x3 * scale,
          y: cy + y3 * scale,
          z: z2,
          scale,
        }
      }

      ctx.save()

      // 1. Ambient Volumetric Glow Core
      const pulseExpand = state === 'listening' ? audioLevel * 30 : Math.sin(t * 3) * 6
      const bloomRadius = 145 + pulseExpand
      const ambientGlow = ctx.createRadialGradient(cx, cy, 5, cx, cy, bloomRadius)
      ambientGlow.addColorStop(0, 'rgba(255, 255, 255, 0.95)')
      ambientGlow.addColorStop(0.2, primaryGlow)
      ambientGlow.addColorStop(0.6, state === 'thinking' ? 'rgba(255, 140, 0, 0.2)' : 'rgba(0, 160, 255, 0.15)')
      ambientGlow.addColorStop(1, 'transparent')

      ctx.fillStyle = ambientGlow
      ctx.beginPath()
      ctx.arc(cx, cy, bloomRadius, 0, Math.PI * 2)
      ctx.fill()

      // 2. Helper: Draw 3D Ring with Depth
      const draw3DRing = (
        radius: number,
        tiltAngle: number,
        tiltAxis: 'x' | 'y',
        spinOffset: number,
        color: string,
        lineWidth: number,
        dashArray: number[] | null = null,
        drawTicks = false
      ) => {
        const SEGMENTS = 64
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

          if (drawTicks && s % 4 === 0 && s < SEGMENTS) {
            const outX = rx * 1.08
            const outY = ry * 1.08
            const ptOut = project(outX, outY, rz)
            ctx.moveTo(pt.x, pt.y)
            ctx.lineTo(ptOut.x, ptOut.y)
            ctx.moveTo(pt.x, pt.y)
          }
        }
        ctx.stroke()
        ctx.restore()
      }

      // 3. Render Concentric Arc-Reactor Titanium Gimbals
      const ringColorA = state === 'thinking' ? 'rgba(255, 180, 0, 0.85)' : 'rgba(0, 229, 255, 0.85)'
      const ringColorB = state === 'thinking' ? 'rgba(255, 220, 100, 0.9)' : 'rgba(56, 189, 248, 0.9)'

      // Outer Main Armor Ring with Calibration Ticks
      draw3DRing(135, 0.12, 'x', t * 0.3, ringColorA, 2.2, null, true)
      // Segmented Orbit Ring
      draw3DRing(124, 0.42, 'x', -t * 0.4, ringColorB, 1.8, [18, 10, 36, 10])
      // Counter-rotating Inner Gimbal
      draw3DRing(108, 0.85, 'y', t * 0.65, ringColorA, 1.6, [24, 8, 12, 8])
      // High-speed Core Stabilization Ring
      draw3DRing(78, -0.65, 'x', -t * 0.9, ringColorB, 1.8, [14, 6])
      // Central Unobtanium Shield Ring
      draw3DRing(45, 0.3, 'y', t * 1.4, '#ffffff', 2.0)

      // 4. Render 10 Toroidal Magnetic Copper/Gold Coils (Arc Reactor Signature)
      const numCoils = 10
      const coilRadius = 96
      for (let c = 0; c < numCoils; c++) {
        const coilAngle = (c / numCoils) * Math.PI * 2 + t * 0.15
        const cx3d = coilRadius * Math.cos(coilAngle)
        const cy3d = coilRadius * Math.sin(coilAngle)
        const pt = project(cx3d, cy3d, 0)

        // Draw Coil Housing
        ctx.save()
        ctx.fillStyle = state === 'thinking' ? '#ffd700' : '#00e5ff'
        ctx.shadowColor = state === 'thinking' ? '#ff9900' : '#00e5ff'
        ctx.shadowBlur = 10
        ctx.beginPath()
        ctx.arc(pt.x, pt.y, Math.max(3, 5.5 * pt.scale), 0, Math.PI * 2)
        ctx.fill()

        // Energy Arc jumping to center
        ctx.strokeStyle = state === 'thinking' ? 'rgba(255, 200, 50, 0.5)' : 'rgba(0, 229, 255, 0.5)'
        ctx.lineWidth = 1.0
        const centerPt = project(0, 0, 0)
        ctx.beginPath()
        ctx.moveTo(pt.x, pt.y)
        ctx.lineTo(centerPt.x + (Math.random() - 0.5) * 6, centerPt.y + (Math.random() - 0.5) * 6)
        ctx.stroke()
        ctx.restore()
      }

      // 5. 3D Orbiting Quantum Embers
      PARTICLES.forEach((p, idx) => {
        p.theta += p.speed * 0.02 * (state === 'thinking' ? 2.5 : 1.0)
        const currentR = p.orbitRadius + (state === 'listening' ? audioLevel * 18 : Math.sin(t * 4 + idx) * 3)
        const px = currentR * Math.cos(p.phi) * Math.cos(p.theta)
        const py = currentR * Math.sin(p.phi)
        const pz = currentR * Math.cos(p.phi) * Math.sin(p.theta)

        const pt = project(px, py, pz)
        const depth = (pt.z + 140) / 280
        const alpha = Math.max(0.15, Math.min(0.95, 0.3 + depth * 0.6))
        const pRadius = Math.max(0.8, p.baseRadius * (0.8 + depth * 0.4))

        ctx.globalAlpha = alpha
        ctx.fillStyle = state === 'thinking' ? '#ffd700' : p.color
        ctx.beginPath()
        ctx.arc(pt.x, pt.y, pRadius, 0, Math.PI * 2)
        ctx.fill()
      })
      ctx.globalAlpha = 1.0

      // 6. Central Molten Reactor Heart
      const centerPt = project(0, 0, 0)
      const coreR = Math.max(16, 24 + (state === 'speaking' ? Math.sin(t * 12) * 5 : audioLevel * 14))
      const coreGrad = ctx.createRadialGradient(centerPt.x, centerPt.y, 2, centerPt.x, centerPt.y, coreR)
      coreGrad.addColorStop(0, '#ffffff')
      coreGrad.addColorStop(0.35, coreColor)
      coreGrad.addColorStop(0.8, state === 'thinking' ? '#b45309' : '#0369a1')
      coreGrad.addColorStop(1, 'transparent')

      ctx.fillStyle = coreGrad
      ctx.beginPath()
      ctx.arc(centerPt.x, centerPt.y, coreR, 0, Math.PI * 2)
      ctx.fill()

      // Central Stark Triangular Core Mask
      ctx.save()
      ctx.strokeStyle = '#ffffff'
      ctx.lineWidth = 1.8
      ctx.beginPath()
      const triRadius = 14
      for (let i = 0; i < 3; i++) {
        const ang = (i * 2 * Math.PI) / 3 - Math.PI / 2 + t * 0.5
        const tx = centerPt.x + triRadius * Math.cos(ang)
        const ty = centerPt.y + triRadius * Math.sin(ang)
        if (i === 0) ctx.moveTo(tx, ty)
        else ctx.lineTo(tx, ty)
      }
      ctx.closePath()
      ctx.stroke()
      ctx.restore()

      ctx.restore()
      animId = requestAnimationFrame(render)
    }

    render()

    return () => {
      running = false
      cancelAnimationFrame(animId)
    }
  }, [state, audioLevel, size])

  const stateLabels: Record<ReactorState, { label: string; badge: string }> = {
    idle: { label: 'STANDBY // GPT-6 ASTRA READY', badge: 'border-cyan-500/50 text-cyan-300' },
    listening: { label: 'ACOUSTIC SENSORS ACTIVE', badge: 'border-cyan-400 text-cyan-200 animate-pulse' },
    thinking: { label: 'NEURAL REASONING ENGINE ACTIVE', badge: 'border-amber-400 text-amber-300' },
    executing: { label: 'TOOL EXECUTION & CODE MODIFICATION', badge: 'border-emerald-400 text-emerald-300' },
    speaking: { label: 'VOCALIZING RESPONSE (MIC PAUSED)', badge: 'border-orange-500 text-orange-400' },
  }

  const currentBadge = stateLabels[state] || stateLabels.idle

  return (
    <div
      onClick={onClick}
      className={`relative flex flex-col items-center justify-center select-none ${
        interactive ? 'cursor-pointer group' : ''
      } ${className}`}
    >
      {/* Top Status Hologram Pill */}
      <div className="mb-1 flex items-center gap-1.5 font-mono text-[9px] font-bold tracking-widest uppercase">
        <span className={`rounded-full border px-3 py-0.5 bg-[#030712]/90 shadow-[0_0_12px_rgba(0,229,255,0.2)] ${currentBadge.badge}`}>
          {currentBadge.label}
        </span>
      </div>

      {/* 3D Arc-Reactor Canvas with HUD Tech Rings */}
      <div className="relative flex items-center justify-center">
        {/* Hologram Reticle SVG Overlay */}
        <svg
          className="absolute inset-0 h-full w-full pointer-events-none opacity-40 group-hover:opacity-70 transition-opacity"
          viewBox="0 0 380 380"
          fill="none"
        >
          <circle cx="190" cy="190" r="175" stroke="#00e5ff" strokeWidth="1" strokeDasharray="12 12" />
          <circle cx="190" cy="190" r="182" stroke="#ff9e0b" strokeWidth="0.8" strokeDasharray="4 24" />
          <path d="M 20 40 L 20 20 L 40 20" stroke="#00e5ff" strokeWidth="1.5" />
          <path d="M 360 40 L 360 20 L 340 20" stroke="#00e5ff" strokeWidth="1.5" />
          <path d="M 20 340 L 20 360 L 40 360" stroke="#ff9e0b" strokeWidth="1.5" />
          <path d="M 360 340 L 360 360 L 340 360" stroke="#ff9e0b" strokeWidth="1.5" />
        </svg>

        <canvas
          ref={canvasRef}
          style={{ width: `${size}px`, height: `${size}px` }}
          className="transition-transform group-hover:scale-[1.02] duration-300"
        />
      </div>

      {/* Bottom Subtitle */}
      <div className="mt-1 flex flex-col items-center text-center">
        <span className="font-mono text-xs font-black tracking-[0.25em] text-white drop-shadow-[0_0_8px_rgba(0,229,255,0.6)]">
          ARC REACTOR // MK-LXXXV
        </span>
        <span className="font-mono text-[9px] tracking-[0.2em] text-cyan-400/80 font-semibold uppercase">
          REASONING CORE: GPT-6 ASTRA
        </span>
      </div>
    </div>
  )
}
