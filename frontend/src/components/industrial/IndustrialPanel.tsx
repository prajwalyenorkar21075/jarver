import { useState, useEffect, useCallback } from 'react'

interface IndustrialDevice {
  id: string
  name: string
  kind: string
  protocol: string
  address: string
  port: number
  tags: { tag: string; address: number | string; type: string; unit: string; scale?: number }[]
  cell: string
  simulated: boolean
}

interface TagReading {
  tag: string
  value: number | boolean | string
  unit: string
  quality: string
  timestamp: number
  source: string
}

export default function IndustrialPanel() {
  const [devices, setDevices] = useState<IndustrialDevice[]>([])
  const [selected, setSelected] = useState<string>('')
  const [readings, setReadings] = useState<TagReading[]>([])
  const [readErrors, setReadErrors] = useState<{ tag: string; error: string }[]>([])
  const [partial, setPartial] = useState(false)
  const [simulated, setSimulated] = useState(false)
  const [machineState, setMachineState] = useState<string>('unknown')
  const [alarms, setAlarms] = useState<any[]>([])
  const [protocols, setProtocols] = useState<Record<string, any>>({})
  const [controlMode, setControlMode] = useState('MONITORING')
  const [error, setError] = useState<string | null>(null)
  const [writeTag, setWriteTag] = useState('')
  const [writeValue, setWriteValue] = useState('')
  const [writeBusy, setWriteBusy] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)

  const flash = (msg: string) => {
    setNotice(msg)
    setTimeout(() => setNotice(null), 4000)
  }

  const loadAll = useCallback(async () => {
    try {
      const [devRes, alarmRes, protoRes] = await Promise.all([
        fetch('/api/industrial/devices'),
        fetch('/api/industrial/alarms?limit=50'),
        fetch('/api/industrial/protocols'),
      ])
      if (devRes.ok) {
        const data = await devRes.json()
        setDevices(data.devices || [])
        if (!selected && data.devices?.length) setSelected(data.devices[0].id)
      }
      if (alarmRes.ok) setAlarms((await alarmRes.json()).alarms || [])
      if (protoRes.ok) {
        const p = await protoRes.json()
        setProtocols(p)
        if (p.control_mode) setControlMode(p.control_mode)
      }
    } catch (e: any) {
      setError(`Industrial service unreachable: ${e?.message || e}`)
    }
  }, [selected])

  useEffect(() => {
    loadAll()
  }, [loadAll])

  const readDevice = useCallback(async (deviceId: string) => {
    if (!deviceId) return
    setError(null)
    try {
      const res = await fetch(`/api/industrial/device/${encodeURIComponent(deviceId)}/read`)
      const data = await res.json()
      if (!res.ok) throw new Error(data?.detail || 'read failed')
      setReadings(data.readings || [])
      setReadErrors(data.errors || [])
      setPartial(!!data.partial)
      setSimulated(!!data.simulated)
      const stRes = await fetch(`/api/industrial/device/${encodeURIComponent(deviceId)}/state`)
      if (stRes.ok) setMachineState((await stRes.json()).state || 'unknown')
    } catch (e: any) {
      setError(`Read failed: ${e?.message || e}`)
    }
  }, [])

  useEffect(() => {
    if (selected) readDevice(selected)
  }, [selected, readDevice])

  const handleWrite = async () => {
    if (!writeTag || !writeValue) {
      flash('Pick a tag and a value first.')
      return
    }
    setWriteBusy(true)
    try {
      // First attempt without authorization — the backend will block CONTROL
      // actions and tell us to confirm explicitly.
      let res = await fetch(
        `/api/industrial/device/${encodeURIComponent(selected)}/tag/${encodeURIComponent(writeTag)}/write`,
        { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ value: Number(writeValue) || writeValue }) }
      )
      if (res.status === 403) {
        const detail = await res.json().catch(() => ({}))
        const msg = detail?.detail?.message || detail?.detail || 'confirmation required'
        if (!window.confirm(`CONTROL ACTION — write ${writeTag} = ${writeValue} on ${selected}?\n\n${msg}\n\nThis commands real equipment. Confirm only if you intend it.`)) {
          flash('Write cancelled — no value was sent to the device.')
          return
        }
        res = await fetch(
          `/api/industrial/device/${encodeURIComponent(selected)}/tag/${encodeURIComponent(writeTag)}/write`,
          { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ value: Number(writeValue) || writeValue, authorized: true }) }
        )
      }
      const data = await res.json()
      if (!res.ok) throw new Error(data?.detail || 'write failed')
      flash(`Write accepted: ${writeTag} = ${writeValue}. Verified by read-back.`)
      readDevice(selected)
    } catch (e: any) {
      setError(`Write failed: ${e?.message || e}`)
    } finally {
      setWriteBusy(false)
    }
  }

  const sel = devices.find((d) => d.id === selected)

  return (
    <div className="flex h-full w-full flex-col gap-3 overflow-y-auto bg-[#030612] p-4 font-mono text-white">
      <div className="flex items-center gap-3">
        <span className="text-sm font-bold tracking-[0.2em] text-[#00e5ff]">INDUSTRIAL AUTOMATION</span>
        <span className="rounded border border-cyan-500/40 bg-cyan-500/10 px-2 py-0.5 text-[10px] text-cyan-300">
          MODE: {controlMode}
        </span>
        {simulated && (
          <span className="rounded border border-yellow-500/50 bg-yellow-500/10 px-2 py-0.5 text-[10px] text-yellow-300">
            SIMULATED DEVICE
          </span>
        )}
      </div>

      {notice && <div className="rounded border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-300">{notice}</div>}
      {error && <div className="rounded border border-red-500/40 bg-red-500/10 px-3 py-2 text-xs text-red-300">{error}</div>}

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <div className="rounded border border-cyan-500/30 bg-[#040a18]/80 p-3">
          <div className="mb-2 text-[11px] font-bold tracking-widest text-cyan-300">DEVICES (PLC / HMI / SCADA)</div>
          <select value={selected} onChange={(e) => setSelected(e.target.value)} className="mb-2 w-full rounded border border-cyan-500/30 bg-[#030713] px-2 py-1 text-xs text-white">
            {devices.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} — {d.protocol} {d.address ? `(${d.address}:${d.port})` : '(unconfigured)'}
              </option>
            ))}
          </select>
          <button type="button" onClick={() => readDevice(selected)} className="rounded border border-cyan-500/50 bg-cyan-500/15 px-3 py-1 text-xs font-bold text-cyan-200 hover:bg-cyan-500/25">
            READ ALL TAGS
          </button>
          {sel && (
            <div className="mt-2 text-[10px] leading-relaxed text-cyan-100/70">
              <div>PROTOCOL: {sel.protocol} · KIND: {sel.kind} · CELL: {sel.cell || '—'}</div>
              <div>MACHINE STATE: <span className="font-bold text-white">{machineState}</span></div>
              <div>TAGS: {sel.tags.map((t) => t.tag).join(', ')}</div>
            </div>
          )}
        </div>

        <div className="rounded border border-cyan-500/30 bg-[#040a18]/80 p-3">
          <div className="mb-2 text-[11px] font-bold tracking-widest text-cyan-300">PROTOCOLS</div>
          <div className="space-y-1 text-[11px] text-cyan-100/80">
            {Object.entries(protocols).filter(([k]) => k !== 'control_mode').map(([k, v]: any) => (
              <div key={k} className="flex items-center gap-2">
                <span className={`h-2 w-2 rounded-full ${v?.available ? 'bg-emerald-400' : 'bg-red-400'}`} />
                <span className="font-bold text-white">{k}</span>
                <span className="text-cyan-100/60">{v?.available ? `ready (${v.driver})` : `unavailable — ${v?.reason || ''}`}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="rounded border border-cyan-500/30 bg-[#040a18]/80 p-3">
        <div className="mb-2 text-[11px] font-bold tracking-widest text-cyan-300">
          LIVE TAG READINGS {simulated ? '(SIMULATED — from test simulator, not hardware)' : '(REAL DEVICE READ)'}
          {partial && <span className="ml-2 text-yellow-300">PARTIAL — some tags failed</span>}
        </div>
        {readings.length === 0 && <div className="text-[11px] text-cyan-100/50">No readings yet. Select a configured device and read its tags.</div>}
        <div className="grid grid-cols-1 gap-1 sm:grid-cols-2 lg:grid-cols-3">
          {readings.map((r) => (
            <div key={r.tag} className="rounded border border-cyan-500/20 bg-[#030713] px-2 py-1 text-[11px]">
              <span className="font-bold text-white">{r.tag}</span>
              <span className="ml-2 text-[#00e5ff]">{String(r.value)} {r.unit}</span>
              <span className="ml-2 text-[10px] text-cyan-100/50">{r.quality}</span>
            </div>
          ))}
        </div>
        {readErrors.length > 0 && (
          <div className="mt-2 space-y-1 text-[11px] text-yellow-300">
            {readErrors.map((e) => (
              <div key={e.tag}>⚠ {e.tag}: {(e.error || '').slice(0, 160)}</div>
            ))}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <div className="rounded border border-red-500/30 bg-[#040a18]/80 p-3">
          <div className="mb-2 text-[11px] font-bold tracking-widest text-red-300">CONTROL WRITE (REQUIRES CONFIRMATION)</div>
          <div className="flex flex-wrap items-center gap-2">
            <select value={writeTag} onChange={(e) => setWriteTag(e.target.value)} className="rounded border border-red-500/30 bg-[#030713] px-2 py-1 text-xs text-white">
              <option value="">— tag —</option>
              {(sel?.tags || []).map((t) => (
                <option key={t.tag} value={t.tag}>{t.tag}</option>
              ))}
            </select>
            <input value={writeValue} onChange={(e) => setWriteValue(e.target.value)} placeholder="value" className="w-28 rounded border border-red-500/30 bg-[#030713] px-2 py-1 text-xs text-white" />
            <button type="button" disabled={writeBusy} onClick={handleWrite} className="rounded border border-red-500/50 bg-red-500/15 px-3 py-1 text-xs font-bold text-red-200 hover:bg-red-500/25 disabled:opacity-50">
              {writeBusy ? 'SENDING…' : 'WRITE TAG'}
            </button>
          </div>
          <div className="mt-1 text-[10px] text-red-200/60">Blocked until you confirm. Confirmed writes are verified by read-back and audited.</div>
        </div>

        <div className="rounded border border-cyan-500/30 bg-[#040a18]/80 p-3">
          <div className="mb-2 text-[11px] font-bold tracking-widest text-cyan-300">ACTIVE ALARMS ({alarms.filter((a) => a.active).length})</div>
          <div className="max-h-32 space-y-1 overflow-y-auto text-[11px]">
            {alarms.filter((a) => a.active).map((a) => (
              <div key={a.id} className="rounded border border-yellow-500/30 bg-yellow-500/5 px-2 py-1 text-yellow-200">
                [{a.severity}] {a.code}: {a.message}
              </div>
            ))}
            {alarms.filter((a) => a.active).length === 0 && <div className="text-cyan-100/50">No active alarms.</div>}
          </div>
        </div>
      </div>
    </div>
  )
}
