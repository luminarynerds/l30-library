/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { BookOpen } from 'lucide-react'
import { browseIndieCatalog, generateSlug } from '@/api/indie-catalog-api'

export default function MoreByAuthor({
  authorPenName,
  currentBookId,
}: {
  authorPenName: string
  currentBookId: number | string
}) {
  const { data } = useQuery({
    queryKey: ['indie-more-by-author', authorPenName],
    queryFn: () => browseIndieCatalog({ author: authorPenName, per_page: 6 }),
    enabled: !!authorPenName,
  })

  const items = (data?.items ?? [])
    .filter((item) => String(item.id) !== String(currentBookId))
    .slice(0, 4)

  if (items.length === 0) return null

  return (
    <section>
      <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">
        More by {authorPenName}
      </h2>
      <div className="flex gap-4 overflow-x-auto pb-2 -mx-1 px-1 snap-x">
        {items.map((item) => (
          <Link
            key={item.id}
            to={`/indie/book/${generateSlug(item.title, item.id)}`}
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
          </Link>
        ))}
      </div>
    </section>
  )
}
