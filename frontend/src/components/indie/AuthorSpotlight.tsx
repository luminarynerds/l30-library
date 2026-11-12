/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Author Spotlight Section
 * Displays a featured/random indie author with bio and link to their books.
 */
import { Link } from "react-router-dom"
import { User, BookOpen, ChevronRight } from "lucide-react"
import IndieFollowButton from "@/components/indie/IndieFollowButton"
import { penNameToSlug } from "@/api/indie-catalog-api"

export interface FeaturedAuthor {
  id: number
  pen_name: string
  bio: string
  profile_image_url: string | null
  book_count: number
}

export default function AuthorSpotlight({
  author,
}: {
  author: FeaturedAuthor
}): React.ReactElement {
  const authorSlug = penNameToSlug(author.pen_name)

  return (
    <section aria-label="Author Spotlight">
      <div className="flex items-center gap-2 mb-4">
        <User className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
        <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          Author Spotlight
        </h2>
      </div>

      <div className="bg-lsc-cream/50 dark:bg-earth-800 rounded-xl p-6 border border-lsc-border/30 dark:border-earth-700">
        <div className="flex items-start gap-4">
          {/* Author avatar */}
          <div className="w-14 h-14 rounded-full bg-lsc-rose/10 dark:bg-lsc-rose/20 flex items-center justify-center flex-shrink-0 overflow-hidden">
            {author.profile_image_url ? (
              <img
                src={author.profile_image_url}
                alt={author.pen_name}
                className="w-full h-full object-cover rounded-full"
              />
            ) : (
              <User className="w-7 h-7 text-lsc-rose" aria-hidden="true" />
            )}
          </div>

          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              {author.pen_name}
            </h3>

            {author.book_count > 0 && (
              <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 flex items-center gap-1 mt-0.5">
                <BookOpen className="w-3 h-3" aria-hidden="true" />
                {author.book_count} {author.book_count === 1 ? "book" : "books"} available
              </p>
            )}

            <p className="mt-2 text-sm text-lsc-dark/80 dark:text-lsc-cream/80 leading-relaxed line-clamp-3">
              {author.bio}
            </p>

            <div className="mt-3 flex flex-wrap items-center gap-3">
              <Link
                to={`/indie/author/${authorSlug}`}
                className="inline-flex items-center gap-1 text-sm font-medium text-lsc-rose hover:text-lsc-rose/80 hover:underline"
              >
                View all books by {author.pen_name}
                <ChevronRight className="w-4 h-4" aria-hidden="true" />
              </Link>
              <IndieFollowButton authorId={author.id} authorName={author.pen_name} />
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
