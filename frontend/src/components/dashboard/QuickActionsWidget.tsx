import { useJarvisStore } from '../../store/useJarvisStore'

export default function QuickActionsWidget() {
  const openPanel = useJarvisStore((s) => s.openPanel)

  return (
    <div className="relative rounded-2xl border border-cyan-500/40 bg-[#040a18]/95 p-4 transition-all hover:border-[#00e5ff]/70 shadow-[0_0_15px_rgba(0,229,255,0.06)] w-full max-w-[320px]">
      {/* Header */}
      <div className="flex items-center justify-between text-xs font-mono text-white/95">
        <div className="flex items-center gap-1.5 text-[#00e5ff]">
          <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
            <path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z" />
          </svg>
          <span className="font-semibold tracking-wider text-[#00e5ff]">QUICK ACTIONS</span>
        </div>
        <span className="text-cyan-400/50 cursor-pointer hover:text-white">&gt;</span>
      </div>

      {/* 2x2 Grid with Solid Navy Fill & Laser Cyan Accents */}
      <div className="mt-3 grid grid-cols-2 gap-2.5 font-mono">
        {/* 1. Search Web */}
        <button
          type="button"
          onClick={() =>
            openPanel(
              {
                type: 'search',
                title: 'Aero-Wingjet Search',
                query: 'Iron Man Jarvis AI',
              },
              'center'
            )
          }
          className="group flex flex-col items-start rounded-xl border border-cyan-500/30 bg-[#071530] p-2.5 text-left hover:border-[#00e5ff] hover:bg-[#0a1e42] transition-all cursor-pointer shadow-[0_0_10px_rgba(0,229,255,0.05)]"
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-cyan-400/60 bg-cyan-500/20 text-[#00e5ff]">
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="2" y1="12" x2="22" y2="12" />
              <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
            </svg>
          </div>
          <div className="mt-2 text-xs font-semibold text-white group-hover:text-[#00e5ff] transition-colors">
            Search Web
          </div>
          <div className="text-[10px] text-cyan-300/60">Wingjet intel</div>
        </button>

        {/* 2. YouTube Streams */}
        <button
          type="button"
          onClick={() =>
            openPanel(
              {
                type: 'youtube',
                title: 'Jarvis Audio Stream',
                videoId: 'Ke1Y3P9D0Bc',
              },
              'docked-tr'
            )
          }
          className="group flex flex-col items-start rounded-xl border border-cyan-500/30 bg-[#071530] p-2.5 text-left hover:border-[#00e5ff] hover:bg-[#0a1e42] transition-all cursor-pointer shadow-[0_0_10px_rgba(0,229,255,0.05)]"
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-red-500/60 bg-red-500/20 text-red-400">
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
              <polygon points="5,3 19,12 5,21" />
            </svg>
          </div>
          <div className="mt-2 text-xs font-semibold text-white group-hover:text-[#00e5ff] transition-colors">
            Live Stream
          </div>
          <div className="text-[10px] text-cyan-300/60">Launch player</div>
        </button>

        {/* 3. Voice Instruction */}
        <button
          type="button"
          onClick={() => {
            const inputEl = document.getElementById('jarvis-main-input')
            inputEl?.focus()
          }}
          className="group flex flex-col items-start rounded-xl border border-cyan-500/30 bg-[#071530] p-2.5 text-left hover:border-[#00e5ff] hover:bg-[#0a1e42] transition-all cursor-pointer shadow-[0_0_10px_rgba(0,229,255,0.05)]"
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-blue-400/60 bg-blue-500/20 text-[#3b82f6]">
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" />
            </svg>
          </div>
          <div className="mt-2 text-xs font-semibold text-white group-hover:text-[#00e5ff] transition-colors">
            AI Directives
          </div>
          <div className="text-[10px] text-cyan-300/60">Type or speak</div>
        </button>

        {/* 4. Desktop Automation */}
        <button
          type="button"
          onClick={() =>
            openPanel(
              {
                type: 'search',
                title: 'Data Telemetry Analysis',
                query: 'System Analytics',
              },
              'center'
            )
          }
          className="group flex flex-col items-start rounded-xl border border-cyan-500/30 bg-[#071530] p-2.5 text-left hover:border-[#00e5ff] hover:bg-[#0a1e42] transition-all cursor-pointer shadow-[0_0_10px_rgba(0,229,255,0.05)]"
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-cyan-400/60 bg-cyan-500/20 text-[#00e5ff]">
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="20" x2="18" y2="10" />
              <line x1="12" y1="20" x2="12" y2="4" />
              <line x1="6" y1="20" x2="6" y2="14" />
            </svg>
          </div>
          <div className="mt-2 text-xs font-semibold text-white group-hover:text-[#00e5ff] transition-colors">
            Telemetry
          </div>
          <div className="text-[10px] text-cyan-300/60">System metrics</div>
        </button>
      </div>
    </div>
  )
}
