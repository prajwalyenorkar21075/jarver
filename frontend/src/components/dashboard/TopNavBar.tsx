import { useState } from 'react'
import { useJarvisStore, speakJarvis } from '../../store/useJarvisStore'

export default function TopNavBar() {
  const [query, setQuery] = useState('')
  const executeCommand = useJarvisStore((s) => s.executeCommand)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return
    executeCommand(query.trim())
    setQuery('')
  }

  return (
    <header className="relative z-30 flex h-14 w-full items-center justify-between px-6 pt-2 select-none border-b border-cyan-500/30 bg-[#040a18]/90 backdrop-blur-none">
      {/* Left: Brand with Hexagon Icon */}
      <div className="flex items-center gap-3">
        {/* Hexagon Logo Icon */}
        <div className="relative flex h-10 w-10 items-center justify-center">
          <svg className="h-full w-full" viewBox="0 0 40 40" fill="none">
            <polygon
              points="20,2 37,11 37,29 20,38 3,29 3,11"
              fill="#071530"
              stroke="#00e5ff"
              strokeWidth="2"
            />
            <polygon
              points="20,8 31,14 31,26 20,32 9,26 9,14"
              fill="none"
              stroke="#00e5ff"
              strokeWidth="1.2"
              strokeDasharray="4 2"
            />
            <circle cx="20" cy="20" r="3" fill="#ffffff" />
          </svg>
        </div>

        <div>
          <h1 className="font-mono text-base font-extrabold tracking-[0.2em] text-white">
            JARVIS<span className="text-[#00e5ff]">.AI</span>
          </h1>
          <p className="font-mono text-[10px] tracking-wider text-cyan-300/80">AEROSPACE DEFENSE HUD</p>
        </div>
      </div>

      {/* Center: Search Bar & Browser Launchers */}
      <div className="hidden md:flex items-center gap-2">
        <form
          onSubmit={handleSubmit}
          className="flex items-center gap-2 rounded-full border border-cyan-500/40 bg-black/85 px-4 py-1.5 transition-all focus-within:border-[#00e5ff] w-[320px]"
        >
          <svg className="h-4 w-4 text-cyan-400/60" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask Jarvis anything..."
            className="flex-1 bg-transparent font-mono text-xs text-white placeholder-white/40 focus:outline-none"
          />
        </form>

        {/* HUD Intelligence Console Toggle */}
        <button
          type="button"
          onClick={() => {
            const store = useJarvisStore.getState()
            if (store.panelOpen) {
              store.closePanel()
            } else {
              store.openPanel(
                {
                  type: 'search',
                  title: 'HUD Intelligence Console',
                  query: 'Iron Man Jarvis AI',
                },
                'center'
              )
            }
          }}
          className="cursor-pointer flex items-center gap-1.5 rounded-full border border-cyan-400/60 bg-[#071530] px-3.5 py-1.5 text-xs font-mono font-bold text-[#00e5ff] hover:bg-[#00e5ff] hover:text-black transition-all active:scale-95 shadow-[0_0_10px_rgba(0,229,255,0.2)]"
          title="Toggle HUD Intelligence Console"
        >
          <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="2" y1="12" x2="22" y2="12" />
            <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1 4-10z" />
          </svg>
          <span>HUD INTEL</span>
        </button>

        {/* Direct Open Browser in New Tab Button */}
        <button
          type="button"
          onClick={() => {
            window.open('https://www.google.com', '_blank', 'noopener,noreferrer')
          }}
          className="cursor-pointer flex items-center gap-1.5 rounded-full border border-[#00e5ff]/50 bg-[#00e5ff] px-3.5 py-1.5 text-xs font-mono font-extrabold text-black hover:bg-cyan-300 transition-all active:scale-95 shadow-[0_0_12px_rgba(0,229,255,0.3)]"
          title="Open Google in a new browser tab"
        >
          <span>OPEN BROWSER</span>
          <span>↗</span>
        </button>

        {/* Direct Test Voice Trigger */}
        <button
          type="button"
          onClick={() => {
            speakJarvis('Jarvis voice system online and fully operational, sir.')
          }}
          className="cursor-pointer flex items-center gap-1.5 rounded-full border border-cyan-400/40 bg-cyan-500/10 px-3 py-1.5 text-xs font-mono font-semibold text-cyan-300 hover:bg-cyan-500/25 hover:border-cyan-300 transition-all active:scale-95"
          title="Test Cloned Jarvis Voice Audio"
        >
          <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
            <path d="M19 10v1a7 7 0 0 1-14 0v-1" />
            <line x1="12" y1="19" x2="12" y2="22" stroke="currentColor" strokeWidth="2" />
          </svg>
          <span>TEST VOICE</span>
        </button>
      </div>

      {/* Right: Online Status, Bell, User Avatar */}
      <div className="flex items-center gap-3">
        {/* Online Indicator Pill */}
        <div className="flex items-center gap-2 rounded-full border border-cyan-500/40 bg-[#071530] px-3 py-1 font-mono text-xs text-[#00e5ff]">
          <span className="h-2 w-2 rounded-full bg-[#00e5ff] animate-pulse" />
          <span className="font-bold">ONLINE</span>
        </div>

        {/* Notification Bell */}
        <button
          type="button"
          className="relative flex h-8 w-8 cursor-pointer items-center justify-center rounded-full border border-cyan-500/35 bg-[#071530] text-white/70 hover:text-white transition-colors"
          title="Notifications"
        >
          <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
            <path d="M13.73 21a2 2 0 0 1-3.46 0" />
          </svg>
          <span className="absolute top-1.5 right-1.5 h-1.5 w-1.5 rounded-full bg-[#00e5ff]" />
        </button>

        {/* User Profile Avatar */}
        <div className="relative flex h-9 w-9 cursor-pointer items-center justify-center rounded-full border border-[#00e5ff] bg-[#071530] p-0.5 shadow-[0_0_8px_rgba(0,229,255,0.3)]">
          <div className="flex h-full w-full items-center justify-center rounded-full bg-[#040a18] font-mono text-xs font-bold text-[#00e5ff]">
            TS
          </div>
        </div>
      </div>
    </header>
  )
}
