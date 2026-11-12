/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState } from 'react'
import {
  ChevronDown, Clock, Zap, Heart, MessageCircle, DollarSign, CheckCircle, AlertCircle,
  Banknote, Eraser, HeartCrack, Home, Scale, Gavel, Users, Baby, Shield, FileText, BookOpen,
  type LucideIcon,
} from 'lucide-react'

import { LegalCollection, recordCollectionFeedback } from '@/api/legal-api'
import SaveButton from './SaveButton'
import RelatedCollections from './RelatedCollections'
import { useTranslation, getCurrentLocale } from '@/i18n'

const ICON_MAP: Record<string, LucideIcon> = {
  banknote: Banknote,
  eraser: Eraser,
  'heart-crack': HeartCrack,
  home: Home,
  scale: Scale,
  gavel: Gavel,
  users: Users,
  baby: Baby,
  shield: Shield,
  'file-text': FileText,
  'book-open': BookOpen,
}

// DB complexity_level values: easy | moderate | complex
const COMPLEXITY_LABEL_KEYS: Record<string, { key: string; fallback: string }> = {
  easy: { key: 'components.legal.legalCollectionCard.complexityEasy', fallback: 'Easy' },
  moderate: { key: 'components.legal.legalCollectionCard.complexityModerate', fallback: 'Moderate' },
  complex: { key: 'components.legal.legalCollectionCard.complexityComplex', fallback: 'Complex' },
}

interface LegalCollectionCardProps {
  collection: LegalCollection
  onViewClick?: () => void
  relatedCollections?: LegalCollection[]
  onRelatedCollectionClick?: (collection: LegalCollection) => void
}

