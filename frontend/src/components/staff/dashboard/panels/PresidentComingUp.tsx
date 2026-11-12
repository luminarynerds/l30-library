/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { getPresidentUpcoming, UpcomingItem } from '@/api/staff-api/board-dashboard'

export default function PresidentComingUp() {
  const { token } = useAuth()
  const [items, setItems] = useState<UpcomingItem[]>([])

  useEffect(() => {
    if (!token) return
    getPresidentUpcoming(token).then(r => setItems(r.items)).catch(() => {})
  }, [token])

  if (items.length === 0) return null

  return (
    <div>
      <p className="text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/60 mb-2">Coming up</p>
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm divide-y divide-lsc-border dark:divide-earth-700">
        {items.map((item, i) => (
          <div key={i} className="flex items-center gap-3 px-4 py-3">
            <span className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50 min-w-[64px]">{item.date}</span>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">{item.title}</p>
              <p className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50">{item.note}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
