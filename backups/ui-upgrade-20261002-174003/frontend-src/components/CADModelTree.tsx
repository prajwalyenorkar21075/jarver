interface CADModelTreeProps {
  tree: any;
  selectedFeature: string | null;
  onFeatureSelect: (featureId: string) => void;
}

export function CADModelTree({ tree, selectedFeature, onFeatureSelect }: CADModelTreeProps) {
  if (!tree) {
    return <div style={{ padding: 16, color: '#888' }}>No model loaded</div>;
  }

  const renderFeature = (feature: any, depth: number = 0) => {
    const isSelected = selectedFeature === feature.id;
    const hasChildren = feature.children && feature.children.length > 0;

    return (
      <div key={feature.id}>
        <div
          onClick={() => feature.type !== 'document' && onFeatureSelect(feature.id)}
          style={{
            padding: '8px 12px',
            paddingLeft: 12 + depth * 16,
            background: isSelected ? '#4a90e2' : 'transparent',
            color: isSelected ? 'white' : '#ddd',
            cursor: feature.type !== 'document' ? 'pointer' : 'default',
            borderLeft: isSelected ? '3px solid #00ff00' : '3px solid transparent',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            fontSize: 13,
          }}
        >
          <span style={{ opacity: 0.6 }}>
            {feature.type === 'document' ? '📄' : feature.type === 'primitive' ? '⬜' : '⚙️'}
          </span>
          <span style={{ flex: 1 }}>{feature.name}</span>
          {!feature.visible && <span style={{ opacity: 0.4, fontSize: 11 }}>hidden</span>}
        </div>
        {hasChildren && feature.children.map((child: any) => renderFeature(child, depth + 1))}
      </div>
    );
  };

  return (
    <div style={{ background: '#252525' }}>
      <div
        style={{
          padding: '12px 16px',
          borderBottom: '1px solid #333',
          color: '#fff',
          fontWeight: 600,
          fontSize: 14,
        }}
      >
        Model Tree
      </div>
      {renderFeature(tree)}
    </div>
  );
}
