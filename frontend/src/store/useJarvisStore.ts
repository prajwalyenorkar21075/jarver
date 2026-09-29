import { create } from 'zustand'
import type { OrbState } from 'thinking-orbs'

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
}

export interface ChatMessage {
  id: string
  sender: 'user' | 'jarvis'
  text: string
  timestamp: string
}

interface JarvisStore {
  // Orb State
  orbState: OrbState
  setOrbState: (state: OrbState) => void

  // Voice & Interaction State
  isListening: boolean
  setIsListening: (listening: boolean) => void
  voiceStatus: 'idle' | 'listening' | 'processing' | 'speaking'
  setVoiceStatus: (status: 'idle' | 'listening' | 'processing' | 'speaking') => void
  currentTranscript: string
  setCurrentTranscript: (transcript: string) => void

  // System Notification Toast
  systemNotice: string | null
  setSystemNotice: (notice: string | null) => void

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
  addMessage: (sender: 'user' | 'jarvis', text: string) => void

  // High level command executor
  executeCommand: (command: string) => void
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

export async function speakJarvis(text: string) {
  if (!text || !text.trim()) return

  // 1. Immediate visual feedback: show solving (speaking) animation as requested
  useJarvisStore.getState().setOrbState('solving')
  useJarvisStore.getState().setVoiceStatus('speaking')

  const resetToIdle = () => {
    useJarvisStore.getState().setOrbState('composing')
    useJarvisStore.getState().setVoiceStatus('idle')
  }

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
        resetToIdle()
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
        resetToIdle()
      }
      audio.onerror = () => {
        resetToIdle()
      }

      await audio.play()
      return
    }
  } catch (e2) {
    console.warn('HTML5 Audio fallback failed:', e2)
  }

  // 4. Tertiary Engine: Web Speech API (Local Browser Voice)
  if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
    try {
      window.speechSynthesis.cancel()
      const utterance = new SpeechSynthesisUtterance(text)
      utterance.rate = 1.05
      utterance.pitch = 0.95
      utterance.onend = resetToIdle
      utterance.onerror = resetToIdle

      const voices = window.speechSynthesis.getVoices()
      const preferred =
        voices.find(
          (v) =>
            v.lang.startsWith('en') &&
            (v.name.includes('Natural') ||
              v.name.includes('UK') ||
              v.name.includes('David') ||
              v.name.includes('Male') ||
              v.name.includes('George'))
        ) || voices.find((v) => v.lang.startsWith('en'))
      if (preferred) utterance.voice = preferred

      window.speechSynthesis.speak(utterance)
      return
    } catch (e) {
      console.warn('Web Speech fallback failed:', e)
      resetToIdle()
    }
  } else {
    setTimeout(resetToIdle, 3000)
  }
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
  },
  voiceStatus: 'idle',
  setVoiceStatus: (voiceStatus) => set({ voiceStatus }),
  currentTranscript: '',
  setCurrentTranscript: (currentTranscript) => set({ currentTranscript }),

  systemNotice: null,
  setSystemNotice: (systemNotice) => set({ systemNotice }),

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

  addMessage: (sender, text) => {
    const time = new Date().toLocaleTimeString([], { hour12: false })
    set((state) => ({
      messages: [...state.messages.slice(-19), { id: Math.random().toString(), sender, text, timestamp: time }],
    }))
  },

  executeCommand: async (rawCommand: string) => {
    const cmd = rawCommand.trim()
    if (!cmd) return

    // Immediate acoustic confirmation blip & audio hardware priming
    playHudChirp()

    // The moment Enter is pressed, immediately show searching (thinking) blob animation
    set({ orbState: 'searching', voiceStatus: 'processing' })
    get().addMessage('user', cmd)

    // 1. Execute via PC Desktop Automation Handler (YouTube, Instagram, Facebook, Browser, PC Apps, URLs)
    try {
      const sysRes = await fetch('/api/system/open', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target: cmd, type: 'auto' }),
      })

      if (sysRes.ok) {
        const sysData = await sysRes.json()
        if (sysData.success) {
          // Real system target opened on PC!
          const reply = sysData.reply || `Executing command on your PC, sir.`

          // Also trigger client window.open if it's a URL for instant opening
          if (sysData.type === 'url' && sysData.target) {
            try {
              window.open(sysData.target, '_blank', 'noopener,noreferrer')
            } catch (e) {
              console.warn('Direct window.open blocked by popup policy:', e)
            }
          }

          // Show floating HUD notification
          get().setSystemNotice(reply)
          setTimeout(() => get().setSystemNotice(null), 4000)

          get().addMessage('jarvis', reply)
          speakJarvis(reply)
          return
        }
      }
    } catch (sysErr) {
      console.warn('System open API check error:', sysErr)
    }

    // 2. Panel Layout & Choreography Commands
    const lower = cmd.toLowerCase()
    if (lower.includes('dock') || lower.includes('move')) {
      if (lower.includes('top-right') || lower.includes('top right') || lower.includes('tr')) {
        set({ panelPosition: 'docked-tr' })
        const reply = 'Docking workspace panel to top-right corner.'
        get().addMessage('jarvis', reply)
        speakJarvis(reply)
        return
      }
      if (lower.includes('top-left') || lower.includes('top left') || lower.includes('tl')) {
        set({ panelPosition: 'docked-tl' })
        const reply = 'Docking workspace panel to top-left corner.'
        get().addMessage('jarvis', reply)
        speakJarvis(reply)
        return
      }
      if (lower.includes('bottom-right') || lower.includes('bottom right') || lower.includes('br')) {
        set({ panelPosition: 'docked-br' })
        const reply = 'Docking workspace panel to bottom-right corner.'
        get().addMessage('jarvis', reply)
        speakJarvis(reply)
        return
      }
      if (lower.includes('center') || lower.includes('maximize') || lower.includes('zoom')) {
        set({ panelPosition: 'center' })
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
      const reply = 'Workspace panel dismissed, sir.'
      get().addMessage('jarvis', reply)
      speakJarvis(reply)
      return
    }

    // 3. Intelligent Query via Groq LLM Backend & Cloned Voice Response
    const history = get().messages.map((m) => ({
      role: m.sender === 'user' ? 'user' : 'assistant',
      content: m.text,
    }))

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [
            ...history.slice(-6),
            {
              role: 'system',
              content:
                'You are JARVIS, Tony Stark’s ultra-intelligent, sophisticated, and polite AI assistant. Keep responses crisp, articulate, and sci-fi themed.',
            },
            { role: 'user', content: cmd },
          ],
        }),
      })

      const data = await res.json()
      const reply = data?.reply || 'Understood, sir. Systems are executing.'

      if (data?.system_action?.success && data?.system_action?.target) {
        if (data.system_action.type === 'url') {
          window.open(data.system_action.target, '_blank', 'noopener,noreferrer')
        }
        get().setSystemNotice(reply)
        setTimeout(() => get().setSystemNotice(null), 4000)
      }

      get().addMessage('jarvis', reply)
      speakJarvis(reply)
    } catch (err) {
      console.warn('Backend LLM error:', err)
      const fallback = `Acknowledged: "${cmd}". Standing by for instructions.`
      get().addMessage('jarvis', fallback)
      speakJarvis(fallback)
    }
  },
}))
