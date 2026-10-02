import { create } from 'zustand'

export interface ToolCallEvent {
  id: string
  tool: string
  args: Record<string, unknown>
  status: 'pending' | 'running' | 'completed' | 'error'
  result?: unknown
  timestamp: string
}

export interface TerminalEntry {
  id: string
  cmd: string
  stdout: string
  stderr: string
  exitCode: number
  timestamp: string
}

export interface DiffEntry {
  path: string
  diff: string
  timestamp: string
}

export interface AgentError {
  id: string
  tool?: string
  message: string
  severity: 'warning' | 'error' | 'critical'
  timestamp: string
}

export interface AgentStatus {
  engine: 'jarvis' | 'opencode' | 'idle'
  phase: 'idle' | 'thinking' | 'executing' | 'retrying' | 'complete' | 'error'
  iteration: number
  maxIterations: number
  retries: number
}

interface AgentWorkspaceState {
  isActive: boolean
  agentStatus: AgentStatus
  streamingText: string
  toolCalls: ToolCallEvent[]
  terminalEntries: TerminalEntry[]
  diffs: DiffEntry[]
  errors: AgentError[]
  changedFiles: string[]
  activityLog: Array<{ id: string; type: string; message: string; timestamp: string }>

  setActive: (active: boolean) => void
  reset: () => void
  setAgentStatus: (partial: Partial<AgentStatus>) => void
  appendStreamingText: (delta: string) => void
  clearStreamingText: () => void
  addToolCall: (tool: string, args: Record<string, unknown>) => string
  completeToolCall: (id: string, result: unknown, success: boolean) => void
  addTerminalEntry: (entry: Omit<TerminalEntry, 'id' | 'timestamp'>) => void
  addDiff: (path: string, diff: string) => void
  addError: (message: string, tool?: string, severity?: AgentError['severity']) => void
  addChangedFile: (path: string) => void
  addActivity: (type: string, message: string) => void
}

const defaultAgentStatus: AgentStatus = {
  engine: 'idle',
  phase: 'idle',
  iteration: 0,
  maxIterations: 15,
  retries: 0,
}

export const useAgentWorkspaceStore = create<AgentWorkspaceState>((set, get) => ({
  isActive: false,
  agentStatus: { ...defaultAgentStatus },
  streamingText: '',
  toolCalls: [],
  terminalEntries: [],
  diffs: [],
  errors: [],
  changedFiles: [],
  activityLog: [],

  setActive: (active) => set({ isActive: active }),

  reset: () =>
    set({
      agentStatus: { ...defaultAgentStatus },
      streamingText: '',
      toolCalls: [],
      terminalEntries: [],
      diffs: [],
      errors: [],
      changedFiles: [],
      activityLog: [],
    }),

  setAgentStatus: (partial) =>
    set((s) => ({ agentStatus: { ...s.agentStatus, ...partial } })),

  appendStreamingText: (delta) =>
    set((s) => ({ streamingText: s.streamingText + delta })),

  clearStreamingText: () => set({ streamingText: '' }),

  addToolCall: (tool, args) => {
    const id = `tool_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`
    set((s) => ({
      toolCalls: [
        ...s.toolCalls,
        { id, tool, args, status: 'running', timestamp: new Date().toLocaleTimeString() },
      ],
    }))
    get().addActivity('tool', `▶ ${tool}`)
    return id
  },

  completeToolCall: (id, result, success) =>
    set((s) => ({
      toolCalls: s.toolCalls.map((tc) =>
        tc.id === id ? { ...tc, status: success ? 'completed' : 'error', result } : tc
      ),
    })),

  addTerminalEntry: (entry) =>
    set((s) => ({
      terminalEntries: [
        ...s.terminalEntries,
        {
          ...entry,
          id: `term_${Date.now()}`,
          timestamp: new Date().toLocaleTimeString(),
        },
      ],
    })),

  addDiff: (path, diff) =>
    set((s) => ({
      diffs: [...s.diffs, { path, diff, timestamp: new Date().toLocaleTimeString() }],
      changedFiles: s.changedFiles.includes(path) ? s.changedFiles : [...s.changedFiles, path],
    })),

  addError: (message, tool, severity = 'error') =>
    set((s) => ({
      errors: [
        ...s.errors,
        {
          id: `err_${Date.now()}`,
          tool,
          message,
          severity,
          timestamp: new Date().toLocaleTimeString(),
        },
      ],
    })),

  addChangedFile: (path) =>
    set((s) => ({
      changedFiles: s.changedFiles.includes(path) ? s.changedFiles : [...s.changedFiles, path],
    })),

  addActivity: (type, message) =>
    set((s) => ({
      activityLog: [
        ...s.activityLog.slice(-99),
        { id: `act_${Date.now()}`, type, message, timestamp: new Date().toLocaleTimeString() },
      ],
    })),
}))
