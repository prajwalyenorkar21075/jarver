import { useState } from 'react'
import { useJarvisStore } from '../../store/useJarvisStore'

export default function ScheduleWidget() {
  const tasks = useJarvisStore((s) => s.tasks)
  const createTask = useJarvisStore((s) => s.createTask)
  const toggleTaskStatus = useJarvisStore((s) => s.toggleTaskStatus)
  const deleteTask = useJarvisStore((s) => s.deleteTask)
  const createBackupSnapshot = useJarvisStore((s) => s.createBackupSnapshot)
  const backupsAvailable = useJarvisStore((s) => s.backupsAvailable)

  const [isAdding, setIsAdding] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [priority, setPriority] = useState('medium')

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newTitle.trim()) return
    await createTask(newTitle.trim(), priority)
    setNewTitle('')
    setIsAdding(false)
  }

  const getPriorityColor = (p: string) => {
    switch (p) {
      case 'high':
        return 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.6)]'
      case 'low':
        return 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]'
      default:
        return 'bg-[#00e5ff] shadow-[0_0_8px_rgba(0,229,255,0.6)]'
    }
  }

  return (
    <div className="relative rounded-2xl border border-cyan-500/40 bg-[#040a18]/95 p-4 transition-all hover:border-[#00e5ff]/70 shadow-[0_0_15px_rgba(0,229,255,0.06)] w-full max-w-[320px]">
      {/* Header */}
      <div className="flex items-center justify-between text-xs font-mono">
        <div className="flex items-center gap-2 text-white/95">
          <svg className="h-4 w-4 text-[#00e5ff]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
            <line x1="16" y1="2" x2="16" y2="6" />
            <line x1="8" y1="2" x2="8" y2="6" />
            <line x1="3" y1="10" x2="21" y2="10" />
          </svg>
          <span className="font-semibold tracking-wider text-[#00e5ff]">PERSISTENT TASKS</span>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => setIsAdding(!isAdding)}
            className="cursor-pointer rounded-md border border-cyan-500/40 bg-[#071530] px-2 py-0.5 text-[11px] text-[#00e5ff] hover:bg-[#00e5ff] hover:text-black transition-all"
            title="Add a new task"
          >
            {isAdding ? 'Cancel' : '+ Add'}
          </button>
        </div>
      </div>

      {/* Task Creation Form Inline */}
      {isAdding && (
        <form onSubmit={handleCreate} className="mt-3 flex flex-col gap-2 font-mono text-xs">
          <input
            type="text"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            placeholder="Task description..."
            className="w-full rounded border border-cyan-500/50 bg-[#071530] px-2.5 py-1 text-white placeholder-cyan-400/40 focus:border-[#00e5ff] focus:outline-none"
            autoFocus
          />
          <div className="flex items-center justify-between">
            <select
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              className="rounded border border-cyan-500/30 bg-[#071530] px-2 py-0.5 text-[10px] text-cyan-300 focus:outline-none"
            >
              <option value="low">Low Priority</option>
              <option value="medium">Medium</option>
              <option value="high">High Priority</option>
            </select>
            <button
              type="submit"
              className="rounded bg-[#00e5ff] px-2.5 py-0.5 text-[11px] font-bold text-black hover:bg-cyan-300"
            >
              Save
            </button>
          </div>
        </form>
      )}

      {/* Task List */}
      <div className="mt-3 space-y-1.5 font-mono max-h-[160px] overflow-y-auto pr-1">
        {tasks.length === 0 ? (
          <div className="py-3 text-center text-[11px] text-cyan-400/40">
            No active tasks. Say "Add task..." to Jarvis or click + Add.
          </div>
        ) : (
          tasks.map((t) => {
            const isDone = t.status === 'completed'
            return (
              <div
                key={t.id}
                className={`group flex items-center justify-between rounded-xl border p-2 transition-all ${
                  isDone
                    ? 'border-cyan-500/10 bg-[#071530]/40 opacity-60'
                    : 'border-cyan-500/20 bg-[#071530] hover:border-[#00e5ff]/50'
                }`}
              >
                <div
                  className="flex flex-1 items-center gap-2 cursor-pointer min-w-0"
                  onClick={() => toggleTaskStatus(t.id, t.status)}
                >
                  <span className={`h-2 w-2 rounded-full shrink-0 ${getPriorityColor(t.priority)}`} />
                  <span
                    className={`text-xs truncate ${
                      isDone ? 'line-through text-cyan-300/40' : 'text-white/95 font-medium'
                    }`}
                  >
                    {t.title}
                  </span>
                </div>

                <div className="flex items-center gap-1.5 shrink-0 pl-1">
                  <button
                    type="button"
                    onClick={() => toggleTaskStatus(t.id, t.status)}
                    className="text-[10px] text-cyan-400 hover:text-white"
                    title={isDone ? 'Mark Pending' : 'Mark Complete'}
                  >
                    {isDone ? '↩' : '✓'}
                  </button>
                  <button
                    type="button"
                    onClick={() => deleteTask(t.id)}
                    className="text-[10px] text-red-400/60 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
                    title="Delete Task"
                  >
                    ✕
                  </button>
                </div>
              </div>
            )
          })
        )}
      </div>

      {/* Persistence & Backup Footer */}
      <div className="mt-3 pt-2 border-t border-cyan-500/20 flex items-center justify-between text-[10px] font-mono text-cyan-400/60">
        <span className="flex items-center gap-1">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <span>DB: SQLite WAL ({backupsAvailable} Snapshots)</span>
        </span>
        <button
          type="button"
          onClick={() => createBackupSnapshot()}
          className="cursor-pointer text-[10px] font-bold text-[#00e5ff] hover:underline"
          title="Create an instant atomic persistent backup"
        >
          [💾 SNAPSHOT]
        </button>
      </div>
    </div>
  )
}

