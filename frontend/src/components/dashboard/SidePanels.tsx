import { useEffect, useState } from 'react'
import { useJarvisStore } from '../../store/useJarvisStore'

const panel = 'mx-auto flex h-full w-full max-w-5xl flex-col overflow-hidden rounded-lg border border-cyan-500/30 bg-[#040a18]/95'
const panelHeader = 'flex items-center justify-between border-b border-cyan-500/25 px-4 py-2.5 font-mono text-[12px] font-bold tracking-[0.25em] text-[#00e5ff]'
const input =
  'rounded border border-cyan-500/40 bg-[#020610] px-3 py-1.5 font-mono text-[12px] text-cyan-100 placeholder-white/30 focus:border-[#00e5ff] focus:outline-none'
const btn =
  'cursor-pointer rounded border border-cyan-500/50 bg-[#071530] px-3 py-1.5 font-mono text-[11px] font-bold text-cyan-300 transition-all hover:border-[#00e5ff] hover:bg-[#00e5ff]/15 hover:text-white active:scale-95 disabled:cursor-not-allowed disabled:opacity-40'
const btnPrimary =
  'cursor-pointer rounded border border-[#00e5ff] bg-[#00e5ff] px-3 py-1.5 font-mono text-[11px] font-extrabold text-black transition-all hover:bg-cyan-300 active:scale-95 disabled:cursor-not-allowed disabled:opacity-40'

function PanelEmpty({ text }: { text: string }) {
  return <div className="px-4 py-6 font-mono text-[11px] text-cyan-300/50">{text}</div>
}

// ---------------------------------------------------------------- Robotics ---

