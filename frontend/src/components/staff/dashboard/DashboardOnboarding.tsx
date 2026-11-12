/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { ClipboardList, Briefcase, Gavel, Baby, Megaphone, ListChecks } from 'lucide-react'

type DashboardFunction = 'front_desk' | 'board_ops' | 'board_president' | 'kids_services' | 'page_shelver' | 'marketing'
type DashboardTone = 'calm' | 'standard' | 'full'

interface DashboardProfileUpdate {
  dashboard_functions: DashboardFunction[]
  dashboard_tone: DashboardTone
}

interface Props {
  userName: string
  onComplete: (data: DashboardProfileUpdate) => void
}

const FUNCTION_OPTIONS: { id: DashboardFunction; label: string; sub: string; icon: React.ReactNode }[] = [
  { id: 'front_desk', label: 'Public service', sub: 'Circ, reference, programs', icon: <ClipboardList className="w-4 h-4 text-lsc-dark/60 dark:text-lsc-cream/60" aria-hidden="true" /> },
  { id: 'board_ops', label: 'Board / governance', sub: 'Trustees, secretary', icon: <Gavel className="w-4 h-4 text-lsc-dark/60 dark:text-lsc-cream/60" aria-hidden="true" /> },
  { id: 'board_president', label: 'Board president / chair', sub: 'Sign-offs, meeting prep', icon: <Briefcase className="w-4 h-4 text-lsc-dark/60 dark:text-lsc-cream/60" aria-hidden="true" /> },
  { id: 'page_shelver', label: 'Page / shelver', sub: 'Shelving, holds, tasks', icon: <ListChecks className="w-4 h-4 text-lsc-dark/60 dark:text-lsc-cream/60" aria-hidden="true" /> },
  { id: 'marketing', label: 'Marketing & comms', sub: 'Newsletter, social, content', icon: <Megaphone className="w-4 h-4 text-lsc-dark/60 dark:text-lsc-cream/60" aria-hidden="true" /> },
  { id: 'kids_services', label: 'Kids & teen services', sub: 'Programs, storytime, reading', icon: <Baby className="w-4 h-4 text-lsc-dark/60 dark:text-lsc-cream/60" aria-hidden="true" /> },
]

const TONE_OPTIONS: { id: DashboardTone; label: string; sub: string }[] = [
  { id: 'calm', label: 'Calm', sub: 'Just dates, no colors' },
  { id: 'standard', label: 'Standard', sub: 'Subtle visual cues' },
  { id: 'full', label: 'Full', sub: 'Colors and counts' },
]

export default function DashboardOnboarding({ userName, onComplete }: Props) {
  const [selectedFunctions, setSelectedFunctions] = useState<Set<DashboardFunction>>(new Set())
  const [selectedTone, setSelectedTone] = useState<DashboardTone>('standard')

  const toggleFunction = (fn: DashboardFunction) => {
    setSelectedFunctions(prev => {
      const next = new Set(prev)
      if (next.has(fn)) next.delete(fn)
      else next.add(fn)
      return next
    })
  }

  const handleSubmit = () => {
    const fns = Array.from(selectedFunctions)
    if (fns.length === 0) return
    onComplete({ dashboard_functions: fns, dashboard_tone: selectedTone })
  }

  const handleSkip = () => {
    onComplete({ dashboard_functions: ['front_desk'], dashboard_tone: 'standard' })
  }

  return (
    <div className="max-w-xl mx-auto py-12 px-4">
      <p className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50 tracking-wider mb-1">QUICK SETUP</p>
      <h1 className="text-3xl font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-1">Welcome, {userName}.</h1>
      <p className="text-sm text-lsc-dark/60 dark:text-lsc-cream/70 mb-8">Two questions, then you&apos;re in. Both easy to change later.</p>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 shadow-sm mb-4">
        <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">What do you do here?</p>
        <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/70 mb-4">Pick all that apply.</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {FUNCTION_OPTIONS.map(opt => (
            <label
              key={opt.id}
              className={`flex items-center gap-3 p-3 rounded-xl border cursor-pointer transition-colors ${
                selectedFunctions.has(opt.id)
                  ? 'border-lsc-rose bg-lsc-cream/50 dark:bg-lsc-brown/30 dark:border-lsc-rose-light'
                  : 'border-lsc-border dark:border-earth-700 hover:bg-lsc-cream/30 dark:hover:bg-lsc-brown/20'
              }`}
            >
              <input
                type="checkbox"
                checked={selectedFunctions.has(opt.id)}
                onChange={() => toggleFunction(opt.id)}
                className="sr-only"
              />
              {opt.icon}
              <div>
                <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">{opt.label}</p>
                <p className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50">{opt.sub}</p>
              </div>
            </label>
          ))}
        </div>
      </div>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 shadow-sm mb-6">
        <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">How should the system flag time-sensitive items?</p>
        <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/70 mb-4">Change anytime.</p>
        <div className="grid grid-cols-3 gap-2">
          {TONE_OPTIONS.map(opt => (
            <label
              key={opt.id}
              className={`block p-3 rounded-xl border cursor-pointer transition-colors text-center ${
                selectedTone === opt.id
                  ? 'border-lsc-rose bg-lsc-cream/50 dark:bg-lsc-brown/30 dark:border-lsc-rose-light'
                  : 'border-lsc-border dark:border-earth-700 hover:bg-lsc-cream/30 dark:hover:bg-lsc-brown/20'
              }`}
            >
              <input
                type="radio"
                name="tone"
                checked={selectedTone === opt.id}
                onChange={() => setSelectedTone(opt.id)}
                className="sr-only"
              />
              <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">{opt.label}</p>
              <p className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50">{opt.sub}</p>
            </label>
          ))}
        </div>
      </div>

      <div className="flex items-center justify-between">
        <button
          onClick={handleSkip}
          className="text-sm text-lsc-dark/50 dark:text-lsc-cream/50 underline hover:text-lsc-dark dark:hover:text-lsc-cream"
        >
          Skip -- use defaults
        </button>
        <button
          onClick={handleSubmit}
          disabled={selectedFunctions.size === 0}
          className="px-5 py-2 text-sm font-medium rounded-xl bg-lsc-rose text-white hover:bg-lsc-rose/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          Done
        </button>
      </div>
    </div>
  )
}
