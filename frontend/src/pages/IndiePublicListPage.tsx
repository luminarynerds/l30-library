/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect } from "react"
import { useParams, Link } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { Globe, BookOpen, Loader2, User } from "lucide-react"
import { getSharedIndieReadingList } from "@/api/indie-engagement-api"
import { useBranding } from "@/contexts/BrandingContext"
import PageContainer from '@/components/layout/PageContainer'

export default function IndiePublicListPage() {
  const { token } = useParams<{ token: string }>()
  const branding = useBranding()

  useEffect(() => {
    document.title = "Shared Reading List | Indie Catalog"
    return () => { document.title = branding.library_name }
  }, [branding.library_name])

  const { data: list, isLoading, error } = useQuery({
    queryKey: ["indie-shared-list", token],
    queryFn: () => getSharedIndieReadingList(token!),
    enabled: !!token,
  })

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
      </div>
    )
  }

  if (error || !list) {
    return (
      <PageContainer className="py-8 text-center">
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          This list is not available or may have been made private.
        </p>
        <Link to="/indie" className="text-lsc-rose underline hover:text-lsc-rose/80">
          Browse the catalog
        </Link>
      </PageContainer>
    )
  }

  return (
    <PageContainer className="py-8">
      <div className="mb-6">
        <div className="flex items-center gap-2 text-xs text-lsc-dark/50 dark:text-lsc-cream/50 mb-2">
          <Globe className="w-3 h-3" />
          <span>Shared reading list</span>
        </div>
        <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          {list.name}
        </h1>
        {list.description && (
          <p className="text-lsc-dark/60 dark:text-lsc-cream/60 mt-1">{list.description}</p>
        )}
        <div className="flex items-center gap-1.5 mt-2 text-sm text-lsc-dark/50 dark:text-lsc-cream/50">
          <User className="w-3.5 h-3.5" />
          <span>by {list.creator_name}</span>
          <span className="mx-1">&middot;</span>
          <span>{list.items.length} {list.items.length === 1 ? "book" : "books"}</span>
        </div>
      </div>

      {list.items.length === 0 ? (
        <div className="text-center py-12">
          <BookOpen className="w-12 h-12 mx-auto text-lsc-dark/20 dark:text-lsc-cream/20 mb-4" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">This list is empty</p>
        </div>
      ) : (
        <div className="space-y-3">
          {list.items.map((item) => (
            <div
              key={item.ebook_id}
              className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-4 flex items-center gap-4"
            >
              <div className="w-10 h-14 bg-lsc-cream dark:bg-lsc-brown rounded flex items-center justify-center flex-shrink-0">
                <BookOpen className="w-5 h-5 text-lsc-rose/50" aria-hidden="true" />
              </div>
              <div className="flex-1 min-w-0">
                <Link
                  to={`/indie/book/${item.ebook_id}`}
                  className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream hover:text-lsc-rose block"
                >
                  Book #{item.ebook_id}
                </Link>
                {item.note && (
                  <p className="text-sm text-lsc-dark/60 dark:text-lsc-cream/60 truncate">{item.note}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </PageContainer>
  )
}
