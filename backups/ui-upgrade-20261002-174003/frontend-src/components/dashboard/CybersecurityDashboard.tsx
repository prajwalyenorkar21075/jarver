import { useState, useEffect, useCallback } from 'react'

interface SecurityAlert {
  id: string
  severity: string
  title: string
  description: string
  status: string
  timestamp: string
}

interface SecurityEvent {
  id: string
  event_type: string
  severity: string
  source: string
  description: string
  timestamp: string
}

interface Vulnerability {
  id: string
  title: string
  severity: string
  category: string
  target: string
  status: string
  discovered_at: string
}

interface ScanResults {
  threat_scan?: { total: number; threats: any[] }
  endpoint_check?: { status: string; issues: any[] }
  network_check?: { listening_ports: any[]; active_connections: any[] }
  vulnerability_scan?: { total_vulnerabilities: number; vulnerabilities: any[] }
  integrity_check?: { total_issues: number; modified_files: any[] }
  log_analysis?: { total_suspicious_events: number; events: any[] }
  [key: string]: any
}

interface SecurityStatus {
  status: string
  modules: Record<string, string>
  stats: Record<string, any>
}

type TabId = 'overview' | 'alerts' | 'vulnerabilities' | 'scans' | 'incidents'

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'text-red-400 bg-red-500/20 border-red-500/40',
  high: 'text-orange-400 bg-orange-500/20 border-orange-500/40',
  medium: 'text-yellow-400 bg-yellow-500/20 border-yellow-500/40',
  low: 'text-blue-400 bg-blue-500/20 border-blue-500/40',
  info: 'text-cyan-400 bg-cyan-500/20 border-cyan-500/40',
}

const STATUS_COLORS: Record<string, string> = {
  active: 'text-red-400',
  acknowledged: 'text-yellow-400',
  resolved: 'text-green-400',
  open: 'text-red-400',
  closed: 'text-green-400',
  investigating: 'text-yellow-400',
}

