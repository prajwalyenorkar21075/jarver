import { useEffect, useRef, useState, useCallback } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { TransformControls } from 'three/addons/controls/TransformControls.js'
import { CADModelTree } from './CADModelTree'
import { CADPropertiesPanel } from './CADPropertiesPanel'
import { CADViewCube, type ViewCubePreset } from './CADViewCube'

type ToolMode = 'select' | 'move' | 'rotate' | 'scale' | 'measure' | 'sketch'

interface TransformOverride {
  position: [number, number, number]
  rotation: [number, number, number]
  scale: [number, number, number]
}

interface MeshData {
  feature_id: string
  name: string
  type: string
  parameters: Record<string, any>
  vertices: number[]
  indices: number[]
  bbox?: {
    min: [number, number, number]
    max: [number, number, number]
    size: [number, number, number]
  }
}

interface SketchSegment3D {
  start: [number, number, number]
  end: [number, number, number]
}

interface SketchEntityData {
  id: string
  type: string
  segments_3d: SketchSegment3D[]
  color?: string
}

interface SketchData {
  sketch_id: string
  name: string
  workplane: string
  offset: number
  entities: SketchEntityData[]
}

const VIEW_COLORS = {
  base: 0x2f6ea8,
  selected: 0x00e5ff,
  hover: 0x5aa5e6,
  edges: 0x0a1e38,
  selectedEdges: 0x00ffff,
}

