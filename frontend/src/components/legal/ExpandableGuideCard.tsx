/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import DOMPurify from 'dompurify'
import { Heart, MessageCircle, ChevronDown, BookOpen } from 'lucide-react'
import { LegalGuideSummary } from '@/api/legal-api'
import CollapsibleSection from './CollapsibleSection'
import SaveButton from './SaveButton'
import GlossaryTermLink from './GlossaryTermLink'
import { useGlossaryTerms } from '@/hooks/useGlossaryTerms'
import { getCurrentLocale, useTranslation } from '@/i18n'

interface CostBreakdownItem {
  name?: string
  amount?: number | string
  [key: string]: unknown
}


const READING_LEVEL_KEYS: Record<string, { key: string; fallback: string }> = {
  elementary: { key: 'components.legal.expandableGuideCard.readingLevelElementary', fallback: 'Elementary (grades 3-5)' },
  middle_school: { key: 'components.legal.expandableGuideCard.readingLevelMiddleSchool', fallback: 'Middle school (grades 6-8)' },
  high_school: { key: 'components.legal.expandableGuideCard.readingLevelHighSchool', fallback: 'High school (grades 9-12)' },
  college: { key: 'components.legal.expandableGuideCard.readingLevelCollege', fallback: 'College level' },
}

interface ExpandableGuideCardProps {
  guide: LegalGuideSummary & {
    content?: string
    steps?: Record<string, unknown>[]
    reading_level?: string
    video_url?: string | null
    timeline_description?: string | null
    cost_breakdown?: CostBreakdownItem[]
  }
  onFeedback?: (guideId: number, wasHelpful: boolean) => void
}

