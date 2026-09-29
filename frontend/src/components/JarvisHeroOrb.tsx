import { useEffect, useRef } from 'react'
import { MODE_FRAMES, resolvePreset, paintFrame, type OrbState } from 'thinking-orbs/engine'
import { useJarvisStore } from '../store/useJarvisStore'

interface JarvisHeroOrbProps {
  size?: number
}

// 3D particle for the volumetric orbital nebula cloud
interface Particle3D {
  x: number
  y: number
  z: number
  baseRadius: number
  speed: number
  angle: number
  inclination: number
  color: string
}

export default function JarvisHeroOrb({ size = 460 }: JarvisHeroOrbProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const orbState = useJarvisStore((s) => s.orbState)
  const isListening = useJarvisStore((s) => s.isListening)
  const setIsListening = useJarvisStore((s) => s.setIsListening)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const dpr = Math.min(2.5, window.devicePixelRatio || 1)
    canvas.width = Math.round(size * dpr)
    canvas.height = Math.round(size * dpr)

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // 150 3D Quantum Nebula Particles orbiting around the enlarged core
    const PARTICLE_COUNT = 150
    const particles: Particle3D[] = []
    const colors = ['#00e5ff', '#38bdf8', '#ff9a3c', '#f59e0b', '#c084fc', '#ffffff', '#22d3ee']

    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const radius = 95 + Math.random() * 115
      const theta = Math.random() * Math.PI * 2
      const phi = (Math.random() - 0.5) * Math.PI

      particles.push({
        x: radius * Math.cos(phi) * Math.cos(theta),
        y: radius * Math.sin(phi),
        z: radius * Math.cos(phi) * Math.sin(theta),
        baseRadius: Math.random() * 2.2 + 1.0,
        speed: (Math.random() * 0.45 + 0.3) * (Math.random() > 0.5 ? 1 : -1),
        angle: Math.random() * Math.PI * 2,
        inclination: Math.random() * 0.7 - 0.35,
        color: colors[Math.floor(Math.random() * colors.length)],
      })
    }

    let rafId = 0
    let running = true

    const render = () => {
      if (!running) return
      const t = performance.now() / 1000

      // Get thinking-orbs preset configuration
      const { mode, speed: baseSpeed, opts } = resolvePreset(orbState as OrbState, 64)
      const frameFn = MODE_FRAMES[mode]

      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      ctx.clearRect(0, 0, size, size)

      const cx = size / 2
      const cy = size / 2

      // 3D rotation angles
      const yaw = t * 0.45
      const pitch = Math.sin(t * 0.3) * 0.35 + 0.1
      const roll = Math.cos(t * 0.2) * 0.2

      const cosY = Math.cos(yaw), sinY = Math.sin(yaw)
      const cosP = Math.cos(pitch), sinP = Math.sin(pitch)
      const cosR = Math.cos(roll), sinR = Math.sin(roll)

      const project = (x: number, y: number, z: number): [number, number, number] => {
        const x1 = x * cosY - z * sinY
        const z1 = x * sinY + z * cosY
        const y2 = y * cosP - z1 * sinP
        const z2 = y * sinP + z1 * cosP
        const x3 = x1 * cosR - y2 * sinR
        const y3 = x1 * sinR + y2 * cosR
        const fov = 480
        const scale = fov / (fov + z2)
        return [cx + x3 * scale, cy + y3 * scale, z2]
      }

      ctx.save()

      // 1. Ambient Volumetric Radiant Nebula Core (Golden Heart + Cyan Ion Corona)
      const radialGlow = ctx.createRadialGradient(cx, cy, 8, cx, cy, size * 0.48)
      radialGlow.addColorStop(0, 'rgba(255, 175, 45, 0.48)')
      radialGlow.addColorStop(0.32, 'rgba(212, 113, 43, 0.3)')
      radialGlow.addColorStop(0.68, 'rgba(0, 229, 255, 0.14)')
      radialGlow.addColorStop(0.9, 'rgba(168, 85, 247, 0.06)')
      radialGlow.addColorStop(1, 'transparent')

      ctx.fillStyle = radialGlow
      ctx.beginPath()
      ctx.arc(cx, cy, size * 0.48, 0, Math.PI * 2)
      ctx.fill()

      // 2. Render 3D Background Particles (depth-sorted behind core, z < 0)
      ctx.globalCompositeOperation = 'screen'

      const projectedParticles = particles.map((p) => {
        // Orbit motion
        p.angle += p.speed * 0.02
        const currentR = 115 + Math.sin(p.angle * 2 + t) * 22
        const px = currentR * Math.cos(p.angle)
        const py = currentR * Math.sin(p.angle * 1.5) * Math.sin(p.inclination * Math.PI)
        const pz = currentR * Math.sin(p.angle) * Math.cos(p.inclination * Math.PI)

        const [sx, sy, sz] = project(px, py, pz)
        return { p, sx, sy, sz }
      })

      // Sort by depth
      projectedParticles.sort((a, b) => a.sz - b.sz)

      // Draw particles behind center (sz < 0)
      for (const item of projectedParticles) {
        if (item.sz >= 0) continue
        const depthAlpha = Math.max(0.12, (item.sz + 160) / 320)
        ctx.fillStyle = item.p.color
        ctx.globalAlpha = depthAlpha * 0.65
        ctx.beginPath()
        ctx.arc(item.sx, item.sy, item.p.baseRadius * (0.7 + depthAlpha * 0.5), 0, Math.PI * 2)
        ctx.fill()
      }

      // 3. Render Thinking Orb (Multi-Chromatic Additive Pass)
      const tSec = (performance.now() / 1000) * baseSpeed
      const orbRenderSize = size * 0.88
      const frame = frameFn(orbRenderSize, tSec, opts)

      // Pass A: Cyan / Blue outer edge radiance
      ctx.save()
      ctx.translate((size - orbRenderSize) / 2, (size - orbRenderSize) / 2)
      ctx.globalAlpha = 0.85
      paintFrame(ctx, frame, true, { r: 0, g: 229, b: 255 })
      ctx.restore()

      // Pass B: Intense Golden Amber Core Highlights
      ctx.save()
      ctx.translate((size - orbRenderSize) / 2, (size - orbRenderSize) / 2)
      ctx.globalAlpha = 0.95
      paintFrame(ctx, frame, true, { r: 255, g: 154, b: 60 })
      ctx.restore()

      // 4. Draw Foreground Particles (sz >= 0) with glowing spark trails
      for (const item of projectedParticles) {
        if (item.sz < 0) continue
        const depthAlpha = Math.min(1, 0.45 + (item.sz / 160) * 0.55)
        ctx.fillStyle = item.p.color
        ctx.globalAlpha = depthAlpha
        ctx.beginPath()
        ctx.arc(item.sx, item.sy, item.p.baseRadius * (1 + (item.sz / 180) * 0.8), 0, Math.PI * 2)
        ctx.fill()
      }

      ctx.restore()
      rafId = requestAnimationFrame(render)
    }

    render()

    return () => {
      running = false
      cancelAnimationFrame(rafId)
    }
  }, [orbState, size])

  return (
    <div className="relative flex flex-col items-center justify-center select-none">
      {/* Outer Hologram Radial Aura Glow */}
      <div
        className="pointer-events-none absolute rounded-full transition-all duration-700 ease-out"
        style={{
          width: size * 1.5,
          height: size * 1.5,
          background: isListening
            ? 'radial-gradient(circle, rgba(0,229,255,0.2) 0%, rgba(212,113,43,0.15) 40%, rgba(168,85,247,0.05) 65%, transparent 75%)'
            : 'radial-gradient(circle, rgba(212,113,43,0.15) 0%, rgba(0,229,255,0.08) 45%, transparent 70%)',
        }}
      />

      {/* Rotating Cybernetic Sci-Fi HUD Rings */}
      <div
        className="pointer-events-none absolute flex items-center justify-center"
        style={{ width: size * 1.3, height: size * 1.3 }}
      >
        {/* Outer Rotating Segmented Amber & Cyan Ring */}
        <svg
          className="absolute inset-0 h-full w-full animate-[spin_40s_linear_infinite] opacity-65"
          viewBox="0 0 600 600"
        >
          <circle
            cx="300"
            cy="300"
            r="280"
            fill="none"
            stroke="#D4712B"
            strokeWidth="1.6"
            strokeDasharray="8 18 48 18 90 18"
            strokeOpacity="0.8"
          />
          <circle
            cx="300"
            cy="300"
            r="262"
            fill="none"
            stroke="#00e5ff"
            strokeWidth="1.2"
            strokeDasharray="10 40 20 40"
            strokeOpacity="0.65"
          />
        </svg>

        {/* Counter-rotating Inner Ring */}
        <svg
          className="absolute inset-0 h-full w-full animate-[spin_25s_linear_infinite_reverse] opacity-55"
          viewBox="0 0 600 600"
        >
          <circle
            cx="300"
            cy="300"
            r="238"
            fill="none"
            stroke="#D4712B"
            strokeWidth="1.4"
            strokeDasharray="3 12 20 12"
          />
          <circle
            cx="300"
            cy="300"
            r="220"
            fill="none"
            stroke="#ffffff"
            strokeWidth="0.9"
            strokeDasharray="1 22"
            strokeOpacity="0.75"
          />
          {/* Cardinal Radar Tick Crosshairs */}
          <line x1="300" y1="20" x2="300" y2="40" stroke="#00e5ff" strokeWidth="2" />
          <line x1="300" y1="560" x2="300" y2="580" stroke="#00e5ff" strokeWidth="2" />
          <line x1="20" y1="300" x2="40" y2="300" stroke="#D4712B" strokeWidth="2" />
          <line x1="560" y1="300" x2="580" y2="300" stroke="#D4712B" strokeWidth="2" />
        </svg>

        {/* Dynamic Audio Pulse Ping Ring when listening */}
        {isListening && (
          <div
            className="absolute inset-0 rounded-full border border-cyan-400/50 animate-ping"
            style={{ animationDuration: '2.2s' }}
          />
        )}
      </div>

      {/* Interactive Main 3D Particle Orb Canvas (Pure Visual, No Clutter Text) */}
      <div
        className="relative z-10 cursor-pointer group transition-transform duration-300 hover:scale-[1.03] active:scale-[0.98]"
        onClick={() => setIsListening(!isListening)}
        title={isListening ? 'Click to pause voice listening' : 'Click to activate voice listening'}
      >
        <canvas
          ref={canvasRef}
          role="img"
          aria-label={`Jarvis Core — ${orbState}`}
          style={{ width: size, height: size, display: 'block' }}
        />
      </div>
    </div>
  )
}

