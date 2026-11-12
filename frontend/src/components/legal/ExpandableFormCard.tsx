/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { Heart, MessageCircle, ChevronDown, FileText, ExternalLink } from 'lucide-react'
import { LegalForm } from '@/api/legal-api'
import CollapsibleSection from './CollapsibleSection'
import SaveButton from './SaveButton'
import GlossaryTermLink from './GlossaryTermLink'
import { useGlossaryTerms } from '@/hooks/useGlossaryTerms'
import { useTranslation, getCurrentLocale } from '@/i18n'

interface ExpandableFormCardProps {
  form: LegalForm
  onFeedback?: (formId: number, wasHelpful: boolean) => void
}

// DB difficulty_level values: easy | moderate | complex ('simple' kept for the legacy type alias)
const difficultyColors = {
  easy: 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300',
  simple: 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300',
  moderate: 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-300',
  complex: 'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300',
}

const DIFFICULTY_LABEL_KEYS: Record<string, { key: string; fallback: string }> = {
  easy: { key: 'components.legal.expandableFormCard.difficultyEasy', fallback: 'easy' },
  simple: { key: 'components.legal.expandableFormCard.difficultySimple', fallback: 'simple' },
  moderate: { key: 'components.legal.expandableFormCard.difficultyModerate', fallback: 'moderate' },
  complex: { key: 'components.legal.expandableFormCard.difficultyComplex', fallback: 'complex' },
}

