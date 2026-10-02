/**
 * J.A.R.V.I.S. Unified Voice & Audio Controller
 * 
 * Implements:
 * 1. WebRTC Hardware Echo Cancellation, Noise Suppression & Auto Gain Control
 * 2. Real-Time VAD (Voice Activity Detection) with adaptive noise floor and live audio levels
 * 3. Strict Mute-During-Speech & Acoustic Reverb Cooldown Lifecycle (prevents self-hearing)
 * 4. Anti-Self-Echo & Self-Utterance Filter (discards transcripts matching JARVIS's own speech)
 * 5. Multilingual Wake-Word Engine (English, Hindi, Marathi: "Jarvis", "Hey Jarvis", "जार्विस")
 * 6. Single-Response Guarantee (prevents infinite self-triggering loops)
 * 7. Unified Web Speech API + Neural Whisper Large v3 Fallback
 */

import {
  useJarvisStore,
  guessTextLanguage,
  normalizeSpeechLang,
  playHudChirp,
} from '../store/useJarvisStore'

export type VoiceState =
  | 'idle'
  | 'listening_wakeword'
  | 'listening_command'
  | 'processing'
  | 'speaking'
  | 'cooldown'

// Acoustic reverb cooldown in milliseconds after TTS playback finishes
const ACOUSTIC_COOLDOWN_MS = 750

// Self-utterance expiration in milliseconds (ignore matches within this window)
const SELF_UTTERANCE_EXPIRY_MS = 10000

// Wake-word definitions across supported languages (longest first)
const WAKE_WORDS_ENGLISH = [
  'hello jarvis',
  'okay jarvis',
  'hey jarvis',
  'ok jarvis',
  'hi jarvis',
  'jarvis',
  'javascript',
  'hello javascript',
  'hey javascript',
  'java',
  'hey java',
]

const WAKE_WORDS_DEVANAGARI = [
  'नमस्कार जार्विस',
  'नमस्ते जार्विस',
  'जार्विस सुनो',
  'हे जार्विस',
  'ऐक जार्विस',
  'जार्विस',
]

interface SpokenRecord {
  text: string
  normalized: string
  timestamp: number
}

class JarvisVoiceController {
  private state: VoiceState = 'idle'
  private recognition: any = null
  private speechSupported: boolean = false
  private audioStream: MediaStream | null = null
  private audioContext: AudioContext | null = null
  private analyser: AnalyserNode | null = null
  private vadInterval: number | null = null
  private cooldownTimer: any = null
  private mediaRecorder: MediaRecorder | null = null
  private audioChunks: Blob[] = []

  // Anti-Self-Echo Ring Buffer
  private recentSpoken: SpokenRecord[] = []

  // VAD dynamic energy tracking
  private noiseFloor: number = 0.015
  private consecutiveVoiceFrames: number = 0
  private consecutiveSilenceFrames: number = 0

  // Turn management
  private currentTurnHandled: boolean = false
  private wakeWordMode: boolean = true
  private activeCommandTimer: any = null

  constructor() {
    if (typeof window !== 'undefined') {
      this.initRecognition()
    }
  }

