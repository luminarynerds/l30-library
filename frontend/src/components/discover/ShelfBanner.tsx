/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { BookOpen, Sparkles, X } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { getDiscoverShelf } from '@/api/discover-shelves-api'
import { useLanguage } from '@/i18n'

interface Props {
  slug: string
  onClear: () => void
}

function ShelfItemCover({ src }: { src: string | null }): React.ReactElement {
  const [failed, setFailed] = useState(false)
  if (!src || failed) {
    return (
      <div
        className="w-full h-full flex items-center justify-center"
        style={{ backgroundColor: 'rgb(var(--accent-rose-rgb))', color: 'rgb(var(--accent-rose-text-rgb))' }}
        aria-hidden="true"
      >
        <BookOpen className="w-10 h-10 opacity-90" aria-hidden="true" />
      </div>
    )
  }
  return (
    <img
      src={src}
      alt=""
      loading="lazy"
      onError={() => setFailed(true)}
      className="w-full h-full object-cover"
    />
  )
}

export default function ShelfBanner({ slug, onClear }: Props): React.ReactElement | null {
  const { language } = useLanguage()
  const { data, isLoading, isError } = useQuery({
    queryKey: ['discover-ra-shelf', slug, language],
    queryFn: () => getDiscoverShelf(slug, language),
    staleTime: 5 * 60 * 1000,
    retry: false,
  })

  if (isLoading) return null
  if (isError || !data) return null

  return (
    <section
      aria-label={`${data.title} shelf`}
      className="mb-6 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-cream dark:bg-earth-900 p-5"
      data-testid="ra-shelf-banner"
    >
      <div className="flex items-start gap-3 mb-4">
        <Sparkles className="w-5 h-5 text-lsc-rose shrink-0 mt-0.5" aria-hidden="true" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-3">
            <h2 className="font-serif font-bold text-xl text-lsc-dark dark:text-lsc-cream">
              {data.title}
            </h2>
            <button
              type="button"
              onClick={onClear}
              className="text-sm text-earth-600 dark:text-cream-400 hover:text-lsc-dark dark:hover:text-lsc-cream inline-flex items-center gap-1 focus-ring rounded px-2 py-1"
              aria-label="Close shelf and browse the full catalog"
            >
              <X className="w-4 h-4" aria-hidden="true" />
              Clear shelf
            </button>
          </div>
          {data.description && (
            <p className="text-sm text-earth-600 dark:text-cream-400 mt-1 leading-relaxed">
              {data.description}
            </p>
          )}
        </div>
      </div>

      {data.items.length === 0 ? (
        <p className="text-sm text-earth-600 dark:text-cream-500 italic">
          Our librarians are still curating this shelf -- check back soon.
        </p>
      ) : (
        <ul
          className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4"
          role="list"
          data-testid="ra-shelf-items"
        >
          {data.items.map((item) => (
            <li key={item.id}>
              <Link
                to={`/catalog/${item.id}`}
                className="block bg-lsc-white dark:bg-earth-800 rounded-lg overflow-hidden focus-ring hover:shadow-soft-md transition-shadow"
              >
                <div className="aspect-[2/3] bg-lsc-cream dark:bg-earth-900 overflow-hidden">
                  <ShelfItemCover src={item.cover_url} />
                </div>
                <div className="p-2">
                  <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream truncate">
                    {item.title}
                  </p>
                  {item.author && (
                    <p className="text-xs text-earth-600 dark:text-cream-400 truncate">
                      {item.author}
                    </p>
                  )}
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
