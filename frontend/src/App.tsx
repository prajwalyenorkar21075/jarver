import TopNavBar from './components/dashboard/TopNavBar'
import LeftSidebar from './components/dashboard/LeftSidebar'
import WeatherWidget from './components/dashboard/WeatherWidget'
import WorldClockWidget from './components/dashboard/WorldClockWidget'
import ScheduleWidget from './components/dashboard/ScheduleWidget'
import JarvisNebulaCore from './components/dashboard/JarvisNebulaCore'
import QuickActionsWidget from './components/dashboard/QuickActionsWidget'
import SystemStatusWidget from './components/dashboard/SystemStatusWidget'
import RecentFilesWidget from './components/dashboard/RecentFilesWidget'
import BottomBar from './components/dashboard/BottomBar'
import JarvisBrowserPanel from './components/JarvisBrowserPanel'
import { useJarvisStore } from './store/useJarvisStore'

export default function App() {
  const systemNotice = useJarvisStore((s) => s.systemNotice)

  return (
    <div className="relative flex h-screen max-h-screen w-full flex-col justify-between overflow-hidden bg-black font-sans select-none text-white">
      {/* 1. Deep Obsidian Stark Lab Backdrop */}
      <div className="pointer-events-none fixed inset-0 z-0 bg-[#030612]" />
      {/* Volumetric Hologram Core Illumination matching Iron Man Lab */}
      <div
        className="pointer-events-none fixed inset-0 z-0 opacity-80"
        style={{
          background: 'radial-gradient(ellipse 55% 45% at 50% 50%, rgba(255, 145, 0, 0.13), rgba(0, 229, 255, 0.05), transparent 75%)',
        }}
      />

      {/* Subtle Cybernetic Grid Overlay */}
      <div
        className="pointer-events-none fixed inset-0 z-0 opacity-15"
        style={{
          backgroundImage:
            'linear-gradient(to right, rgba(0, 229, 255, 0.2) 1px, transparent 1px), linear-gradient(to bottom, rgba(0, 229, 255, 0.12) 1px, transparent 1px)',
          backgroundSize: '48px 48px',
          maskImage: 'radial-gradient(ellipse 80% 70% at 50% 50%, black 20%, transparent 80%)',
          WebkitMaskImage: 'radial-gradient(ellipse 80% 70% at 50% 50%, black 20%, transparent 80%)',
        }}
      />

      {/* Desktop Automation Action Toast */}
      {systemNotice && (
        <div className="fixed top-16 left-1/2 -translate-x-1/2 z-50 flex items-center gap-3 rounded-full border border-cyan-400/80 bg-[#060e20] px-6 py-2.5 font-mono text-xs text-cyan-300 transition-all">
          <span className="h-2 w-2 rounded-full bg-cyan-400 animate-ping" />
          <span className="font-bold tracking-wider text-white">PC AUTOMATION:</span>
          <span className="text-cyan-200">{systemNotice}</span>
        </div>
      )}

      {/* 2. Top Header Navigation */}
      <TopNavBar />

      {/* 3. Left Hexagonal Dock Sidebar */}
      <LeftSidebar />

      {/* 4. Main 3-Column Hologram Dashboard */}
      <main className="relative z-10 flex flex-1 items-center justify-between px-6 lg:pl-28 lg:pr-8 py-1 max-w-[1720px] mx-auto w-full gap-4 xl:gap-8 overflow-hidden">
        {/* Left Column Widgets */}
        <div className="hidden md:flex flex-col gap-3 justify-center shrink-0 w-[280px] xl:w-[320px]">
          <WeatherWidget />
          <WorldClockWidget />
          <ScheduleWidget />
        </div>

        {/* Center Stage: Cybernetic Hexagon Frame & 3D Glowing Particle Orb */}
        <div className="flex flex-1 items-center justify-center min-w-0">
          <JarvisNebulaCore />
        </div>

        {/* Right Column Widgets */}
        <div className="hidden md:flex flex-col gap-3 justify-center shrink-0 w-[280px] xl:w-[320px]">
          <QuickActionsWidget />
          <SystemStatusWidget />
          <RecentFilesWidget />
        </div>
      </main>

      {/* 5. Bottom Navigation & Media Command Bar */}
      <BottomBar />

      {/* 6. Choreographed In-App Browser Panel */}
      <JarvisBrowserPanel />
    </div>
  )
}
