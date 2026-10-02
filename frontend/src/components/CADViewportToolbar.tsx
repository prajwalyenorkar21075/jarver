interface CADViewportToolbarProps {
  onCreateBox: () => void;
  onCreateCylinder: () => void;
  onCreateSphere: () => void;
  onCreateCone: () => void;
  onCreateTorus: () => void;
  onDeleteFeature: () => void;
  onRefresh: () => void;
  onFitView: () => void;
  disabled: boolean;
  hasSelection: boolean;
}

const btn =
  'rounded border border-cyan-500/40 bg-[#071530] px-3 py-1.5 font-mono text-[11px] font-bold text-cyan-300 transition-all hover:border-[#00e5ff] hover:bg-[#00e5ff]/15 hover:text-white active:scale-95 disabled:cursor-not-allowed disabled:opacity-40';

export function CADViewportToolbar({
  onCreateBox,
  onCreateCylinder,
  onCreateSphere,
  onCreateCone,
  onCreateTorus,
  onDeleteFeature,
  onRefresh,
  onFitView,
  disabled,
  hasSelection,
}: CADViewportToolbarProps) {
  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-cyan-500/20 bg-[#040a18] px-3 py-2">
      <span className="mr-1 font-mono text-[10px] tracking-[0.25em] text-cyan-400/60">PRIMITIVES</span>
      <button type="button" className={btn} onClick={onCreateBox} disabled={disabled}>
        BOX
      </button>
      <button type="button" className={btn} onClick={onCreateCylinder} disabled={disabled}>
        CYLINDER
      </button>
      <button type="button" className={btn} onClick={onCreateSphere} disabled={disabled}>
        SPHERE
      </button>
      <button type="button" className={btn} onClick={onCreateCone} disabled={disabled}>
        CONE
      </button>
      <button type="button" className={btn} onClick={onCreateTorus} disabled={disabled}>
        TORUS
      </button>
      <div className="flex-1" />
      <button type="button" className={btn} onClick={onFitView} disabled={disabled}>
        FIT
      </button>
      <button type="button" className={btn} onClick={onRefresh} disabled={disabled}>
        RELOAD
      </button>
      <button
        type="button"
        className="rounded border border-rose-500/50 bg-[#1a0710] px-3 py-1.5 font-mono text-[11px] font-bold text-rose-300 transition-all hover:border-rose-400 hover:bg-rose-500/20 active:scale-95 disabled:cursor-not-allowed disabled:opacity-40"
        onClick={onDeleteFeature}
        disabled={disabled || !hasSelection}
        title={hasSelection ? 'Delete selected feature' : 'Select an object first'}
      >
        DELETE
      </button>
    </div>
  );
}