  /** Normalizes a string for robust phonetic & echo matching. */
  private normalizeForMatch(str: string): string {
    return (str || '')
      .toLowerCase()
      .replace(/[.,\/#!$%\^&\*;:{}=\-_`~()?"'।॥]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim()
  }

  /** Records text spoken by JARVIS to prevent acoustic feedback / self-hearing. */
  public recordSpokenText(text: string) {
    if (!text || !text.trim()) return
    const now = Date.now()
    const normalized = this.normalizeForMatch(text)
    this.recentSpoken.push({ text: text.trim(), normalized, timestamp: now })

    // Purge records older than expiry window
    this.recentSpoken = this.recentSpoken.filter(
      (r) => now - r.timestamp < SELF_UTTERANCE_EXPIRY_MS
    )
  }

  /**
   * Checks whether a candidate transcript is an acoustic echo of JARVIS's own TTS output.
   * Uses both substring containment and token set overlap.
   */
  public isAcousticEcho(candidate: string): boolean {
    if (!candidate || !candidate.trim()) return true
    const norm = this.normalizeForMatch(candidate)
    if (!norm) return true
    const now = Date.now()

    // Clean up stale records
    this.recentSpoken = this.recentSpoken.filter(
      (r) => now - r.timestamp < SELF_UTTERANCE_EXPIRY_MS
    )

    const candidateTokens = new Set(norm.split(' ').filter((w) => w.length > 2))

    for (const record of this.recentSpoken) {
      // 1. Direct or substring containment
      if (record.normalized.includes(norm) || (norm.length > 10 && norm.includes(record.normalized))) {
        console.warn(`[AntiEcho] Suppressed direct self-speech echo: "${candidate}"`)
        return true
      }

      // 2. Token overlap similarity
      if (candidateTokens.size > 0) {
        const recordTokens = new Set(record.normalized.split(' ').filter((w) => w.length > 2))
        let matches = 0
        candidateTokens.forEach((token) => {
          if (recordTokens.has(token)) matches++
        })
        const overlapRatio = matches / candidateTokens.size
        if (overlapRatio >= 0.5) {
          console.warn(
            `[AntiEcho] Suppressed token overlap echo (${Math.round(overlapRatio * 100)}%): "${candidate}"`
          )
          return true
        }
      }
    }

    return false
  }

  /**
   * Parses wake word and extracts command payload.
   * Returns: { hasWakeWord: boolean, command: string, isWakeWordOnly: boolean }
   */
  public parseWakeWord(transcript: string): {
    hasWakeWord: boolean
    command: string
    isWakeWordOnly: boolean
  } {
    const raw = transcript.trim()
    const lower = raw.toLowerCase()

    // 1. Check English wake words (Exact & Prefix matches first)
    for (const ww of WAKE_WORDS_ENGLISH) {
      if (lower === ww) {
        return { hasWakeWord: true, command: '', isWakeWordOnly: true }
      }
      if (lower.startsWith(ww + ' ') || lower.startsWith(ww + ',') || lower.startsWith(ww + ':')) {
        const cmd = raw.slice(ww.length).replace(/^[\s,:]+/, '').trim()
        return { hasWakeWord: true, command: cmd, isWakeWordOnly: !cmd }
      }
    }
    for (const ww of WAKE_WORDS_ENGLISH) {
      const idx = lower.indexOf(ww)
      if (idx !== -1 && idx < 15) {
        const cmd = (raw.slice(0, idx) + ' ' + raw.slice(idx + ww.length)).replace(/\s+/g, ' ').trim()
        return { hasWakeWord: true, command: cmd, isWakeWordOnly: !cmd }
      }
    }

    // 2. Check Devanagari (Hindi / Marathi) wake words (Exact & Prefix matches first)
    for (const ww of WAKE_WORDS_DEVANAGARI) {
      if (raw === ww) {
        return { hasWakeWord: true, command: '', isWakeWordOnly: true }
      }
      if (raw.startsWith(ww + ' ') || raw.startsWith(ww + ',') || raw.startsWith(ww + '।')) {
        const cmd = raw.slice(ww.length).replace(/^[\s,।]+/, '').trim()
        return { hasWakeWord: true, command: cmd, isWakeWordOnly: !cmd }
      }
    }
    for (const ww of WAKE_WORDS_DEVANAGARI) {
      const idx = raw.indexOf(ww)
      if (idx !== -1 && idx < 20) {
        const cmd = (raw.slice(0, idx) + ' ' + raw.slice(idx + ww.length)).replace(/\s+/g, ' ').trim()
        return { hasWakeWord: true, command: cmd, isWakeWordOnly: !cmd }
      }
    }

    return { hasWakeWord: false, command: raw, isWakeWordOnly: false }
  }

  /** Initialize Web Speech API instance with clean event handlers. */
  private initRecognition() {
    const win = window as any
    const SpeechClass = win.SpeechRecognition || win.webkitSpeechRecognition

    if (!SpeechClass) {
      this.speechSupported = false
      console.warn('[VoiceController] Web Speech API not supported in this browser.')
      return
    }

    this.speechSupported = true
    const rec = new SpeechClass()
    rec.continuous = true
    rec.interimResults = true
    rec.maxAlternatives = 1

    rec.onstart = () => {
      // Speech recognition is running
    }

    rec.onresult = (event: any) => {
      // STRICT HARD MUTE: Ignore completely if JARVIS is speaking or cooling down
      if (this.state === 'speaking' || this.state === 'cooldown' || this.state === 'processing') {
        return
      }

      let interim = ''
      let final = ''

      for (let i = event.resultIndex; i < event.results.length; ++i) {
        const res = event.results[i]
        if (res.isFinal) {
          final += res[0].transcript
        } else {
          interim += res[0].transcript
        }
      }

      const activeText = (final || interim).trim()
      if (!activeText) return

      // Update transcript in store for live feedback
      useJarvisStore.getState().setCurrentTranscript(activeText)

      if (final && final.trim()) {
        this.handleFinalTranscript(final.trim())
      }
    }

    rec.onerror = (event: any) => {
      if (event.error === 'no-speech') {
        // Normal silence timeout
        return
      }
      if (event.error === 'aborted') {
        // Intentionally aborted during speech/cooldown
        return
      }
      console.warn('[VoiceController] SpeechRecognition error:', event.error)
      if (event.error === 'not-allowed') {
        useJarvisStore
          .getState()
          .setSystemNotice('Microphone blocked: Please allow mic access in your browser address bar.')
        setTimeout(() => useJarvisStore.getState().setSystemNotice(null), 5000)
        this.stop()
      }
    }

    rec.onend = () => {
      // Safely auto-restart ONLY if we are supposed to be listening and NOT speaking or in cooldown
      if (
        (this.state === 'listening_wakeword' || this.state === 'listening_command') &&
        useJarvisStore.getState().isListening
      ) {
        try {
          rec.start()
        } catch {
          // Ignore restart collisions
        }
      }
    }

    this.recognition = rec
  }

  /** Handles final transcript received from Web Speech API or Whisper. */
  private handleFinalTranscript(transcript: string) {
    if (this.currentTurnHandled) return
    if (this.state === 'speaking' || this.state === 'cooldown' || this.state === 'processing') {
      return
    }

    // Anti-Self-Echo Check: Verify this is not JARVIS's own voice
    if (this.isAcousticEcho(transcript)) {
      useJarvisStore.getState().setCurrentTranscript('')
      return
    }

    const lowerTranscript = transcript.toLowerCase()
    const isPriorityCommand =
      lowerTranscript.includes('acknowledge') ||
      lowerTranscript.includes('standing pollution') ||
      lowerTranscript.includes('standing position') ||
      lowerTranscript.includes('standing protocol') ||
      lowerTranscript.includes('standing by') ||
      lowerTranscript.includes('are you there') ||
      lowerTranscript.includes('are you listening') ||
      lowerTranscript.includes('java is not properly answering') ||
      lowerTranscript.includes('system check') ||
      lowerTranscript.includes('status check')

    if (isPriorityCommand) {
      playHudChirp()
      this.dispatchCommand(transcript)
      return
    }

    const { hasWakeWord, command, isWakeWordOnly } = this.parseWakeWord(transcript)

    // Handle Wake-Word Standby vs Direct Command
    if (this.state === 'listening_wakeword') {
      if (!hasWakeWord) {
        // Ambient speech without wake word; ignore
        return
      }

      if (isWakeWordOnly) {
        // User said "Jarvis" / "Hey Jarvis" alone
        playHudChirp()
        this.currentTurnHandled = true
        useJarvisStore.getState().setCurrentTranscript('')
        useJarvisStore.getState().setSystemNotice('Jarvis: "Yes, sir? Standing by."')
        setTimeout(() => useJarvisStore.getState().setSystemNotice(null), 2500)

        // Elevate state to command listening
        this.state = 'listening_command'
        useJarvisStore.getState().setVoiceStatus(this.state)
        this.currentTurnHandled = false

        // Timeout back to wake word if no command follows within 10s
        if (this.activeCommandTimer) clearTimeout(this.activeCommandTimer)
        this.activeCommandTimer = setTimeout(() => {
          if (this.state === 'listening_command') {
            this.state = 'listening_wakeword'
            useJarvisStore.getState().setVoiceStatus(this.state)
          }
        }, 10000)
        return
      }

      // Wake word with command attached (e.g. "Jarvis, open YouTube")
      this.dispatchCommand(command || transcript)
      return
    }

    // Direct listening mode (command mode / push-to-talk)
    const effectiveCommand = command || transcript
    this.dispatchCommand(effectiveCommand)
  }

  /** Dispatches valid user command to store executor with single-turn locking. */
  private dispatchCommand(commandText: string) {
    const text = (commandText || '').trim()
    if (!text) return
    if (this.currentTurnHandled) return

    this.currentTurnHandled = true
    if (this.activeCommandTimer) {
      clearTimeout(this.activeCommandTimer)
      this.activeCommandTimer = null
    }

    // Clear transcript preview
    useJarvisStore.getState().setCurrentTranscript('')

    // Auto-detect and sync language
    const currentLang = useJarvisStore.getState().speechLanguage
    const detected = normalizeSpeechLang(guessTextLanguage(text))
    if (currentLang === 'auto' && detected) {
      useJarvisStore.getState().setDetectedLanguage(detected)
      if (this.recognition) {
        this.recognition.lang = detected
      }
    }

    // Pause recognition immediately while command processes
    this.state = 'processing'
    this.stopRecognition()
    this.stopMediaRecorder()

    useJarvisStore.getState().executeCommand(text)
  }

  /**
   * Initializes WebRTC AudioStream with Hardware Echo Cancellation and AnalyserNode.
   */
  public async initAudioHardware(): Promise<boolean> {
    if (this.audioStream && this.audioStream.active) return true

    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        console.warn('[VoiceController] getUserMedia not available.')
        return false
      }

      // WebRTC Hardware Acoustic Echo Cancellation & Noise Filtering
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: { ideal: true },
          noiseSuppression: { ideal: true },
          autoGainControl: { ideal: true },
          channelCount: 1,
          sampleRate: { ideal: 16000 },
        },
      })

      this.audioStream = stream

      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext
      if (AudioContextClass) {
        const ctx = new AudioContextClass()
        if (ctx.state === 'suspended') {
          await ctx.resume().catch(() => {})
        }
        const source = ctx.createMediaStreamSource(stream)
        const analyser = ctx.createAnalyser()
        analyser.fftSize = 256
        analyser.smoothingTimeConstant = 0.4
        source.connect(analyser)

        this.audioContext = ctx
        this.analyser = analyser

        this.startVadLoop()
      }

      return true
    } catch (err) {
      console.warn('[VoiceController] Error accessing microphone hardware:', err)
      return false
    }
  }

  /** Starts real-time VAD (Voice Activity Detection) loop. */
  private startVadLoop() {
    if (this.vadInterval) return

    const bufferLength = this.analyser ? this.analyser.frequencyBinCount : 0
    const dataArray = new Uint8Array(bufferLength)

    const checkVad = () => {
      // Stop loop if analyser is gone
      if (!this.analyser || !this.audioStream?.active) {
        this.vadInterval = null
        return
      }

      // Hard mute during speech, cooldown, or processing
      if (this.state === 'speaking' || this.state === 'cooldown' || this.state === 'processing') {
        useJarvisStore.getState().setAudioLevel?.(0)
        useJarvisStore.getState().setIsVoiceActive?.(false)
        this.vadInterval = requestAnimationFrame(checkVad)
        return
      }

      this.analyser.getByteFrequencyData(dataArray)

      // Calculate instantaneous RMS / Energy
      let sum = 0
      for (let i = 0; i < bufferLength; i++) {
        sum += dataArray[i] * dataArray[i]
      }
      const rms = Math.sqrt(sum / bufferLength) / 255.0

      // Slowly adapt noise floor during silence
      if (rms < this.noiseFloor) {
        this.noiseFloor = this.noiseFloor * 0.95 + rms * 0.05
      } else {
        this.noiseFloor = this.noiseFloor * 0.999 + rms * 0.001
      }
      this.noiseFloor = Math.max(0.01, Math.min(this.noiseFloor, 0.15))

      const speechThreshold = this.noiseFloor * 2.0 + 0.035
      const isSpeechFrame = rms > speechThreshold

      if (isSpeechFrame) {
        this.consecutiveVoiceFrames++
        this.consecutiveSilenceFrames = 0
      } else {
        this.consecutiveSilenceFrames++
        if (this.consecutiveSilenceFrames > 8) {
          this.consecutiveVoiceFrames = 0
        }
      }

      // Voice is considered active if sound energy sustained for at least 3 frames (~50ms)
      const voiceActive = this.consecutiveVoiceFrames >= 3

      // Expose to store for UI animations
      useJarvisStore.getState().setAudioLevel?.(Math.min(1.0, rms * 3.5))
      useJarvisStore.getState().setIsVoiceActive?.(voiceActive)

      this.vadInterval = requestAnimationFrame(checkVad)
    }

    this.vadInterval = requestAnimationFrame(checkVad)
  }

  /** Start MediaRecorder for Whisper fallback audio capture. */
  private startMediaRecorder() {
    if (!this.audioStream || !this.audioStream.active) return
    try {
      this.audioChunks = []
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm'

      const recorder = new MediaRecorder(this.audioStream, { mimeType })
      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          this.audioChunks.push(e.data)
        }
      }

      recorder.onstop = async () => {
        if (this.audioChunks.length > 0 && !this.currentTurnHandled) {
          const blob = new Blob(this.audioChunks, { type: mimeType })
          if (blob.size > 2000) {
            this.sendToNeuralWhisper(blob)
          }
        }
      }

      recorder.start(300)
      this.mediaRecorder = recorder
    } catch (e) {
      console.warn('[VoiceController] MediaRecorder error:', e)
    }
  }

  private stopMediaRecorder() {
    if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
      try {
        this.mediaRecorder.stop()
      } catch {
        // Ignored
      }
    }
    this.mediaRecorder = null
  }

  /** Sends recorded audio blob to Groq Whisper Large v3 endpoint. */
  private async sendToNeuralWhisper(blob: Blob) {
    if (this.currentTurnHandled) return
    if (this.state === 'speaking' || this.state === 'cooldown' || this.state === 'processing') {
      return
    }

    try {
      const formData = new FormData()
      formData.append('file', blob, 'speech.webm')

      const res = await fetch('/api/voice/transcribe', {
        method: 'POST',
        body: formData,
      })

      if (res.ok) {
        const data = await res.json()
        if (data?.text?.trim() && !this.currentTurnHandled) {
          const confidence = data.confidence || 0.5
          const codeSwitching = data.code_switching || false
          
          console.log(
            `[VoiceController] Neural Whisper transcribed: "${data.text.trim()}" ` +
            `(confidence: ${(confidence * 100).toFixed(1)}%, code-switching: ${codeSwitching})`
          )
          
          // Low confidence warning
          if (confidence < 0.4) {
            console.warn('[VoiceController] Low confidence transcription, may be inaccurate')
          }
          
          this.handleFinalTranscript(data.text.trim())
        }
      }
    } catch (err) {
      console.warn('[VoiceController] Whisper transcription failed:', err)
    }
  }

  /** Strictly stop Web Speech API recognition. */
  private stopRecognition() {
    if (this.recognition) {
      try {
        this.recognition.abort()
      } catch {
        // Ignored
      }
    }
  }

  /** Strictly start Web Speech API recognition. */
  private startRecognition() {
    if (!this.recognition) {
      this.initRecognition()
    }
    if (this.recognition) {
      const lang = useJarvisStore.getState().speechLanguage
      const detected = useJarvisStore.getState().detectedLanguage
      this.recognition.lang = lang && lang !== 'auto' ? lang : detected || 'en-IN'

      try {
        this.recognition.start()
      } catch {
        // Already started or busy
      }
    }
  }

  /**
   * CRITICAL LIFECYCLE METHOD 1: Pause microphone input during JARVIS speech.
   * Called immediately when JARVIS begins speaking.
   */
  public pauseForSpeech() {
    this.state = 'speaking'
    if (this.cooldownTimer) {
      clearTimeout(this.cooldownTimer)
      this.cooldownTimer = null
    }

    // Stop recognition engine immediately
    this.stopRecognition()
    this.stopMediaRecorder()

    // Clear any interim transcript
    useJarvisStore.getState().setCurrentTranscript('')
    useJarvisStore.getState().setAudioLevel?.(0)
    useJarvisStore.getState().setIsVoiceActive?.(false)
  }

  /**
   * CRITICAL LIFECYCLE METHOD 2: Safely return to listening after TTS finishes.
   * Enforces acoustic reverb cooldown before re-arming the microphone.
   */
  public resumeAfterSpeech() {
    this.state = 'cooldown'
    useJarvisStore.getState().setVoiceStatus(this.state)

    if (this.cooldownTimer) {
      clearTimeout(this.cooldownTimer)
    }

    this.cooldownTimer = setTimeout(() => {
      this.cooldownTimer = null
      this.currentTurnHandled = false

      const isListening = useJarvisStore.getState().isListening

      if (isListening) {
        // Resume listening in appropriate mode
        this.state = this.wakeWordMode ? 'listening_wakeword' : 'listening_command'
        useJarvisStore.getState().setVoiceStatus(this.state)
        this.startRecognition()
      } else {
        this.state = 'idle'
        useJarvisStore.getState().setVoiceStatus('idle')
      }
    }, ACOUSTIC_COOLDOWN_MS)
  }

  /**
   * Toggles listening mode on/off (user clicked the mic button).
   */
  public async toggleListening(): Promise<boolean> {
    playHudChirp()
    const currentlyListening = useJarvisStore.getState().isListening

    if (currentlyListening) {
      // User is turning mic OFF
      this.stop()
      return false
    } else {
      // User is turning mic ON
      const microphoneReady = await this.initAudioHardware()
      if (!microphoneReady) {
        this.state = 'idle'
        useJarvisStore.getState().setIsListening(false)
        useJarvisStore.getState().setVoiceStatus('error')
        useJarvisStore.getState().setSystemNotice('Microphone unavailable. Check your browser microphone permission.')
        setTimeout(() => useJarvisStore.getState().setSystemNotice(null), 5000)
        return false
      }

      this.currentTurnHandled = false
      this.state = 'listening_command' // Direct push-to-talk listening
      useJarvisStore.getState().setIsListening(true)
      useJarvisStore.getState().setVoiceStatus(this.state)
      useJarvisStore.getState().setSystemNotice('Microphone online. Listening for voice instruction...')
      setTimeout(() => useJarvisStore.getState().setSystemNotice(null), 3000)

      this.startRecognition()
      this.startMediaRecorder()
      return true
    }
  }

  /** Stops voice controller and releases hardware resources safely. */
  public stop() {
    this.state = 'idle'
    if (this.cooldownTimer) {
      clearTimeout(this.cooldownTimer)
      this.cooldownTimer = null
    }
    if (this.activeCommandTimer) {
      clearTimeout(this.activeCommandTimer)
      this.activeCommandTimer = null
    }

    if (this.audioContext && this.audioContext.state !== 'closed') {
      try {
        this.audioContext.suspend().catch(() => {})
      } catch {
        // Ignored
      }
    }

    this.stopRecognition()
    this.stopMediaRecorder()

    useJarvisStore.getState().setIsListening(false)
    useJarvisStore.getState().setVoiceStatus('idle')
    useJarvisStore.getState().setCurrentTranscript('')
    useJarvisStore.getState().setAudioLevel?.(0)
    useJarvisStore.getState().setIsVoiceActive?.(false)
  }

  /** Set wake-word mode preference (true = standby for "Hey Jarvis", false = push to talk). */
  public setWakeWordMode(enabled: boolean) {
    this.wakeWordMode = enabled
    if (useJarvisStore.getState().isListening && this.state !== 'speaking' && this.state !== 'cooldown') {
      this.state = enabled ? 'listening_wakeword' : 'listening_command'
      useJarvisStore.getState().setVoiceStatus(this.state)
    }
  }

  /** Update speech recognition language on the fly. */
  public updateLanguage(lang: string) {
    if (this.recognition) {
      try {
        this.recognition.lang = lang
      } catch {
        // Ignored
      }
    }
  }

  public getState(): VoiceState {
    return this.state
  }

  public isSpeechSupported(): boolean {
    return this.speechSupported
  }
}

// Global singleton instance
export const voiceController = new JarvisVoiceController()
