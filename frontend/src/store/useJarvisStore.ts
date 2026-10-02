import { create } from 'zustand'
import type { OrbState } from 'thinking-orbs'
import { voiceController } from '../services/voiceController'

// Tracks the object currently selected in the CAD viewport so chat/voice
// commands can be scoped to it server-side.
let cadSelectedFeatureId: string | null = null

export const ORB_STATES: OrbState[] = [
  'working',
  'searching',
  'solving',
  'listening',
  'connecting',
  'weaving',
  'composing',
  'breathing',
  'shaping',
]

export type PanelPosition = 'center' | 'docked-tr' | 'docked-tl' | 'docked-br' | 'minimized' | 'closed'
export type PanelContentType = 'youtube' | 'search' | 'web'

export interface PanelContent {
  type: PanelContentType
  title: string
  url?: string
  videoId?: string
  query?: string
  /** When true the embedded player starts unmuted (voice-initiated playback). */
  autoplaySound?: boolean
}

export type SpeechLang = 'en-IN' | 'hi-IN' | 'mr-IN'

const MR_MARKERS = [
  'आहे', 'आहेत', 'करा', 'नाही', 'नको', 'काय', 'तुम्ही', 'आपण', 'झाले',
  'कसा', 'कशी', 'मला', 'पाहिजे', 'धन्यवाद', 'नमस्कार', 'साठी', 'करायचं',
]

/** Heuristic English / Hindi / Marathi guess for a transcript or reply. */
export function guessTextLanguage(text: string): SpeechLang {
  const clean = (text || '').trim()
  if (!/[\u0900-\u097F]/.test(clean)) return 'en-IN'
  return MR_MARKERS.some((m) => clean.includes(m)) ? 'mr-IN' : 'hi-IN'
}

/** Normalizes Whisper language names ("hindi") and ISO codes ("hi") to a recognition lang. */
export function normalizeSpeechLang(raw?: string | null): SpeechLang | null {
  if (!raw) return null
  const v = raw.toLowerCase().trim()
  if (v.includes('hindi') || v.startsWith('hi')) return 'hi-IN'
  if (v.includes('marathi') || v.startsWith('mr')) return 'mr-IN'
  if (v.includes('english') || v.startsWith('en')) return 'en-IN'
  return null
}

export const SPEECH_LANG_LABELS: Record<string, string> = {
  auto: '🤖 AUTO Detect',
  'en-IN': '🌐 EN-IN / Hinglish',
  'mr-IN': '🇮🇳 मराठी',
  'hi-IN': '🇮🇳 हिंदी',
  'en-US': '🇺🇸 EN-US',
}

export interface ChatAttachment {
  filename: string
  path: string
  url?: string
  mime_type?: string
  size?: number
  category?: string
}

export interface ChatMessage {
  id: string
  sender: 'user' | 'jarvis'
  text: string
  timestamp: string
  attachments?: ChatAttachment[]
}

export interface TelemetryData {
  status: string
  cpu_percent: number
  ram_percent: number
  ram_used_gb: number
  ram_total_gb: number
  disk_percent: number
  disk_free_gb: number
  battery?: {
    percent: number
    power_plugged: boolean
    secsleft?: number | null
  } | null
  active_processes: number
  timestamp: string
}

export interface SafetyAction {
  action: string
  prompt: string
}

export interface TaskItem {
  id: number
  title: string
  description?: string
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled'
  priority: 'low' | 'medium' | 'high'
  due_date?: string
  created_at: string
}

export interface MemoryItem {
  id: number
  category: string
  title: string
  content: string
  importance: number
  created_at: string
}

export interface BiometricsState {
  userId: string
  displayName: string
  role: 'owner' | 'guest' | 'authorized'
  isOwner: boolean
  faceMatched: boolean
  faceConfidence: number
  voiceMatched: boolean
  voiceConfidence: number
  cameraActive: boolean
  micActive: boolean
  consentGiven: boolean
  hasEnrolledFace: boolean
  hasEnrolledVoice: boolean
  enrolledProfiles: number
  permissions: string[]
}

interface JarvisStore {
  // Orb State
  orbState: OrbState
  setOrbState: (state: OrbState) => void

  // Voice & Interaction State
  isListening: boolean
  setIsListening: (listening: boolean) => void
  voiceStatus: 'idle' | 'listening' | 'listening_wakeword' | 'listening_command' | 'processing' | 'executing' | 'speaking' | 'cooldown' | 'error'
  setVoiceStatus: (status: 'idle' | 'listening' | 'listening_wakeword' | 'listening_command' | 'processing' | 'executing' | 'speaking' | 'cooldown' | 'error') => void
  executionOutcome: 'success' | 'error' | null
  setExecutionOutcome: (outcome: 'success' | 'error' | null, message?: string) => void
  currentTranscript: string
  setCurrentTranscript: (transcript: string) => void
  speechLanguage: string
  setSpeechLanguage: (lang: string) => void
  detectedLanguage: SpeechLang
  setDetectedLanguage: (lang: SpeechLang) => void
  audioLevel: number
  setAudioLevel: (level: number) => void
  isVoiceActive: boolean
  setIsVoiceActive: (active: boolean) => void
  wakeWordEnabled: boolean
  setWakeWordEnabled: (enabled: boolean) => void
  toggleListening: () => Promise<void>

