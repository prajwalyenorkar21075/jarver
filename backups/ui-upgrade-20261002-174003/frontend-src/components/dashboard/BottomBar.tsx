import { useState } from 'react'
import { useJarvisStore } from '../../store/useJarvisStore'

export default function BottomBar() {
  const [inputText, setInputText] = useState('')
  const executeCommand = useJarvisStore((s) => s.executeCommand)
  const audioLevel = useJarvisStore((s) => s.audioLevel)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputText.trim()) return
    executeCommand(inputText.trim())
    setInputText('')
  }

  return (
    <footer className="relative z-30 flex flex-col md:flex-row items-center justify-between gap-4 px-6 pb-4 pt-2 select-none w-full max-w-[1440px] mx-auto">
      {/* 1. Left: Media Player Widget */}
      <div className="flex items-center gap-3 rounded-2xl border border-cyan-500/40 bg-[#040a18]/95 p-2.5 w-full md:w-[320px] shadow-[0_0_15px_rgba(0,229,255,0.08)]">
        {/* Album Art Thumbnail */}
        <div className="relative h-11 w-11 shrink-0 overflow-hidden rounded-xl border border-cyan-400/50 bg-[#071530]">
          <svg className="h-full w-full opacity-80" viewBox="0 0 40 40">
            <rect width="40" height="40" fill="#071530" />
            <circle cx="20" cy="18" r="9" fill="#00e5ff" opacity="0.8" />
            <path d="M0 32 L40 32" stroke="#00e5ff" strokeWidth="1" />
            <path d="M0 36 L40 36" stroke="#00e5ff" strokeWidth="1" />
            <path d="M20 18 L0 40 L40 40 Z" fill="rgba(0, 229, 255, 0.25)" />
          </svg>
        </div>

        {/* Track Details & Controls */}
        <div className="flex-1 min-w-0 font-mono">
          <div className="flex items-center justify-between">
            <div className="truncate">
              <div className="text-[11px] font-semibold text-white truncate">JARVIS Media</div>
              <div className="text-[9px] text-cyan-300/60 truncate">Standby — no track loaded</div>
            </div>

            {/* Playback Controls — each launches a real backend command */}
            <div className="flex items-center gap-1.5 text-white/70">
              <button
                type="button"
                onClick={() => executeCommand('open youtube')}
                className="cursor-pointer hover:text-[#00e5ff] transition-colors"
                title="Open YouTube"
              >
                <svg className="h-3 w-3" viewBox="0 0 24 24" fill="currentColor">
                  <polygon points="19,20 9,12 19,4" />
                  <rect x="5" y="4" width="3" height="16" />
                </svg>
              </button>
              <button
                type="button"
                onClick={() => executeCommand('play music')}
                className="cursor-pointer flex h-6 w-6 items-center justify-center rounded-full bg-cyan-500/20 text-[#00e5ff] hover:bg-[#00e5ff] hover:text-black transition-all border border-cyan-400/50 shadow-[0_0_8px_rgba(0,229,255,0.2)]"
                title="Play music (launches YouTube search)"
              >
                <svg className="h-3 w-3" viewBox="0 0 24 24" fill="currentColor">
                  <polygon points="5,3 19,12 5,21" />
                </svg>
              </button>
              <button
                type="button"
                onClick={() => executeCommand('open spotify')}
                className="cursor-pointer hover:text-[#00e5ff] transition-colors"
                title="Open Spotify (reports honestly if not installed)"
              >
                <svg className="h-3 w-3" viewBox="0 0 24 24" fill="currentColor">
                  <polygon points="5,4 15,12 5,20" />
                  <rect x="16" y="4" width="3" height="16" />
                </svg>
              </button>
            </div>
          </div>

          {/* Live microphone level (real telemetry while voice input is active) */}
          <div className="mt-1.5 h-1 w-full rounded-full bg-black/60 overflow-hidden border border-cyan-500/20">
            <div
              className="h-full rounded-full bg-[#00e5ff] shadow-[0_0_8px_#00e5ff] transition-all"
              style={{ width: `${Math.min(100, Math.round((audioLevel || 0) * 100))}%` }}
            />
          </div>
        </div>
      </div>

      {/* 2. Center: Primary Input Bar */}
      <form
        onSubmit={handleSubmit}
        className="flex items-center gap-2 rounded-2xl border border-cyan-500/50 bg-[#040a18]/95 px-4 py-2 transition-all focus-within:border-[#00e5ff] flex-1 max-w-[480px] w-full shadow-[0_0_15px_rgba(0,229,255,0.12)]"
      >
        {/* Star Icon */}
        <div className="text-[#00e5ff]">
          <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2l2.4 7.4H22l-6 4.6 2.3 7-6.3-4.6-6.3 4.6 2.3-7-6-4.6h7.6z" />
          </svg>
        </div>

        <input
          id="jarvis-main-input"
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="Ask Jarvis anything..."
          className="flex-1 bg-transparent font-mono text-sm text-white placeholder-white/40 focus:outline-none"
        />

        {/* Submit Arrow Button - Solid Cyber Cyan */}
        <button
          type="submit"
          className="flex h-8 w-8 cursor-pointer items-center justify-center rounded-xl bg-[#00e5ff] text-black font-extrabold hover:bg-cyan-300 transition-all shadow-[0_0_12px_rgba(0,229,255,0.4)] active:scale-95"
          title="Send"
        >
          <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.8">
            <line x1="5" y1="12" x2="19" y2="12" />
            <polyline points="12 5 19 12 12 19" />
          </svg>
        </button>
      </form>

      {/* 3. Right: Inspirational Quote Pill */}
      <div className="hidden lg:flex items-center gap-3 rounded-2xl border border-cyan-500/40 bg-[#040a18]/95 px-4 py-2.5 max-w-[340px] shadow-[0_0_15px_rgba(0,229,255,0.08)]">
        <div className="text-[#00e5ff]">
          <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2l2.4 7.4H22l-6 4.6 2.3 7-6.3-4.6-6.3 4.6 2.3-7-6-4.6h7.6z" />
          </svg>
        </div>

        <div className="flex-1 font-mono text-[10px] text-cyan-100/80 italic leading-snug">
          &quot;Better tools. Better thoughts. A brighter future.&quot;
        </div>

        {/* Subtle Waveform Line */}
        <div className="flex items-center gap-0.5 text-[#00e5ff]">
          <span className="h-2 w-0.5 rounded-full bg-[#00e5ff]" />
          <span className="h-3 w-0.5 rounded-full bg-cyan-300" />
          <span className="h-4 w-0.5 rounded-full bg-[#00e5ff]" />
          <span className="h-2 w-0.5 rounded-full bg-cyan-400" />
        </div>
      </div>
    </footer>
  )
}
