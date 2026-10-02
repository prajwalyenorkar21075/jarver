import { useState, useRef, useEffect, useCallback } from 'react'
import { useJarvisStore } from '../../store/useJarvisStore'

export default function BiometricSecurityModal() {
  const isOpen = useJarvisStore((s) => s.biometricsModalOpen)
  const setIsOpen = useJarvisStore((s) => s.setBiometricsModalOpen)
  const biometrics = useJarvisStore((s) => s.biometrics)
  const setConsent = useJarvisStore((s) => s.setBiometricConsent)
  const verifyFace = useJarvisStore((s) => s.verifyFaceFrame)
  const enrollFace = useJarvisStore((s) => s.enrollFaceFrame)
  const enrollVoice = useJarvisStore((s) => s.enrollVoiceAudio)
  const purgeBiometrics = useJarvisStore((s) => s.purgeBiometrics)
  const switchUser = useJarvisStore((s) => s.switchUserRole)
  const toggleCamera = useJarvisStore((s) => s.toggleCameraActive)

  const [stream, setStream] = useState<MediaStream | null>(null)
  const [cameraActive, setCameraActive] = useState(false)
  const [cameraError, setCameraError] = useState<string | null>(null)
  const [isEnrollingVoice, setIsEnrollingVoice] = useState(false)
  const [enrollProgress, setEnrollProgress] = useState<string | null>(null)
  const [detectedFaces, setDetectedFaces] = useState<any[]>([])

  const videoRef = useRef<HTMLVideoElement | null>(null)
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const overlayCanvasRef = useRef<HTMLCanvasElement | null>(null)

  // Start Camera
  const startCamera = async () => {
    try {
      setCameraError(null)
      const media = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 } },
        audio: false,
      })
      setStream(media)
      if (videoRef.current) {
        videoRef.current.srcObject = media
        videoRef.current.play().catch(() => {})
      }
      setCameraActive(true)
      toggleCamera(true)
    } catch (err: any) {
      console.warn('Camera access denied or unavailable:', err)
      setCameraError('Camera access required for live facial verification. Please permit camera in browser.')
      setCameraActive(false)
      toggleCamera(false)
    }
  }

  // Stop Camera
  const stopCamera = useCallback(() => {
    if (stream) {
      stream.getTracks().forEach((t) => t.stop())
      setStream(null)
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
    setCameraActive(false)
    toggleCamera(false)
  }, [stream, toggleCamera])

  // Continuous Face Scan Loop when camera is active
  useEffect(() => {
    if (!isOpen || !cameraActive) return

    const interval = setInterval(async () => {
      if (!videoRef.current || !canvasRef.current) return
      const video = videoRef.current
      if (video.readyState < 2) return

      const canvas = canvasRef.current
      canvas.width = video.videoWidth || 320
      canvas.height = video.videoHeight || 240
      const ctx = canvas.getContext('2d')
      if (!ctx) return

      ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
      const base64 = canvas.toDataURL('image/jpeg', 0.75)

      const result = await verifyFace(base64)
      if (result && result.detected && Array.isArray(result.faces)) {
        setDetectedFaces(result.faces)
        drawOverlay(result.faces, canvas.width, canvas.height)
      } else {
        setDetectedFaces([])
        clearOverlay()
      }
    }, 1200)

    return () => clearInterval(interval)
  }, [isOpen, cameraActive, verifyFace])

  // Draw HUD bounding reticles over detected faces
  const drawOverlay = (faces: any[], w: number, h: number) => {
    const overlay = overlayCanvasRef.current
    if (!overlay) return
    overlay.width = w
    overlay.height = h
    const ctx = overlay.getContext('2d')
    if (!ctx) return
    ctx.clearRect(0, 0, w, h)

    faces.forEach((f) => {
      const [x, y, fw, fh] = f.bbox
      const isOwner = f.role === 'owner'
      const color = isOwner ? '#00e5ff' : '#f59e0b'

      // Corner brackets HUD reticle
      ctx.strokeStyle = color
      ctx.lineWidth = 2
      const lineLen = Math.min(fw, fh) * 0.25

      // Top-Left
      ctx.beginPath()
      ctx.moveTo(x, y + lineLen)
      ctx.lineTo(x, y)
      ctx.lineTo(x + lineLen, y)
      ctx.stroke()

      // Top-Right
      ctx.beginPath()
      ctx.moveTo(x + fw - lineLen, y)
      ctx.lineTo(x + fw, y)
      ctx.lineTo(x + fw, y + lineLen)
      ctx.stroke()

      // Bottom-Left
      ctx.beginPath()
      ctx.moveTo(x, y + fh - lineLen)
      ctx.lineTo(x, y + fh)
      ctx.lineTo(x + lineLen, y + fh)
      ctx.stroke()

      // Bottom-Right
      ctx.beginPath()
      ctx.moveTo(x + fw - lineLen, y + fh)
      ctx.lineTo(x + fw, y + fh)
      ctx.lineTo(x + fw, y + fh - lineLen)
      ctx.stroke()

      // Holographic Name & Confidence Tag
      ctx.fillStyle = isOwner ? 'rgba(0, 229, 255, 0.25)' : 'rgba(245, 158, 11, 0.25)'
      ctx.fillRect(x, Math.max(0, y - 24), Math.max(140, fw), 22)
      ctx.fillStyle = color
      ctx.font = 'bold 11px monospace'
      const label = `${f.display_name.toUpperCase()} [${Math.round((f.confidence || 0.95) * 100)}%]`
      ctx.fillText(label, x + 4, Math.max(14, y - 8))
    })
  }

  const clearOverlay = () => {
    const overlay = overlayCanvasRef.current
    if (overlay) {
      const ctx = overlay.getContext('2d')
      if (ctx) ctx.clearRect(0, 0, overlay.width, overlay.height)
    }
  }

  // Handle Face Enrollment
  const handleEnrollFace = async () => {
    if (!biometrics.consentGiven) {
      alert('Please grant biometric processing permission first.')
      return
    }
    if (!cameraActive || !videoRef.current || !canvasRef.current) {
      alert('Please activate camera preview first.')
      return
    }
    setEnrollProgress('Capturing canonical face scan & computing 128-D embedding...')
    const canvas = canvasRef.current
    const video = videoRef.current
    canvas.width = video.videoWidth || 320
    canvas.height = video.videoHeight || 240
    const ctx = canvas.getContext('2d')
    if (ctx) {
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
      const base64 = canvas.toDataURL('image/jpeg', 0.85)
      const res = await enrollFace(base64, 'Tony Stark')
      if (res && res.status === 'ok') {
        setEnrollProgress('✓ Face scan successfully encoded and saved!')
      } else {
        setEnrollProgress(`⚠️ ${res?.message || 'Face enrollment failed'}`)
      }
      setTimeout(() => setEnrollProgress(null), 4000)
    }
  }

  // Handle Voice Enrollment
  const handleEnrollVoice = async () => {
    if (!biometrics.consentGiven) {
      alert('Please grant biometric processing permission first.')
      return
    }
    try {
      setIsEnrollingVoice(true)
      setEnrollProgress('🎙️ Recording 3 seconds of speech... Please speak into microphone.')

      const micStream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(micStream)
      const chunks: Blob[] = []

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.push(e.data)
      }

      recorder.onstop = async () => {
        micStream.getTracks().forEach((t) => t.stop())
        const blob = new Blob(chunks, { type: 'audio/wav' })
        const reader = new FileReader()
        reader.onloadend = async () => {
          const base64 = reader.result as string
          const res = await enrollVoice(base64, 'Tony Stark')
          setIsEnrollingVoice(false)
          if (res && res.status === 'ok') {
            setEnrollProgress('✓ Acoustic voice signature enrolled successfully!')
          } else {
            setEnrollProgress(`⚠️ ${res?.message || 'Voice sample error'}`)
          }
          setTimeout(() => setEnrollProgress(null), 4000)
        }
        reader.readAsDataURL(blob)
      }

      recorder.start()
      setTimeout(() => {
        if (recorder.state === 'recording') recorder.stop()
      }, 3200)
    } catch (err: any) {
      setIsEnrollingVoice(false)
      setEnrollProgress(`⚠️ Microphone access denied: ${err?.message}`)
      setTimeout(() => setEnrollProgress(null), 4000)
    }
  }

  const handleClose = () => {
    stopCamera()
    setIsOpen(false)
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md p-4 select-none">
      <div className="relative w-full max-w-4xl rounded-2xl border border-cyan-500/50 bg-[#040916] p-6 shadow-[0_0_40px_rgba(0,229,255,0.18)] font-mono text-white max-h-[90vh] overflow-y-auto">
        {/* Top Header */}
        <div className="flex items-center justify-between border-b border-cyan-500/30 pb-4">
          <div className="flex items-center gap-3">
            <div className="relative flex h-10 w-10 items-center justify-center rounded-lg border border-cyan-400 bg-[#071530] text-[#00e5ff] shadow-[0_0_12px_rgba(0,229,255,0.4)]">
              <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 2a5 5 0 0 0-5 5v3a5 5 0 0 0 10 0V7a5 5 0 0 0-5-5Z" />
                <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                <line x1="12" y1="19" x2="12" y2="22" stroke="currentColor" strokeWidth="2" />
              </svg>
            </div>
            <div>
              <h2 className="text-base font-bold tracking-wider text-cyan-300">
                BIOMETRIC SECURITY & NEURAL IDENTITY
              </h2>
              <p className="text-[11px] text-cyan-400/60">
                AEROSPACE MULTI-MODAL RECOGNITION // LOCAL EMBEDDINGS ONLY
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={handleClose}
            className="cursor-pointer rounded-lg border border-cyan-500/40 bg-[#071530] px-3 py-1 text-xs text-cyan-300 hover:bg-cyan-500 hover:text-black transition-all"
          >
            ✕ CLOSE
          </button>
        </div>

        {/* Status Pill Strip */}
        <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
          <div className="rounded-xl border border-cyan-500/20 bg-[#071530]/80 p-3">
            <span className="text-[10px] text-cyan-400/60 uppercase">Active Identity</span>
            <div className="mt-1 flex items-center gap-2">
              <span className={`h-2.5 w-2.5 rounded-full ${biometrics.isOwner ? 'bg-cyan-400 animate-pulse' : 'bg-amber-400'}`} />
              <span className="font-bold text-white text-sm">{biometrics.displayName}</span>
            </div>
            <span className={`text-[10px] uppercase font-semibold ${biometrics.isOwner ? 'text-[#00e5ff]' : 'text-amber-400'}`}>
              Role: {biometrics.role}
            </span>
          </div>

          <div className="rounded-xl border border-cyan-500/20 bg-[#071530]/80 p-3">
            <span className="text-[10px] text-cyan-400/60 uppercase">Facial Verification</span>
            <div className="mt-1 text-sm font-bold">
              {biometrics.faceMatched ? (
                <span className="text-emerald-400">✓ VERIFIED ({Math.round(biometrics.faceConfidence * 100)}%)</span>
              ) : (
                <span className="text-white/40">STANDBY / UNMATCHED</span>
              )}
            </div>
            <span className="text-[10px] text-cyan-400/60">
              {biometrics.hasEnrolledFace ? 'Profile: Enrolled' : 'Profile: Not Enrolled'}
            </span>
          </div>

          <div className="rounded-xl border border-cyan-500/20 bg-[#071530]/80 p-3">
            <span className="text-[10px] text-cyan-400/60 uppercase">Voice Identification</span>
            <div className="mt-1 text-sm font-bold">
              {biometrics.voiceMatched ? (
                <span className="text-emerald-400">✓ VERIFIED ({Math.round(biometrics.voiceConfidence * 100)}%)</span>
              ) : (
                <span className="text-white/40">STANDBY / SILENT</span>
              )}
            </div>
            <span className="text-[10px] text-cyan-400/60">
              {biometrics.hasEnrolledVoice ? 'Profile: Enrolled' : 'Profile: Not Enrolled'}
            </span>
          </div>

          <div className="rounded-xl border border-cyan-500/20 bg-[#071530]/80 p-3">
            <span className="text-[10px] text-cyan-400/60 uppercase">Hardware Sensors</span>
            <div className="mt-1 text-xs space-y-1">
              <div className="flex items-center justify-between">
                <span>Camera:</span>
                <span className={cameraActive ? 'text-emerald-400 font-bold' : 'text-white/40'}>
                  {cameraActive ? 'ACTIVE 🟢' : 'OFF ⚪'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span>Consent:</span>
                <span className={biometrics.consentGiven ? 'text-cyan-300 font-bold' : 'text-amber-400'}>
                  {biometrics.consentGiven ? 'GRANTED' : 'PENDING'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Notification / Progress banner */}
        {enrollProgress && (
          <div className="mt-3 rounded-lg border border-cyan-400 bg-cyan-950/60 px-4 py-2 text-xs text-cyan-200 animate-pulse">
            {enrollProgress}
          </div>
        )}

        {/* Main Content 2-Column Split */}
        <div className="mt-4 grid grid-cols-1 lg:grid-cols-12 gap-5">
          {/* Left Column: Live Camera Video with Reticle (7 cols) */}
          <div className="lg:col-span-7 flex flex-col gap-3">
            <div className="relative aspect-[4/3] w-full rounded-xl border border-cyan-500/40 bg-black overflow-hidden flex items-center justify-center shadow-[inset_0_0_30px_rgba(0,229,255,0.1)]">
              {/* HTML5 Video */}
              <video
                ref={videoRef}
                playsInline
                muted
                className={`h-full w-full object-cover ${cameraActive ? 'block' : 'hidden'}`}
              />

              {/* Overlay Canvas for HUD Bounding Boxes */}
              <canvas
                ref={overlayCanvasRef}
                className={`absolute inset-0 pointer-events-none h-full w-full ${cameraActive ? 'block' : 'hidden'}`}
              />

              {/* Hidden Canvas for Frame Capture */}
              <canvas ref={canvasRef} className="hidden" />

              {!cameraActive && (
                <div className="text-center p-6 space-y-2">
                  <div className="mx-auto h-12 w-12 rounded-full border border-cyan-500/40 bg-[#071530] flex items-center justify-center text-cyan-400">
                    📷
                  </div>
                  <div className="text-xs text-cyan-300 font-semibold">Camera Standby</div>
                  <p className="text-[11px] text-cyan-400/50 max-w-xs">
                    Click "Activate Camera" to initiate real-time local facial recognition.
                  </p>
                </div>
              )}

              {/* Live Tag Pill inside camera view */}
              {cameraActive && (
                <div className="absolute top-3 left-3 z-10 flex items-center gap-1.5 rounded-full bg-black/70 px-2.5 py-1 text-[10px] font-mono border border-cyan-400/40 text-cyan-300">
                  <span className="h-2 w-2 rounded-full bg-emerald-400 animate-ping" />
                  <span>LIVE RECOGNITION HUD</span>
                </div>
              )}
            </div>

            {/* Live Detected Faces Badges */}
            {detectedFaces.length > 0 && (
              <div className="flex flex-wrap gap-2 text-[10px]">
                {detectedFaces.map((f, i) => (
                  <span
                    key={i}
                    className={`px-2.5 py-0.5 rounded border ${
                      f.role === 'owner'
                        ? 'border-cyan-400/60 bg-cyan-950/40 text-cyan-300 shadow-[0_0_6px_rgba(0,229,255,0.2)]'
                        : 'border-amber-400/60 bg-amber-950/40 text-amber-300'
                    }`}
                  >
                    Target #{i + 1}: {f.display_name} [{Math.round((f.confidence || 0.95) * 100)}%]
                  </span>
                ))}
              </div>
            )}


            {cameraError && (
              <div className="text-xs text-amber-400 bg-amber-950/40 border border-amber-500/40 p-2 rounded-lg">
                ⚠️ {cameraError}
              </div>
            )}

            {/* Camera Controls */}
            <div className="flex items-center gap-2">
              {!cameraActive ? (
                <button
                  type="button"
                  onClick={startCamera}
                  className="flex-1 cursor-pointer rounded-lg bg-[#00e5ff] py-2 text-xs font-bold text-black hover:bg-cyan-300 transition-all shadow-[0_0_12px_rgba(0,229,255,0.4)]"
                >
                  ▶ ACTIVATE CAMERA FEED
                </button>
              ) : (
                <button
                  type="button"
                  onClick={stopCamera}
                  className="flex-1 cursor-pointer rounded-lg border border-red-500/60 bg-red-950/40 py-2 text-xs font-bold text-red-300 hover:bg-red-900/60 transition-all"
                >
                  ⏹ STOP CAMERA FEED
                </button>
              )}

              <button
                type="button"
                onClick={handleEnrollFace}
                disabled={!cameraActive || !biometrics.consentGiven}
                className="cursor-pointer rounded-lg border border-cyan-500/50 bg-[#071530] px-4 py-2 text-xs font-bold text-[#00e5ff] hover:bg-[#00e5ff] hover:text-black transition-all disabled:opacity-40 disabled:pointer-events-none"
              >
                📸 ENROLL FACE
              </button>
            </div>
          </div>

          {/* Right Column: Biometric Actions, Consent & Permissions (5 cols) */}
          <div className="lg:col-span-5 flex flex-col gap-4 text-xs">
            {/* 1. Explicit Consent Card */}
            <div className="rounded-xl border border-cyan-500/30 bg-[#071530]/60 p-4">
              <div className="flex items-start gap-2.5">
                <input
                  type="checkbox"
                  id="consent-check"
                  checked={biometrics.consentGiven}
                  onChange={(e) => setConsent(e.target.checked)}
                  className="mt-0.5 h-4 w-4 rounded border-cyan-400 bg-black text-[#00e5ff] cursor-pointer"
                />
                <label htmlFor="consent-check" className="cursor-pointer text-[11px] leading-tight text-white/90">
                  <span className="font-bold text-cyan-300">Biometric Consent: </span>
                  I explicitly authorize JARVIS to compute and store local mathematical 128-D vector embeddings for face and voice identification.
                </label>
              </div>
              <p className="mt-2 text-[10px] text-cyan-400/50">
                🔒 Privacy Guarantee: No raw photos or audio recordings are saved on disk. Only non-reversible mathematical vectors are stored locally in SQLite.
              </p>
            </div>

            {/* 2. Voice Enrollment Card */}
            <div className="rounded-xl border border-cyan-500/30 bg-[#071530]/60 p-4 flex flex-col gap-2">
              <span className="font-bold text-cyan-300">Acoustic Speaker Signature</span>
              <p className="text-[11px] text-cyan-400/60">
                Record 3 seconds of voice sample to calibrate acoustic Mel-spectral speaker recognition.
              </p>
              <button
                type="button"
                onClick={handleEnrollVoice}
                disabled={isEnrollingVoice || !biometrics.consentGiven}
                className="cursor-pointer flex items-center justify-center gap-2 rounded-lg border border-amber-500/60 bg-amber-950/30 py-2 font-bold text-amber-300 hover:bg-amber-500 hover:text-black transition-all disabled:opacity-40"
              >
                <span>🎙️</span>
                <span>{isEnrollingVoice ? 'RECORDING VOICE...' : 'ENROLL MY VOICE SIGNATURE'}</span>
              </button>
            </div>

            {/* 3. Role Switcher for Multi-User Testing */}
            <div className="rounded-xl border border-cyan-500/30 bg-[#071530]/60 p-4 flex flex-col gap-2.5">
              <span className="font-bold text-cyan-300">Simulate Identity Switch</span>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => switchUser('owner', 'Tony Stark')}
                  className={`cursor-pointer rounded-lg py-1.5 font-bold transition-all border ${
                    biometrics.isOwner
                      ? 'border-[#00e5ff] bg-[#00e5ff] text-black shadow-[0_0_10px_rgba(0,229,255,0.4)]'
                      : 'border-cyan-500/30 bg-[#071530] text-cyan-300 hover:border-[#00e5ff]'
                  }`}
                >
                  🛡️ OWNER (TONY)
                </button>
                <button
                  type="button"
                  onClick={() => switchUser('guest', 'Guest User')}
                  className={`cursor-pointer rounded-lg py-1.5 font-bold transition-all border ${
                    !biometrics.isOwner
                      ? 'border-amber-400 bg-amber-400 text-black shadow-[0_0_10px_rgba(245,158,11,0.4)]'
                      : 'border-cyan-500/30 bg-[#071530] text-cyan-300 hover:border-amber-400'
                  }`}
                >
                  👤 GUEST MODE
                </button>
              </div>

              {/* Permissions Checklist */}
              <div className="mt-1 space-y-1 text-[11px] border-t border-cyan-500/20 pt-2">
                <div className="flex justify-between">
                  <span className="text-cyan-400/60">Workstation Shutdown:</span>
                  <span className={biometrics.isOwner ? 'text-emerald-400 font-bold' : 'text-red-400'}>
                    {biometrics.isOwner ? 'AUTHORIZED ✓' : 'LOCKED ✕'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-cyan-400/60">App Termination:</span>
                  <span className={biometrics.isOwner ? 'text-emerald-400 font-bold' : 'text-red-400'}>
                    {biometrics.isOwner ? 'AUTHORIZED ✓' : 'LOCKED ✕'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-cyan-400/60">Multitask AI Brain:</span>
                  <span className="text-emerald-400 font-bold">AUTHORIZED ✓</span>
                </div>
              </div>
            </div>

            {/* 4. Purge All Biometric Data Button */}
            <button
              type="button"
              onClick={() => {
                if (confirm('Permanently purge all biometric face scans and voice embeddings from local database?')) {
                  purgeBiometrics()
                }
              }}
              className="cursor-pointer rounded-lg border border-red-500/50 bg-red-950/20 py-2 text-xs font-bold text-red-400 hover:bg-red-900/40 hover:text-white transition-all text-center"
            >
              🗑️ PURGE ALL BIOMETRIC DATA
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
