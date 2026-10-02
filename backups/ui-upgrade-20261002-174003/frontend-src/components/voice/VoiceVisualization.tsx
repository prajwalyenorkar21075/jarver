import { useEffect, useRef, useState } from 'react'
import { useJarvisStore } from '../../store/useJarvisStore'

interface VoiceVisualizationProps {
  className?: string
}

export function VoiceVisualization({ className = '' }: VoiceVisualizationProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animationRef = useRef<number | null>(null)
  const [audioLevels, setAudioLevels] = useState<number[]>(new Array(32).fill(0))
  const audioLevel = useJarvisStore((state) => state.audioLevel)
  const voiceState = useJarvisStore((state) => state.voiceStatus)
  const isListening = useJarvisStore((state) => state.isListening)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const width = canvas.width
    const height = canvas.height
    const barCount = 32
    const barWidth = width / barCount - 2
    const gap = 2

    const animate = () => {
      ctx.clearRect(0, 0, width, height)

      const newLevels = audioLevels.map((level, i) => {
        const target = i === Math.floor(barCount / 2) ? audioLevel : audioLevel * (0.5 + Math.random() * 0.5)
        return level * 0.7 + target * 0.3
      })
      setAudioLevels(newLevels)

      newLevels.forEach((level, i) => {
        const barHeight = level * height * 0.8
        const x = i * (barWidth + gap)
        const y = (height - barHeight) / 2

        const gradient = ctx.createLinearGradient(0, y, 0, y + barHeight)
        
        if (voiceState === 'speaking') {
          gradient.addColorStop(0, '#00d4ff')
          gradient.addColorStop(0.5, '#0099ff')
          gradient.addColorStop(1, '#0066cc')
        } else if (voiceState === 'listening_wakeword' || voiceState === 'listening_command') {
          gradient.addColorStop(0, '#00ff88')
          gradient.addColorStop(0.5, '#00cc66')
          gradient.addColorStop(1, '#009944')
        } else if (voiceState === 'processing') {
          gradient.addColorStop(0, '#ffaa00')
          gradient.addColorStop(0.5, '#ff8800')
          gradient.addColorStop(1, '#ff6600')
        } else {
          gradient.addColorStop(0, '#666666')
          gradient.addColorStop(0.5, '#444444')
          gradient.addColorStop(1, '#333333')
        }

        ctx.fillStyle = gradient
        ctx.fillRect(x, y, barWidth, barHeight)
      })

      animationRef.current = requestAnimationFrame(animate)
    }

    animate()

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [audioLevel, voiceState, audioLevels])

  return (
    <div className={`relative ${className}`}>
      <canvas
        ref={canvasRef}
        width={512}
        height={128}
        className="w-full h-full"
      />
      {isListening && (
        <div className="absolute top-2 right-2 flex items-center gap-2">
          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
          <span className="text-xs text-green-400 font-mono">LISTENING</span>
        </div>
      )}
    </div>
  )
}
