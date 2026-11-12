/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Star, BookOpen } from 'lucide-react'
import { getIndieRecommendations, generateSlug } from '@/api/indie-catalog-api'

export default function ReadersAlsoEnjoyed({ ebookId }: { ebookId: number }) {
  const { data } = useQuery({
    queryKey: ['indie-recommendations', ebookId],
    queryFn: () => getIndieRecommendations(ebookId),
    enabled: !!ebookId,
  })

  if (!data || data.items.length === 0) return null

  const heading = data.algorithm === 'borrow_overlap'
    ? 'Readers Also Enjoyed'
    : 'More to Explore'

  return (
    <section>
      <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">
        {heading}
      </h2>
      <div className="flex gap-4 overflow-x-auto pb-2 -mx-1 px-1 snap-x">
        {data.items.map((item) => (
          <Link
            key={item.ebook_id}
            to={`/indie/book/${generateSlug(item.title, item.ebook_id)}`}
            className="flex-shrink-0 w-44 bg-lsc-white dark:bg-earth-800 rounded-xl p-3 hover:shadow-md transition-shadow snap-start"
          >
            <div className="aspect-[2/3] bg-lsc-cream dark:bg-lsc-brown rounded-lg overflow-hidden mb-2">
              {item.cover_url ? (
                <img
                  src={item.cover_url}
                  alt={`Cover of ${item.title}`}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  <BookOpen className="w-8 h-8 text-lsc-rose/30" />
                </div>
              )}
            </div>
            <h3
              className="font-medium text-sm text-lsc-dark dark:text-lsc-cream truncate"
              title={item.title}
            >
              {item.title}
            </h3>
            <p
              className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 truncate"
              title={item.author_pen_name}
            >
              {item.author_pen_name}
            </p>
            {item.average_rating != null && (
              <span className="flex items-center gap-0.5 text-xs mt-1">
                <Star className="w-3 h-3 text-status-warning-500 fill-yellow-500" />
                {item.average_rating.toFixed(1)}
              </span>
            )}
          </Link>
        ))}
      </div>
    </section>
  )
}
