/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from "react"
import { useParams, Link } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Globe, Lock, Trash2, Loader2, BookOpen, Copy, Check } from "lucide-react"
import {
  getIndieReadingList,
  updateIndieReadingList,
  removeFromIndieReadingList} from "@/api/indie-engagement-api"
import { useBranding } from "@/contexts/BrandingContext"
import PageContainer from '@/components/layout/PageContainer'

export default function IndieReadingListDetailPage() {
  const { id } = useParams<{ id: string }>()
  const listId = Number(id)
  const branding = useBranding()
  const queryClient = useQueryClient()
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    document.title = "Reading List | Indie Catalog"
    return () => { document.title = branding.library_name }
  }, [branding.library_name])

  const { data: list, isLoading } = useQuery({
    queryKey: ["indie-reading-list", listId],
    queryFn: () => getIndieReadingList(listId),
    enabled: !isNaN(listId),
  })

  const togglePublicMutation = useMutation({
    mutationFn: () => updateIndieReadingList(listId, { is_public: !list?.is_public }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["indie-reading-list", listId] })
      queryClient.invalidateQueries({ queryKey: ["indie-reading-lists"] })
    },
  })

  const removeMutation = useMutation({
    mutationFn: (ebookId: number) => removeFromIndieReadingList(listId, ebookId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["indie-reading-list", listId] })
      queryClient.invalidateQueries({ queryKey: ["indie-reading-lists"] })
    },
  })

  const handleCopyLink = () => {
    if (!list?.share_token) return
    const url = `${window.location.origin}/indie/lists/shared/${list.share_token}`
    navigator.clipboard.writeText(url)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
      </div>
    )
  }

  if (!list) {
    return (
      <PageContainer className="py-8 text-center">
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">List not found</p>
      </PageContainer>
    )
  }

  return (
    <PageContainer className="py-8">
      <div className="mb-6">
        <Link
          to="/indie/lists"
          className="text-sm text-lsc-rose hover:text-lsc-rose/80 mb-2 inline-block"
        >
          &larr; Back to My Lists
        </Link>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              {list.name}
            </h1>
            {list.description && (
              <p className="text-lsc-dark/60 dark:text-lsc-cream/60 mt-1">{list.description}</p>
            )}
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <button
              onClick={() => togglePublicMutation.mutate()}
              disabled={togglePublicMutation.isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-earth-300 dark:border-earth-600 rounded-lg hover:bg-earth-100 dark:hover:bg-earth-700 transition-colors text-lsc-dark dark:text-lsc-cream"
            >
              {list.is_public ? <Globe className="w-3.5 h-3.5" /> : <Lock className="w-3.5 h-3.5" />}
              {list.is_public ? "Public" : "Private"}
            </button>
            {list.is_public && list.share_token && (
              <button
                onClick={handleCopyLink}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors"
              >
                {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                {copied ? "Copied!" : "Copy Link"}
              </button>
            )}
          </div>
        </div>
      </div>

      {list.items.length === 0 ? (
        <div className="text-center py-12">
          <BookOpen className="w-12 h-12 mx-auto text-lsc-dark/20 dark:text-lsc-cream/20 mb-4" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
            This list is empty
          </p>
          <Link
            to="/indie"
            className="text-lsc-rose underline hover:text-lsc-rose/80"
          >
            Browse the catalog to add books
          </Link>
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
                <p className="text-xs text-lsc-dark/40 dark:text-lsc-cream/40">
                  Added {new Date(item.added_at).toLocaleDateString()}
                </p>
              </div>
              <button
                onClick={() => removeMutation.mutate(item.ebook_id)}
                disabled={removeMutation.isPending}
                className="p-2 text-lsc-dark/30 dark:text-lsc-cream/30 hover:text-status-danger-500 transition-colors"
                aria-label="Remove from list"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </PageContainer>
  )
}
