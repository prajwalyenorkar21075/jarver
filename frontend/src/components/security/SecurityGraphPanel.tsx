import { useState, useEffect, useCallback } from 'react'

export default function SecurityGraphPanel() {
  const [summary, setSummary] = useState<any>(null)
  const [paths, setPaths] = useState<any[]>([])
  const [nodes, setNodes] = useState<any[]>([])
  const [query, setQuery] = useState('')
  const [nodeType, setNodeType] = useState('')
  const [selected, setSelected] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const [s, p] = await Promise.all([
        fetch('/api/security/graph/summary'),
        fetch('/api/security/graph/attack-paths?limit=20'),
      ])
      if (s.ok) setSummary(await s.json())
      if (p.ok) setPaths((await p.json()).paths || [])
    } catch (e: any) {
      setError(`Asset graph unreachable: ${e?.message || e}`)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const sync = async () => {
    setError(null)
    try {
      const res = await fetch('/api/security/graph/sync', { method: 'POST' })
      if (!res.ok) throw new Error('sync failed')
      await load()
    } catch (e: any) {
      setError(`Sync: ${e?.message || e}`)
    }
  }

  const search = async () => {
    setError(null)
    try {
      const res = await fetch(`/api/security/graph/nodes?limit=100${nodeType ? `&node_type=${nodeType}` : ''}${query ? `&q=${encodeURIComponent(query)}` : ''}`)
      if (!res.ok) throw new Error('search failed')
      setNodes((await res.json()).nodes || [])
    } catch (e: any) {
      setError(`Search: ${e?.message || e}`)
    }
  }

  const inspectNode = async (id: string) => {
    try {
      const res = await fetch(`/api/security/graph/neighbors/${id}?depth=1`)
      if (res.ok) setSelected(await res.json())
    } catch {
      setSelected(null)
    }
  }

  return (
    <div className="flex h-full w-full flex-col gap-3 overflow-y-auto bg-[#030612] p-4 font-mono text-white">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-bold tracking-[0.2em] text-[#00e5ff]">SECURITY ASSET GRAPH</span>
        <button type="button" onClick={sync} className="rounded border border-cyan-500/50 bg-cyan-500/15 px-3 py-1 text-xs font-bold text-cyan-200 hover:bg-cyan-500/25">
          SYNC FROM SECURITY DB
        </button>
      </div>

      {error && <div className="rounded border border-red-500/40 bg-red-500/10 px-3 py-2 text-xs text-red-300">{error}</div>}

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
        <div className="rounded border border-cyan-500/30 bg-[#040a18]/80 p-3 text-[11px]">
          <div className="mb-2 font-bold tracking-widest text-cyan-300">GRAPH SUMMARY</div>
          <div>TOTAL NODES: <span className="font-bold text-white">{summary?.total_nodes ?? '—'}</span></div>
          <div>TOTAL EDGES: <span className="font-bold text-white">{summary?.total_edges ?? '—'}</span></div>
          <div>HIGH-RISK NODES: <span className="font-bold text-red-300">{summary?.high_risk_nodes ?? '—'}</span></div>
          <div className="mt-1 text-cyan-100/70">
            {Object.entries(summary?.nodes_by_type || {}).map(([k, v]) => (
              <div key={k}>{k}: {String(v)}</div>
            ))}
          </div>
          <div className="mt-2 font-bold text-cyan-300">TOP RISK</div>
          {(summary?.top_risk || []).slice(0, 6).map((n: any, i: number) => (
            <div key={i} className="text-orange-200">{n.node_type}: {(n.name || '').slice(0, 60)} ({n.risk_score})</div>
          ))}
        </div>

        <div className="rounded border border-cyan-500/30 bg-[#040a18]/80 p-3 text-[11px]">
          <div className="mb-2 font-bold tracking-widest text-cyan-300">ATTACK PATHS (DEVICE → VULN)</div>
          <div className="max-h-64 space-y-1 overflow-y-auto">
            {paths.map((p, i) => (
              <div key={i} className="rounded border border-red-500/20 bg-red-500/5 px-2 py-1 text-red-200">
                {p.device} → {p.service} → {(p.vulnerability || '').slice(0, 70)} [{p.severity}]
              </div>
            ))}
            {paths.length === 0 && <div className="text-cyan-100/50">No attack paths. Sync the graph after running scans.</div>}
          </div>
        </div>

        <div className="rounded border border-cyan-500/30 bg-[#040a18]/80 p-3 text-[11px]">
          <div className="mb-2 font-bold tracking-widest text-cyan-300">SEARCH NODES</div>
          <div className="mb-1 flex gap-1">
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="name contains…" className="w-32 rounded border border-cyan-500/30 bg-[#030713] px-2 py-1 text-[11px] text-white" />
            <input value={nodeType} onChange={(e) => setNodeType(e.target.value)} placeholder="type (device, vulnerability…)" className="w-40 rounded border border-cyan-500/30 bg-[#030713] px-2 py-1 text-[11px] text-white" />
            <button type="button" onClick={search} className="rounded border border-cyan-500/50 bg-cyan-500/15 px-2 py-1 font-bold text-cyan-200 hover:bg-cyan-500/25">GO</button>
          </div>
          <div className="max-h-48 space-y-1 overflow-y-auto">
            {nodes.map((n) => (
              <button type="button" key={n.id} onClick={() => inspectNode(n.id)} className="block w-full rounded border border-cyan-500/20 bg-[#030713] px-2 py-1 text-left text-cyan-100 hover:border-cyan-400">
                <span className="font-bold text-white">{n.node_type}</span> {(n.name || '').slice(0, 60)}
              </button>
            ))}
            {nodes.length === 0 && <div className="text-cyan-100/50">Search the graph, then click a node to see its relationships.</div>}
          </div>
          {selected?.root && (
            <div className="mt-2 rounded border border-cyan-500/30 bg-[#030713] p-2">
              <div className="font-bold text-white">{selected.root.node_type}: {(selected.root.name || '').slice(0, 80)}</div>
              <div className="text-cyan-100/70">neighbours: {selected.node_count - 1} · edges: {selected.edge_count}</div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
