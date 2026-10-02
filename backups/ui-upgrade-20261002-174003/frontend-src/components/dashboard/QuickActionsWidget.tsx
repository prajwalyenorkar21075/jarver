import { useJarvisStore } from '../../store/useJarvisStore'

export default function QuickActionsWidget() {
  const openPanel = useJarvisStore((s) => s.openPanel)
  const executeCommand = useJarvisStore((s) => s.executeCommand)

  const navigateToView = (view: string) => {
    window.dispatchEvent(new CustomEvent('jarvis-navigate', { detail: { view } }))
  }

  return (
    <div className="relative rounded-2xl border border-cyan-500/40 bg-[#040a18]/95 p-4 transition-all hover:border-[#00e5ff]/70 shadow-[0_0_15px_rgba(0,229,255,0.06)] w-full max-w-[320px]">
      {/* Header */}
      <div className="flex items-center justify-between text-xs font-mono text-white/95">
        <div className="flex items-center gap-1.5 text-[#00e5ff]">
          <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
            <path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z" />
          </svg>
          <span className="font-semibold tracking-wider text-[#00e5ff]">SYSTEM DIRECTIVES</span>
        </div>
        <span className="text-[10px] text-cyan-400/60 font-mono">AUTOMATION</span>
      </div>

      {/* Feature Navigation */}
      <div className="mt-3 grid grid-cols-4 gap-1.5 font-mono">
        <button
          type="button"
          onClick={() => navigateToView('diagnostics')}
          className="flex flex-col items-center rounded-lg border border-cyan-500/30 bg-[#071530] p-2 text-center hover:border-[#00e5ff] hover:bg-[#0a1e42] transition-all cursor-pointer active:scale-95"
        >
          <div className="text-lg">🔍</div>
          <div className="text-[9px] text-cyan-300/80 mt-1">Diagnostics</div>
        </button>
        <button
          type="button"
          onClick={() => navigateToView('search')}
          className="flex flex-col items-center rounded-lg border border-cyan-500/30 bg-[#071530] p-2 text-center hover:border-[#00e5ff] hover:bg-[#0a1e42] transition-all cursor-pointer active:scale-95"
        >
          <div className="text-lg">🌐</div>
          <div className="text-[9px] text-cyan-300/80 mt-1">Web Search</div>
        </button>
        <button
          type="button"
          onClick={() => navigateToView('vision')}
          className="flex flex-col items-center rounded-lg border border-cyan-500/30 bg-[#071530] p-2 text-center hover:border-[#00e5ff] hover:bg-[#0a1e42] transition-all cursor-pointer active:scale-95"
        >
          <div className="text-lg">👁️</div>
          <div className="text-[9px] text-cyan-300/80 mt-1">Vision</div>
        </button>
        <button
          type="button"
          onClick={() => navigateToView('image')}
          className="flex flex-col items-center rounded-lg border border-cyan-500/30 bg-[#071530] p-2 text-center hover:border-[#00e5ff] hover:bg-[#0a1e42] transition-all cursor-pointer active:scale-95"
        >
          <div className="text-lg">🎨</div>
          <div className="text-[9px] text-cyan-300/80 mt-1">Image Gen</div>
        </button>
        <button
          type="button"
          onClick={() => navigateToView('document')}
          className="flex flex-col items-center rounded-lg border border-cyan-500/30 bg-[#071530] p-2 text-center hover:border-[#00e5ff] hover:bg-[#0a1e42] transition-all cursor-pointer active:scale-95"
        >
          <div className="text-lg">📄</div>
          <div className="text-[9px] text-cyan-300/80 mt-1">Doc Analysis</div>
        </button>
        <button
          type="button"
          onClick={() => navigateToView('cybersecurity')}
          className="flex flex-col items-center rounded-lg border border-cyan-500/30 bg-[#071530] p-2 text-center hover:border-[#00e5ff] hover:bg-[#0a1e42] transition-all cursor-pointer active:scale-95"
        >
          <div className="text-lg">🛡️</div>
          <div className="text-[9px] text-cyan-300/80 mt-1">Security</div>
        </button>
        <button
          type="button"
          onClick={() => navigateToView('cad')}
          className="flex flex-col items-center rounded-lg border border-cyan-500/30 bg-[#071530] p-2 text-center hover:border-[#00e5ff] hover:bg-[#0a1e42] transition-all cursor-pointer active:scale-95"
        >
          <div className="text-lg">📐</div>
          <div className="text-[9px] text-cyan-300/80 mt-1">CAD</div>
        </button>
        <button
          type="button"
          onClick={() => navigateToView('dashboard')}
          className="flex flex-col items-center rounded-lg border border-cyan-500/30 bg-[#071530] p-2 text-center hover:border-[#00e5ff] hover:bg-[#0a1e42] transition-all cursor-pointer active:scale-95"
        >
          <div className="text-lg">🏠</div>
          <div className="text-[9px] text-cyan-300/80 mt-1">Dashboard</div>
        </button>
      </div>

      {/* 2x2 Grid with Solid Navy Fill & Laser Cyan Accents */}
      <div className="mt-3 grid grid-cols-2 gap-2.5 font-mono">
        {/* 1. Camera Access */}
        <button
          type="button"
          onClick={() => executeCommand('open camera')}
          className="group flex flex-col items-start rounded-xl border border-cyan-500/30 bg-[#071530] p-2.5 text-left hover:border-[#00e5ff] hover:bg-[#0a1e42] transition-all cursor-pointer shadow-[0_0_10px_rgba(0,229,255,0.05)] active:scale-95"
          title="Launch Windows native Camera app"
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-cyan-400/60 bg-cyan-500/20 text-[#00e5ff]">
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
              <circle cx="12" cy="13" r="4" />
            </svg>
          </div>
          <div className="mt-2 text-xs font-semibold text-white group-hover:text-[#00e5ff] transition-colors">
            Camera Feed
          </div>
          <div className="text-[10px] text-cyan-300/60">Launch camera</div>
        </button>

        {/* 2. YouTube Streams / Play Song */}
        <button
          type="button"
          onClick={() => executeCommand('play a song')}
          className="group flex flex-col items-start rounded-xl border border-cyan-500/30 bg-[#071530] p-2.5 text-left hover:border-[#00e5ff] hover:bg-[#0a1e42] transition-all cursor-pointer shadow-[0_0_10px_rgba(0,229,255,0.05)] active:scale-95"
          title="Play YouTube music stream"
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-red-500/60 bg-red-500/20 text-red-400">
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
              <polygon points="5,3 19,12 5,21" />
            </svg>
          </div>
          <div className="mt-2 text-xs font-semibold text-white group-hover:text-[#00e5ff] transition-colors">
            Play Music
          </div>
          <div className="text-[10px] text-cyan-300/60">Audio stream</div>
        </button>

        {/* 3. Search Web */}
        <button
          type="button"
          onClick={() =>
            openPanel(
              {
                type: 'search',
                title: 'Jarvis Intelligence Web Search',
                query: 'Deep learning transformers architecture',
              },
              'center'
            )
          }
          className="group flex flex-col items-start rounded-xl border border-cyan-500/30 bg-[#071530] p-2.5 text-left hover:border-[#00e5ff] hover:bg-[#0a1e42] transition-all cursor-pointer shadow-[0_0_10px_rgba(0,229,255,0.05)] active:scale-95"
          title="Search the web"
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-blue-400/60 bg-blue-500/20 text-[#3b82f6]">
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="2" y1="12" x2="22" y2="12" />
              <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
            </svg>
          </div>
          <div className="mt-2 text-xs font-semibold text-white group-hover:text-[#00e5ff] transition-colors">
            Search Web
          </div>
          <div className="text-[10px] text-cyan-300/60">Global search</div>
        </button>

        {/* 4. Safe Workspace Files */}
        <button
          type="button"
          onClick={() => executeCommand('list workspace files')}
          className="group flex flex-col items-start rounded-xl border border-cyan-500/30 bg-[#071530] p-2.5 text-left hover:border-[#00e5ff] hover:bg-[#0a1e42] transition-all cursor-pointer shadow-[0_0_10px_rgba(0,229,255,0.05)] active:scale-95"
          title="List files in protected workspace"
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-cyan-400/60 bg-cyan-500/20 text-[#00e5ff]">
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
            </svg>
          </div>
          <div className="mt-2 text-xs font-semibold text-white group-hover:text-[#00e5ff] transition-colors">
            Safe Files
          </div>
          <div className="text-[10px] text-cyan-300/60">Workspace sandbox</div>
        </button>
      </div>

      {/* Multilingual Quick Directive Chips */}
      <div className="mt-3 flex flex-wrap gap-1.5 pt-2 border-t border-cyan-500/20 font-mono text-[10px]">
        <button
          type="button"
          onClick={() => executeCommand('माझा camera उघड')}
          className="cursor-pointer rounded-md border border-cyan-500/30 bg-[#071530] px-2 py-0.5 text-cyan-300 hover:border-cyan-400 hover:text-white transition-all active:scale-95"
        >
          📷 कॅमेरा उघड
        </button>
        <button
          type="button"
          onClick={() => executeCommand('एक गाना लाव')}
          className="cursor-pointer rounded-md border border-cyan-500/30 bg-[#071530] px-2 py-0.5 text-cyan-300 hover:border-cyan-400 hover:text-white transition-all active:scale-95"
        >
          🎵 एक गाना लाव
        </button>
        <button
          type="button"
          onClick={() => executeCommand('shutdown the PC')}
          className="cursor-pointer rounded-md border border-red-500/40 bg-red-950/40 px-2 py-0.5 text-red-300 hover:border-red-400 hover:text-white transition-all active:scale-95"
          title="Tests safety confirmation gate"
        >
          ⚠️ Shutdown PC
        </button>
      </div>
    </div>
  )
}
