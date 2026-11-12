/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Bookmark toggle button for indie ebooks (save for later).
 * Shows a bookmark icon that toggles saved state with optimistic UI.
 */
import { useState, useCallback } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Bookmark } from 'lucide-react'
import { clsx } from '@/utils/helpers'
import { bookmarkEbook, unbookmarkEbook, getBookmarkStatus } from '@/api/indie-engagement-api'
import toast from 'react-hot-toast'

interface BookmarkButtonProps {
  ebookId: number
  title?: string
  className?: string
}

export default function BookmarkButton({ ebookId, title, className }: BookmarkButtonProps) {
  const queryClient = useQueryClient()
  const [optimistic, setOptimistic] = useState<boolean | null>(null)

  const { data } = useQuery({
    queryKey: ['indie-bookmark-status', ebookId],
    queryFn: () => getBookmarkStatus(ebookId),
    staleTime: 60_000,
  })

  const isBookmarked = optimistic ?? data?.bookmarked ?? false

  const toggleMutation = useMutation({
    mutationFn: async () => {
      if (isBookmarked) {
        return unbookmarkEbook(ebookId)
      } else {
        return bookmarkEbook(ebookId)
      }
    },
    onMutate: () => {
      setOptimistic(!isBookmarked)
    },
    onSuccess: (result) => {
      setOptimistic(null)
      queryClient.setQueryData(['indie-bookmark-status', ebookId], { bookmarked: result.bookmarked })
      queryClient.invalidateQueries({ queryKey: ['indie-bookmarks'] })
    },
    onError: () => {
      setOptimistic(null)
      toast.error('Failed to update bookmark')
    },
  })

  const handleClick = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    toggleMutation.mutate()
  }, [toggleMutation])

  return (
    <button
      onClick={handleClick}
      disabled={toggleMutation.isPending}
      aria-label={isBookmarked ? `Remove ${title || 'book'} from saved list` : `Save ${title || 'book'} for later`}
      aria-pressed={isBookmarked}
      className={clsx(
        'p-1.5 rounded-lg transition-colors',
        isBookmarked
          ? 'text-lsc-rose bg-lsc-rose/10 hover:bg-lsc-rose/20'
          : 'text-lsc-dark/40 dark:text-lsc-cream/40 hover:text-lsc-rose hover:bg-lsc-rose/5',
        className,
      )}
      title={isBookmarked ? 'Remove from saved' : 'Save for later'}
    >
      <Bookmark
        className={clsx('w-4 h-4', isBookmarked && 'fill-current')}
        aria-hidden="true"
      />
    </button>
  )
}
