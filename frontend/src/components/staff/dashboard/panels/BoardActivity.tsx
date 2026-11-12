/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { useTone } from '@/contexts/ToneContext'
import { getBoardActivity, BoardActivityItem } from '@/api/staff-api/board-dashboard'

export default function BoardActivity() {
  const { token } = useAuth()
  const { tone } = useTone()
  const [items, setItems] = useState<BoardActivityItem[]>([])
  const [visible, setVisible] = useState(tone !== 'calm')

  useEffect(() => {
    if (!token) return
    getBoardActivity(token).then(r => setItems(r.items)).catch(() => {})
  }, [token])

  useEffect(() => { setVisible(tone !== 'calm') }, [tone])

  if (items.length === 0 && !visible) return null

  if (!visible) {
    return (
      <div className="text-center py-2">
        <button onClick={() => setVisible(true)} className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50 underline hover:text-lsc-dark dark:hover:text-lsc-cream">
          Show recent activity
        </button>
      </div>
    )
  }

  if (items.length === 0) return null

  return (
    <div>
      <p className="text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/60 mb-2">Recent activity</p>
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm divide-y divide-lsc-border dark:divide-earth-700">
        {items.map(item => (
          <div key={item.id} className="flex items-center gap-3 px-4 py-2.5">
            <span className="flex-1 text-xs text-lsc-dark dark:text-lsc-cream">{item.description}</span>
            <span className="text-[11px] text-lsc-dark/40 dark:text-lsc-cream/40">{item.timestamp}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
