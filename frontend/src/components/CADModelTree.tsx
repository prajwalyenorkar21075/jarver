interface CADModelTreeProps {
  tree: any
  selectedFeature: string | null
  onFeatureSelect: (featureId: string) => void
}

const typeIcon: Record<string, string> = {
  box: '▣',
  cylinder: '⬢',
  sphere: '◯',
  cone: '△',
  torus: '◎',
  extrude: '▲',
  revolve: '↺',
  hole: '⊚',
  fillet: '⌒',
  chamfer: '⊿',
  shell: '▢',
  boolean_cut: '✂',
  boolean_union: '∪',
  boolean_intersection: '∩',
  pattern_circular: '☷',
  pattern_linear: '☰',
  mirror: '⧉',
  sketch: '✎',
}

export function CADModelTree({ tree, selectedFeature, onFeatureSelect }: CADModelTreeProps) {
  const toggleVisibility = async (e: React.MouseEvent, feature: any) => {
    e.stopPropagation()
    const nextVis = !feature.visible
    try {
      await fetch(`/api/cad/feature/${feature.id}/parameters`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ visible: nextVis }),
      })
      window.dispatchEvent(new CustomEvent('jarvis-cad-refresh', {}))
    } catch {}
  }

  const handleDelete = async (e: React.MouseEvent, featureId: string) => {
    e.stopPropagation()
    try {
      await fetch(`/api/cad/feature/${featureId}`, { method: 'DELETE' })
      window.dispatchEvent(new CustomEvent('jarvis-cad-refresh', {}))
    } catch {}
  }

  const renderFeature = (feature: any, depth: number = 0) => {
    const isSelected = selectedFeature === feature.id
    const isDocument = feature.type === 'document'
    const ptype = feature.parameters?.primitive_type || feature.type
    const icon = typeIcon[ptype] || (feature.type === 'sketch' ? '✎' : '⚙')

    return (
      <div key={feature.id} className="group/item">
        <div
          onClick={() => !isDocument && onFeatureSelect(feature.id)}
          className={`flex items-center gap-1.5 border-l-2 py-1.5 pr-2 text-[11px] font-mono transition-colors ${
            isSelected
              ? 'border-[#00e5ff] bg-[#00e5ff]/20 text-white font-bold'
              : 'border-transparent text-cyan-100/75 hover:bg-cyan-500/10'
          } ${isDocument ? 'cursor-default font-mono text-[10px] tracking-[0.2em] text-cyan-400/80 uppercase' : 'cursor-pointer'}`}
          style={{ paddingLeft: 10 + depth * 12 }}
        >
          <span className={`text-[12px] ${isSelected ? 'text-[#00e5ff]' : 'text-cyan-400/60'}`}>
            {isDocument ? '▤' : icon}
          </span>
          <span className="flex-1 truncate">{feature.name}</span>

          {!isDocument && (
            <div className="flex items-center gap-1 opacity-0 group-hover/item:opacity-100 transition-opacity">
              {/* Visibility Toggle Eye */}
              <button
                type="button"
                onClick={(e) => toggleVisibility(e, feature)}
                title={feature.visible ? 'Hide feature' : 'Show feature'}
                className="text-[10px] text-cyan-400 hover:text-white px-1"
              >
                {feature.visible ? '👁' : '∅'}
              </button>

              {/* Quick Delete */}
              <button
                type="button"
                onClick={(e) => handleDelete(e, feature.id)}
                title="Delete feature"
                className="text-[10px] text-rose-400 hover:text-rose-200 px-1"
              >
                ×
              </button>
            </div>
          )}

          {!feature.visible && !isDocument && (
            <span className="rounded bg-amber-500/20 px-1 font-mono text-[8px] text-amber-300">
              OFF
            </span>
          )}
        </div>
        {feature.children?.map((child: any) => renderFeature(child, depth + 1))}
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col bg-[#040a18] select-none">
      <div className="flex items-center justify-between border-b border-cyan-500/20 px-3 py-2 font-mono text-[10px] font-bold tracking-[0.25em] text-[#00e5ff]">
        <span>MODEL TREE</span>
        <button
          type="button"
          onClick={() => window.dispatchEvent(new CustomEvent('jarvis-cad-refresh', {}))}
          title="Refresh model tree"
          className="text-cyan-400/60 hover:text-[#00e5ff] text-[11px]"
        >
          ↻
        </button>
      </div>
      <div className="flex-1 overflow-auto py-1">
        {tree ? (
          renderFeature(tree)
        ) : (
          <div className="px-3 py-4 font-mono text-[11px] leading-relaxed text-cyan-300/50">
            No model loaded.
            <br />
            Create a part via commands or ribbon buttons.
          </div>
        )}
      </div>
    </div>
  )
}
