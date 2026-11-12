/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useCallback } from 'react'
import { ArrowLeft, HelpCircle, MessageCircle, Scale } from 'lucide-react'
import type { LegalTopic, LegalProviderSummary } from '@/api/legal-api'
import { useTranslation } from '@/i18n'

type Step = 'topic' | 'urgency' | 'result'
type Urgency = 'today' | 'this_week' | 'researching'

interface LegalTriageWizardProps {
  topics: LegalTopic[]
  providers: LegalProviderSummary[]
  onSelectTopic: (topicId: number | null) => void
  /**
   * Called when the wizard wants to route the patron to one of the
   * always-visible page sections. The page is responsible for
   * scrolling + focusing the matching `<section>` landmark.
   * Stable section ids: 'resources' | 'clinics' | 'forms' | 'privacy'.
   */
  onJumpToSection: (section: string) => void
}

const STEP_OF_KEYS = [
  { key: 'components.legal.legalTriageWizard.stepOf1', fallback: 'Step 1 of 3' },
  { key: 'components.legal.legalTriageWizard.stepOf2', fallback: 'Step 2 of 3' },
  { key: 'components.legal.legalTriageWizard.stepOf3', fallback: 'Step 3 of 3' },
] as const

const STORAGE_KEY = 'legal-triage-dismissed'
const EXPIRY_MS = 30 * 24 * 60 * 60 * 1000 // 30 days

function isDismissed(): boolean {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return false
    const { expiry } = JSON.parse(raw)
    if (Date.now() > expiry) {
      localStorage.removeItem(STORAGE_KEY)
      return false
    }
    return true
  } catch {
    return false
  }
}

function dismiss(): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify({ expiry: Date.now() + EXPIRY_MS }))
}