export function RoboticsPanel() {
  const [domains, setDomains] = useState<any[] | null>(null)
  const [status, setStatus] = useState<'loading' | 'ok' | 'unavailable'>('loading')
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState<any>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    fetch('/api/robotics/domains')
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((d) => {
        setDomains(d.domains || [])
        setStatus('ok')
      })
      .catch(() => setStatus('unavailable'))
  }, [])

  const ask = async () => {
    if (!question.trim()) return
    setBusy(true)
    setAnswer(null)
    try {
      const res = await fetch('/api/robotics/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: question.trim(), limit: 6 }),
      })
      const data = await res.json()
      if (res.ok) setAnswer(data)
      else setAnswer({ error: data.detail || 'Query failed' })
    } catch {
      setAnswer({ error: 'Backend unreachable' })
    }
    setBusy(false)
  }

  return (
    <div className={panel}>
      <div className={panelHeader}>
        <span>ROBOTICS KNOWLEDGE CONSOLE</span>
        <span className="text-[10px] text-cyan-300/60">{status === 'ok' ? `${domains?.length ?? 0} DOMAINS` : status === 'loading' ? 'LINKING…' : 'KB OFFLINE'}</span>
      </div>
      <div className="border-b border-cyan-500/20 p-3">
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault()
            ask()
          }}
        >
          <input
            className={`${input} flex-1`}
            placeholder="Ask about actuators, control loops, ROS, sensors…"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
          />
          <button type="submit" className={btnPrimary} disabled={busy || status !== 'ok'}>
            {busy ? 'QUERYING…' : 'QUERY'}
          </button>
        </form>
      </div>
      <div className="flex-1 space-y-4 overflow-auto p-4">
        {answer?.error && <div className="rounded border border-rose-500/40 bg-rose-950/30 p-3 font-mono text-[11px] text-rose-300">{answer.error}</div>}
        {answer && Array.isArray(answer.results) && answer.results.length === 0 && (
          <PanelEmpty text="No knowledge entries matched that query." />
        )}
        {answer && Array.isArray(answer.results) && answer.results.map((r: any, i: number) => (
          <div key={i} className="rounded border border-cyan-500/25 bg-[#071530]/60 p-3">
            <div className="mb-1 flex items-center justify-between">
              <span className="font-mono text-[11px] font-bold text-[#00e5ff]">{r.title || r.topic || `Entry ${i + 1}`}</span>
              {r.domain && <span className="font-mono text-[9px] text-cyan-400/60">{String(r.domain).toUpperCase()}</span>}
            </div>
            <div className="whitespace-pre-wrap font-mono text-[11px] leading-relaxed text-cyan-100/85">
              {typeof r === 'string' ? r : r.content || r.summary || r.answer || JSON.stringify(r, null, 2)}
            </div>
          </div>
        ))}
        {domains && domains.length > 0 && (
          <div>
            <div className="mb-2 font-mono text-[10px] tracking-[0.25em] text-cyan-400/70">KNOWLEDGE DOMAINS</div>
            <div className="grid grid-cols-2 gap-2 lg:grid-cols-3">
              {domains.map((d) => (
                <button
                  key={d.name}
                  type="button"
                  className="cursor-pointer rounded border border-cyan-500/25 bg-[#071530]/50 p-2.5 text-left transition-colors hover:border-[#00e5ff]/60"
                  onClick={() => setQuestion(`Explain ${d.name}`)}
                >
                  <div className="font-mono text-[11px] font-bold text-cyan-200">{d.name}</div>
                  <div className="mt-0.5 line-clamp-2 font-mono text-[10px] text-cyan-300/50">{d.description}</div>
                  <div className="mt-1 font-mono text-[9px] text-amber-300/70">{d.entry_count} entries</div>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ----------------------------------------------------------------- Memory ---

export function MemoryPanel() {
  const tasks = useJarvisStore((s) => s.tasks)
  const memories = useJarvisStore((s) => s.memories)
  const fetchPersistentState = useJarvisStore((s) => s.fetchPersistentState)
  const [taskTitle, setTaskTitle] = useState('')
  const [memoryText, setMemoryText] = useState('')
  const [notice, setNotice] = useState<string | null>(null)

  useEffect(() => {
    fetchPersistentState()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const flash = (m: string) => {
    setNotice(m)
    setTimeout(() => setNotice(null), 2500)
  }

  const addTask = async () => {
    if (!taskTitle.trim()) return
    const res = await fetch('/api/memory/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: taskTitle.trim(), priority: 'medium' }),
    })
    if (res.ok) {
      setTaskTitle('')
      fetchPersistentState()
      flash('Task saved to memory store')
    } else flash('Backend rejected the task')
  }

  const addMemory = async () => {
    if (!memoryText.trim()) return
    const res = await fetch('/api/memory/memories', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ category: 'note', title: memoryText.trim().slice(0, 60), content: memoryText.trim(), importance: 5 }),
    })
    if (res.ok) {
      setMemoryText('')
      fetchPersistentState()
      flash('Memory stored')
    } else flash('Backend rejected the memory')
  }

  const removeTask = async (id: any) => {
    await fetch(`/api/memory/tasks/${id}`, { method: 'DELETE' })
    fetchPersistentState()
  }

  const removeMemory = async (id: any) => {
    await fetch(`/api/memory/memories/${id}`, { method: 'DELETE' })
    fetchPersistentState()
  }

  return (
    <div className={panel}>
      <div className={panelHeader}>
        <span>ADAPTIVE MEMORY</span>
        {notice && <span className="text-[10px] text-amber-300">{notice}</span>}
      </div>
      <div className="grid flex-1 grid-cols-1 gap-4 overflow-auto p-4 md:grid-cols-2">
        <div className="flex flex-col">
          <div className="mb-2 font-mono text-[10px] tracking-[0.25em] text-cyan-400/70">PERSISTENT TASKS ({(tasks || []).length})</div>
          <form
            className="mb-2 flex gap-2"
            onSubmit={(e) => {
              e.preventDefault()
              addTask()
            }}
          >
            <input className={`${input} flex-1`} placeholder="New task…" value={taskTitle} onChange={(e) => setTaskTitle(e.target.value)} />
            <button type="submit" className={btn}>ADD</button>
          </form>
          <div className="flex-1 space-y-1.5 overflow-auto pr-1">
            {(tasks || []).length === 0 && <PanelEmpty text="No tasks in the store." />}
            {(tasks || []).map((t: any) => (
              <div key={t.id} className="flex items-center justify-between rounded border border-cyan-500/20 bg-[#071530]/60 px-2.5 py-1.5">
                <div className="min-w-0">
                  <div className="truncate font-mono text-[11px] text-cyan-100">{t.title || t.name || String(t)}</div>
                  <div className="font-mono text-[9px] text-cyan-400/50">{String(t.status || 'pending').toUpperCase()} · {String(t.priority || 'medium').toUpperCase()}</div>
                </div>
                <button type="button" className="ml-2 cursor-pointer font-mono text-[10px] text-rose-400/70 hover:text-rose-300" onClick={() => removeTask(t.id)}>
                  ✕
                </button>
              </div>
            ))}
          </div>
        </div>

        <div className="flex flex-col">
          <div className="mb-2 font-mono text-[10px] tracking-[0.25em] text-cyan-400/70">STORED MEMORIES ({(memories || []).length})</div>
          <form
            className="mb-2 flex gap-2"
            onSubmit={(e) => {
              e.preventDefault()
              addMemory()
            }}
          >
            <input className={`${input} flex-1`} placeholder="Remember that…" value={memoryText} onChange={(e) => setMemoryText(e.target.value)} />
            <button type="submit" className={btn}>STORE</button>
          </form>
          <div className="flex-1 space-y-1.5 overflow-auto pr-1">
            {(memories || []).length === 0 && <PanelEmpty text="No memories stored yet." />}
            {(memories || []).map((m: any) => (
              <div key={m.id} className="flex items-start justify-between rounded border border-cyan-500/20 bg-[#071530]/60 px-2.5 py-1.5">
                <div className="min-w-0">
                  <div className="truncate font-mono text-[11px] text-cyan-100">{m.title || String(m.content || m).slice(0, 60)}</div>
                  <div className="font-mono text-[9px] text-cyan-400/50">{String(m.category || 'note').toUpperCase()}</div>
                </div>
                <button type="button" className="ml-2 cursor-pointer font-mono text-[10px] text-rose-400/70 hover:text-rose-300" onClick={() => removeMemory(m.id)}>
                  ✕
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------- Project ---

export function ProjectPanel() {
  const executeCommand = useJarvisStore((s) => s.executeCommand)
  const [items, setItems] = useState<any[]>([])
  const [path, setPath] = useState<string>('')
  const [status, setStatus] = useState<'loading' | 'ok' | 'unavailable'>('loading')

  const list = (dir?: string) => {
    setStatus('loading')
    fetch('/api/system/files', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'list', ...(dir ? { path: dir } : {}) }),
    })
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((d) => {
        setItems(Array.isArray(d.items) ? d.items : [])
        setStatus(Array.isArray(d.items) ? 'ok' : 'unavailable')
        setPath(dir || '')
      })
      .catch(() => setStatus('unavailable'))
  }

  useEffect(() => {
    list()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className={panel}>
      <div className={panelHeader}>
        <span>PROJECT WORKSPACE</span>
        <button type="button" className={btn} onClick={() => list(path || undefined)}>
          RELOAD
        </button>
      </div>
      <div className="border-b border-cyan-500/20 px-4 py-2 font-mono text-[10px] text-cyan-300/60">
        {path ? `DIR: ${path}` : 'WORKSPACE SANDBOX ROOT'} · {status === 'ok' ? `${items.length} ENTRIES` : status === 'loading' ? 'READING…' : 'LISTING UNAVAILABLE'}
      </div>
      <div className="flex-1 overflow-auto p-4">
        {status !== 'ok' && <PanelEmpty text={status === 'loading' ? 'Reading workspace…' : 'Workspace listing unavailable — is the backend online?'} />}
        <div className="grid grid-cols-1 gap-1.5 md:grid-cols-2">
          {items.map((f: any) => (
            <button
              key={f.name}
              type="button"
              className="flex cursor-pointer items-center justify-between rounded border border-cyan-500/20 bg-[#071530]/60 px-3 py-2 text-left transition-colors hover:border-[#00e5ff]/60"
              onClick={() => {
                if (f.is_dir) list(path ? `${path}/${f.name}` : f.name)
                else executeCommand(`read file ${path ? `${path}/${f.name}` : f.name}`)
              }}
            >
              <span className="truncate font-mono text-[11px] text-cyan-100">
                {f.is_dir ? '▸ ' : ''}{f.name}
              </span>
              <span className="ml-2 shrink-0 font-mono text-[9px] text-cyan-400/50">
                {f.is_dir ? 'DIR' : f.size_kb ? `${f.size_kb} KB` : 'FILE'}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

// --------------------------------------------------------------- Settings ---

export function SettingsPanel() {
  const autostartEnabled = useJarvisStore((s) => s.autostartEnabled)
  const toggleAutostart = useJarvisStore((s) => s.toggleAutostart)
  const speechLanguage = useJarvisStore((s) => s.speechLanguage)
  const setSpeechLanguage = useJarvisStore((s) => s.setSpeechLanguage)
  const setSystemNotice = useJarvisStore((s) => s.setSystemNotice)
  const backendStatus = useJarvisStore((s) => s.backendStatus)

  const langs: Array<[string, string]> = [
    ['auto', 'Auto detect (EN / मराठी / हिंदी)'],
    ['en-IN', 'English / Hinglish (India)'],
    ['mr-IN', 'Marathi (मराठी)'],
    ['hi-IN', 'Hindi (हिंदी)'],
    ['en-US', 'English (US)'],
  ]

  const toggleRow = (label: string, hint: string, on: boolean, onClick: () => void) => (
    <div className="flex items-center justify-between rounded border border-cyan-500/20 bg-[#071530]/60 px-4 py-3">
      <div>
        <div className="font-mono text-[12px] text-cyan-100">{label}</div>
        <div className="font-mono text-[10px] text-cyan-300/50">{hint}</div>
      </div>
      <button
        type="button"
        onClick={onClick}
        className={`relative h-6 w-11 cursor-pointer rounded-full border transition-colors ${
          on ? 'border-emerald-400 bg-emerald-500/30' : 'border-cyan-500/40 bg-[#020610]'
        }`}
      >
        <span
          className={`absolute top-0.5 h-4 w-4 rounded-full transition-all ${on ? 'left-6 bg-emerald-300' : 'left-1 bg-cyan-500/50'}`}
        />
      </button>
    </div>
  )

  return (
    <div className={panel}>
      <div className={panelHeader}>
        <span>SETTINGS</span>
        <span className={`text-[10px] ${backendStatus === 'connected' ? 'text-emerald-400' : 'text-rose-400'}`}>
          BACKEND {backendStatus.toUpperCase()}
        </span>
      </div>
      <div className="flex-1 space-y-3 overflow-auto p-4">
        {toggleRow(
          'Windows Auto-Start',
          'Launch JARVIS on PC boot via safe startup entry',
          autostartEnabled,
          () => toggleAutostart()
        )}
        <div className="rounded border border-cyan-500/20 bg-[#071530]/60 px-4 py-3">
          <div className="mb-2 font-mono text-[12px] text-cyan-100">Speech Input Language</div>
          <div className="flex flex-wrap gap-2">
            {langs.map(([code, label]) => (
              <button
                key={code}
                type="button"
                onClick={() => {
                  setSpeechLanguage(code as any)
                  setSystemNotice(`Speech input: ${label}`)
                  setTimeout(() => useJarvisStore.getState().setSystemNotice(null), 2500)
                }}
                className={`cursor-pointer rounded border px-3 py-1.5 font-mono text-[11px] transition-all active:scale-95 ${
                  speechLanguage === code
                    ? 'border-[#00e5ff] bg-[#00e5ff] text-black font-bold'
                    : 'border-cyan-500/40 bg-[#020610] text-cyan-300 hover:border-[#00e5ff]/70'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
        <div className="rounded border border-cyan-500/20 bg-[#071530]/60 px-4 py-3 font-mono text-[11px] leading-relaxed text-cyan-300/60">
          More controls live where they act: biometric enrollment in the 🧬 BIOMETRICS console (top bar),
          CAD/document options in the menu bar, and keyboard shortcuts Orbit = drag · Pan = right-drag · Zoom = scroll.
        </div>
      </div>
    </div>
  )
}
