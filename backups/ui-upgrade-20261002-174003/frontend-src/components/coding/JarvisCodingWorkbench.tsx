import { useState, useEffect, useRef, useCallback } from 'react'
import { useJarvisStore, playHudChirp, speakJarvis } from '../../store/useJarvisStore'
import { voiceController } from '../../services/voiceController'
import { socketService, type SocketConnectionState } from '../../services/socketService'
import ArcReactor3D, { type ReactorState } from './ArcReactor3D'

interface ToolCallItem {
  id?: string
  name: string
  arguments: any
}

interface DiffItem {
  path: string
  diff: string
}

interface CodingMessage {
  id: string | number
  role: 'user' | 'assistant' | 'system'
  content: string
  tool_calls?: ToolCallItem[]
  tool_results?: any[]
  diffs?: DiffItem[]
  timestamp?: string
  provider?: string
}

interface SkillItem {
  id: string
  display_name: string
  description: string
  icon: string
  enabled: boolean
  tools_count: number
  tools: Array<{ name: string; description: string }>
}

interface TreeNode {
  name: string
  type: 'file' | 'directory'
  path: string
  size?: number
  children?: TreeNode[]
}

interface ActivityItem {
  id: number
  type: 'tool' | 'info' | 'error' | 'success'
  message: string
  timestamp: string
}

interface TerminalLog {
  cmd: string
  output: string
  success: boolean
  timestamp: string
}

const FILE_ICONS: Record<string, string> = {
  ts: '🔷', tsx: '🔷', js: '🟡', jsx: '🟡',
  py: '🐍', json: '📋', md: '📝', txt: '📄',
  html: '🌐', css: '🎨', scss: '🎨',
  svg: '🖼️', png: '🖼️', jpg: '🖼️',
  gitignore: '🔒', env: '🔐', toml: '⚙️', yaml: '⚙️', yml: '⚙️',
  sh: '🖥️', bat: '🖥️', ps1: '🖥️',
}

function getFileIcon(name: string): string {
  const ext = name.split('.').pop()?.toLowerCase() || ''
  return FILE_ICONS[ext] || '📄'
}

function getLanguageFromExt(name: string): string {
  const ext = name.split('.').pop()?.toLowerCase() || ''
  const map: Record<string, string> = {
    ts: 'TypeScript', tsx: 'TypeScript', js: 'JavaScript', jsx: 'JavaScript',
    py: 'Python', json: 'JSON', md: 'Markdown', html: 'HTML', css: 'CSS',
    scss: 'SCSS', svg: 'SVG', toml: 'TOML', yaml: 'YAML', yml: 'YAML',
    sh: 'Shell', bat: 'Batch', ps1: 'PowerShell',
  }
  return map[ext] || 'Plain Text'
}

