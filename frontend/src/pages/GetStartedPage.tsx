/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { Rocket, HelpCircle, BookOpen, Check } from 'lucide-react'
import StandardPageLayout from '@/components/StandardPageLayout'
import { StepByStepGuide, type Step } from '@/components/StepByStepGuide'
import { useAuth } from '@/contexts/AuthContext'
import { usePageTitle } from '@/hooks/usePageTitle'
import { useTranslation } from '@/i18n/I18nContext'

const STORAGE_KEY = 'l30-get-started-progress'

interface ProgressState {
  cardApplied: boolean
  accountCreated: boolean
  firstHold: boolean
}

const STEP_ID_MAP: Record<string, keyof ProgressState> = {
  'apply-card': 'cardApplied',
  'create-account': 'accountCreated',
  'first-hold': 'firstHold',
}

function loadProgress(): ProgressState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      return {
        cardApplied: Boolean(parsed.cardApplied),
        accountCreated: Boolean(parsed.accountCreated),
        firstHold: Boolean(parsed.firstHold),
      }
    }
  } catch {
    // Corrupted data -- start fresh
  }
  return { cardApplied: false, accountCreated: false, firstHold: false }
}

function saveProgress(state: ProgressState): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  } catch {
    // Storage full or unavailable -- fail silently
  }
}

function progressToStepIds(state: ProgressState): string[] {
  const ids: string[] = []
  if (state.cardApplied) ids.push('apply-card')
  if (state.accountCreated) ids.push('create-account')
  if (state.firstHold) ids.push('first-hold')
  return ids
}

const buildSteps = (t: (key: string) => string): Step[] => [
  {
    id: 'apply-card',
    actionTitle: t('getStarted.step1.title'),
    instruction: t('getStarted.step1.instruction'),
    expectedResult: t('getStarted.step1.expectedResult'),
    actionUrl: '/card-application',
    actionLabel: t('getStarted.step1.actionLabel'),
  },
  {
    id: 'create-account',
    actionTitle: 'Join the waiting list',
    instruction: t('getStarted.step2.instruction'),
    expectedResult: t('getStarted.step2.expectedResult'),
    actionUrl: '/register',
    actionLabel: 'Join the waiting list',
  },
  {
    id: 'first-hold',
    actionTitle: t('getStarted.step3.title'),
    instruction: t('getStarted.step3.instruction'),
    expectedResult: t('getStarted.step3.expectedResult'),
    actionUrl: '/catalog',
    actionLabel: t('getStarted.step3.actionLabel'),
  },
]

export default function GetStartedPage(): React.ReactElement {
  usePageTitle('Get Started')
  const { t } = useTranslation()
  const { isAuthenticated, user } = useAuth()

  const [progress, setProgress] = useState<ProgressState>(() => {
    const stored = loadProgress()

    // Auto-detect from auth state
    if (isAuthenticated) {
      stored.accountCreated = true
      if (user?.library_card) {
        stored.cardApplied = true
      }
    }

    return stored
  })

  // Sync auth-derived state on login/logout changes
  useEffect(() => {
    setProgress((prev) => {
      const next = { ...prev }
      if (isAuthenticated) {
        next.accountCreated = true
        if (user?.library_card) {
          next.cardApplied = true
        }
      }
      return next
    })
  }, [isAuthenticated, user?.library_card])

  // Persist to localStorage whenever progress changes
  useEffect(() => {
    saveProgress(progress)
  }, [progress])

  const markedComplete = progressToStepIds(progress)

  const handleMarkComplete = useCallback((stepId: string) => {
    const key = STEP_ID_MAP[stepId]
    if (!key) return
    setProgress((prev) => ({ ...prev, [key]: true }))
  }, [])

  const steps = buildSteps(t)
  const allComplete = markedComplete.length === steps.length

  return (
    <StandardPageLayout
      title={t('getStarted.title')}
      subtitle={t('getStarted.subtitle')}
      icon={Rocket}
      maxWidth="xl"
    >
      <StepByStepGuide
        steps={steps}
        markedComplete={markedComplete}
        onMarkComplete={handleMarkComplete}
        hideCompletion
      />

      {/* Completion celebration */}
      {allComplete && (
        <section
          className="mt-8 p-6 bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-800 rounded-xl"
          aria-live="polite"
        >
          <div className="flex items-start gap-3">
            <Check className="w-6 h-6 text-status-success-600 dark:text-status-success-400 flex-shrink-0 mt-0.5" aria-hidden="true" />
            <div>
              <h3 className="font-serif text-lg font-semibold text-status-success-800 dark:text-status-success-300 mb-2">
                You're all set. Welcome to L30.
              </h3>
              <p className="text-sm text-status-success-700 dark:text-status-success-400/90 leading-relaxed mb-4">
                Your library card is ready, your account is active, and you know how to place holds.
                You're ready to explore everything the library has to offer.
              </p>
              <div className="flex flex-wrap gap-3">
                <Link
                  to="/catalog"
                  className="inline-flex items-center px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white text-sm font-medium rounded-xl motion-safe:transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lsc-rose"
                >
                  Browse the catalog
                </Link>
                <Link
                  to="/events"
                  className="inline-flex items-center px-4 py-2 bg-lsc-cream dark:bg-lsc-brown hover:bg-lsc-border dark:hover:bg-lsc-brown/80 text-lsc-dark dark:text-lsc-cream text-sm font-medium border border-lsc-border dark:border-lsc-brown rounded-xl motion-safe:transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lsc-rose"
                >
                  Find events near you
                </Link>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Help callout */}
      <section className="mt-10 grid sm:grid-cols-2 gap-4">
        <Link
          to="/ask-librarian"
          className="flex items-center gap-3 p-4 rounded-xl bg-lsc-cream/50 dark:bg-lsc-brown/20 border border-lsc-border dark:border-earth-700 hover:border-lsc-rose dark:hover:border-lsc-rose motion-safe:transition-colors"
        >
          <HelpCircle className="w-5 h-5 text-lsc-rose flex-shrink-0" aria-hidden="true" />
          <div>
            <span className="font-medium text-sm text-lsc-dark dark:text-lsc-cream">
              {t('getStarted.needHelp')}
            </span>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">
              {t('getStarted.needHelpDescription')}
            </p>
          </div>
        </Link>

        <Link
          to="/guides/library-card"
          className="flex items-center gap-3 p-4 rounded-xl bg-lsc-cream/50 dark:bg-lsc-brown/20 border border-lsc-border dark:border-earth-700 hover:border-lsc-rose dark:hover:border-lsc-rose motion-safe:transition-colors"
        >
          <BookOpen className="w-5 h-5 text-lsc-rose flex-shrink-0" aria-hidden="true" />
          <div>
            <span className="font-medium text-sm text-lsc-dark dark:text-lsc-cream">
              {t('getStarted.detailedGuide')}
            </span>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">
              {t('getStarted.detailedGuideDescription')}
            </p>
          </div>
        </Link>
      </section>
    </StandardPageLayout>
  )
}