export default function LegalTriageWizard({
  topics,
  providers,
  onSelectTopic,
  onJumpToSection,
}: LegalTriageWizardProps): React.ReactElement | null {
  const { t } = useTranslation()
  const [visible, setVisible] = useState(!isDismissed())
  const [step, setStep] = useState<Step>('topic')
  const [selectedTopicId, setSelectedTopicId] = useState<number | null>(null)
  const [selectedUrgency, setSelectedUrgency] = useState<Urgency | null>(null)

  const handleTopicSelect = useCallback((topicId: number | null) => {
    setSelectedTopicId(topicId)
    setStep('urgency')
  }, [])

  const handleUrgencySelect = useCallback((urgency: Urgency) => {
    setSelectedUrgency(urgency)
    setStep('result')
  }, [])

  const handleDismiss = useCallback(() => {
    dismiss()
    setVisible(false)
  }, [])

  const handleRestart = useCallback(() => {
    setStep('topic')
    setSelectedTopicId(null)
    setSelectedUrgency(null)
  }, [])

  const handleGoToResources = useCallback(() => {
    onSelectTopic(selectedTopicId)
    onJumpToSection('resources')
    handleDismiss()
  }, [selectedTopicId, onSelectTopic, onJumpToSection, handleDismiss])

  const handleGoToClinics = useCallback(() => {
    onJumpToSection('clinics')
    handleDismiss()
  }, [onJumpToSection, handleDismiss])

  if (!visible) return null

  const stepNumber = step === 'topic' ? 1 : step === 'urgency' ? 2 : 3
  const stepOf = STEP_OF_KEYS[stepNumber - 1] ?? STEP_OF_KEYS[0]
  const filteredProviders = selectedTopicId
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ? providers.filter((p) => (p as any).topic_ids?.includes(selectedTopicId))
    : providers

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <HelpCircle aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-earth-50">
            {t('components.legal.legalTriageWizard.whatKindOfHelpDo', 'What kind of help do you need?')}
          </h2>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50">
            {t(stepOf.key, stepOf.fallback)}
          </span>
          <button
            onClick={handleDismiss}
            className="inline-flex items-center min-h-[44px] px-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/80 hover:text-lsc-dark dark:hover:text-lsc-cream transition-colors"
          >
            {t('components.legal.legalTriageWizard.skip', 'Skip')}
          </button>
        </div>
      </div>

      {step !== 'topic' && (
        <button
          onClick={() => setStep(step === 'result' ? 'urgency' : 'topic')}
          className="flex items-center gap-1 min-h-[44px] px-2 text-sm text-lsc-dark dark:text-lsc-cream hover:text-lsc-rose dark:hover:text-lsc-rose-light mb-4 transition-colors"
        >
          <ArrowLeft aria-hidden="true" className="w-4 h-4" />
          {t('components.legal.legalTriageWizard.back', 'Back')}
        </button>
      )}

      {step === 'topic' && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {topics.map((topic) => (
            <button
              key={topic.id}
              onClick={() => handleTopicSelect(topic.id)}
              className="p-3 min-h-[44px] text-left rounded-xl border border-lsc-border dark:border-earth-700 hover:border-lsc-rose dark:hover:border-lsc-rose transition-colors bg-lsc-cream/50 dark:bg-earth-900/30"
            >
              <span className="text-sm font-medium text-lsc-dark dark:text-earth-50">{topic.name}</span>
            </button>
          ))}
          <button
            onClick={() => handleTopicSelect(null)}
            className="p-3 min-h-[44px] text-left rounded-xl border border-lsc-border dark:border-earth-700 hover:border-lsc-rose dark:hover:border-lsc-rose transition-colors bg-lsc-cream/50 dark:bg-earth-900/30"
          >
            <span className="text-sm font-medium text-lsc-dark dark:text-earth-50">{t('components.legal.legalTriageWizard.imNotSure', "I'm not sure")}</span>
          </button>
        </div>
      )}

      {step === 'urgency' && (
        <div className="grid gap-3">
          {([
            {
              value: 'today' as Urgency,
              label: t('components.legal.legalTriageWizard.iNeedHelpToday', 'I need help today'),
              sublabel: t('components.legal.legalTriageWizard.emergencyOrUrgentSituation', 'Emergency or urgent situation'),
            },
            {
              value: 'this_week' as Urgency,
              label: t('components.legal.legalTriageWizard.withinTheNextWeek', 'Within the next week'),
              sublabel: t('components.legal.legalTriageWizard.iHaveAnUpcoming', 'I have an upcoming deadline'),
            },
            {
              value: 'researching' as Urgency,
              label: t('components.legal.legalTriageWizard.imResearching', "I'm researching"),
              sublabel: t('components.legal.legalTriageWizard.noImmediateDeadline', 'No immediate deadline'),
            },
          ]).map((option) => (
            <button
              key={option.value}
              onClick={() => handleUrgencySelect(option.value)}
              className="p-4 min-h-[44px] text-left rounded-xl border border-lsc-border dark:border-earth-700 hover:border-lsc-rose dark:hover:border-lsc-rose transition-colors bg-lsc-cream/50 dark:bg-earth-900/30"
            >
              <span className="text-sm font-medium text-lsc-dark dark:text-earth-50 block">{option.label}</span>
              <span className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50">{option.sublabel}</span>
            </button>
          ))}
        </div>
      )}

      {step === 'result' && (
        <div className="space-y-4">
          {selectedUrgency === 'today' && (
            <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-xl p-4">
              <h3 className="font-medium text-status-danger-800 dark:text-status-danger-200 mb-2">
                {t('components.legal.legalTriageWizard.contactTheseResourcesNow', 'Contact these resources now:')}
              </h3>
              <ul className="space-y-2">
                {(filteredProviders.length > 0 ? filteredProviders : providers).map((p) => (
                  <li key={p.id} className="flex items-center gap-2 text-sm text-status-danger-700 dark:text-status-danger-300">
                    <Scale aria-hidden="true" className="w-4 h-4 flex-shrink-0" />
                    <span className="font-medium">{p.name}</span>
                    {p.phone && (
                      <a
                        href={`tel:${p.phone.replace(/[^\d+]/g, '')}`}
                        aria-label={`Call ${p.name} at ${p.phone}`}
                        className="inline-flex items-center min-h-[44px] px-1 underline"
                      >
                        {p.phone}
                      </a>
                    )}
                  </li>
                ))}
              </ul>
              <button
                onClick={handleGoToClinics}
                className="mt-3 inline-flex items-center min-h-[44px] text-sm text-status-danger-700 dark:text-status-danger-300 underline hover:no-underline"
              >
                {t('components.legal.legalTriageWizard.seeUpcomingFreeLegal', 'See upcoming free legal clinics')}
              </button>
            </div>
          )}

          {selectedUrgency !== 'today' && (
            <div className="space-y-3">
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                {selectedTopicId
                  ? t('components.legal.legalTriageWizard.heresWhatWeHave', "Here's what we have for your topic:")
                  : t('components.legal.legalTriageWizard.notSureWhatYou', 'Not sure what you need? Start here:')}
              </p>
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={handleGoToResources}
                  className="inline-flex items-center min-h-[44px] px-4 py-2 bg-lsc-rose text-white rounded-xl text-sm font-medium hover:bg-lsc-rose/90 transition-colors"
                >
                  {selectedTopicId
                    ? t('components.legal.legalTriageWizard.browseGuidesResources', 'Browse guides & resources')
                    : t('components.legal.legalTriageWizard.browseAllResources', 'Browse all resources')}
                </button>
                <button
                  onClick={handleGoToClinics}
                  className="inline-flex items-center min-h-[44px] px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-xl text-sm font-medium text-lsc-dark dark:text-earth-50 hover:border-lsc-rose transition-colors"
                >
                  {t('components.legal.legalTriageWizard.findAFreeLegal', 'Find a free legal clinic')}
                </button>
                <a
                  href="/ask-librarian"
                  className="inline-flex items-center min-h-[44px] gap-1 px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-xl text-sm font-medium text-lsc-dark dark:text-earth-50 hover:border-lsc-rose transition-colors"
                >
                  <MessageCircle aria-hidden="true" className="w-4 h-4" />
                  {t('components.legal.legalTriageWizard.askALibrarian', 'Ask a Librarian')}
                </a>
              </div>
            </div>
          )}

          <button
            onClick={handleRestart}
            className="inline-flex items-center min-h-[44px] px-2 text-xs text-lsc-dark dark:text-lsc-cream hover:text-lsc-rose dark:hover:text-lsc-rose-light transition-colors"
          >
            {t('components.legal.legalTriageWizard.startOver', 'Start over')}
          </button>
        </div>
      )}
    </div>
  )
}

export function RestartTriageLink({ onRestart }: { onRestart: () => void }): React.ReactElement {
  const { t } = useTranslation()
  return (
    <button
      onClick={onRestart}
      className="inline-flex items-center min-h-[44px] text-sm text-lsc-rose dark:text-lsc-rose-light hover:underline transition-colors"
    >
      {t('components.legal.legalTriageWizard.needHelpFindingThe', 'Need help finding the right resource? Restart guided help')}
    </button>
  )
}