export default function LegalCollectionCard({
  collection,
  onViewClick: _onViewClick,
  relatedCollections,
  onRelatedCollectionClick
}: LegalCollectionCardProps): React.ReactElement {
  const { t } = useTranslation()
  const [isExpanded, setIsExpanded] = useState(false)
  const [feedbackSubmitted, setFeedbackSubmitted] = useState<boolean | null>(null)

  const handleFeedback = async (wasHelpful: boolean) => {
    try {
      await recordCollectionFeedback(collection.id, wasHelpful)
      setFeedbackSubmitted(wasHelpful)
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    }
  }

  const totalResourceCount =
    collection.guide_ids.length +
    collection.form_ids.length +
    collection.clinic_ids.length +
    collection.provider_ids.length

  const helpfulRatio =
    collection.helpful_count + collection.unhelpful_count > 0
      ? Math.round((collection.helpful_count / (collection.helpful_count + collection.unhelpful_count)) * 100)
      : null

  // Format cost display
  const formatCost = () => {
    if (collection.estimated_cost_max === 0 || (collection.estimated_cost_min === 0 && !collection.estimated_cost_max)) {
      return t('components.legal.legalCollectionCard.free', 'Free')
    }
    if (collection.estimated_cost_min === 0 && collection.estimated_cost_max) {
      return `$0-${collection.estimated_cost_max}`
    }
    if (collection.estimated_cost_max) {
      return `$${collection.estimated_cost_min}-${collection.estimated_cost_max}`
    }
    return `$${collection.estimated_cost_min}+`
  }

  const lastReviewedDate = collection.last_reviewed_date
    ? new Date(collection.last_reviewed_date).toLocaleDateString(getCurrentLocale(), {
        year: 'numeric',
        month: 'short',
      })
    : null

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden hover:border-lsc-rose transition-colors">
      {/* Header */}
      <div className="p-6 border-b border-lsc-border dark:border-earth-700">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              {collection.icon && (() => {
                const IconComp = ICON_MAP[collection.icon]
                // Non-ASCII string (emoji) — render as-is rather than falling back to a wrong icon
                const isEmoji = /[^\p{ASCII}]/u.test(collection.icon)
                return (
                  <div className={`p-2 rounded-lg ${collection.color_code || 'bg-lsc-cream dark:bg-lsc-brown/30'}`}>
                    {IconComp ? (
                      <IconComp aria-hidden className="w-5 h-5 text-lsc-dark dark:text-earth-50" />
                    ) : isEmoji ? (
                      <span aria-hidden="true">{collection.icon}</span>
                    ) : (
                      <BookOpen aria-hidden className="w-5 h-5 text-lsc-dark dark:text-earth-50" />
                    )}
                  </div>
                )
              })()}
              <div className="flex-1">
                <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-earth-50">
                  {collection.title}
                </h3>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  {collection.situation.replace(/[-_]/g, ' ')}
                </p>
              </div>
            </div>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4 line-clamp-2" title={collection.description}>
              {collection.description}
            </p>

            {/* Key info row: Cost, Time, Complexity */}
            <div className="flex flex-wrap gap-4 mb-3 text-sm">
              {/* Cost indicator (Librarian rec - Priority 1) */}
              <div className="flex items-center gap-1 px-3 py-1.5 bg-status-warning-50 dark:bg-status-warning-900/20 rounded-lg border border-status-warning-200 dark:border-status-warning-800">
                <DollarSign className="w-4 h-4 text-status-warning-600 dark:text-status-warning-400 flex-shrink-0" />
                <span className="font-semibold text-status-warning-900 dark:text-status-warning-100">{formatCost()}</span>
                {collection.fee_waiver_available && (
                  <span className="text-xs text-status-warning-700 dark:text-status-warning-300 ml-1">{t('components.legal.legalCollectionCard.waivable', 'Waivable')}</span>
                )}
              </div>

              <div className="flex items-center gap-1 text-lsc-dark/70 dark:text-lsc-cream/70">
                <Clock className="w-4 h-4" />
                <span>
                  {collection.estimated_time_minutes
                    ? t('components.legal.legalCollectionCard.minutes', { count: collection.estimated_time_minutes })
                    : t('components.legal.legalCollectionCard.variable', 'Variable')}
                </span>
              </div>

              <div className="flex items-center gap-1 text-lsc-dark/70 dark:text-lsc-cream/70">
                <Zap className="w-4 h-4" />
                <span className="capitalize">{(() => {
                  const label = COMPLEXITY_LABEL_KEYS[collection.complexity_level ?? '']
                  return label
                    ? t(label.key, label.fallback)
                    : collection.complexity_level || t('components.legal.legalCollectionCard.intermediate', 'intermediate')
                })()}</span>
              </div>

              <div className="flex items-center gap-1 px-2 py-1 bg-lsc-cream dark:bg-lsc-brown/20 rounded">
                <span className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
                  {t('components.legal.legalCollectionCard.resources', { count: totalResourceCount })}
                </span>
              </div>
            </div>

            {/* Last reviewed (Librarian rec - Priority 1) */}
            {lastReviewedDate && (
              <p className="text-xs text-status-success-600 dark:text-status-success-400 flex items-center gap-1">
                <CheckCircle className="w-3 h-3" />
                {t('components.legal.legalCollectionCard.lastReviewed', 'Last reviewed:')} {lastReviewedDate}
              </p>
            )}
          </div>

          {/* Expand button */}
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex-shrink-0 p-2 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg transition-colors"
            aria-label={isExpanded ? `Collapse ${collection.title}` : `Expand ${collection.title}`}
            aria-expanded={isExpanded}
            aria-controls={`collection-panel-${collection.id}`}
          >
            <ChevronDown
              className={`w-5 h-5 text-lsc-dark dark:text-earth-50 transition-transform ${
                isExpanded ? 'rotate-180' : ''
              }`}
            />
          </button>
        </div>
      </div>

      {/* Expanded content */}
      {isExpanded && (
        <div id={`collection-panel-${collection.id}`} className="border-t border-lsc-border dark:border-earth-700 px-6 py-4 space-y-4">
          {/* Cost detail (Librarian rec - Priority 1) */}
          {collection.cost_description && (
            <div className="p-3 bg-earth-50 dark:bg-earth-800/20 rounded-lg border border-lsc-border dark:border-earth-700">
              <p className="text-sm text-earth-900 dark:text-earth-200">
                <strong>{t('components.legal.legalCollectionCard.costDetails', 'Cost details:')}</strong> {collection.cost_description}
              </p>
            </div>
          )}

          {/* Success outcomes */}
          {collection.success_outcomes.length > 0 && (
            <div>
              <h4 className="font-medium text-lsc-dark dark:text-earth-50 mb-2 text-sm">
                {t('components.legal.legalCollectionCard.whatYoullAccomplish', "What you'll accomplish:")}
              </h4>
              <ul className="space-y-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                {collection.success_outcomes.slice(0, 3).map((outcome, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-lsc-rose flex-shrink-0">✓</span>
                    <span>{outcome}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Resources breakdown */}
          <div>
            <h4 className="font-medium text-lsc-dark dark:text-earth-50 mb-3 text-sm">
              {t('components.legal.legalCollectionCard.insideThisCollection', 'Inside this collection:')}
            </h4>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              {collection.guide_ids.length > 0 && (
                <div className="p-2 bg-lsc-cream dark:bg-lsc-brown/20 rounded text-center">
                  <div className="font-bold text-lsc-dark dark:text-earth-50">
                    {collection.guide_ids.length}
                  </div>
                  <div className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('components.legal.legalCollectionCard.guides', 'Guides')}</div>
                </div>
              )}
              {collection.form_ids.length > 0 && (
                <div className="p-2 bg-lsc-cream dark:bg-lsc-brown/20 rounded text-center">
                  <div className="font-bold text-lsc-dark dark:text-earth-50">
                    {collection.form_ids.length}
                  </div>
                  <div className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('components.legal.legalCollectionCard.forms', 'Forms')}</div>
                </div>
              )}
              {collection.clinic_ids.length > 0 && (
                <div className="p-2 bg-lsc-cream dark:bg-lsc-brown/20 rounded text-center">
                  <div className="font-bold text-lsc-dark dark:text-earth-50">
                    {collection.clinic_ids.length}
                  </div>
                  <div className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('components.legal.legalCollectionCard.clinics', 'Clinics')}</div>
                </div>
              )}
              {collection.provider_ids.length > 0 && (
                <div className="p-2 bg-lsc-cream dark:bg-lsc-brown/20 rounded text-center">
                  <div className="font-bold text-lsc-dark dark:text-earth-50">
                    {collection.provider_ids.length}
                  </div>
                  <div className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('components.legal.legalCollectionCard.services', 'Services')}</div>
                </div>
              )}
            </div>
          </div>

          {/* Reading level */}
          {collection.reading_level && (
            <div className="pt-2 border-t border-lsc-border dark:border-earth-700">
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                <strong>{t('components.legal.legalCollectionCard.readingLevel', 'Reading level:')}</strong> {collection.reading_level.replace('_', ' ')}
              </p>
            </div>
          )}

          {/* Related Collections */}
          {relatedCollections && relatedCollections.length > 0 && (
            <RelatedCollections
              relatedCollections={relatedCollections}
              {...(onRelatedCollectionClick !== undefined ? { onCollectionClick: onRelatedCollectionClick } : {})}
            />
          )}
        </div>
      )}

      {/* Footer with CTA and Ask Librarian */}
      <div className="px-6 py-4 bg-lsc-cream/50 dark:bg-earth-900/50 border-t border-lsc-border dark:border-earth-700 space-y-3">
        {/* Help section (Librarian rec - Priority 1) */}
        <div className="flex gap-3">
          <a
            href="/contact?topic=legal-resources"
            className="flex items-center justify-center gap-2 flex-1 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg text-sm font-medium transition-colors"
            title={t('components.legal.legalCollectionCard.bookAConsultationWithLibrary')}
          >
            <AlertCircle className="w-4 h-4" />
            {t('components.legal.legalCollectionCard.askALibrarian', 'Ask a Librarian')}
          </a>
          <SaveButton
            id={collection.id}
            type="collection"
            title={collection.title}
            description={collection.description}
            showLabel={false}
          />
        </div>

        {/* Feedback section */}
        <div className="flex items-center justify-between pt-2 border-t border-lsc-border dark:border-earth-700">
          <div className="flex items-center gap-2">
            {helpfulRatio !== null && (
              <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                <Heart className="w-3 h-3 inline mr-1" />
                {t('components.legal.legalCollectionCard.percentFoundHelpful', { percent: helpfulRatio })}
              </div>
            )}
          </div>

          <div className="flex items-center gap-2">
            {feedbackSubmitted === null ? (
              <>
                <button
                  onClick={() => handleFeedback(true)}
                  className="flex items-center gap-1 px-2 py-1 text-xs rounded hover:bg-lsc-white dark:hover:bg-earth-800 transition-colors text-lsc-dark/70 dark:text-lsc-cream/70"
                  aria-label={`Mark ${collection.title} as helpful`}
                  aria-pressed={false}
                >
                  <Heart className="w-3 h-3" />
                  {t('components.legal.legalCollectionCard.helpful', 'Helpful')}
                </button>
                <button
                  onClick={() => handleFeedback(false)}
                  className="flex items-center gap-1 px-2 py-1 text-xs rounded hover:bg-lsc-white dark:hover:bg-earth-800 transition-colors text-lsc-dark/70 dark:text-lsc-cream/70"
                  aria-label={`Mark ${collection.title} as not helpful`}
                  aria-pressed={false}
                >
                  <MessageCircle className="w-3 h-3" />
                  {t('components.legal.legalCollectionCard.notHelpful', 'Not helpful')}
                </button>
              </>
            ) : (
              <span className="text-xs text-status-success-600 dark:text-status-success-400 font-medium">✓ {t('components.legal.legalCollectionCard.feedbackRecorded', 'Feedback recorded')}</span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
