import { useState, useEffect, useRef, useCallback } from 'react'
import { useJarvisStore, playHudChirp, speakJarvis } from '../../store/useJarvisStore'
import { useAgentWorkspaceStore } from '../../store/useAgentWorkspaceStore'
import { socketService, type SocketConnectionState } from '../../services/socketService'
import ArcReactor3D, { type ReactorState } from './ArcReactor3D'

interface CodingMessage {
  id: string | number
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp?: string
  provider?: string
  engine?: string
}

interface TreeNode {
  name: string
  type: 'file' | 'directory'
  path: string
  children?: TreeNode[]
}

interface AgentEngineStatus {
  jarvis: { available: boolean }
  opencode: { available: boolean }
}

type WorkspaceTab = 'files' | 'diffs' | 'terminal' | 'errors' | 'activity'

const EXAMPLE_TASKS = [
  'Build a login page with email and password',
  'Fix the TypeScript errors in the frontend',
  'Create a REST API endpoint for user registration',
  'Add unit tests for the coding engine',
  'Refactor the WebSocket handler for streaming',
]

export default function AutonomousCodingWorkspace() {
  const isCodingMode = useJarvisStore((s) => s.isCodingMode)
  const toggleCodingMode = useJarvisStore((s) => s.toggleCodingMode)

  const {
    agentStatus, streamingText, toolCalls, terminalEntries, diffs, errors,
    changedFiles, activityLog, reset: resetAgent, setAgentStatus,
    appendStreamingText, clearStreamingText, addToolCall, completeToolCall,
    addTerminalEntry, addDiff, addError, addChangedFile, addActivity,
  } = useAgentWorkspaceStore()

  const [messages, setMessages] = useState<CodingMessage[]>([])
  const [inputText, setInputText] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)
  const [sessionId] = useState('default_coding')
  const [connectionState, setConnectionState] = useState<SocketConnectionState>('disconnected')
  const [activeTab, setActiveTab] = useState<WorkspaceTab>('activity')
  const [treeData, setTreeData] = useState<TreeNode | null>(null)
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const [fileContent, setFileContent] = useState('')
  const [engineStatus, setEngineStatus] = useState<AgentEngineStatus | null>(null)
  const [expandedFolders, setExpandedFolders] = useState<Record<string, boolean>>({ '.': true })

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const terminalEndRef = useRef<HTMLDivElement>(null)
  const pendingToolIds = useRef<Map<string, string>>(new Map())

  const getReactorState = (): ReactorState => {
    if (isProcessing) return agentStatus.phase === 'retrying' ? 'thinking' : 'thinking'
    if (agentStatus.phase === 'complete') return 'speaking'
    return 'idle'
  }

  const loadWorkspaceTree = useCallback(async () => {
    try {
      const res = await fetch('/api/coding/workspace/tree?max_depth=3')
      if (res.ok) {
        const data = await res.json()
        const items = data.result?.items || data.items || data.tree
        if (items) {
          setTreeData({ name: 'Workspace', type: 'directory', path: '.', children: items })
        }
      }
    } catch { /* ignored */ }
  }, [])

  const loadEngineStatus = useCallback(async () => {
    try {
      const res = await fetch('/api/coding/agent/status')
      if (res.ok) {
        const data = await res.json()
        setEngineStatus(data.engines)
      }
    } catch { /* ignored */ }
  }, [])

  const openFile = useCallback(async (path: string) => {
    setSelectedFile(path)
    try {
      const res = await fetch(`/api/coding/workspace/file?path=${encodeURIComponent(path)}`)
      if (res.ok) {
        const data = await res.json()
        const content = data.result?.raw || data.raw || data.content || ''
        setFileContent(content)
      }
    } catch { /* ignored */ }
  }, [])

  const handleAgentEvent = useCallback((event: { type: string; data: Record<string, unknown> }) => {
    const { type, data } = event

    switch (type) {
      case 'agent_start':
        setAgentStatus({
          engine: (data.engine as 'jarvis' | 'opencode') || 'jarvis',
          phase: 'thinking',
          iteration: 0,
        })
        addActivity('agent', `Agent started (${data.engine})`)
        break

      case 'iteration_start':
        setAgentStatus({
          phase: 'executing',
          iteration: (data.iteration as number) || 0,
          maxIterations: (data.max_iterations as number) || 15,
        })
        break

      case 'token_delta':
        appendStreamingText((data.delta as string) || '')
        break

      case 'tool_start': {
        const toolName = (data.tool as string) || 'unknown'
        const toolId = addToolCall(toolName, (data.args as Record<string, unknown>) || {})
        pendingToolIds.current.set(toolName + Date.now(), toolId)
        setActiveTab('activity')
        break
      }

      case 'tool_result': {
        const tool = (data.tool as string) || ''
        const result = data.result as Record<string, unknown>
        const entries = [...pendingToolIds.current.entries()]
        const match = entries.find(([k]) => k.startsWith(tool))
        if (match) {
          completeToolCall(match[1], result, !!result?.success)
          pendingToolIds.current.delete(match[0])
        }
        break
      }

      case 'terminal_output':
        addTerminalEntry({
          cmd: (data.cmd as string) || '',
          stdout: (data.stdout as string) || '',
          stderr: (data.stderr as string) || '',
          exitCode: (data.exit_code as number) ?? -1,
        })
        setActiveTab('terminal')
        break

      case 'file_changed':
        addDiff((data.path as string) || '', (data.diff as string) || '')
        addChangedFile((data.path as string) || '')
        loadWorkspaceTree()
        setActiveTab('diffs')
        break

      case 'error':
        addError(
          (data.message as string) || 'Unknown error',
          data.tool as string | undefined,
          (data.severity as 'warning' | 'error' | 'critical') || 'error',
        )
        setActiveTab('errors')
        break

      case 'retry':
        setAgentStatus({ phase: 'retrying', retries: (data.attempt as number) || 0 })
        addActivity('retry', `Retrying (attempt ${data.attempt})`)
        break

      case 'agent_complete':
        setAgentStatus({ phase: 'complete' })
        addActivity('complete', 'Agent task complete')
        break

      case 'status':
        addActivity('status', (data.message as string) || 'Processing...')
        break
    }
  }, [
    setAgentStatus, appendStreamingText, addToolCall, completeToolCall,
    addTerminalEntry, addDiff, addError, addChangedFile, addActivity, loadWorkspaceTree,
  ])

  useEffect(() => {
    if (!isCodingMode) {
      socketService.close()
      return
    }

    socketService.onStateChange = (state) => setConnectionState(state)
    socketService.connect(sessionId)

    const handleResult = (data: Record<string, unknown>) => {
      setIsProcessing(false)
      clearStreamingText()

      const status = (data.status as string) || 'ok'
      const errors = (data.errors as string[]) || []
      const phase = status === 'ok' ? 'complete' : 'error'
      setAgentStatus({ phase })

      let reply = (data.reply as string) || 'Task completed, sir.'
      if (status === 'error') {
        reply = `The coding task did NOT complete successfully: ${errors[0] || reply}`
        addActivity('error', `Task failed: ${errors[0] || 'see errors tab'}`)
        addError(errors[0] || 'Coding agent reported failure with no error detail')
      } else if (status === 'partial') {
        reply = `${reply}\n\n⚠ Partial success — unresolved issues: ${errors.join('; ')}`
        addActivity('status', `Partial success: ${errors[0] || ''}`)
      }

      const assistantMsg: CodingMessage = {
        id: Date.now(),
        role: 'assistant',
        content: reply,
        provider: (data.provider as string) || '',
        engine: (data.engine as string) || 'jarvis',
        timestamp: new Date().toLocaleTimeString(),
      }
      setMessages((prev) => [...prev, assistantMsg])

      const diffsList = (data.diffs as Array<{ path: string; diff: string }>) || []
      diffsList.forEach((d) => addDiff(d.path, d.diff))

      if (diffsList.length > 0 || (data.verified_writes as string[])?.length) loadWorkspaceTree()
      if (reply) speakJarvis(reply)
      playHudChirp()
    }

    const handleCancelled = () => {
      setIsProcessing(false)
      setAgentStatus({ phase: 'idle' })
      addActivity('cancel', 'Operation cancelled')
    }

    const handleError = (msg: string) => {
      setIsProcessing(false)
      setAgentStatus({ phase: 'error' })
      addError(typeof msg === 'string' ? msg : 'WebSocket error')
    }

    socketService.on('result', handleResult)
    socketService.on('cancelled', handleCancelled)
    socketService.on('error', handleError)
    socketService.on('*', handleAgentEvent)

    return () => {
      socketService.off('result', handleResult)
      socketService.off('cancelled', handleCancelled)
      socketService.off('error', handleError)
      socketService.off('*', handleAgentEvent)
      socketService.onStateChange = null
      socketService.close()
    }
  }, [isCodingMode, sessionId, handleAgentEvent, clearStreamingText, setAgentStatus, addDiff, addError, addActivity, loadWorkspaceTree])

  useEffect(() => {
    if (isCodingMode) {
      loadWorkspaceTree()
      loadEngineStatus()
    }
  }, [isCodingMode, loadWorkspaceTree, loadEngineStatus])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingText])

  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [terminalEntries])

  const sendTask = () => {
    const text = inputText.trim()
    if (!text || isProcessing) return

    playHudChirp()
    setInputText('')
    setIsProcessing(true)
    resetAgent()
    setAgentStatus({ phase: 'thinking', engine: 'jarvis' })

    const userMsg: CodingMessage = {
      id: Date.now(),
      role: 'user',
      content: text,
      timestamp: new Date().toLocaleTimeString(),
    }
    setMessages((prev) => [...prev, userMsg])

    const sent = socketService.sendMessage(text, selectedFile || '', true)
    if (!sent) {
      setIsProcessing(false)
      addError('WebSocket not connected. Retrying connection...')
      socketService.connect(sessionId)
    }
  }

  const cancelTask = () => {
    socketService.sendCancel()
    setIsProcessing(false)
    setAgentStatus({ phase: 'idle' })
  }

  const toggleFolder = (path: string) => {
    setExpandedFolders((prev) => ({ ...prev, [path]: !prev[path] }))
  }

  if (!isCodingMode) return null

  return (
    <div className="fixed inset-0 z-[100] flex flex-col bg-[#030612] text-cyan-100 overflow-hidden">
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-2 border-b border-cyan-500/20 bg-[#040916]/90 backdrop-blur-md shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8">
              <ArcReactor3D state={getReactorState()} size={32} />
            </div>
            <div>
              <h1 className="text-sm font-bold tracking-widest text-cyan-300">
                J.A.R.V.I.S. AUTONOMOUS CODING AGENT
              </h1>
              <p className="text-[10px] text-cyan-500/70 font-mono">
                {agentStatus.engine !== 'idle' ? `Engine: ${agentStatus.engine.toUpperCase()}` : 'Ready'}
                {agentStatus.phase !== 'idle' && ` · ${agentStatus.phase.toUpperCase()}`}
                {agentStatus.iteration > 0 && ` · Step ${agentStatus.iteration}/${agentStatus.maxIterations}`}
              </p>
            </div>
          </div>

          <div className="hidden md:flex items-center gap-2 ml-4">
            {engineStatus && (
              <>
                <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono border ${
                  engineStatus.jarvis.available
                    ? 'border-green-500/40 text-green-400 bg-green-500/10'
                    : 'border-red-500/40 text-red-400'
                }`}>
                  JARVIS {engineStatus.jarvis.available ? '●' : '○'}
                </span>
                <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono border ${
                  engineStatus.opencode.available
                    ? 'border-orange-500/40 text-orange-400 bg-orange-500/10'
                    : 'border-gray-600/40 text-gray-500'
                }`}>
                  OPENCODE {engineStatus.opencode.available ? '●' : '○'}
                </span>
              </>
            )}
            <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono border ${
              connectionState === 'connected'
                ? 'border-cyan-500/40 text-cyan-400'
                : 'border-yellow-500/40 text-yellow-400'
            }`}>
              WS {connectionState.toUpperCase()}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {isProcessing && (
            <button
              onClick={cancelTask}
              className="px-3 py-1 text-xs rounded border border-red-500/40 text-red-400 hover:bg-red-500/10 transition-colors"
            >
              Cancel
            </button>
          )}
          <button
            onClick={() => toggleCodingMode(false)}
            className="px-3 py-1 text-xs rounded border border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/10 transition-colors"
          >
            Exit Workspace
          </button>
        </div>
      </header>

      {/* Main dual-panel layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: Conversation Panel (60%) */}
        <div className="flex flex-col w-full lg:w-[58%] border-r border-cyan-500/15">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.length === 0 && !isProcessing && (
              <div className="flex flex-col items-center justify-center h-full text-center px-8">
                <div className="w-16 h-16 mb-4 opacity-60">
                  <ArcReactor3D state="idle" size={64} />
                </div>
                <h2 className="text-lg font-semibold text-cyan-300 mb-2">
                  Autonomous Coding Agent
                </h2>
                <p className="text-sm text-cyan-500/70 mb-6 max-w-md">
                  Give me a task in natural language. I'll analyze, write code, run tests,
                  and fix errors automatically until it works.
                </p>
                <div className="flex flex-wrap gap-2 justify-center max-w-lg">
                  {EXAMPLE_TASKS.map((task) => (
                    <button
                      key={task}
                      onClick={() => { setInputText(task) }}
                      className="px-3 py-1.5 text-xs rounded-lg border border-cyan-500/20 text-cyan-400/80
                        hover:border-cyan-400/50 hover:bg-cyan-500/10 transition-all"
                    >
                      {task}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg) => (
              <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] rounded-xl px-4 py-2.5 ${
                  msg.role === 'user'
                    ? 'bg-cyan-500/15 border border-cyan-500/25 text-cyan-100'
                    : 'bg-[#0a1628]/80 border border-cyan-500/10 text-gray-200'
                }`}>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-[10px] font-mono text-cyan-500/60">
                      {msg.role === 'user' ? 'YOU' : 'JARVIS'}
                      {msg.engine && ` · ${msg.engine}`}
                    </span>
                    <span className="text-[10px] text-gray-600">{msg.timestamp}</span>
                  </div>
                  <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                </div>
              </div>
            ))}

            {/* Live streaming response */}
            {isProcessing && streamingText && (
              <div className="flex justify-start">
                <div className="max-w-[85%] rounded-xl px-4 py-2.5 bg-[#0a1628]/80 border border-cyan-500/10">
                  <span className="text-[10px] font-mono text-cyan-500/60">JARVIS · streaming</span>
                  <p className="text-sm whitespace-pre-wrap mt-1">{streamingText}</p>
                  <span className="inline-block w-2 h-4 bg-cyan-400 animate-pulse ml-0.5" />
                </div>
              </div>
            )}

            {/* Processing indicator */}
            {isProcessing && !streamingText && (
              <div className="flex justify-start">
                <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-[#0a1628]/60 border border-cyan-500/10">
                  <div className="w-5 h-5">
                    <ArcReactor3D state="thinking" size={20} />
                  </div>
                  <div>
                    <p className="text-xs text-cyan-400 font-mono">
                      {agentStatus.phase === 'retrying'
                        ? `Fixing errors... (retry ${agentStatus.retries})`
                        : agentStatus.phase === 'executing'
                          ? `Executing tools... (step ${agentStatus.iteration})`
                          : 'Analyzing task...'}
                    </p>
                    {toolCalls.length > 0 && (
                      <p className="text-[10px] text-cyan-500/50 mt-0.5">
                        Last: {toolCalls[toolCalls.length - 1]?.tool}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input area */}
          <div className="shrink-0 p-3 border-t border-cyan-500/15 bg-[#040916]/60">
            <div className="flex gap-2">
              <textarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    sendTask()
                  }
                }}
                placeholder="Describe a coding task... (e.g. 'build a login page' or 'fix this error')"
                rows={2}
                disabled={isProcessing}
                className="flex-1 px-3 py-2 rounded-lg bg-[#0a1628]/80 border border-cyan-500/20
                  text-sm text-cyan-100 placeholder:text-cyan-700 resize-none
                  focus:outline-none focus:border-cyan-400/50 disabled:opacity-50"
              />
              <button
                onClick={sendTask}
                disabled={isProcessing || !inputText.trim()}
                className="px-5 py-2 rounded-lg bg-cyan-500/20 border border-cyan-400/40
                  text-cyan-300 text-sm font-medium hover:bg-cyan-500/30
                  disabled:opacity-40 disabled:cursor-not-allowed transition-all"
              >
                {isProcessing ? 'Working...' : 'Execute'}
              </button>
            </div>
          </div>
        </div>

        {/* Right: Agent Workspace Panel (42%) */}
        <div className="hidden lg:flex flex-col w-[42%] bg-[#040916]/40">
          {/* Tab bar */}
          <div className="flex border-b border-cyan-500/15 shrink-0">
            {([
              ['activity', 'Activity', activityLog.length],
              ['files', 'Files', changedFiles.length],
              ['diffs', 'Diffs', diffs.length],
              ['terminal', 'Terminal', terminalEntries.length],
              ['errors', 'Errors', errors.length],
            ] as const).map(([tab, label, count]) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`flex-1 px-3 py-2 text-xs font-mono transition-colors ${
                  activeTab === tab
                    ? 'text-cyan-300 border-b-2 border-cyan-400 bg-cyan-500/5'
                    : 'text-cyan-600 hover:text-cyan-400'
                }`}
              >
                {label}
                {count > 0 && (
                  <span className="ml-1 px-1.5 py-0.5 rounded-full bg-cyan-500/20 text-[10px]">
                    {count}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div className="flex-1 overflow-y-auto">
            {activeTab === 'activity' && (
              <div className="p-2 space-y-1 font-mono text-xs">
                {activityLog.length === 0 && (
                  <p className="text-cyan-700 p-4 text-center">Agent activity will appear here...</p>
                )}
                {activityLog.map((entry) => (
                  <div key={entry.id} className="flex gap-2 px-2 py-1 rounded hover:bg-cyan-500/5">
                    <span className="text-cyan-600 shrink-0">{entry.timestamp}</span>
                    <span className={`shrink-0 ${
                      entry.type === 'error' ? 'text-red-400' :
                      entry.type === 'complete' ? 'text-green-400' :
                      entry.type === 'tool' ? 'text-yellow-400' :
                      'text-cyan-500'
                    }`}>
                      [{entry.type}]
                    </span>
                    <span className="text-gray-300 truncate">{entry.message}</span>
                  </div>
                ))}
                {toolCalls.map((tc) => (
                  <div key={tc.id} className="flex gap-2 px-2 py-1 rounded bg-[#0a1628]/40 ml-2">
                    <span className={`shrink-0 ${
                      tc.status === 'completed' ? 'text-green-400' :
                      tc.status === 'error' ? 'text-red-400' :
                      tc.status === 'running' ? 'text-yellow-400 animate-pulse' :
                      'text-gray-500'
                    }`}>
                      {tc.status === 'running' ? '▶' : tc.status === 'completed' ? '✓' : tc.status === 'error' ? '✗' : '○'}
                    </span>
                    <span className="text-cyan-400">{tc.tool}</span>
                    <span className="text-gray-600 truncate">{JSON.stringify(tc.args).slice(0, 60)}</span>
                  </div>
                ))}
              </div>
            )}

            {activeTab === 'files' && (
              <div className="p-2">
                {changedFiles.length > 0 && (
                  <div className="mb-3 px-2">
                    <p className="text-[10px] text-cyan-500/60 font-mono mb-1">CHANGED FILES</p>
                    {changedFiles.map((f) => (
                      <button
                        key={f}
                        onClick={() => openFile(f)}
                        className="block w-full text-left px-2 py-1 text-xs text-green-400 hover:bg-cyan-500/10 rounded font-mono"
                      >
                        ● {f}
                      </button>
                    ))}
                  </div>
                )}
                {treeData ? (
                  <FileTree
                    node={treeData}
                    expanded={expandedFolders}
                    onToggle={toggleFolder}
                    onSelect={openFile}
                    selectedFile={selectedFile}
                    changedFiles={changedFiles}
                  />
                ) : (
                  <p className="text-cyan-700 p-4 text-center text-xs">Loading workspace...</p>
                )}
                {selectedFile && fileContent && (
                  <div className="mt-3 border-t border-cyan-500/10 pt-2">
                    <p className="text-[10px] text-cyan-500/60 font-mono px-2 mb-1">{selectedFile}</p>
                    <pre className="text-[11px] text-gray-300 px-2 overflow-x-auto max-h-48 font-mono whitespace-pre-wrap">
                      {fileContent.slice(0, 3000)}
                      {fileContent.length > 3000 && '\n... [truncated]'}
                    </pre>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'diffs' && (
              <div className="p-2 space-y-3">
                {diffs.length === 0 && (
                  <p className="text-cyan-700 p-4 text-center text-xs">File diffs will appear here...</p>
                )}
                {diffs.map((d, i) => (
                  <div key={i} className="rounded-lg border border-cyan-500/10 overflow-hidden">
                    <div className="px-3 py-1.5 bg-cyan-500/5 border-b border-cyan-500/10 flex justify-between">
                      <span className="text-xs font-mono text-cyan-300">{d.path}</span>
                      <span className="text-[10px] text-gray-600">{d.timestamp}</span>
                    </div>
                    <pre className="p-2 text-[11px] font-mono overflow-x-auto max-h-60">
                      {d.diff.split('\n').map((line, li) => (
                        <div key={li} className={
                          line.startsWith('+') ? 'text-green-400 bg-green-500/5' :
                          line.startsWith('-') ? 'text-red-400 bg-red-500/5' :
                          line.startsWith('@@') ? 'text-cyan-400' :
                          'text-gray-400'
                        }>
                          {line}
                        </div>
                      ))}
                    </pre>
                  </div>
                ))}
              </div>
            )}

            {activeTab === 'terminal' && (
              <div className="p-2 font-mono text-xs">
                {terminalEntries.length === 0 && (
                  <p className="text-cyan-700 p-4 text-center">Command output will appear here...</p>
                )}
                {terminalEntries.map((entry) => (
                  <div key={entry.id} className="mb-3 rounded-lg border border-cyan-500/10 overflow-hidden">
                    <div className="px-3 py-1 bg-[#0a1628]/60 flex items-center gap-2">
                      <span className="text-cyan-500">$</span>
                      <span className="text-cyan-300">{entry.cmd}</span>
                      <span className={`ml-auto text-[10px] ${
                        entry.exitCode === 0 ? 'text-green-400' : 'text-red-400'
                      }`}>
                        exit {entry.exitCode}
                      </span>
                    </div>
                    {entry.stdout && (
                      <pre className="p-2 text-green-400/80 whitespace-pre-wrap">{entry.stdout}</pre>
                    )}
                    {entry.stderr && (
                      <pre className="p-2 text-red-400/80 whitespace-pre-wrap">{entry.stderr}</pre>
                    )}
                  </div>
                ))}
                <div ref={terminalEndRef} />
              </div>
            )}

            {activeTab === 'errors' && (
              <div className="p-2 space-y-2">
                {errors.length === 0 && (
                  <p className="text-cyan-700 p-4 text-center text-xs">No errors detected</p>
                )}
                {errors.map((err) => (
                  <div key={err.id} className={`rounded-lg border px-3 py-2 ${
                    err.severity === 'critical' ? 'border-red-500/30 bg-red-500/5' :
                    err.severity === 'warning' ? 'border-yellow-500/30 bg-yellow-500/5' :
                    'border-red-500/20 bg-red-500/5'
                  }`}>
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-[10px] font-mono uppercase ${
                        err.severity === 'critical' ? 'text-red-400' :
                        err.severity === 'warning' ? 'text-yellow-400' :
                        'text-red-300'
                      }`}>
                        {err.severity}
                      </span>
                      {err.tool && <span className="text-[10px] text-gray-500">via {err.tool}</span>}
                      <span className="text-[10px] text-gray-600 ml-auto">{err.timestamp}</span>
                    </div>
                    <p className="text-xs text-gray-300 font-mono">{err.message}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function FileTree({
  node, expanded, onToggle, onSelect, selectedFile, changedFiles, depth = 0,
}: {
  node: TreeNode
  expanded: Record<string, boolean>
  onToggle: (path: string) => void
  onSelect: (path: string) => void
  selectedFile: string | null
  changedFiles: string[]
  depth?: number
}) {
  const isExpanded = expanded[node.path] ?? false
  const isChanged = changedFiles.includes(node.path)
  const isSelected = selectedFile === node.path

  if (node.type === 'file') {
    return (
      <button
        onClick={() => onSelect(node.path)}
        className={`flex items-center gap-1 w-full text-left px-2 py-0.5 text-xs font-mono rounded hover:bg-cyan-500/10 ${
          isSelected ? 'bg-cyan-500/15 text-cyan-200' : 'text-gray-400'
        } ${isChanged ? 'text-green-400' : ''}`}
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
      >
        <span>{isChanged ? '●' : '📄'}</span>
        <span className="truncate">{node.name}</span>
      </button>
    )
  }

  return (
    <div>
      <button
        onClick={() => onToggle(node.path)}
        className="flex items-center gap-1 w-full text-left px-2 py-0.5 text-xs font-mono text-cyan-500/70 hover:bg-cyan-500/10 rounded"
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
      >
        <span>{isExpanded ? '📂' : '📁'}</span>
        <span>{node.name}</span>
      </button>
      {isExpanded && node.children?.map((child) => (
        <FileTree
          key={child.path}
          node={child}
          expanded={expanded}
          onToggle={onToggle}
          onSelect={onSelect}
          selectedFile={selectedFile}
          changedFiles={changedFiles}
          depth={depth + 1}
        />
      ))}
    </div>
  )
}
