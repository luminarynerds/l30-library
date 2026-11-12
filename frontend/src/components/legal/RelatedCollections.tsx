/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { ArrowRight } from 'lucide-react'
import { LegalCollection } from '@/api/legal-api'
import { useTranslation } from '@/i18n'

interface RelatedCollectionsProps {
  relatedCollections: LegalCollection[]
  onCollectionClick?: (collection: LegalCollection) => void
}

export default function RelatedCollections({
  relatedCollections,
  onCollectionClick,
}: RelatedCollectionsProps) {
  const { t } = useTranslation()
  if (!relatedCollections || relatedCollections.length === 0) {
    return null
  }

  return (
    <div className="pt-4 border-t border-lsc-border dark:border-earth-700">
      <h4 className="font-medium text-lsc-dark dark:text-earth-50 mb-3 text-sm">
        {t('components.legal.relatedCollections.relatedLegalJourneys', 'Related Legal Journeys')}
      </h4>
      <div className="space-y-2">
        {relatedCollections.map((collection) => (
          <button
            key={collection.id}
            onClick={() => onCollectionClick?.(collection)}
            className="w-full text-left p-3 bg-lsc-cream/50 dark:bg-earth-700/30 hover:bg-lsc-cream dark:hover:bg-earth-700/50 rounded-lg border border-lsc-border dark:border-earth-700 transition-colors"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  {collection.icon && <span className="text-lg">{collection.icon}</span>}
                  <p className="font-medium text-sm text-lsc-dark dark:text-earth-50 truncate" title={collection.title}>
                    {collection.title}
                  </p>
                </div>
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1 line-clamp-1" title={collection.description}>
                  {collection.description}
                </p>
              </div>
              <ArrowRight className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" />
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
