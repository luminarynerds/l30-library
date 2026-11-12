/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * IndieFollowButton -- patron-side follow toggle for an indie author.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Bell, BellOff, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuth } from '@/contexts/AuthContext'
import { fetchApi } from '@/lib/api-client'
import { clsx } from '@/utils/helpers'

interface FollowStatus {
  indie_author_id: number
  following: boolean
  follower_count: number
}

interface Props {
  authorId: number
  authorName: string
  className?: string
}

export default function IndieFollowButton({
  authorId,
  authorName,
  className,
}: Props): React.ReactElement {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const { data, isLoading } = useQuery<FollowStatus>({
    queryKey: ['indie-author-follow', authorId],
    queryFn: () => fetchApi<FollowStatus>(`/indie/authors/${authorId}/follow`),
    enabled: !!user,
    staleTime: 60_000,
  })

  const follow = useMutation({
    mutationFn: () =>
      fetchApi<FollowStatus>(`/indie/authors/${authorId}/follow`, { method: 'POST' }),
    onSuccess: (next) => {
      queryClient.setQueryData(['indie-author-follow', authorId], next)
      toast.success(`Following ${authorName}`)
    },
    onError: () => toast.error('Unable to follow right now'),
  })

  const unfollow = useMutation({
    mutationFn: async () => {
      await fetchApi(`/indie/authors/${authorId}/follow`, { method: 'DELETE' })
    },
    onSuccess: () => {
      queryClient.setQueryData<FollowStatus>(['indie-author-follow', authorId], (prev) =>
        prev ? { ...prev, following: false, follower_count: Math.max(0, prev.follower_count - 1) } : prev,
      )
      toast.success(`Unfollowed ${authorName}`)
    },
    onError: () => toast.error('Unable to unfollow right now'),
  })

  if (!user) {
    return (
      <button
        type="button"
        onClick={() => navigate(`/login?next=${encodeURIComponent(window.location.pathname)}`)}
        className={clsx(
          'inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg border border-lsc-rose text-lsc-rose hover:bg-lsc-rose/10',
          className,
        )}
        aria-label={`Sign in to follow ${authorName}`}
      >
        <Bell className="w-4 h-4" aria-hidden="true" />
        Sign in to follow
      </button>
    )
  }

  const isPending = isLoading || follow.isPending || unfollow.isPending
  const following = data?.following ?? false

  return (
    <button
      type="button"
      onClick={() => (following ? unfollow.mutate() : follow.mutate())}
      disabled={isPending}
      aria-pressed={following}
      aria-label={following ? `Unfollow ${authorName}` : `Follow ${authorName}`}
      className={clsx(
        'inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg disabled:opacity-50',
        following
          ? 'border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-800'
          : 'bg-lsc-rose text-white hover:bg-lsc-rose/90',
        className,
      )}
    >
      {isPending ? (
        <Loader2 className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" />
      ) : following ? (
        <BellOff className="w-4 h-4" aria-hidden="true" />
      ) : (
        <Bell className="w-4 h-4" aria-hidden="true" />
      )}
      {following ? 'Following' : 'Follow'}
      {data && data.follower_count > 0 && (
        <span className="text-xs opacity-80">
          ({data.follower_count})
        </span>
      )}
    </button>
  )
}
