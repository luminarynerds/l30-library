/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Cohort opt-in + shared discussion thread for a learning path (V1).
 *
 * Privacy: only first names are rendered. Member listing is only shown
 * to opted-in members. Non-members see member count only.
 */
import * as Sentry from '@/lib/sentry-lazy'
import { useCallback, useEffect, useState } from 'react'
import toast from 'react-hot-toast'

import {
  getCohortStatus,
  joinCohort,
  leaveCohort,
  listCohortDiscussion,
  postCohortDiscussion,
  type CohortDiscussionPost,
  type CohortStatus,
} from '@/api/domains/learning/cohort-api'
import { Button } from '@/components/ui/Button'
import { friendlyErrorMessage } from '@/utils/friendlyError'

interface CohortPanelProps {
  pathId: number
  isAuthenticated: boolean
}

export default function CohortPanel({ pathId, isAuthenticated }: CohortPanelProps) {
  const [status, setStatus] = useState<CohortStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [posts, setPosts] = useState<CohortDiscussionPost[]>([])
  const [postsLoading, setPostsLoading] = useState(false)
  const [draft, setDraft] = useState('')

  const refreshStatus = useCallback(async () => {
    if (!isAuthenticated) {
      setLoading(false)
      return
    }
    try {
      setLoading(true)
      const data = await getCohortStatus(pathId)
      setStatus(data)
    } catch (err: unknown) {
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
    } finally {
      setLoading(false)
    }
  }, [pathId, isAuthenticated])

  const refreshPosts = useCallback(async () => {
    if (!isAuthenticated) return
    try {
      setPostsLoading(true)
      const data = await listCohortDiscussion(pathId)
      setPosts(data)
    } catch (err: unknown) {
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
    } finally {
      setPostsLoading(false)
    }
  }, [pathId, isAuthenticated])

  useEffect(() => {
    refreshStatus()
  }, [refreshStatus])

  useEffect(() => {
    if (status?.is_member) {
      refreshPosts()
    }
  }, [status?.is_member, refreshPosts])

  const handleJoin = async () => {
    if (busy) return
    try {
      setBusy(true)
      const next = await joinCohort(pathId)
      setStatus(next)
      toast.success("You're in the cohort.")
    } catch (err: unknown) {
      toast.error(friendlyErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const handleLeave = async () => {
    if (busy) return
    try {
      setBusy(true)
      const next = await leaveCohort(pathId)
      setStatus(next)
      setPosts([])
      toast.success('You left the cohort.')
    } catch (err: unknown) {
      toast.error(friendlyErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const handlePost = async () => {
    const trimmed = draft.trim()
    if (!trimmed || busy) return
    try {
      setBusy(true)
      const created = await postCohortDiscussion(pathId, trimmed)
      setPosts((prev) => [...prev, created])
      setDraft('')
    } catch (err: unknown) {
      toast.error(friendlyErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  if (!isAuthenticated) {
    return null
  }

  return (
    <section
      aria-labelledby="cohort-heading"
      className="mt-6 bg-lsc-white dark:bg-earth-800 rounded-lg shadow-md p-6 border border-lsc-border dark:border-earth-700 max-w-4xl mx-auto"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2
            id="cohort-heading"
            className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream"
          >
            Cohort
          </h2>
          <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80 mt-1">
            Opt in to learn alongside other patrons working through this path.
            {status && (
              <>
                {' '}
                <span className="font-medium">
                  {status.member_count}{' '}
                  {status.member_count === 1 ? 'learner' : 'learners'}
                </span>{' '}
                in this cohort.
              </>
            )}
          </p>
        </div>
        {!loading && status && (
          status.is_member ? (
            <Button variant="tertiary" onClick={handleLeave} disabled={busy}>
              Leave cohort
            </Button>
          ) : (
            <Button onClick={handleJoin} disabled={busy}>
              Join cohort
            </Button>
          )
        )}
      </div>

      {status?.is_member && (
        <>
          {status.members.length > 1 && (
            <div className="mt-4">
              <h3 className="text-sm font-medium text-lsc-dark/80 dark:text-lsc-cream/80 mb-2">
                Learners in this cohort
              </h3>
              <ul className="flex flex-wrap gap-2">
                {status.members.map((m) => (
                  <li
                    key={m.user_id}
                    className="px-3 py-1 rounded-full bg-earth-100 dark:bg-earth-700 text-sm text-lsc-dark dark:text-lsc-cream"
                  >
                    {m.first_name || 'Member'}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="mt-6">
            <h3 className="text-sm font-medium text-lsc-dark/80 dark:text-lsc-cream/80 mb-2">
              Discussion
            </h3>
            {postsLoading ? (
              <p className="text-sm text-lsc-dark/60 dark:text-lsc-cream/60">
                Loading discussion…
              </p>
            ) : posts.length === 0 ? (
              <p className="text-sm text-lsc-dark/60 dark:text-lsc-cream/60">
                No posts yet. Start the conversation.
              </p>
            ) : (
              <ul className="space-y-3">
                {posts.map((p) => (
                  <li
                    key={p.id}
                    className="rounded border border-lsc-border dark:border-earth-700 p-3"
                  >
                    <div className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60">
                      <span className="font-medium">{p.author_display_name || 'Member'}</span>{' '}
                      <time dateTime={p.created_at}>
                        {new Date(p.created_at).toLocaleString()}
                      </time>
                    </div>
                    <p className="mt-1 whitespace-pre-wrap text-lsc-dark dark:text-lsc-cream">
                      {p.body}
                    </p>
                  </li>
                ))}
              </ul>
            )}

            <div className="mt-4">
              <label htmlFor="cohort-post-body" className="sr-only">
                New post
              </label>
              <textarea
                id="cohort-post-body"
                className="w-full rounded border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 p-2 text-sm text-lsc-dark dark:text-lsc-cream"
                rows={3}
                placeholder="Share a question or insight with the cohort..."
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                maxLength={4000}
              />
              <div className="mt-2 flex justify-end">
                <Button onClick={handlePost} disabled={busy || !draft.trim()}>
                  Post
                </Button>
              </div>
            </div>
          </div>
        </>
      )}
    </section>
  )
}
