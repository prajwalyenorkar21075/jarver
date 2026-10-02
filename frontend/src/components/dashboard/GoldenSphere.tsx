import { useEffect, useRef } from 'react'

// ============================================================================
// GOLDEN PARTICLE SPHERE v2 — studied from 8930741b (clear master frame)
//
// What the image actually is, element by element:
//  1. Small glowing TORUS RING at centre (bright gold rim, dark hole).
//  2. THIN RADIAL SPOKES from the ring outward (slightly wobbly threads).
//  3. A SPHERE SHELL of tangled golden arcs + circuit-like filaments,
//     brighter/denser toward the rim, dark hollow middle band.
//  4. Dense BOKEH sparkle: hundreds of soft out-of-focus gold dots,
//     clustered top and bottom, a few big blurred orbs.
//  5. Pure black background. No text, no frames, no straight UI lines.
// ============================================================================

function mulberry(seed: number) {
  let s = seed >>> 0
  return () => {
    s = (s + 0x6d2b79f5) >>> 0
    let z = s
    z = Math.imul(z ^ (z >>> 15), z | 1)
    z ^= z + Math.imul(z ^ (z >>> 7), z | 61)
    return ((z ^ (z >>> 14)) >>> 0) / 4294967296
  }
}

interface ShellArc { tilt: number; phase: number; r: number; len: number; a: number; w: number; sp: number }
interface Spoke { ang: number; wob: number; len: number; bright: boolean; drift: number }
interface Bokeh { x: number; y: number; r: number; tw: number; sp: number; big: boolean }
interface Filament { cx: number; cy: number; r: number; a0: number; a1: number; jag: number[] }

