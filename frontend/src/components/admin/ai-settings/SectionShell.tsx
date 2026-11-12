/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useId, type ReactNode } from 'react'
import { ArrowLeft } from 'lucide-react'

interface Tab {
  id: string
  label: string
  icon: React.ElementType
}

interface SectionShellProps {
  title: string
  description: string
  tabs: Tab[]
  defaultTab?: string
  backLabel?: string
  onBack: () => void
  children: (activeTab: string) => ReactNode
}

export function SectionShell({
  title,
  description,
  tabs,
  defaultTab,
  backLabel = 'Back to Dashboard',
  onBack,
  children,
}: SectionShellProps) {
  const [activeTab, setActiveTab] = useState(defaultTab || tabs[0]?.id || '')
  const idPrefix = useId()

  const handleKeyDown = (e: React.KeyboardEvent, index: number) => {
    let nextIndex = index
    if (e.key === 'ArrowRight') nextIndex = (index + 1) % tabs.length
    else if (e.key === 'ArrowLeft') nextIndex = (index - 1 + tabs.length) % tabs.length
    else if (e.key === 'Escape') { onBack(); return }
    else return
    e.preventDefault()
    const nextTab = tabs[nextIndex]
    if (!nextTab) return
    setActiveTab(nextTab.id)
    document.getElementById(`${idPrefix}-tab-${nextTab.id}`)?.focus()
  }

  return (
    <section aria-label={title}>
      <button
        onClick={onBack}
        className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose mb-4 focus:outline-none focus:ring-2 focus:ring-lsc-rose/50 rounded-lg px-2 py-1 -ml-2"
      >
        <ArrowLeft className="w-4 h-4" aria-hidden="true" />
        {backLabel}
      </button>
      <div className="mb-2">
        <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">{title}</h2>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{description}</p>
      </div>
      <div
        role="tablist"
        aria-label={`${title} tabs`}
        className="mb-6 border-b border-lsc-border dark:border-earth-700 overflow-x-auto"
      >
        <div className="flex gap-1 min-w-max">
          {tabs.map((tab, index) => {
            const Icon = tab.icon
            const isActive = activeTab === tab.id
            return (
              <button
                key={tab.id}
                id={`${idPrefix}-tab-${tab.id}`}
                role="tab"
                aria-selected={isActive}
                aria-controls={`${idPrefix}-panel-${tab.id}`}
                tabIndex={isActive ? 0 : -1}
                onClick={() => setActiveTab(tab.id)}
                onKeyDown={(e) => handleKeyDown(e, index)}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                  isActive
                    ? 'border-lsc-rose text-lsc-rose'
                    : 'border-transparent text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-dark dark:hover:text-lsc-cream hover:border-lsc-border'
                }`}
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                {tab.label}
              </button>
            )
          })}
        </div>
      </div>
      <div
        id={`${idPrefix}-panel-${activeTab}`}
        role="tabpanel"
        aria-labelledby={`${idPrefix}-tab-${activeTab}`}
        tabIndex={0}
      >
        {children(activeTab)}
      </div>
    </section>
  )
}