export function CADViewport() {
  const containerRef = useRef<HTMLDivElement>(null)
  const coordRef = useRef<HTMLDivElement>(null)
  const sceneRef = useRef<THREE.Scene | null>(null)
  const perspCameraRef = useRef<THREE.PerspectiveCamera | null>(null)
  const orthoCameraRef = useRef<THREE.OrthographicCamera | null>(null)
  const activeCameraRef = useRef<THREE.Camera | null>(null)
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null)
  const controlsRef = useRef<OrbitControls | null>(null)
  const meshMapRef = useRef<Map<string, THREE.Mesh>>(new Map())
  const sketchGroupRef = useRef<THREE.Group | null>(null)
  const gridRef = useRef<THREE.Group | null>(null)
  const workplaneGridRef = useRef<THREE.GridHelper | null>(null)
  const axesRef = useRef<THREE.Group | null>(null)
  const bboxHelperRef = useRef<THREE.BoxHelper | null>(null)
  const tcRef = useRef<TransformControls | null>(null)
  const overridesRef = useRef(new Map<string, TransformOverride>())

  // Section view clipping plane
  const sectionPlaneRef = useRef<THREE.Plane>(new THREE.Plane(new THREE.Vector3(1, 0, 0), 0))
  const [sectionActive, setSectionActive] = useState(false)
  const [sectionOffset, setSectionOffset] = useState(0)
  const [isOrtho, setIsOrtho] = useState(false)

  const selectedRef = useRef<string | null>(null)
  const hoveredRef = useRef<string | null>(null)
  const raycasterRef = useRef(new THREE.Raycaster())
  const pointerDownRef = useRef<{ x: number; y: number } | null>(null)

  const [selectedFeature, setSelectedFeature] = useState<string | null>(null)
  const activeToolRef = useRef<ToolMode>('select')
  const [modelTree, setModelTree] = useState<any>(null)
  const [backendOk, setBackendOk] = useState<boolean | null>(null)
  const [gridVisible, setGridVisible] = useState(true)
  const [axesVisible, setAxesVisible] = useState(true)
  const [activeWorkplane, setActiveWorkplane] = useState('XY')
  const [measurementOverlay, setMeasurementOverlay] = useState<{
    width?: number
    height?: number
    depth?: number
    volume?: number
    name?: string
  } | null>(null)

  const refreshMeasurement = (mesh: THREE.Mesh, name?: string) => {
    const box = new THREE.Box3().setFromObject(mesh)
    const size = new THREE.Vector3()
    box.getSize(size)
    setMeasurementOverlay({
      name: name || mesh.userData.name || 'Feature',
      width: Math.round(size.x * 100) / 100,
      height: Math.round(size.y * 100) / 100,
      depth: Math.round(size.z * 100) / 100,
      volume: Math.round(size.x * size.y * size.z),
    })
  }

  const recordOverride = (id: string, mesh: THREE.Mesh) => {
    overridesRef.current.set(id, {
      position: [mesh.position.x, mesh.position.y, mesh.position.z],
      rotation: [mesh.rotation.x, mesh.rotation.y, mesh.rotation.z],
      scale: [mesh.scale.x, mesh.scale.y, mesh.scale.z],
    })
  }

  const attachGizmo = (mode: ToolMode) => {
    const tc = tcRef.current
    if (!tc) return
    activeToolRef.current = mode
    const mesh = selectedRef.current ? meshMapRef.current.get(selectedRef.current) : undefined
    if (mode === 'select' || mode === 'measure' || mode === 'sketch' || !mesh) {
      tc.detach()
      tc.getHelper().visible = false
      return
    }
    tc.attach(mesh)
    tc.setMode(mode === 'move' ? 'translate' : mode)
    tc.getHelper().visible = true
  }

  const syncTransformToInspector = (id: string, mesh: THREE.Mesh) => {
    const mat = mesh.material as THREE.MeshStandardMaterial
    window.dispatchEvent(
      new CustomEvent('jarvis-cad-transform-synced', {
        detail: {
          featureId: id,
          position: { x: mesh.position.x, y: mesh.position.y, z: mesh.position.z },
          rotation: {
            x: THREE.MathUtils.radToDeg(mesh.rotation.x),
            y: THREE.MathUtils.radToDeg(mesh.rotation.y),
            z: THREE.MathUtils.radToDeg(mesh.rotation.z),
          },
          scale: { x: mesh.scale.x, y: mesh.scale.y, z: mesh.scale.z },
          material: {
            type: mat.type,
            color: `#${mat.color.getHexString()}`,
            metalness: mat.metalness,
            roughness: mat.roughness,
          },
        },
      })
    )
  }

  const repaint = useCallback(() => {
    meshMapRef.current.forEach((mesh, id) => {
      const mat = mesh.material as THREE.MeshStandardMaterial
      const edgeLine = mesh.userData.edgeLine as THREE.LineSegments | undefined

      if (id === selectedRef.current) {
        mat.color.setHex(0x194d7d)
        mat.emissive.setHex(VIEW_COLORS.selected)
        mat.emissiveIntensity = 0.45
        if (edgeLine) {
          ;(edgeLine.material as THREE.LineBasicMaterial).color.setHex(VIEW_COLORS.selectedEdges)
        }
      } else if (id === hoveredRef.current) {
        mat.color.setHex(VIEW_COLORS.base)
        mat.emissive.setHex(VIEW_COLORS.hover)
        mat.emissiveIntensity = 0.2
        if (edgeLine) {
          ;(edgeLine.material as THREE.LineBasicMaterial).color.setHex(0x00b4d8)
        }
      } else {
        mat.color.setHex(VIEW_COLORS.base)
        mat.emissive.setHex(0x000000)
        mat.emissiveIntensity = 0
        if (edgeLine) {
          ;(edgeLine.material as THREE.LineBasicMaterial).color.setHex(VIEW_COLORS.edges)
        }
      }
    })
    if (bboxHelperRef.current) {
      bboxHelperRef.current.update()
    }
  }, [])

  // Broadcast selection updates & sync with backend context
  useEffect(() => {
    selectedRef.current = selectedFeature
    window.dispatchEvent(
      new CustomEvent('jarvis-cad-selected', { detail: { featureId: selectedFeature } })
    )

    // Notify backend context of selection change
    if (selectedFeature) {
      fetch('/api/cad/context', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ selected_feature_id: selectedFeature }),
      }).catch(() => {})
    }

    // Update bounding box helper
    if (sceneRef.current) {
      if (bboxHelperRef.current) {
        sceneRef.current.remove(bboxHelperRef.current)
        bboxHelperRef.current.geometry.dispose()
        bboxHelperRef.current = null
      }
      if (selectedFeature) {
        const mesh = meshMapRef.current.get(selectedFeature)
        if (mesh) {
          const helper = new THREE.BoxHelper(mesh, 0x00e5ff)
          ;(helper.material as THREE.LineBasicMaterial).linewidth = 2
          sceneRef.current.add(helper)
          bboxHelperRef.current = helper

          refreshMeasurement(mesh, mesh.userData.name)
          syncTransformToInspector(selectedFeature, mesh)
        } else {
          setMeasurementOverlay(null)
        }
      } else {
        setMeasurementOverlay(null)
      }
    }
    attachGizmo(activeToolRef.current)
    repaint()
  }, [selectedFeature])

  // Setup Three.js scene, cameras, lights, and render loop
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0x040813)
    scene.fog = new THREE.Fog(0x040813, 1000, 4000)
    sceneRef.current = scene

    const width = container.clientWidth || 800
    const height = container.clientHeight || 600

    // Perspective Camera
    const perspCam = new THREE.PerspectiveCamera(50, width / height, 0.1, 10000)
    perspCam.position.set(160, 140, 180)
    perspCameraRef.current = perspCam

    // Orthographic Camera for engineering CAD orthogonal views
    const aspect = width / height
    const frustumSize = 250
    const orthoCam = new THREE.OrthographicCamera(
      (-frustumSize * aspect) / 2,
      (frustumSize * aspect) / 2,
      frustumSize / 2,
      -frustumSize / 2,
      0.1,
      10000
    )
    orthoCam.position.set(160, 140, 180)
    orthoCameraRef.current = orthoCam

    activeCameraRef.current = perspCam

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setSize(width, height)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.shadowMap.enabled = true
    renderer.shadowMap.type = THREE.PCFShadowMap
    renderer.localClippingEnabled = true
    container.appendChild(renderer.domElement)
    rendererRef.current = renderer

    const controls = new OrbitControls(perspCam, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.08
    controls.target.set(0, 0, 0)
    controlsRef.current = controls

    // Transform gizmo for Move / Rotate / Scale
    const tc = new TransformControls(perspCam, renderer.domElement)
    tc.addEventListener('dragging-changed', (ev: any) => {
      controls.enabled = !ev.value
    })
    tc.addEventListener('objectChange', () => {
      const obj = tc.object as THREE.Mesh
      if (!obj || !obj.userData.featureId) return
      const id = obj.userData.featureId as string
      recordOverride(id, obj)
      if (bboxHelperRef.current) bboxHelperRef.current.update()
      syncTransformToInspector(id, obj)
      refreshMeasurement(obj, obj.userData.name)
      repaint()
    })
    scene.add(tc.getHelper())
    tcRef.current = tc

    // Lighting (Studio CAD 3-point lighting setup)
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.85)
    scene.add(ambientLight)

    const mainKeyLight = new THREE.DirectionalLight(0xffffff, 1.4)
    mainKeyLight.position.set(200, 300, 200)
    mainKeyLight.castShadow = true
    mainKeyLight.shadow.mapSize.width = 2048
    mainKeyLight.shadow.mapSize.height = 2048
    scene.add(mainKeyLight)

    const fillLight = new THREE.DirectionalLight(0x4080ff, 0.7)
    fillLight.position.set(-200, 100, -150)
    scene.add(fillLight)

    const rimLight = new THREE.DirectionalLight(0x00e5ff, 0.5)
    rimLight.position.set(0, -200, 100)
    scene.add(rimLight)

    // Base Engineering Grid
    const gridGroup = new THREE.Group()
    const mainGrid = new THREE.GridHelper(500, 50, 0x00e5ff, 0x0e2547)
    mainGrid.position.y = -0.1
    gridGroup.add(mainGrid)
    scene.add(gridGroup)
    gridRef.current = gridGroup

    // Workplane grid helper (active workplane)
    const wpGrid = new THREE.GridHelper(200, 20, 0xff00ff, 0x331040)
    wpGrid.visible = false
    scene.add(wpGrid)
    workplaneGridRef.current = wpGrid

    // Sketch group for 2D geometry lines rendered in 3D
    const sketchGroup = new THREE.Group()
    scene.add(sketchGroup)
    sketchGroupRef.current = sketchGroup

    // World Axes Helper with X, Y, Z labels
    const axesGroup = new THREE.Group()
    const axesHelper = new THREE.AxesHelper(60)
    axesGroup.add(axesHelper)
    scene.add(axesGroup)
    axesRef.current = axesGroup

    // Render loop
    let raf = 0
    const animate = () => {
      raf = requestAnimationFrame(animate)
      controls.update()
      const cam = activeCameraRef.current || perspCam
      renderer.render(scene, cam)
    }
    animate()

    // Resize observer
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width: w, height: h } = entry.contentRect
        if (w === 0 || h === 0) continue

        perspCam.aspect = w / h
        perspCam.updateProjectionMatrix()

        const asp = w / h
        const fs = 250
        orthoCam.left = (-fs * asp) / 2
        orthoCam.right = (fs * asp) / 2
        orthoCam.top = fs / 2
        orthoCam.bottom = -fs / 2
        orthoCam.updateProjectionMatrix()

        renderer.setSize(w, h)
      }
    })
    resizeObserver.observe(container)

    // Raycasting & Pointer selection
    const pickMesh = (clientX: number, clientY: number): { mesh: THREE.Mesh } | null => {
      const rect = renderer.domElement.getBoundingClientRect()
      const x = ((clientX - rect.left) / rect.width) * 2 - 1
      const y = -((clientY - rect.top) / rect.height) * 2 + 1
      const cam = activeCameraRef.current || perspCam
      raycasterRef.current.setFromCamera(new THREE.Vector2(x, y), cam)
      const meshes = Array.from(meshMapRef.current.values())
      const hits = raycasterRef.current.intersectObjects(meshes, false)
      if (hits.length > 0) {
        return { mesh: hits[0].object as THREE.Mesh }
      }
      return null
    }

    const groundPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0)
    const worldPoint = new THREE.Vector3()

    const onPointerMove = (ev: PointerEvent) => {
      const hit = pickMesh(ev.clientX, ev.clientY)
      const nextHover = hit ? (hit.mesh.userData.featureId as string) : null
      if (nextHover !== hoveredRef.current) {
        hoveredRef.current = nextHover
        renderer.domElement.style.cursor = nextHover ? 'pointer' : 'default'
        repaint()
      }

      // Update Cursor World Coordinates
      if (coordRef.current) {
        const rect = renderer.domElement.getBoundingClientRect()
        const x = ((ev.clientX - rect.left) / rect.width) * 2 - 1
        const y = -((ev.clientY - rect.top) / rect.height) * 2 + 1
        const cam = activeCameraRef.current || perspCam
        raycasterRef.current.setFromCamera(new THREE.Vector2(x, y), cam)
        if (raycasterRef.current.ray.intersectPlane(groundPlane, worldPoint)) {
          coordRef.current.textContent = `X: ${worldPoint.x.toFixed(1)}  Y: 0.0  Z: ${worldPoint.z.toFixed(1)} mm`
        }
      }
    }

    const onPointerDown = (ev: PointerEvent) => {
      pointerDownRef.current = { x: ev.clientX, y: ev.clientY }
    }

    const onPointerUp = (ev: PointerEvent) => {
      const down = pointerDownRef.current
      pointerDownRef.current = null
      if (!down) return
      const dragged = Math.abs(ev.clientX - down.x) > 6 || Math.abs(ev.clientY - down.y) > 6
      if (dragged) return
      const hit = pickMesh(ev.clientX, ev.clientY)
      setSelectedFeature(hit ? (hit.mesh.userData.featureId as string) : null)
    }

    renderer.domElement.addEventListener('pointermove', onPointerMove)
    renderer.domElement.addEventListener('pointerdown', onPointerDown)
    renderer.domElement.addEventListener('pointerup', onPointerUp)

    return () => {
      cancelAnimationFrame(raf)
      resizeObserver.disconnect()
      renderer.domElement.removeEventListener('pointermove', onPointerMove)
      renderer.domElement.removeEventListener('pointerdown', onPointerDown)
      renderer.domElement.removeEventListener('pointerup', onPointerUp)
      tc.detach()
      tc.dispose()
      controls.dispose()
      renderer.dispose()
      if (renderer.domElement.parentElement === container) {
        container.removeChild(renderer.domElement)
      }
      meshMapRef.current.forEach((mesh) => {
        mesh.geometry.dispose()
        ;(mesh.material as THREE.Material).dispose()
      })
      meshMapRef.current.clear()
    }
  }, [repaint])

  // Camera framing presets
  const contentsBox = (): THREE.Box3 | null => {
    if (meshMapRef.current.size === 0) return null
    const box = new THREE.Box3()
    meshMapRef.current.forEach((mesh) => box.expandByObject(mesh))
    return box
  }

  const applyView = (preset: ViewCubePreset) => {
    const camera = activeCameraRef.current
    const controls = controlsRef.current
    if (!camera || !controls) return

    const box = contentsBox()
    const center = box ? box.getCenter(new THREE.Vector3()) : new THREE.Vector3(0, 0, 0)
    const size = box ? Math.max(box.getSize(new THREE.Vector3()).length(), 40) : 180

    let dist = 220
    if (camera instanceof THREE.PerspectiveCamera) {
      dist = (size / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)))) * 1.35
    } else if (camera instanceof THREE.OrthographicCamera) {
      dist = 300
    }

    const dirs: Record<Exclude<ViewCubePreset, 'fit'>, THREE.Vector3> = {
      front: new THREE.Vector3(0, 0, 1),
      back: new THREE.Vector3(0, 0, -1),
      left: new THREE.Vector3(-1, 0, 0),
      right: new THREE.Vector3(1, 0, 0),
      top: new THREE.Vector3(0, 1, 0.0001),
      bottom: new THREE.Vector3(0, -1, 0.0001),
      iso: new THREE.Vector3(1, 0.85, 1),
    }

    const dir =
      preset === 'fit'
        ? camera.position.clone().sub(controls.target).normalize()
        : dirs[preset].clone().normalize()

    camera.position.copy(center).addScaledVector(dir, dist)
    controls.target.copy(center)
    controls.update()
  }

  // Toggle Orthographic vs Perspective Camera
  const toggleOrthoPersp = () => {
    const nextOrtho = !isOrtho
    setIsOrtho(nextOrtho)
    const controls = controlsRef.current
    const tc = tcRef.current
    if (!controls || !tc) return

    const currentCam = activeCameraRef.current
    const nextCam = nextOrtho ? orthoCameraRef.current : perspCameraRef.current
    if (!nextCam || !currentCam) return

    nextCam.position.copy(currentCam.position)
    nextCam.rotation.copy(currentCam.rotation)

    activeCameraRef.current = nextCam
    controls.object = nextCam
    controls.update()

    tc.camera = nextCam
  }

  // Toggle Section View Clipping Plane
  const toggleSectionView = () => {
    const next = !sectionActive
    setSectionActive(next)
    updateSectionPlanes(next, sectionOffset)
  }

  const updateSectionPlanes = (active: boolean, offset: number) => {
    sectionPlaneRef.current.constant = offset
    const planes = active ? [sectionPlaneRef.current] : []
    meshMapRef.current.forEach((mesh) => {
      const mat = mesh.material as THREE.MeshStandardMaterial
      mat.clippingPlanes = planes
      mat.needsUpdate = true
    })
  }

  // Real Brep Tessellated Mesh & 2D Sketch Loading from Backend
  const loadDocumentMeshes = async (selectId?: string | null) => {
    try {
      const [meshRes, treeRes] = await Promise.all([
        fetch('/api/cad/document/meshes'),
        fetch('/api/cad/document/tree'),
      ])

      const meshData = await meshRes.json()
      const treeData = await treeRes.json()

      if (meshRes.ok && meshData.success) {
        setBackendOk(true)
        if (treeData?.success) {
          setModelTree(treeData.tree)
        }

        renderRealMeshes(meshData.meshes || [])
        renderSketches(meshData.sketches || [])

        if (selectId !== undefined) {
          setSelectedFeature(selectId)
        } else if (selectedRef.current && !meshMapRef.current.has(selectedRef.current)) {
          setSelectedFeature(null)
        }
      } else {
        setBackendOk(false)
      }
    } catch {
      setBackendOk(false)
    }
  }

  const renderRealMeshes = (meshes: MeshData[]) => {
    const scene = sceneRef.current
    if (!scene) return

    const currentIds = new Set(meshes.map((m) => m.feature_id))

    // Remove deleted meshes
    meshMapRef.current.forEach((mesh, id) => {
      if (!currentIds.has(id)) {
        scene.remove(mesh)
        mesh.geometry.dispose()
        ;(mesh.material as THREE.Material).dispose()
        meshMapRef.current.delete(id)
      }
    })

    // Construct or update each OpenCASCADE tessellated mesh
    for (const m of meshes) {
      if (!m.vertices || m.vertices.length === 0) continue

      // Existing mesh: dispose old geometry
      const existing = meshMapRef.current.get(m.feature_id)
      if (existing) {
        existing.geometry.dispose()
        scene.remove(existing)
        meshMapRef.current.delete(m.feature_id)
      }

      const geom = new THREE.BufferGeometry()
      geom.setAttribute('position', new THREE.Float32BufferAttribute(m.vertices, 3))
      if (m.indices && m.indices.length > 0) {
        geom.setIndex(m.indices)
      }
      geom.computeVertexNormals()

      const material = new THREE.MeshStandardMaterial({
        color: VIEW_COLORS.base,
        metalness: 0.45,
        roughness: 0.35,
        clippingPlanes: sectionActive ? [sectionPlaneRef.current] : [],
        clipShadows: true,
      })

      const mesh = new THREE.Mesh(geom, material)
      mesh.castShadow = true
      mesh.receiveShadow = true
      mesh.userData.featureId = m.feature_id
      mesh.userData.name = m.name
      mesh.userData.type = m.type

      // Add CAD sharp edge wireframe overlay
      const edgesGeom = new THREE.EdgesGeometry(geom, 24)
      const edgesMat = new THREE.LineBasicMaterial({
        color: VIEW_COLORS.edges,
        linewidth: 1.5,
      })
      const edgeLine = new THREE.LineSegments(edgesGeom, edgesMat)
      mesh.add(edgeLine)
      mesh.userData.edgeLine = edgeLine

      // Preserve user local transform overrides if any
      const ov = overridesRef.current.get(m.feature_id)
      if (ov) {
        mesh.position.set(ov.position[0], ov.position[1], ov.position[2])
        mesh.rotation.set(ov.rotation[0], ov.rotation[1], ov.rotation[2])
        mesh.scale.set(ov.scale[0], ov.scale[1], ov.scale[2])
      }

      scene.add(mesh)
      meshMapRef.current.set(m.feature_id, mesh)
    }

    repaint()
  }

  // Render 2D Sketch Geometry onto 3D Workplanes
  const renderSketches = (sketches: SketchData[]) => {
    const group = sketchGroupRef.current
    if (!group) return

    // Clear old sketch lines
    while (group.children.length > 0) {
      const child = group.children[0]
      group.remove(child)
      if (child instanceof THREE.LineSegments || child instanceof THREE.Line) {
        child.geometry.dispose()
        ;(child.material as THREE.Material).dispose()
      }
    }

    for (const sk of sketches) {
      for (const ent of sk.entities) {
        if (!ent.segments_3d || ent.segments_3d.length === 0) continue

        const points: number[] = []
        for (const seg of ent.segments_3d) {
          points.push(...seg.start, ...seg.end)
        }

        const geom = new THREE.BufferGeometry()
        geom.setAttribute('position', new THREE.Float32BufferAttribute(points, 3))

        const mat = new THREE.LineBasicMaterial({
          color: ent.color || (ent.type === 'circle' ? 0xffbb00 : 0x00ffcc),
          linewidth: 2,
        })
        const lines = new THREE.LineSegments(geom, mat)
        lines.userData.sketchId = sk.sketch_id
        lines.userData.entityId = ent.id
        group.add(lines)
      }
    }
  }

  useEffect(() => {
    loadDocumentMeshes()
  }, [])

  // External CAD Events
  useEffect(() => {
    const onRefresh = (ev: Event) => {
      const detail = (ev as CustomEvent).detail || {}
      loadDocumentMeshes(detail.featureId ?? null)
      if (detail.featureId) {
        setTimeout(focusSelected, 250)
      }
    }

    const onView = (ev: Event) => {
      const preset = (ev as CustomEvent).detail?.preset as ViewCubePreset | undefined
      if (preset) applyView(preset)
    }

    const onToggle = (ev: Event) => {
      const target = (ev as CustomEvent).detail?.target as string | undefined
      if (target === 'grid') {
        setGridVisible((v) => {
          if (gridRef.current) gridRef.current.visible = !v
          return !v
        })
      } else if (target === 'axes') {
        setAxesVisible((v) => {
          if (axesRef.current) axesRef.current.visible = !v
          return !v
        })
      } else if (target === 'ortho') {
        toggleOrthoPersp()
      } else if (target === 'section') {
        toggleSectionView()
      }
    }

    const onWorkplaneChange = (ev: Event) => {
      const wp = (ev as CustomEvent).detail?.workplane || 'XY'
      setActiveWorkplane(wp)
      if (workplaneGridRef.current) {
        workplaneGridRef.current.visible = true
        if (wp === 'XY') {
          workplaneGridRef.current.rotation.set(Math.PI / 2, 0, 0)
        } else if (wp === 'XZ') {
          workplaneGridRef.current.rotation.set(0, 0, 0)
        } else if (wp === 'YZ') {
          workplaneGridRef.current.rotation.set(0, 0, Math.PI / 2)
        }
      }
    }

    const onCadTool = (ev: Event) => {
      const mode = (ev as CustomEvent).detail?.mode as ToolMode | undefined
      if (mode) attachGizmo(mode)
    }

    const onCadDelete = async () => {
      if (!selectedRef.current) return
      try {
        const res = await fetch(`/api/cad/feature/${selectedRef.current}`, { method: 'DELETE' })
        if (res.ok) {
          setSelectedFeature(null)
          await loadDocumentMeshes(null)
        }
      } catch {}
    }

    window.addEventListener('jarvis-cad-refresh', onRefresh)
    window.addEventListener('jarvis-cad-view', onView)
    window.addEventListener('jarvis-cad-toggle', onToggle)
    window.addEventListener('jarvis-cad-workplane', onWorkplaneChange)
    window.addEventListener('jarvis-cad-tool', onCadTool)
    window.addEventListener('jarvis-cad-delete', onCadDelete)

    return () => {
      window.removeEventListener('jarvis-cad-refresh', onRefresh)
      window.removeEventListener('jarvis-cad-view', onView)
      window.removeEventListener('jarvis-cad-toggle', onToggle)
      window.removeEventListener('jarvis-cad-workplane', onWorkplaneChange)
      window.removeEventListener('jarvis-cad-tool', onCadTool)
      window.removeEventListener('jarvis-cad-delete', onCadDelete)
    }
  }, [repaint, isOrtho, sectionActive, sectionOffset])

  const focusSelected = () => {
    if (!selectedFeature) return
    const mesh = meshMapRef.current.get(selectedFeature)
    const controls = controlsRef.current
    if (!mesh || !controls) return
    controls.target.copy(mesh.position)
    controls.update()
  }

  const featureCount = (() => {
    let n = 0
    const walk = (f: any) => {
      if (f.type !== 'document') n += 1
      ;(f.children || []).forEach(walk)
    }
    if (modelTree) walk(modelTree)
    return n
  })()

  return (
    <div className="flex h-full w-full overflow-hidden bg-[#030612] select-none text-white">
      {/* 1. LEFT: MODEL TREE DOCK */}
      <div className="w-[220px] shrink-0 overflow-y-auto border-r border-cyan-500/20 bg-[#040815]">
        <CADModelTree
          tree={modelTree}
          selectedFeature={selectedFeature}
          onFeatureSelect={(id) => setSelectedFeature(id)}
        />
      </div>

      {/* 2. CENTER: MAIN 3D CAD VIEWPORT */}
      <div className="relative flex flex-1 flex-col min-w-0 min-h-0 bg-[#030713]">
        {/* Viewport 3D Canvas */}
        <div ref={containerRef} className="absolute inset-0 h-full w-full" />

        {/* TOP-LEFT OVERLAY: Workspace Status Badge */}
        <div className="pointer-events-none absolute left-3 top-3 rounded border border-cyan-500/30 bg-[#040916]/85 px-3 py-2 font-mono text-[10px] leading-relaxed text-cyan-200 backdrop-blur-sm shadow-md">
          <div className="flex items-center gap-1.5 font-bold tracking-[0.25em] text-[#00e5ff]">
            <span className="h-1.5 w-1.5 rounded-full bg-[#00e5ff] animate-pulse" />
            ENGINEERING CAD WORKSPACE
          </div>
          <div className="text-cyan-300/70">
            DOCUMENT: {modelTree?.name ?? 'Default'} · OBJECTS: {featureCount} · WP: {activeWorkplane}
          </div>
          <div className="flex items-center gap-2">
            <span className={backendOk === false ? 'text-rose-400' : 'text-emerald-400'}>
              ENGINE: {backendOk === null ? 'CONNECTING…' : backendOk ? 'ONLINE · CADQUERY / OCC' : 'OFFLINE'}
            </span>
            <span className="text-cyan-400/40">|</span>
            <span className="text-cyan-300 font-semibold">
              CAMERA: {isOrtho ? 'ORTHOGRAPHIC' : 'PERSPECTIVE'}
            </span>
          </div>
        </div>

        {/* TOP-RIGHT OVERLAY: Interactive 3D ViewCube & Viewport Quick Toggles */}
        <div className="absolute top-3 right-3 z-10 flex flex-col items-end gap-2">
          <CADViewCube
            onSelectView={applyView}
            gridActive={gridVisible}
            axesActive={axesVisible}
            onToggleGrid={() =>
              window.dispatchEvent(
                new CustomEvent('jarvis-cad-toggle', { detail: { target: 'grid' } })
              )
            }
            onToggleAxes={() =>
              window.dispatchEvent(
                new CustomEvent('jarvis-cad-toggle', { detail: { target: 'axes' } })
              )
            }
          />

          {/* Quick Camera & Section Controls */}
          <div className="flex items-center gap-1 rounded border border-cyan-500/30 bg-[#040916]/85 p-1 backdrop-blur-sm shadow-md">
            <button
              type="button"
              onClick={toggleOrthoPersp}
              title="Toggle Orthographic / Perspective Camera"
              className={`rounded px-2 py-0.5 font-mono text-[10px] font-bold uppercase transition-colors ${
                isOrtho
                  ? 'bg-[#00e5ff] text-black'
                  : 'text-cyan-200 hover:bg-cyan-500/20 hover:text-white'
              }`}
            >
              {isOrtho ? 'ORTHO' : 'PERSP'}
            </button>
            <button
              type="button"
              onClick={toggleSectionView}
              title="Toggle Section View (X-Plane Cut)"
              className={`rounded px-2 py-0.5 font-mono text-[10px] font-bold uppercase transition-colors ${
                sectionActive
                  ? 'bg-amber-400 text-black'
                  : 'text-cyan-200 hover:bg-cyan-500/20 hover:text-white'
              }`}
            >
              SECTION
            </button>
          </div>

          {/* Section Plane Offset Slider when Section View is active */}
          {sectionActive && (
            <div className="flex items-center gap-2 rounded border border-amber-400/40 bg-[#0a0e1c]/90 px-3 py-1 font-mono text-[10px] text-amber-300 backdrop-blur-md shadow-lg">
              <span>CUT X:</span>
              <input
                type="range"
                min={-150}
                max={150}
                value={sectionOffset}
                onChange={(e) => {
                  const val = parseFloat(e.target.value)
                  setSectionOffset(val)
                  updateSectionPlanes(true, val)
                }}
                className="w-24 accent-amber-400 cursor-pointer"
              />
              <span>{sectionOffset}mm</span>
            </div>
          )}
        </div>

        {/* BOTTOM-LEFT OVERLAY: Live Cursor World Coordinates */}
        <div className="pointer-events-none absolute bottom-3 left-3 z-10 flex items-center gap-2 rounded border border-cyan-500/30 bg-[#040916]/85 px-3 py-1.5 font-mono text-[11px] text-[#00e5ff] backdrop-blur-sm shadow-md">
          <span className="text-cyan-400/60 font-bold">CRS</span>
          <span ref={coordRef}>X: 0.0  Y: 0.0  Z: 0.0 mm</span>
        </div>

        {/* BOTTOM-CENTER OVERLAY: Measurement Info Display */}
        {measurementOverlay && (
          <div className="pointer-events-none absolute bottom-3 left-1/2 -translate-x-1/2 z-10 flex items-center gap-3 rounded border border-cyan-500/40 bg-[#061124]/90 px-4 py-1.5 font-mono text-[10px] text-cyan-200 backdrop-blur-md shadow-lg">
            <span className="text-[#00e5ff] font-bold tracking-wider">
              {(measurementOverlay.name || 'FEATURE').toUpperCase()}:
            </span>
            <span>
              DIM: {measurementOverlay.width} × {measurementOverlay.height} × {measurementOverlay.depth} mm
            </span>
            <span className="text-cyan-400/50">|</span>
            <span>VOL: {measurementOverlay.volume?.toLocaleString()} mm³</span>
          </div>
        )}
      </div>

      {/* 3. RIGHT: PROPERTIES & INSPECTOR DOCK */}
      <div className="w-[280px] shrink-0 overflow-y-auto border-l border-cyan-500/20 bg-[#040815]">
        <CADPropertiesPanel
          featureId={selectedFeature}
          onFeatureUpdate={() => loadDocumentMeshes()}
        />
      </div>
    </div>
  )
}
