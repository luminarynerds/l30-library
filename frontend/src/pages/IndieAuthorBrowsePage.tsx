/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { BookOpen, Users, Search } from 'lucide-react'
import { getPublicAuthorLists, penNameToSlug } from '@/api/indie-catalog-api'
import IndieFollowButton from '@/components/indie/IndieFollowButton'
import { useUnifiedAccessibility } from '@/features/accessibility/hooks/useUnifiedAccessibility'
import toast from 'react-hot-toast'
import { t } from '@/i18n'
import PageContainer from '@/components/layout/PageContainer'

interface AuthorItemResponse {
  id: number
  author_id: number
  author: AuthorBriefResponse
  staff_note?: string
  display_order: number
  added_at: string
}

interface AuthorBriefResponse {
  id: number
  pen_name: string
  bio?: string
  profile_image_url?: string
  approved_books: number
  total_borrows: number
  trust_level: number
}

export default function IndieAuthorBrowsePage() {
  const { announceToScreenReader } = useUnifiedAccessibility()
  const [searchQuery, setSearchQuery] = useState('')

  const { data: lists = [], isLoading, error } = useQuery({
    queryKey: ['indie-author-lists'],
    queryFn: () => getPublicAuthorLists(),
  })

  if (error) {
    toast.error(t('toast.indieAuthorBrowse.failedToLoadAuthorLists'))
    announceToScreenReader('Failed to load author lists')
  }

  // Flatten all authors from all lists for search
  const allAuthors: (AuthorItemResponse & { listTitle: string })[] = []
  lists.forEach((list) => {
    (list.items || []).forEach((item) => {
      allAuthors.push({ ...item, listTitle: list.title })
    })
  })

  // Filter authors by search query
  const filteredAuthors = searchQuery
    ? allAuthors.filter((author) =>
        author.author.pen_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        author.author.bio?.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : allAuthors

  return (
    <PageContainer className="py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-4">
          <Users className="w-8 h-8 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">Browse Indie Authors</h1>
        </div>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 max-w-2xl">
          Discover curated collections of independent authors in our library. Each collection is carefully selected by our librarians to highlight talented voices in indie publishing.
        </p>
      </div>

      {/* Search Bar */}
      <div className="mb-8">
        <div className="relative">
          <Search className="absolute left-3 top-3 w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/60" aria-hidden="true" />
          <input
            type="text"
            placeholder={t('placeholder.indieAuthorBrowse.searchAuthorsByName')}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream placeholder-lsc-dark/40 focus:outline-none focus:ring-2 focus:ring-lsc-rose/50"
            aria-label={t('aria.indieAuthorBrowse.searchAuthors')}
          />
        </div>
      </div>

      {isLoading ? (
        <div className="text-center py-16">
          <div className="inline-block motion-safe:animate-spin">
            <BookOpen className="w-8 h-8 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
          </div>
          <p className="mt-4 text-lsc-dark/70 dark:text-lsc-cream/70">Loading author collections...</p>
        </div>
      ) : lists.length === 0 ? (
        <div className="text-center py-16">
          <BookOpen className="w-12 h-12 mx-auto mb-4 text-lsc-dark/30 dark:text-lsc-cream/60" aria-hidden="true" />
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">No Author Collections Yet</h2>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">Check back soon for curated indie author collections from our librarians.</p>
        </div>
      ) : (
        <div className="space-y-8">
          {lists.map((list) => (
            <section key={list.id} className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border/60 dark:border-earth-700/80 p-6">
              <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">{list.title}</h2>
              {list.description && (
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">{list.description}</p>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {(list.items || []).map((item) => (
                  <AuthorCard key={item.id} author={item.author} staffNote={item.staff_note} />
                ))}
              </div>
            </section>
          ))}

          {searchQuery && filteredAuthors.length === 0 && (
            <div className="text-center py-12">
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">No authors match "{searchQuery}"</p>
            </div>
          )}
        </div>
      )}
    </PageContainer>
  )
}

interface AuthorCardProps {
  author: AuthorBriefResponse
  staffNote?: string | undefined
}

function AuthorCard({ author, staffNote }: AuthorCardProps) {
  const slug = penNameToSlug(author.pen_name)
  return (
    <div className="bg-earth-50 dark:bg-earth-700/50 rounded-xl p-4 hover:shadow-md transition-shadow">
      <Link
        to={`/indie/author/${slug}`}
        className="flex gap-4"
        aria-label={`View profile of ${author.pen_name}`}
      >
        {author.profile_image_url ? (
          <img
            src={author.profile_image_url}
            alt={author.pen_name}
            className="w-16 h-16 rounded-full object-cover shrink-0"
          />
        ) : (
          <div className="w-16 h-16 rounded-full bg-lsc-dark/10 dark:bg-earth-600 flex items-center justify-center shrink-0">
            <Users className="w-8 h-8 text-lsc-dark/30 dark:text-lsc-cream/60" aria-hidden="true" />
          </div>
        )}

        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-lsc-dark dark:text-lsc-cream text-sm">{author.pen_name}</h3>
          {author.bio && (
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 line-clamp-2 mt-1" title={author.bio}>{author.bio}</p>
          )}
          <div className="flex gap-2 mt-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
            <span>{author.approved_books} books</span>
            <span>•</span>
            <span>{author.total_borrows} borrows</span>
          </div>
          {staffNote && (
            <p className="text-xs text-lsc-rose dark:text-lsc-rose-light italic mt-2 border-l-2 border-lsc-rose pl-2">
              {staffNote}
            </p>
          )}
        </div>
      </Link>
      <div className="mt-3 flex justify-end">
        <IndieFollowButton authorId={author.id} authorName={author.pen_name} />
      </div>
    </div>
  )
}