export function CybersecurityDashboard() {
  const [activeTab, setActiveTab] = useState<TabId>('overview')
  const [status, setStatus] = useState<SecurityStatus | null>(null)
  const [alerts, setAlerts] = useState<SecurityAlert[]>([])
  const [vulnerabilities, setVulnerabilities] = useState<Vulnerability[]>([])
  const [events, setEvents] = useState<SecurityEvent[]>([])
  const [scanResults, setScanResults] = useState<ScanResults | null>(null)
  const [isScanning, setIsScanning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastScanTime, setLastScanTime] = useState<string | null>(null)

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch('/api/cybersecurity/status')
      if (res.ok) {
        const data = await res.json()
        setStatus(data)
      }
    } catch (err) {
      console.error('Failed to fetch security status:', err)
    }
  }, [])

  const fetchAlerts = useCallback(async () => {
    try {
      const res = await fetch('/api/cybersecurity/alerts')
      if (res.ok) {
        const data = await res.json()
        setAlerts(data.alerts || [])
      }
    } catch (err) {
      console.error('Failed to fetch alerts:', err)
    }
  }, [])

  const fetchVulnerabilities = useCallback(async () => {
    try {
      const res = await fetch('/api/cybersecurity/vulnerabilities')
      if (res.ok) {
        const data = await res.json()
        setVulnerabilities(data.vulnerabilities || [])
      }
    } catch (err) {
      console.error('Failed to fetch vulnerabilities:', err)
    }
  }, [])

  const fetchEvents = useCallback(async () => {
    try {
      const res = await fetch('/api/cybersecurity/events')
      if (res.ok) {
        const data = await res.json()
        setEvents(data.events || [])
      }
    } catch (err) {
      console.error('Failed to fetch events:', err)
    }
  }, [])

  const runFullScan = async () => {
    setIsScanning(true)
    setError(null)
    try {
      const res = await fetch('/api/cybersecurity/full-scan', { method: 'POST' })
      if (!res.ok) throw new Error(`Scan failed: HTTP ${res.status}`)
      const data = await res.json()
      setScanResults(data.results || data)
      setLastScanTime(new Date().toLocaleTimeString())
      await fetchStatus()
      await fetchAlerts()
      await fetchVulnerabilities()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Scan failed')
    } finally {
      setIsScanning(false)
    }
  }

  const runTargetedScan = async (endpoint: string, body?: Record<string, any>) => {
    setError(null)
    try {
      const res = await fetch(`/api/cybersecurity/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: body ? JSON.stringify(body) : undefined,
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setScanResults((prev) => ({ ...prev, [endpoint.split('/')[0]]: data }))
      setLastScanTime(new Date().toLocaleTimeString())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Scan failed')
    }
  }

  useEffect(() => {
    fetchStatus()
    fetchAlerts()
    fetchVulnerabilities()
    fetchEvents()
  }, [fetchStatus, fetchAlerts, fetchVulnerabilities, fetchEvents])

  const activeAlerts = alerts.filter((a) => a.status === 'active')
  const criticalAlerts = activeAlerts.filter((a) => a.severity === 'critical' || a.severity === 'high')
  const openVulns = vulnerabilities.filter((v) => v.status === 'open')
  const criticalVulns = openVulns.filter((v) => v.severity === 'critical' || v.severity === 'high')

  const tabs: { id: TabId; label: string }[] = [
    { id: 'overview', label: 'OVERVIEW' },
    { id: 'alerts', label: `ALERTS (${activeAlerts.length})` },
    { id: 'vulnerabilities', label: `VULNS (${openVulns.length})` },
    { id: 'scans', label: 'SCANS' },
    { id: 'incidents', label: 'INCIDENTS' },
  ]

  return (
    <div className="flex flex-col gap-4 w-full font-mono text-white">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-cyan-500/40 bg-cyan-500/10">
            <svg className="h-5 w-5 text-cyan-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
          </div>
          <div>
            <h2 className="text-xl font-bold text-cyan-400 tracking-wider">CYBERSECURITY COMMAND CENTER</h2>
            <p className="text-[10px] text-cyan-400/60">DEFENSIVE SECURITY MONITORING &amp; ANALYSIS</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {lastScanTime && (
            <span className="text-[10px] text-cyan-400/60">LAST SCAN: {lastScanTime}</span>
          )}
          <button
            onClick={runFullScan}
            disabled={isScanning}
            className="flex items-center gap-2 rounded-lg border border-cyan-500/40 bg-cyan-500/10 px-4 py-2 text-xs text-cyan-300 hover:border-cyan-400 hover:bg-cyan-500/20 hover:text-white transition-all disabled:opacity-50 cursor-pointer"
          >
            {isScanning ? (
              <>
                <span className="h-2 w-2 rounded-full bg-cyan-400 animate-ping" />
                SCANNING...
              </>
            ) : (
              <>
                <svg className="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="11" cy="11" r="8" />
                  <path d="m21 21-4.35-4.35" />
                </svg>
                FULL SCAN
              </>
            )}
          </button>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-2 text-xs text-red-300">
          {error}
          <button onClick={() => setError(null)} className="ml-3 text-red-400 hover:text-white">Dismiss</button>
        </div>
      )}

      {/* Stats Overview */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <StatCard
          label="ACTIVE ALERTS"
          value={activeAlerts.length}
          color={criticalAlerts.length > 0 ? 'red' : 'green'}
          sub={criticalAlerts.length > 0 ? `${criticalAlerts.length} critical` : 'All clear'}
        />
        <StatCard
          label="VULNERABILITIES"
          value={openVulns.length}
          color={criticalVulns.length > 0 ? 'orange' : 'green'}
          sub={criticalVulns.length > 0 ? `${criticalVulns.length} high/critical` : 'Minimal'}
        />
        <StatCard
          label="EVENTS"
          value={events.length}
          color="cyan"
          sub="Total recorded"
        />
        <StatCard
          label="MODULES"
          value={status ? Object.keys(status.modules || {}).length : 20}
          color="cyan"
          sub="Active scanners"
        />
        <StatCard
          label="STATUS"
          value={status?.status || 'UNKNOWN'}
          color={status?.status === 'operational' ? 'green' : 'yellow'}
          sub="System health"
        />
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-cyan-500/20 pb-0">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-[11px] tracking-wider transition-all cursor-pointer border-b-2 ${
              activeTab === tab.id
                ? 'border-cyan-400 text-cyan-300 bg-cyan-500/10'
                : 'border-transparent text-cyan-400/50 hover:text-cyan-300 hover:border-cyan-500/30'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="min-h-[400px]">
        {activeTab === 'overview' && (
          <OverviewTab
            alerts={activeAlerts}
            vulnerabilities={openVulns}
            events={events}
            scanResults={scanResults}
            onRunScan={runTargetedScan}
            isScanning={isScanning}
          />
        )}
        {activeTab === 'alerts' && <AlertsTab alerts={alerts} onRefresh={fetchAlerts} />}
        {activeTab === 'vulnerabilities' && <VulnerabilitiesTab vulnerabilities={vulnerabilities} onRefresh={fetchVulnerabilities} />}
        {activeTab === 'scans' && (
          <ScansTab
            scanResults={scanResults}
            onRunScan={runTargetedScan}
            isScanning={isScanning}
          />
        )}
        {activeTab === 'incidents' && <IncidentsTab />}
      </div>
    </div>
  )
}

function StatCard({ label, value, color, sub }: { label: string; value: any; color: string; sub: string }) {
  const colorMap: Record<string, string> = {
    red: 'border-red-500/40 text-red-400',
    orange: 'border-orange-500/40 text-orange-400',
    yellow: 'border-yellow-500/40 text-yellow-400',
    green: 'border-green-500/40 text-green-400',
    cyan: 'border-cyan-500/40 text-cyan-400',
  }
  const cls = colorMap[color] || colorMap.cyan
  return (
    <div className={`rounded-lg border bg-[#040a18]/95 p-3 ${cls.split(' ')[0]} backdrop-blur-xl`}>
      <div className="text-[9px] text-cyan-400/60 tracking-wider">{label}</div>
      <div className={`text-2xl font-bold mt-1 ${cls.split(' ')[1]}`}>{value}</div>
      <div className="text-[9px] text-cyan-400/40 mt-0.5">{sub}</div>
    </div>
  )
}

function OverviewTab({
  alerts,
  vulnerabilities,
  events,
  scanResults,
  onRunScan,
  isScanning,
}: {
  alerts: SecurityAlert[]
  vulnerabilities: Vulnerability[]
  events: SecurityEvent[]
  scanResults: ScanResults | null
  onRunScan: (endpoint: string, body?: Record<string, any>) => void
  isScanning: boolean
}) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
      {/* Recent Alerts */}
      <div className="rounded-lg border border-cyan-500/20 bg-[#040a18]/95 p-4">
        <h3 className="text-xs font-bold text-cyan-400 tracking-wider mb-3">RECENT ALERTS</h3>
        {alerts.length === 0 ? (
          <div className="text-[11px] text-green-400/80 py-4 text-center">No active alerts. All systems secure.</div>
        ) : (
          <div className="flex flex-col gap-2 max-h-[200px] overflow-y-auto">
            {alerts.slice(0, 5).map((alert) => (
              <div key={alert.id} className={`rounded border p-2 ${SEVERITY_COLORS[alert.severity] || SEVERITY_COLORS.info}`}>
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold">{alert.title}</span>
                  <span className="text-[9px] uppercase">{alert.severity}</span>
                </div>
                <div className="text-[10px] opacity-70 mt-0.5">{alert.description}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Top Vulnerabilities */}
      <div className="rounded-lg border border-cyan-500/20 bg-[#040a18]/95 p-4">
        <h3 className="text-xs font-bold text-cyan-400 tracking-wider mb-3">TOP VULNERABILITIES</h3>
        {vulnerabilities.length === 0 ? (
          <div className="text-[11px] text-green-400/80 py-4 text-center">No open vulnerabilities found.</div>
        ) : (
          <div className="flex flex-col gap-2 max-h-[200px] overflow-y-auto">
            {vulnerabilities.slice(0, 5).map((vuln) => (
              <div key={vuln.id} className={`rounded border p-2 ${SEVERITY_COLORS[vuln.severity] || SEVERITY_COLORS.info}`}>
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold">{vuln.title}</span>
                  <span className="text-[9px] uppercase">{vuln.severity}</span>
                </div>
                <div className="text-[10px] opacity-70 mt-0.5">{vuln.category} - {vuln.target}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Quick Scan Actions */}
      <div className="rounded-lg border border-cyan-500/20 bg-[#040a18]/95 p-4">
        <h3 className="text-xs font-bold text-cyan-400 tracking-wider mb-3">QUICK SCAN ACTIONS</h3>
        <div className="grid grid-cols-2 gap-2">
          {[
            { label: 'Threat Detection', endpoint: 'threat/scan', icon: '🛡️' },
            { label: 'Endpoint Check', endpoint: 'endpoint/check', icon: '🖥️' },
            { label: 'Network Check', endpoint: 'network/check', icon: '🌐' },
            { label: 'Vulnerability Scan', endpoint: 'vulnerability/scan', icon: '🔍' },
            { label: 'Integrity Check', endpoint: 'integrity/verify', icon: '📁' },
            { label: 'Log Analysis', endpoint: 'logs/analyze', icon: '📋' },
            { label: 'Secret Scan', endpoint: 'secrets/scan', body: { target_path: '.' }, icon: '🔑' },
            { label: 'Privacy Scan', endpoint: 'privacy/scan', body: { target_path: '.' }, icon: '🔒' },
          ].map((scan) => (
            <button
              key={scan.endpoint}
              onClick={() => onRunScan(scan.endpoint, scan.body)}
              disabled={isScanning}
              className="flex items-center gap-2 rounded-lg border border-cyan-500/20 bg-[#071530] px-3 py-2 text-[11px] text-cyan-300 hover:border-cyan-400 hover:bg-cyan-500/10 hover:text-white transition-all disabled:opacity-50 cursor-pointer"
            >
              <span>{scan.icon}</span>
              <span>{scan.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Recent Events */}
      <div className="rounded-lg border border-cyan-500/20 bg-[#040a18]/95 p-4">
        <h3 className="text-xs font-bold text-cyan-400 tracking-wider mb-3">RECENT EVENTS</h3>
        {events.length === 0 ? (
          <div className="text-[11px] text-cyan-400/50 py-4 text-center">No security events recorded yet.</div>
        ) : (
          <div className="flex flex-col gap-1.5 max-h-[200px] overflow-y-auto">
            {events.slice(0, 8).map((event) => (
              <div key={event.id} className="flex items-center gap-2 text-[10px]">
                <span className={`inline-block h-1.5 w-1.5 rounded-full ${
                  event.severity === 'critical' ? 'bg-red-400' :
                  event.severity === 'high' ? 'bg-orange-400' :
                  event.severity === 'medium' ? 'bg-yellow-400' : 'bg-cyan-400'
                }`} />
                <span className="text-cyan-400/60 w-16 shrink-0">{event.event_type}</span>
                <span className="text-white/80 truncate">{event.description}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Scan Results Summary */}
      {scanResults && (
        <div className="lg:col-span-2 rounded-lg border border-cyan-500/20 bg-[#040a18]/95 p-4">
          <h3 className="text-xs font-bold text-cyan-400 tracking-wider mb-3">LATEST SCAN RESULTS</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {scanResults.total_findings !== undefined && (
              <div className="text-center">
                <div className="text-2xl font-bold text-cyan-400">{scanResults.total_findings}</div>
                <div className="text-[9px] text-cyan-400/60">TOTAL FINDINGS</div>
              </div>
            )}
            {scanResults.threat_scan && (
              <div className="text-center">
                <div className="text-2xl font-bold text-red-400">{scanResults.threat_scan.total || 0}</div>
                <div className="text-[9px] text-cyan-400/60">THREATS</div>
              </div>
            )}
            {scanResults.vulnerability_scan && (
              <div className="text-center">
                <div className="text-2xl font-bold text-orange-400">{scanResults.vulnerability_scan.total_vulnerabilities || 0}</div>
                <div className="text-[9px] text-cyan-400/60">VULNERABILITIES</div>
              </div>
            )}
            {scanResults.integrity_check && (
              <div className="text-center">
                <div className="text-2xl font-bold text-yellow-400">{scanResults.integrity_check.total_issues || 0}</div>
                <div className="text-[9px] text-cyan-400/60">INTEGRITY ISSUES</div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function AlertsTab({ alerts, onRefresh }: { alerts: SecurityAlert[]; onRefresh: () => void }) {
  return (
    <div className="mt-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-bold text-cyan-400 tracking-wider">ALL SECURITY ALERTS</h3>
        <button
          onClick={onRefresh}
          className="text-[10px] text-cyan-400/60 hover:text-cyan-300 cursor-pointer"
        >
          REFRESH
        </button>
      </div>
      {alerts.length === 0 ? (
        <div className="rounded-lg border border-cyan-500/20 bg-[#040a18]/95 p-8 text-center">
          <div className="text-3xl mb-2">🛡️</div>
          <div className="text-sm text-green-400">No security alerts</div>
          <div className="text-[10px] text-cyan-400/50 mt-1">All systems operating normally</div>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {alerts.map((alert) => (
            <div key={alert.id} className={`rounded-lg border p-3 ${SEVERITY_COLORS[alert.severity] || SEVERITY_COLORS.info}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-[9px] font-bold uppercase px-1.5 py-0.5 rounded border border-current">
                    {alert.severity}
                  </span>
                  <span className="text-xs font-bold">{alert.title}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-[9px] uppercase ${STATUS_COLORS[alert.status] || 'text-cyan-400'}`}>
                    {alert.status}
                  </span>
                  <span className="text-[9px] opacity-50">{alert.timestamp}</span>
                </div>
              </div>
              <div className="text-[10px] opacity-70 mt-1">{alert.description}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function VulnerabilitiesTab({ vulnerabilities, onRefresh }: { vulnerabilities: Vulnerability[]; onRefresh: () => void }) {
  return (
    <div className="mt-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-bold text-cyan-400 tracking-wider">VULNERABILITY REGISTER</h3>
        <button
          onClick={onRefresh}
          className="text-[10px] text-cyan-400/60 hover:text-cyan-300 cursor-pointer"
        >
          REFRESH
        </button>
      </div>
      {vulnerabilities.length === 0 ? (
        <div className="rounded-lg border border-cyan-500/20 bg-[#040a18]/95 p-8 text-center">
          <div className="text-3xl mb-2">✅</div>
          <div className="text-sm text-green-400">No known vulnerabilities</div>
          <div className="text-[10px] text-cyan-400/50 mt-1">Run a vulnerability scan to check your system</div>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {vulnerabilities.map((vuln) => (
            <div key={vuln.id} className={`rounded-lg border p-3 ${SEVERITY_COLORS[vuln.severity] || SEVERITY_COLORS.info}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-[9px] font-bold uppercase px-1.5 py-0.5 rounded border border-current">
                    {vuln.severity}
                  </span>
                  <span className="text-xs font-bold">{vuln.title}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[9px] opacity-60">{vuln.category}</span>
                  <span className={`text-[9px] uppercase ${STATUS_COLORS[vuln.status] || 'text-cyan-400'}`}>
                    {vuln.status}
                  </span>
                </div>
              </div>
              <div className="text-[10px] opacity-70 mt-1">Target: {vuln.target}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function ScansTab({
  scanResults,
  onRunScan,
  isScanning,
}: {
  scanResults: ScanResults | null
  onRunScan: (endpoint: string, body?: Record<string, any>) => void
  isScanning: boolean
}) {
  const scanModules = [
    { name: 'Threat Detection', endpoint: 'threat/scan', desc: 'Detect suspicious processes, files, and network behavior', icon: '🛡️' },
    { name: 'Endpoint Security', endpoint: 'endpoint/check', desc: 'Windows process, service, and security configuration audit', icon: '🖥️' },
    { name: 'Network Security', endpoint: 'network/check', desc: 'Inspect listening ports, connections, and interfaces', icon: '🌐' },
    { name: 'Vulnerability Scan', endpoint: 'vulnerability/scan', desc: 'Scan for software vulnerabilities and missing patches', icon: '🔍' },
    { name: 'File Integrity', endpoint: 'integrity/verify', desc: 'Verify file integrity against baselines', icon: '📁' },
    { name: 'Log Analysis', endpoint: 'logs/analyze', desc: 'Analyze system and security logs for suspicious activity', icon: '📋' },
    { name: 'Secret Detection', endpoint: 'secrets/scan', desc: 'Scan for exposed API keys, tokens, and credentials', icon: '🔑', body: { target_path: '.' } },
    { name: 'Database Audit', endpoint: 'database/audit', desc: 'Audit database configuration and permissions', icon: '🗄️', body: { db_path: 'jarvis.db' } },
    { name: 'Privacy Scan', endpoint: 'privacy/scan', desc: 'Detect PII exposure and data leakage', icon: '🔒', body: { target_path: '.' } },
    { name: 'Dependency Scan', endpoint: 'dependency/scan', desc: 'Check npm/pip dependencies for known vulnerabilities', icon: '📦', body: { project_path: '.' } },
  ]

  return (
    <div className="mt-4">
      <h3 className="text-xs font-bold text-cyan-400 tracking-wider mb-3">SECURITY SCAN MODULES</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {scanModules.map((mod) => (
          <div key={mod.endpoint} className="rounded-lg border border-cyan-500/20 bg-[#040a18]/95 p-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-lg">{mod.icon}</span>
                <div>
                  <div className="text-[11px] font-bold text-white">{mod.name}</div>
                  <div className="text-[9px] text-cyan-400/50">{mod.desc}</div>
                </div>
              </div>
              <button
                onClick={() => onRunScan(mod.endpoint, mod.body)}
                disabled={isScanning}
                className="rounded border border-cyan-500/30 bg-cyan-500/10 px-3 py-1 text-[10px] text-cyan-300 hover:border-cyan-400 hover:bg-cyan-500/20 hover:text-white transition-all disabled:opacity-50 cursor-pointer"
              >
                RUN
              </button>
            </div>
          </div>
        ))}
      </div>

      {scanResults && (
        <div className="mt-4 rounded-lg border border-cyan-500/20 bg-[#040a18]/95 p-4">
          <h3 className="text-xs font-bold text-cyan-400 tracking-wider mb-3">RAW SCAN DATA</h3>
          <pre className="text-[10px] text-cyan-300/80 overflow-x-auto max-h-[300px] overflow-y-auto">
            {JSON.stringify(scanResults, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}

function IncidentsTab() {
  const [incidents, setIncidents] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchIncidents = async () => {
      try {
        const res = await fetch('/api/cybersecurity/incidents')
        if (res.ok) {
          const data = await res.json()
          setIncidents(data.incidents || [])
        }
      } catch (err) {
        console.error('Failed to fetch incidents:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchIncidents()
  }, [])

  if (loading) {
    return (
      <div className="mt-4 text-center text-[11px] text-cyan-400/60 py-8">
        Loading incidents...
      </div>
    )
  }

  return (
    <div className="mt-4">
      <h3 className="text-xs font-bold text-cyan-400 tracking-wider mb-3">SECURITY INCIDENTS</h3>
      {incidents.length === 0 ? (
        <div className="rounded-lg border border-cyan-500/20 bg-[#040a18]/95 p-8 text-center">
          <div className="text-3xl mb-2">📋</div>
          <div className="text-sm text-green-400">No active incidents</div>
          <div className="text-[10px] text-cyan-400/50 mt-1">System is operating normally</div>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {incidents.map((inc: any) => (
            <div key={inc.id} className={`rounded-lg border p-3 ${SEVERITY_COLORS[inc.severity] || SEVERITY_COLORS.info}`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-[9px] font-bold uppercase px-1.5 py-0.5 rounded border border-current">
                    {inc.severity}
                  </span>
                  <span className="text-xs font-bold">{inc.title}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-[9px] uppercase ${STATUS_COLORS[inc.status] || 'text-cyan-400'}`}>
                    {inc.status}
                  </span>
                </div>
              </div>
              <div className="text-[10px] opacity-70 mt-1">{inc.incident_type} - {inc.description}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