export default function ExpandableGuideCard({
  guide,
  onFeedback,
}: ExpandableGuideCardProps): React.ReactElement {
  const { t } = useTranslation()
  const [isExpanded, setIsExpanded] = useState(false)
  const [feedbackSubmitted, setFeedbackSubmitted] = useState<boolean | null>(null)
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({})
  const { searchTerms } = useGlossaryTerms()

  const handleFeedback = (wasHelpful: boolean) => {
    onFeedback?.(guide.id, wasHelpful)
    setFeedbackSubmitted(wasHelpful)
  }

  const toggleSection = (sectionId: string) => {
    setExpandedSections((prev) => ({
      ...prev,
      [sectionId]: !prev[sectionId],
    }))
  }

  const helpfulCount = guide.helpful_count ?? 0
  const notHelpfulCount = guide.not_helpful_count ?? 0
  const helpfulRatio =
    helpfulCount + notHelpfulCount > 0
      ? Math.round((helpfulCount / (helpfulCount + notHelpfulCount)) * 100)
      : null

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700 hover:border-lsc-rose transition-colors">
      {/* Header - Always visible */}
      <div className="flex items-start gap-4">
        <div className="p-2 bg-lsc-cream dark:bg-lsc-brown/30 rounded-lg flex-shrink-0">
          <BookOpen aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
        </div>
        <div className="flex-1 min-w-0">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-left group flex-1 w-full"
            aria-expanded={isExpanded}
            aria-controls={`guide-panel-${guide.id}`}
          >
            <span className="font-serif font-semibold text-lg text-lsc-dark dark:text-earth-50 mb-2 block group-hover:text-lsc-rose transition-colors">
              {guide.title}
            </span>
          </button>

          {guide.summary && (
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3 line-clamp-2" title={guide.summary}>
              {guide.summary}
            </p>
          )}

          {/* Quick tags */}
          <div className="flex flex-wrap gap-2">
            {guide.topic_name && (
              <span className="px-2 py-0.5 bg-lsc-cream dark:bg-lsc-brown text-lsc-dark/70 dark:text-lsc-cream/70 rounded text-xs">
                {guide.topic_name}
              </span>
            )}
            {guide.reading_level && (
              <span className="px-2 py-0.5 bg-earth-100 dark:bg-earth-800/30 text-earth-700 dark:text-lsc-rose-light rounded text-xs">
                {t('components.legal.expandableGuideCard.readingLevel', 'Reading level:')}{' '}
                {(() => {
                  const label = READING_LEVEL_KEYS[guide.reading_level]
                  return label ? t(label.key, label.fallback) : guide.reading_level.replace(/_/g, ' ')
                })()}
              </span>
            )}
            {guide.is_featured && (
              <span className="px-2 py-0.5 bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-300 rounded text-xs">
                {t('components.legal.expandableGuideCard.featured', 'Featured')}
              </span>
            )}
          </div>
        </div>

        {/* Expand button */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="p-1 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded transition-colors flex-shrink-0"
          aria-label={isExpanded ? `Collapse ${guide.title}` : `Expand ${guide.title}`}
          aria-expanded={isExpanded}
          aria-controls={`guide-panel-${guide.id}`}
        >
          <ChevronDown
            className={`w-5 h-5 text-lsc-dark dark:text-earth-50 transition-transform ${
              isExpanded ? 'rotate-180' : ''
            }`}
          />
        </button>
      </div>

      {/* Expanded sections */}
      {isExpanded && (
        <div id={`guide-panel-${guide.id}`} className="mt-4 pt-4 border-t border-lsc-border dark:border-earth-700 space-y-3">
          {/* Video section */}
          {guide.video_url && (
            <CollapsibleSection
              title={t('components.legal.expandableGuideCard.watchGuide', 'Watch Guide')}
              badge={t('components.legal.expandableGuideCard.video', 'Video')}
              isOpen={expandedSections['video'] || false}
              onToggle={() => toggleSection('video')}
              className="bg-lsc-cream/50 dark:bg-earth-900/30"
            >
              <a
                href={guide.video_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-lsc-rose hover:text-lsc-rose/80 font-medium inline-flex items-center gap-1"
              >
                {t('components.legal.expandableGuideCard.openVideoInNew', 'Open video in new window')}
                <span>→</span>
              </a>
            </CollapsibleSection>
          )}

          {/* Timeline section */}
          {guide.timeline_description && (
            <CollapsibleSection
              title={t('components.legal.expandableGuideCard.timeline', 'Timeline')}
              badge={t('components.legal.expandableGuideCard.estimated', 'Estimated')}
              isOpen={expandedSections['timeline'] || false}
              onToggle={() => toggleSection('timeline')}
              className="bg-lsc-cream/50 dark:bg-earth-900/30"
            >
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                {guide.timeline_description}
              </p>
            </CollapsibleSection>
          )}

          {/* Cost breakdown section */}
          {guide.cost_breakdown && guide.cost_breakdown.length > 0 && (
            <CollapsibleSection
              title={t('components.legal.expandableGuideCard.costs', 'Costs')}
              badge={t('components.legal.expandableGuideCard.breakdown', 'Breakdown')}
              isOpen={expandedSections['costs'] || false}
              onToggle={() => toggleSection('costs')}
              className="bg-lsc-cream/50 dark:bg-earth-900/30"
            >
              <div className="space-y-2 text-sm">
                {guide.cost_breakdown.map((item: CostBreakdownItem, idx) => (
                  <div key={idx} className="flex justify-between items-start">
                    <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{item.name || String(item)}</span>
                    {typeof item === 'object' && item.amount && (
                      <span className="font-medium text-lsc-dark dark:text-earth-50">${item.amount}</span>
                    )}
                  </div>
                ))}
              </div>
            </CollapsibleSection>
          )}

          {/* Content section */}
          {guide.content && (
            <CollapsibleSection
              title={t('components.legal.expandableGuideCard.fullContent', 'Full Content')}
              badge={t('components.legal.expandableGuideCard.details', 'Details')}
              isOpen={expandedSections['content'] || false}
              onToggle={() => toggleSection('content')}
              className="bg-lsc-cream/50 dark:bg-earth-900/30"
            >
              <div
                className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 prose dark:prose-invert prose-sm max-w-none"
                dangerouslySetInnerHTML={{
                  __html: DOMPurify.sanitize(guide.content.substring(0, 500) + '...'),
                }}
              />
            </CollapsibleSection>
          )}

          {/* Legal terms glossary */}
          {(() => {
            const relevantTerms = searchTerms('settlement plaintiff defendant damages liability')
            return relevantTerms.length > 0 ? (
              <CollapsibleSection
                title={t('components.legal.expandableGuideCard.keyLegalTerms', 'Key Legal Terms')}
                badge={relevantTerms.length.toString()}
                isOpen={expandedSections['glossary'] || false}
                onToggle={() => toggleSection('glossary')}
                className="bg-category-50 dark:bg-category-900/20 border-category-200 dark:border-category-800"
              >
                <div className="space-y-3 text-sm">
                  {relevantTerms.slice(0, 3).map((term) => (
                    <div key={term.term} className="text-category-900 dark:text-category-200">
                      <GlossaryTermLink
                        term={term.term}
                        definition={term.definition}
                        className="font-semibold"
                      />
                      <p className="mt-1 text-xs text-category-800 dark:text-category-300">
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
      <div className="mt-4 pt-4 border-t border-lsc-border dark:border-earth-700 flex items-center justify-between gap-4 flex-wrap">
        <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 space-y-0.5">
          {helpfulRatio !== null && (
            <span className="block">
              <Heart aria-hidden="true" className="w-3 h-3 inline mr-1" />
              {t('components.legal.expandableGuideCard.percentFoundHelpful', { percent: helpfulRatio })}
            </span>
          )}
          {guide.last_reviewed_at && (
            <span className="block">
              {t('components.legal.expandableGuideCard.lastReviewed', 'Last reviewed:')}{' '}
              {new Date(guide.last_reviewed_at).toLocaleDateString(getCurrentLocale(), { month: 'long', year: 'numeric' })}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <SaveButton
            id={guide.id}
            type="guide"
            title={guide.title}
            {...(guide.summary != null ? { description: guide.summary } : {})}
            showLabel={true}
          />

          {feedbackSubmitted === null && (
            <>
              <button
                onClick={() => handleFeedback(true)}
                className="flex items-center gap-1 px-2 py-1 text-xs rounded hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors text-lsc-dark/70 dark:text-lsc-cream/70"
                aria-label={`Mark ${guide.title} as helpful`}
                aria-pressed={false}
              >
                <Heart aria-hidden="true" className="w-3 h-3" />
                {t('components.legal.expandableGuideCard.helpful', 'Helpful')}
              </button>
              <button
                onClick={() => handleFeedback(false)}
                className="flex items-center gap-1 px-2 py-1 text-xs rounded hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors text-lsc-dark/70 dark:text-lsc-cream/70"
                aria-label={`Mark ${guide.title} as not helpful`}
                aria-pressed={false}
              >
                <MessageCircle aria-hidden="true" className="w-3 h-3" />
                {t('components.legal.expandableGuideCard.notHelpful', 'Not helpful')}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
