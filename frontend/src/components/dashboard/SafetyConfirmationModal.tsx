import { useEffect } from 'react'
import { useJarvisStore } from '../../store/useJarvisStore'

export default function SafetyConfirmationModal() {
  const pendingSafetyConfirmation = useJarvisStore((s) => s.pendingSafetyConfirmation)
  const confirmSafetyAction = useJarvisStore((s) => s.confirmSafetyAction)

  useEffect(() => {
    if (!pendingSafetyConfirmation) return

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        confirmSafetyAction('cancel')
      } else if (e.key === 'Enter') {
        confirmSafetyAction('confirm')
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [pendingSafetyConfirmation, confirmSafetyAction])

  if (!pendingSafetyConfirmation) return null

  const isShutdown = pendingSafetyConfirmation.action.toLowerCase().includes('shutdown')
  const isRestart = pendingSafetyConfirmation.action.toLowerCase().includes('restart')

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 backdrop-blur-md bg-black/80 animate-in fade-in duration-200">
      {/* Sci-Fi Holographic Dialog Container */}
      <div className="relative w-full max-w-lg rounded-2xl border-2 border-red-500/80 bg-[#070b18] p-6 shadow-[0_0_50px_rgba(239,68,68,0.4)] overflow-hidden font-mono">
        {/* Subtle Cybernetic Grid Pattern */}
        <div
          className="pointer-events-none absolute inset-0 opacity-15"
          style={{
            backgroundImage:
              'linear-gradient(to right, rgba(239, 68, 68, 0.3) 1px, transparent 1px), linear-gradient(to bottom, rgba(239, 68, 68, 0.2) 1px, transparent 1px)',
            backgroundSize: '24px 24px',
          }}
        />

        {/* Warning Accent Bars */}
        <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-red-600 via-amber-500 to-red-600 animate-pulse" />

        {/* Header Icon + Title */}
        <div className="relative z-10 flex items-start gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-red-500/60 bg-red-950/60 text-red-400 shadow-[0_0_15px_rgba(239,68,68,0.3)]">
            <svg className="h-6 w-6 animate-pulse" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 9v4" />
              <path d="M12 17h.01" />
              <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
            </svg>
          </div>

          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className="rounded bg-red-500/20 px-2 py-0.5 text-[10px] font-extrabold tracking-widest text-red-400 uppercase border border-red-500/40">
                CRITICAL GATE PROTOCOL
              </span>
              <span className="h-2 w-2 rounded-full bg-red-500 animate-ping" />
            </div>

            <h3 className="mt-1 text-lg font-black tracking-wider text-white">
              {isShutdown
                ? 'SYSTEM SHUTDOWN DIRECTIVE'
                : isRestart
                ? 'SYSTEM REBOOT DIRECTIVE'
                : 'SECURITY AUTHORIZATION REQUIRED'}
            </h3>
            <p className="text-xs text-red-300/80 tracking-wide">
              TARGET: <span className="font-bold text-white uppercase">{pendingSafetyConfirmation.action}</span>
            </p>
          </div>
        </div>

        {/* Prompt Content */}
        <div className="relative z-10 mt-5 rounded-xl border border-red-500/30 bg-[#0a1224] p-4 text-sm leading-relaxed text-red-100">
          <p className="font-semibold text-white/95">
            "{pendingSafetyConfirmation.prompt}"
          </p>
          <p className="mt-2 text-xs text-red-300/70">
            Jarvis safety protocols require human authorization for destructive or power-state commands.
            This action will be automatically aborted in 60 seconds if unconfirmed.
          </p>
        </div>

        {/* Vernacular Voice Tip */}
        <div className="relative z-10 mt-3 flex items-center gap-2 text-[11px] text-cyan-300/80">
          <svg className="h-3.5 w-3.5 text-cyan-400" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
            <path d="M19 10v1a7 7 0 0 1-14 0v-1" />
          </svg>
          <span>You can also speak: <strong>"Confirm"</strong>, <strong>"हो"</strong>, or <strong>"Cancel"</strong>, <strong>"नाही"</strong></span>
        </div>

        {/* Action Buttons */}
        <div className="relative z-10 mt-6 flex items-center justify-end gap-3">
          {/* Abort Button */}
          <button
            type="button"
            onClick={() => confirmSafetyAction('cancel')}
            className="cursor-pointer flex items-center gap-2 rounded-xl border border-cyan-400/60 bg-[#081a38] px-5 py-2.5 text-xs font-bold text-cyan-300 hover:bg-cyan-500/20 hover:border-cyan-300 hover:text-white transition-all active:scale-95 shadow-[0_0_15px_rgba(0,229,255,0.15)]"
          >
            <span>✕</span>
            <span>ABORT ACTION [ESC]</span>
          </button>

          {/* Confirm Button */}
          <button
            type="button"
            onClick={() => confirmSafetyAction('confirm')}
            className="cursor-pointer flex items-center gap-2 rounded-xl border border-red-400 bg-red-600 px-6 py-2.5 text-xs font-black text-white hover:bg-red-500 hover:shadow-[0_0_25px_rgba(239,68,68,0.7)] transition-all active:scale-95 animate-pulse"
          >
            <span>⚡</span>
            <span>AUTHORIZE &amp; PROCEED [ENTER]</span>
          </button>
        </div>
      </div>
    </div>
  )
}
