import { create } from 'zustand'
import { devtools } from 'zustand/middleware'

export interface ConversationMessage {
  id: string
  sender: 'user' | 'jarvis'
  text: string
  timestamp: string
  isStreaming?: boolean
  attachments?: Array<{
    name: string
    path: string
    mime_type: string
    size: number
    preview?: string
  }>
}

interface ConversationStore {
  messages: ConversationMessage[]
  streamingMessageId: string | null
  isStreaming: boolean
  abortController: AbortController | null

  addMessage: (sender: 'user' | 'jarvis', text: string, attachments?: ConversationMessage['attachments']) => string
  appendDelta: (messageId: string, delta: string) => void
  startStreaming: (messageId: string) => void
  endStreaming: () => void
  setAbortController: (controller: AbortController | null) => void
  clearMessages: () => void
  removeMessage: (id: string) => void
}

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
}

function getTimestamp(): string {
  return new Date().toLocaleTimeString([], { hour12: false })
}

export const useConversationStore = create<ConversationStore>()(
  devtools(
    (set) => ({
      messages: [
        {
          id: 'init-1',
          sender: 'jarvis',
          text: 'Good day, sir. Systems are online and monitoring. Standing by for instructions.',
          timestamp: getTimestamp(),
        },
      ],
      streamingMessageId: null,
      isStreaming: false,
      abortController: null,

      addMessage: (sender, text, attachments) => {
        const id = generateId()
        const message: ConversationMessage = {
          id,
          sender,
          text,
          timestamp: getTimestamp(),
          attachments,
        }
        set((state) => ({
          messages: [...state.messages.slice(-199), message],
        }))
        return id
      },

      appendDelta: (messageId, delta) => {
        set((state) => ({
          messages: state.messages.map((msg) =>
            msg.id === messageId ? { ...msg, text: msg.text + delta } : msg
          ),
        }))
      },

      startStreaming: (messageId) => {
        set({ streamingMessageId: messageId, isStreaming: true })
      },

      endStreaming: () => {
        set({ streamingMessageId: null, isStreaming: false })
      },

      setAbortController: (controller) => {
        set({ abortController: controller })
      },

      clearMessages: () => {
        set({ messages: [] })
      },

      removeMessage: (id) => {
        set((state) => ({
          messages: state.messages.filter((m) => m.id !== id),
        }))
      },
    }),
    { name: 'conversation-store' }
  )
)