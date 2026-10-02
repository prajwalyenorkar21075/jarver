import { useEffect, useRef, useState } from 'react'
import { useJarvisStore } from '../../store/useJarvisStore'

export default function BottomBar() {
  const [inputText, setInputText] = useState('')
  const [historyOpen, setHistoryOpen] = useState(false)
  const historyIdx = useRef(-1)
  const executeCommand = useJarvisStore((s) => s.executeCommand)
  const messages = useJarvisStore((s) => s.messages)
  const voiceStatus = useJarvisStore((s) => s.voiceStatus)
  const backendStatus = useJarvisStore((s) => s.backendStatus)
  const audioLevel = useJarvisStore((s) => s.audioLevel)
  const isListening = useJarvisStore((s) => s.isListening)
  const toggleListening = useJarvisStore((s) => s.toggleListening)

  const commandHistory = messages.filter((m) => m.sender === 'user').slice(-20).reverse()
  const lastResult = [...messages].reverse().find((m) => m.sender === 'jarvis')

  const statusLabel =
    backendStatus !== 'connected'
      ? 'BACKEND OFFLINE'
      : voiceStatus === 'processing'
      ? 'EXECUTING…'
      : voiceStatus === 'speaking'
      ? 'SPEAKING'
      : isListening
      ? 'LISTENING'
      : 'READY'

  const statusColor =
    backendStatus !== 'connected'
      ? 'text-rose-400 border-rose-500/50'
      : voiceStatus === 'processing'
      ? 'text-amber-300 border-amber-500/50'
      : isListening || voiceStatus === 'speaking'
      ? 'text-[#00e5ff] border-[#00e5ff]/60'
      : 'text-emerald-400 border-emerald-500/50'

  const handleSubmit = (e?: React.FormEvent, raw?: string) => {
    e?.preventDefault()
    const text = (raw ?? inputText).trim()
    if (!text) return
    executeCommand(text)
    setInputText('')
    historyIdx.current = -1
    setHistoryOpen(false)
  }

  const navigateHistory = (dir: 1 | -1) => {
    if (commandHistory.length === 0) return
    const next = Math.max(0, Math.min(commandHistory.length - 1, historyIdx.current + dir))
    historyIdx.current = next
    setInputText(commandHistory[next].text)
  }

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setHistoryOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const tinyBtn =
    'cursor-pointer rounded border border-cyan-500/40 bg-[#071530] px-2 py-1 font-mono text-[9px] font-bold text-cyan-300 transition-all hover:border-[#00e5ff] hover:text-white active:scale-95'

  return (
    <footer className="relative z-30 w-full max-w-[1720px] mx-auto select-none px-6 pb-3 pt-1">
      {/* Command history popover */}
      {historyOpen && (
        <div className="absolute bottom-full left-1/2 z-40 mb-2 max-h-64 w-[min(560px,90vw)] -translate-x-1/2 overflow-auto rounded-lg border border-cyan-500/40 bg-[#040a18] py-1 shadow-[0_10px_40px_rgba(0,0,0,0.8)]">
          <div className="px-3 py-1 font-mono text-[9px] tracking-[0.25em] text-cyan-400/60">COMMAND HISTORY</div>
          {commandHistory.length === 0 && (
            <div className="px-3 py-2 font-mono text-[10px] text-white/40">No commands yet this session.</div>
          )}
          {commandHistory.map((m, i) => (
            <button
              key={m.id}
              type="button"
              onClick={() => handleSubmit(undefined, m.text)}
              className={`block w-full cursor-pointer px-3 py-1.5 text-left font-mono text-[11px] transition-colors hover:bg-[#00e5ff]/10 ${
                i === 0 ? 'text-cyan-100' : 'text-cyan-100/60'
              }`}
            >
              <span className="mr-2 text-cyan-500/50">{m.timestamp}</span>
              {m.text}
            </button>
          ))}
        </div>
      )}

      <div className="flex flex-col items-stretch gap-2 lg:flex-row lg:items-center">
        {/* 1. Left: execution status + last tool result */}
        <div className="flex min-w-0 flex-1 items-center gap-2">
          <div className={`shrink-0 rounded border bg-[#040a18]/95 px-2.5 py-1 font-mono text-[10px] font-bold tracking-wider ${statusColor}`}>
            {statusLabel}
          </div>
          <div className="min-w-0 truncate rounded border border-cyan-500/25 bg-[#040a18]/95 px-2.5 py-1 font-mono text-[10px] text-cyan-100/70" title={lastResult?.text}>
            {lastResult ? `RESULT: ${lastResult.text}` : 'RESULT: —'}
          </div>
        </div>

        {/* 2. Center: command console input */}
        <form
          onSubmit={handleSubmit}
          className="flex w-full max-w-[560px] items-center gap-1.5 rounded-xl border border-cyan-500/50 bg-[#040a18]/95 px-3 py-1.5 shadow-[0_0_15px_rgba(0,229,255,0.12)] transition-all focus-within:border-[#00e5ff]"
        >
          <span className="font-mono text-[12px] font-bold text-[#00e5ff]">&gt;</span>
          <input
            id="jarvis-main-input"
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'ArrowUp') {
                e.preventDefault()
                navigateHistory(1)
              } else if (e.key === 'ArrowDown') {
                e.preventDefault()
                navigateHistory(-1)
              }
            }}
            placeholder="Command — e.g. create a box 100 by 50 by 30"
            className="min-w-0 flex-1 bg-transparent font-mono text-[12px] text-white placeholder-white/40 focus:outline-none"
          />
          <button
            type="button"
            className={tinyBtn}
            onClick={() => setHistoryOpen((v) => !v)}
            title="Command history"
          >
            HIST
          </button>
          <button
            type="button"
            onClick={() => toggleListening()}
            className={`flex h-7 w-7 cursor-pointer items-center justify-center rounded-lg border transition-all active:scale-95 ${
              isListening
                ? 'animate-pulse border-[#00e5ff] bg-[#00e5ff] text-black'
                : 'border-cyan-500/50 bg-[#071530] text-cyan-300 hover:border-[#00e5ff] hover:text-white'
            }`}
            title={isListening ? 'Stop voice input' : 'Start voice input'}
          >
            <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
              <path d="M19 10v1a7 7 0 0 1-14 0v-1" fill="none" stroke="currentColor" strokeWidth="2" />
              <line x1="12" y1="19" x2="12" y2="22" stroke="currentColor" strokeWidth="2" />
            </svg>
          </button>
          <button
            type="submit"
            className="flex h-7 w-8 cursor-pointer items-center justify-center rounded-lg bg-[#00e5ff] font-extrabold text-black shadow-[0_0_12px_rgba(0,229,255,0.4)] transition-all hover:bg-cyan-300 active:scale-95"
            title="Execute command"
          >
            <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.8">
              <line x1="5" y1="12" x2="19" y2="12" />
              <polyline points="12 5 19 12 12 19" />
            </svg>
          </button>
        </form>

        {/* 3. Right: live mic level + media quick commands (real backend actions) */}
        <div className="flex items-center gap-2 rounded-xl border border-cyan-500/40 bg-[#040a18]/95 px-3 py-1.5">
          <span className="font-mono text-[9px] tracking-wider text-cyan-400/60">MIC</span>
          <div className="h-1.5 w-16 overflow-hidden rounded-full border border-cyan-500/20 bg-black/60">
            <div
              className="h-full rounded-full bg-[#00e5ff] shadow-[0_0_8px_#00e5ff] transition-all"
              style={{ width: `${Math.min(100, Math.round((audioLevel || 0) * 100))}%` }}
            />
          </div>
          <button type="button" className={tinyBtn} onClick={() => executeCommand('open youtube')} title="Open YouTube">
            YT
          </button>
          <button type="button" className={tinyBtn} onClick={() => executeCommand('play music')} title="Play music">
            ♪
          </button>
          <button type="button" className={tinyBtn} onClick={() => executeCommand('open spotify')} title="Open Spotify (honest if missing)">
            SP
          </button>
        </div>
      </div>
    </footer>
  )
}
