/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { ClipboardList, Gavel, Briefcase, Baby, Megaphone, ListChecks } from 'lucide-react'

type DashboardFunction = 'front_desk' | 'board_ops' | 'board_president' | 'kids_services' | 'page_shelver' | 'marketing'

const FUNCTION_META: Record<DashboardFunction, { label: string; icon: React.ReactNode }> = {
  front_desk: { label: 'Front Desk', icon: <ClipboardList className="w-5 h-5" aria-hidden="true" /> },
  board_ops: { label: 'Board', icon: <Gavel className="w-5 h-5" aria-hidden="true" /> },
  board_president: { label: 'President', icon: <Briefcase className="w-5 h-5" aria-hidden="true" /> },
  page_shelver: { label: 'Shelver', icon: <ListChecks className="w-5 h-5" aria-hidden="true" /> },
  marketing: { label: 'Marketing', icon: <Megaphone className="w-5 h-5" aria-hidden="true" /> },
  kids_services: { label: 'Kids', icon: <Baby className="w-5 h-5" aria-hidden="true" /> },
}

interface Props {
  functions: DashboardFunction[]
  active: DashboardFunction
  onSwitch: (fn: DashboardFunction) => void
}

export default function RoleSwitcher({ functions, active, onSwitch }: Props) {
  if (functions.length <= 1) return null

  return (
    <aside className="w-16 flex-shrink-0">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm py-3 space-y-1">
        {functions.map(fn => {
          const meta = FUNCTION_META[fn]
          const isActive = fn === active
          return (
            <button
              key={fn}
              onClick={() => onSwitch(fn)}
              title={meta.label}
              className={`w-full flex flex-col items-center gap-1 py-2.5 px-1 rounded-xl transition-colors ${
                isActive
                  ? 'text-lsc-rose dark:text-lsc-rose-light bg-lsc-cream dark:bg-lsc-brown/30'
                  : 'text-lsc-dark/50 dark:text-lsc-cream/50 hover:bg-lsc-cream/50 dark:hover:bg-lsc-brown/20'
              }`}
            >
              {meta.icon}
              <span className="text-[10px] font-medium leading-tight">{meta.label}</span>
            </button>
          )
        })}
      </div>
    </aside>
  )
}