  // System Notification Toast
  systemNotice: string | null
  setSystemNotice: (notice: string | null) => void

  // Safety Confirmation Gate
  pendingSafetyConfirmation: SafetyAction | null
  setPendingSafetyConfirmation: (val: SafetyAction | null) => void
  confirmSafetyAction: (decision: 'confirm' | 'cancel') => Promise<void>

  // System Connection Health
  backendStatus: 'connected' | 'connecting' | 'disconnected'
  setBackendStatus: (status: 'connected' | 'connecting' | 'disconnected') => void

  // Real-time System Telemetry
  telemetry: TelemetryData | null
  fetchTelemetry: () => Promise<void>

  // Persistent Storage & Tasks State
  tasks: TaskItem[]
  memories: MemoryItem[]
  autostartEnabled: boolean
  backupsAvailable: number
  lastSessionInfo: Record<string, unknown> | null
  fetchPersistentState: () => Promise<void>
  toggleAutostart: (enable?: boolean) => Promise<void>
  createTask: (title: string, priority?: string) => Promise<void>
  toggleTaskStatus: (taskId: number, currentStatus: string) => Promise<void>
  deleteTask: (taskId: number) => Promise<void>
  createBackupSnapshot: () => Promise<void>

  // Biometric Security & Identity State
  biometrics: BiometricsState
  biometricsModalOpen: boolean
  setBiometricsModalOpen: (open: boolean) => void
  fetchBiometricsStatus: () => Promise<void>
  setBiometricConsent: (consent: boolean) => Promise<void>
  verifyFaceFrame: (base64Image: string) => Promise<any>
  enrollFaceFrame: (base64Image: string, displayName?: string) => Promise<any>
  enrollVoiceAudio: (audioBase64: string, displayName?: string) => Promise<any>
  purgeBiometrics: () => Promise<void>
  toggleCameraActive: (enable?: boolean) => Promise<void>
  switchUserRole: (role: 'owner' | 'guest', displayName?: string) => Promise<void>

  // Panel State
  panelOpen: boolean
  panelPosition: PanelPosition
  panelContent: PanelContent
  openPanel: (content: PanelContent, position?: PanelPosition) => void
  closePanel: () => void
  setPanelPosition: (pos: PanelPosition) => void
  togglePanelZoom: () => void

  // Conversation & Logs
  messages: ChatMessage[]
  addMessage: (sender: 'user' | 'jarvis', text: string, attachments?: ChatAttachment[]) => void

  // Autonomous AI Coding Assistant & Workbench
  isCodingMode: boolean
  toggleCodingMode: (enable?: boolean) => void

  // High level command executor
  executeCommand: (command: string, attachments?: ChatAttachment[]) => void
}

// Persistent Web Audio Context for zero-delay, autoplay-immune playback
let audioCtx: AudioContext | null = null
let activeSourceNode: AudioBufferSourceNode | null = null

export function getAudioContext(): AudioContext {
  if (!audioCtx && typeof window !== 'undefined') {
    const AudioCtxClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
    if (AudioCtxClass) {
      audioCtx = new AudioCtxClass()
    }
  }
  if (audioCtx && audioCtx.state === 'suspended') {
    audioCtx.resume().catch(() => {})
  }
  return audioCtx as AudioContext
}

// Immediate subtle HUD acoustic confirmation chime (880Hz -> 1320Hz)
export function playHudChirp() {
  try {
    const ctx = getAudioContext()
    if (!ctx) return
    const now = ctx.currentTime
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()

    osc.type = 'sine'
    osc.frequency.setValueAtTime(880, now)
    osc.frequency.exponentialRampToValueAtTime(1320, now + 0.06)

    gain.gain.setValueAtTime(0.06, now)
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.06)

    osc.connect(gain)
    gain.connect(ctx.destination)

    osc.start(now)
    osc.stop(now + 0.06)
  } catch (e) {
    // Ignore
  }
}

// Auto-unlock audio hardware on first user interaction anywhere on the document
if (typeof window !== 'undefined') {
  // Prime the browser voice list so the first Hindi/Marathi reply can pick a voice
  if ('speechSynthesis' in window) {
    window.speechSynthesis.getVoices()
    window.speechSynthesis.addEventListener?.('voiceschanged', () => {
      window.speechSynthesis.getVoices()
    })
  }
  const unlockAudio = () => {
    getAudioContext()
    window.removeEventListener('click', unlockAudio)
    window.removeEventListener('keydown', unlockAudio)
    window.removeEventListener('touchstart', unlockAudio)
  }
  window.addEventListener('click', unlockAudio, { once: true })
  window.addEventListener('keydown', unlockAudio, { once: true })
  window.addEventListener('touchstart', unlockAudio, { once: true })
}

// Last-resort fallback only: the cloned JARVIS voice (backend /api/tts) speaks
// every reply - English, Hindi and Marathi alike. If synthesis is unavailable,
// this keeps the same deep, male JARVIS-like speaker instead of silently
// switching to a female or system default voice.
const MALE_VOICE_HINTS = [
  'male', 'david', 'mark', 'andrew', 'brian', 'ryan', 'thomas', 'james',
  'richard', 'oliver', 'george', 'guy', 'fred', 'daniel', 'gordon', 'alex',
  'ravi', 'neeraj', 'madhur', 'prabhat', 'manohar', 'hemant', 'prashant',
  'anirudh', 'ashok', 'vikram', 'rajesh', 'suresh', 'anand', 'girish',
  'rishi', 'aarav', 'aditya', 'rahul', 'yash', 'amit', 'hari', 'deepak',
]

