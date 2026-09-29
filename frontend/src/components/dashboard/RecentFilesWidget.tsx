type FileIconType = 'figma' | 'pdf' | 'code' | 'notes'

function FileIcon({ type }: { type: FileIconType }) {
  if (type === 'figma') {
    return (
      <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="currentColor">
        <polygon points="12,2 22,12 12,22 2,12" />
      </svg>
    )
  }
  if (type === 'pdf') {
    return (
      <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
        <line x1="10" y1="9" x2="8" y2="9" />
      </svg>
    )
  }
  if (type === 'code') {
    return (
      <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <polyline points="16 18 22 12 16 6" />
        <polyline points="8 6 2 12 8 18" />
      </svg>
    )
  }
  // notes
  return (
    <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="12" y1="17" x2="8" y2="17" />
    </svg>
  )
}

export default function RecentFilesWidget() {
  const files: { id: string; name: string; time: string; badgeColor: string; icon: FileIconType }[] = [
    {
      id: '1',
      name: 'Mark_VII_Schematics.fig',
      time: '2 hours ago',
      badgeColor: 'bg-cyan-500/20 text-[#00e5ff] border-cyan-400/50',
      icon: 'figma',
    },
    {
      id: '2',
      name: 'Flight_Telemetry.pdf',
      time: '5 hours ago',
      badgeColor: 'bg-blue-500/20 text-blue-300 border-blue-400/50',
      icon: 'pdf',
    },
    {
      id: '3',
      name: 'Jarvis_Core_Engine.py',
      time: '1 day ago',
      badgeColor: 'bg-cyan-500/20 text-[#00e5ff] border-cyan-400/50',
      icon: 'code',
    },
    {
      id: '4',
      name: 'Defense_Directives.md',
      time: '2 days ago',
      badgeColor: 'bg-sky-500/20 text-sky-300 border-sky-400/50',
      icon: 'notes',
    },
  ]

  return (
    <div className="relative rounded-2xl border border-cyan-500/40 bg-[#040a18]/95 p-4 transition-all hover:border-[#00e5ff]/70 shadow-[0_0_15px_rgba(0,229,255,0.06)] w-full max-w-[320px]">
      {/* Header */}
      <div className="flex items-center justify-between text-xs font-mono">
        <div className="flex items-center gap-1.5 text-white/95">
          <svg className="h-4 w-4 text-[#00e5ff]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
          </svg>
          <span className="font-semibold tracking-wider text-[#00e5ff]">RECENT FILES</span>
        </div>
        <span className="text-[10px] text-cyan-400/60 cursor-pointer hover:text-white">View All &gt;</span>
      </div>

      {/* File List in Navy Fill Cards */}
      <div className="mt-3.5 space-y-2 font-mono">
        {files.map((f) => (
          <div
            key={f.id}
            className="flex items-center justify-between rounded-xl bg-[#071530] border border-cyan-500/20 p-2 hover:border-[#00e5ff]/50 hover:bg-[#0a1e42] transition-colors cursor-pointer group"
          >
            <div className="flex items-center gap-2.5 truncate">
              <div
                className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border ${f.badgeColor}`}
              >
                <FileIcon type={f.icon} />
              </div>
              <div className="truncate">
                <div className="text-xs font-semibold text-white/95 group-hover:text-[#00e5ff] transition-colors truncate">
                  {f.name}
                </div>
                <div className="text-[10px] text-cyan-300/50">{f.time}</div>
              </div>
            </div>

            {/* Menu dots */}
            <span className="text-cyan-400/40 group-hover:text-[#00e5ff] px-1">•••</span>
          </div>
        ))}
      </div>
    </div>
  )
}