export default function JarvisCodingWorkbench() {
  const isCodingMode = useJarvisStore((s) => s.isCodingMode)
  const toggleCodingMode = useJarvisStore((s) => s.toggleCodingMode)
  const orbState = useJarvisStore((s) => s.orbState)
  const audioLevel = useJarvisStore((s) => s.audioLevel)
  const isListening = useJarvisStore((s) => s.isListening)

  const [activeTab, setActiveTab] = useState<'explorer' | 'inspector' | 'terminal' | 'skills'>('explorer')
  const [messages, setMessages] = useState<CodingMessage[]>([])
  const [inputText, setInputText] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)
  const [sessionId, setSessionId] = useState('default_coding')
  const [sessions, setSessions] = useState<any[]>([])
  const [connectionState, setConnectionState] = useState<SocketConnectionState>('disconnected')

  // Workspace explorer state
  const [treeData, setTreeData] = useState<TreeNode | null>(null)
  const [expandedFolders, setExpandedFolders] = useState<Record<string, boolean>>({ '.': true, jarvis: true })
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const [fileContent, setFileContent] = useState<string>('')
  const [fileOriginalContent, setFileOriginalContent] = useState<string>('')
  const [fileTotalLines, setFileTotalLines] = useState<number>(0)
  const [isLoadingFile, setIsLoadingFile] = useState(false)
  const [fileModified, setFileModified] = useState(false)

  // Terminal state
  const [terminalInput, setTerminalInput] = useState('')
  const [terminalLogs, setTerminalLogs] = useState<TerminalLog[]>([
    { cmd: 'jarvis-cli --version', output: 'J.A.R.V.I.S. Autonomous AI Coding Assistant v2.0 (GPT-6 Astra Ready)', success: true, timestamp: new Date().toLocaleTimeString() },
  ])

  // Skills state
  const [skillsList, setSkillsList] = useState<SkillItem[]>([])
  const [notification, setNotification] = useState<string | null>(null)

  // Activity feed
  const [activityLog, setActivityLog] = useState<ActivityItem[]>([])

  const messagesEndRef = useRef<HTMLDivElement | null>(null)
  const terminalEndRef = useRef<HTMLDivElement | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)

  const showNotice = (msg: string) => {
    setNotification(msg)
    setTimeout(() => setNotification(null), 3500)
  }

  const addActivity = useCallback((type: ActivityItem['type'], message: string) => {
    setActivityLog((prev) => [
      ...prev.slice(-49),
      { id: Date.now(), type, message, timestamp: new Date().toLocaleTimeString() },
    ])
  }, [])

  const getReactorState = (): ReactorState => {
    if (isProcessing) return 'thinking'
    if (orbState === 'solving') return 'speaking'
    if (isListening || orbState === 'listening') return 'listening'
    return 'idle'
  }

  // Load Sessions and History
  const loadSessions = useCallback(async () => {
    try {
      const res = await fetch('/api/coding/sessions')
      if (res.ok) {
        const data = await res.json()
        setSessions(data.sessions || [])
      }
    } catch { /* Ignored */ }
  }, [])

  const loadSessionMessages = useCallback(async (sid: string) => {
    try {
      const res = await fetch(`/api/coding/sessions/${sid}/messages`)
      if (res.ok) {
        const data = await res.json()
        setMessages(data.messages || [])
      }
    } catch { /* Ignored */ }
  }, [])

  const loadWorkspaceTree = useCallback(async () => {
    try {
      const res = await fetch('/api/coding/workspace/tree?max_depth=3')
      if (res.ok) {
        const data = await res.json()
        const items = data.result?.items || data.items
        if (items) {
          setTreeData({ name: 'Workspace Root', type: 'directory', path: '.', children: items })
        }
      }
    } catch { /* Ignored */ }
  }, [])

  const loadSkills = useCallback(async () => {
    try {
      const res = await fetch('/api/skills')
      if (res.ok) {
        const data = await res.json()
        if (data.skills) setSkillsList(data.skills)
      }
    } catch { /* Ignored */ }
  }, [])

  // WebSocket listeners
  useEffect(() => {
    socketService.onStateChange = (state) => setConnectionState(state);
    socketService.connect(sessionId);

    const handleResult = (data: any) => {
      setIsProcessing(false);
      const assistantMsg: CodingMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: data.reply || 'Task completed, sir.',
        tool_calls: data.tool_calls || [],
        tool_results: data.tool_results || [],
        diffs: data.diffs || [],
        provider: data.provider || 'openai (gpt-6-astra)',
        timestamp: new Date().toLocaleTimeString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);

      if (data.tool_calls?.length > 0) {
        data.tool_calls.forEach((tc: ToolCallItem) => {
          addActivity('tool', `Executed: ${tc.name}`);
        });
      }
      if (data.diffs?.length > 0) {
        addActivity('success', `Modified ${data.diffs.length} file(s)`);
        loadWorkspaceTree();
        if (selectedFile) openFileInInspector(selectedFile);
      }
      addActivity('info', data.reply?.slice(0, 80) || 'Task completed');
      if (data.reply) speakJarvis(data.reply);
    };

    const handleStatus = (msg: string) => {
      addActivity('info', `Status: ${msg}`);
    };

    const handleCancelled = () => {
      setIsProcessing(false);
      addActivity('info', 'Operation cancelled');
      showNotice('Operation cancelled');
    };

    const handleError = (msg: string) => {
      setIsProcessing(false);
      addActivity('error', `Error: ${msg}`);
    };

    const handleConnected = () => {
      addActivity('success', 'WebSocket connected');
    };

    socketService.on('result', handleResult);
    socketService.on('status', handleStatus);
    socketService.on('cancelled', handleCancelled);
    socketService.on('error', handleError);
    socketService.on('connected', handleConnected);

    return () => {
      socketService.off('result', handleResult);
      socketService.off('status', handleStatus);
      socketService.off('cancelled', handleCancelled);
      socketService.off('error', handleError);
      socketService.off('connected', handleConnected);
    };
  }, [sessionId]);

  useEffect(() => {
    if (isCodingMode) {
      loadSessions()
      loadSessionMessages(sessionId)
      loadWorkspaceTree()
      loadSkills()
    }
  }, [isCodingMode, sessionId, loadSessions, loadSessionMessages, loadWorkspaceTree, loadSkills])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isProcessing])

  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [terminalLogs])

  // Open file in Inspector
  const openFileInInspector = async (path: string) => {
    setIsLoadingFile(true)
    setSelectedFile(path)
    setActiveTab('inspector')
    try {
      const res = await fetch(`/api/coding/workspace/file?path=${encodeURIComponent(path)}`)
      if (res.ok) {
        const data = await res.json()
        let content = ''
        let totalLines = 0
        if (data.result) {
          content = data.result.raw || ''
          totalLines = data.result.total_lines || 0
        } else if (data.content) {
          content = data.raw || data.content
          totalLines = data.total_lines || 0
        }
        setFileContent(content)
        setFileOriginalContent(content)
        setFileTotalLines(totalLines)
        setFileModified(false)
      }
    } catch (e) {
      showNotice(`Failed to open file: ${e}`)
    } finally {
      setIsLoadingFile(false)
    }
  }

  const toggleFolder = (path: string) => {
    setExpandedFolders((prev) => ({ ...prev, [path]: !prev[path] }))
  }

  const handleToggleSkill = async (skillId: string, currentEnabled: boolean) => {
    playHudChirp()
    try {
      const res = await fetch('/api/skills/toggle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ skill_id: skillId, enabled: !currentEnabled }),
      })
      if (res.ok) {
        setSkillsList((prev) =>
          prev.map((s) => (s.id === skillId ? { ...s, enabled: !currentEnabled } : s))
        )
        showNotice(`Skill '${skillId}' ${!currentEnabled ? 'ENABLED' : 'DISABLED'}`)
      }
    } catch {
      showNotice('Failed to toggle skill')
    }
  }

  // Save File
  const handleSaveFile = async () => {
    if (!selectedFile) return
    playHudChirp()
    try {
      const res = await fetch('/api/coding/workspace/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: selectedFile, content: fileContent, overwrite: true }),
      })
      if (res.ok) {
        setFileOriginalContent(fileContent)
        setFileModified(false)
        showNotice(`Saved ${selectedFile}`)
        addActivity('success', `Saved: ${selectedFile}`)
      }
    } catch (e) {
      showNotice(`Save error: ${e}`)
    }
  }

  // Rollback File
  const handleRollback = async (path: string) => {
    playHudChirp()
    try {
      const res = await fetch('/api/coding/rollback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path }),
      })
      const data = await res.json()
      if (data.result?.success || data.success) {
        showNotice(`Reverted ${path}`)
        addActivity('info', `Rolled back: ${path}`)
        openFileInInspector(path)
      } else {
        showNotice(`Rollback failed: ${data.result?.error || data.error}`)
      }
    } catch (e) {
      showNotice(`Rollback error: ${e}`)
    }
  }

  // Run Terminal Command
  const handleRunCommand = async (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    const cmd = terminalInput.trim()
    if (!cmd) return
    playHudChirp()
    setTerminalInput('')
    const ts = new Date().toLocaleTimeString()
    try {
      const res = await fetch('/api/coding/workspace/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: cmd, cwd: '.' }),
      })
      const data = await res.json()
      const resultObj = data.result || data
      const output = resultObj.stdout || resultObj.stderr || resultObj.error || 'Done.'
      const success = resultObj.success !== false
      setTerminalLogs((prev) => [...prev, { cmd, output, success, timestamp: ts }])
      addActivity(success ? 'success' : 'error', `Terminal: ${cmd.slice(0, 40)}`)
    } catch (err) {
      setTerminalLogs((prev) => [...prev, { cmd, output: String(err), success: false, timestamp: ts }])
    }
  }

  // Send Coding Prompt
  const handleSendMessage = async (textToSend?: string) => {
    const prompt = (textToSend || inputText).trim()
    if (!prompt || isProcessing) return

    playHudChirp()
    setInputText('')
    setIsProcessing(true)

    const userMsg: CodingMessage = {
      id: Date.now(),
      role: 'user',
      content: prompt,
      timestamp: new Date().toLocaleTimeString(),
    }
    setMessages((prev) => [...prev, userMsg])
    addActivity('info', `Sent: ${prompt.slice(0, 50)}`)

    const sent = socketService.sendMessage(prompt, selectedFile || '')
    if (!sent) {
      setIsProcessing(false)
      addActivity('error', 'Failed to send — WebSocket disconnected')
      showNotice('Connection lost. Attempting reconnect...')
    }
  }

  // Stop Operation
  const handleStop = () => {
    playHudChirp()
    socketService.sendCancel()
    setIsProcessing(false)
    addActivity('info', 'Stop requested')
  }

  // Clear Terminal
  const handleClearTerminal = () => {
    playHudChirp()
    setTerminalLogs([])
    addActivity('info', 'Terminal cleared')
  }

  // Clear Chat
  const handleClearChat = () => {
    playHudChirp()
    setMessages([])
    setActivityLog([])
    addActivity('info', 'Chat cleared')
  }

  // Create New Session
  const handleNewSession = async () => {
    playHudChirp()
    try {
      const res = await fetch('/api/coding/sessions/new', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: `Task #${sessions.length + 1}` }),
      })
      if (res.ok) {
        const data = await res.json()
        setSessionId(data.session.id)
        setMessages([])
        loadSessions()
        showNotice(`New session: ${data.session.id}`)
      }
    } catch {
      showNotice('Failed to create session')
    }
  }

  // Handle file content changes
  const handleFileContentChange = (newContent: string) => {
    setFileContent(newContent)
    setFileModified(newContent !== fileOriginalContent)
  }

  // Keyboard shortcut for save
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's' && isCodingMode && selectedFile) {
        e.preventDefault()
        handleSaveFile()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [isCodingMode, selectedFile, fileContent])

  if (!isCodingMode) return null

  const lineNumbers = fileContent.split('\n').length

  const connectionColor = {
    connected: 'text-emerald-400',
    connecting: 'text-amber-400',
    disconnected: 'text-red-400',
    error: 'text-red-400',
  }[connectionState]

  const connectionDot = {
    connected: 'bg-emerald-400',
    connecting: 'bg-amber-400 animate-pulse',
    disconnected: 'bg-red-400',
    error: 'bg-red-400 animate-pulse',
  }[connectionState]

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-[#02050f]/98 text-white backdrop-blur-2xl select-none font-sans overflow-hidden">
      {/* HEADER */}
      <header className="relative flex h-12 shrink-0 items-center justify-between border-b border-cyan-500/30 bg-[#04091a] px-4 shadow-[0_2px_16px_rgba(0,229,255,0.08)]">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-cyan-400/50 bg-cyan-950/40 text-cyan-300 shadow-[0_0_10px_rgba(0,229,255,0.2)]">
            <svg className="h-4 w-4 text-[#00e5ff]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="12 2 2 7 12 12 22 7 12 2" />
              <polyline points="2 17 12 22 22 17" />
              <polyline points="2 12 12 17 22 12" />
            </svg>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-black tracking-widest text-white drop-shadow-[0_0_6px_rgba(0,229,255,0.5)]">
                J.A.R.V.I.S. CODING LAB
              </span>
              <span className="rounded-full border border-amber-500/50 bg-amber-500/10 px-1.5 py-0.5 font-mono text-[8px] font-bold text-amber-300">
                GPT-6 ASTRA
              </span>
            </div>
            <div className="font-mono text-[9px] text-cyan-400/60">
              AUTONOMOUS AI WORKSPACE
            </div>
          </div>
        </div>

        {/* Center Session Controls */}
        <div className="hidden md:flex items-center gap-2">
          <select
            value={sessionId}
            onChange={(e) => {
              setSessionId(e.target.value)
              loadSessionMessages(e.target.value)
            }}
            className="rounded-lg border border-cyan-500/30 bg-[#061026] px-2 py-1 font-mono text-[10px] text-cyan-200 focus:outline-none focus:border-[#00e5ff]"
          >
            <option value="default_coding">default_coding</option>
            {sessions.map((s) => (
              <option key={s.id} value={s.id}>{s.title || s.id}</option>
            ))}
          </select>
          <button
            type="button"
            onClick={handleNewSession}
            className="rounded-lg border border-cyan-400/40 bg-cyan-500/15 px-2.5 py-1 font-mono text-[10px] font-bold text-cyan-300 hover:bg-[#00e5ff] hover:text-black transition-all cursor-pointer"
          >
            + New
          </button>
        </div>

        {/* Right Controls */}
        <div className="flex items-center gap-2">
          {notification && (
            <div className="rounded-lg border border-amber-400/60 bg-[#091530] px-2.5 py-1 font-mono text-[10px] text-amber-300 animate-pulse max-w-[200px] truncate">
              {notification}
            </div>
          )}

          {/* Connection Indicator */}
          <div className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-2 py-1">
            <span className={`h-1.5 w-1.5 rounded-full ${connectionDot}`} />
            <span className={`font-mono text-[9px] font-bold ${connectionColor}`}>
              {connectionState.toUpperCase()}
            </span>
          </div>

          {/* Voice Toggle */}
          <button
            type="button"
            onClick={async () => {
              playHudChirp()
              await voiceController.toggleListening()
            }}
            className={`flex items-center gap-1 rounded-lg border px-2 py-1 font-mono text-[10px] font-bold transition-all cursor-pointer ${
              isListening
                ? 'border-cyan-400 bg-cyan-400/20 text-cyan-300 shadow-[0_0_10px_rgba(0,229,255,0.3)] animate-pulse'
                : 'border-white/15 bg-white/5 text-white/60 hover:text-white'
            }`}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${isListening ? 'bg-cyan-400 animate-ping' : 'bg-white/30'}`} />
            MIC
          </button>

          {/* Close */}
          <button
            type="button"
            onClick={() => {
              playHudChirp()
              toggleCodingMode(false)
            }}
            className="flex h-7 w-7 items-center justify-center rounded-lg border border-white/15 bg-white/5 text-white/60 hover:border-red-400 hover:bg-red-500/20 hover:text-red-300 transition-all cursor-pointer"
          >
            <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
      </header>

      {/* ACTION TOOLBAR */}
      <div className="flex items-center justify-between border-b border-cyan-500/20 bg-[#030818] px-4 py-1.5">
        <div className="flex items-center gap-1.5">
          {/* Run Button */}
          <button
            type="button"
            onClick={() => {
              if (activeTab === 'terminal') {
                handleRunCommand()
              } else if (selectedFile) {
                const ext = selectedFile.split('.').pop()?.toLowerCase() || ''
                const runCmd = ext === 'py' ? `python ${selectedFile}` : ext === 'js' || ext === 'ts' ? `node ${selectedFile}` : ''
                if (runCmd) {
                  setTerminalInput(runCmd)
                  setActiveTab('terminal')
                  setTimeout(() => handleRunCommand(), 50)
                } else {
                  showNotice('No runner for this file type')
                }
              }
            }}
            className="flex items-center gap-1.5 rounded-lg border border-emerald-500/40 bg-emerald-500/15 px-3 py-1.5 font-mono text-[10px] font-bold text-emerald-300 hover:bg-emerald-500 hover:text-black transition-all cursor-pointer"
          >
            <svg className="h-3 w-3" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3" /></svg>
            Run
          </button>

          {/* Stop Button */}
          <button
            type="button"
            onClick={handleStop}
            disabled={!isProcessing}
            className="flex items-center gap-1.5 rounded-lg border border-red-500/40 bg-red-500/15 px-3 py-1.5 font-mono text-[10px] font-bold text-red-300 hover:bg-red-500 hover:text-black transition-all cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <svg className="h-3 w-3" viewBox="0 0 24 24" fill="currentColor"><rect x="4" y="4" width="16" height="16" rx="2" /></svg>
            Stop
          </button>

          {/* Save Button */}
          <button
            type="button"
            onClick={handleSaveFile}
            disabled={!selectedFile || !fileModified}
            className="flex items-center gap-1.5 rounded-lg border border-cyan-500/40 bg-cyan-500/15 px-3 py-1.5 font-mono text-[10px] font-bold text-cyan-300 hover:bg-[#00e5ff] hover:text-black transition-all cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <svg className="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" /><polyline points="17 21 17 13 7 13 7 21" /><polyline points="7 3 7 8 15 8" /></svg>
            Save
            {fileModified && <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse" />}
          </button>

          {/* Clear Button */}
          <button
            type="button"
            onClick={() => {
              if (activeTab === 'terminal') handleClearTerminal()
              else handleClearChat()
            }}
            className="flex items-center gap-1.5 rounded-lg border border-white/20 bg-white/5 px-3 py-1.5 font-mono text-[10px] font-bold text-white/60 hover:text-white hover:bg-white/10 transition-all cursor-pointer"
          >
            <svg className="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /></svg>
            Clear {activeTab === 'terminal' ? 'Terminal' : 'Chat'}
          </button>
        </div>

        {/* Right side: Quick actions */}
        <div className="flex items-center gap-1.5">
          {selectedFile && (
            <span className="font-mono text-[9px] text-white/40">
              {getLanguageFromExt(selectedFile)} {fileModified && '• Modified'}
            </span>
          )}
          <ArcReactor3D state={getReactorState()} audioLevel={audioLevel} size={32} interactive={false} />
        </div>
      </div>

      {/* MAIN BODY */}
      <div className="flex flex-1 overflow-hidden">
        {/* LEFT: Chat + Activity */}
        <div className="flex flex-col flex-1 max-w-[55%] border-r border-cyan-500/20 bg-[#030714] min-w-[420px]">
          {/* Quick Prompts */}
          <div className="flex items-center gap-1.5 border-b border-cyan-500/15 bg-[#040a1d]/50 px-3 py-1.5 overflow-x-auto text-[10px] font-mono">
            <span className="text-cyan-400/50 font-bold shrink-0">QUICK:</span>
            {[
              { label: 'Scan Workspace', prompt: 'Use workspace_tree to list the project structure and give an architecture overview.' },
              { label: 'Audit Backend', prompt: 'Audit the backend endpoints in app/main.py and verify security.' },
              { label: 'Git Status', prompt: 'Run git_status and summarize current branch changes.' },
              { label: 'Test Skills', prompt: 'List all active skills and test system_telemetry and workspace_tree tools.' },
            ].map((q, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleSendMessage(q.prompt)}
                disabled={isProcessing}
                className="shrink-0 rounded-full border border-cyan-500/25 bg-[#06142e] px-2 py-0.5 text-cyan-200 hover:border-cyan-400 hover:text-white transition-all cursor-pointer disabled:opacity-40"
              >
                {q.label}
              </button>
            ))}
          </div>

          {/* Chat Messages */}
          <div className="flex-1 overflow-y-auto p-3 space-y-3 font-mono text-xs">
            {messages.length === 0 && !isProcessing && (
              <div className="flex flex-col items-center justify-center h-full text-center px-6 text-cyan-300/60">
                <ArcReactor3D state={getReactorState()} audioLevel={audioLevel} size={140} />
                <h3 className="mt-3 font-mono text-sm font-bold text-white tracking-widest">
                  AUTONOMOUS CODING READY
                </h3>
                <p className="mt-1 text-[10px] text-cyan-200/50 max-w-sm">
                  Read, edit, debug, generate and run code. All edits are auto-backed up and reversible.
                </p>
              </div>
            )}

            {messages.map((m) => (
              <div
                key={m.id}
                className={`flex flex-col gap-1 ${m.role === 'user' ? 'items-end' : 'items-start'}`}
              >
                <div className="flex items-center gap-1.5 text-[9px] text-white/40">
                  <span className={`font-bold ${m.role === 'user' ? 'text-cyan-400' : 'text-amber-400'}`}>
                    {m.role === 'user' ? 'STARK' : `JARVIS [${m.provider?.split('(')[1]?.replace(')', '') || 'GPT-6'}]`}
                  </span>
                  <span>{m.timestamp || ''}</span>
                </div>

                <div
                  className={`max-w-[92%] rounded-xl px-3 py-2 leading-relaxed whitespace-pre-wrap ${
                    m.role === 'user'
                      ? 'border border-cyan-500/50 bg-[#071a38] text-white shadow-[0_0_12px_rgba(0,229,255,0.08)]'
                      : 'border border-amber-500/30 bg-[#091224] text-cyan-100 shadow-[0_0_12px_rgba(255,160,0,0.06)]'
                  }`}
                >
                  {m.content}

                  {m.tool_calls && m.tool_calls.length > 0 && (
                    <div className="mt-2 space-y-1 border-t border-cyan-500/20 pt-2">
                      <div className="text-[9px] font-bold uppercase tracking-wider text-cyan-400 flex items-center gap-1">
                        <span className="h-1 w-1 rounded-full bg-cyan-400 animate-ping" />
                        Tools ({m.tool_calls.length})
                      </div>
                      {m.tool_calls.map((tc, idx) => (
                        <div key={idx} className="rounded-lg border border-cyan-500/20 bg-[#040c1d] p-1.5 text-[10px]">
                          <div className="flex items-center justify-between text-cyan-300 font-bold">
                            <span>{tc.name}</span>
                            <span className="text-[8px] text-emerald-400">OK</span>
                          </div>
                          <div className="text-[9px] text-cyan-200/50 truncate">
                            {JSON.stringify(tc.arguments).slice(0, 80)}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {m.diffs && m.diffs.length > 0 && (
                    <div className="mt-2 space-y-1.5 border-t border-amber-500/20 pt-2">
                      <div className="text-[9px] font-bold uppercase tracking-wider text-amber-400">
                        Code Changes
                      </div>
                      {m.diffs.map((d, idx) => (
                        <div key={idx} className="rounded-lg border border-amber-500/30 bg-[#050e20] p-2">
                          <div className="flex items-center justify-between text-white font-bold mb-1">
                            <span className="text-[10px]">{d.path}</span>
                            <button
                              type="button"
                              onClick={() => handleRollback(d.path)}
                              className="rounded bg-red-500/20 px-1.5 py-0.5 text-[8px] text-red-300 hover:bg-red-500 hover:text-white cursor-pointer"
                            >
                              Rollback
                            </button>
                          </div>
                          <pre className="overflow-x-auto text-[9px] text-emerald-300 bg-black/50 p-1.5 rounded max-h-28">
                            {d.diff}
                          </pre>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {isProcessing && (
              <div className="flex items-center gap-2 text-amber-300 text-[10px] animate-pulse p-2 rounded-lg border border-amber-500/20 bg-amber-500/5">
                <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-ping" />
                <span>Reasoning and executing...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Activity Feed (compact) */}
          {activityLog.length > 0 && (
            <div className="border-t border-cyan-500/15 bg-[#020610] px-3 py-1.5 max-h-20 overflow-y-auto">
              <div className="text-[8px] font-mono font-bold text-cyan-400/50 uppercase tracking-wider mb-1">Activity</div>
              {activityLog.slice(-5).map((a) => (
                <div key={a.id} className="flex items-center gap-1.5 text-[9px] font-mono">
                  <span className="text-white/30">{a.timestamp}</span>
                  <span className={
                    a.type === 'error' ? 'text-red-400' :
                    a.type === 'success' ? 'text-emerald-400' :
                    a.type === 'tool' ? 'text-cyan-300' : 'text-white/50'
                  }>
                    {a.type === 'error' ? '✕' : a.type === 'success' ? '✓' : a.type === 'tool' ? '⚡' : '›'} {a.message}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Chat Input */}
          <div className="border-t border-cyan-500/20 bg-[#040b1e] p-2.5">
            <form
              onSubmit={(e) => {
                e.preventDefault()
                handleSendMessage()
              }}
              className="flex items-center gap-2 rounded-xl border border-cyan-500/40 bg-[#06122a] px-3 py-1.5 focus-within:border-[#00e5ff] shadow-[0_0_12px_rgba(0,229,255,0.08)]"
            >
              <textarea
                ref={textareaRef}
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    handleSendMessage()
                  }
                }}
                placeholder="Instruct JARVIS to write, debug, or inspect code..."
                rows={1}
                className="flex-1 bg-transparent font-mono text-[11px] text-white placeholder-white/30 focus:outline-none resize-none"
              />
              <button
                type="submit"
                disabled={isProcessing || !inputText.trim()}
                className="flex h-7 w-7 items-center justify-center rounded-lg bg-[#00e5ff] text-black font-extrabold hover:bg-cyan-300 transition-all cursor-pointer disabled:opacity-30"
              >
                <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <line x1="5" y1="12" x2="19" y2="12" />
                  <polyline points="12 5 19 12 12 19" />
                </svg>
              </button>
            </form>
          </div>
        </div>

        {/* RIGHT: Multi-Tab Panel */}
        <div className="flex flex-col flex-1 bg-[#020510] overflow-hidden">
          {/* Tab Header */}
          <div className="flex items-center justify-between border-b border-cyan-500/20 bg-[#04091a] px-3">
            <div className="flex items-center gap-0.5 font-mono text-[10px] font-bold">
              {[
                { id: 'explorer', label: 'Explorer' },
                { id: 'inspector', label: selectedFile ? `Editor: ${selectedFile.split('/').pop()}` : 'Editor' },
                { id: 'terminal', label: 'Terminal' },
                { id: 'skills', label: `Skills (${skillsList.length})` },
              ].map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => {
                    playHudChirp()
                    setActiveTab(tab.id as any)
                  }}
                  className={`border-b-2 px-2.5 py-2 transition-all cursor-pointer ${
                    activeTab === tab.id
                      ? 'border-[#00e5ff] text-[#00e5ff] bg-cyan-500/5'
                      : 'border-transparent text-white/50 hover:text-white/80'
                  }`}
                >
                  {tab.label}
                  {tab.id === 'inspector' && fileModified && (
                    <span className="ml-1 h-1.5 w-1.5 rounded-full bg-amber-400 inline-block" />
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* TAB 1: EXPLORER */}
          {activeTab === 'explorer' && (
            <div className="flex-1 overflow-y-auto p-3 font-mono text-[11px] space-y-0.5">
              <div className="flex items-center justify-between pb-2 border-b border-cyan-500/15 text-cyan-400 font-bold text-[10px]">
                <span>WORKSPACE</span>
                <button
                  type="button"
                  onClick={loadWorkspaceTree}
                  className="text-[9px] text-cyan-300 hover:underline cursor-pointer"
                >
                  Refresh
                </button>
              </div>
              {treeData && (
                <div className="mt-2 space-y-0">
                  {renderTreeNodes(treeData.children || [], 0, expandedFolders, toggleFolder, openFileInInspector, selectedFile)}
                </div>
              )}
            </div>
          )}

          {/* TAB 2: CODE EDITOR with line numbers */}
          {activeTab === 'inspector' && (
            <div className="flex flex-col flex-1 overflow-hidden font-mono text-[11px]">
              {isLoadingFile ? (
                <div className="flex flex-1 items-center justify-center text-cyan-400 animate-pulse text-xs">
                  Loading file...
                </div>
              ) : selectedFile ? (
                <>
                  {/* Editor toolbar */}
                  <div className="flex items-center justify-between border-b border-cyan-500/15 bg-[#050c20] px-3 py-1.5">
                    <div className="flex items-center gap-2">
                      <span className="text-cyan-300 font-bold text-[10px]">{getFileIcon(selectedFile)} {selectedFile}</span>
                      <span className="text-white/30 text-[9px]">{fileTotalLines || lineNumbers} lines</span>
                      {fileModified && (
                        <span className="rounded bg-amber-500/20 border border-amber-500/30 px-1.5 py-0.5 text-[8px] text-amber-300 font-bold">MODIFIED</span>
                      )}
                    </div>
                    <div className="flex items-center gap-1.5">
                      <button
                        type="button"
                        onClick={() => handleRollback(selectedFile)}
                        className="rounded border border-red-500/30 bg-red-500/10 px-2 py-0.5 text-[9px] text-red-300 hover:bg-red-500 hover:text-white cursor-pointer"
                      >
                        Rollback
                      </button>
                      <button
                        type="button"
                        onClick={handleSaveFile}
                        disabled={!fileModified}
                        className="rounded bg-[#00e5ff] px-2.5 py-0.5 text-[9px] font-bold text-black hover:bg-cyan-300 cursor-pointer disabled:opacity-30 shadow-[0_0_6px_rgba(0,229,255,0.3)]"
                      >
                        Save
                      </button>
                    </div>
                  </div>

                  {/* Editor with line numbers */}
                  <div className="flex flex-1 overflow-hidden">
                    {/* Line numbers gutter */}
                    <div className="shrink-0 overflow-hidden bg-[#030810] border-r border-cyan-500/10 select-none">
                      <div className="py-2 px-2 text-right">
                        {Array.from({ length: lineNumbers }, (_, i) => (
                          <div key={i} className="text-[10px] leading-[1.6] text-white/20 font-mono">
                            {i + 1}
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Code textarea */}
                    <textarea
                      value={fileContent}
                      onChange={(e) => handleFileContentChange(e.target.value)}
                      className="flex-1 w-full bg-[#02050e] p-2 text-[11px] font-mono text-cyan-100 focus:outline-none resize-none leading-[1.6] tab-size-2"
                      spellCheck={false}
                      style={{ tabSize: 2 }}
                    />
                  </div>
                </>
              ) : (
                <div className="flex flex-1 items-center justify-center text-white/30 text-xs">
                  Select a file from Explorer to inspect or edit.
                </div>
              )}
            </div>
          )}

          {/* TAB 3: TERMINAL */}
          {activeTab === 'terminal' && (
            <div className="flex flex-col flex-1 bg-[#010408] overflow-hidden">
              <div className="flex-1 overflow-y-auto p-3 space-y-2 font-mono text-[11px]">
                {terminalLogs.length === 0 && (
                  <div className="text-white/20 text-center py-8 text-xs">
                    Terminal ready. Enter a command below.
                  </div>
                )}
                {terminalLogs.map((log, i) => (
                  <div key={i} className="space-y-0.5">
                    <div className="flex items-center gap-1.5 text-white font-bold text-[10px]">
                      <span className="text-cyan-400">jarvis@stark</span>
                      <span className="text-white/40">:</span>
                      <span className="text-emerald-400">~</span>
                      <span className="text-white/40">$</span>
                      <span>{log.cmd}</span>
                      <span className="ml-auto text-[8px] text-white/20">{log.timestamp}</span>
                    </div>
                    <pre className={`p-1.5 rounded text-[10px] whitespace-pre-wrap leading-relaxed ${
                      log.success
                        ? 'text-cyan-200 bg-[#040e22]'
                        : 'text-red-300 bg-red-950/20 border border-red-500/20'
                    }`}>
                      {log.output}
                    </pre>
                  </div>
                ))}
                <div ref={terminalEndRef} />
              </div>

              <form onSubmit={handleRunCommand} className="flex items-center gap-2 border-t border-cyan-500/20 bg-[#030810] px-3 py-2">
                <span className="text-cyan-400 font-mono text-[10px] font-bold">$</span>
                <input
                  type="text"
                  value={terminalInput}
                  onChange={(e) => setTerminalInput(e.target.value)}
                  placeholder="Enter command..."
                  className="flex-1 bg-transparent font-mono text-[11px] text-white focus:outline-none placeholder-white/20"
                />
                <button
                  type="submit"
                  className="rounded bg-cyan-500/20 px-2.5 py-1 text-cyan-300 hover:bg-[#00e5ff] hover:text-black font-bold text-[10px] cursor-pointer font-mono"
                >
                  Run
                </button>
              </form>
            </div>
          )}

          {/* TAB 4: SKILLS */}
          {activeTab === 'skills' && (
            <div className="flex-1 overflow-y-auto p-3 space-y-2.5 font-mono text-[11px]">
              <div className="border-b border-cyan-500/15 pb-1.5 text-cyan-400 font-bold text-[10px]">
                SKILL PLUGINS & TOOL REGISTRY
              </div>
              {skillsList.map((skill) => (
                <div
                  key={skill.id}
                  className={`rounded-xl border p-3 transition-all ${
                    skill.enabled
                      ? 'border-cyan-400/40 bg-[#06122c] shadow-[0_0_12px_rgba(0,229,255,0.06)]'
                      : 'border-white/8 bg-[#040817] opacity-50'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-sm">⚡</span>
                      <div>
                        <div className="font-bold text-white text-xs">{skill.display_name}</div>
                        <div className="text-[9px] text-cyan-300/60">{skill.tools_count} tools</div>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleToggleSkill(skill.id, skill.enabled)}
                      className={`rounded-full px-2.5 py-0.5 font-bold text-[9px] transition-all cursor-pointer ${
                        skill.enabled
                          ? 'bg-[#00e5ff] text-black shadow-[0_0_8px_rgba(0,229,255,0.3)]'
                          : 'bg-white/10 text-white/40 hover:bg-white/20'
                      }`}
                    >
                      {skill.enabled ? 'ACTIVE' : 'OFF'}
                    </button>
                  </div>
                  <p className="mt-1.5 text-[10px] text-white/60">{skill.description}</p>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {skill.tools?.map((tool, idx) => (
                      <span key={idx} className="rounded bg-[#020718] border border-cyan-500/20 px-1.5 py-0.5 text-[8px] text-cyan-200">
                        {tool.name}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* STATUS BAR */}
      <div className="flex items-center justify-between border-t border-cyan-500/15 bg-[#030810] px-4 py-1 font-mono text-[9px]">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1">
            <span className={`h-1 w-1 rounded-full ${connectionDot}`} />
            <span className={connectionColor}>{connectionState}</span>
          </span>
          <span className="text-white/30">Session: {sessionId}</span>
          {selectedFile && (
            <span className="text-white/30">File: {selectedFile}</span>
          )}
        </div>
        <div className="flex items-center gap-3 text-white/30">
          <span>Ln {lineNumbers}</span>
          <span>UTF-8</span>
          <span>{selectedFile ? getLanguageFromExt(selectedFile) : 'Plain Text'}</span>
        </div>
      </div>
    </div>
  )
}

function renderTreeNodes(
  nodes: TreeNode[],
  depth: number,
  expanded: Record<string, boolean>,
  onToggle: (path: string) => void,
  onOpenFile: (path: string) => void,
  selectedFile: string | null
) {
  return nodes.map((node) => {
    const isFolder = node.type === 'directory'
    const isExpanded = !!expanded[node.path]
    const isSelected = node.path === selectedFile

    return (
      <div key={node.path} style={{ paddingLeft: `${depth * 12}px` }}>
        {isFolder ? (
          <div>
            <div
              onClick={() => onToggle(node.path)}
              className="flex items-center gap-1 py-0.5 text-cyan-200/80 hover:text-white cursor-pointer select-none text-[10px]"
            >
              <span className="text-[8px] text-white/30">{isExpanded ? '▼' : '▶'}</span>
              <span>📁</span>
              <span>{node.name}</span>
            </div>
            {isExpanded && node.children && (
              <div>{renderTreeNodes(node.children, depth + 1, expanded, onToggle, onOpenFile, selectedFile)}</div>
            )}
          </div>
        ) : (
          <div
            onClick={() => onOpenFile(node.path)}
            className={`flex items-center justify-between py-0.5 cursor-pointer text-[10px] rounded-sm px-1 ${
              isSelected
                ? 'bg-cyan-500/15 text-[#00e5ff]'
                : 'text-white/60 hover:text-[#00e5ff] hover:bg-white/5'
            }`}
          >
            <span className="flex items-center gap-1">
              <span>{getFileIcon(node.name)}</span>
              <span>{node.name}</span>
            </span>
            {node.size !== undefined && (
              <span className="text-[8px] text-white/25">{(node.size / 1024).toFixed(1)}k</span>
            )}
          </div>
        )}
      </div>
    )
  })
}
