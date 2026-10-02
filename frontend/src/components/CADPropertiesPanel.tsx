import { useState, useEffect } from 'react'

interface CADPropertiesPanelProps {
  featureId: string | null
  onFeatureUpdate: () => void
}

interface Measurements {
  volume?: number | null
  surfaceArea?: number | null
  centerOfMass?: { x: number; y: number; z: number } | null
  bbox?: { width: number; height: number; depth: number } | null
}

interface TransformData {
  position: { x: number; y: number; z: number }
  rotation: { x: number; y: number; z: number }
  scale: { x: number; y: number; z: number }
}

const sectionHeader =
  'flex items-center justify-between border-b border-cyan-500/20 bg-[#071328]/60 px-3 py-1.5 font-mono text-[10px] font-bold tracking-[0.2em] text-[#00e5ff]'
const row = 'flex items-center justify-between gap-2 py-1 px-3 border-b border-cyan-500/10'
const label = 'font-mono text-[10px] uppercase tracking-wider text-cyan-400/60'
const value = 'font-mono text-[11px] text-cyan-100 font-semibold'
const numInput =
  'w-16 rounded border border-cyan-500/30 bg-[#020610] px-1.5 py-0.5 font-mono text-[11px] text-right text-cyan-100 focus:border-[#00e5ff] focus:outline-none'
const field =
  'w-full rounded border border-cyan-500/30 bg-[#020610] px-2 py-1 font-mono text-[12px] text-cyan-100 focus:border-[#00e5ff] focus:outline-none'
const miniBtn =
  'cursor-pointer rounded border border-cyan-500/40 bg-[#071530] px-2 py-1 font-mono text-[10px] font-bold text-cyan-300 transition-all hover:border-[#00e5ff] hover:text-white active:scale-95 disabled:cursor-not-allowed disabled:opacity-40'

const fmt = (n: number | undefined | null, unit: string) =>
  n === undefined || n === null || Number.isNaN(n)
    ? '—'
    : `${n.toLocaleString(undefined, { maximumFractionDigits: 2 })} ${unit}`