const FEMALE_VOICE_HINTS = [
  'female', 'zira', 'jenny', 'aria', 'emma', 'susan', 'helen', 'michelle',
  'sonia', 'heera', 'swara', 'kalpana', 'aditi', 'neerja', 'veena', 'sapna',
  'shruti', 'kalpana',
]

function voiceSpeakerScore(voice: SpeechSynthesisVoice): number {
  const name = voice.name.toLowerCase()
  let score = 0
  if (FEMALE_VOICE_HINTS.some((hint) => name.includes(hint))) score -= 3
  if (MALE_VOICE_HINTS.some((hint) => name.includes(hint))) score += 3
  if (voice.lang.toUpperCase().endsWith('-IN')) score += 1
  if (voice.lang.toLowerCase().startsWith('en-gb')) score += 1
  return score
}

function pickBrowserVoice(text: string): SpeechSynthesisVoice | undefined {
  const voices = window.speechSynthesis.getVoices()
  if (!voices.length) return undefined

  const lang = guessTextLanguage(text)
  const prefix = lang.slice(0, 2)
  const rank = (list: SpeechSynthesisVoice[]) =>
    list.slice().sort((a, b) => voiceSpeakerScore(b) - voiceSpeakerScore(a))

  const languageVoices = rank(
    voices.filter((v) => v.lang.toLowerCase().replace('_', '-').startsWith(prefix))
  )
  if (languageVoices.length) {
    // Prefer a male speaker of the reply's language; only then any speaker of
    // that language (still deepened in speakViaBrowser).
    return languageVoices.find((v) => voiceSpeakerScore(v) > 0) || languageVoices[0]
  }

  const englishVoices = rank(voices.filter((v) => v.lang.toLowerCase().startsWith('en')))
  return englishVoices.find((v) => voiceSpeakerScore(v) > 0) || englishVoices[0]
}

function speakViaBrowser(text: string, onDone: () => void) {
  if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
    setTimeout(onDone, 2500)
    return
  }
  try {
    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = guessTextLanguage(text)
    utterance.rate = 1.0
    utterance.pitch = 0.8
    utterance.onend = onDone
    utterance.onerror = onDone
    const voice = pickBrowserVoice(text)
    if (voice) utterance.voice = voice
    window.speechSynthesis.speak(utterance)
  } catch (e) {
    console.warn('Web Speech fallback failed:', e)
    onDone()
  }
}

export async function speakJarvis(text: string) {
  if (!text || !text.trim()) return

  // 1. Anti-Self-Echo & Pause Microphone Listening
  voiceController.recordSpokenText(text)
  voiceController.pauseForSpeech()

  useJarvisStore.getState().setOrbState('solving')
  useJarvisStore.getState().setVoiceStatus('speaking')

  let hasEnded = false
  const onPlaybackDone = () => {
    if (hasEnded) return
    hasEnded = true
    useJarvisStore.getState().setOrbState('composing')
    // Resume listening safely after acoustic reverb cooldown
    voiceController.resumeAfterSpeech()
  }

  // Single voice identity: every reply - English, Hindi, Marathi, Hinglish -
  // is spoken by the cloned JARVIS voice on the backend (Devanagari is
  // romanised server-side so the same speaker voices all languages).
  // 2. Primary Engine: Pocket-TTS Cloned Voice via Web Audio API (Immune to browser 5s autoplay limits)
  try {
    const ctx = getAudioContext()
    if (ctx && ctx.state === 'suspended') {
      await ctx.resume().catch(() => {})
    }

    if (activeSourceNode) {
      try {
        activeSourceNode.stop()
      } catch {
        // Ignored
      }
      activeSourceNode = null
    }

    const res = await fetch('/api/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: text.trim() }),
    })

    if (res.ok && ctx) {
      const arrayBuffer = await res.arrayBuffer()
      // Web Audio API buffer decoding
      const audioBuffer = await ctx.decodeAudioData(arrayBuffer)

      const source = ctx.createBufferSource()
      source.buffer = audioBuffer
      source.connect(ctx.destination)
      activeSourceNode = source

      source.onended = () => {
        if (activeSourceNode === source) activeSourceNode = null
        onPlaybackDone()
      }

      source.start(0)
      return
    }
  } catch (err) {
    console.warn('Web Audio Pocket-TTS synthesis error, attempting HTML5 audio fallback:', err)
  }

  // 3. Secondary Engine: Standard HTML5 Audio Tag
  try {
    const res = await fetch('/api/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: text.trim() }),
    })

    if (res.ok) {
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const audio = new Audio(url)

      audio.onended = () => {
        URL.revokeObjectURL(url)
        onPlaybackDone()
      }
      audio.onerror = () => {
        onPlaybackDone()
      }

      await audio.play()
      return
    }
  } catch (e2) {
    console.warn('HTML5 Audio fallback failed:', e2)
  }

  // 4. Tertiary Engine: Web Speech API (Local Browser Voice)
  speakViaBrowser(text, onPlaybackDone)
}

/** Finds a resolved YouTube video in a /api/chat system_action payload. */
function findPlayableVideo(
  systemAction: any
): { video_id: string; query?: string; title?: string } | null {
  if (!systemAction) return null
  if (systemAction.video_id) return systemAction
  const actions = Array.isArray(systemAction.executed_actions) ? systemAction.executed_actions : []
  return actions.find((a: any) => a && a.video_id) || null
}

