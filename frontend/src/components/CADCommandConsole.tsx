import React, { useState, useEffect, useRef } from 'react'
import { useJarvisStore, playHudChirp, speakJarvis } from '../store/useJarvisStore'

interface CandidateObject {
  id: string
  name: string
  type?: string
}

interface FileAttachment {
  filename: string
  path: string
  url?: string
  mime_type?: string
  size?: number
  category?: string
}

interface PendingFile {
  id: string
  name: string
  size: number
  mime_type: string
  isImage: boolean
  previewUrl: string
  ref: FileAttachment
}

interface ConsoleLog {
  id: string
  text: string
  type: 'cmd' | 'resp' | 'sys' | 'err' | 'ambiguous'
  timestamp: string
  action?: string
  parameters?: Record<string, any>
  durationMs?: number
  candidates?: CandidateObject[]
  attachments?: FileAttachment[]
  outputs?: FileAttachment[]
}

const MAX_FILE_MB = 60

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result).split(',')[1] || '')
    reader.onerror = () => reject(new Error('Could not read the file locally'))
    reader.readAsDataURL(file)
  })
}

function isImageLike(name: string, mime: string) {
  return mime.startsWith('image/') || /\.(png|jpe?g|webp|gif|bmp|tiff?)$/i.test(name)
}

