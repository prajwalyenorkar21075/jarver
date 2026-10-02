import { useEffect, useState } from 'react'
import { useJarvisStore, playHudChirp } from '../../store/useJarvisStore'

interface NavItem {
  id: string
  label: string
  glyph: string
  views: string[]
  action: 'navigate' | 'coding' | 'browser'
}

const ITEMS: NavItem[] = [
  { id: 'home', label: 'HOME', glyph: '⌂', views: ['cad', 'dashboard'], action: 'navigate' },
  { id: 'project', label: 'PROJECT', glyph: '▤', views: ['project'], action: 'navigate' },
  { id: 'cad', label: 'CAD', glyph: '⬢', views: ['cad'], action: 'navigate' },
  { id: 'robotics', label: 'ROBOTICS', glyph: '🤖', views: ['robotics'], action: 'navigate' },
  { id: 'ai', label: 'AI', glyph: '◉', views: ['diagnostics', 'ai'], action: 'navigate' },
  { id: 'cybersecurity', label: 'CYBERSECURITY', glyph: '🛡', views: ['cybersecurity'], action: 'navigate' },
  { id: 'assetgraph', label: 'ASSET GRAPH', glyph: '◈', views: ['assetgraph'], action: 'navigate' },
  { id: 'industrial', label: 'INDUSTRIAL', glyph: '⚙', views: ['industrial'], action: 'navigate' },
  { id: 'maintenance', label: 'MAINTENANCE', glyph: '✚', views: ['maintenance'], action: 'navigate' },
  { id: 'twincell', label: 'TWIN + CELL', glyph: '⧉', views: ['twincell'], action: 'navigate' },
  { id: 'files', label: 'FILES', glyph: '🗀', views: [], action: 'coding' },
  { id: 'browser', label: 'BROWSER', glyph: '🌐', views: [], action: 'browser' },
  { id: 'memory', label: 'MEMORY', glyph: '☑', views: ['memory'], action: 'navigate' },
  { id: 'tools', label: 'TOOLS', glyph: '⚒', views: ['vision', 'image', 'document'], action: 'navigate' },
  { id: 'settings', label: 'SETTINGS', glyph: '⚙', views: ['settings'], action: 'navigate' },
]

export default function LeftSidebar() {
  const [activeView, setActiveView] = useState('cad')
  const [collapsed, setCollapsed] = useState(false)
  const toggleCodingMode = useJarvisStore((s) => s.toggleCodingMode)
  const isCodingMode = useJarvisStore((s) => s.isCodingMode)
  const openPanel = useJarvisStore((s) => s.openPanel)

  useEffect(() => {
    const onNavigate = (e: CustomEvent) => {
      setActiveView(String(e.detail?.view ?? 'cad'))
    }
    window.addEventListener('jarvis-navigate', onNavigate as EventListener)
    return () => window.removeEventListener('jarvis-navigate', onNavigate as EventListener)
  }, [])

  const handleItemClick = (it: NavItem) => {
    playHudChirp()
    if (it.action === 'navigate') {
      const view = it.id === 'home' ? 'cad' : it.id === 'ai' ? 'diagnostics' : it.id
      setActiveView(view)
      window.dispatchEvent(new CustomEvent('jarvis-navigate', { detail: { view } }))
    } else if (it.action === 'coding') {
      toggleCodingMode(true)
    } else if (it.action === 'browser') {
      openPanel(
        { type: 'search', title: 'J.A.R.V.I.S. CAD Browser & Standards', query: 'ISO engineering CAD standards' },
        'center'
      )
    }
  }

  const isActive = (it: NavItem) => {
    if (it.action === 'coding') return isCodingMode
    return it.views.includes(activeView)
  }

  return (
    <aside
      className={`relative z-20 flex flex-col shrink-0 border-r border-cyan-500/20 bg-[#030713] transition-all duration-200 select-none ${
        collapsed ? 'w-14' : 'w-48'
      }`}
    >
      {/* Sidebar Header with Collapse / Expand Toggle */}
      <div className="flex h-10 items-center justify-between border-b border-cyan-500/20 px-3">
        {!collapsed && (
          <span className="font-mono text-[10px] font-bold tracking-[0.25em] text-[#00e5ff]">
            NAVIGATION
          </span>
        )}
        <button
          type="button"
          onClick={() => {
            playHudChirp()
            setCollapsed(!collapsed)
          }}
          title={collapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
          className="cursor-pointer ml-auto rounded p-1 font-mono text-cyan-300 hover:bg-cyan-500/20 hover:text-white transition-colors"
        >
          {collapsed ? '»' : '«'}
        </button>
      </div>

      {/* Nav List */}
      <nav className="flex-1 overflow-y-auto py-2 px-1.5 space-y-1">
        {ITEMS.map((it) => {
          const active = isActive(it)
          return (
            <button
              key={it.id}
              type="button"
              onClick={() => handleItemClick(it)}
              title={collapsed ? it.label : undefined}
              className={`group flex w-full cursor-pointer items-center gap-2.5 rounded px-2.5 py-2 transition-all select-none active:scale-95 ${
                active
                  ? 'border-l-2 border-[#00e5ff] bg-[#00e5ff]/15 text-white font-bold'
                  : 'border-l-2 border-transparent text-cyan-100/60 hover:bg-[#071328] hover:text-[#00e5ff]'
              }`}
            >
              <span className={`font-mono text-[14px] leading-none shrink-0 ${active ? 'text-[#00e5ff]' : 'text-cyan-400/70 group-hover:text-[#00e5ff]'}`}>
                {it.glyph}
              </span>
              {!collapsed && (
                <span className={`font-mono text-[11px] tracking-wider truncate text-left ${active ? 'text-[#00e5ff]' : 'text-cyan-100/80 group-hover:text-white'}`}>
                  {it.label}
                </span>
              )}
            </button>
          )
        })}
      </nav>

      {/* Bottom Engineering Tag */}
      <div className="border-t border-cyan-500/20 p-2 text-center">
        {!collapsed ? (
          <div className="font-mono text-[9px] text-cyan-400/40 tracking-widest">
            STARK IND. CAD
          </div>
        ) : (
          <div className="font-mono text-[9px] text-[#00e5ff]">
            ⬢
          </div>
        )}
      </div>
    </aside>
  )
}
