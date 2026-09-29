import { useState } from 'react'

interface ScheduleItem {
  id: string
  title: string
  time: string
  dotColor: string
}

export default function ScheduleWidget() {
  const [items, setItems] = useState<ScheduleItem[]>([
    { id: '1', title: 'UI Design Review', time: '10:00 AM – 11:00 AM', dotColor: 'bg-cyan-400' },
    { id: '2', title: 'Study – Distributed Systems', time: '02:00 PM – 03:30 PM', dotColor: 'bg-[#3b82f6]' },
    { id: '3', title: 'Workout', time: '06:00 PM – 07:00 PM', dotColor: 'bg-[#00e5ff]' },
  ])

  const handleAdd = () => {
    const title = prompt('Enter task title:')
    if (!title) return
    const time = prompt('Enter time (e.g. 08:00 PM – 09:00 PM):') || '08:00 PM – 09:00 PM'
    setItems((prev) => [
      ...prev,
      { id: Math.random().toString(), title, time, dotColor: 'bg-[#00e5ff]' },
    ])
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
          <span className="font-semibold tracking-wider text-[#00e5ff]">SCHEDULE</span>
        </div>

        <button
          type="button"
          onClick={handleAdd}
          className="cursor-pointer rounded-md border border-cyan-500/40 bg-[#071530] px-2.5 py-0.5 text-[11px] text-[#00e5ff] hover:bg-[#00e5ff] hover:text-black transition-all"
        >
          + Add
        </button>
      </div>

      {/* Task List */}
      <div className="mt-3.5 space-y-2 font-mono">
        {items.map((it) => (
          <div key={it.id} className="flex items-start gap-2.5 rounded-xl bg-[#071530] border border-cyan-500/20 p-2 hover:border-[#00e5ff]/50 transition-colors">
            <span className={`mt-1.5 h-2 w-2 rounded-full shrink-0 ${it.dotColor}`} />
            <div>
              <div className="text-xs font-semibold text-white/95 leading-tight">{it.title}</div>
              <div className="text-[10px] text-cyan-300/50 mt-0.5">{it.time}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
