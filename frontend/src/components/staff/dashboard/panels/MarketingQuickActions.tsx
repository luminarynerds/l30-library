/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from 'react-router-dom'
import { Mail, CalendarClock, Sparkles, BarChart3 } from 'lucide-react'

const ACTIONS = [
  { label: 'New newsletter', icon: <Mail className="w-4 h-4" aria-hidden="true" />, to: '/staff/marketing-hub' },
  { label: 'Schedule post', icon: <CalendarClock className="w-4 h-4" aria-hidden="true" />, to: '/staff/marketing-hub' },
  { label: 'Generate from event', icon: <Sparkles className="w-4 h-4" aria-hidden="true" />, to: '/staff/marketing-hub' },
  { label: 'Analytics', icon: <BarChart3 className="w-4 h-4" aria-hidden="true" />, to: '/staff/marketing-hub' },
]

export default function MarketingQuickActions() {
  return (
    <div>
      <p className="text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/60 mb-2">Quick actions</p>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        {ACTIONS.map(a => (
          <Link
            key={a.label}
            to={a.to}
            className="flex items-center justify-center gap-2 py-2.5 px-3 text-sm font-medium rounded-xl bg-lsc-white dark:bg-earth-800 shadow-sm text-lsc-dark dark:text-lsc-cream motion-safe:hover:scale-[1.03] motion-safe:active:scale-[0.98] hover:ring-2 hover:ring-lsc-rose/50 transition-all"
          >
            {a.icon}
            {a.label}
          </Link>
        ))}
      </div>
    </div>
  )
}
