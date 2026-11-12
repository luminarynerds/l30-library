/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { getPresidentNextMeeting, NextMeeting } from '@/api/staff-api/board-dashboard'
import { Circle, CheckCircle2 } from 'lucide-react'

export default function PresidentNextMeetingPanel() {
  const { token } = useAuth()
  const [meeting, setMeeting] = useState<NextMeeting | null>(null)

  useEffect(() => {
    if (!token) return
    getPresidentNextMeeting(token).then(setMeeting).catch(() => {})
  }, [token])

  if (!meeting || !meeting.date) return null

  return (
    <div>
      <p className="text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/60 mb-2">Your next meeting</p>
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-5">
        <div className="flex items-baseline justify-between mb-3">
          <div>
            <p className="text-base font-medium text-lsc-dark dark:text-lsc-cream">{meeting.date} at {meeting.time}</p>
            <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60">
              {meeting.location}{meeting.is_chairing ? " -- You're chairing" : ''}
            </p>
          </div>
          {meeting.relative_time && (
            <span className="text-xs text-lsc-dark/40 dark:text-lsc-cream/40">{meeting.relative_time}</span>
          )}
        </div>
        {meeting.checklist.length > 0 && (
          <div className="bg-lsc-cream/50 dark:bg-lsc-brown/20 rounded-xl p-3 mb-4">
            <p className="text-xs font-medium text-lsc-dark dark:text-lsc-cream mb-2">Before the meeting</p>
            <div className="space-y-1.5">
              {meeting.checklist.map(item => (
                <div key={item.label} className="flex items-center gap-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                  {item.done
                    ? <CheckCircle2 className="w-3.5 h-3.5 text-status-success-500" aria-hidden="true" />
                    : <Circle className="w-3.5 h-3.5 text-lsc-dark/30 dark:text-lsc-cream/30" aria-hidden="true" />
                  }
                  <span className={item.done ? 'line-through text-lsc-dark/40 dark:text-lsc-cream/40' : ''}>{item.label}</span>
                </div>
              ))}
            </div>
          </div>
        )}
        <Link to="/board/meetings" className="px-3 py-1.5 text-xs font-medium rounded-xl bg-lsc-cream dark:bg-lsc-brown/30 text-lsc-dark dark:text-lsc-cream hover:ring-2 hover:ring-lsc-rose/50 transition-all inline-block">
          Open meeting packet
        </Link>
      </div>
    </div>
  )
}
