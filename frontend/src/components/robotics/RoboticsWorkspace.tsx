import { useState, useEffect, useRef } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { playHudChirp } from '../../store/useJarvisStore'

interface JointState {
  j1: number
  j2: number
  j3: number
  j4: number
  j5: number
  j6: number
}

export default function RoboticsWorkspace() {
  const containerRef = useRef<HTMLDivElement>(null)
  const [joints, setJoints] = useState<JointState>({
    j1: 0,
    j2: 25,
    j3: -45,
    j4: 0,
    j5: 30,
    j6: 0,
  })

  const [simPlaying, setSimPlaying] = useState(false)
  const [activeTab, setActiveTab] = useState<'joints' | 'sensors' | 'ros' | 'commands'>('joints')
  const [statusNotice, setStatusNotice] = useState<string | null>(null)

  // Real robotics service state from the J.A.R.V.I.S. backend
  const [serviceStatus, setServiceStatus] = useState<any>(null)
  const [serviceOnline, setServiceOnline] = useState<boolean | null>(null)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const res = await fetch('/api/robotics/status')
        const data = await res.json()
        if (cancelled) return
        if (res.ok) {
          setServiceStatus(data)
          setServiceOnline(true)
        } else {
          setServiceOnline(false)
        }
      } catch {
        if (!cancelled) setServiceOnline(false)
      }
    }
    load()
    const interval = setInterval(load, 5000)
    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [])

  // Robot 3D Mesh references for Forward Kinematics
  const jointsRef = useRef(joints)
  jointsRef.current = joints

  const baseGroupRef = useRef<THREE.Group | null>(null)
  const link1GroupRef = useRef<THREE.Group | null>(null)
  const link2GroupRef = useRef<THREE.Group | null>(null)
  const link3GroupRef = useRef<THREE.Group | null>(null)
  const link4GroupRef = useRef<THREE.Group | null>(null)
  const gripperRef = useRef<THREE.Group | null>(null)

  // End effector calculated pose
  const [eePose, setEePose] = useState({ x: 185.2, y: 142.0, z: 0.0, roll: 0, pitch: 10, yaw: 0 })

  const flashNotice = (msg: string) => {
    setStatusNotice(msg)
    setTimeout(() => setStatusNotice(null), 3000)
  }

  // Three.js Robot Model Visualization
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0x040814)
    scene.fog = new THREE.Fog(0x040814, 500, 2000)

    const camera = new THREE.PerspectiveCamera(50, container.clientWidth / container.clientHeight, 0.1, 1000)
    camera.position.set(220, 180, 240)

    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(container.clientWidth, container.clientHeight)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.shadowMap.enabled = true
    container.appendChild(renderer.domElement)

    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.08
    controls.target.set(0, 60, 0)

    // Lighting
    scene.add(new THREE.AmbientLight(0xbad4fa, 0.6))
    const dir = new THREE.DirectionalLight(0xffffff, 1.2)
    dir.position.set(100, 200, 120)
    scene.add(dir)

    const rim = new THREE.DirectionalLight(0x00e5ff, 0.5)
    rim.position.set(-100, 100, -100)
    scene.add(rim)

    // Floor Grid
    const grid = new THREE.GridHelper(400, 40, 0x1e3a5f, 0x09192f)
    grid.position.y = 0
    scene.add(grid)

    // Build 6-DOF Robot Arm Hierarchy
    const metalMat = new THREE.MeshStandardMaterial({ color: 0x1a2638, metalness: 0.8, roughness: 0.3 })
    const orangeMat = new THREE.MeshStandardMaterial({ color: 0xff6600, metalness: 0.4, roughness: 0.4 })
    const cyanMat = new THREE.MeshStandardMaterial({ color: 0x00e5ff, emissive: 0x00e5ff, emissiveIntensity: 0.3 })

    // Base pedestal
    const baseMesh = new THREE.Mesh(new THREE.CylinderGeometry(35, 42, 14, 32), metalMat)
    baseMesh.position.y = 7
    scene.add(baseMesh)

    // J1: Base Rotating Turret
    const j1Group = new THREE.Group()
    j1Group.position.y = 14
    scene.add(j1Group)
    baseGroupRef.current = j1Group

    const j1Mesh = new THREE.Mesh(new THREE.CylinderGeometry(26, 26, 22, 32), orangeMat)
    j1Mesh.position.y = 11
    j1Group.add(j1Mesh)

    // J2: Shoulder Link
    const j2Group = new THREE.Group()
    j2Group.position.set(0, 22, 0)
    j1Group.add(j2Group)
    link1GroupRef.current = j2Group

    const j2JointMesh = new THREE.Mesh(new THREE.CylinderGeometry(16, 16, 28, 24), metalMat)
    j2JointMesh.rotation.z = Math.PI / 2
    j2Group.add(j2JointMesh)

    const upperArm = new THREE.Mesh(new THREE.BoxGeometry(16, 75, 20), orangeMat)
    upperArm.position.y = 37.5
    j2Group.add(upperArm)

    // J3: Elbow Link
    const j3Group = new THREE.Group()
    j3Group.position.set(0, 75, 0)
    j2Group.add(j3Group)
    link2GroupRef.current = j3Group

    const j3JointMesh = new THREE.Mesh(new THREE.CylinderGeometry(14, 14, 24, 24), metalMat)
    j3JointMesh.rotation.z = Math.PI / 2
    j3Group.add(j3JointMesh)

    const forearm = new THREE.Mesh(new THREE.BoxGeometry(14, 65, 16), metalMat)
    forearm.position.y = 32.5
    j3Group.add(forearm)

    // J4: Forearm Roll
    const j4Group = new THREE.Group()
    j4Group.position.set(0, 65, 0)
    j3Group.add(j4Group)
    link3GroupRef.current = j4Group

    const j4Mesh = new THREE.Mesh(new THREE.CylinderGeometry(10, 10, 20, 24), orangeMat)
    j4Mesh.position.y = 10
    j4Group.add(j4Mesh)

    // J5: Wrist Pitch
    const j5Group = new THREE.Group()
    j5Group.position.set(0, 20, 0)
    j4Group.add(j5Group)
    link4GroupRef.current = j5Group

    const j5JointMesh = new THREE.Mesh(new THREE.CylinderGeometry(8, 8, 18, 24), metalMat)
    j5JointMesh.rotation.x = Math.PI / 2
    j5Group.add(j5JointMesh)

    // J6: End Effector / Gripper Flange
    const j6Group = new THREE.Group()
    j6Group.position.set(0, 15, 0)
    j5Group.add(j6Group)
    gripperRef.current = j6Group

    // Parallel Gripper Fingers
    const gripperBase = new THREE.Mesh(new THREE.BoxGeometry(24, 6, 12), metalMat)
    j6Group.add(gripperBase)

    const fingerL = new THREE.Mesh(new THREE.BoxGeometry(4, 18, 6), cyanMat)
    fingerL.position.set(-7, 9, 0)
    const fingerR = new THREE.Mesh(new THREE.BoxGeometry(4, 18, 6), cyanMat)
    fingerR.position.set(7, 9, 0)
    j6Group.add(fingerL, fingerR)

    let raf = 0
    const animate = () => {
      raf = requestAnimationFrame(animate)
      controls.update()

      // Apply Forward Kinematics rotations to 3D bones
      const cur = jointsRef.current
      if (baseGroupRef.current) baseGroupRef.current.rotation.y = THREE.MathUtils.degToRad(cur.j1)
      if (link1GroupRef.current) link1GroupRef.current.rotation.z = THREE.MathUtils.degToRad(cur.j2)
      if (link2GroupRef.current) link2GroupRef.current.rotation.z = THREE.MathUtils.degToRad(cur.j3)
      if (link3GroupRef.current) link3GroupRef.current.rotation.y = THREE.MathUtils.degToRad(cur.j4)
      if (link4GroupRef.current) link4GroupRef.current.rotation.x = THREE.MathUtils.degToRad(cur.j5)
      if (gripperRef.current) gripperRef.current.rotation.z = THREE.MathUtils.degToRad(cur.j6)

      // Calculate world position of end effector
      if (gripperRef.current) {
        const wp = new THREE.Vector3()
        gripperRef.current.getWorldPosition(wp)
        setEePose((p) => ({
          ...p,
          x: Math.round(wp.x * 10) / 10,
          y: Math.round(wp.y * 10) / 10,
          z: Math.round(wp.z * 10) / 10,
        }))
      }

      renderer.render(scene, camera)
    }
    animate()

    const onResize = () => {
      if (!container) return
      camera.aspect = container.clientWidth / container.clientHeight
      camera.updateProjectionMatrix()
      renderer.setSize(container.clientWidth, container.clientHeight)
    }
    window.addEventListener('resize', onResize)

    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('resize', onResize)
      controls.dispose()
      renderer.dispose()
      if (renderer.domElement.parentElement === container) {
        container.removeChild(renderer.domElement)
      }
    }
  }, [])

  // Simulation Loop
  useEffect(() => {
    if (!simPlaying) return
    const interval = setInterval(() => {
      setJoints((j) => ({
        ...j,
        j1: Math.sin(Date.now() / 1000) * 45,
        j2: 25 + Math.sin(Date.now() / 800) * 15,
        j3: -45 + Math.cos(Date.now() / 900) * 20,
      }))
    }, 40)
    return () => clearInterval(interval)
  }, [simPlaying])

  const handleHome = () => {
    playHudChirp()
    setSimPlaying(false)
    setJoints({ j1: 0, j2: 0, j3: 0, j4: 0, j5: 0, j6: 0 })
    flashNotice('Robot returned to HOME zero-offset pose')
  }

  const handlePickAndPlace = () => {
    playHudChirp()
    setSimPlaying(false)
    setJoints({ j1: 35, j2: 45, j3: -60, j4: 10, j5: 25, j6: 0 })
    flashNotice('Executing Pick & Place kinematic routine')
  }

  const handleEmergencyStop = async () => {
    playHudChirp()
    setSimPlaying(false)
    try {
      const res = await fetch('/api/robotics/emergency-stop', { method: 'POST' })
      flashNotice(res.ok ? 'E-STOP sent to robotics service (simulation)' : 'E-STOP recorded locally: service rejected the request')
    } catch {
      flashNotice('E-STOP recorded locally: robotics service unreachable')
    }
  }

  return (
    <div className="flex h-full w-full overflow-hidden bg-[#030612] select-none text-white font-mono">
      {/* 1. LEFT: 3D ROBOT VIEWPORT & SIMULATION */}
      <div className="relative flex flex-1 flex-col min-w-0 min-h-0 bg-[#030713]">
        <div ref={containerRef} className="absolute inset-0 h-full w-full" />

        {/* Viewport Overlay: Header & Health */}
        <div className="pointer-events-none absolute top-3 left-3 z-10 flex flex-col gap-1 rounded border border-cyan-500/30 bg-[#040a18]/85 p-3 backdrop-blur-md">
          <div className="flex items-center gap-2 font-bold tracking-[0.2em] text-[#00e5ff]">
            <span className={`h-2 w-2 rounded-full ${serviceOnline ? 'bg-emerald-400' : 'bg-rose-400'} animate-pulse`} />
            6-DOF ROBOTIC MANIPULATOR KINEMATICS
          </div>
          <div className="text-[10px] text-cyan-300/70">
            MODEL: STARK-M1 (VISUALIZED) · SERVICE: {serviceOnline === null ? 'QUERYING…' : serviceOnline ? `MODE ${serviceStatus?.robot_state?.mode ?? '—'}` : 'BACKEND OFFLINE'}
          </div>
          <div className="flex items-center gap-3 text-[10px]">
            <span className={serviceStatus?.simulation ? 'text-amber-400' : 'text-emerald-400'}>
              {serviceStatus?.simulation ? 'ENGINE: INTERNAL SIMULATION' : 'ENGINE: LIVE'}
            </span>
            <span className="text-cyan-400/60">ROS2 BRIDGE: NOT CONNECTED (no hardware on this PC)</span>
          </div>
          {serviceStatus?.robot_state && (
            <div className="text-[10px] text-cyan-200">
              BATTERY: {serviceStatus.robot_state.battery_level}% · POSE X:{serviceStatus.robot_state.pose?.x?.toFixed?.(2) ?? serviceStatus.robot_state.pose?.x} Y:{serviceStatus.robot_state.pose?.y?.toFixed?.(2) ?? serviceStatus.robot_state.pose?.y} · NAV: {serviceStatus.robot_state.navigation_status}
            </div>
          )}
        </div>

        {/* Viewport Bottom Overlay: Cartesian End-Effector Readout */}
        <div className="pointer-events-none absolute bottom-3 left-3 z-10 flex items-center gap-4 rounded border border-cyan-500/30 bg-[#040a18]/90 px-4 py-2 text-[11px] backdrop-blur-md">
          <div className="flex items-center gap-1.5 font-bold text-[#00e5ff]">
            <span>TCP POSE:</span>
          </div>
          <div className="text-cyan-100">
            X: <span className="font-bold text-white">{eePose.x}</span> mm
          </div>
          <div className="text-cyan-100">
            Y: <span className="font-bold text-white">{eePose.y}</span> mm
          </div>
          <div className="text-cyan-100">
            Z: <span className="font-bold text-white">{eePose.z}</span> mm
          </div>
        </div>

        {/* Simulation Controls Overlay */}
        <div className="absolute bottom-3 right-3 z-10 flex items-center gap-2 rounded border border-cyan-500/30 bg-[#040a18]/90 p-1.5 backdrop-blur-md">
          <button
            type="button"
            onClick={() => setSimPlaying(!simPlaying)}
            className={`cursor-pointer rounded px-3 py-1 text-[11px] font-bold transition-all ${
              simPlaying
                ? 'bg-amber-500 text-black'
                : 'border border-cyan-500/40 bg-[#071530] text-[#00e5ff] hover:bg-[#00e5ff] hover:text-black'
            }`}
          >
            {simPlaying ? 'PAUSE SIM' : 'PLAY SIM'}
          </button>
          <button
            type="button"
            onClick={handleHome}
            className="cursor-pointer rounded border border-cyan-500/40 bg-[#071530] px-3 py-1 text-[11px] font-bold text-cyan-200 hover:border-cyan-400 hover:text-white"
          >
            HOME
          </button>
        </div>
      </div>

      {/* 2. RIGHT: ROBOTICS TELEMETRY & CONTROL TABS */}
      <div className="w-[340px] shrink-0 flex flex-col border-l border-cyan-500/20 bg-[#040816]">
        {/* Navigation Tabs */}
        <div className="flex border-b border-cyan-500/20 bg-[#061124] text-[10px] font-bold">
          {(['joints', 'sensors', 'ros', 'commands'] as const).map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={`flex-1 py-2 text-center uppercase tracking-wider transition-colors cursor-pointer ${
                activeTab === tab
                  ? 'border-b-2 border-[#00e5ff] bg-[#00e5ff]/15 text-[#00e5ff]'
                  : 'text-cyan-300/60 hover:text-white'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Notification Banner */}
        {statusNotice && (
          <div className="bg-amber-500/20 border-b border-amber-500/40 px-3 py-1.5 text-[10px] text-amber-300 text-center animate-pulse">
            {statusNotice}
          </div>
        )}

        {/* Tab 1: Joint Configuration & Angles */}
        {activeTab === 'joints' && (
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            <div className="text-[10px] tracking-widest text-cyan-400/60 border-b border-cyan-500/20 pb-1">
              FORWARD KINEMATICS (JOINT ANGLES)
            </div>

            {(['j1', 'j2', 'j3', 'j4', 'j5', 'j6'] as const).map((jKey, idx) => {
              const labels = [
                'J1: Base Yaw',
                'J2: Shoulder Pitch',
                'J3: Elbow Pitch',
                'J4: Forearm Roll',
                'J5: Wrist Pitch',
                'J6: Tool Flange Roll',
              ]
              const minMax: Record<string, [number, number]> = {
                j1: [-180, 180],
                j2: [-90, 90],
                j3: [-135, 135],
                j4: [-180, 180],
                j5: [-100, 100],
                j6: [-360, 360],
              }
              const [min, max] = minMax[jKey]
              return (
                <div key={jKey} className="space-y-1">
                  <div className="flex justify-between text-[11px]">
                    <span className="text-cyan-200">{labels[idx]}</span>
                    <span className="font-bold text-[#00e5ff]">{Math.round(joints[jKey])}°</span>
                  </div>
                  <input
                    type="range"
                    min={min}
                    max={max}
                    value={joints[jKey]}
                    onChange={(e) =>
                      setJoints({ ...joints, [jKey]: parseFloat(e.target.value) })
                    }
                    className="w-full accent-[#00e5ff] cursor-pointer"
                  />
                  <div className="flex justify-between text-[8px] text-cyan-500/50">
                    <span>{min}°</span>
                    <span>{max}°</span>
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {/* Tab 2: Sensors Telemetry */}
        {activeTab === 'sensors' && (
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            <div className="text-[10px] tracking-widest text-cyan-400/60 border-b border-cyan-500/20 pb-1">
              INTEGRATED SENSORS TELEMETRY
            </div>
            <div className="rounded border border-amber-500/40 bg-amber-500/10 px-2.5 py-1.5 text-[10px] text-amber-300">
              SIMULATED READINGS — no physical sensors are connected to this workstation.
              Values below are the lab reference model, not live hardware data.
            </div>
            <div className="rounded border border-cyan-500/20 bg-[#020610] p-2.5 space-y-1 text-[11px]">
              <div className="text-[#00e5ff] font-bold">6-AXIS FORCE / TORQUE SENSOR</div>
              <div className="flex justify-between text-cyan-200">
                <span>Fx: +2.1 N</span>
                <span>Fy: -0.4 N</span>
                <span>Fz: +14.8 N</span>
              </div>
              <div className="flex justify-between text-cyan-200">
                <span>Tx: 0.12 Nm</span>
                <span>Ty: 0.04 Nm</span>
                <span>Tz: 0.31 Nm</span>
              </div>
            </div>

            <div className="rounded border border-cyan-500/20 bg-[#020610] p-2.5 space-y-1 text-[11px]">
              <div className="text-[#00e5ff] font-bold">IMU ACCELEROMETER & GYRO</div>
              <div className="flex justify-between text-cyan-200">
                <span>Roll rate: 0.02 rad/s</span>
                <span>Pitch rate: 0.01 rad/s</span>
              </div>
              <div className="text-cyan-400/60 text-[10px]">Temperature: 34.2 °C (Nominal)</div>
            </div>

            <div className="rounded border border-cyan-500/20 bg-[#020610] p-2.5 space-y-1 text-[11px]">
              <div className="text-[#00e5ff] font-bold">OPTICAL GRIPPER DISTANCE</div>
              <div className="text-emerald-400 font-bold">Target In Range: 42.5 mm</div>
            </div>
          </div>
        )}

        {/* Tab 3: ROS2 Node & Topic Status */}
        {activeTab === 'ros' && (
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            <div className="text-[10px] tracking-widest text-cyan-400/60 border-b border-cyan-500/20 pb-1">
              ROS2 / MICRO-ROS MIDDLEWARE
            </div>
            <div className="rounded border border-cyan-500/30 bg-[#020610] px-2.5 py-1.5 text-[10px] text-cyan-300">
              SERVICE: {serviceOnline === null ? 'QUERYING BACKEND…' : serviceOnline ? 'J.A.R.V.I.S. ROBOTICS SERVICE ONLINE (SIMULATION MODE)' : 'BACKEND OFFLINE — NO SERVICE'} · ROS2 DAEMON: ABSENT ON THIS OS, BRIDGE UNAVAILABLE
            </div>
            <div className="space-y-1 text-[11px]">
              <div className="flex justify-between border-b border-cyan-500/10 py-1">
                <span className="text-cyan-400/60">NODE NAME</span>
                <span className="text-cyan-100 font-bold">{serviceOnline ? '/jarvis_robotics_service' : '— offline —'}</span>
              </div>
              <div className="flex justify-between border-b border-cyan-500/10 py-1">
                <span className="text-cyan-400/60">EXECUTION MODE</span>
                <span className="text-amber-400 font-bold">{serviceStatus?.simulation ? 'SIMULATED' : 'LIVE'}</span>
              </div>
              <div className="flex justify-between border-b border-cyan-500/10 py-1">
                <span className="text-cyan-400/60">ROBOT MODE</span>
                <span className="text-cyan-100 font-bold">{serviceStatus?.robot_state?.mode ?? '—'}</span>
              </div>
              <div className="flex justify-between border-b border-cyan-500/10 py-1">
                <span className="text-cyan-400/60">NAVIGATION</span>
                <span className="text-cyan-100 font-bold">{serviceStatus?.navigation?.status ?? serviceStatus?.robot_state?.navigation_status ?? '—'}</span>
              </div>
              <div className="flex justify-between border-b border-cyan-500/10 py-1">
                <span className="text-cyan-400/60">MAPPED LOCATIONS</span>
                <span className="text-[#00e5ff] font-bold">{serviceStatus?.semantic_map?.total_locations ?? serviceStatus?.semantic_map?.location_count ?? 0}</span>
              </div>
            </div>
            <div className="text-[9px] text-cyan-500/50 leading-relaxed">
              /joint_states, /tf and trajectory controller figures require a running ROS2 domain; no
              ROS2 environment is installed on this machine, so those rates are not reported here.
            </div>
          </div>
        )}

        {/* Tab 4: Autonomous Robotic Commands */}
        {activeTab === 'commands' && (
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            <div className="text-[10px] tracking-widest text-cyan-400/60 border-b border-cyan-500/20 pb-1">
              MANIPULATOR COMMAND ACTIONS
            </div>
            <button
              type="button"
              onClick={handleHome}
              className="w-full rounded border border-cyan-500/40 bg-[#071530] py-2 font-mono text-[11px] font-bold text-cyan-200 hover:border-[#00e5ff] hover:text-white transition-all cursor-pointer"
            >
              MOVE TO HOME POSITION
            </button>
            <button
              type="button"
              onClick={handlePickAndPlace}
              className="w-full rounded border border-cyan-500/40 bg-[#071530] py-2 font-mono text-[11px] font-bold text-cyan-200 hover:border-[#00e5ff] hover:text-white transition-all cursor-pointer"
            >
              RUN PICK & PLACE ROUTINE
            </button>
            <button
              type="button"
              onClick={() => {
                playHudChirp()
                setJoints((j) => ({ ...j, j6: j.j6 + 45 }))
                flashNotice('Gripper rotated +45°')
              }}
              className="w-full rounded border border-cyan-500/40 bg-[#071530] py-2 font-mono text-[11px] font-bold text-cyan-200 hover:border-[#00e5ff] hover:text-white transition-all cursor-pointer"
            >
              ROTATE END-EFFECTOR (+45°)
            </button>
            <div className="pt-2">
              <button
                type="button"
                onClick={handleEmergencyStop}
                className="w-full rounded border border-rose-500 bg-rose-950/80 py-2.5 font-mono text-[11px] font-extrabold text-rose-300 hover:bg-rose-900 transition-all cursor-pointer shadow-[0_0_12px_rgba(244,63,94,0.4)]"
              >
                EMERGENCY STOP (E-STOP)
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
