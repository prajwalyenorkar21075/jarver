export type ViewCubePreset = 'top' | 'front' | 'right' | 'left' | 'back' | 'bottom' | 'iso' | 'fit'

interface CADViewCubeProps {
  currentView?: string
  onSelectView: (preset: ViewCubePreset) => void
  onToggleGrid?: () => void
  onToggleAxes?: () => void
  gridActive?: boolean
  axesActive?: boolean
}

export function CADViewCube({
  onSelectView,
  onToggleGrid,
  onToggleAxes,
  gridActive = true,
  axesActive = true,
}: CADViewCubeProps) {
  const cubeFaceBtn = (face: ViewCubePreset, label: string, className: string) => (
    <button
      type="button"
      onClick={() => onSelectView(face)}
      title={`View: ${label}`}
      className={`absolute flex items-center justify-center font-mono text-[9px] font-bold tracking-wider transition-all select-none hover:bg-[#00e5ff] hover:text-black active:scale-95 ${className}`}
    >
      {label}
    </button>
  )

  return (
    <div className="relative flex flex-col items-center gap-1.5 rounded-lg border border-cyan-500/30 bg-[#040916]/85 p-2 backdrop-blur-md shadow-[0_8px_24px_rgba(0,0,0,0.6)]">
      {/* 3D Isometric View Cube */}
      <div className="relative h-20 w-20 [perspective:300px]">
        <div className="relative h-full w-full [transform-style:preserve-3d] [transform:rotateX(-25deg)_rotateY(-35deg)] transition-transform duration-300">
          {/* TOP Face */}
          {cubeFaceBtn(
            'top',
            'TOP',
            'w-14 h-14 border border-cyan-400/60 bg-[#071936]/90 text-cyan-200 [transform:rotateX(90deg)_translateZ(28px)] top-3 left-3 shadow-[inset_0_0_8px_rgba(0,229,255,0.2)]'
          )}
          {/* FRONT Face */}
          {cubeFaceBtn(
            'front',
            'FRONT',
            'w-14 h-14 border border-cyan-400/60 bg-[#06142c]/90 text-cyan-200 [transform:translateZ(28px)] top-3 left-3 shadow-[inset_0_0_8px_rgba(0,229,255,0.2)]'
          )}
          {/* RIGHT Face */}
          {cubeFaceBtn(
            'right',
            'RIGHT',
            'w-14 h-14 border border-cyan-400/60 bg-[#051124]/90 text-cyan-200 [transform:rotateY(90deg)_translateZ(28px)] top-3 left-3 shadow-[inset_0_0_8px_rgba(0,229,255,0.2)]'
          )}
          {/* LEFT Face */}
          {cubeFaceBtn(
            'left',
            'LEFT',
            'w-14 h-14 border border-cyan-400/40 bg-[#040c1a]/90 text-cyan-300/70 [transform:rotateY(-90deg)_translateZ(28px)] top-3 left-3'
          )}
          {/* BACK Face */}
          {cubeFaceBtn(
            'back',
            'BACK',
            'w-14 h-14 border border-cyan-400/40 bg-[#040c1a]/90 text-cyan-300/70 [transform:rotateY(180deg)_translateZ(28px)] top-3 left-3'
          )}
          {/* BOTTOM Face */}
          {cubeFaceBtn(
            'bottom',
            'BTM',
            'w-14 h-14 border border-cyan-400/40 bg-[#040c1a]/90 text-cyan-300/70 [transform:rotateX(-90deg)_translateZ(28px)] top-3 left-3'
          )}
        </div>
      </div>

      {/* Compass Compass Direction Ticks */}
      <div className="flex w-full items-center justify-between px-1 font-mono text-[8px] text-cyan-400/60">
        <span>W</span>
        <span className="text-[#00e5ff] font-bold">N</span>
        <span>E</span>
      </div>

      {/* Quick View Presets Bar */}
      <div className="grid grid-cols-4 gap-1 w-full pt-1 border-t border-cyan-500/20">
        {(['iso', 'front', 'top', 'right', 'left', 'back', 'bottom', 'fit'] as ViewCubePreset[]).map((preset) => (
          <button
            key={preset}
            type="button"
            onClick={() => onSelectView(preset)}
            className="rounded border border-cyan-500/30 bg-[#071530] px-1 py-0.5 font-mono text-[9px] font-bold text-cyan-300 transition-colors hover:border-[#00e5ff] hover:bg-[#00e5ff] hover:text-black active:scale-95 text-center"
          >
            {preset.toUpperCase()}
          </button>
        ))}
      </div>

      {/* Grid and Axes Toggle Micro-buttons */}
      <div className="flex gap-1 w-full pt-1 border-t border-cyan-500/20">
        {onToggleGrid && (
          <button
            type="button"
            onClick={onToggleGrid}
            className={`flex-1 rounded border px-1.5 py-0.5 font-mono text-[8px] font-bold transition-all ${
              gridActive
                ? 'border-cyan-400 bg-cyan-500/20 text-[#00e5ff]'
                : 'border-cyan-500/30 bg-[#050e20] text-cyan-400/40'
            }`}
          >
            GRID: {gridActive ? 'ON' : 'OFF'}
          </button>
        )}
        {onToggleAxes && (
          <button
            type="button"
            onClick={onToggleAxes}
            className={`flex-1 rounded border px-1.5 py-0.5 font-mono text-[8px] font-bold transition-all ${
              axesActive
                ? 'border-cyan-400 bg-cyan-500/20 text-[#00e5ff]'
                : 'border-cyan-500/30 bg-[#050e20] text-cyan-400/40'
            }`}
          >
            AXES: {axesActive ? 'ON' : 'OFF'}
          </button>
        )}
      </div>
    </div>
  )
}