export const useJarvisStore = create<JarvisStore>((set, get) => ({
  // Composing is idle as requested
  orbState: 'composing',
  setOrbState: (orbState) => set({ orbState }),

  isListening: false,
  setIsListening: (isListening) => {
    set({
      isListening,
      voiceStatus: isListening ? 'listening' : 'idle',
      orbState: isListening ? 'listening' : 'composing',
    })
    if (!isListening) {
      voiceController.stop()
    }
  },
  voiceStatus: 'idle',
  setVoiceStatus: (voiceStatus) => set({ voiceStatus }),
  executionOutcome: null,
  setExecutionOutcome: (outcome, message) => {
    set({ executionOutcome: outcome, systemNotice: outcome ? message ?? get().systemNotice : get().systemNotice })
    if (outcome) {
      setTimeout(() => {
        if (get().executionOutcome === outcome) set({ executionOutcome: null })
      }, 4000)
    }
  },
  currentTranscript: '',
  setCurrentTranscript: (currentTranscript) => set({ currentTranscript }),

  speechLanguage: 'auto',
  setSpeechLanguage: (speechLanguage) => {
    set({ speechLanguage })
    voiceController.updateLanguage(speechLanguage)
  },
  detectedLanguage: 'en-IN',
  setDetectedLanguage: (detectedLanguage) => set({ detectedLanguage }),

  audioLevel: 0,
  setAudioLevel: (audioLevel) => set({ audioLevel }),
  isVoiceActive: false,
  setIsVoiceActive: (isVoiceActive) => set({ isVoiceActive }),
  wakeWordEnabled: true,
  setWakeWordEnabled: (wakeWordEnabled) => {
    set({ wakeWordEnabled })
    voiceController.setWakeWordMode(wakeWordEnabled)
  },
  toggleListening: async () => {
    await voiceController.toggleListening()
  },

  systemNotice: null,
  setSystemNotice: (systemNotice) => set({ systemNotice }),

  pendingSafetyConfirmation: null,
  setPendingSafetyConfirmation: (pendingSafetyConfirmation) => set({ pendingSafetyConfirmation }),
  confirmSafetyAction: async (decision: 'confirm' | 'cancel') => {
    try {
      const res = await fetch('/api/system/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision }),
      })
      const data = await res.json()
      set({ pendingSafetyConfirmation: null })
      const reply = data.reply || (decision === 'confirm' ? 'Action confirmed, sir.' : 'Action cancelled, sir.')
      get().addMessage('jarvis', reply)
      speakJarvis(reply)
      get().setSystemNotice(reply)
      setTimeout(() => get().setSystemNotice(null), 4000)
    } catch {
      set({ pendingSafetyConfirmation: null })
    }
  },

  // System Connection Health
  backendStatus: 'connecting',
  setBackendStatus: (status) => set({ backendStatus: status }),

  telemetry: null,
  fetchTelemetry: async () => {
    try {
      const res = await fetch('/api/system/telemetry')
      if (res.ok) {
        const data = await res.json()
        set({ telemetry: data, backendStatus: 'connected' })
      } else if (res.status === 503) {
        set({ backendStatus: 'connecting' })
      }
    } catch {
      // Backend may be warming up
    }
  },

  // Persistent State
  tasks: [],
  memories: [],
  autostartEnabled: false,
  backupsAvailable: 0,
  lastSessionInfo: null,

  fetchPersistentState: async () => {
    let attempts = 0
    const maxAttempts = 6
    while (attempts < maxAttempts) {
      try {
        const res = await fetch('/api/memory/state')
        if (res.status === 503) {
          // Backend is still warming up
          set({ backendStatus: 'connecting' })
          attempts++
          await new Promise((r) => setTimeout(r, 1000))
          continue
        }
        if (res.ok) {
          const data = await res.json()
          const updates: Partial<JarvisStore> = {
            backendStatus: 'connected',
            tasks: data.tasks || [],
            memories: data.memories || [],
            autostartEnabled: !!data.autostart_enabled,
            backupsAvailable: (data.backups || []).length,
            lastSessionInfo: data.last_session || null,
          }

          // Restore conversations seamlessly from persistent storage — but only
          // rehydrate a cold transcript; never wipe the live session history.
          if (Array.isArray(data.recent_conversations) && data.recent_conversations.length > 0 && get().messages.length <= 2) {
            const restoredMessages: ChatMessage[] = data.recent_conversations.map((item: any) => ({
              id: `msg-${item.id || Math.random()}`,
              sender: item.role === 'user' ? 'user' : 'jarvis',
              text: item.content,
              timestamp: item.timestamp
                ? new Date(item.timestamp).toLocaleTimeString([], { hour12: false })
                : new Date().toLocaleTimeString([], { hour12: false }),
            }))
            updates.messages = restoredMessages
          }

          set(updates as any)
          return
        }
      } catch (err) {
        attempts++
        set({ backendStatus: 'connecting' })
        if (attempts < maxAttempts) {
          await new Promise((r) => setTimeout(r, 1000))
          continue
        }
        console.warn('Failed to load persistent memory state:', err)
        set({ backendStatus: 'disconnected' })
      }
    }
  },

  toggleAutostart: async (enable?: boolean) => {
    try {
      const target = enable !== undefined ? enable : !get().autostartEnabled
      const res = await fetch('/api/system/autostart', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: target }),
      })
      if (res.ok) {
        const data = await res.json()
        const isEnabled = !!data.autostart_enabled
        set({ autostartEnabled: isEnabled })
        get().setSystemNotice(isEnabled ? '🛡️ Windows Auto-Start Enabled' : 'Windows Auto-Start Disabled')
        setTimeout(() => get().setSystemNotice(null), 3500)
      }
    } catch (err) {
      console.warn('Failed to toggle autostart:', err)
    }
  },

  createTask: async (title: string, priority: string = 'medium') => {
    try {
      const res = await fetch('/api/memory/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, priority }),
      })
      if (res.ok) {
        const newTask = await res.json()
        set((state) => ({ tasks: [newTask, ...state.tasks] }))
        get().setSystemNotice(`✓ Task recorded: ${title}`)
        setTimeout(() => get().setSystemNotice(null), 3000)
      }
    } catch (err) {
      console.warn('Failed to create task:', err)
    }
  },

  toggleTaskStatus: async (taskId: number, currentStatus: string) => {
    try {
      const newStatus = currentStatus === 'completed' ? 'pending' : 'completed'
      const res = await fetch(`/api/memory/tasks/${taskId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      })
      if (res.ok) {
        set((state) => ({
          tasks: state.tasks.map((t) => (t.id === taskId ? { ...t, status: newStatus as any } : t)),
        }))
      }
    } catch (err) {
      console.warn('Failed to toggle task status:', err)
    }
  },

  deleteTask: async (taskId: number) => {
    try {
      const res = await fetch(`/api/memory/tasks/${taskId}`, {
        method: 'DELETE',
      })
      if (res.ok) {
        set((state) => ({
          tasks: state.tasks.filter((t) => t.id !== taskId),
        }))
        get().setSystemNotice('Task removed')
        setTimeout(() => get().setSystemNotice(null), 2500)
      }
    } catch (err) {
      console.warn('Failed to delete task:', err)
    }
  },

  createBackupSnapshot: async () => {
    try {
      const res = await fetch('/api/memory/backup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description: 'Manual user backup snapshot' }),
      })
      if (res.ok) {
        const data = await res.json()
        set((state) => ({ backupsAvailable: state.backupsAvailable + 1 }))
        get().setSystemNotice(`💾 Persistent snapshot created (${data.backup_file || 'success'})`)
        setTimeout(() => get().setSystemNotice(null), 4000)
      }
    } catch (err) {
      console.warn('Failed to create backup snapshot:', err)
    }
  },

  // Biometric Security State & Methods
  biometrics: {
    userId: 'owner',
    displayName: 'Tony Stark',
    role: 'owner',
    isOwner: true,
    faceMatched: false,
    faceConfidence: 0.0,
    voiceMatched: false,
    voiceConfidence: 0.0,
    cameraActive: false,
    micActive: false,
    consentGiven: false,
    hasEnrolledFace: false,
    hasEnrolledVoice: false,
    enrolledProfiles: 0,
    permissions: ['system_actions', 'shutdown', 'file_ops', 'multitask'],
  },
  biometricsModalOpen: false,
  setBiometricsModalOpen: (biometricsModalOpen: boolean) => set({ biometricsModalOpen }),

  fetchBiometricsStatus: async () => {
    try {
      const res = await fetch('/api/biometrics/status')
      if (res.ok) {
        const data = await res.json()
        set({
          biometrics: {
            userId: data.user_id || 'owner',
            displayName: data.display_name || 'Tony Stark',
            role: data.role || 'owner',
            isOwner: data.role === 'owner',
            faceMatched: !!data.face_matched,
            faceConfidence: data.face_confidence || 0,
            voiceMatched: !!data.voice_matched,
            voiceConfidence: data.voice_confidence || 0,
            cameraActive: !!data.camera_active,
            micActive: !!data.mic_active,
            consentGiven: !!data.consent_given,
            hasEnrolledFace: !!data.has_enrolled_face,
            hasEnrolledVoice: !!data.has_enrolled_voice,
            enrolledProfiles: data.enrolled_profiles || 0,
            permissions: data.permissions || ['chat'],
          },
        })
      }
    } catch (err) {
      console.warn('Failed to fetch biometric state:', err)
    }
  },

  setBiometricConsent: async (consent: boolean) => {
    try {
      const res = await fetch('/api/biometrics/consent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: 'owner', consent }),
      })
      if (res.ok) {
        set((state) => ({
          biometrics: { ...state.biometrics, consentGiven: consent },
        }))
        get().setSystemNotice(consent ? '🛡️ Biometric processing authorized' : 'Biometric consent revoked')
        setTimeout(() => get().setSystemNotice(null), 3000)
      }
    } catch (err) {
      console.warn('Failed to set consent:', err)
    }
  },

  verifyFaceFrame: async (base64Image: string) => {
    try {
      const res = await fetch('/api/biometrics/verify/face', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: base64Image }),
      })
      if (res.ok) {
        const data = await res.json()
        if (data.detected && data.faces && data.faces.length > 0) {
          const top = data.faces[0]
          set((state) => ({
            biometrics: {
              ...state.biometrics,
              userId: top.user_id,
              displayName: top.display_name,
              role: top.role,
              isOwner: top.role === 'owner',
              faceMatched: top.identified,
              faceConfidence: top.confidence,
              cameraActive: true,
            },
          }))
        }
        return data
      }
    } catch (err) {
      console.warn('Face verification error:', err)
    }
    return { detected: false, faces: [] }
  },

  enrollFaceFrame: async (base64Image: string, displayName = 'Tony Stark') => {
    try {
      const res = await fetch('/api/biometrics/enroll/face', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: base64Image, user_id: 'owner', display_name: displayName }),
      })
      const data = await res.json()
      if (res.ok && data.status === 'ok') {
        get().setSystemNotice(`✓ Face scan enrolled for ${displayName}`)
        setTimeout(() => get().setSystemNotice(null), 3500)
        await get().fetchBiometricsStatus()
      } else {
        get().setSystemNotice(`⚠️ ${data.message || 'Face enrollment failed'}`)
        setTimeout(() => get().setSystemNotice(null), 4000)
      }
      return data
    } catch (err) {
      console.warn('Face enrollment error:', err)
      return { status: 'error', message: String(err) }
    }
  },

  enrollVoiceAudio: async (audioBase64: string, displayName = 'Tony Stark') => {
    try {
      const res = await fetch('/api/biometrics/enroll/voice', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ audio: audioBase64, user_id: 'owner', display_name: displayName }),
      })
      const data = await res.json()
      if (res.ok && data.status === 'ok') {
        get().setSystemNotice(`✓ Voice signature enrolled for ${displayName}`)
        setTimeout(() => get().setSystemNotice(null), 3500)
        await get().fetchBiometricsStatus()
      } else {
        get().setSystemNotice(`⚠️ ${data.message || 'Voice enrollment failed'}`)
        setTimeout(() => get().setSystemNotice(null), 4000)
      }
      return data
    } catch (err) {
      console.warn('Voice enrollment error:', err)
      return { status: 'error', message: String(err) }
    }
  },

  purgeBiometrics: async () => {
    try {
      const res = await fetch('/api/biometrics/purge', { method: 'POST' })
      if (res.ok) {
        get().setSystemNotice('🗑️ All biometric data purged from local disk')
        setTimeout(() => get().setSystemNotice(null), 3500)
        await get().fetchBiometricsStatus()
      }
    } catch (err) {
      console.warn('Biometric purge error:', err)
    }
  },

  toggleCameraActive: async (enable?: boolean) => {
    const target = enable !== undefined ? enable : !get().biometrics.cameraActive
    try {
      await fetch('/api/biometrics/camera/toggle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enable: target }),
      })
      set((state) => ({ biometrics: { ...state.biometrics, cameraActive: target } }))
    } catch {
      set((state) => ({ biometrics: { ...state.biometrics, cameraActive: target } }))
    }
  },

  switchUserRole: async (role: 'owner' | 'guest', displayName?: string) => {
    try {
      const res = await fetch('/api/biometrics/user/switch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role, display_name: displayName || (role === 'owner' ? 'Tony Stark' : 'Guest User') }),
      })
      if (res.ok) {
        await get().fetchBiometricsStatus()
        get().setSystemNotice(role === 'owner' ? '🛡️ Switched to Owner: Tony Stark' : '👤 Switched to Guest Mode')
        setTimeout(() => get().setSystemNotice(null), 3000)
      }
    } catch (err) {
      console.warn('Switch role error:', err)
    }
  },

  panelOpen: false,
  panelPosition: 'closed',
  panelContent: {
    type: 'youtube',
    title: 'YouTube Stream',
    videoId: 'f02mOEt11OQ',
    query: '',
  },

  openPanel: (content, position = 'docked-tr') => {
    set({
      panelOpen: true,
      panelPosition: position,
      panelContent: content,
    })
  },

  closePanel: () => {
    set({
      panelOpen: false,
      panelPosition: 'closed',
    })
  },

  setPanelPosition: (panelPosition) => set({ panelPosition }),

  togglePanelZoom: () => {
    const current = get().panelPosition
    if (current === 'center') {
      set({ panelPosition: 'docked-tr' })
    } else {
      set({ panelPosition: 'center' })
    }
  },

  messages: [
    {
      id: 'init-1',
      sender: 'jarvis',
      text: 'Good day, sir. Systems are online and monitoring. Standing by for instructions.',
      timestamp: '17:34:23',
    },
  ],

  addMessage: (sender, text, attachments) => {
    const time = new Date().toLocaleTimeString([], { hour12: false })
    set((state) => ({
      messages: [...state.messages.slice(-19), {
        id: Math.random().toString(), sender, text, timestamp: time,
        ...(attachments && attachments.length ? { attachments } : {}),
      }],
    }))
  },

  isCodingMode: false,
  toggleCodingMode: (enable?: boolean) => {
    const next = enable !== undefined ? enable : !get().isCodingMode
    set({ isCodingMode: next })
  },

  executeCommand: async (rawCommand: string, attachments?: ChatAttachment[]) => {
    const cmd = rawCommand.trim()
    if (!cmd) return

    // Immediate acoustic confirmation blip & audio hardware priming
    playHudChirp()
    console.log(`[JARVIS:STATE] listening -> processing | Command: "${cmd}"`)

    const lowerCmd = cmd.toLowerCase()

    // Intercept Coding Assistant commands
    if (
      lowerCmd.includes('code mode') ||
      lowerCmd.includes('coding assistant') ||
      lowerCmd.includes('coding lab') ||
      lowerCmd.includes('open code editor') ||
      lowerCmd.includes('start coding') ||
      lowerCmd.includes('write code') ||
      lowerCmd.includes('coding workbench')
    ) {
      set({ isCodingMode: true, orbState: 'solving', voiceStatus: 'speaking' })
      get().addMessage('user', cmd)
      const reply = 'Initializing Autonomous AI Coding Lab with GPT-6 Astra reasoning core, sir.'
      get().addMessage('jarvis', reply)
      speakJarvis(reply)
      return
    }

    if (
      lowerCmd.includes('close code mode') ||
      lowerCmd.includes('exit code mode') ||
      lowerCmd.includes('close coding') ||
      lowerCmd.includes('exit coding')
    ) {
      set({ isCodingMode: false, orbState: 'solving', voiceStatus: 'speaking' })
      get().addMessage('user', cmd)
      const reply = 'Returning to holographic command center, sir.'
      get().addMessage('jarvis', reply)
      speakJarvis(reply)
      return
    }

    // The moment Enter is pressed or speech completes, transition to processing state
    set({ orbState: 'searching', voiceStatus: 'processing' })
    get().addMessage('user', cmd, attachments)
    get().setSystemNotice(`Processing: "${cmd.length > 36 ? cmd.slice(0, 33) + '...' : cmd}" with neural core...`)

    // Check if there is an active safety confirmation awaiting user response
    if (get().pendingSafetyConfirmation) {
      const lower = cmd.toLowerCase()
      if (['yes', 'confirm', 'proceed', 'हो', 'हाँ', 'करा', 'करो'].some((w) => lower.includes(w))) {
        await get().confirmSafetyAction('confirm')
        return
      } else if (['no', 'cancel', 'abort', 'नाही', 'थांब', 'नको', 'नहीं', 'रद्द'].some((w) => lower.includes(w))) {
        await get().confirmSafetyAction('cancel')
        return
      }
    }

    // 1. Panel Layout & Choreography Commands
    const lower = cmd.toLowerCase()
    if (lower.includes('dock') || lower.includes('move')) {
      if (lower.includes('top-right') || lower.includes('top right') || lower.includes('tr')) {
        set({ panelPosition: 'docked-tr', orbState: 'solving', voiceStatus: 'speaking' })
        const reply = 'Docking workspace panel to top-right corner.'
        get().addMessage('jarvis', reply)
        speakJarvis(reply)
        return
      }
      if (lower.includes('top-left') || lower.includes('top left') || lower.includes('tl')) {
        set({ panelPosition: 'docked-tl', orbState: 'solving', voiceStatus: 'speaking' })
        const reply = 'Docking workspace panel to top-left corner.'
        get().addMessage('jarvis', reply)
        speakJarvis(reply)
        return
      }
      if (lower.includes('bottom-right') || lower.includes('bottom right') || lower.includes('br')) {
        set({ panelPosition: 'docked-br', orbState: 'solving', voiceStatus: 'speaking' })
        const reply = 'Docking workspace panel to bottom-right corner.'
        get().addMessage('jarvis', reply)
        speakJarvis(reply)
        return
      }
      if (lower.includes('center') || lower.includes('maximize') || lower.includes('zoom')) {
        set({ panelPosition: 'center', orbState: 'solving', voiceStatus: 'speaking' })
        const reply = 'Centering and expanding workspace panel.'
        get().addMessage('jarvis', reply)
        speakJarvis(reply)
        return
      }
    }

    if (
      lower.includes('close panel') ||
      lower.includes('hide panel') ||
      lower.includes('close browser') ||
      lower.includes('close youtube') ||
      lower.includes('dismiss')
    ) {
      get().closePanel()
      set({ orbState: 'solving', voiceStatus: 'speaking' })
      const reply = 'Workspace panel dismissed, sir.'
      get().addMessage('jarvis', reply)
      speakJarvis(reply)
      return
    }

    // 2. Multitasking AI Brain Conversational, Task Execution & Deep Reasoning
    const history = get().messages.map((m) => ({
      role: m.sender === 'user' ? 'user' : 'assistant',
      content: m.text,
    }))

    let data: any = null
    let attempts = 0
    const maxAttempts = 3
    const startTime = performance.now()

    while (attempts < maxAttempts) {
      try {
        console.log(`[JARVIS:HTTP] POST /api/chat attempt ${attempts + 1}/${maxAttempts} for: "${cmd}"`)
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), 12000)

        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          signal: controller.signal,
          body: JSON.stringify({
            messages: [
              ...history.slice(-8),
              { role: 'user', content: cmd },
            ],
            selected_feature_id: cadSelectedFeatureId,
            ...(attachments && attachments.length
              ? { attachments: attachments.map((a) => ({ filename: a.filename, path: a.path, mime_type: a.mime_type || '' })) }
              : {}),
          }),
        })

        clearTimeout(timeoutId)

        if (res.status === 503) {
          attempts++
          set({ backendStatus: 'connecting' })
          if (attempts < maxAttempts) {
            await new Promise((r) => setTimeout(r, 600))
            continue
          }
        }

        if (res.ok) {
          data = await res.json()
          set({ backendStatus: 'connected' })
          break
        } else {
          attempts++
          if (attempts < maxAttempts) {
            await new Promise((r) => setTimeout(r, 500))
            continue
          }
        }
      } catch (err: any) {
        attempts++
        if (err.name === 'AbortError') {
          console.warn('[JARVIS:HTTP] Request timed out after 12s, retrying...')
        } else {
          console.warn('[JARVIS:HTTP] Connection error:', err)
        }
        if (attempts < maxAttempts) {
          set({ backendStatus: 'connecting' })
          await new Promise((r) => setTimeout(r, 500))
          continue
        }
        set({ backendStatus: 'disconnected' })
      }
    }

    const elapsed = Math.round(performance.now() - startTime)

    if (data && data.reply) {
      console.log(`[JARVIS:STATE] processing -> answering (${elapsed}ms) | Reply: "${data.reply.slice(0, 80)}..."`)
      set({ orbState: 'solving', voiceStatus: 'speaking' })
      get().setExecutionOutcome(data.status === 'error' ? 'error' : 'success')

      if (data.requires_confirmation) {
        set({
          pendingSafetyConfirmation: {
            action: data.safety_action,
            prompt: data.reply,
          },
        })
        get().setSystemNotice(`⚠️ SAFETY GATE: ${data.safety_action?.toUpperCase()} REQUIRES CONFIRMATION`)
      } else if (data.cad_action) {
        // JARVIS → real CAD engine: route the verified action into the workspace.
        const ca = data.cad_action
        set({ voiceStatus: 'executing' })
        window.dispatchEvent(new CustomEvent('jarvis-navigate', { detail: { view: 'cad' } }))
        const refresh = (featureId: string | null) =>
          window.dispatchEvent(new CustomEvent('jarvis-cad-refresh', { detail: { featureId } }))
        switch (ca.action) {
          case 'transform':
            if (ca.op === 'rotate') {
              window.dispatchEvent(new CustomEvent('jarvis-cad-rotate', { detail: { angle: ca.angle_deg, axis: ca.axis } }))
            } else if (ca.op === 'move') {
              window.dispatchEvent(
                new CustomEvent('jarvis-cad-move', {
                  detail: ca.absolute ? { axis: ca.axis, setValue: ca.value_mm } : { [ca.axis]: ca.value_mm },
                })
              )
            } else if (ca.op === 'scale') {
              window.dispatchEvent(new CustomEvent('jarvis-cad-scale', { detail: { factor: ca.factor } }))
            }
            break
          case 'viewport':
            if (ca.op === 'fit') {
              window.dispatchEvent(new CustomEvent('jarvis-cad-view', { detail: { preset: 'fit' } }))
            }
            break
          case 'measure':
            window.dispatchEvent(new CustomEvent('jarvis-cad-measure', { detail: { featureId: ca.feature_id } }))
            break
          case 'create_primitive':
          case 'refresh_viewport':
          default:
            refresh(ca.feature_id ?? null)
            break
        }
        get().setSystemNotice(`CAD ENGINE: ${data.reply}`)
        setTimeout(() => get().setSystemNotice(null), 4500)
      } else if (data.system_action) {
        const ytAction = findPlayableVideo(data.system_action)
        if (ytAction) {
          get().openPanel(
            {
              type: 'youtube',
              title: ytAction.title || `Now Playing: ${ytAction.query || 'Music'}`,
              videoId: ytAction.video_id,
              query: ytAction.query || '',
              autoplaySound: true,
            },
            'docked-tr'
          )
        }
        const actionNotice = data.is_compound
          ? `Executed ${data.system_action.executed_actions?.length || 2} Compound Tasks`
          : data.reply
        get().setSystemNotice(actionNotice)
        setTimeout(() => get().setSystemNotice(null), 4500)
      } else {
        get().setSystemNotice(`JARVIS: "${data.reply.length > 50 ? data.reply.slice(0, 47) + '...' : data.reply}"`)
        setTimeout(() => get().setSystemNotice(null), 4000)
      }

      const reply = data.reply
      const generatedOutputs: ChatAttachment[] = Array.isArray(data.outputs) ? data.outputs : []
      get().addMessage('jarvis', reply, generatedOutputs.length ? generatedOutputs : undefined)
      speakJarvis(reply)

      // Refresh persistent state (tasks, memories, backups) seamlessly
      get().fetchPersistentState().catch(() => {})
    } else {
      console.error(`[JARVIS:STATE] processing -> connection_failure (${elapsed}ms)`)
      set({ orbState: 'solving', voiceStatus: 'speaking' })

      const failureReply =
        get().backendStatus === 'disconnected'
          ? 'Workstation backend connection offline, sir. Core services on port 8000 are unreachable.'
          : 'I encountered an interruption communicating with the neural core, sir. All core system controls remain ready.'
      get().addMessage('jarvis', failureReply)
      get().setSystemNotice(`⚠️ ${failureReply}`)
      setTimeout(() => get().setSystemNotice(null), 5000)
      speakJarvis(failureReply)
    }
  },
}))

if (typeof window !== 'undefined') {
  window.addEventListener('jarvis-cad-selected', (e) => {
    cadSelectedFeatureId = (e as CustomEvent).detail?.featureId ?? null
  })
  window.addEventListener('jarvis-cad-outcome', (e) => {
    const d = (e as CustomEvent).detail
    if (d?.status) useJarvisStore.getState().setExecutionOutcome(d.status, d.message)
  })
}
