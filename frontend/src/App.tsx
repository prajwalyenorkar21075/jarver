import { useEffect, useState } from 'react'
import CADTopBar from './components/CADTopBar'
import LeftSidebar from './components/dashboard/LeftSidebar'
import { CADViewport } from './components/CADViewport'
import CADCommandConsole from './components/CADCommandConsole'
import RoboticsWorkspace from './components/robotics/RoboticsWorkspace'
import IndustrialPanel from './components/industrial/IndustrialPanel'
import MaintenancePanel from './components/industrial/MaintenancePanel'
import TwinCellPanel from './components/industrial/TwinCellPanel'
import SecurityGraphPanel from './components/security/SecurityGraphPanel'
import { MemoryPanel, ProjectPanel, SettingsPanel } from './components/dashboard/SidePanels'
import JarvisBrowserPanel from './components/JarvisBrowserPanel'
import SafetyConfirmationModal from './components/dashboard/SafetyConfirmationModal'
import BiometricSecurityModal from './components/dashboard/BiometricSecurityModal'
import AutonomousCodingWorkspace from './components/coding/AutonomousCodingWorkspace'
import { DiagnosticsDashboard } from './components/dashboard/DiagnosticsDashboard'
import { CybersecurityDashboard } from './components/dashboard/CybersecurityDashboard'
import { WebSearchPanel, VisionPanel, ImageGenerationPanel, DocumentAnalysisPanel } from './components/features'
import { useJarvisStore } from './store/useJarvisStore'

type ViewMode =
  | 'cad'
  | 'dashboard'
  | 'robotics'
  | 'project'
  | 'diagnostics'
  | 'ai'
  | 'cybersecurity'
  | 'assetgraph'
  | 'industrial'
  | 'maintenance'
  | 'twincell'
  | 'memory'
  | 'settings'
  | 'search'
  | 'vision'
  | 'image'
  | 'document'

export default function App() {
  // Primary default view mode is now CAD engineering workspace
  const [viewMode, setViewMode] = useState<ViewMode>('cad')
  const systemNotice = useJarvisStore((s) => s.systemNotice)
  const fetchPersistentState = useJarvisStore((s) => s.fetchPersistentState)
  const fetchTelemetry = useJarvisStore((s) => s.fetchTelemetry)
  const fetchBiometricsStatus = useJarvisStore((s) => s.fetchBiometricsStatus)

  // Auto-restore state on PC restart / app launch
  useEffect(() => {
    fetchPersistentState()
    fetchTelemetry()
    fetchBiometricsStatus()

    const interval = setInterval(() => {
      fetchTelemetry()
      fetchBiometricsStatus()
    }, 15000)

    return () => clearInterval(interval)
  }, [fetchPersistentState, fetchTelemetry, fetchBiometricsStatus])

  // Listen for navigation events from LeftSidebar, TopBar, or command actions
  useEffect(() => {
    const handleNavigate = (e: CustomEvent) => {
      const targetView = (e.detail?.view || 'cad') as ViewMode
      setViewMode(targetView === 'dashboard' ? 'cad' : targetView)
    }

    window.addEventListener('jarvis-navigate', handleNavigate as EventListener)
    return () => window.removeEventListener('jarvis-navigate', handleNavigate as EventListener)
  }, [])

  const renderWorkspace = () => {
    switch (viewMode) {
      case 'robotics':
        return <RoboticsWorkspace />
      case 'project':
        return <ProjectPanel />
      case 'diagnostics':
      case 'ai':
        return <DiagnosticsDashboard />
      case 'cybersecurity':
        return <CybersecurityDashboard />
      case 'assetgraph':
        return <SecurityGraphPanel />
      case 'industrial':
        return <IndustrialPanel />
      case 'maintenance':
        return <MaintenancePanel />
      case 'twincell':
        return <TwinCellPanel />
      case 'memory':
        return <MemoryPanel />
      case 'settings':
        return <SettingsPanel />
      case 'search':
        return <WebSearchPanel />
      case 'vision':
        return <VisionPanel />
      case 'image':
        return <ImageGenerationPanel />
      case 'document':
        return <DocumentAnalysisPanel />
      case 'cad':
      default:
        return <CADViewport />
    }
  }

  return (
    <div className="relative flex h-screen max-h-screen w-full flex-col justify-between overflow-hidden bg-[#030612] font-sans select-none text-white">
      {/* Engineering Blueprint Grid Background */}
      <div className="pointer-events-none fixed inset-0 z-0 bg-[#030612]" />
      <div
        className="pointer-events-none fixed inset-0 z-0 opacity-15"
        style={{
          backgroundImage:
            'linear-gradient(to right, rgba(0, 229, 255, 0.15) 1px, transparent 1px), linear-gradient(to bottom, rgba(0, 229, 255, 0.08) 1px, transparent 1px)',
          backgroundSize: '40px 40px',
        }}
      />

      {/* Global Automation / Notice Toast */}
      {systemNotice && (
        <div className="fixed top-14 left-1/2 -translate-x-1/2 z-50 flex items-center gap-3 rounded-full border border-cyan-400 bg-[#051126] px-5 py-2 font-mono text-xs text-cyan-200 shadow-[0_0_20px_rgba(0,229,255,0.35)] transition-all animate-bounce">
          <span className="h-2 w-2 rounded-full bg-cyan-400 animate-ping" />
          <span className="font-bold tracking-wider text-white">J.A.R.V.I.S.:</span>
          <span className="text-cyan-200">{systemNotice}</span>
        </div>
      )}

      {/* 1. TOP CAD TOOLBAR & MENUS (Inspired by AutoCAD + J.A.R.V.I.S. Core) */}
      <CADTopBar />

      {/* 2. MIDDLE WORKSPACE AREA (Left Sidebar + Central Interactive Viewport / Workspace) */}
      <div className="relative z-10 flex min-h-0 flex-1 w-full overflow-hidden">
        {/* Left Collapsible Engineering Navigation Sidebar */}
        <LeftSidebar />

        {/* Central Workspace Canvas */}
        <main className="relative flex flex-1 min-w-0 min-h-0 flex-col overflow-hidden bg-[#030713]">
          {renderWorkspace()}
        </main>
      </div>

      {/* 3. BOTTOM AUTOCAD-STYLE COMMAND CONSOLE */}
      <CADCommandConsole />

      {/* In-App Auxiliary Workspaces & Dialogs */}
      <JarvisBrowserPanel />
      <SafetyConfirmationModal />
      <BiometricSecurityModal />
      <AutonomousCodingWorkspace />
    </div>
  )
}
