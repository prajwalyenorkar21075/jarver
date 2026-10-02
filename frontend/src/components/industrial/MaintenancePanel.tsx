import { useState, useEffect, useCallback } from 'react'

export default function MaintenancePanel() {
  const [status, setStatus] = useState<any>(null)
  const [analysis, setAnalysis] = useState<any>(null)
  const [health, setHealth] = useState<Record<string, any>>({})
  const [alerts, setAlerts] = useState<any[]>([])
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [threshold, setThreshold] = useState({ signal: 'vibration_rms', warn: '4.5', critical: '7.1', unit: 'mm/s' })

  const load = useCallback(async () => {
    try {
      const [st, al] = await Promise.all([
        fetch('/api/maintenance/status'),
        fetch('/api/maintenance/alerts?limit=30'),
      ])
      if (st.ok) setStatus(await st.json())
      if (al.ok) setAlerts((await al.json()).alerts || [])
    } catch (e: any) {
      setError(`Maintenance service unreachable: ${e?.message || e}`)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const runAnalysis = async () => {
    setBusy(true)
    setError(null)
    try {
      const res = await fetch('/api/maintenance/analyze', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })
      const data = await res.json()
      if (!res.ok) throw new Error(data?.detail || 'analysis failed')
      setAnalysis(data)
      setHealth(data.equipment_health || {})
      const al = await fetch('/api/maintenance/alerts?limit=30')
      if (al.ok) setAlerts((await al.json()).alerts || [])
    } catch (e: any) {
      setError(`Analysis: ${e?.message || e}`)
    } finally {
      setBusy(false)
    }
  }

  const collect = async (source: string) => {
    setBusy(true)
    try {
      const res = await fetch('/api/maintenance/collect', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ source }) })
      const data = await res.json()
      if (!res.ok && !data?.success) throw new Error(data?.error || data?.detail || 'collect failed')
      await load()
    } catch (e: any) {
      setError(`Collect (${source}): ${e?.message || e}`)
    } finally {
      setBusy(false)
    }
  }

  const saveThreshold = async () => {
    try {
      const res = await fetch('/api/maintenance/thresholds', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ signal: threshold.signal, warn: Number(threshold.warn), critical: Number(threshold.critical), unit: threshold.unit }),
      })
      if (!res.ok) throw new Error('save failed')
      await load()
    } catch (e: any) {
      setError(`Threshold: ${e?.message || e}`)
    }
  }

  return (
    <div className="flex h-full w-full flex-col gap-3 overflow-y-auto bg-[#030612] p-4 font-mono text-white">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-bold tracking-[0.2em] text-[#00e5ff]">PREDICTIVE MAINTENANCE</span>
        <span className="rounded border border-cyan-500/40 bg-cyan-500/10 px-2 py-0.5 text-[10px] text-cyan-300">
          REAL SAMPLES ONLY — NO SYNTHETIC DATA
        </span>
      </div>

      {error && <div className="rounded border border-red-500/40 bg-red-500/10 px-3 py-2 text-xs text-red-300">{error}</div>}

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
        <div className="rounded border border-cyan-500/30 bg-[#040a18]/80 p-3 text-[11px]">
          <div className="mb-2 font-bold tracking-widest text-cyan-300">DATA STORE</div>
          <div>TRACKED SIGNALS: <span className="font-bold text-white">{status?.tracked_signals ?? '—'}</span></div>
          <div>TOTAL SAMPLES: <span className="font-bold text-white">{status?.total_samples ?? '—'}</span></div>
          <div>DEVICES: <span className="font-bold text-white">{(status?.devices || []).join(', ') || '—'}</span></div>
          <div className="mt-2 flex flex-wrap gap-1">
            <button type="button" disabled={busy} onClick={() => collect('host')} className="rounded border border-cyan-500/50 bg-cyan-500/15 px-2 py-1 text-[11px] font-bold text-cyan-200 hover:bg-cyan-500/25 disabled:opacity-50">COLLECT HOST</button>
            <button type="button" disabled={busy} onClick={() => collect('robot')} className="rounded border border-cyan-500/50 bg-cyan-500/15 px-2 py-1 text-[11px] font-bold text-cyan-200 hover:bg-cyan-500/25 disabled:opacity-50">COLLECT ROBOT</button>
            <button type="button" disabled={busy} onClick={runAnalysis} className="rounded border border-emerald-500/50 bg-emerald-500/15 px-2 py-1 text-[11px] font-bold text-emerald-200 hover:bg-emerald-500/25 disabled:opacity-50">
              {busy ? 'WORKING…' : 'RUN ANALYSIS'}
            </button>
          </div>
        </div>

        <div className="rounded border border-cyan-500/30 bg-[#040a18]/80 p-3 text-[11px]">
          <div className="mb-2 font-bold tracking-widest text-cyan-300">EQUIPMENT HEALTH</div>
          {Object.keys(health).length === 0 && <div className="text-cyan-100/50">Run analysis to compute health from stored samples.</div>}
          {Object.entries(health).map(([dev, h]: any) => (
            <div key={dev} className="mb-1 rounded border border-cyan-500/20 bg-[#030713] px-2 py-1">
              <span className="font-bold text-white">{dev}</span>
              <span className="ml-2 text-[#00e5ff]">{h.health_score ?? h.status}</span>
              <span className="ml-2 text-cyan-100/60">{h.status}</span>
              {h.health_score == null && <div className="mt-1 text-[10px] text-yellow-300">{h.message}</div>}
            </div>
          ))}
        </div>

        <div className="rounded border border-cyan-500/30 bg-[#040a18]/80 p-3 text-[11px]">
          <div className="mb-2 font-bold tracking-widest text-cyan-300">THRESHOLDS (FROM DATASHEET)</div>
          <div className="flex flex-wrap gap-1">
            <input value={threshold.signal} onChange={(e) => setThreshold({ ...threshold, signal: e.target.value })} className="w-32 rounded border border-cyan-500/30 bg-[#030713] px-2 py-1 text-[11px] text-white" placeholder="signal" />
            <input value={threshold.warn} onChange={(e) => setThreshold({ ...threshold, warn: e.target.value })} className="w-16 rounded border border-cyan-500/30 bg-[#030713] px-2 py-1 text-[11px] text-white" placeholder="warn" />
            <input value={threshold.critical} onChange={(e) => setThreshold({ ...threshold, critical: e.target.value })} className="w-16 rounded border border-cyan-500/30 bg-[#030713] px-2 py-1 text-[11px] text-white" placeholder="crit" />
            <input value={threshold.unit} onChange={(e) => setThreshold({ ...threshold, unit: e.target.value })} className="w-16 rounded border border-cyan-500/30 bg-[#030713] px-2 py-1 text-[11px] text-white" placeholder="unit" />
            <button type="button" onClick={saveThreshold} className="rounded border border-cyan-500/50 bg-cyan-500/15 px-2 py-1 font-bold text-cyan-200 hover:bg-cyan-500/25">SAVE</button>
          </div>
          <div className="mt-1 text-cyan-100/60">CONFIGURED: {(status?.thresholds_configured || []).join(', ')}</div>
        </div>
      </div>

      {analysis && (
        <div className="rounded border border-cyan-500/30 bg-[#040a18]/80 p-3 text-[11px]">
          <div className="mb-2 font-bold tracking-widest text-cyan-300">ANALYSIS — {analysis.signals_analyzed} SIGNALS</div>
          <div className="mb-2 space-y-1">
            {(analysis.recommendations || []).map((r: string, i: number) => (
              <div key={i} className="rounded border border-emerald-500/20 bg-emerald-500/5 px-2 py-1 text-emerald-200">▸ {r}</div>
            ))}
          </div>
          <div className="space-y-1">
            {(analysis.results || []).map((r: any) => (
              <div key={`${r.device_id}:${r.signal}`} className="rounded border border-cyan-500/20 bg-[#030713] px-2 py-1">
                <span className="font-bold text-white">{r.device_id}.{r.signal}</span>
                <span className="ml-2 text-cyan-100/70">n={r.samples} mean={r.features?.mean?.toFixed?.(3)} trend={r.trend?.direction || '—'}</span>
                {r.threshold?.configured && <span className="ml-2 text-yellow-300">threshold: {r.threshold.status}</span>}
                {(r.anomalies?.anomaly_count || 0) > 0 && <span className="ml-2 text-orange-300">anomalies: {r.anomalies.anomaly_count}</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="rounded border border-cyan-500/30 bg-[#040a18]/80 p-3 text-[11px]">
        <div className="mb-2 font-bold tracking-widest text-cyan-300">ALERTS ({alerts.length})</div>
        <div className="max-h-40 space-y-1 overflow-y-auto">
          {alerts.map((a) => (
            <div key={a.id} className="rounded border border-yellow-500/30 bg-yellow-500/5 px-2 py-1 text-yellow-200">
              [{a.severity}] {a.device_id}.{a.signal} — {a.message}
            </div>
          ))}
          {alerts.length === 0 && <div className="text-cyan-100/50">No alerts stored.</div>}
        </div>
      </div>
    </div>
  )
}
