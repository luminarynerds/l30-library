/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from 'react-router-dom'
import { Plus, Gavel, BarChart3, CalendarPlus, UserPlus } from 'lucide-react'

const ACTIONS = [
  { label: 'New agenda', icon: <Plus className="w-4 h-4" aria-hidden="true" />, to: '/board/meetings/new' },
  { label: 'Record motion', icon: <Gavel className="w-4 h-4" aria-hidden="true" />, to: '/board/motions/new' },
  { label: 'Generate report', icon: <BarChart3 className="w-4 h-4" aria-hidden="true" />, to: '/board/reports' },
  { label: 'Schedule meeting', icon: <CalendarPlus className="w-4 h-4" aria-hidden="true" />, to: '/board/meetings/new' },
  { label: 'Manage members', icon: <UserPlus className="w-4 h-4" aria-hidden="true" />, to: '/board/members' },
]

export default function BoardQuickActions() {
  return (
    <div>
      <p className="text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/60 mb-2">Quick actions</p>
      <div className="flex flex-wrap gap-2">
        {ACTIONS.map(a => (
          <Link key={a.label} to={a.to} className="flex items-center gap-2 py-2 px-3 text-xs font-medium rounded-xl bg-lsc-white dark:bg-earth-800 shadow-sm text-lsc-dark dark:text-lsc-cream motion-safe:hover:scale-[1.03] motion-safe:active:scale-[0.98] hover:ring-2 hover:ring-lsc-rose/50 transition-all">
            {a.icon}
            {a.label}
          </Link>
        ))}
      </div>
    </div>
  )
}
