import { useRef, useEffect, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { CADViewportToolbar } from './CADViewportToolbar';
import { CADModelTree } from './CADModelTree';
import { CADPropertiesPanel } from './CADPropertiesPanel';

interface CADFeature {
  id: string;
  name: string;
  type: string;
  status: string;
  visible: boolean;
  parameters?: Record<string, any>;
  children?: CADFeature[];
}

interface CADViewportProps {
  onFeatureSelect?: (featureId: string) => void;
}

export function CADViewport({ onFeatureSelect }: CADViewportProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const meshMapRef = useRef<Map<string, THREE.Mesh>>(new Map());
  
  const [selectedFeature, setSelectedFeature] = useState<string | null>(null);
  const [modelTree, setModelTree] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!containerRef.current) return;

    // Scene setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1e1e1e);
    sceneRef.current = scene;

    // Camera
    const camera = new THREE.PerspectiveCamera(
      60,
      containerRef.current.clientWidth / containerRef.current.clientHeight,
      0.1,
      10000
    );
    camera.position.set(50, 50, 50);
    cameraRef.current = camera;

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(containerRef.current.clientWidth, containerRef.current.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    containerRef.current.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // Controls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controlsRef.current = controls;

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(50, 100, 50);
    directionalLight.castShadow = true;
    directionalLight.shadow.mapSize.width = 2048;
    directionalLight.shadow.mapSize.height = 2048;
    scene.add(directionalLight);

    // Grid
    const gridHelper = new THREE.GridHelper(100, 10, 0x444444, 0x222222);
    scene.add(gridHelper);

    // Axes
    const axesHelper = new THREE.AxesHelper(10);
    scene.add(axesHelper);

    // Animation loop
    const animate = () => {
      requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    // Handle resize
    const handleResize = () => {
      if (!containerRef.current) return;
      const width = containerRef.current.clientWidth;
      const height = containerRef.current.clientHeight;
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height);
    };
    window.addEventListener('resize', handleResize);

    // Load initial model
    loadModelTree();

    return () => {
      window.removeEventListener('resize', handleResize);
      if (containerRef.current && renderer.domElement) {
        containerRef.current.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, []);

  const loadModelTree = async () => {
    try {
      const response = await fetch('/api/cad/document/tree');
      const data = await response.json();
      if (data.success) {
        setModelTree(data.tree);
        await buildSceneFromTree(data.tree);
      }
    } catch (error) {
      console.error('Failed to load model tree:', error);
    }
  };

  const buildSceneFromTree = async (tree: any) => {
    if (!sceneRef.current) return;

    // Clear existing meshes
    meshMapRef.current.forEach((mesh) => {
      sceneRef.current!.remove(mesh);
      mesh.geometry.dispose();
      if (mesh.material instanceof THREE.Material) {
        mesh.material.dispose();
      }
    });
    meshMapRef.current.clear();

    // Build meshes from tree
    if (tree.children) {
      for (const feature of tree.children) {
        await buildFeatureMesh(feature);
      }
    }
  };

  const buildFeatureMesh = async (feature: CADFeature) => {
    if (!sceneRef.current || !feature.visible) return;

    let geometry: THREE.BufferGeometry;
    const params = feature.parameters || {};

    switch (feature.type) {
      case 'primitive':
        if (params.primitive_type === 'box') {
          geometry = new THREE.BoxGeometry(params.width || 10, params.height || 10, params.depth || 10);
        } else if (params.primitive_type === 'cylinder') {
          geometry = new THREE.CylinderGeometry(params.radius || 5, params.radius || 5, params.height || 10, 32);
        } else if (params.primitive_type === 'sphere') {
          geometry = new THREE.SphereGeometry(params.radius || 5, 32, 32);
        } else if (params.primitive_type === 'cone') {
          geometry = new THREE.ConeGeometry(params.radius || 5, params.height || 10, 32);
        } else if (params.primitive_type === 'torus') {
          geometry = new THREE.TorusGeometry(params.major_radius || 10, params.minor_radius || 2, 16, 100);
        } else {
          return;
        }
        break;
      default:
        // For other feature types, try to fetch geometry from backend
        try {
          const response = await fetch(`/api/cad/feature/${feature.id}`);
          const data = await response.json();
          if (data.success && data.feature.parameters) {
            const p = data.feature.parameters;
            if (p.primitive_type === 'box') {
              geometry = new THREE.BoxGeometry(p.width || 10, p.height || 10, p.depth || 10);
            } else {
              return;
            }
          } else {
            return;
          }
        } catch {
          return;
        }
    }

    const material = new THREE.MeshStandardMaterial({
      color: selectedFeature === feature.id ? 0x00ff00 : 0x4a90e2,
      metalness: 0.3,
      roughness: 0.7,
    });

    const mesh = new THREE.Mesh(geometry, material);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    mesh.userData.featureId = feature.id;

    sceneRef.current.add(mesh);
    meshMapRef.current.set(feature.id, mesh);

    // Build children
    if (feature.children) {
      for (const child of feature.children) {
        await buildFeatureMesh(child);
      }
    }
  };

  const handleFeatureSelect = (featureId: string) => {
    setSelectedFeature(featureId);
    
    // Update mesh colors
    meshMapRef.current.forEach((mesh, id) => {
      if (mesh.material instanceof THREE.MeshStandardMaterial) {
        mesh.material.color.setHex(id === featureId ? 0x00ff00 : 0x4a90e2);
      }
    });

    onFeatureSelect?.(featureId);
  };

  const handleCreateBox = async () => {
    setLoading(true);
    try {
      await fetch('/api/cad/primitive/box?width=10&height=10&depth=10', {
        method: 'POST',
      });
      await loadModelTree();
    } catch (error) {
      console.error('Failed to create box:', error);
    }
    setLoading(false);
  };

  const handleCreateCylinder = async () => {
    setLoading(true);
    try {
      await fetch('/api/cad/primitive/cylinder?radius=5&height=10', {
        method: 'POST',
      });
      await loadModelTree();
    } catch (error) {
      console.error('Failed to create cylinder:', error);
    }
    setLoading(false);
  };

  const handleCreateSphere = async () => {
    setLoading(true);
    try {
      await fetch('/api/cad/primitive/sphere?radius=5', {
        method: 'POST',
      });
      await loadModelTree();
    } catch (error) {
      console.error('Failed to create sphere:', error);
    }
    setLoading(false);
  };

  const handleDeleteFeature = async () => {
    if (!selectedFeature) return;
    setLoading(true);
    try {
      await fetch(`/api/cad/feature/${selectedFeature}`, {
        method: 'DELETE',
      });
      setSelectedFeature(null);
      await loadModelTree();
    } catch (error) {
      console.error('Failed to delete feature:', error);
    }
    setLoading(false);
  };

  return (
    <div style={{ display: 'flex', height: '100vh', background: '#1e1e1e', overflow: 'hidden' }}>
      <div style={{ width: 200, borderRight: '1px solid #333', overflow: 'auto', flexShrink: 0 }}>
        <CADModelTree
          tree={modelTree}
          selectedFeature={selectedFeature}
          onFeatureSelect={handleFeatureSelect}
        />
      </div>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 200 }}>
        <CADViewportToolbar
          onCreateBox={handleCreateBox}
          onCreateCylinder={handleCreateCylinder}
          onCreateSphere={handleCreateSphere}
          onDeleteFeature={handleDeleteFeature}
          onRefresh={loadModelTree}
          disabled={loading}
        />
        <div ref={containerRef} style={{ flex: 1, position: 'relative', minHeight: 0 }} />
      </div>

      <div style={{ width: 250, borderLeft: '1px solid #333', overflow: 'auto', flexShrink: 0 }}>
        <CADPropertiesPanel
          featureId={selectedFeature}
          onFeatureUpdate={loadModelTree}
        />
      </div>
    </div>
  );
}
