/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from "react-router-dom"
import { ArrowRight, ArrowLeft, RefreshCw, UserPlus } from "lucide-react"

const ACTIONS = [
  { label: "Check out", icon: <ArrowRight className="w-5 h-5" aria-hidden="true" />, to: "/staff/circulation?tab=checkout" },
  { label: "Return", icon: <ArrowLeft className="w-5 h-5" aria-hidden="true" />, to: "/staff/circulation?tab=checkin" },
  { label: "Renew", icon: <RefreshCw className="w-5 h-5" aria-hidden="true" />, to: "/staff/circulation?tab=renew" },
  { label: "New patron", icon: <UserPlus className="w-5 h-5" aria-hidden="true" />, to: "/staff/patrons" },
]

export default function FrontDeskQuickActions() {
  return (
    <div>
      <p className="text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/60 mb-2">Quick actions</p>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {ACTIONS.map(a => (
          <Link
            key={a.label}
            to={a.to}
            className="flex items-center justify-center gap-2 py-4 px-3 text-base font-medium rounded-xl bg-lsc-white dark:bg-earth-800 shadow-sm text-lsc-dark dark:text-lsc-cream motion-safe:hover:scale-[1.03] motion-safe:active:scale-[0.98] hover:ring-2 hover:ring-lsc-rose/50 transition-all"
          >
            {a.icon}
            {a.label}
          </Link>
        ))}
      </div>
    </div>
  )
}