export function CADPropertiesPanel({ featureId, onFeatureUpdate }: CADPropertiesPanelProps) {
  const [feature, setFeature] = useState<any>(null)
  const [measurements, setMeasurements] = useState<Measurements>({})
  const [loading, setLoading] = useState(false)
  const [editing, setEditing] = useState(false)
  const [params, setParams] = useState<Record<string, any>>({})
  const [nameDraft, setNameDraft] = useState('')
  const [notice, setNotice] = useState<string | null>(null)
  const [layer, setLayer] = useState('Layer 0 (Default)')

  // Real 3D transform values from Three.js mesh
  const [transform, setTransform] = useState<TransformData>({
    position: { x: 0, y: 0, z: 0 },
    rotation: { x: 0, y: 0, z: 0 },
    scale: { x: 1, y: 1, z: 1 },
  })

  // Material state
  const [materialInfo, setMaterialInfo] = useState({
    type: 'MeshStandardMaterial',
    color: '#3f7fbf',
    metalness: 0.35,
    roughness: 0.55,
  })

  useEffect(() => {
    if (!featureId) {
      setFeature(null)
      setMeasurements({})
      setEditing(false)
      return
    }
    loadFeature()

    // Query 3D viewport for the selected mesh's live transforms
    window.dispatchEvent(
      new CustomEvent('jarvis-cad-request-transform', {
        detail: { featureId },
      })
    )
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [featureId])

  // Listen for transform updates from the 3D viewport
  useEffect(() => {
    const handleTransformUpdate = (e: Event) => {
      const detail = (e as CustomEvent).detail
      if (detail && detail.featureId === featureId) {
        if (detail.position) setTransform((t) => ({ ...t, position: { ...detail.position } }))
        if (detail.rotation) setTransform((t) => ({ ...t, rotation: { ...detail.rotation } }))
        if (detail.scale) setTransform((t) => ({ ...t, scale: { ...detail.scale } }))
        if (detail.material) setMaterialInfo((m) => ({ ...m, ...detail.material }))
      }
    }

    window.addEventListener('jarvis-cad-transform-synced', handleTransformUpdate)
    return () => window.removeEventListener('jarvis-cad-transform-synced', handleTransformUpdate)
  }, [featureId])

  const flash = (msg: string) => {
    setNotice(msg)
    setTimeout(() => setNotice(null), 2500)
  }

  const loadFeature = async () => {
    if (!featureId) return
    setLoading(true)
    setEditing(false)
    try {
      const response = await fetch(`/api/cad/feature/${featureId}`)
      const data = await response.json()
      if (data.success) {
        setFeature(data.feature)
        setNameDraft(data.feature.name)
        setParams(data.feature.parameters || {})
        setLayer(data.feature.parameters?.layer || 'Layer 0 (Default)')
      } else {
        setFeature(null)
      }
    } catch {
      setFeature(null)
      flash('Backend unreachable')
    }

    // Real measurements from the CAD engine
    try {
      const [vol, area, com, bbox] = await Promise.all([
        fetch(`/api/cad/measure/volume/${featureId}`).then((r) => (r.ok ? r.json() : null)),
        fetch(`/api/cad/measure/surface-area/${featureId}`).then((r) => (r.ok ? r.json() : null)),
        fetch(`/api/cad/measure/center-of-mass/${featureId}`).then((r) => (r.ok ? r.json() : null)),
        fetch(`/api/cad/measure/bounding-box/${featureId}`).then((r) => (r.ok ? r.json() : null)),
      ])
      setMeasurements({
        volume: vol?.success ? vol.volume : null,
        surfaceArea: area?.success ? area.surface_area : null,
        centerOfMass: com?.success ? com.center_of_mass : null,
        bbox: bbox?.success
          ? {
              width: bbox.bounding_box.width,
              height: bbox.bounding_box.height,
              depth: bbox.bounding_box.depth,
            }
          : null,
      })
    } catch {
      setMeasurements({})
    }
    setLoading(false)
  }

  const handleTransformChange = (
    category: 'position' | 'rotation' | 'scale',
    axis: 'x' | 'y' | 'z',
    val: number
  ) => {
    const updated = {
      ...transform,
      [category]: {
        ...transform[category],
        [axis]: val,
      },
    }
    setTransform(updated)
    // Send to 3D viewport to mutate live mesh
    window.dispatchEvent(
      new CustomEvent('jarvis-cad-apply-transform', {
        detail: {
          featureId,
          transform: updated,
        },
      })
    )
  }

  const handleLayerChange = async (nextLayer: string) => {
    if (!featureId || !feature) return
    setLayer(nextLayer)
    try {
      const merged = { ...(feature.parameters || {}), layer: nextLayer }
      const res = await fetch(`/api/cad/feature/${featureId}/parameters`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(merged),
      })
      if (res.ok) {
        flash(`Layer "${nextLayer}" stored on feature`)
        onFeatureUpdate()
      } else {
        flash('Layer not stored: backend rejected')
      }
    } catch {
      flash('Layer not stored: backend unreachable')
    }
  }

  const handleSaveParams = async () => {
    if (!featureId) return
    setLoading(true)
    try {
      const res = await fetch(`/api/cad/feature/${featureId}/parameters`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
      })
      if (res.ok) {
        setEditing(false)
        onFeatureUpdate()
        await loadFeature()
        flash('Parameters applied')
      } else {
        flash('Backend rejected parameter change')
      }
    } catch {
      flash('Backend unreachable')
    }
    setLoading(false)
  }

  const commitRename = async () => {
    if (!featureId || !nameDraft.trim() || nameDraft === feature.name) {
      setNameDraft(feature?.name || '')
      return
    }
    setLoading(true)
    try {
      const res = await fetch(
        `/api/cad/feature/${featureId}/rename?new_name=${encodeURIComponent(nameDraft.trim())}`,
        { method: 'PUT' }
      )
      if (res.ok) {
        onFeatureUpdate()
        await loadFeature()
      } else {
        flash('Rename failed')
      }
    } catch {
      flash('Backend unreachable')
    }
    setLoading(false)
  }

  const handleToggleVisibility = async () => {
    if (!featureId || !feature) return
    setLoading(true)
    try {
      await fetch(`/api/cad/feature/${featureId}/visibility?visible=${!feature.visible}`, {
        method: 'PUT',
      })
      onFeatureUpdate()
      await loadFeature()
    } catch {
      flash('Backend unreachable')
    }
    setLoading(false)
  }

  // Dimension extraction from parameters or measurements
  const pType = feature?.parameters?.primitive_type || feature?.type || '—'
  const widthVal =
    params.width ?? measurements.bbox?.width ?? (params.radius ? params.radius * 2 : null)
  const heightVal = params.height ?? measurements.bbox?.height ?? null
  const depthVal =
    params.depth ?? measurements.bbox?.depth ?? (params.radius ? params.radius * 2 : null)
  const radiusVal = params.radius ?? (params.major_radius ? params.major_radius : null)

  return (
    <div className="flex h-full flex-col bg-[#040916] text-white select-none">
      {/* Inspector Header */}
      <div className="flex items-center justify-between border-b border-cyan-500/25 bg-[#061124] px-3 py-2">
        <span className="font-mono text-[11px] font-bold tracking-[0.25em] text-[#00e5ff]">
          PROPERTIES
        </span>
        {notice && <span className="font-mono text-[9px] text-amber-300 animate-pulse">{notice}</span>}
      </div>

      <div className="flex-1 overflow-y-auto">
        {!featureId && (
          <div className="px-4 py-8 font-mono text-[11px] leading-relaxed text-cyan-300/50 text-center">
            No object selected.
            <br />
            <span className="text-[10px] text-cyan-400/40">
              Pick a 3D object in the viewport or double-click in the model tree.
            </span>
          </div>
        )}

        {featureId && loading && !feature && (
          <div className="px-4 py-6 font-mono text-[11px] text-cyan-300/50">Reading feature...</div>
        )}

        {featureId && feature && (
          <>
            {/* 1. GENERAL PROPERTIES */}
            <div className={sectionHeader}>
              <span>GENERAL</span>
              <span className="text-[9px] text-cyan-400/50">{feature.id.slice(0, 8)}</span>
            </div>

            <div className="p-3 border-b border-cyan-500/10 space-y-2">
              <div>
                <div className={label}>Name</div>
                <input
                  className={field}
                  type="text"
                  value={nameDraft}
                  onChange={(e) => setNameDraft(e.target.value)}
                  onBlur={commitRename}
                  onKeyDown={(e) => e.key === 'Enter' && (e.target as HTMLInputElement).blur()}
                />
              </div>
            </div>

            <div className={row}>
              <span className={label}>Type</span>
              <span className={value}>{String(pType).toUpperCase()}</span>
            </div>

            <div className={row}>
              <span className={label}>Layer</span>
              <select
                className="bg-[#020610] text-[11px] font-mono text-cyan-200 border border-cyan-500/30 rounded px-1.5 py-0.5 focus:outline-none"
                value={layer}
                onChange={(e) => handleLayerChange(e.target.value)}
              >
                <option>Layer 0 (Default)</option>
                <option>Mechanical (Machined)</option>
                <option>Construction (Guide)</option>
                <option>Aero Detail (J.A.R.V.I.S.)</option>
              </select>
            </div>

            <div className={row}>
              <span className={label}>Visibility</span>
              <button
                type="button"
                onClick={handleToggleVisibility}
                disabled={loading}
                className={`rounded px-2 py-0.5 font-mono text-[10px] font-bold transition-all ${
                  feature.visible
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                    : 'bg-rose-500/20 text-rose-400 border border-rose-500/40'
                }`}
              >
                {feature.visible ? 'VISIBLE' : 'HIDDEN'}
              </button>
            </div>

            {/* 2. REAL 3D TRANSFORMS (Position, Rotation, Scale) */}
            <div className={sectionHeader}>
              <span>TRANSFORMS</span>
              <span className="text-[9px] text-cyan-400/50">LOCAL COORD</span>
            </div>

            {/* Position X, Y, Z */}
            <div className="px-3 py-2 border-b border-cyan-500/10">
              <div className="flex items-center justify-between mb-1">
                <span className={label}>Position (mm)</span>
              </div>
              <div className="flex items-center gap-1.5">
                {(['x', 'y', 'z'] as const).map((axis) => (
                  <div key={axis} className="flex-1 flex items-center gap-1 bg-[#020610] border border-cyan-500/20 rounded px-1.5 py-0.5">
                    <span className="font-mono text-[9px] font-bold text-cyan-400 uppercase">{axis}</span>
                    <input
                      type="number"
                      step="1"
                      className="w-full bg-transparent font-mono text-[11px] text-right text-white focus:outline-none"
                      value={Math.round(transform.position[axis] * 10) / 10}
                      onChange={(e) =>
                        handleTransformChange('position', axis, parseFloat(e.target.value) || 0)
                      }
                    />
                  </div>
                ))}
              </div>
            </div>

            {/* Rotation X, Y, Z */}
            <div className="px-3 py-2 border-b border-cyan-500/10">
              <div className="flex items-center justify-between mb-1">
                <span className={label}>Rotation (deg)</span>
              </div>
              <div className="flex items-center gap-1.5">
                {(['x', 'y', 'z'] as const).map((axis) => (
                  <div key={axis} className="flex-1 flex items-center gap-1 bg-[#020610] border border-cyan-500/20 rounded px-1.5 py-0.5">
                    <span className="font-mono text-[9px] font-bold text-amber-400 uppercase">{axis}</span>
                    <input
                      type="number"
                      step="5"
                      className="w-full bg-transparent font-mono text-[11px] text-right text-white focus:outline-none"
                      value={Math.round(transform.rotation[axis])}
                      onChange={(e) =>
                        handleTransformChange('rotation', axis, parseFloat(e.target.value) || 0)
                      }
                    />
                  </div>
                ))}
              </div>
            </div>

            {/* Scale X, Y, Z */}
            <div className="px-3 py-2 border-b border-cyan-500/10">
              <div className="flex items-center justify-between mb-1">
                <span className={label}>Scale</span>
              </div>
              <div className="flex items-center gap-1.5">
                {(['x', 'y', 'z'] as const).map((axis) => (
                  <div key={axis} className="flex-1 flex items-center gap-1 bg-[#020610] border border-cyan-500/20 rounded px-1.5 py-0.5">
                    <span className="font-mono text-[9px] font-bold text-emerald-400 uppercase">{axis}</span>
                    <input
                      type="number"
                      step="0.1"
                      className="w-full bg-transparent font-mono text-[11px] text-right text-white focus:outline-none"
                      value={Math.round(transform.scale[axis] * 100) / 100}
                      onChange={(e) =>
                        handleTransformChange('scale', axis, parseFloat(e.target.value) || 1)
                      }
                    />
                  </div>
                ))}
              </div>
            </div>

            {/* 3. DIMENSIONS & GEOMETRY */}
            <div className={sectionHeader}>
              <span>DIMENSIONS</span>
              <span className="text-[9px] text-cyan-400/50">PARAMETRIC</span>
            </div>

            {widthVal != null && (
              <div className={row}>
                <span className={label}>Width</span>
                <span className={value}>{fmt(widthVal, 'mm')}</span>
              </div>
            )}
            {heightVal != null && (
              <div className={row}>
                <span className={label}>Height</span>
                <span className={value}>{fmt(heightVal, 'mm')}</span>
              </div>
            )}
            {depthVal != null && (
              <div className={row}>
                <span className={label}>Depth</span>
                <span className={value}>{fmt(depthVal, 'mm')}</span>
              </div>
            )}
            {radiusVal != null && (
              <div className={row}>
                <span className={label}>Radius</span>
                <span className={value}>{fmt(radiusVal, 'mm')}</span>
              </div>
            )}

            {/* 4. MATERIAL SPECIFICATION */}
            <div className={sectionHeader}>
              <span>MATERIAL</span>
              <span className="text-[9px] text-cyan-400/50">PBR SHADER</span>
            </div>

            <div className={row}>
              <span className={label}>Shader</span>
              <span className={value}>{materialInfo.type}</span>
            </div>
            <div className={row}>
              <span className={label}>Color</span>
              <div className="flex items-center gap-2">
                <span
                  className="h-3 w-5 rounded border border-white/40"
                  style={{ backgroundColor: materialInfo.color }}
                />
                <span className={value}>{materialInfo.color.toUpperCase()}</span>
              </div>
            </div>
            <div className={row}>
              <span className={label}>Metalness</span>
              <span className={value}>{materialInfo.metalness.toFixed(2)}</span>
            </div>
            <div className={row}>
              <span className={label}>Roughness</span>
              <span className={value}>{materialInfo.roughness.toFixed(2)}</span>
            </div>

            {/* 5. MEASUREMENTS & CAD ENGINE METRICS */}
            <div className={sectionHeader}>
              <span>ENGINEERING METRICS</span>
              <span className="text-[9px] text-cyan-400/50">EXACT</span>
            </div>

            {measurements.volume != null && (
              <div className={row}>
                <span className={label}>Volume</span>
                <span className={value}>{fmt(measurements.volume, 'mm³')}</span>
              </div>
            )}
            {measurements.surfaceArea != null && (
              <div className={row}>
                <span className={label}>Surface area</span>
                <span className={value}>{fmt(measurements.surfaceArea, 'mm²')}</span>
              </div>
            )}
            {measurements.bbox && (
              <div className={row}>
                <span className={label}>Bounding box</span>
                <span className={value}>
                  {fmt(measurements.bbox.width, '×')} {fmt(measurements.bbox.height, '×')}{' '}
                  {fmt(measurements.bbox.depth, 'mm')}
                </span>
              </div>
            )}
            {measurements.centerOfMass && (
              <div className={row}>
                <span className={label}>Center of Mass</span>
                <span className={value}>
                  X:{measurements.centerOfMass.x.toFixed(1)} Y:{measurements.centerOfMass.y.toFixed(1)} Z:
                  {measurements.centerOfMass.z.toFixed(1)}
                </span>
              </div>
            )}

            {/* 6. EDITABLE FEATURE PARAMETERS */}
            <div className={sectionHeader}>
              <span>PARAMETERS</span>
              <button
                type="button"
                className={miniBtn}
                onClick={editing ? handleSaveParams : () => setEditing(true)}
                disabled={loading}
              >
                {editing ? 'APPLY' : 'EDIT'}
              </button>
            </div>

            <div className="p-3 space-y-2">
              {Object.entries(params).map(([key, val]) => (
                <div key={key} className="flex items-center justify-between gap-2">
                  <span className={label}>{key}</span>
                  {editing ? (
                    <input
                      className={numInput}
                      type={typeof val === 'number' ? 'number' : 'text'}
                      value={val}
                      step="any"
                      onChange={(e) =>
                        setParams({
                          ...params,
                          [key]:
                            typeof val === 'number'
                              ? parseFloat(e.target.value) || 0
                              : e.target.value,
                        })
                      }
                    />
                  ) : (
                    <span className={value}>{String(val)}</span>
                  )}
                </div>
              ))}
              {editing && (
                <button
                  type="button"
                  className={`${miniBtn} w-full mt-2`}
                  onClick={() => setEditing(false)}
                  disabled={loading}
                >
                  CANCEL
                </button>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
