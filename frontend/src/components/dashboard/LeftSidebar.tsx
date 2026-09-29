import { useState } from 'react'

interface NavItem {
  id: string
  label: string
  icon: (active: boolean) => React.ReactNode
}

export default function LeftSidebar() {
  const [activeTab, setActiveTab] = useState('home')

  const items: NavItem[] = [
    {
      id: 'home',
      label: 'Home',
      icon: (active) => (
        <svg className={`h-4 w-4 ${active ? 'text-white' : 'text-white/60'}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
          <polyline points="9 22 9 12 15 12 15 22" />
        </svg>
      ),
    },
    {
      id: 'chat',
      label: 'Chat',
      icon: (active) => (
        <svg className={`h-4 w-4 ${active ? 'text-white' : 'text-white/60'}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
      ),
    },
    {
      id: 'projects',
      label: 'Projects',
      icon: (active) => (
        <svg className={`h-4 w-4 ${active ? 'text-white' : 'text-white/60'}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
          <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
        </svg>
      ),
    },
    {
      id: 'apps',
      label: 'Apps',
      icon: (active) => (
        <svg className={`h-4 w-4 ${active ? 'text-white' : 'text-white/60'}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="3" y="3" width="7" height="7" />
          <rect x="14" y="3" width="7" height="7" />
          <rect x="14" y="14" width="7" height="7" />
          <rect x="3" y="14" width="7" height="7" />
        </svg>
      ),
    },
    {
      id: 'tools',
      label: 'Tools',
      icon: (active) => (
        <svg className={`h-4 w-4 ${active ? 'text-white' : 'text-white/60'}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
        </svg>
      ),
    },
    {
      id: 'files',
      label: 'Files',
      icon: (active) => (
        <svg className={`h-4 w-4 ${active ? 'text-white' : 'text-white/60'}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
          <polyline points="10 9 9 9 8 9" />
        </svg>
      ),
    },
  ]

  return (
    <aside className="fixed left-5 top-1/2 -translate-y-1/2 z-20 hidden lg:flex flex-col items-center gap-5 rounded-2xl border border-cyan-500/40 bg-[#040a18]/95 p-2 transition-all shadow-[0_0_20px_rgba(0,229,255,0.1)]">
      {items.map((it) => {
        const active = activeTab === it.id
        return (
          <button
            key={it.id}
            type="button"
            onClick={() => setActiveTab(it.id)}
            className="group flex flex-col items-center cursor-pointer transition-all"
            title={it.label}
          >
            {active ? (
              <div className="relative flex h-11 w-11 items-center justify-center">
                <svg className="absolute inset-0 h-full w-full" viewBox="0 0 44 44" fill="none">
                  <polygon
                    points="22,2 41,12 41,32 22,42 3,32 3,12"
                    fill="rgba(0, 229, 255, 0.2)"
                    stroke="#00e5ff"
                    strokeWidth="2"
                  />
                </svg>
                <div className="relative z-10 flex flex-col items-center text-[#00e5ff]">
                  {it.icon(true)}
                  <span className="text-[9px] font-mono font-bold text-[#00e5ff] mt-0.5">{it.label}</span>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center p-2 rounded-xl text-white/50 hover:text-[#00e5ff] hover:bg-[#071530] transition-all">
                {it.icon(false)}
                <span className="text-[9px] font-mono mt-1 opacity-70 group-hover:opacity-100 group-hover:text-cyan-300">{it.label}</span>
              </div>
            )}
          </button>
        )
      })}
    </aside>
  )
}
