import { useState, useEffect } from 'react'

interface TestResult {
  name: string
  category: string
  status: 'PASS' | 'FAIL' | 'RUNNING' | 'ERROR' | 'SKIPPED'
  duration_ms: number
  message?: string
  error?: string
  timestamp: string
}

interface DiagnosticsReport {
  total_tests: number
  passed: number
  failed: number
  errors: number
  skipped: number
  total_duration_ms: number
  system_health: string
  timestamp: string
  results: TestResult[]
}

export function DiagnosticsDashboard() {
  const [report, setReport] = useState<DiagnosticsReport | null>(null)
  const [isRunning, setIsRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const runDiagnostics = async () => {
    setIsRunning(true)
    setError(null)

    try {
      const res = await fetch('/api/diagnostics/run', { method: 'POST' })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setReport(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setIsRunning(false)
    }
  }

  const loadLatestReport = async () => {
    try {
      const res = await fetch('/api/diagnostics/latest')
      if (res.ok) {
        const data = await res.json()
        if (data.report) setReport(data)
      }
    } catch (err) {
      console.error('Failed to load diagnostics:', err)
    }
  }

  useEffect(() => {
    loadLatestReport()
  }, [])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'PASS': return 'text-green-400 bg-green-400/10 border-green-400/30'
      case 'FAIL': return 'text-red-400 bg-red-400/10 border-red-400/30'
      case 'RUNNING': return 'text-blue-400 bg-blue-400/10 border-blue-400/30 animate-pulse'
      case 'ERROR': return 'text-orange-400 bg-orange-400/10 border-orange-400/30'
      case 'SKIPPED': return 'text-gray-400 bg-gray-400/10 border-gray-400/30'
      default: return 'text-gray-400 bg-gray-400/10 border-gray-400/30'
    }
  }

  const getHealthColor = (health: string) => {
    switch (health) {
      case 'EXCELLENT': return 'text-green-400'
      case 'GOOD': return 'text-blue-400'
      case 'DEGRADED': return 'text-yellow-400'
      case 'CRITICAL': return 'text-red-400'
      default: return 'text-gray-400'
    }
  }

  return (
    <div className="flex flex-col gap-4 p-6 bg-black/40 backdrop-blur-xl border border-cyan-500/20 rounded-lg">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-cyan-400 font-mono">SYSTEM DIAGNOSTICS</h2>
        <button
          onClick={runDiagnostics}
          disabled={isRunning}
          className="px-4 py-2 bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-400/50 rounded text-cyan-300 font-mono text-sm disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          {isRunning ? 'RUNNING...' : 'RUN DIAGNOSTICS'}
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-500/10 border border-red-400/30 rounded text-red-300 text-sm">
          Error: {error}
        </div>
      )}

      {report && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="flex flex-col items-center p-3 bg-blue-500/10 border border-blue-400/30 rounded">
              <div className="text-3xl font-bold text-blue-400 font-mono">{report.total_tests}</div>
              <div className="text-xs text-blue-300 font-mono">TOTAL</div>
            </div>
            <div className="flex flex-col items-center p-3 bg-green-500/10 border border-green-400/30 rounded">
              <div className="text-3xl font-bold text-green-400 font-mono">{report.passed}</div>
              <div className="text-xs text-green-300 font-mono">PASSED</div>
            </div>
            <div className="flex flex-col items-center p-3 bg-red-500/10 border border-red-400/30 rounded">
              <div className="text-3xl font-bold text-red-400 font-mono">{report.failed}</div>
              <div className="text-xs text-red-300 font-mono">FAILED</div>
            </div>
            <div className="flex flex-col items-center p-3 bg-orange-500/10 border border-orange-400/30 rounded">
              <div className="text-3xl font-bold text-orange-400 font-mono">{report.errors}</div>
              <div className="text-xs text-orange-300 font-mono">ERRORS</div>
            </div>
            <div className="flex flex-col items-center p-3 bg-gray-500/10 border border-gray-400/30 rounded">
              <div className="text-3xl font-bold text-gray-400 font-mono">{report.skipped}</div>
              <div className="text-xs text-gray-300 font-mono">SKIPPED</div>
            </div>
          </div>

          <div className="flex items-center justify-between p-3 bg-black/40 border border-cyan-500/20 rounded">
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-400 font-mono">SYSTEM HEALTH:</span>
              <span className={`text-xl font-bold font-mono ${getHealthColor(report.system_health)}`}>
                {report.system_health}
              </span>
            </div>
            <div className="text-xs text-gray-500 font-mono">
              Duration: {report.total_duration_ms.toFixed(0)}ms
            </div>
          </div>

          <div className="flex flex-col gap-2 max-h-96 overflow-y-auto">
            {report.results.map((result, idx) => (
              <div
                key={idx}
                className={`flex items-center justify-between p-3 border rounded ${getStatusColor(result.status)}`}
              >
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm font-bold">{result.name}</span>
                    <span className="text-xs opacity-70">[{result.category}]</span>
                  </div>
                  {result.message && (
                    <div className="text-xs opacity-80">{result.message}</div>
                  )}
                  {result.error && (
                    <div className="text-xs text-red-300">Error: {result.error}</div>
                  )}
                </div>
                <div className="flex flex-col items-end gap-1">
                  <span className="font-mono text-sm font-bold">{result.status}</span>
                  <span className="text-xs opacity-70">{result.duration_ms.toFixed(0)}ms</span>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {!report && !isRunning && (
        <div className="text-center py-8 text-gray-500 font-mono">
          No diagnostics data available. Click "RUN DIAGNOSTICS" to start.
        </div>
      )}
    </div>
  )
}
