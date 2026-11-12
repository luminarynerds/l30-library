/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Library, BookOpen, Loader2, ArrowLeft } from 'lucide-react'
import { clsx } from '@/utils/helpers'
import { getMetisLibCollections } from '@/api/domains/catalog/metislib-api'
import PageContainer from '@/components/layout/PageContainer'
import { useTranslation } from '@/i18n'

export default function EbookCollectionsPage(): React.ReactElement {
  const { t } = useTranslation()
  const { data, isLoading } = useQuery({
    queryKey: ['metislib-collections'],
    queryFn: getMetisLibCollections,
  })

  return (
    <PageContainer className="py-8">
      {/* Back link */}
      <Link to="/ebooks" className="inline-flex items-center gap-1.5 text-sm text-earth-600 dark:text-lsc-cream/50 hover:text-lsc-rose mb-6 transition-colors">
        <ArrowLeft className="w-4 h-4" />
        Back to Digital Library
      </Link>

      {/* Header */}
      <div className="mb-10 text-center">
        <h1 className="font-serif text-4xl md:text-5xl font-bold text-lsc-dark dark:text-lsc-cream mb-3">
          Collections
        </h1>
        <p className="text-earth-600 dark:text-lsc-cream/50 max-w-lg mx-auto text-lg">
          Curated reading lists for every interest
        </p>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-20" role="status" aria-live="polite">
          <Loader2 className="w-8 h-8 text-lsc-rose motion-safe:animate-spin" aria-hidden="true" />
          <span className="sr-only">{t('common.loading', 'Loading…')}</span>
        </div>
      )}

      {/* Collections Grid */}
      {data && data.items && data.items.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {data.items.map((collection) => (
            <div
              key={collection.id}
              className={clsx(
                'rounded-xl overflow-hidden p-6',
                'bg-gradient-to-b from-white/5 to-white/[0.02] dark:from-white/10 dark:to-white/[0.03]',
                'border border-white/10 dark:border-white/5',
                'backdrop-blur-sm hover:border-white/20 dark:hover:border-white/15',
                'transition-all duration-300 hover:shadow-lg hover:shadow-black/20'
              )}
            >
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2 rounded-xl bg-gradient-to-br from-lsc-rose/20 to-lsc-rose/5">
                  <Library className="w-5 h-5 text-lsc-rose" />
                </div>
                <h2 className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream">
                  {collection.title}
                </h2>
              </div>
              <p className="text-sm text-earth-600 dark:text-lsc-cream/50 line-clamp-3" title={collection.description || 'A curated collection of eBooks.'}>
                {collection.description || 'A curated collection of eBooks.'}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Empty State */}
      {data && (!data.items || data.items.length === 0) && (
        <div className="text-center py-20">
          <BookOpen className="w-12 h-12 text-earth-300 dark:text-lsc-cream/10 mx-auto mb-4" />
          <h3 className="font-serif text-lg text-lsc-dark dark:text-lsc-cream/80 mb-1">No collections yet</h3>
          <p className="text-earth-600 dark:text-lsc-cream/40 mb-6">Curated collections are coming soon.</p>
          <Link to="/ebooks" className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-lsc-rose text-white font-medium hover:bg-lsc-rose/90 transition-colors">
            Browse All eBooks
          </Link>
        </div>
      )}
    </PageContainer>
  )
}
