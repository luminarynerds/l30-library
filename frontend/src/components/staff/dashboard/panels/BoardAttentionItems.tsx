/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { useTone } from '@/contexts/ToneContext'
import { getBoardAttention, AttentionItem } from '@/api/staff-api/board-dashboard'
import { ChevronRight } from 'lucide-react'

const URGENCY_STYLES = {
  overdue: { border: 'border-l-red-500', badge: 'text-status-danger-600 dark:text-status-danger-400' },
  upcoming: { border: 'border-l-status-warning-500', badge: 'text-status-warning-600 dark:text-status-warning-400' },
  routine: { border: 'border-l-lsc-border dark:border-l-earth-600', badge: 'text-lsc-dark/50 dark:text-lsc-cream/50' },
}

export default function BoardAttentionItems() {
  const { token } = useAuth()
  const { showUrgencyColors, formatDeadline } = useTone()
  const [items, setItems] = useState<AttentionItem[]>([])

  useEffect(() => {
    if (!token) return
    getBoardAttention(token).then(r => setItems(r.items)).catch(() => {})
  }, [token])

  if (items.length === 0) return null

  return (
    <div>
      <p className="text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/60 mb-2">Needs your attention</p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {items.map(item => {
          const styles = showUrgencyColors ? URGENCY_STYLES[item.urgency] : URGENCY_STYLES.routine
          return (
            <div key={item.id} className={`bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-4 border-l-[3px] ${styles.border}`}>
              {item.deadline && (
                <p className={`text-[11px] font-medium mb-1 ${styles.badge}`}>
                  {formatDeadline(item.deadline)}
                </p>
              )}
              <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">{item.title}</p>
              <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 mb-3">{item.description}</p>
              <Link to={item.action_url} className="inline-flex items-center gap-1 text-xs font-medium text-lsc-rose dark:text-lsc-rose-light hover:underline">
                {item.action_label} <ChevronRight className="w-3 h-3" aria-hidden="true" />
              </Link>
            </div>
          )
        })}
      </div>
    </div>
  )
}
