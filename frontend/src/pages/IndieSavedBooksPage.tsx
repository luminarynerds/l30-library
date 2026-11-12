/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * My Saved Books page -- shows bookmarked indie ebooks.
 */
import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Bookmark, BookOpen, Loader2 } from 'lucide-react'
import { getMyBookmarks } from '@/api/indie-engagement-api'
import { getPublicBookDetail, generateSlug, type BookDetailPublic } from '@/api/indie-catalog-api'
import BookmarkButton from '@/components/indie/BookmarkButton'
import { useBranding } from '@/contexts/BrandingContext'
import PageContainer from '@/components/layout/PageContainer'

export default function IndieSavedBooksPage() {
  const branding = useBranding()

  useEffect(() => {
    document.title = 'My Saved Books | Indie Catalog'
    return () => { document.title = branding.library_name }
  }, [branding.library_name])

  const { data: bookmarks, isLoading } = useQuery({
    queryKey: ['indie-bookmarks'],
    queryFn: getMyBookmarks,
  })

  // Fetch full book details for bookmarked IDs
  const ebookIds = bookmarks?.items.map((b) => b.ebook_id) || []

  const { data: booksData, isLoading: booksLoading } = useQuery({
    queryKey: ['indie-bookmark-books', ebookIds],
    queryFn: async () => {
      if (ebookIds.length === 0) return []
      const results = await Promise.all(
        ebookIds.map((id) =>
          getPublicBookDetail(String(id)).catch(() => null),
        ),
      )
      return results.filter((b): b is BookDetailPublic => b !== null)
    },
    enabled: ebookIds.length > 0,
  })

  const books = booksData || []
  const loading = isLoading || booksLoading

  return (
    <PageContainer className="py-8">
      <div className="flex items-center gap-3 mb-6">
        <Bookmark className="w-6 h-6 text-lsc-rose" />
        <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          My Saved Books
        </h1>
      </div>

      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
        </div>
      ) : books.length === 0 ? (
        <div className="text-center py-12">
          <Bookmark className="w-12 h-12 mx-auto text-lsc-dark/20 dark:text-lsc-cream/20 mb-4" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
            No saved books yet
          </p>
          <p className="text-sm text-lsc-dark/50 dark:text-lsc-cream/50">
            Click the bookmark icon on any book to save it for later.
          </p>
          <Link
            to="/indie"
            className="mt-4 inline-block text-lsc-rose underline hover:text-lsc-rose/80"
          >
            Browse catalog
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {books.map((ebook: BookDetailPublic) => (
            <div
              key={ebook.id}
              className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-4 flex gap-4"
            >
              <div className="w-16 h-24 bg-lsc-cream dark:bg-lsc-brown rounded-lg flex items-center justify-center flex-shrink-0 overflow-hidden">
                {ebook.cover_url ? (
                  <img
                    src={ebook.cover_url}
                    alt={`Cover of ${ebook.title}`}
                    className="w-full h-full object-cover"
                    loading="lazy"
                  />
                ) : (
                  <BookOpen className="w-6 h-6 text-lsc-rose/50" aria-hidden="true" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <Link
                  to={`/indie/book/${generateSlug(ebook.title, ebook.id)}`}
                  className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream hover:text-lsc-rose truncate block"
                >
                  {ebook.title}
                </Link>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  by {ebook.author_pen_name}
                </p>
                {ebook.genre && (
                  <span className="text-xs px-2 py-0.5 mt-1 inline-block bg-lsc-cream dark:bg-lsc-brown text-lsc-dark/70 dark:text-lsc-cream/70 rounded">
                    {ebook.genre}
                  </span>
                )}
              </div>
              <BookmarkButton ebookId={ebook.id} title={ebook.title} />
            </div>
          ))}
        </div>
      )}
    </PageContainer>
  )
}
