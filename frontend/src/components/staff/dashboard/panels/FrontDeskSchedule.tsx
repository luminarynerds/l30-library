/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { useTone } from '@/contexts/ToneContext'
import { getTodaySchedule, ScheduleItem } from '@/api/staff-api/desk-state'

function formatRelativeTime(timeStr: string, tone: 'calm' | 'standard' | 'full'): string | null {
  if (tone === 'calm') return null

  // Parse time like "11:00 AM - 12:00 PM" or "4:00 PM - 5:00 PM"
  const match = timeStr.match(/(\d{1,2}):(\d{2})\s*(AM|PM)/i)
  if (!match || !match[1] || !match[2] || !match[3]) return null

  const now = new Date()
  const hours = parseInt(match[1]) + (match[3].toUpperCase() === 'PM' && match[1] !== '12' ? 12 : 0)
  const minutes = parseInt(match[2])
  const eventTime = new Date(now)
  eventTime.setHours(hours, minutes, 0, 0)

  const diffMin = Math.round((eventTime.getTime() - now.getTime()) / 60000)

  if (diffMin < -30) return null // already well past
  if (diffMin < 0) return tone === 'full' ? 'NOW' : 'happening now'
  if (diffMin < 60) return tone === 'full' ? `IN ${diffMin} MIN` : `in ${diffMin} min`
  if (diffMin < 120) return tone === 'full' ? 'IN 1 HR' : 'in 1 hr'
  return tone === 'full' ? 'LATER' : 'later'
}

export default function FrontDeskSchedule() {
  const { token } = useAuth()
  const { tone, showUrgencyColors } = useTone()
  const [items, setItems] = useState<ScheduleItem[]>([])

  useEffect(() => {
    if (!token) return
    getTodaySchedule(token).then(r => setItems(r.items)).catch(() => {})
  }, [token])

  if (items.length === 0) return null

  return (
    <div>
      <p className="text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/60 mb-2">Today on the desk</p>
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm divide-y divide-lsc-border dark:divide-earth-700">
        {items.map(item => {
          const relative = formatRelativeTime(item.time, tone)
          const isSoon = relative && (relative.includes('min') || relative.includes('MIN') || relative.includes('NOW') || relative.includes('now'))
          return (
            <div key={item.id} className="flex items-center gap-3 px-4 py-3">
              <span className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50 min-w-[120px]">{item.time}</span>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">{item.title}</p>
                {(item.location || item.desk_note) && (
                  <p className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50">
                    {[item.location, item.desk_note].filter(Boolean).join(' -- ')}
                  </p>
                )}
              </div>
              {relative && (
                <span className={`text-[11px] font-medium whitespace-nowrap ${
                  showUrgencyColors && isSoon
                    ? 'text-status-warning-600 dark:text-status-warning-400'
                    : 'text-lsc-dark/40 dark:text-lsc-cream/40'
                }`}>{relative}</span>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
