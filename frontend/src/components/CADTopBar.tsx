import { useState, useEffect, useRef } from 'react'
import { useJarvisStore, playHudChirp } from '../store/useJarvisStore'

type WorkspaceMode = 'model' | 'sketch' | 'assembly' | 'drawing'

export default function CADTopBar() {
  const [workspace, setWorkspace] = useState<WorkspaceMode>('model')
  const [selectedFeature, setSelectedFeature] = useState<string | null>(null)
  const [activeTool, setActiveTool] = useState<'select' | 'move' | 'rotate' | 'scale'>('select')
  const [activeWorkplane, setActiveWorkplane] = useState('XY')
  const [gridSnap, setGridSnap] = useState(true)
  const [objSnap, setObjSnap] = useState(true)
  const [orthoMode, setOrthoMode] = useState(false)
  const barRef = useRef<HTMLDivElement>(null)

  const isListening = useJarvisStore((s) => s.isListening)
  const toggleListening = useJarvisStore((s) => s.toggleListening)
  const setSystemNotice = useJarvisStore((s) => s.setSystemNotice)

  useEffect(() => {
    const handleSelected = (e: Event) => {
      const id = (e as CustomEvent).detail?.featureId ?? null
      setSelectedFeature(id)
    }
    window.addEventListener('jarvis-cad-selected', handleSelected)
    return () => window.removeEventListener('jarvis-cad-selected', handleSelected)
  }, [])

  const notify = (msg: string) => {
    setSystemNotice(msg)
    setTimeout(() => setSystemNotice(null), 3500)
  }

  // Execute CAD command via the unified command engine
  const executeCadCommand = async (cmdText: string) => {
    playHudChirp()
    try {
      const res = await fetch('/api/cad/command/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: cmdText }),
      })
      const data = await res.json()
      if (res.ok && data.success) {
        window.dispatchEvent(
          new CustomEvent('jarvis-cad-refresh', {
            detail: { featureId: data.feature_id, context: data.context },
          })
        )
        notify(data.message || `Executed ${data.action}`)
      } else {
        notify(`CAD: ${data.message || data.detail || 'Execution failed'}`)
      }
    } catch {
      notify('CAD: Backend communication error')
    }
  }

  // Workspace Switcher
  const handleWorkspaceChange = async (ws: WorkspaceMode) => {
    setWorkspace(ws)
    playHudChirp()
    try {
      await fetch('/api/cad/context', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ workspace: ws }),
      })
    } catch {}
    notify(`Switched to ${ws.toUpperCase()} workspace`)
  }

  // Workplane Switcher
  const handleWorkplaneChange = async (wp: string) => {
    setActiveWorkplane(wp)
    playHudChirp()
    try {
      await fetch('/api/cad/context', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active_workplane: wp }),
      })
    } catch {}
    window.dispatchEvent(new CustomEvent('jarvis-cad-workplane', { detail: { workplane: wp } }))
    notify(`Active workplane: ${wp}`)
  }

  // Quick Primitive Handlers
  const handleCreateBox = () => executeCadCommand('create a box 100 by 60 by 20 mm')
  const handleCreateCylinder = () => executeCadCommand('create a cylinder radius 20 height 60 mm')
  const handleCreateSphere = () => executeCadCommand('create a sphere radius 25 mm')
  const handleCreateCone = () => executeCadCommand('create a cone radius 20 height 50 mm')
  const handleCreateTorus = () => executeCadCommand('create a torus major radius 30 minor radius 8 mm')

  // Feature Handlers
  const handleHole = () => {
    const dia = prompt('Enter hole diameter in mm:', '10')
    if (dia) executeCadCommand(`make a ${dia} mm hole at the center`)
  }

  const handleExtrude = () => {
    const dist = prompt('Enter extrusion distance in mm:', '30')
    if (dist) executeCadCommand(`extrude ${dist} mm`)
  }

  const handleRevolve = () => {
    const angle = prompt('Enter revolution angle in degrees:', '360')
    if (angle) executeCadCommand(`revolve ${angle} degrees`)
  }

  const handleFillet = () => {
    const r = prompt('Enter fillet radius in mm:', '5')
    if (r) executeCadCommand(`fillet radius ${r} mm`)
  }

  const handleChamfer = () => {
    const d = prompt('Enter chamfer distance in mm:', '3')
    if (d) executeCadCommand(`chamfer ${d} mm`)
  }

  const handleShell = () => {
    const t = prompt('Enter shell wall thickness in mm:', '2')
    if (t) executeCadCommand(`shell thickness ${t} mm`)
  }

  // Booleans
  const handleUnion = () => executeCadCommand('boolean union')
  const handleCut = () => executeCadCommand('boolean cut')
  const handleIntersect = () => executeCadCommand('boolean intersection')

  // Patterns & Mirror
  const handleCircularPattern = () => {
    const count = prompt('Enter number of circular pattern instances:', '6')
    if (count) executeCadCommand(`make ${count} equally spaced circular pattern`)
  }

  const handleLinearPattern = () => {
    const count = prompt('Enter number of linear pattern instances:', '4')
    if (count) executeCadCommand(`make ${count} linear pattern spacing 40 mm on X`)
  }

  const handleMirror = () => executeCadCommand('mirror across YZ plane')

  // Sketch Handlers
  const handleAddSketchLine = () => executeCadCommand('sketch line from 0,0 to 50,50')
  const handleAddSketchCircle = () => executeCadCommand('sketch circle radius 25 at 0,0')
  const handleAddSketchRect = () => executeCadCommand('sketch rectangle 60 by 40')
  const handleOffsetSketch = () => {
    const dist = prompt('Enter offset distance in mm:', '5')
    if (dist) executeCadCommand(`offset sketch ${dist} mm`)
  }

  // Transform tools
  const setToolMode = (mode: 'select' | 'move' | 'rotate' | 'scale') => {
    setActiveTool(mode)
    playHudChirp()
    window.dispatchEvent(new CustomEvent('jarvis-cad-tool', { detail: { mode } }))
  }

  const handleUndo = () => executeCadCommand('undo')
  const handleRedo = () => executeCadCommand('redo')
  const handleDelete = () => executeCadCommand('delete that')

  const handleFitView = () => {
    playHudChirp()
    window.dispatchEvent(new CustomEvent('jarvis-cad-view', { detail: { preset: 'fit' } }))
  }

  const handleIsoView = () => {
    playHudChirp()
    window.dispatchEvent(new CustomEvent('jarvis-cad-view', { detail: { preset: 'iso' } }))
  }

  const handleTopView = () => {
    playHudChirp()
    window.dispatchEvent(new CustomEvent('jarvis-cad-view', { detail: { preset: 'top' } }))
  }

  const handleFrontView = () => {
    playHudChirp()
    window.dispatchEvent(new CustomEvent('jarvis-cad-view', { detail: { preset: 'front' } }))
  }

  const handleMeasure = async () => {
    if (!selectedFeature) {
      notify('Select an object in the viewport first')
      return
    }
    executeCadCommand('measure bounding box')
  }

  // Export handlers
  const handleExportStl = async () => {
    if (!selectedFeature) {
      notify('Select a part to export')
      return
    }
    window.open(`/api/cad/export/stl/${selectedFeature}?file_path=model.stl`, '_blank')
    notify('Exporting STL…')
  }

  const handleExportStep = async () => {
    if (!selectedFeature) {
      notify('Select a part to export')
      return
    }
    window.open(`/api/cad/export/step/${selectedFeature}?file_path=model.step`, '_blank')
    notify('Exporting STEP…')
  }

  const btnClass = (active = false, danger = false) =>
    `cursor-pointer rounded px-2.5 py-1 font-mono text-[11px] font-bold tracking-wider transition-all select-none active:scale-95 disabled:cursor-not-allowed disabled:opacity-35 ${
      danger
        ? 'border border-rose-500/50 bg-[#1a060e] text-rose-300 hover:bg-rose-500/20'
        : active
        ? 'bg-[#00e5ff] text-black shadow-[0_0_10px_rgba(0,229,255,0.4)]'
        : 'border border-cyan-500/30 bg-[#071328] text-cyan-200 hover:border-[#00e5ff] hover:bg-[#00e5ff]/15 hover:text-white'
    }`

  const tabClass = (active: boolean) =>
    `cursor-pointer px-3 py-1 font-mono text-[11px] font-extrabold uppercase tracking-widest transition-all select-none border-b-2 ${
      active
        ? 'border-[#00e5ff] text-[#00e5ff] bg-[#00e5ff]/10'
        : 'border-transparent text-cyan-200/60 hover:text-cyan-100 hover:bg-cyan-500/10'
    }`

  return (
    <header
      ref={barRef}
      className="relative z-30 flex flex-col w-full border-b border-cyan-500/25 bg-[#030713] select-none shadow-md"
    >
      {/* 1. TOP BAR: Brand, Workspaces, Menus, Quick Actions, Audio Status */}
      <div className="flex h-10 items-center justify-between px-3 border-b border-cyan-500/15">
        <div className="flex items-center gap-3">
          {/* Brand Vector */}
          <div className="flex items-center gap-2 pr-3 border-r border-cyan-500/25">
            <svg className="h-5 w-5 text-[#00e5ff]" viewBox="0 0 40 40" fill="none">
              <polygon
                points="20,2 37,11 37,29 20,38 3,29 3,11"
                fill="#071530"
                stroke="currentColor"
                strokeWidth="2"
              />
              <circle cx="20" cy="20" r="4" fill="#00e5ff" />
            </svg>
            <span className="font-mono text-sm font-black tracking-[0.2em] text-white">
              J.A.R.V.I.S.<span className="text-[#00e5ff]">CAD</span>
            </span>
          </div>

          {/* Workspaces Tabs */}
          <nav className="flex items-center gap-1">
            <button
              type="button"
              className={tabClass(workspace === 'model')}
              onClick={() => handleWorkspaceChange('model')}
            >
              Part / Model
            </button>
            <button
              type="button"
              className={tabClass(workspace === 'sketch')}
              onClick={() => handleWorkspaceChange('sketch')}
            >
              Sketch 2D
            </button>
            <button
              type="button"
              className={tabClass(workspace === 'assembly')}
              onClick={() => handleWorkspaceChange('assembly')}
            >
              Assembly
            </button>
            <button
              type="button"
              className={tabClass(workspace === 'drawing')}
              onClick={() => handleWorkspaceChange('drawing')}
            >
              Drawing
            </button>
          </nav>
        </div>

        {/* Right Status & Controls */}
        <div className="flex items-center gap-2">
          {/* Workplane Selector */}
          <div className="flex items-center gap-1 bg-[#061022] border border-cyan-500/30 rounded px-1.5 py-0.5 font-mono text-[10px]">
            <span className="text-cyan-400/60 font-semibold">WP:</span>
            {['XY', 'XZ', 'YZ'].map((wp) => (
              <button
                key={wp}
                type="button"
                onClick={() => handleWorkplaneChange(wp)}
                className={`px-1 rounded ${
                  activeWorkplane === wp ? 'bg-[#00e5ff] text-black font-bold' : 'text-cyan-300 hover:text-white'
                }`}
              >
                {wp}
              </button>
            ))}
          </div>

          {/* Snapping Controls */}
          <div className="flex items-center gap-1 bg-[#061022] border border-cyan-500/30 rounded px-1.5 py-0.5 font-mono text-[10px]">
            <button
              type="button"
              onClick={() => {
                const next = !gridSnap
                setGridSnap(next)
                executeCadCommand(next ? 'enable grid snap' : 'disable grid snap')
              }}
              className={`px-1.5 py-0.5 rounded font-bold transition-colors ${
                gridSnap ? 'bg-cyan-500/20 text-[#00e5ff]' : 'text-cyan-400/40 hover:text-cyan-200'
              }`}
              title="Grid Snapping Toggle"
            >
              SNAP: {gridSnap ? 'ON' : 'OFF'}
            </button>
            <button
              type="button"
              onClick={() => {
                const next = !objSnap
                setObjSnap(next)
                executeCadCommand(next ? 'enable object snap' : 'disable object snap')
              }}
              className={`px-1.5 py-0.5 rounded font-bold transition-colors ${
                objSnap ? 'bg-cyan-500/20 text-[#00e5ff]' : 'text-cyan-400/40 hover:text-cyan-200'
              }`}
              title="Object Snap (OSNAP) Toggle"
            >
              OSNAP: {objSnap ? 'ON' : 'OFF'}
            </button>
            <button
              type="button"
              onClick={() => {
                const next = !orthoMode
                setOrthoMode(next)
                executeCadCommand(next ? 'enable ortho mode' : 'disable ortho mode')
              }}
              className={`px-1.5 py-0.5 rounded font-bold transition-colors ${
                orthoMode ? 'bg-cyan-500/20 text-[#00e5ff]' : 'text-cyan-400/40 hover:text-cyan-200'
              }`}
              title="Ortho Mode Toggle"
            >
              ORTHO: {orthoMode ? 'ON' : 'OFF'}
            </button>
          </div>

          {/* Undo / Redo */}
          <button type="button" className={btnClass(false)} onClick={handleUndo} title="Undo CAD operation">
            UNDO
          </button>
          <button type="button" className={btnClass(false)} onClick={handleRedo} title="Redo CAD operation">
            REDO
          </button>

          {/* Fit View */}
          <button type="button" className={btnClass(false)} onClick={handleFitView} title="Fit all objects into view">
            FIT
          </button>

          {/* Voice Indicator */}
          <button
            type="button"
            onClick={toggleListening}
            className={`flex items-center gap-1.5 rounded px-2.5 py-1 font-mono text-[10px] font-bold border transition-all ${
              isListening
                ? 'border-[#00e5ff] bg-[#00e5ff]/20 text-[#00e5ff] animate-pulse'
                : 'border-cyan-500/30 bg-[#071328] text-cyan-300 hover:border-cyan-400'
            }`}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${isListening ? 'bg-[#00e5ff]' : 'bg-cyan-500/50'}`} />
            <span>{isListening ? 'VOICE ON' : 'VOICE OFF'}</span>
          </button>
        </div>
      </div>

      {/* 2. RIBBON TOOLBAR: Dynamic Context-Aware CAD Engineering Tools */}
      <div className="flex h-10 items-center justify-between px-3 bg-[#02050f] overflow-x-auto">
        <div className="flex items-center gap-2">
          {/* Transform Selection Tools */}
          <div className="flex items-center gap-1 pr-2 border-r border-cyan-500/20">
            <button
              type="button"
              className={btnClass(activeTool === 'select')}
              onClick={() => setToolMode('select')}
              title="Select Objects"
            >
              SELECT
            </button>
            <button
              type="button"
              className={btnClass(activeTool === 'move')}
              onClick={() => setToolMode('move')}
              disabled={!selectedFeature}
              title="Move selected part"
            >
              MOVE
            </button>
            <button
              type="button"
              className={btnClass(activeTool === 'rotate')}
              onClick={() => setToolMode('rotate')}
              disabled={!selectedFeature}
              title="Rotate selected part"
            >
              ROTATE
            </button>
            <button
              type="button"
              className={btnClass(activeTool === 'scale')}
              onClick={() => setToolMode('scale')}
              disabled={!selectedFeature}
              title="Scale selected part"
            >
              SCALE
            </button>
          </div>

          {/* WORKSPACE-SPECIFIC TOOLS */}
          {workspace === 'model' && (
            <>
              {/* Primitives */}
              <div className="flex items-center gap-1 pr-2 border-r border-cyan-500/20">
                <span className="font-mono text-[9px] uppercase tracking-wider text-cyan-400/50">
                  SOLIDS:
                </span>
                <button type="button" className={btnClass(false)} onClick={handleCreateBox}>
                  BOX
                </button>
                <button type="button" className={btnClass(false)} onClick={handleCreateCylinder}>
                  CYLINDER
                </button>
                <button type="button" className={btnClass(false)} onClick={handleCreateSphere}>
                  SPHERE
                </button>
                <button type="button" className={btnClass(false)} onClick={handleCreateCone}>
                  CONE
                </button>
                <button type="button" className={btnClass(false)} onClick={handleCreateTorus}>
                  TORUS
                </button>
              </div>

              {/* 3D Features */}
              <div className="flex items-center gap-1 pr-2 border-r border-cyan-500/20">
                <span className="font-mono text-[9px] uppercase tracking-wider text-cyan-400/50">
                  FEATURES:
                </span>
                <button
                  type="button"
                  className={btnClass(false)}
                  onClick={handleHole}
                  disabled={!selectedFeature}
                  title="Make a hole in the selected part"
                >
                  HOLE
                </button>
                <button
                  type="button"
                  className={btnClass(false)}
                  onClick={handleFillet}
                  disabled={!selectedFeature}
                  title="Apply edge fillet"
                >
                  FILLET
                </button>
                <button
                  type="button"
                  className={btnClass(false)}
                  onClick={handleChamfer}
                  disabled={!selectedFeature}
                  title="Apply edge chamfer"
                >
                  CHAMFER
                </button>
                <button
                  type="button"
                  className={btnClass(false)}
                  onClick={handleShell}
                  disabled={!selectedFeature}
                  title="Hollow out part into a thin-walled shell"
                >
                  SHELL
                </button>
              </div>

              {/* Booleans */}
              <div className="flex items-center gap-1 pr-2 border-r border-cyan-500/20">
                <span className="font-mono text-[9px] uppercase tracking-wider text-cyan-400/50">
                  BOOLEANS:
                </span>
                <button type="button" className={btnClass(false)} onClick={handleUnion} title="Boolean Union">
                  UNION
                </button>
                <button type="button" className={btnClass(false)} onClick={handleCut} title="Boolean Cut">
                  CUT
                </button>
                <button type="button" className={btnClass(false)} onClick={handleIntersect} title="Boolean Intersection">
                  INTERSECT
                </button>
              </div>

              {/* Patterns & Mirror */}
              <div className="flex items-center gap-1 pr-2 border-r border-cyan-500/20">
                <span className="font-mono text-[9px] uppercase tracking-wider text-cyan-400/50">
                  PATTERNS:
                </span>
                <button
                  type="button"
                  className={btnClass(false)}
                  onClick={handleCircularPattern}
                  disabled={!selectedFeature}
                  title="Create circular polar array"
                >
                  CIRCULAR
                </button>
                <button
                  type="button"
                  className={btnClass(false)}
                  onClick={handleLinearPattern}
                  disabled={!selectedFeature}
                  title="Create linear array pattern"
                >
                  LINEAR
                </button>
                <button
                  type="button"
                  className={btnClass(false)}
                  onClick={handleMirror}
                  disabled={!selectedFeature}
                  title="Mirror part across workplane"
                >
                  MIRROR
                </button>
              </div>
            </>
          )}

          {workspace === 'sketch' && (
            <>
              {/* Sketch Entities */}
              <div className="flex items-center gap-1 pr-2 border-r border-cyan-500/20">
                <span className="font-mono text-[9px] uppercase tracking-wider text-cyan-400/50">
                  DRAW:
                </span>
                <button type="button" className={btnClass(false)} onClick={handleAddSketchLine}>
                  LINE
                </button>
                <button type="button" className={btnClass(false)} onClick={handleAddSketchRect}>
                  RECTANGLE
                </button>
                <button type="button" className={btnClass(false)} onClick={handleAddSketchCircle}>
                  CIRCLE
                </button>
                <button type="button" className={btnClass(false)} onClick={handleOffsetSketch}>
                  OFFSET
                </button>
              </div>

              {/* 3D Extrude / Revolve from active sketch */}
              <div className="flex items-center gap-1 pr-2 border-r border-cyan-500/20">
                <span className="font-mono text-[9px] uppercase tracking-wider text-cyan-400/50">
                  EXTRUDE:
                </span>
                <button type="button" className={btnClass(false)} onClick={handleExtrude}>
                  EXTRUDE 3D
                </button>
                <button type="button" className={btnClass(false)} onClick={handleRevolve}>
                  REVOLVE 360°
                </button>
              </div>
            </>
          )}

          {workspace === 'assembly' && (
            <div className="flex items-center gap-1 pr-2 border-r border-cyan-500/20">
              <span className="font-mono text-[9px] uppercase tracking-wider text-cyan-400/50">
                ASSEMBLY:
              </span>
              <button
                type="button"
                className={btnClass(false)}
                onClick={() => executeCadCommand('duplicate that')}
                disabled={!selectedFeature}
              >
                INSERT COMPONENT
              </button>
              <button
                type="button"
                className={btnClass(false)}
                onClick={() => executeCadCommand('move that to 0 0 0')}
                disabled={!selectedFeature}
              >
                ALIGN ORIGIN
              </button>
            </div>
          )}

          {workspace === 'drawing' && (
            <div className="flex items-center gap-1 pr-2 border-r border-cyan-500/20">
              <span className="font-mono text-[9px] uppercase tracking-wider text-cyan-400/50">
                VIEWS:
              </span>
              <button type="button" className={btnClass(false)} onClick={handleTopView}>
                TOP (2D)
              </button>
              <button type="button" className={btnClass(false)} onClick={handleFrontView}>
                FRONT (2D)
              </button>
              <button type="button" className={btnClass(false)} onClick={handleIsoView}>
                ISOMETRIC
              </button>
            </div>
          )}

          {/* Delete & Measure */}
          <div className="flex items-center gap-1">
            <button
              type="button"
              className={btnClass(false)}
              onClick={handleMeasure}
              disabled={!selectedFeature}
              title="Measure dimensions and volume"
            >
              MEASURE
            </button>
            <button
              type="button"
              className={btnClass(false, true)}
              onClick={handleDelete}
              disabled={!selectedFeature}
              title="Delete selected feature"
            >
              DELETE
            </button>
          </div>
        </div>

        {/* Export Dropdown / Actions */}
        <div className="flex items-center gap-1">
          <button
            type="button"
            className={btnClass(false)}
            onClick={handleExportStl}
            disabled={!selectedFeature}
            title="Download STL 3D Mesh"
          >
            EXPORT STL
          </button>
          <button
            type="button"
            className={btnClass(false)}
            onClick={handleExportStep}
            disabled={!selectedFeature}
            title="Download STEP CAD Model"
          >
            EXPORT STEP
          </button>
        </div>
      </div>
    </header>
  )
}
