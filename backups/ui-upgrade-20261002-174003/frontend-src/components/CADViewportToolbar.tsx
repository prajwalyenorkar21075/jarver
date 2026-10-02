interface CADViewportToolbarProps {
  onCreateBox: () => void;
  onCreateCylinder: () => void;
  onCreateSphere: () => void;
  onDeleteFeature: () => void;
  onRefresh: () => void;
  disabled: boolean;
}

export function CADViewportToolbar({
  onCreateBox,
  onCreateCylinder,
  onCreateSphere,
  onDeleteFeature,
  onRefresh,
  disabled,
}: CADViewportToolbarProps) {
  return (
    <div
      style={{
        display: 'flex',
        gap: 8,
        padding: 8,
        background: '#2d2d2d',
        borderBottom: '1px solid #333',
        alignItems: 'center',
      }}
    >
      <button
        onClick={onCreateBox}
        disabled={disabled}
        style={{
          padding: '6px 12px',
          background: '#4a90e2',
          color: 'white',
          border: 'none',
          borderRadius: 4,
          cursor: disabled ? 'not-allowed' : 'pointer',
          fontSize: 13,
        }}
      >
        Box
      </button>
      <button
        onClick={onCreateCylinder}
        disabled={disabled}
        style={{
          padding: '6px 12px',
          background: '#4a90e2',
          color: 'white',
          border: 'none',
          borderRadius: 4,
          cursor: disabled ? 'not-allowed' : 'pointer',
          fontSize: 13,
        }}
      >
        Cylinder
      </button>
      <button
        onClick={onCreateSphere}
        disabled={disabled}
        style={{
          padding: '6px 12px',
          background: '#4a90e2',
          color: 'white',
          border: 'none',
          borderRadius: 4,
          cursor: disabled ? 'not-allowed' : 'pointer',
          fontSize: 13,
        }}
      >
        Sphere
      </button>
      <div style={{ flex: 1 }} />
      <button
        onClick={onDeleteFeature}
        disabled={disabled}
        style={{
          padding: '6px 12px',
          background: '#e24a4a',
          color: 'white',
          border: 'none',
          borderRadius: 4,
          cursor: disabled ? 'not-allowed' : 'pointer',
          fontSize: 13,
        }}
      >
        Delete
      </button>
      <button
        onClick={onRefresh}
        disabled={disabled}
        style={{
          padding: '6px 12px',
          background: '#555',
          color: 'white',
          border: 'none',
          borderRadius: 4,
          cursor: disabled ? 'not-allowed' : 'pointer',
          fontSize: 13,
        }}
      >
        Refresh
      </button>
    </div>
  );
}
