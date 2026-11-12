/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useRef, useEffect } from 'react'
import { Settings, ClipboardList, Gavel, Briefcase, ListChecks, Megaphone, Baby } from 'lucide-react'
import type { DashboardFunction, DashboardTone } from '@/api/staff-api/dashboard-profile'

const FUNCTION_OPTIONS: { id: DashboardFunction; label: string; icon: React.ReactNode }[] = [
  { id: 'front_desk', label: 'Public service', icon: <ClipboardList className="w-4 h-4" aria-hidden="true" /> },
  { id: 'board_ops', label: 'Board / governance', icon: <Gavel className="w-4 h-4" aria-hidden="true" /> },
  { id: 'board_president', label: 'Board president', icon: <Briefcase className="w-4 h-4" aria-hidden="true" /> },
  { id: 'page_shelver', label: 'Page / shelver', icon: <ListChecks className="w-4 h-4" aria-hidden="true" /> },
  { id: 'marketing', label: 'Marketing & comms', icon: <Megaphone className="w-4 h-4" aria-hidden="true" /> },
  { id: 'kids_services', label: 'Kids & teen', icon: <Baby className="w-4 h-4" aria-hidden="true" /> },
]

const TONE_OPTIONS: { id: DashboardTone; label: string }[] = [
  { id: 'calm', label: 'Calm' },
  { id: 'standard', label: 'Standard' },
  { id: 'full', label: 'Full' },
]

interface Props {
  currentFunctions: DashboardFunction[]
  currentTone: DashboardTone
  onSave: (functions: DashboardFunction[], tone: DashboardTone) => void
}

export default function DashboardSettings({ currentFunctions, currentTone, onSave }: Props) {
  const [open, setOpen] = useState(false)
  const [selected, setSelected] = useState<Set<DashboardFunction>>(new Set(currentFunctions))
  const [tone, setTone] = useState<DashboardTone>(currentTone)
  const panelRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  useEffect(() => {
    setSelected(new Set(currentFunctions))
    setTone(currentTone)
  }, [currentFunctions, currentTone])

  const toggle = (fn: DashboardFunction) => {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(fn)) { if (next.size > 1) next.delete(fn) }
      else next.add(fn)
      return next
    })
  }

  const handleSave = () => {
    onSave(Array.from(selected), tone)
    setOpen(false)
  }

  const hasChanges = tone !== currentTone ||
    selected.size !== currentFunctions.length ||
    Array.from(selected).some(f => !currentFunctions.includes(f))

  return (
    <div className="relative" ref={panelRef}>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1 text-xs text-lsc-dark/40 dark:text-lsc-cream/40 hover:text-lsc-dark dark:hover:text-lsc-cream transition-colors"
        title="Dashboard settings"
      >
        <Settings className="w-3.5 h-3.5" aria-hidden="true" />
      </button>

      {open && (
        <div className="absolute right-0 top-8 z-50 w-72 bg-lsc-white dark:bg-earth-800 rounded-xl shadow-soft-lg border border-lsc-border dark:border-earth-700 p-4 space-y-4">
          <div>
            <p className="text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/60 mb-2">My dashboards</p>
            <div className="space-y-1">
              {FUNCTION_OPTIONS.map(opt => (
                <label
                  key={opt.id}
                  className={`flex items-center gap-2.5 p-2 rounded-lg cursor-pointer transition-colors ${
                    selected.has(opt.id)
                      ? 'bg-lsc-cream/60 dark:bg-lsc-brown/30 text-lsc-dark dark:text-lsc-cream'
                      : 'text-lsc-dark/50 dark:text-lsc-cream/50 hover:bg-lsc-cream/30 dark:hover:bg-lsc-brown/20'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selected.has(opt.id)}
                    onChange={() => toggle(opt.id)}
                    className="sr-only"
                  />
                  {opt.icon}
                  <span className="text-xs font-medium">{opt.label}</span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <p className="text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/60 mb-2">Urgency tone</p>
            <div className="flex gap-1">
              {TONE_OPTIONS.map(opt => (
                <button
                  key={opt.id}
                  onClick={() => setTone(opt.id)}
                  className={`flex-1 text-xs font-medium py-1.5 rounded-lg transition-colors ${
                    tone === opt.id
                      ? 'bg-lsc-rose text-white'
                      : 'bg-lsc-cream/50 dark:bg-lsc-brown/20 text-lsc-dark/60 dark:text-lsc-cream/60 hover:bg-lsc-cream dark:hover:bg-lsc-brown/30'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {hasChanges && (
            <button
              onClick={handleSave}
              className="w-full text-xs font-medium py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 transition-colors"
            >
              Save changes
            </button>
          )}
        </div>
      )}
    </div>
  )
}
