import React, { useState, useEffect, useRef } from 'react'
import { useJarvisStore } from '../../store/useJarvisStore'

interface FileTreeItem {
  name: string
  type: 'file' | 'directory'
  children?: FileTreeItem[]
  path: string
}

interface LiveCodingState {
  sessionId: string
  isStreaming: boolean
  toolCalls: Array<{
    id: string
    name: string
    arguments: any
    status: 'pending' | 'running' | 'completed' | 'error'
  }>
  terminalOutput: string[]
  diffChanges: string[]
  errors: string[]
}

export function LiveCodingWorkspace() {
  const { 
    isCodingMode, 
    messages,
    addMessage,
  } = useJarvisStore()

  const [fileTree, setFileTree] = useState<FileTreeItem[]>([])
  const [activeFile] = useState<string>('')
  const [terminalOutput, setTerminalOutput] = useState<string[]>([])
  const [codingSession, setCodingSession] = useState<LiveCodingState>({
    sessionId: 'session_' + Date.now(),
    isStreaming: false,
    toolCalls: [],
    terminalOutput: [],
    diffChanges: [],
    errors: []
  })
  
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const [inputValue, setInputValue] = useState('')
  const [attachments, setAttachments] = useState<Array<{name: string, url: string, type: string}>>([])
  
  // Initialize coding session
  useEffect(() => {
    if (isCodingMode) {
      initializeCodingSession()
    }
  }, [isCodingMode])
  
  const initializeCodingSession = async () => {
    try {
      const response = await fetch('/api/coding/sessions/new', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: 'Live Coding Session ' + new Date().toLocaleTimeString(),
          active_file: ''
        })
      })
      const data = await response.json()
      if (data.session) {
        setCodingSession(prev => ({ ...prev, sessionId: data.session.id }))
      }
      await loadWorkspaceTree()
    } catch (error) {
      console.error('Failed to initialize coding session:', error)
    }
  }
  
  const loadWorkspaceTree = async () => {
    try {
      const response = await fetch('/api/coding/workspace/tree?max_depth=3')
      const data = await response.json()
      if (data.status === 'ok') {
        setFileTree(data.tree || [])
      }
    } catch (error) {
      console.error('Failed to load workspace tree:', error)
    }
  }
  
  const handleFileUpload = async (files: FileList) => {
    const newAttachments: Array<{name: string, url: string, type: string}> = []
    for (const file of files) {
      try {
        const content = await file.text()
        const base64 = btoa(content)
        
        const response = await fetch('/api/upload', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            filename: file.name,
            content_base64: base64,
            mime_type: file.type,
            category: file.type.startsWith('image/') ? 'image' : 'code'
          })
        })
        const data = await response.json()
        
        if (data.success) {
          newAttachments.push({
            name: file.name,
            url: data.path,
            type: file.type
          })
        }
      } catch (error) {
        console.error('Failed to upload file:', error)
      }
    }
    
    setAttachments(prev => [...prev, ...newAttachments])
  }
  
  const sendMessage = async () => {
    if (!inputValue.trim()) return
    
    const message = inputValue.trim()
    setInputValue('')
    
    // Add user message
    addMessage('user', message)
    setTerminalOutput(prev => [...prev, `> ${message}`])
    
    try {
      const response = await fetch('/api/coding/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: codingSession.sessionId,
          message: message,
          active_file: activeFile,
          auto_run_tools: true
        })
      })
      
      const data = await response.json()
      
      // Process streaming-like output from response
      if (data.tool_calls && data.tool_calls.length > 0) {
        processToolCalls(data.tool_calls)
      }
      
      if (data.diffs && data.diffs.length > 0) {
        setCodingSession(prev => ({ ...prev, diffChanges: data.diffs }))
      }
      
      if (data.terminal_output) {
        setTerminalOutput(prev => [...prev, data.terminal_output])
      }
      
      if (data.error) {
        setCodingSession(prev => ({ 
          ...prev, 
          errors: [...prev.errors, data.error] 
        }))
      }
      
      if (data.reply) {
        addMessage('jarvis', data.reply)
      }
      
      // Refresh workspace tree if files changed
      if (data.file_changes) {
        await loadWorkspaceTree()
      }
      
    } catch (error) {
      const errorMsg = `Error: ${error instanceof Error ? error.message : String(error)}`
      setTerminalOutput(prev => [...prev, errorMsg])
      addMessage('jarvis', `An error occurred: ${errorMsg}`)
    }
  }
  
  const processToolCalls = (toolCalls: any[]) => {
    setCodingSession(prev => ({
      ...prev,
      toolCalls: toolCalls.map(tc => ({
        id: tc.id || Math.random().toString(),
        name: tc.name,
        arguments: tc.arguments,
        status: 'completed'
      }))
    }))
  }
  
  const handleFileUploadInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      handleFileUpload(e.target.files)
      e.target.value = ''
    }
  }
  
  const renderFileTree = () => {
    return (
      <div className="flex-1 overflow-y-auto font-mono text-xs">
        <div className="px-2 py-1 text-sm font-semibold text-cyan-300 border-b border-cyan-500/30">
          Files
        </div>
        {fileTree.length > 0 ? (
          <TreeRenderer nodes={fileTree} />
        ) : (
          <div className="p-4 text-gray-500">Loading workspace...</div>
        )}
      </div>
    )
  }
  
  const renderCodeViewer = () => {
    return (
      <div className="flex-1 flex flex-col">
        <div className="flex items-center justify-between p-2 border-b border-cyan-500/30">
          <h3 className="text-sm font-medium text-cyan-200">
            {activeFile || 'Select a file'}
          </h3>
          <div className="flex gap-2">
            <button 
              className="px-2 py-1 text-xs rounded bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300"
              onClick={() => {}}
            >
              Run
            </button>
          </div>
        </div>
        <div className="flex-1 bg-black/50 overflow-y-auto p-2 font-mono text-xs">
          {activeFile ? (
            <CodeRenderer path={activeFile} />
          ) : (
            <div className="text-gray-500">Select a file to view</div>
          )}
        </div>
      </div>
    )
  }
  
  const renderTerminal = () => {
    return (
      <div className="flex-1 flex flex-col bg-black/30">
        <div className="border-b border-cyan-500/30 p-2">
          <span className="text-cyan-400">$</span>
        </div>
        <div className="flex-1 overflow-y-auto p-2 font-mono text-xs">
          <pre className="whitespace-pre-wrap text-green-400">
            {terminalOutput.join('\n')}
          </pre>
        </div>
      </div>
    )
  }
  
  const renderChat = () => {
    return (
      <div className="flex flex-col h-full">
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {messages.map((msg, idx) => (
            <div 
              key={idx}
              className={`flex ${
                msg.sender === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              <div 
                className={`max-w-[80%] p-2 rounded-lg ${
                  msg.sender === 'user' 
                    ? 'bg-cyan-500/20 text-cyan-100'
                    : 'bg-gray-800/50 text-gray-200'
                }`}
              >
                {msg.text}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
        
        {/* Attachments preview */}
        {attachments.length > 0 && (
          <div className="flex gap-2 p-2 border-b border-cyan-500/30 flex-wrap">
            {attachments.map((att, idx) => (
              <div 
                key={idx} 
                className="flex items-center gap-1 px-2 py-1 bg-cyan-500/10 rounded text-xs"
              >
                <span className="text-cyan-400">📎</span>
                <span className="text-gray-300">{att.name}</span>
              </div>
            ))}
          </div>
        )}
        
        {/* Input area */}
        <div className="p-2 border-t border-cyan-500/30">
          <div className="flex gap-2">
            <label className="flex items-center px-3 py-2 bg-cyan-500/10 border border-cyan-500/30 rounded-lg text-cyan-400 text-xs cursor-pointer hover:bg-cyan-500/20 transition-colors" title="Attach files to this session">
              📎
              <input
                type="file"
                multiple
                className="hidden"
                onChange={handleFileUploadInput}
              />
            </label>
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
              placeholder="Type a command..."
              className="flex-1 px-3 py-1 rounded bg-gray-800/50 text-cyan-100 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500"
            />
            <button
              onClick={sendMessage}
              className="px-4 py-1 rounded bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 transition-colors"
            >
              Send
            </button>
          </div>
        </div>
      </div>
    )
  }
  
  return (
    <div className="h-full flex bg-gradient-to-br from-[#040916] to-[#061226] text-cyan-100">
      {/* Left Sidebar: File Explorer */}
      <div className="hidden xl:block w-64 border-r border-cyan-500/20 overflow-hidden">
        <div className="p-3 border-b border-cyan-500/30">
          <h2 className="text-lg font-semibold text-cyan-200">Explorer</h2>
        </div>
        {renderFileTree()}
      </div>
      
      {/* Center: Code Viewer */}
      <div className="hidden md:block w-96 border-r border-cyan-500/20 overflow-hidden">
        {renderCodeViewer()}
      </div>
      
      {/* Right Panel: Chat + Terminal */}
      <div className="hidden lg:block flex-col w-96 border-l border-cyan-500/20 overflow-hidden">
        <div className="flex-1 overflow-y-auto">
          {renderChat()}
        </div>
        <div className="h-48 border-t border-cyan-500/30">
          {renderTerminal()}
        </div>
      </div>
      
      {/* Mobile: Tabs */}
      <div className="lg:hidden flex-1 flex flex-col">
        <div className="border-b border-cyan-500/30 p-2">
          <div className="flex gap-2">
            <button className="px-3 py-1 text-xs rounded bg-cyan-500/20">Chat</button>
            <button className="px-3 py-1 text-xs rounded bg-cyan-500/20">Files</button>
            <button className="px-3 py-1 text-xs rounded bg-cyan-500/20">Terminal</button>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto">
          {renderChat()}
        </div>
      </div>
    </div>
  )
}

// Helper components
function TreeRenderer({ nodes }: { nodes: FileTreeItem[] }) {
  return (
    <div className="tree-container">
      {nodes.map(node => (
        <TreeNode key={node.path} node={node} />
      ))}
    </div>
  )
}

function TreeNode({ node }: { node: FileTreeItem }) {
  const [expanded, setExpanded] = useState(false)
  const [selected, setSelected] = useState(false)
  
  const handleClick = () => {
    if (node.type === 'directory') {
      setExpanded(!expanded)
    } else {
      setSelected(true)
    }
  }
  
  return (
    <div>
      <div 
        className={`flex items-center gap-1 p-1 rounded hover:bg-cyan-500/10 cursor-pointer ${
          selected && 'bg-cyan-500/20'
        }`}
        onClick={handleClick}
      >
        {node.type === 'directory' && (
          <span className="text-cyan-400">
            {expanded ? '📁' : '📂'}
          </span>
        )}
        {node.type === 'file' && (
          <span className="text-green-400">📄</span>
        )}
        <span className="text-gray-300">{node.name}</span>
      </div>
      {expanded && node.children && (
        <div className="ml-4">
          <TreeRenderer nodes={node.children} />
        </div>
      )}
    </div>
  )
}

function CodeRenderer({ path }: { path: string }) {
  const [code, setCode] = useState('')
  const [loading, setLoading] = useState(true)
  
  useEffect(() => {
    if (path) {
      loadFile(path)
    }
  }, [path])
  
  const loadFile = async (filePath: string) => {
    try {
      const response = await fetch(`/api/coding/workspace/file?path=${encodeURIComponent(filePath)}`)
      const data = await response.json()
      if (data.content) {
        setCode(data.content)
      }
    } catch (error) {
      console.error('Failed to load file:', error)
    } finally {
      setLoading(false)
    }
  }
  
  if (loading) {
    return <div className="text-gray-500 p-4">Loading...</div>
  }
  
  return (
    <pre className="whitespace-pre-wrap break-all text-xs">
      {code || 'No content'}
    </pre>
  )
}

export default LiveCodingWorkspace