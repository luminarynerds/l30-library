/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useRef, useCallback } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { Shield, ClipboardCheck } from 'lucide-react'
import { useTranslation } from '@/i18n'
import { TAB_DEFINITIONS, TAB_KEYS, type ActiveTab } from './constants'
import QuickStats from './components/QuickStats'
import TemplateLibraryTab from './components/TemplateLibraryTab'
import ProgramPlansTab from './components/ProgramPlansTab'
import MarketingRemindersTab from './components/MarketingRemindersTab'
import SuccessMetricsTab from './components/SuccessMetricsTab'
import { AdminShell } from '@/components/shells/AdminShell'
import PageContainer from '@/components/layout/PageContainer'

export default function ProgramPlanningPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user } = useAuth()
  const [activeTab, setActiveTab] = useState<ActiveTab>('templates')
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([])

  const handleTabKeyDown = useCallback((e: React.KeyboardEvent<HTMLDivElement>) => {
    const currentIndex = TAB_KEYS.indexOf(activeTab)
    let newIndex: number | null = null

    switch (e.key) {
      case 'ArrowRight':
        newIndex = (currentIndex + 1) % TAB_KEYS.length
        break
      case 'ArrowLeft':
        newIndex = (currentIndex - 1 + TAB_KEYS.length) % TAB_KEYS.length
        break
      case 'Home':
        newIndex = 0
        break
      case 'End':
        newIndex = TAB_KEYS.length - 1
        break
      default:
        return
    }

    e.preventDefault()
    const newKey = TAB_KEYS[newIndex]
    if (newKey) {
      setActiveTab(newKey)
      tabRefs.current[newIndex]?.focus()
    }
  }, [activeTab])

  if (!user || !['admin', 'super_admin', 'staff'].includes(user.role)) {
    return (
      <AdminShell title="Program Planning" icon={<ClipboardCheck className="w-5 h-5" />}>
        <div className="min-h-screen bg-gradient-to-b from-lsc-cream via-lsc-cream to-earth-50 dark:from-lsc-dark dark:via-earth-800 dark:to-lsc-dark py-20">
          <PageContainer className="text-center">
            <Shield className="w-16 h-16 text-lsc-dark/70 dark:text-lsc-cream/70 mx-auto mb-4" />
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">Staff-Only Area</h1>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">{t('programPlanning.staffOrAdminAccessRequired')}</p>
          </PageContainer>
        </div>
      </AdminShell>
    )
  }

  return (
    <AdminShell title="Program Planning" icon={<ClipboardCheck className="w-5 h-5" />}>
      <div className="min-h-screen bg-gradient-to-b from-lsc-cream via-lsc-cream to-earth-50 dark:from-lsc-dark dark:via-earth-800 dark:to-lsc-dark">
        <PageContainer className="py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <ClipboardCheck className="w-8 h-8 text-lsc-dark/70 dark:text-lsc-cream/70" />
            <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              Program Planning Tools
            </h2>
          </div>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            Your program planning toolkit. Reuse what worked, track what you need, and see what made a difference.
          </p>
        </div>

        {/* Quick Stats */}
        <QuickStats />

        {/* Tab Navigation */}
        <div className="flex gap-2 mb-6 border-b border-lsc-border dark:border-earth-700" role="tablist" onKeyDown={handleTabKeyDown}>
          {TAB_DEFINITIONS.map((tab, index) => (
            <button
              key={tab.key}
              ref={el => { tabRefs.current[index] = el }}
              id={`tab-${tab.key}`}
              role="tab"
              aria-selected={activeTab === tab.key}
              aria-controls={`tabpanel-${tab.key}`}
              tabIndex={activeTab === tab.key ? 0 : -1}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.key
                  ? 'border-earth-600 text-earth-700 dark:border-earth-400 dark:text-earth-300'
                  : 'border-transparent text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div role="tabpanel" id={`tabpanel-${activeTab}`} aria-labelledby={`tab-${activeTab}`}>
          {activeTab === 'templates' && <TemplateLibraryTab />}
          {activeTab === 'plans' && <ProgramPlansTab />}
          {activeTab === 'reminders' && <MarketingRemindersTab />}
          {activeTab === 'metrics' && <SuccessMetricsTab />}
        </div>
        </PageContainer>
      </div>
    </AdminShell>
  )
}
