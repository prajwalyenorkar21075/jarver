import { useEffect, useRef, useCallback, useState } from 'react'
import { useConversationStore } from '../store/useConversationStore'
import { playHudChirp, speakJarvis } from '../store/useJarvisStore'

interface Attachment {
  name: string
  path: string
  mime_type: string
  size: number
  preview?: string
}

export default function StreamingChatPanel() {
  const messages = useConversationStore((s) => s.messages)
  const isStreaming = useConversationStore((s) => s.isStreaming)
  const streamingMessageId = useConversationStore((s) => s.streamingMessageId)
  const addMessage = useConversationStore((s) => s.addMessage)
  const appendDelta = useConversationStore((s) => s.appendDelta)
  const startStreaming = useConversationStore((s) => s.startStreaming)
  const endStreaming = useConversationStore((s) => s.endStreaming)
  const setAbortController = useConversationStore((s) => s.setAbortController)

  const [inputValue, setInputValue] = useState('')
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [dragActive, setDragActive] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, isStreaming, scrollToBottom])

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files.length > 0) {
      await uploadFiles(Array.from(e.dataTransfer.files))
    }
  }

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      await uploadFiles(Array.from(e.target.files))
      e.target.value = ''
    }
  }

  const uploadFiles = async (files: File[]) => {
    for (const file of files) {
      try {
        const base64 = await fileToBase64(file)
        const response = await fetch('/api/upload', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            filename: file.name,
            content_base64: base64,
            mime_type: file.type,
            category: file.type.startsWith('image/') ? 'image' : 'code',
          }),
        })
        const data = await response.json()
        if (data.success) {
          const attachment: Attachment = {
            name: data.original_filename || file.name,
            path: data.path,
            mime_type: file.type,
            size: file.size,
            preview: file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined,
          }
          setAttachments((prev) => [...prev, attachment])
        }
      } catch (err) {
        console.error('Upload failed:', err)
      }
    }
  }

  const fileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => {
        const result = reader.result as string
        resolve(result.split(',')[1])
      }
      reader.onerror = reject
      reader.readAsDataURL(file)
    })
  }

  const removeAttachment = (index: number) => {
    setAttachments((prev) => prev.filter((_, i) => i !== index))
  }

  const sendMessage = async () => {
    const text = inputValue.trim()
    if (!text && attachments.length === 0) return

    playHudChirp()
    setInputValue('')

    // Add user message
    const messageId = addMessage('user', text, attachments.length > 0 ? [...attachments] : undefined)
    setAttachments([])

    // Start streaming
    const controller = new AbortController()
    setAbortController(controller)
    startStreaming(messageId)

    // Add empty assistant message
    const assistantId = addMessage('jarvis', '')

    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: controller.signal,
        body: JSON.stringify({
          messages: [
            ...messages.slice(-10).map((m) => ({ role: m.sender === 'user' ? 'user' : 'assistant', content: m.text })),
            { role: 'user', content: text },
          ],
          stream: true,
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const reader = response.body?.getReader()
      if (!reader) throw new Error('No response body')

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6)
            if (dataStr === '[DONE]' || dataStr.trim() === '') continue
            try {
              const data = JSON.parse(dataStr)
              if (data.delta) {
                appendDelta(assistantId, data.delta)
              }
              if (data.done) {
                endStreaming()
                speakJarvis(messages.find((m) => m.id === assistantId)?.text || '')
                break
              }
              if (data.requires_confirmation) {
                // Handle safety confirmation
                endStreaming()
                break
              }
            } catch {
              // Ignore parse errors
            }
          }
        }
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        console.error('Streaming error:', err)
        appendDelta(assistantId, '\n\n[Connection error. Please try again.]')
      }
      endStreaming()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes}B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)}MB`
  }

  const getFileIcon = (mimeType: string) => {
    if (mimeType.startsWith('image/')) return '🖼️'
    if (mimeType.startsWith('video/')) return '🎬'
    if (mimeType.startsWith('audio/')) return '🎵'
    if (mimeType.includes('pdf')) return '📄'
    if (mimeType.includes('text') || mimeType.includes('json') || mimeType.includes('javascript') || mimeType.includes('typescript')) return '📝'
    return '📎'
  }

  return (
    <div className="flex flex-col h-full bg-[#030612] border-r border-cyan-500/20">
      {/* Header */}
      <div className="flex h-12 shrink-0 items-center justify-between border-b border-cyan-500/30 bg-[#040a18] px-4 font-mono text-xs">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-[#00e5ff] animate-pulse" />
          <span className="font-bold text-[#00e5ff] tracking-wider">CONVERSATION</span>
          {isStreaming && (
            <span className="rounded bg-cyan-500/20 border border-cyan-400/40 px-2 py-0.5 text-[10px] font-bold text-[#00e5ff] animate-pulse">
              STREAMING
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-white/40 text-[10px]">{messages.length} messages</span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex flex-col gap-1.5 ${
              msg.sender === 'user' ? 'items-end' : 'items-start'
            }`}
          >
            {/* Sender Badge */}
            <div className="flex items-center gap-2 text-[10px] text-white/50 w-full">
              {msg.sender === 'user' ? (
                <>
                  <span className="flex-1 text-right" />
                  <span className="font-bold text-cyan-400">TONY STARK</span>
                  <span>{msg.timestamp}</span>
                </>
              ) : (
                <>
                  <span className="font-bold text-amber-400">J.A.R.V.I.S.</span>
                  <span>{msg.timestamp}</span>
                  <span className="flex-1" />
                </>
              )}
            </div>

            {/* Message Bubble */}
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-3 leading-relaxed whitespace-pre-wrap ${
                msg.sender === 'user'
                  ? 'border border-cyan-500/50 bg-[#071a38] text-white shadow-[0_0_15px_rgba(0,229,255,0.1)]'
                  : 'border border-amber-500/30 bg-[#091224] text-cyan-100 shadow-[0_0_15px_rgba(255,160,0,0.08)]'
              }`}
            >
              {msg.text}

              {/* Attachments */}
              {msg.attachments && msg.attachments.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {msg.attachments.map((att, idx) => (
                    <div
                      key={idx}
                      className="flex items-center gap-1.5 rounded-lg border border-cyan-500/30 bg-[#040c1d] p-1.5 text-[11px]"
                    >
                      <span>{getFileIcon(att.mime_type)}</span>
                      <span className="text-cyan-300 truncate max-w-[200px]">{att.name}</span>
                      <span className="text-white/40">{formatSize(att.size)}</span>
                      {att.preview && (
                        <img
                          src={att.preview}
                          alt={att.name}
                          className="h-16 w-auto rounded object-cover"
                        />
                      )}
                    </div>
                  ))}
                </div>
              )}

              {msg.isStreaming && (
                <span className="inline-block h-1.5 w-1.5 rounded-full bg-cyan-400 animate-pulse ml-1" />
              )}
            </div>
          </div>
        ))}

        {isStreaming && !streamingMessageId && (
          <div className="flex items-center gap-2 text-amber-300 text-xs animate-pulse p-3 rounded-xl border border-amber-500/30 bg-amber-500/10">
            <span className="h-2 w-2 rounded-full bg-amber-400 animate-ping" />
            <span>J.A.R.V.I.S. is reasoning...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Attachments Preview */}
      {attachments.length > 0 && (
        <div className="flex flex-wrap gap-2 p-3 border-t border-cyan-500/20 bg-[#040a18]">
          {attachments.map((att, idx) => (
            <div
              key={idx}
              className="flex items-center gap-2 rounded-lg border border-cyan-500/30 bg-[#06122c] px-2 py-1.5 text-xs"
            >
              <span>{getFileIcon(att.mime_type)}</span>
              <span className="text-cyan-300 truncate max-w-[150px]">{att.name}</span>
              <span className="text-white/40">{formatSize(att.size)}</span>
              <button
                type="button"
                onClick={() => removeAttachment(idx)}
                className="text-white/50 hover:text-red-400 transition-colors"
              >
                ✕
              </button>
              {att.preview && (
                <img src={att.preview} alt={att.name} className="h-12 w-auto rounded object-cover" />
              )}
            </div>
          ))}
        </div>
      )}

      {/* Input Area */}
      <div className="shrink-0 p-3 border-t border-cyan-500/20 bg-[#040a18]">
        <div
          className={`relative rounded-2xl border transition-all ${
            dragActive ? 'border-[#00e5ff] bg-cyan-500/5' : 'border-cyan-500/30 bg-[#06122a]'
          }`}
          onDragEnter={handleDragEnter}
          onDragLeave={handleDragLeave}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
        >
          <div className="flex items-end gap-2 p-2">
            {/* Drag indicator */}
            {dragActive && (
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none rounded-2xl bg-cyan-500/10 border-2 border-dashed border-[#00e5ff]">
                <span className="text-[#00e5ff] font-mono text-sm font-bold">Drop files here to attach</span>
              </div>
            )}

            {/* File input */}
            <input
              type="file"
              ref={fileInputRef}
              multiple
              onChange={handleFileSelect}
              className="hidden"
              id="file-upload"
            />

            {/* Attach button */}
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="flex-shrink-0 cursor-pointer p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/20 transition-colors"
              title="Attach file"
            >
              <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
            </button>

            {/* Textarea */}
            <textarea
              ref={textareaRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Message JARVIS... (Enter to send, Shift+Enter for new line)"
              rows={1}
              className="flex-1 bg-transparent border-none focus:outline-none resize-none font-mono text-xs text-white placeholder-white/40 min-h-[40px] max-h-[120px]"
            />

            {/* Send button */}
            <button
              type="button"
              onClick={sendMessage}
              disabled={(!inputValue.trim() && attachments.length === 0) || isStreaming}
              className="flex-shrink-0 cursor-pointer p-2 rounded-xl bg-[#00e5ff] text-black font-extrabold hover:bg-cyan-300 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
              title="Send"
            >
              <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <line x1="5" y1="12" x2="19" y2="12" />
                <polyline points="12 5 19 12 12 19" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}