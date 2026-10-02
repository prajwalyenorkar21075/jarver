import { useState } from 'react'
import { useJarvisStore } from '../store/useJarvisStore'
import { voiceController } from '../services/voiceController'

export default function JarvisVoiceBar() {
  const [inputText, setInputText] = useState('')

  const isListening = useJarvisStore((s) => s.isListening)
  const currentTranscript = useJarvisStore((s) => s.currentTranscript)
  const executeCommand = useJarvisStore((s) => s.executeCommand)
  const messages = useJarvisStore((s) => s.messages)
  const speechSupported = voiceController.isSpeechSupported()

  const latestMessage = messages[messages.length - 1]

  const toggleMic = async () => {
    await voiceController.toggleListening()
  }

  const handleTextSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputText.trim()) return
    executeCommand(inputText.trim())
    setInputText('')
  }

  return (
    <div className="fixed bottom-5 left-1/2 z-30 flex w-[min(94vw,760px)] -translate-x-1/2 flex-col items-center gap-2.5">
      {/* Dynamic Transcript & Latest Response Box */}
      {(currentTranscript || latestMessage) && (
        <div className="flex w-full items-center justify-between gap-3 rounded-full border border-cyan-500/35 bg-[#060b18]/95 px-4 py-1.5 text-xs font-mono transition-all">
          <div className="flex items-center gap-2 truncate">
            <span
              className={`h-2 w-2 rounded-full shrink-0 ${
                currentTranscript ? 'bg-cyan-400 animate-ping' : 'bg-[#D4712B]'
              }`}
            />
            <span className="text-white/40 shrink-0 font-semibold">
              {currentTranscript ? 'TRANSCRIPT:' : latestMessage?.sender === 'jarvis' ? 'JARVIS:' : 'YOU:'}
            </span>
            <span className="text-white/90 truncate">
              {currentTranscript || latestMessage?.text}
            </span>
          </div>

          <span className="text-[10px] text-white/35 shrink-0 font-mono">
            {currentTranscript ? 'LIVE' : latestMessage?.timestamp}
          </span>
        </div>
      )}

      {/* Main Glassmorphic Command & Glowing Mic Dock */}
      <div className="flex w-full items-center gap-2.5 rounded-2xl border border-cyan-500/35 bg-[#060b18]/95 p-2">
        {/* Glowing Cyan Mic Activation Button */}
        <button
          type="button"
          onClick={toggleMic}
          className={`flex h-11 w-11 shrink-0 cursor-pointer items-center justify-center rounded-xl transition-all duration-300 border border-cyan-400/50 ${
            isListening
              ? 'bg-cyan-400 text-black scale-105'
              : 'bg-cyan-500 text-black hover:scale-105 active:scale-95'
          }`}
          title={isListening ? 'Stop listening' : speechSupported ? 'Start voice recognition' : 'Microphone standby'}
        >
          {isListening ? (
            <svg className="h-5 w-5 animate-pulse" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" />
              <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
            </svg>
          ) : (
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
              <path d="M12 2a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
              <path d="M19 10v1a7 7 0 0 1-14 0v-1" />
              <line x1="12" y1="19" x2="12" y2="22" strokeWidth="2.4" />
            </svg>
          )}
        </button>

        {/* Text Command Input Form */}
        <form onSubmit={handleTextSubmit} className="flex flex-1 items-center gap-2">
          <input
            id="jarvis-main-input"
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder={
              isListening
                ? 'Listening to speech... or type instruction here'
                : 'Listening to speech... or type instruction here'
            }
            className="flex-1 bg-transparent px-3 py-1 font-mono text-sm text-white placeholder-white/35 focus:outline-none"
          />
          <button
            type="submit"
            className="cursor-pointer rounded-xl bg-white/10 px-4 py-2 font-mono text-xs font-semibold text-white/90 hover:bg-white/20 active:scale-95 transition-all"
          >
            Send
          </button>
        </form>
      </div>

      {/* Suggested Quick Triggers (Choreography & Tools) */}
      <div className="flex flex-wrap items-center justify-center gap-2 text-[11px] font-mono select-none">
        <button
          type="button"
          onClick={() => executeCommand('open YouTube in top-right')}
          className="cursor-pointer flex items-center gap-1.5 rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1 text-amber-300 hover:bg-amber-500/20 active:scale-95 transition-all"
        >
          <svg className="h-3 w-3" viewBox="0 0 24 24" fill="currentColor">
            <polygon points="5,3 19,12 5,21" />
          </svg>
          <span>Open YouTube in Top Right</span>
        </button>

        <button
          type="button"
          onClick={() => executeCommand('search Arc Reactor propulsion')}
          className="cursor-pointer flex items-center gap-1.5 rounded-full border border-cyan-500/30 bg-cyan-500/10 px-3 py-1 text-cyan-300 hover:bg-cyan-500/20 active:scale-95 transition-all"
        >
          <svg className="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <span>Search In App</span>
        </button>

        <button
          type="button"
          onClick={() => executeCommand('center panel')}
          className="cursor-pointer flex items-center gap-1.5 rounded-full border border-white/15 bg-white/5 px-3 py-1 text-white/70 hover:bg-white/15 active:scale-95 transition-all"
        >
          <svg className="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="15 3 21 3 21 9" />
            <polyline points="9 21 3 21 3 15" />
            <line x1="21" y1="3" x2="14" y2="10" />
            <line x1="3" y1="21" x2="10" y2="14" />
          </svg>
          <span>Center Panel</span>
        </button>

        <button
          type="button"
          onClick={() => executeCommand('play this music')}
          className="cursor-pointer flex items-center gap-1.5 rounded-full border border-purple-500/30 bg-purple-500/10 px-3 py-1 text-purple-300 hover:bg-purple-500/20 active:scale-95 transition-all"
        >
          <svg className="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M9 18V5l12-2v13" />
            <circle cx="6" cy="18" r="3" />
            <circle cx="18" cy="16" r="3" />
          </svg>
          <span>Play Music</span>
        </button>

        <button
          type="button"
          onClick={() => executeCommand('orb solving')}
          className="cursor-pointer flex items-center gap-1.5 rounded-full border border-white/15 bg-white/5 px-3 py-1 text-white/70 hover:bg-white/15 active:scale-95 transition-all"
        >
          <svg className="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <path d="m4.93 4.93 4.24 4.24" />
            <path d="m14.83 9.17 4.24-4.24" />
            <path d="m14.83 14.83 4.24 4.24" />
            <path d="m9.17 14.83-4.24 4.24" />
          </svg>
          <span>State: Solving</span>
        </button>
      </div>
    </div>
  )
}

