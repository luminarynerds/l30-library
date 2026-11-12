/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { BookOpen, Loader2 } from 'lucide-react'
import type { LegalCollection } from '@/api/legal-api'
import LegalCollectionCard from './LegalCollectionCard'
import { useTranslation } from '@/i18n'

interface FeaturedCollectionsProps {
  collections: LegalCollection[]
  isLoading: boolean
}

const RELATIONSHIP_MAP: Record<string, string[]> = {
  'facing-eviction': ['small-claims-court', 'employment-wages'],
  'immigration-help': ['employment-wages'],
  'custody-family-law': ['small-claims-court'],
  'employment-wages': ['small-claims-court', 'facing-eviction'],
  'small-claims-court': ['employment-wages', 'facing-eviction'],
}

export default function FeaturedCollections({
  collections,
  isLoading,
}: FeaturedCollectionsProps): React.ReactElement | null {
  const { t } = useTranslation()
  if (collections.length === 0 && !isLoading) return null

  return (
    <div className="mb-8">
      <div className="flex items-center gap-2 mb-6">
        <BookOpen aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-earth-50">
          {t('components.legal.featuredCollections.guidedLegalJourneys', 'Guided Legal Journeys')}
        </h2>
      </div>
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
        {t(
          'components.legal.featuredCollections.curatedPathsThroughRelated',
          'Curated paths through related forms, guides, and services for common legal situations.',
        )}
      </p>
      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
        </div>
      ) : (
        <div className="grid md:grid-cols-2 gap-6">
          {collections.map((collection) => {
            const relatedSlugs = RELATIONSHIP_MAP[collection.slug] || []
            const relatedCollectionsList = collections.filter((c) => relatedSlugs.includes(c.slug))
            return (
              <LegalCollectionCard
                key={collection.id}
                collection={collection}
                relatedCollections={relatedCollectionsList}
              />
            )
          })}
        </div>
      )}
    </div>
  )
}
