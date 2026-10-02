import { useState, useCallback } from 'react'

export default function TwinCellPanel() {
  const [report, setReport] = useState<any>(null)
  const [deviations, setDeviations] = useState<any[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [runVision, setRunVision] = useState(false)
  const [expectedJson, setExpectedJson] = useState('{"mode": "IDLE", "battery_level": 95}')
  const [entity, setEntity] = useState('robot-1')

  const inspect = useCallback(async () => {
    setBusy(true)
    setError(null)
    try {
      const res = await fetch('/api/robot-cell/inspect', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cell: 'robot_cell_1', run_vision: runVision }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data?.detail || 'inspection failed')
      setReport(data)
      const dev = await fetch('/api/twin/deviations?limit=20')
      if (dev.ok) setDeviations((await dev.json()).deviations || [])
    } catch (e: any) {
      setError(`Inspection failed: ${e?.message || e}`)
    } finally {
      setBusy(false)
    }
  }, [runVision])

  const setExpected = async () => {
    setError(null)
    try {
      const state = JSON.parse(expectedJson)
      const res = await fetch('/api/twin/expected', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entity, state, source: 'operator' }),
      })
      if (!res.ok) throw new Error('set expected failed')
    } catch (e: any) {
      setError(`Expected-state: ${e?.message || e}`)
    }
  }

  const snapActualFromRobot = async () => {
    setError(null)
    try {
      const res = await fetch('/api/robotics/state')
      if (!res.ok) throw new Error('robot state unavailable')
      const state = await res.json()
      await fetch('/api/twin/actual', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entity, state, source: 'robotics_service', simulated: true }),
      })
      const dev = await fetch('/api/twin/deviations?limit=20')
      if (dev.ok) setDeviations((await dev.json()).deviations || [])
    } catch (e: any) {
      setError(`Snapshot: ${e?.message || e}`)
    }
  }

  return (
    <div className="flex h-full w-full flex-col gap-3 overflow-y-auto bg-[#030612] p-4 font-mono text-white">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-bold tracking-[0.2em] text-[#00e5ff]">DIGITAL TWIN + ROBOT CELL</span>
        <label className="flex items-center gap-1 text-[11px] text-cyan-200">
          <input type="checkbox" checked={runVision} onChange={(e) => setRunVision(e.target.checked)} />
          run vision frame
        </label>
        <button type="button" disabled={busy} onClick={inspect} className="rounded border border-cyan-500/50 bg-cyan-500/15 px-3 py-1 text-xs font-bold text-cyan-200 hover:bg-cyan-500/25 disabled:opacity-50">
          {busy ? 'INSPECTING…' : 'INSPECT ROBOT CELL'}
        </button>
      </div>

      {error && <div className="rounded border border-red-500/40 bg-red-500/10 px-3 py-2 text-xs text-red-300">{error}</div>}

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <div className="rounded border border-cyan-500/30 bg-[#040a18]/80 p-3 text-[11px]">
          <div className="mb-2 font-bold tracking-widest text-cyan-300">EXPECTED vs ACTUAL (TWIN)</div>
          <div className="mb-1 flex gap-1">
            <input value={entity} onChange={(e) => setEntity(e.target.value)} className="w-28 rounded border border-cyan-500/30 bg-[#030713] px-2 py-1 text-[11px] text-white" placeholder="entity" />
            <button type="button" onClick={setExpected} className="rounded border border-cyan-500/50 bg-cyan-500/15 px-2 py-1 font-bold text-cyan-200 hover:bg-cyan-500/25">SET EXPECTED</button>
            <button type="button" onClick={snapActualFromRobot} className="rounded border border-cyan-500/50 bg-cyan-500/15 px-2 py-1 font-bold text-cyan-200 hover:bg-cyan-500/25">SNAPSHOT ROBOT → ACTUAL</button>
          </div>
          <textarea value={expectedJson} onChange={(e) => setExpectedJson(e.target.value)} rows={3} className="w-full rounded border border-cyan-500/30 bg-[#030713] px-2 py-1 font-mono text-[11px] text-white" />
          <div className="mt-2">
            <div className="font-bold text-cyan-300">DEVIATIONS ({deviations.length})</div>
            <div className="max-h-36 space-y-1 overflow-y-auto">
              {deviations.slice().reverse().map((d, i) => (
                <div key={i} className="rounded border border-orange-500/30 bg-orange-500/5 px-2 py-1 text-orange-200">
                  {d.entity}: {d.mismatch_count} mismatch(es)
                  {(d.mismatches || []).slice(0, 3).map((m: any, j: number) => (
                    <div key={j} className="text-[10px] text-orange-200/80">{m.path}: expected {String(m.expected)} vs actual {String(m.actual)}</div>
                  ))}
                </div>
              ))}
              {deviations.length === 0 && <div className="text-cyan-100/50">No deviations recorded. Set expected state, snapshot actual, and compare.</div>}
            </div>
          </div>
        </div>

        <div className="rounded border border-cyan-500/30 bg-[#040a18]/80 p-3 text-[11px]">
          <div className="mb-2 font-bold tracking-widest text-cyan-300">CELL REPORT</div>
          {!report && <div className="text-cyan-100/50">Run an inspection to correlate robot, PLC, vision, alarms and security.</div>}
          {report && (
            <div className="space-y-1">
              <div>REPORT: <span className="font-bold text-white">{report.report_id}</span> · {new Date(report.inspected_at * 1000).toLocaleTimeString()} · {report.duration_ms}ms</div>
              <div>VERDICT: <span className="font-bold text-[#00e5ff]">{report.verdict}</span></div>
              <div>FINDINGS: <span className="font-bold text-white">{report.finding_count}</span> · VALIDATION: {report.validation?.ok ? 'complete' : 'partial'}</div>
              {(report.findings || []).map((f: any, i: number) => (
                <div key={i} className="rounded border border-cyan-500/20 bg-[#030713] px-2 py-1">[{f.severity}] {f.area}: {f.message}</div>
              ))}
              {report.errors?.length > 0 && <div className="text-yellow-300">section errors: {report.errors.join('; ').slice(0, 200)}</div>}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
