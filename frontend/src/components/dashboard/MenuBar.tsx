import { useEffect, useRef, useState } from 'react'
import { useJarvisStore, speakJarvis } from '../../store/useJarvisStore'

type MenuId = 'file' | 'edit' | 'view' | 'create' | 'modify' | 'measure' | 'tools' | 'ai' | 'robotics' | 'security'

interface MenuItem {
  label: string
  action: () => void
  enabled?: boolean
  divider?: boolean
}

const PRIMITIVES: Array<{ label: string; path: string; query: string }> = [
  { label: 'Box (100×50×30)', path: 'box', query: 'width=100&height=50&depth=30' },
  { label: 'Cylinder (R20, H60)', path: 'cylinder', query: 'radius=20&height=60' },
  { label: 'Sphere (R25)', path: 'sphere', query: 'radius=25' },
  { label: 'Cone (R20, H50)', path: 'cone', query: 'radius=20&height=50' },
  { label: 'Torus (R30, r8)', path: 'torus', query: 'major_radius=30&minor_radius=8' },
]

export default function MenuBar() {
  const [openMenu, setOpenMenu] = useState<MenuId | null>(null)
  const [selectedFeature, setSelectedFeature] = useState<{ id: string; name: string } | null>(null)
  const barRef = useRef<HTMLDivElement>(null)

  const setSystemNotice = useJarvisStore((s) => s.setSystemNotice)
  const toggleCodingMode = useJarvisStore((s) => s.toggleCodingMode)
  const setBiometricsModalOpen = useJarvisStore((s) => s.setBiometricsModalOpen)

  useEffect(() => {
    const onSelected = (e: Event) => {
      const d = (e as CustomEvent).detail || {}
      setSelectedFeature(d.featureId ? { id: d.featureId, name: '' } : null)
    }
    const onTree = (e: Event) => {
      const d = (e as CustomEvent).detail || {}
      if (d.selectedName) setSelectedFeature((s) => (s ? { ...s, name: d.selectedName } : s))
    }
    window.addEventListener('jarvis-cad-selected', onSelected)
    window.addEventListener('jarvis-cad-selection-name', onTree)
    return () => {
      window.removeEventListener('jarvis-cad-selected', onSelected)
      window.removeEventListener('jarvis-cad-selection-name', onTree)
    }
  }, [])

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (barRef.current && !barRef.current.contains(e.target as Node)) setOpenMenu(null)
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [])

  const notify = (msg: string) => {
    setSystemNotice(msg)
    setTimeout(() => setSystemNotice(null), 4000)
  }

  const post = async (url: string, method = 'POST'): Promise<any> => {
    const res = await fetch(url, { method })
    const data = await res.json().catch(() => null)
    if (!res.ok || !data || data.success === false) {
      throw new Error(data?.detail || `Request failed (${res.status})`)
    }
    return data
  }

  const run = (fn: () => Promise<void>) => async () => {
    setOpenMenu(null)
    try {
      await fn()
    } catch (e: any) {
      notify(`CAD: ${e?.message || 'operation failed'}`)
    }
  }

  const navigate = (view: string) => {
    setOpenMenu(null)
    window.dispatchEvent(new CustomEvent('jarvis-navigate', { detail: { view } }))
  }

  const cadEvent = (name: string, detail?: any) => {
    setOpenMenu(null)
    window.dispatchEvent(new CustomEvent(name, { detail }))
  }

  const createPrimitive = (p: { label: string; path: string; query: string }) =>
    run(async () => {
      const data = await post(`/api/cad/primitive/${p.path}?${p.query}`)
      window.dispatchEvent(new CustomEvent('jarvis-cad-refresh', { detail: { featureId: data.feature_id } }))
      notify(`Created ${data.name} (${data.message})`)
    })

  const modifySelected = (path: 'fillet' | 'chamfer' | 'shell') => {
    if (!selectedFeature) {
      notify('Select an object in the viewport first')
      return
    }
    const params: Record<string, string> = {
      fillet: `radius=5`,
      chamfer: `distance=3`,
      shell: `thickness=2`,
    }
    run(async () => {
      const data = await post(
        `/api/cad/feature/${path}?feature_id=${selectedFeature.id}&${params[path]}`
      )
      window.dispatchEvent(new CustomEvent('jarvis-cad-refresh', { detail: { featureId: data.feature_id } }))
      notify(`${path.toUpperCase()}: ${data.message}`)
    })()
  }

  const measureSelected = (metric: 'volume' | 'surface-area' | 'bounding-box' | 'center-of-mass') => {
    if (!selectedFeature) {
      notify('Select an object in the viewport first')
      return
    }
    run(async () => {
      const data = await post(`/api/cad/measure/${metric}/${selectedFeature.id}`, 'GET')
      const msg =
        metric === 'volume'
          ? `Volume: ${data.volume.toFixed(2)} ${data.unit}`
          : metric === 'surface-area'
          ? `Surface area: ${data.surface_area.toFixed(2)} ${data.unit}`
          : metric === 'center-of-mass'
          ? `Center of mass: x=${data.center_of_mass.x.toFixed(1)} y=${data.center_of_mass.y.toFixed(1)} z=${data.center_of_mass.z.toFixed(1)} mm`
          : `Bounding box: ${data.bounding_box.width.toFixed(1)} × ${data.bounding_box.height.toFixed(1)} × ${data.bounding_box.depth.toFixed(1)} mm`
      notify(`MEASURE — ${msg}`)
      speakJarvis(msg)
    })()
  }

  const menus: Record<MenuId, MenuItem[]> = {
    file: [
      {
        label: 'New Document',
        action: run(async () => {
          const name = window.prompt('New document name', 'Project') || 'Project'
          const data = await post(`/api/cad/document/new?name=${encodeURIComponent(name)}`)
          window.dispatchEvent(new CustomEvent('jarvis-cad-refresh', { detail: { featureId: null } }))
          notify(`Document created: ${data.document?.name ?? name}`)
        }),
      },
      {
        label: 'Save Document',
        action: run(async () => {
          const path = window.prompt('Save path (.jarviscad)', 'model.jarviscad') || 'model.jarviscad'
          const data = await post(`/api/cad/document/save?file_path=${encodeURIComponent(path)}`)
          notify(`Saved: ${data.file_path ?? path}`)
        }),
      },
      {
        label: 'Load Document',
        action: run(async () => {
          const path = window.prompt('Load path (.jarviscad)')
          if (!path) return
          await post(`/api/cad/document/load?file_path=${encodeURIComponent(path)}`)
          window.dispatchEvent(new CustomEvent('jarvis-cad-refresh', { detail: { featureId: null } }))
          notify(`Loaded ${path}`)
        }),
      },
      { divider: true, label: '' } as any,
      {
        label: 'Export STL (selection)',
        enabled: !!selectedFeature,
        action: run(async () => {
          const path = window.prompt('STL export path', `${selectedFeature!.id}.stl`) || 'export.stl'
          await post(`/api/cad/export/stl/${selectedFeature!.id}?file_path=${encodeURIComponent(path)}`)
          notify(`Exported STL → ${path}`)
        }),
      },
      {
        label: 'Export STEP (selection)',
        enabled: !!selectedFeature,
        action: run(async () => {
          const path = window.prompt('STEP export path', `${selectedFeature!.id}.step`) || 'export.step'
          await post(`/api/cad/export/step/${selectedFeature!.id}?file_path=${encodeURIComponent(path)}`)
          notify(`Exported STEP → ${path}`)
        }),
      },
      {
        label: 'Import STL',
        action: run(async () => {
          const path = window.prompt('STL file path to import')
          if (!path) return
          await post(`/api/cad/import/stl?file_path=${encodeURIComponent(path)}`)
          window.dispatchEvent(new CustomEvent('jarvis-cad-refresh', {}))
          notify(`Imported STL ${path}`)
        }),
      },
      {
        label: 'Import STEP',
        action: run(async () => {
          const path = window.prompt('STEP file path to import')
          if (!path) return
          await post(`/api/cad/import/step?file_path=${encodeURIComponent(path)}`)
          window.dispatchEvent(new CustomEvent('jarvis-cad-refresh', {}))
          notify(`Imported STEP ${path}`)
        }),
      },
    ],
    edit: [
      {
        label: 'Undo',
        action: run(async () => {
          await post('/api/cad/undo')
          window.dispatchEvent(new CustomEvent('jarvis-cad-refresh', { detail: { featureId: null } }))
          notify('Undo applied')
        }),
      },
      {
        label: 'Redo',
        action: run(async () => {
          await post('/api/cad/redo')
          window.dispatchEvent(new CustomEvent('jarvis-cad-refresh', { detail: { featureId: null } }))
          notify('Redo applied')
        }),
      },
      {
        label: 'Delete Selected',
        enabled: !!selectedFeature,
        action: () => cadEvent('jarvis-cad-delete'),
      },
      {
        label: 'Edit Parameters…',
        enabled: !!selectedFeature,
        action: () => {
          cadEvent('jarvis-cad-focus')
          notify('Use the INSPECTOR panel on the right to edit name, visibility and parameters')
        },
      },
    ],
    view: [
      { label: 'Isometric', action: () => cadEvent('jarvis-cad-view', { preset: 'iso' }) },
      { label: 'Front', action: () => cadEvent('jarvis-cad-view', { preset: 'front' }) },
      { label: 'Back', action: () => cadEvent('jarvis-cad-view', { preset: 'back' }) },
      { label: 'Left', action: () => cadEvent('jarvis-cad-view', { preset: 'left' }) },
      { label: 'Right', action: () => cadEvent('jarvis-cad-view', { preset: 'right' }) },
      { label: 'Top', action: () => cadEvent('jarvis-cad-view', { preset: 'top' }) },
      { label: 'Bottom', action: () => cadEvent('jarvis-cad-view', { preset: 'bottom' }) },
      { label: 'Fit to Model', action: () => cadEvent('jarvis-cad-view', { preset: 'fit' }) },
      { divider: true, label: '' } as any,
      { label: 'Toggle Grid', action: () => cadEvent('jarvis-cad-toggle', { target: 'grid' }) },
      { label: 'Toggle Axes', action: () => cadEvent('jarvis-cad-toggle', { target: 'axes' }) },
      { label: 'Reload Model', action: () => cadEvent('jarvis-cad-refresh', {}) },
      { label: 'Engineering Workspace', action: () => navigate('cad') },
      { label: 'Reactor Dashboard', action: () => navigate('dashboard') },
    ],
    create: PRIMITIVES.map((p) => ({ label: p.label, action: createPrimitive(p) })),
    modify: [
      { label: 'Fillet (r = 5 mm)', enabled: !!selectedFeature, action: () => modifySelected('fillet') },
      { label: 'Chamfer (d = 3 mm)', enabled: !!selectedFeature, action: () => modifySelected('chamfer') },
      { label: 'Shell (t = 2 mm)', enabled: !!selectedFeature, action: () => modifySelected('shell') },
    ],
    measure: [
      { label: 'Volume', enabled: !!selectedFeature, action: () => measureSelected('volume') },
      { label: 'Surface Area', enabled: !!selectedFeature, action: () => measureSelected('surface-area') },
      { label: 'Bounding Box', enabled: !!selectedFeature, action: () => measureSelected('bounding-box') },
      { label: 'Center of Mass', enabled: !!selectedFeature, action: () => measureSelected('center-of-mass') },
    ],
    tools: [
      { label: 'Code Workbench', action: () => { setOpenMenu(null); toggleCodingMode(true) } },
      { label: 'System Diagnostics', action: () => navigate('diagnostics') },
      {
        label: 'Open Browser Tab',
        action: () => {
          setOpenMenu(null)
          window.open('https://www.google.com', '_blank', 'noopener,noreferrer')
        },
      },
      { label: 'Vision Analysis', action: () => navigate('vision') },
      { label: 'Image Generation', action: () => navigate('image') },
      { label: 'Document Analysis', action: () => navigate('document') },
      { label: 'Web Search Console', action: () => navigate('search') },
    ],
    ai: [
      {
        label: 'Ask JARVIS (focus command console)',
        action: () => {
          setOpenMenu(null)
          const el = document.getElementById('jarvis-main-input') as HTMLInputElement | null
          el?.focus()
        },
      },
      {
        label: 'Test Voice Output',
        action: () => {
          setOpenMenu(null)
          speakJarvis('JARVIS voice subsystem online, sir.')
        },
      },
      { label: 'Autonomous Coding Agent', action: () => { setOpenMenu(null); toggleCodingMode(true) } },
      { label: 'AI Diagnostics', action: () => navigate('diagnostics') },
    ],
    robotics: [
      { label: 'Robotics Knowledge Console', action: () => navigate('robotics') },
      { label: 'Cybersecurity Operations', action: () => navigate('cybersecurity') },
    ],
    security: [
      { label: 'Cybersecurity Dashboard', action: () => navigate('cybersecurity') },
      { label: 'Biometric Security Console', action: () => { setOpenMenu(null); setBiometricsModalOpen(true) } },
      { label: 'System Diagnostics', action: () => navigate('diagnostics') },
    ],
  }

  const menuTitles: Array<[MenuId, string]> = [
    ['file', 'File'],
    ['edit', 'Edit'],
    ['view', 'View'],
    ['create', 'Create'],
    ['modify', 'Modify'],
    ['measure', 'Measure'],
    ['tools', 'Tools'],
    ['ai', 'AI'],
    ['robotics', 'Robotics'],
    ['security', 'Security'],
  ]

  return (
    <div
      ref={barRef}
      className="relative z-40 flex h-8 w-full shrink-0 items-center gap-0.5 overflow-x-auto border-b border-cyan-500/25 bg-[#030812] px-3 select-none"
    >
      {menuTitles.map(([id, title]) => (
        <div key={id} className="relative">
          <button
            type="button"
            onClick={() => setOpenMenu(openMenu === id ? null : id)}
            onMouseEnter={() => openMenu && setOpenMenu(id)}
            className={`cursor-pointer rounded px-2.5 py-1 font-mono text-[11px] tracking-wider transition-colors ${
              openMenu === id ? 'bg-[#00e5ff] text-black font-bold' : 'text-cyan-200/80 hover:bg-cyan-500/15 hover:text-white'
            }`}
          >
            {title}
          </button>
          {openMenu === id && (
            <div className="absolute left-0 top-full mt-0.5 min-w-[230px] rounded border border-cyan-500/40 bg-[#040a18] py-1 shadow-[0_8px_30px_rgba(0,0,0,0.7)]">
              {menus[id].map((item, i) =>
                (item as any).divider ? (
                  <div key={i} className="my-1 border-t border-cyan-500/20" />
                ) : (
                  <button
                    key={i}
                    type="button"
                    disabled={item.enabled === false}
                    onClick={item.action}
                    className={`block w-full px-3 py-1.5 text-left font-mono text-[11px] transition-colors ${
                      item.enabled === false
                        ? 'cursor-not-allowed text-white/25'
                        : 'cursor-pointer text-cyan-100 hover:bg-[#00e5ff]/15 hover:text-white'
                    }`}
                  >
                    {item.label}
                    {item.enabled === false && <span className="ml-2 text-[9px] text-white/30">— select an object first</span>}
                  </button>
                )
              )}
            </div>
          )}
        </div>
      ))}
      <div className="ml-auto flex items-center gap-2 pr-1 font-mono text-[10px] text-cyan-400/60">
        <span className="hidden xl:inline">SEL:</span>
        <span className={selectedFeature ? 'text-[#00e5ff]' : 'text-white/30'}>
          {selectedFeature ? selectedFeature.id.slice(0, 12) : 'none'}
        </span>
      </div>
    </div>
  )
}
