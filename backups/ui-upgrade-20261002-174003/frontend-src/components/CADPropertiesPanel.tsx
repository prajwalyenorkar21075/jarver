import { useState, useEffect } from 'react';

interface CADPropertiesPanelProps {
  featureId: string | null;
  onFeatureUpdate: () => void;
}

export function CADPropertiesPanel({ featureId, onFeatureUpdate }: CADPropertiesPanelProps) {
  const [feature, setFeature] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState(false);
  const [params, setParams] = useState<Record<string, any>>({});

  useEffect(() => {
    if (!featureId) {
      setFeature(null);
      return;
    }

    loadFeature();
  }, [featureId]);

  const loadFeature = async () => {
    if (!featureId) return;
    setLoading(true);
    try {
      const response = await fetch(`/api/cad/feature/${featureId}`);
      const data = await response.json();
      if (data.success) {
        setFeature(data.feature);
        setParams(data.feature.parameters || {});
      }
    } catch (error) {
      console.error('Failed to load feature:', error);
    }
    setLoading(false);
  };

  const handleSave = async () => {
    if (!featureId) return;
    setLoading(true);
    try {
      await fetch(`/api/cad/feature/${featureId}/parameters`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
      });
      setEditing(false);
      onFeatureUpdate();
      await loadFeature();
    } catch (error) {
      console.error('Failed to update parameters:', error);
    }
    setLoading(false);
  };

  const handleRename = async (newName: string) => {
    if (!featureId) return;
    setLoading(true);
    try {
      await fetch(`/api/cad/feature/${featureId}/rename?new_name=${encodeURIComponent(newName)}`, {
        method: 'PUT',
      });
      onFeatureUpdate();
      await loadFeature();
    } catch (error) {
      console.error('Failed to rename feature:', error);
    }
    setLoading(false);
  };

  const handleToggleVisibility = async () => {
    if (!featureId || !feature) return;
    setLoading(true);
    try {
      await fetch(
        `/api/cad/feature/${featureId}/visibility?visible=${!feature.visible}`,
        { method: 'PUT' }
      );
      onFeatureUpdate();
      await loadFeature();
    } catch (error) {
      console.error('Failed to toggle visibility:', error);
    }
    setLoading(false);
  };

  if (!featureId) {
    return (
      <div style={{ padding: 16, color: '#888' }}>
        Select a feature to view properties
      </div>
    );
  }

  if (loading) {
    return <div style={{ padding: 16, color: '#888' }}>Loading...</div>;
  }

  if (!feature) {
    return <div style={{ padding: 16, color: '#888' }}>Feature not found</div>;
  }

  return (
    <div style={{ background: '#252525', color: '#ddd' }}>
      <div
        style={{
          padding: '12px 16px',
          borderBottom: '1px solid #333',
          color: '#fff',
          fontWeight: 600,
          fontSize: 14,
        }}
      >
        Properties
      </div>

      <div style={{ padding: 16 }}>
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 4, fontSize: 12, color: '#888' }}>
            Name
          </label>
          <input
            type="text"
            value={feature.name}
            onChange={(e) => handleRename(e.target.value)}
            style={{
              width: '100%',
              padding: 6,
              background: '#1e1e1e',
              border: '1px solid #444',
              borderRadius: 4,
              color: '#ddd',
              fontSize: 13,
            }}
          />
        </div>

        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 4, fontSize: 12, color: '#888' }}>
            Type
          </label>
          <div style={{ padding: 6, background: '#1e1e1e', borderRadius: 4, fontSize: 13 }}>
            {feature.feature_type || feature.type}
          </div>
        </div>

        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 4, fontSize: 12, color: '#888' }}>
            Status
          </label>
          <div style={{ padding: 6, background: '#1e1e1e', borderRadius: 4, fontSize: 13 }}>
            {feature.status}
          </div>
        </div>

        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
            <input
              type="checkbox"
              checked={feature.visible}
              onChange={handleToggleVisibility}
            />
            Visible
          </label>
        </div>

        <div style={{ borderTop: '1px solid #333', paddingTop: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
            <label style={{ fontSize: 12, color: '#888', fontWeight: 600 }}>Parameters</label>
            <button
              onClick={() => (editing ? handleSave() : setEditing(true))}
              style={{
                padding: '4px 8px',
                background: editing ? '#4a90e2' : '#555',
                color: 'white',
                border: 'none',
                borderRadius: 4,
                cursor: 'pointer',
                fontSize: 12,
              }}
            >
              {editing ? 'Save' : 'Edit'}
            </button>
          </div>

          {Object.entries(params).map(([key, value]) => (
            <div key={key} style={{ marginBottom: 12 }}>
              <label style={{ display: 'block', marginBottom: 4, fontSize: 12, color: '#888' }}>
                {key}
              </label>
              {editing ? (
                <input
                  type={typeof value === 'number' ? 'number' : 'text'}
                  value={value}
                  onChange={(e) =>
                    setParams({
                      ...params,
                      [key]: typeof value === 'number' ? parseFloat(e.target.value) : e.target.value,
                    })
                  }
                  style={{
                    width: '100%',
                    padding: 6,
                    background: '#1e1e1e',
                    border: '1px solid #444',
                    borderRadius: 4,
                    color: '#ddd',
                    fontSize: 13,
                  }}
                />
              ) : (
                <div style={{ padding: 6, background: '#1e1e1e', borderRadius: 4, fontSize: 13 }}>
                  {String(value)}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