export default function CADCommandConsole() {
  const [inputVal, setInputVal] = useState('')
  const [logs, setLogs] = useState<ConsoleLog[]>([
    {
      id: 'init-1',
      text: 'J.A.R.V.I.S. CAD Command Pipeline Initialized. Voice and text are synchronized.',
      type: 'sys',
      timestamp: '00:00:00',
    },
    {
      id: 'init-2',
      text: 'Try: "Create a box 100 by 60 by 20 mm", "Make a 10 mm hole at the center", "Move that cylinder 50 mm on X", "Rotate selected part 45 degrees", "Undo that". Attach files with the paperclip, drag-drop or Ctrl+V, then ask: "analyze this image", "remove the circle", "summarize this file", "use this in CAD".',
      type: 'sys',
      timestamp: '00:00:00',
    },
  ])
  const [history, setHistory] = useState<string[]>([])
  const [historyIndex, setHistoryIndex] = useState(-1)
  const [selectedFeatureId, setSelectedFeatureId] = useState<string | null>(null)
  const [consoleExpanded, setConsoleExpanded] = useState(false)
  const [isExecuting, setIsExecuting] = useState(false)
  const [pendingFiles, setPendingFiles] = useState<PendingFile[]>([])
  const [dragActive, setDragActive] = useState(false)

  const logEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const chatHistoryRef = useRef<{ role: string; content: string }[]>([])
  const dragDepth = useRef(0)

  const isListening = useJarvisStore((s) => s.isListening)
  const toggleListening = useJarvisStore((s) => s.toggleListening)
  const setSystemNotice = useJarvisStore((s) => s.setSystemNotice)

  useEffect(() => {
    const handleSelected = (e: Event) => {
      setSelectedFeatureId((e as CustomEvent).detail?.featureId ?? null)
    }
    window.addEventListener('jarvis-cad-selected', handleSelected)
    return () => window.removeEventListener('jarvis-cad-selected', handleSelected)
  }, [])

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  const appendLog = (logItem: Omit<ConsoleLog, 'id' | 'timestamp'>) => {
    const now = new Date().toLocaleTimeString()
    setLogs((prev) => [
      ...prev.slice(-80),
      {
        id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        timestamp: now,
        ...logItem,
      },
    ])
  }

  // ---- Attachment uploads (upload -> backend validation -> stored path) ----
  const uploadFiles = async (files: File[]) => {
    for (const file of files.slice(0, 5)) {
      if (file.size > MAX_FILE_MB * 1024 * 1024) {
        appendLog({ text: `[Attach] "${file.name}" is larger than ${MAX_FILE_MB} MB — refused before upload.`, type: 'err' })
        continue
      }
      try {
        const b64 = await fileToBase64(file)
        const res = await fetch('/api/upload', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            filename: file.name,
            content_base64: b64,
            mime_type: file.type || 'application/octet-stream',
            category: 'file',
          }),
        })
        const payload = await res.json().catch(() => ({}))
        const result = payload.result || {}
        const okUpload = res.ok && payload.success === true && result.success === true && !!result.path
        if (!okUpload) {
          appendLog({
            text: `[Attach] Upload rejected: ${result.error || payload.error || result.error || `backend HTTP ${res.status}`}`,
            type: 'err',
          })
          continue
        }
        const ref: FileAttachment = {
          filename: result.original_filename || file.name,
          path: result.path,
          url: result.url,
          mime_type: file.type || result.mime_type,
          size: result.size ?? file.size,
          category: result.category,
        }
        setPendingFiles((prev) => [
          ...prev,
          {
            id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
            name: ref.filename,
            size: ref.size || file.size,
            mime_type: ref.mime_type || file.type,
            isImage: isImageLike(ref.filename, ref.mime_type || ''),
            previewUrl: ref.url || (file.type.startsWith('image/') ? URL.createObjectURL(file) : ''),
            ref,
          },
        ])
        appendLog({ text: `[Attach] "${ref.filename}" uploaded and validated (${Math.round((ref.size || 0) / 1024)} KB).`, type: 'sys' })
      } catch (e: any) {
        appendLog({ text: `[Attach] Failed to upload "${file.name}": ${e.message}`, type: 'err' })
      }
    }
  }

  const handlePaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    const files = Array.from(e.clipboardData?.files || [])
    if (files.length > 0) {
      e.preventDefault()
      uploadFiles(files)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    dragDepth.current = 0
    setDragActive(false)
    const files = Array.from(e.dataTransfer?.files || [])
    if (files.length > 0) uploadFiles(files)
  }

  const removePending = (id: string) => setPendingFiles((prev) => prev.filter((p) => p.id !== id))

  // ---- Attachment-aware AI chat (non-CAD language) ----
  const runChatTurn = async (cmd: string, refs: FileAttachment[]) => {
    appendLog({ text: `[JARVIS] ${cmd}`, type: 'cmd', attachments: refs.length ? refs : undefined })
    chatHistoryRef.current.push({ role: 'user', content: cmd })
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages: [...chatHistoryRef.current.slice(-9), { role: 'user', content: cmd }],
        selected_feature_id: selectedFeatureId || undefined,
        attachments: refs,
      }),
    })
    const data = await res.json().catch(() => ({}))
    const reply: string = data.reply || (res.ok ? 'The assistant returned no reply.' : `Backend error HTTP ${res.status}`)
    chatHistoryRef.current.push({ role: 'assistant', content: reply })
    const outputs: FileAttachment[] = Array.isArray(data.outputs) ? data.outputs : []

    if (data.status === 'error') {
      appendLog({ text: `[AI] ${reply}`, type: 'err', outputs: outputs.length ? outputs : undefined })
    } else {
      appendLog({ text: `[AI] ${reply}`, type: 'resp', outputs: outputs.length ? outputs : undefined })
    }

    // Route generated CAD primitives back into the viewport, like voice does.
    const ca = data.cad_action
    if (ca && (ca.action === 'create_primitive' || ca.feature_id)) {
      window.dispatchEvent(
        new CustomEvent('jarvis-cad-refresh', { detail: { featureId: ca.feature_id ?? null } })
      )
    }
    setSystemNotice(reply)
    setTimeout(() => setSystemNotice(null), 4500)
    if (data.reply) speakJarvis(data.reply)
  }

  // Central CAD Command Execution Pipeline
  const handleCommand = async (rawCmd: string) => {
    const cmd = rawCmd.trim()
    const refs = pendingFiles.map((p) => p.ref)
    if ((!cmd && refs.length === 0) || isExecuting) return

    playHudChirp()
    setHistory((prev) => (cmd ? [...prev, cmd] : prev))
    setHistoryIndex(-1)
    setInputVal('')
    setIsExecuting(true)
    const sentFiles = pendingFiles
    setPendingFiles([])

    if (refs.length > 0) {
      // Attachments force the real AI chat pipeline (with CAD detection inside).
      try {
        await runChatTurn(cmd || `Analyze ${refs.length === 1 ? `the attached file "${refs[0].filename}"` : `${refs.length} attached files`}`, refs)
      } catch (err: any) {
        appendLog({ text: `[System Error] Assistant unreachable: ${err.message}`, type: 'err' })
      } finally {
        setIsExecuting(false)
      }
      return
    }

    appendLog({ text: `J.A.R.V.I.S. > ${cmd}`, type: 'cmd' })

    try {
      const res = await fetch('/api/cad/command/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: cmd }),
      })

      const data = await res.json()

      if (!data.success && data.recognized === false) {
        // Not a CAD operation — hand the sentence to the JARVIS chat brain.
        await runChatTurn(cmd, [])
      } else if (res.ok && data.success) {
        // Successful CAD execution
        appendLog({
          text: data.message || `Executed ${data.action}`,
          type: 'resp',
          action: data.action,
          parameters: data.parameters,
          durationMs: data.duration_ms,
        })

        // Refresh viewport & model tree
        window.dispatchEvent(
          new CustomEvent('jarvis-cad-refresh', {
            detail: { featureId: data.feature_id, context: data.context },
          })
        )

        // System notice toast
        setSystemNotice(data.message)

        // Spoken audio feedback if voice is active or available
        if (data.spoken_reply) {
          speakJarvis(data.spoken_reply)
        }
      } else if (data.ambiguous) {
        // Conversational ambiguity detected (e.g. multiple cylinders or boxes)
        appendLog({
          text: data.clarification || 'Multiple matching objects found. Please select which one:',
          type: 'ambiguous',
          candidates: data.candidates || [],
        })
        if (data.spoken_reply) {
          speakJarvis(data.spoken_reply)
        }
      } else {
        // Real CAD error with explanation
        appendLog({
          text: `[CAD Error] ${data.message || data.detail || 'Command failed'}`,
          type: 'err',
          action: data.action,
        })
        if (data.spoken_reply) {
          speakJarvis(data.spoken_reply)
        }
      }
    } catch (err: any) {
      appendLog({
        text: `[System Error] CAD Engine unreachable: ${err.message}`,
        type: 'err',
      })
    } finally {
      setIsExecuting(false)
      void sentFiles
    }
  }

  // Handle Ambiguity Candidate Selection
  const handleSelectCandidate = async (cand: CandidateObject) => {
    playHudChirp()
    appendLog({
      text: `Selected: ${cand.name} (${cand.id.substring(0, 8)})`,
      type: 'cmd',
    })
    try {
      await fetch('/api/cad/context', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ selected_feature_id: cand.id }),
      })
      window.dispatchEvent(
        new CustomEvent('jarvis-cad-refresh', { detail: { featureId: cand.id } })
      )
      setSystemNotice(`Selected ${cand.name}`)
      speakJarvis(`Selected ${cand.name}, sir.`)
    } catch {}
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleCommand(inputVal)
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      if (history.length === 0) return
      const nextIdx = historyIndex === -1 ? history.length - 1 : Math.max(0, historyIndex - 1)
      setHistoryIndex(nextIdx)
      setInputVal(history[nextIdx])
    } else if (e.key === 'ArrowDown') {
      e.preventDefault()
      if (historyIndex === -1) return
      const nextIdx = historyIndex + 1
      if (nextIdx >= history.length) {
        setHistoryIndex(-1)
        setInputVal('')
      } else {
        setHistoryIndex(nextIdx)
        setInputVal(history[nextIdx])
      }
    }
  }

  const renderAttachmentRow = (items: FileAttachment[] | undefined, label: string) =>
    items && items.length > 0 ? (
      <div className="ml-14 mt-0.5 flex flex-wrap items-center gap-2">
        <span className="text-[9px] text-cyan-400/50">{label}:</span>
        {items.map((a, i) =>
          isImageLike(a.filename, a.mime_type || '') && (a.url || a.path) ? (
            <a
              key={`${a.path}-${i}`}
              href={a.url || `/api/files/${a.path.replace(/\\/g, '/')}`}
              target="_blank"
              rel="noreferrer"
              title={`${a.filename} (${Math.round((a.size || 0) / 1024)} KB)`}
            >
              <img
                src={a.url || `/api/files/${a.path.replace(/\\/g, '/')}`}
                alt={a.filename}
                className="h-12 w-auto rounded border border-cyan-500/40 object-cover hover:border-[#00e5ff]"
              />
            </a>
          ) : (
            <a
              key={`${a.path}-${i}`}
              href={a.url || `/api/files/${a.path.replace(/\\/g, '/')}`}
              target="_blank"
              rel="noreferrer"
              className="rounded bg-cyan-950/80 px-1.5 py-0.5 text-[10px] text-cyan-200 border border-cyan-500/30 hover:border-[#00e5ff]"
            >
              {a.filename} ({Math.round((a.size || 0) / 1024)} KB)
            </a>
          )
        )}
      </div>
    ) : null

  return (
    <footer
      className="relative z-30 flex flex-col w-full border-t border-cyan-500/25 bg-[#030612] select-none font-mono"
      onDragEnter={(e) => {
        e.preventDefault()
        if (e.dataTransfer?.types?.includes('Files')) {
          dragDepth.current += 1
          setDragActive(true)
        }
      }}
      onDragOver={(e) => e.preventDefault()}
      onDragLeave={() => {
        dragDepth.current = Math.max(0, dragDepth.current - 1)
        if (dragDepth.current === 0) setDragActive(false)
      }}
      onDrop={handleDrop}
    >
      {/* Drag & drop overlay (same footprint as the console) */}
      {dragActive && (
        <div className="pointer-events-none absolute inset-0 z-40 m-1 flex items-center justify-center rounded border-2 border-dashed border-[#00e5ff]/70 bg-[#030612]/85">
          <span className="text-[12px] font-bold tracking-widest text-[#00e5ff]">
            DROP FILES TO ATTACH — images, video, PDF, documents, code
          </span>
        </div>
      )}

      {/* Console Output Terminal */}
      <div
        className={`w-full overflow-y-auto px-4 py-2 transition-all duration-200 border-b border-cyan-500/15 ${
          consoleExpanded ? 'h-48 bg-[#02050e]' : 'h-20 bg-[#02050e]/95'
        }`}
      >
        <div className="space-y-1 text-[11px] leading-relaxed">
          {logs.map((log) => (
            <div key={log.id} className="flex flex-col gap-0.5">
              <div
                className={`flex items-start gap-2 ${
                  log.type === 'cmd'
                    ? 'text-[#00e5ff] font-bold'
                    : log.type === 'sys'
                    ? 'text-cyan-400/60'
                    : log.type === 'err'
                    ? 'text-rose-400 font-bold'
                    : log.type === 'ambiguous'
                    ? 'text-amber-300 font-bold'
                    : 'text-cyan-100'
                }`}
              >
                <span className="text-[9px] text-cyan-500/40 shrink-0 select-none">
                  [{log.timestamp}]
                </span>
                <span className="whitespace-pre-wrap">{log.text}</span>

                {/* Duration badge */}
                {log.durationMs !== undefined && (
                  <span className="ml-auto text-[9px] text-cyan-400/40 font-normal">
                    {log.durationMs.toFixed(1)}ms
                  </span>
                )}
              </div>

              {/* Attachments sent with this command */}
              {renderAttachmentRow(log.attachments, 'attached')}

              {/* Generated result files (download / preview) */}
              {renderAttachmentRow(log.outputs, 'result')}

              {/* Parsed CAD parameters pill */}
              {log.action && log.parameters && Object.keys(log.parameters).length > 0 && (
                <div className="ml-14 flex flex-wrap items-center gap-1.5 text-[10px] text-cyan-300/80">
                  <span className="rounded bg-cyan-950/80 px-1.5 py-0.5 border border-cyan-500/30 text-[#00e5ff] font-semibold">
                    {log.action}
                  </span>
                  {Object.entries(log.parameters).map(([k, v]) => (
                    <span key={k} className="rounded bg-[#071328] px-1.5 py-0.5 text-cyan-200/90">
                      {k}: <span className="text-white">{String(v)}</span>
                    </span>
                  ))}
                </div>
              )}

              {/* Ambiguity clarification chips */}
              {log.type === 'ambiguous' && log.candidates && log.candidates.length > 0 && (
                <div className="ml-14 mt-1 flex flex-wrap items-center gap-2">
                  <span className="text-[10px] text-amber-400/80">Choose target:</span>
                  {log.candidates.map((cand) => (
                    <button
                      key={cand.id}
                      type="button"
                      onClick={() => handleSelectCandidate(cand)}
                      className="cursor-pointer rounded border border-amber-400/50 bg-[#1f1706] px-2.5 py-0.5 font-mono text-[10px] font-bold text-amber-200 hover:bg-amber-400 hover:text-black transition-all active:scale-95"
                    >
                      {cand.name}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
          <div ref={logEndRef} />
        </div>
      </div>

      {/* Pending attachment preview chips (above the prompt bar) */}
      {pendingFiles.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 border-t border-cyan-500/15 bg-[#040a1a] px-3 py-1.5">
          {pendingFiles.map((p) => (
            <span
              key={p.id}
              className="flex items-center gap-1.5 rounded border border-cyan-500/30 bg-[#071328] px-1.5 py-0.5 text-[10px] text-cyan-200"
            >
              {p.isImage && p.previewUrl ? (
                <img src={p.previewUrl} alt={p.name} className="h-6 w-6 rounded object-cover" />
              ) : (
                <span className="text-[9px] text-cyan-400/70">
                  {(p.mime_type?.split('/')[1] || p.name.split('.').pop() || 'FILE').toUpperCase().slice(0, 4)}
                </span>
              )}
              <span className="max-w-[140px] truncate">{p.name}</span>
              <span className="text-cyan-500/50">{Math.round(p.size / 1024)}KB</span>
              <button
                type="button"
                onClick={() => removePending(p.id)}
                className="text-rose-400/80 hover:text-rose-300 font-bold"
                title="Remove attachment"
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}

      {/* AutoCAD-style Command Prompt Input Bar */}
      <div className="flex h-11 items-center gap-2 px-3 bg-[#040817]">
        {/* Console Expand / Collapse Toggle Button */}
        <button
          type="button"
          onClick={() => setConsoleExpanded(!consoleExpanded)}
          title={consoleExpanded ? 'Collapse Command History' : 'Expand Command History'}
          className="text-cyan-400/60 hover:text-[#00e5ff] text-[10px] px-1 font-bold transition-colors cursor-pointer"
        >
          {consoleExpanded ? '▼' : '▲'}
        </button>

        {/* Attach Files (upload / drag-drop / paste) */}
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          title="Attach image, video, PDF, document or code file"
          className="text-cyan-400/70 hover:text-[#00e5ff] text-[12px] px-1 transition-colors cursor-pointer"
        >
          📎
        </button>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept="image/*,video/*,.pdf,.docx,.txt,.md,.csv,.json,.xml,.yaml,.yml,.py,.js,.ts,.tsx,.jsx,.html,.css,.c,.cpp,.h,.java,.go,.rs,.sh,.zip"
          className="hidden"
          onChange={(e) => {
            const files = Array.from(e.target.files || [])
            if (files.length) uploadFiles(files)
            e.target.value = ''
          }}
        />

        {/* Prompt Tag */}
        <div className="flex items-center gap-1.5 shrink-0 text-[#00e5ff] font-bold text-[12px] tracking-wider select-none">
          <span>J.A.R.V.I.S.</span>
          {selectedFeatureId && (
            <span className="text-[10px] text-cyan-300/70 font-normal">
              [{selectedFeatureId.substring(0, 8)}]
            </span>
          )}
          <span className="text-cyan-400/70">&gt;</span>
        </div>

        {/* Real Command Input Box */}
        <input
          ref={inputRef}
          type="text"
          value={inputVal}
          disabled={isExecuting}
          onChange={(e) => setInputVal(e.target.value)}
          onPaste={handlePaste}
          onKeyDown={handleKeyDown}
          placeholder='Type a command ("Rotate 45 deg", "analyze this image", "summarize this file")… drag-drop or Ctrl+V to attach'
          className="flex-1 bg-transparent font-mono text-[12px] text-white placeholder-cyan-400/35 focus:outline-none disabled:opacity-50"
        />

        {/* Quick CAD Action Badges */}
        <div className="hidden lg:flex items-center gap-1">
          <button
            type="button"
            onClick={() => handleCommand('undo')}
            className="rounded border border-cyan-500/30 bg-[#071328] px-2 py-0.5 text-[10px] text-cyan-300 hover:border-cyan-400 transition-colors"
          >
            UNDO
          </button>
          <button
            type="button"
            onClick={() => handleCommand('redo')}
            className="rounded border border-cyan-500/30 bg-[#071328] px-2 py-0.5 text-[10px] text-cyan-300 hover:border-cyan-400 transition-colors"
          >
            REDO
          </button>
          <button
            type="button"
            onClick={() => handleCommand('fit view')}
            className="rounded border border-cyan-500/30 bg-[#071328] px-2 py-0.5 text-[10px] text-cyan-300 hover:border-cyan-400 transition-colors"
          >
            FIT
          </button>
        </div>

        {/* Voice Trigger Microphone Button */}
        <button
          type="button"
          onClick={toggleListening}
          title={isListening ? 'Listening for Voice CAD Commands...' : 'Speak CAD Command'}
          className={`flex items-center gap-1.5 rounded border px-2.5 py-1 text-[10px] font-bold transition-all cursor-pointer ${
            isListening
              ? 'border-[#00e5ff] bg-[#00e5ff]/20 text-[#00e5ff] animate-pulse'
              : 'border-cyan-500/30 bg-[#071328] text-cyan-300 hover:border-cyan-400'
          }`}
        >
          <span
            className={`h-2 w-2 rounded-full ${isListening ? 'bg-[#00e5ff]' : 'bg-cyan-500/50'}`}
          />
          <span>{isListening ? 'LISTENING' : 'VOICE'}</span>
        </button>

        {/* Execute Button */}
        <button
          type="button"
          onClick={() => handleCommand(inputVal)}
          disabled={isExecuting || (!inputVal.trim() && pendingFiles.length === 0)}
          className="cursor-pointer rounded border border-[#00e5ff] bg-[#00e5ff] px-3.5 py-1 font-mono text-[11px] font-extrabold text-black transition-all hover:bg-cyan-300 active:scale-95 disabled:cursor-not-allowed disabled:opacity-35"
        >
          {isExecuting ? 'EXEC…' : 'RUN'}
        </button>
      </div>
    </footer>
  )
}
