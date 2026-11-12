/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { KeyboardEvent, useId, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import clsx from 'clsx'
import { Clock, CheckSquare, BarChart3 } from 'lucide-react'
import { AdminShell } from '../components/shells/AdminShell'
import { FocusTimeScheduler } from '../components/staff/FocusTimeScheduler'
import { FocusTimeApprovalDashboard } from '../components/staff/FocusTimeApprovalDashboard'
import { FocusTimeAnalyticsDashboard } from '../components/staff/FocusTimeAnalyticsDashboard'
import { useAuth } from '../contexts/AuthContext'
import { useTranslation } from '@/i18n'

type FocusTimeTab = 'schedule' | 'approvals' | 'analytics'

const MANAGER_ROLES = ['admin', 'super_admin', 'director']

export default function StaffFocusTimePage(): React.ReactElement {
  const { t } = useTranslation()
  const { user } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()

  const isManager = !!user && MANAGER_ROLES.includes(user.role)
  const activeTab = (searchParams.get('tab') as FocusTimeTab) || 'schedule'
  const setActiveTab = (tab: FocusTimeTab) => setSearchParams({ tab })

  // Only the tabs that are actually rendered participate in roving-tabindex
  // keyboard navigation. Non-managers see schedule only.
  const visibleTabs: FocusTimeTab[] = isManager
    ? ['schedule', 'approvals', 'analytics']
    : ['schedule']

  const baseId = useId()
  const tabId = (tab: FocusTimeTab) => `${baseId}-${tab}-tab`
  const panelId = (tab: FocusTimeTab) => `${baseId}-${tab}-panel`

  const tabRefs = useRef<Partial<Record<FocusTimeTab, HTMLButtonElement | null>>>({})

  const focusTab = (tab: FocusTimeTab) => {
    setActiveTab(tab)
    requestAnimationFrame(() => {
      tabRefs.current[tab]?.focus()
    })
  }

  const handleTabKeyDown = (e: KeyboardEvent<HTMLButtonElement>) => {
    const currentIndex = visibleTabs.indexOf(activeTab)
    let nextIndex: number | null = null
    if (e.key === 'ArrowRight') {
      nextIndex = (currentIndex + 1) % visibleTabs.length
    } else if (e.key === 'ArrowLeft') {
      nextIndex = (currentIndex - 1 + visibleTabs.length) % visibleTabs.length
    } else if (e.key === 'Home') {
      nextIndex = 0
    } else if (e.key === 'End') {
      nextIndex = visibleTabs.length - 1
    }
    if (nextIndex !== null) {
      e.preventDefault()
      focusTab(visibleTabs[nextIndex]!)
    }
  }

  const tabClass = (tab: FocusTimeTab) =>
    clsx(
      'flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose',
      activeTab === tab
        ? 'text-lsc-rose border-lsc-rose'
        : 'text-lsc-dark/70 dark:text-lsc-cream/70 border-transparent hover:text-lsc-dark dark:hover:text-lsc-cream',
    )

  return (
    <AdminShell title={t('focusTime.title', 'Focus Time')}>
      <div>
        {/* StaffLayout (via AdminShell title) already emits the page <h1>; this is a styled visual title only, demoted to avoid a duplicate h1. */}
        <p className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          {t('focusTime.title', 'Focus Time')}
        </p>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
          {t('focusTime.subtitle', 'Schedule and manage focused work blocks')}
        </p>
      </div>

      <div
        role="tablist"
        aria-label={t('focusTime.title', 'Focus Time')}
        className="flex gap-1 border-b border-lsc-border dark:border-earth-700"
      >
        <button
          ref={(el) => { tabRefs.current.schedule = el }}
          id={tabId('schedule')}
          role="tab"
          type="button"
          aria-selected={activeTab === 'schedule'}
          aria-controls={panelId('schedule')}
          tabIndex={activeTab === 'schedule' ? 0 : -1}
          onClick={() => setActiveTab('schedule')}
          onKeyDown={handleTabKeyDown}
          className={tabClass('schedule')}
        >
          <Clock aria-hidden="true" className="w-4 h-4" />
          {t('focusTime.tabs.schedule', 'Schedule')}
        </button>
        {isManager && (
          <button
            ref={(el) => { tabRefs.current.approvals = el }}
            id={tabId('approvals')}
            role="tab"
            type="button"
            aria-selected={activeTab === 'approvals'}
            aria-controls={panelId('approvals')}
            tabIndex={activeTab === 'approvals' ? 0 : -1}
            onClick={() => setActiveTab('approvals')}
            onKeyDown={handleTabKeyDown}
            className={tabClass('approvals')}
          >
            <CheckSquare aria-hidden="true" className="w-4 h-4" />
            {t('focusTime.tabs.approvals', 'Approvals')}
          </button>
        )}
        {isManager && (
          <button
            ref={(el) => { tabRefs.current.analytics = el }}
            id={tabId('analytics')}
            role="tab"
            type="button"
            aria-selected={activeTab === 'analytics'}
            aria-controls={panelId('analytics')}
            tabIndex={activeTab === 'analytics' ? 0 : -1}
            onClick={() => setActiveTab('analytics')}
            onKeyDown={handleTabKeyDown}
            className={tabClass('analytics')}
          >
            <BarChart3 aria-hidden="true" className="w-4 h-4" />
            {t('focusTime.tabs.analytics', 'Analytics')}
          </button>
        )}
      </div>

      {activeTab === 'schedule' && (
        <div
          role="tabpanel"
          id={panelId('schedule')}
          aria-labelledby={tabId('schedule')}
          tabIndex={0}
          className="focus:outline-none"
        >
          <FocusTimeScheduler />
        </div>
      )}
      {activeTab === 'approvals' && isManager && (
        <div
          role="tabpanel"
          id={panelId('approvals')}
          aria-labelledby={tabId('approvals')}
          tabIndex={0}
          className="focus:outline-none"
        >
          <FocusTimeApprovalDashboard />
        </div>
      )}
      {activeTab === 'analytics' && isManager && (
        <div
          role="tabpanel"
          id={panelId('analytics')}
          aria-labelledby={tabId('analytics')}
          tabIndex={0}
          className="focus:outline-none"
        >
          <FocusTimeAnalyticsDashboard />
        </div>
      )}
    </AdminShell>
  )
}