export default function GoldenSphere({ size = 620 }: { size?: number }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const dpr = Math.min(2, window.devicePixelRatio || 1)
    canvas.width = Math.round(size * dpr)
    canvas.height = Math.round(size * dpr)
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let raf = 0
    let running = true
    const rnd = mulberry(777001)
    const S = size
    const cx = S / 2
    const cy = S / 2
    const R = S * 0.44

    // shell arcs: tilted great-circle fragments
    const ARCS: ShellArc[] = []
    for (let i = 0; i < 70; i++) {
      ARCS.push({
        tilt: rnd() * Math.PI * 2,
        phase: rnd() * Math.PI * 2,
        r: 0.45 + Math.pow(rnd(), 0.7) * 0.55,
        len: Math.PI * (0.4 + rnd() * 1.6),
        a: 0.1 + rnd() * 0.45,
        w: 0.5 + rnd() * 1.1,
        sp: 0.04 + rnd() * 0.14,
      })
    }
    // radial spokes from the centre ring
    const SPOKES: Spoke[] = []
    for (let i = 0; i < 30; i++) {
      SPOKES.push({
        ang: (i / 30) * Math.PI * 2 + (rnd() - 0.5) * 0.4,
        wob: 0.5 + rnd() * 2,
        len: 0.35 + rnd() * 0.6,
        bright: rnd() > 0.5,
        drift: (rnd() - 0.5) * 0.06,
      })
    }
    // bokeh sparkle, clustered top + bottom like the frame
    const BOKEH: Bokeh[] = []
    for (let i = 0; i < 260; i++) {
      const topBias = rnd() > 0.42
      const y = topBias
        ? cy - R * (0.25 + rnd() * 0.85)
        : cy + R * (rnd() * 0.9 - 0.15)
      const x = cx + (rnd() - 0.5) * 2 * R * 1.05
      BOKEH.push({
        x, y,
        r: 0.6 + Math.pow(rnd(), 2.2) * 7,
        tw: rnd() * Math.PI * 2,
        sp: 0.6 + rnd() * 2.2,
        big: rnd() > 0.93,
      })
    }
    // rim filaments: short jagged circuit-like polylines near the edge
    const FILS: Filament[] = []
    for (let i = 0; i < 46; i++) {
      const a = rnd() * Math.PI * 2
      const rr = R * (0.8 + rnd() * 0.22)
      const jag = Array.from({ length: 6 }, () => (rnd() - 0.5) * 14)
      FILS.push({ cx: cx + Math.cos(a) * rr, cy: cy + Math.sin(a) * rr * 0.96, r: 8 + rnd() * 26, a0: rnd() * Math.PI * 2, a1: 0.6 + rnd() * 1.8, jag })
    }

    const render = () => {
      if (!running) return
      const t = performance.now() / 1000
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      ctx.clearRect(0, 0, S, S)
      ctx.fillStyle = '#000'
      ctx.fillRect(0, 0, S, S)

      const shim = 0.8 + Math.sin(t * 1.6) * 0.12 + Math.sin(t * 4.1) * 0.08
      const spin = t * 0.12

      // 1. faint warm breath (kept very low — light lives on the lines)
      const breath = ctx.createRadialGradient(cx, cy, 1, cx, cy, R * 1.1)
      breath.addColorStop(0, 'rgba(255,175,80,0.15)')
      breath.addColorStop(0.4, 'rgba(140,75,25,0.08)')
      breath.addColorStop(1, 'rgba(0,0,0,0)')
      ctx.fillStyle = breath
      ctx.beginPath(); ctx.arc(cx, cy, R * 1.1, 0, Math.PI * 2); ctx.fill()

      // 2. back shell arcs
      const drawArcs = (front: boolean) => {
        ARCS.forEach((a) => {
          const rot = a.phase + t * a.sp + spin * 0.5
          ctx.save()
          ctx.strokeStyle = `rgba(255,${168 + Math.floor(30 * shim)},85,${(a.a * shim).toFixed(3)})`
          ctx.lineWidth = a.w
          ctx.lineCap = 'round'
          ctx.beginPath()
          let started = false
          const steps = 40
          for (let k = 0; k <= steps; k++) {
            const p = rot + (k / steps) * a.len
            const x = Math.cos(p) * a.r
            const y = Math.sin(p) * a.r
            // fake depth: tilt plane + wobble
            const z = Math.sin(p * 2 + a.tilt) * 0.35
            const xr = x * Math.cos(a.tilt) - z * Math.sin(a.tilt)
            const zr = x * Math.sin(a.tilt) + z * Math.cos(a.tilt)
            const isFront = zr > -0.03
            if (isFront !== front) { started = false; continue }
            const px = cx + xr * R
            const py = cy + y * R * 0.96
            if (!started) { ctx.moveTo(px, py); started = true }
            else ctx.lineTo(px, py)
          }
          ctx.stroke()
          ctx.restore()
        })
      }
      drawArcs(false)

      // 3. centre torus ring
      const rIn = R * 0.115
      ctx.save()
      ctx.strokeStyle = `rgba(255,214,150,${(0.95 * shim).toFixed(3)})`
      ctx.lineWidth = 3
      ctx.beginPath(); ctx.arc(cx, cy, rIn, 0, Math.PI * 2); ctx.stroke()
      ctx.strokeStyle = `rgba(255,150,45,${(0.4 * shim).toFixed(3)})`
      ctx.lineWidth = 8
      ctx.beginPath(); ctx.arc(cx, cy, rIn, 0, Math.PI * 2); ctx.stroke()
      // second faint ring slightly larger (torus thickness in the frame)
      ctx.strokeStyle = `rgba(255,180,90,${(0.3 * shim).toFixed(3)})`
      ctx.lineWidth = 1.6
      ctx.beginPath(); ctx.arc(cx, cy, rIn * 1.45, 0, Math.PI * 2); ctx.stroke()
      ctx.restore()
      const hole = ctx.createRadialGradient(cx, cy, 0, cx, cy, rIn)
      hole.addColorStop(0, 'rgba(0,0,0,0.96)')
      hole.addColorStop(1, 'rgba(0,0,0,0)')
      ctx.fillStyle = hole
      ctx.beginPath(); ctx.arc(cx, cy, rIn, 0, Math.PI * 2); ctx.fill()
      // hot glow hugging the ring
      const halo = ctx.createRadialGradient(cx, cy, rIn * 0.5, cx, cy, rIn * 4)
      halo.addColorStop(0, `rgba(255,210,130,${(0.5 * shim).toFixed(3)})`)
      halo.addColorStop(1, 'rgba(255,150,50,0)')
      ctx.fillStyle = halo
      ctx.beginPath(); ctx.arc(cx, cy, rIn * 4, 0, Math.PI * 2); ctx.fill()

      // 4. radial spokes (thin wobbly threads from ring to shell)
      ctx.save()
      ctx.lineCap = 'round'
      SPOKES.forEach((s, i) => {
        const a = s.ang + t * s.drift + spin * 0.3
        const r0 = rIn * 1.1
        const r1 = rIn + s.len * R
        ctx.strokeStyle = s.bright
          ? `rgba(255,${175 + Math.floor(35 * shim)},100,${(0.7 * shim).toFixed(3)})`
          : `rgba(220,135,50,${(0.4 * shim).toFixed(3)})`
        ctx.lineWidth = s.bright ? 1.6 : 1
        ctx.beginPath()
        const steps = 8
        for (let k = 0; k <= steps; k++) {
          const rr = r0 + ((r1 - r0) * k) / steps
          const wob = Math.sin(k * 1.7 + t * s.wob + i) * 3 * (k / steps)
          const px = cx + Math.cos(a) * rr - Math.sin(a) * wob
          const py = cy + Math.sin(a) * rr * 0.96 + Math.cos(a) * wob
          if (k === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py)
        }
        ctx.stroke()
      })
      ctx.restore()

      // 5. front shell arcs
      drawArcs(true)

      // 6. rim filaments (circuit-like jags near the edge)
      ctx.save()
      ctx.lineCap = 'round'
      FILS.forEach((f, i) => {
        const rot = f.a0 + t * 0.05 * (i % 2 === 0 ? 1 : -1)
        ctx.strokeStyle = `rgba(255,170,80,${(0.35 * shim).toFixed(3)})`
        ctx.lineWidth = 1
        ctx.beginPath()
        const steps = 6
        for (let k = 0; k <= steps; k++) {
          const aa = rot + (k / steps) * f.a1
          const rr = f.r + f.jag[k % f.jag.length] * 0.4
          const px = f.cx + Math.cos(aa) * rr
          const py = f.cy + Math.sin(aa) * rr
          if (k === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py)
        }
        ctx.stroke()
      })
      ctx.restore()

      // 7. bokeh sparkle field (soft blurred gold dots)
      BOKEH.forEach((b) => {
        const tw = 0.3 + 0.7 * (0.5 + 0.5 * Math.sin(t * b.sp + b.tw))
        const driftX = Math.sin(t * 0.3 + b.tw) * 6
        if (b.big) {
          const g = ctx.createRadialGradient(b.x + driftX, b.y, 0, b.x + driftX, b.y, b.r * 2.4)
          g.addColorStop(0, `rgba(255,220,160,${(0.5 * tw).toFixed(3)})`)
          g.addColorStop(1, 'rgba(255,160,60,0)')
          ctx.fillStyle = g
          ctx.beginPath(); ctx.arc(b.x + driftX, b.y, b.r * 2.4, 0, Math.PI * 2); ctx.fill()
        } else {
          ctx.globalAlpha = 0.55 * tw
          ctx.fillStyle = '#f7b95c'
          ctx.beginPath(); ctx.arc(b.x + driftX, b.y, b.r * 0.5, 0, Math.PI * 2); ctx.fill()
        }
      })
      ctx.globalAlpha = 1

      raf = requestAnimationFrame(render)
    }

    render()
    return () => { running = false; cancelAnimationFrame(raf) }
  }, [size])

  return <canvas ref={canvasRef} style={{ width: size, height: size, display: 'block', background: '#000' }} />
}