export default function ExpandableFormCard({
  form,
  onFeedback,
}: ExpandableFormCardProps): React.ReactElement {
  const { t } = useTranslation()
  const [isExpanded, setIsExpanded] = useState(false)
  const [feedbackSubmitted, setFeedbackSubmitted] = useState<boolean | null>(null)
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({})
  const { searchTerms } = useGlossaryTerms()

  const handleFeedback = (wasHelpful: boolean) => {
    onFeedback?.(form.id, wasHelpful)
    setFeedbackSubmitted(wasHelpful)
  }

  const toggleSection = (sectionId: string) => {
    setExpandedSections((prev) => ({
      ...prev,
      [sectionId]: !prev[sectionId],
    }))
  }

  const difficultyColor = difficultyColors[form.difficulty_level as keyof typeof difficultyColors] || difficultyColors.moderate

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 hover:border-lsc-rose transition-colors">
      {/* Header */}
      <div className="p-6 border-b border-lsc-border dark:border-earth-700">
        <div className="flex items-start gap-4">
          <div className="p-2 bg-lsc-cream dark:bg-lsc-brown/30 rounded-lg flex-shrink-0">
            <FileText aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-cream/70" />
          </div>
          <div className="flex-1 min-w-0">
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="text-left group"
              aria-expanded={isExpanded}
              aria-controls={`form-panel-${form.id}`}
            >
              <span className="font-serif font-semibold text-lsc-dark dark:text-earth-50 mb-1 block group-hover:text-lsc-rose transition-colors">
                {form.plain_language_title || form.title}
              </span>
            </button>
            {form.description && (
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
                {form.description}
              </p>
            )}
            <div className="flex flex-wrap gap-2">
              {form.form_number && (
                <span className="px-2 py-0.5 bg-lsc-cream dark:bg-lsc-brown text-lsc-dark/70 dark:text-lsc-cream/70 rounded text-xs">
                  {form.form_number}
                </span>
              )}
              {form.topic_name && (
                <span className="px-2 py-0.5 bg-lsc-cream dark:bg-lsc-brown text-lsc-dark/70 dark:text-lsc-cream/70 rounded text-xs">
                  {form.topic_name}
                </span>
              )}
              <span className={`px-2 py-0.5 rounded text-xs font-medium ${difficultyColor}`}>
                {(() => {
                  const label = DIFFICULTY_LABEL_KEYS[form.difficulty_level]
                  return label ? t(label.key, label.fallback) : form.difficulty_level
                })()}
              </span>
              {form.filing_fee !== null && form.filing_fee > 0 && (
                <span className="px-2 py-0.5 bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light rounded text-xs">
                  {t('components.legal.expandableFormCard.fee', 'Fee:')} ${form.filing_fee}
                </span>
              )}
            </div>
          </div>

          {/* Expand button and form link */}
          <div className="flex items-center gap-2 flex-shrink-0">
            {form.form_url && (
              <a
                href={form.form_url}
                target="_blank"
                rel="noopener noreferrer"
                className="p-1 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded transition-colors"
                title={t('components.legal.expandableFormCard.openForm', 'Open form')}
              >
                <ExternalLink className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
              </a>
            )}
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-1 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded transition-colors"
              aria-label={isExpanded ? `Collapse ${form.plain_language_title || form.title}` : `Expand ${form.plain_language_title || form.title}`}
              aria-expanded={isExpanded}
              aria-controls={`form-panel-${form.id}`}
            >
              <ChevronDown
                className={`w-5 h-5 text-lsc-dark dark:text-earth-50 transition-transform ${
                  isExpanded ? 'rotate-180' : ''
                }`}
              />
            </button>
          </div>
        </div>
      </div>

      {/* Expanded sections */}
      {isExpanded && (
        <div id={`form-panel-${form.id}`} className="px-6 py-4 space-y-3 border-t border-lsc-border dark:border-earth-700">
          {/* When to use section */}
          {form.when_to_use && (
            <CollapsibleSection
              title={t('components.legal.expandableFormCard.whenToUseThisForm')}
              badge={t('components.legal.expandableFormCard.info', 'Info')}
              isOpen={expandedSections['when'] || false}
              onToggle={() => toggleSection('when')}
              className="bg-lsc-cream/50 dark:bg-earth-900/30"
            >
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{form.when_to_use}</p>
            </CollapsibleSection>
          )}

          {/* Instructions section */}
          {form.instructions_url && (
            <CollapsibleSection
              title={t('components.legal.expandableFormCard.instructions', 'Instructions')}
              badge={t('components.legal.expandableFormCard.guide', 'Guide')}
              isOpen={expandedSections['instructions'] || false}
              onToggle={() => toggleSection('instructions')}
              className="bg-lsc-cream/50 dark:bg-earth-900/30"
            >
              <a
                href={form.instructions_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-sm text-lsc-rose hover:text-lsc-rose/80 font-medium"
              >
                {t('components.legal.expandableFormCard.openFormInstructions', 'Open form instructions')}
                <ExternalLink className="w-3 h-3" />
              </a>
            </CollapsibleSection>
          )}

          {/* Jurisdiction section */}
          {form.jurisdiction && (
            <CollapsibleSection
              title={t('components.legal.expandableFormCard.courtInformation', 'Court Information')}
              badge={form.jurisdiction}
              isOpen={expandedSections['jurisdiction'] || false}
              onToggle={() => toggleSection('jurisdiction')}
              className="bg-lsc-cream/50 dark:bg-earth-900/30"
            >
              <div className="space-y-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                <p>
                  <strong>{t('components.legal.expandableFormCard.jurisdiction', 'Jurisdiction:')}</strong> {form.jurisdiction}
                </p>
                {form.status && (
                  <p>
                    <strong>{t('components.legal.expandableFormCard.status', 'Status:')}</strong> <span className="capitalize">{form.status}</span>
                  </p>
                )}
              </div>
            </CollapsibleSection>
          )}

          {/* Languages section */}
          {form.languages_available && form.languages_available.length > 0 && (
            <CollapsibleSection
              title={t('components.legal.expandableFormCard.availableLanguages', 'Available Languages')}
              badge={form.languages_available.length.toString()}
              isOpen={expandedSections['languages'] || false}
              onToggle={() => toggleSection('languages')}
              className="bg-lsc-cream/50 dark:bg-earth-900/30"
            >
              <div className="flex flex-wrap gap-2">
                {form.languages_available.map((lang) => (
                  <span
                    key={lang}
                    className="px-2 py-1 bg-lsc-cream dark:bg-lsc-brown/30 rounded text-xs text-lsc-dark dark:text-lsc-cream"
                  >
                    {lang}
                  </span>
                ))}
              </div>
            </CollapsibleSection>
          )}

          {/* Tips section */}
          <CollapsibleSection
            title={t('components.legal.expandableFormCard.commonTips', 'Common Tips')}
            badge={t('components.legal.expandableFormCard.help', 'Help')}
            isOpen={expandedSections['tips'] || false}
            onToggle={() => toggleSection('tips')}
            className="bg-earth-50 dark:bg-earth-800/20 border-lsc-border dark:border-earth-700"
          >
            <ul className="space-y-2 text-sm text-earth-900 dark:text-lsc-rose-light/80">
              <li className="flex gap-2">
                <span className="flex-shrink-0">•</span>
                <span>{t('components.legal.expandableFormCard.fillOutAllRequiredFields')}</span>
              </li>
              <li className="flex gap-2">
                <span className="flex-shrink-0">•</span>
                <span>{t('components.legal.expandableFormCard.useBlackOrBlueInk')}</span>
              </li>
              <li className="flex gap-2">
                <span className="flex-shrink-0">•</span>
                <span>{t('components.legal.expandableFormCard.keepCopiesForYourRecords')}</span>
              </li>
              <li className="flex gap-2">
                <span className="flex-shrink-0">•</span>
                <span>{t('components.legal.expandableFormCard.ifUnsureAboutAnyField')}</span>
              </li>
            </ul>
          </CollapsibleSection>

          {/* Legal terms glossary */}
          {(() => {
            const relevantTerms = searchTerms('court affidavit summons testimony')
            return relevantTerms.length > 0 ? (
              <CollapsibleSection
                title={t('components.legal.expandableFormCard.legalTermsExplained', 'Legal Terms Explained')}
                badge={relevantTerms.length.toString()}
                isOpen={expandedSections['glossary'] || false}
                onToggle={() => toggleSection('glossary')}
                className="bg-status-warning-50 dark:bg-status-warning-900/20 border-status-warning-200 dark:border-status-warning-800"
              >
                <div className="space-y-3 text-sm">
                  {relevantTerms.slice(0, 3).map((term) => (
                    <div key={term.term} className="text-status-warning-900 dark:text-status-warning-200">
                      <GlossaryTermLink
                        term={term.term}
                        definition={term.definition}
                        className="font-semibold"
                      />
                      <p className="mt-1 text-xs text-status-warning-800 dark:text-status-warning-300">
                        {term.definition}
                      </p>
                    </div>
                  ))}
                </div>
              </CollapsibleSection>
            ) : null
          })()}
        </div>
      )}

      {/* Footer */}
      <div className="px-6 py-4 bg-lsc-cream/50 dark:bg-earth-900/50 border-t border-lsc-border dark:border-earth-700 flex items-center justify-between gap-4 flex-wrap">
        <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 space-y-0.5">
          <span className="block">
            {t('components.legal.expandableFormCard.formAvailableInLanguages', { count: form.languages_available?.length || 1 })}
          </span>
          {form.last_reviewed_at && (
            <span className="block">
              {t('components.legal.expandableFormCard.lastReviewed', 'Last reviewed:')}{' '}
              {new Date(form.last_reviewed_at).toLocaleDateString(getCurrentLocale(), { month: 'long', year: 'numeric' })}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <SaveButton
            id={form.id}
            type="form"
            title={form.title || form.plain_language_title || 'Form'}
            {...(form.description != null ? { description: form.description } : {})}
            showLabel={true}
          />

          {feedbackSubmitted === null ? (
            <>
              <button
                onClick={() => handleFeedback(true)}
                className="flex items-center gap-1 px-2 py-1 text-xs rounded hover:bg-lsc-white dark:hover:bg-earth-800 transition-colors text-lsc-dark/70 dark:text-lsc-cream/70"
                aria-label={`Mark ${form.plain_language_title || form.title} as helpful`}
                aria-pressed={false}
              >
                <Heart className="w-3 h-3" />
                {t('components.legal.expandableFormCard.helpful', 'Helpful')}
              </button>
              <button
                onClick={() => handleFeedback(false)}
                className="flex items-center gap-1 px-2 py-1 text-xs rounded hover:bg-lsc-white dark:hover:bg-earth-800 transition-colors text-lsc-dark/70 dark:text-lsc-cream/70"
                aria-label={`Mark ${form.plain_language_title || form.title} as not helpful`}
                aria-pressed={false}
              >
                <MessageCircle className="w-3 h-3" />
                {t('components.legal.expandableFormCard.notHelpful', 'Not helpful')}
              </button>
            </>
          ) : (
            <span className="text-xs text-status-success-600 dark:text-status-success-400 font-medium">✓ {t('components.legal.expandableFormCard.feedbackRecorded', 'Feedback recorded')}</span>
          )}
        </div>
      </div>
    </div>
  )
}
