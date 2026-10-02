import { useState, useEffect } from 'react'
import { useJarvisStore } from '../../store/useJarvisStore'

interface WorkspaceItem {
  name: string
  is_dir: boolean
  size_kb: number | null
}

export default function RecentFilesWidget() {
  const executeCommand = useJarvisStore((s) => s.executeCommand)
  const [items, setItems] = useState<WorkspaceItem[]>([])
  const [status, setStatus] = useState<'loading' | 'ok' | 'unavailable'>('loading')

  useEffect(() => {
    let cancelled = false
    fetch('/api/system/files', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'list' }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (cancelled) return
        if (data.items && Array.isArray(data.items)) {
          setItems(data.items.slice(0, 5))
          setStatus('ok')
        } else {
          setStatus('unavailable')
        }
      })
      .catch(() => {
        if (!cancelled) setStatus('unavailable')
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="relative rounded-2xl border border-cyan-500/40 bg-[#040a18]/95 p-4 transition-all hover:border-[#00e5ff]/70 shadow-[0_0_15px_rgba(0,229,255,0.06)] w-full max-w-[320px]">
      {/* Header */}
      <div className="flex items-center justify-between text-xs font-mono">
        <div className="flex items-center gap-1.5 text-white/95">
          <svg className="h-4 w-4 text-[#00e5ff]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
          </svg>
          <span className="font-semibold tracking-wider text-[#00e5ff]">WORKSPACE FILES</span>
        </div>
        <span
          onClick={() => executeCommand('list files')}
          className="text-[10px] text-cyan-400/60 cursor-pointer hover:text-white"
          title="List all files in workspace sandbox"
        >
          View All &gt;
        </span>
      </div>

      {/* File List in Navy Fill Cards */}
      <div className="mt-3.5 space-y-2 font-mono">
        {status !== 'ok' && (
          <div className="rounded-xl bg-[#071530] border border-cyan-500/20 p-3 text-xs text-white/50">
            {status === 'loading' ? 'Reading workspace…' : 'Workspace listing unavailable'}
          </div>
        )}
        {items.map((f) => (
          <div
            key={f.name}
            onClick={() => {
              if (f.is_dir) {
                executeCommand(`list files in ${f.name}`)
              } else {
                executeCommand(`read file ${f.name}`)
              }
            }}
            className="flex items-center justify-between rounded-xl bg-[#071530] border border-cyan-500/20 p-2 hover:border-[#00e5ff]/50 hover:bg-[#0a1e42] transition-colors cursor-pointer group"
            title={`Click to ${f.is_dir ? 'explore' : 'read'} with Jarvis`}
          >
            <div className="flex items-center gap-2.5 truncate">
              <div
                className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border ${
                  f.is_dir
                    ? 'bg-blue-500/20 text-blue-300 border-blue-400/50'
                    : 'bg-cyan-500/20 text-[#00e5ff] border-cyan-400/50'
                }`}
              >
                {f.is_dir ? (
                  <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
                  </svg>
                ) : (
                  <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="16 18 22 12 16 6" />
                    <polyline points="8 6 2 12 8 18" />
                  </svg>
                )}
              </div>
              <div className="truncate">
                <div className="text-xs font-semibold text-white/95 group-hover:text-[#00e5ff] transition-colors truncate">
                  {f.name}
                </div>
                <div className="text-[10px] text-cyan-300/50">
                  {f.is_dir ? 'Directory' : f.size_kb ? `${f.size_kb} KB` : 'File'}
                </div>
              </div>
            </div>

            {/* Read action pill */}
            <span className="text-[10px] text-cyan-400/60 group-hover:text-[#00e5ff] group-hover:underline px-1">
              {f.is_dir ? 'OPEN' : 'READ'}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
