import { useState, useRef, useEffect } from 'react'

export function VisionPanel() {
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [faces, setFaces] = useState<any[]>([])
  const [error, setError] = useState<string | null>(null)
  const streamRef = useRef<MediaStream | null>(null)

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480 }
      })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        setIsStreaming(true)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Camera access failed')
    }
  }

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop())
      streamRef.current = null
      setIsStreaming(false)
      setFaces([])
    }
  }

  const captureAndAnalyze = async () => {
    if (!videoRef.current || !canvasRef.current) return

    const video = videoRef.current
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    ctx.drawImage(video, 0, 0)

    canvas.toBlob(async (blob) => {
      if (!blob) return

      try {
        const formData = new FormData()
        formData.append('file', blob, 'frame.png')

        const res = await fetch('/api/vision/analyze', {
          method: 'POST',
          body: formData,
        })

        if (res.ok) {
          const data = await res.json()
          setFaces(data.faces || [])
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Analysis failed')
      }
    }, 'image/png')
  }

  useEffect(() => {
    return () => {
      stopCamera()
    }
  }, [])

  return (
    <div className="flex flex-col gap-4 p-6 bg-black/40 backdrop-blur-xl border border-cyan-500/20 rounded-lg">
      <h2 className="text-2xl font-bold text-cyan-400 font-mono">VISION / FACE DETECTION</h2>

      <div className="flex gap-2">
        <button
          onClick={isStreaming ? stopCamera : startCamera}
          className={`px-4 py-2 border rounded font-mono text-sm transition-all ${
            isStreaming
              ? 'bg-red-500/20 hover:bg-red-500/30 border-red-400/50 text-red-300'
              : 'bg-cyan-500/20 hover:bg-cyan-500/30 border-cyan-400/50 text-cyan-300'
          }`}
        >
          {isStreaming ? 'STOP CAMERA' : 'START CAMERA'}
        </button>
        {isStreaming && (
          <button
            onClick={captureAndAnalyze}
            className="px-4 py-2 bg-green-500/20 hover:bg-green-500/30 border border-green-400/50 rounded text-green-300 font-mono text-sm transition-all"
          >
            ANALYZE FRAME
          </button>
        )}
      </div>

      {error && (
        <div className="p-3 bg-red-500/10 border border-red-400/30 rounded text-red-300 text-sm">
          Error: {error}
        </div>
      )}

      <div className="relative bg-black/60 border border-cyan-500/30 rounded overflow-hidden">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="w-full h-auto"
        />
        <canvas
          ref={canvasRef}
          className="hidden"
        />

        {faces.length > 0 && (
          <div className="absolute top-2 right-2 px-3 py-1 bg-green-500/20 border border-green-400/50 rounded text-green-300 font-mono text-xs">
            {faces.length} FACE{faces.length > 1 ? 'S' : ''} DETECTED
          </div>
        )}
      </div>

      {faces.length > 0 && (
        <div className="flex flex-col gap-2">
          <div className="text-sm text-gray-400 font-mono">Detected Faces:</div>
          {faces.map((face, idx) => (
            <div key={idx} className="p-2 bg-black/40 border border-cyan-500/20 rounded text-sm">
              <div className="text-cyan-300 font-mono">Face #{idx + 1}</div>
              {face.confidence && (
                <div className="text-xs text-gray-400">
                  Confidence: {(face.confidence * 100).toFixed(1)}%
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {!isStreaming && (
        <div className="text-center py-8 text-gray-500 font-mono">
          Click "START CAMERA" to begin face detection
        </div>
      )}
    </div>
  )
}
