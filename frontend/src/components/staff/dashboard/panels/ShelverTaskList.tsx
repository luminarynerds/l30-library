/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { Circle, CircleDot, CheckCircle2 } from 'lucide-react'
import { ShelverTask } from '@/api/staff-api/shelver-dashboard'

type TaskStatus = 'pending' | 'in_progress' | 'done'

interface Props {
  tasks: ShelverTask[]
}

export default function ShelverTaskList({ tasks }: Props) {
  const [statuses, setStatuses] = useState<Record<string, TaskStatus>>(() => {
    const init: Record<string, TaskStatus> = {}
    tasks.forEach(t => { init[t.id] = 'pending' })
    return init
  })

  const advance = (id: string) => {
    setStatuses(prev => {
      const cur = prev[id] ?? 'pending'
      const next: TaskStatus = cur === 'pending' ? 'in_progress' : cur === 'in_progress' ? 'done' : 'done'
      return { ...prev, [id]: next }
    })
  }

  const statusIcon = (s: TaskStatus) => {
    switch (s) {
      case 'done':
        return <CheckCircle2 className="w-5 h-5 text-status-success-500 flex-shrink-0" aria-hidden="true" />
      case 'in_progress':
        return <CircleDot className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0" aria-hidden="true" />
      default:
        return <Circle className="w-5 h-5 text-lsc-dark/30 dark:text-lsc-cream/30 flex-shrink-0" aria-hidden="true" />
    }
  }

  const buttonLabel = (s: TaskStatus) => {
    switch (s) {
      case 'pending': return 'Start'
      case 'in_progress': return 'Mark done'
      default: return null
    }
  }

  if (tasks.length === 0) {
    return (
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 shadow-sm">
        <p className="text-sm text-lsc-dark/50 dark:text-lsc-cream/50">No tasks right now.</p>
      </div>
    )
  }

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm divide-y divide-lsc-border dark:divide-earth-700">
      {tasks.map(task => {
        const status = statuses[task.id] ?? 'pending'
        const label = buttonLabel(status)
        return (
          <div
            key={task.id}
            className={`flex items-center gap-3 px-5 py-4 ${status === 'done' ? 'opacity-50' : ''}`}
          >
            {statusIcon(status)}
            <div className="flex-1 min-w-0">
              <p className={`text-sm font-medium ${
                status === 'done'
                  ? 'text-lsc-dark/40 dark:text-lsc-cream/40 line-through'
                  : 'text-lsc-dark dark:text-lsc-cream'
              }`}>
                {task.label}
                {task.count != null && (
                  <span className="ml-1.5 text-lsc-dark/50 dark:text-lsc-cream/50 font-normal">
                    ({task.count} items)
                  </span>
                )}
              </p>
              {task.detail && (
                <p className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50 mt-0.5">{task.detail}</p>
              )}
            </div>
            {label && (
              <button
                onClick={() => advance(task.id)}
                className="text-xs font-medium px-3 py-1.5 rounded-lg bg-lsc-cream dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream/80 dark:hover:bg-earth-600 transition-colors"
              >
                {label}
              </button>
            )}
          </div>
        )
      })}
    </div>
  )
}
