import { useEffect, useRef } from 'react'
import { useJarvisStore } from '../../store/useJarvisStore'

export type JarvisCoreState =
  | 'IDLE'
  | 'LISTENING'
  | 'THINKING'
  | 'PROCESSING'
  | 'EXECUTING'
  | 'SPEAKING'
  | 'SUCCESS'
  | 'ERROR'

interface JarvisCoreIndicatorProps {
  size?: number
  showLabel?: boolean
  className?: string
}

export default function JarvisCoreIndicator({
  size = 42,
  showLabel = true,
  className = '',
}: JarvisCoreIndicatorProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const rawVoiceStatus = useJarvisStore((s) => s.voiceStatus) as string
  const backendStatus = useJarvisStore((s) => s.backendStatus)
  const isListening = useJarvisStore((s) => s.isListening)
  const audioLevel = useJarvisStore((s) => s.audioLevel)
  const systemNotice = useJarvisStore((s) => s.systemNotice)
  const executionOutcome = useJarvisStore((s) => s.executionOutcome)

  // Derive exact state required: IDLE, LISTENING, THINKING, PROCESSING, EXECUTING, SPEAKING, SUCCESS, ERROR
  let coreState: JarvisCoreState = 'IDLE'
  if (backendStatus === 'disconnected') {
    coreState = 'ERROR'
  } else if (executionOutcome === 'error' || (systemNotice && systemNotice.toLowerCase().includes('error'))) {
    coreState = 'ERROR'
  } else if (executionOutcome === 'success' || (systemNotice && systemNotice.toLowerCase().includes('success'))) {
    coreState = 'SUCCESS'
  } else if (rawVoiceStatus === 'speaking') {
    coreState = 'SPEAKING'
  } else if (rawVoiceStatus === 'executing') {
    coreState = 'EXECUTING'
  } else if (rawVoiceStatus === 'processing') {
    coreState = 'PROCESSING'
  } else if (rawVoiceStatus === 'thinking') {
    coreState = 'THINKING'
  } else if (isListening || rawVoiceStatus.startsWith('listening')) {
    coreState = 'LISTENING'
  } else {
    coreState = 'IDLE'
  }

  const stateColors: Record<JarvisCoreState, { primary: string; ring: string; glow: string; text: string }> = {
    IDLE: { primary: '#00e5ff', ring: '#00a8c6', glow: 'rgba(0, 229, 255, 0.4)', text: 'text-cyan-400' },
    LISTENING: { primary: '#38bdf8', ring: '#0284c7', glow: 'rgba(56, 189, 248, 0.7)', text: 'text-sky-300' },
    THINKING: { primary: '#f59e0b', ring: '#b45309', glow: 'rgba(245, 158, 11, 0.7)', text: 'text-amber-400' },
    PROCESSING: { primary: '#f97316', ring: '#c2410c', glow: 'rgba(249, 115, 22, 0.7)', text: 'text-orange-400' },
    EXECUTING: { primary: '#10b981', ring: '#047857', glow: 'rgba(16, 185, 129, 0.7)', text: 'text-emerald-400' },
    SPEAKING: { primary: '#06b6d4', ring: '#0e7490', glow: 'rgba(6, 182, 212, 0.7)', text: 'text-cyan-300' },
    SUCCESS: { primary: '#22c55e', ring: '#15803d', glow: 'rgba(34, 197, 94, 0.8)', text: 'text-green-400' },
    ERROR: { primary: '#ef4444', ring: '#b91c1c', glow: 'rgba(239, 68, 68, 0.8)', text: 'text-rose-400' },
  }

  const currentConfig = stateColors[coreState]

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = Math.min(2, window.devicePixelRatio || 1)
    canvas.width = Math.round(size * dpr)
    canvas.height = Math.round(size * dpr)

    let animId = 0
    let running = true

    const draw = () => {
      if (!running) return
      const t = performance.now() / 1000

      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      ctx.clearRect(0, 0, size, size)

      const cx = size / 2
      const cy = size / 2
      const radius = size * 0.42

      // Outer dashed tech ring
      ctx.save()
      ctx.translate(cx, cy)
      let speed = 0.6
      if (coreState === 'PROCESSING' || coreState === 'THINKING') speed = 2.4
      if (coreState === 'EXECUTING') speed = 3.2
      if (coreState === 'LISTENING') speed = 1.0 + audioLevel * 2.0
      ctx.rotate(t * speed)

      ctx.beginPath()
      ctx.arc(0, 0, radius, 0, Math.PI * 2)
      ctx.strokeStyle = currentConfig.ring
      ctx.lineWidth = 1.2
      ctx.setLineDash([4, 3])
      ctx.stroke()

      // Counter-rotating inner segmented ring
      ctx.rotate(-t * speed * 1.8)
      ctx.beginPath()
      ctx.arc(0, 0, radius * 0.75, 0, Math.PI * 2)
      ctx.strokeStyle = currentConfig.primary
      ctx.lineWidth = 1.5
      ctx.setLineDash([6, 6])
      ctx.stroke()
      ctx.restore()

      // Central glowing core
      const pulse =
        coreState === 'LISTENING' || coreState === 'SPEAKING'
          ? 0.75 + Math.sin(t * 8) * 0.25 + audioLevel * 0.4
          : 0.85 + Math.sin(t * 3) * 0.15

      const gradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius * 0.55 * pulse)
      gradient.addColorStop(0, '#ffffff')
      gradient.addColorStop(0.35, currentConfig.primary)
      gradient.addColorStop(1, 'transparent')

      ctx.beginPath()
      ctx.arc(cx, cy, radius * 0.55 * pulse, 0, Math.PI * 2)
      ctx.fillStyle = gradient
      ctx.fill()

      // Micro arc reactor triangular center
      ctx.save()
      ctx.translate(cx, cy)
      ctx.rotate(t * 0.4)
      ctx.beginPath()
      const triR = radius * 0.32
      for (let i = 0; i < 3; i++) {
        const angle = (i * Math.PI * 2) / 3 - Math.PI / 2
        const px = Math.cos(angle) * triR
        const py = Math.sin(angle) * triR
        if (i === 0) ctx.moveTo(px, py)
        else ctx.lineTo(px, py)
      }
      ctx.closePath()
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.85)'
      ctx.lineWidth = 1
      ctx.stroke()
      ctx.restore()

      animId = requestAnimationFrame(draw)
    }

    draw()

    return () => {
      running = false
      cancelAnimationFrame(animId)
    }
  }, [size, coreState, audioLevel, currentConfig])

  return (
    <div className={`flex items-center gap-2.5 rounded border border-cyan-500/25 bg-[#030814]/90 px-2.5 py-1 backdrop-blur-sm ${className}`}>
      <div className="relative flex items-center justify-center shrink-0" style={{ width: size, height: size }}>
        <canvas ref={canvasRef} style={{ width: size, height: size }} />
      </div>
      {showLabel && (
        <div className="flex flex-col min-w-[70px]">
          <span className="font-mono text-[9px] font-bold tracking-[0.2em] text-cyan-300/70">
            J.A.R.V.I.S.
          </span>
          <span className={`font-mono text-[10px] font-black tracking-wider ${currentConfig.text}`}>
            {coreState}
          </span>
        </div>
      )}
    </div>
  )
}
