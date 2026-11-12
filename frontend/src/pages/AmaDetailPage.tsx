/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * AMA Detail / Live Page
 * Route: /amas/:sessionId (public, with auth-gated interactions)
 *
 * Shows an individual AMA session with its Q&A, with live updates via
 * polling while the session is live, question submission, and upvoting.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useParams, Link, Navigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  ArrowLeft,
  AlertCircle,
  ChevronUp,
  Clock,
  Loader2,
  LogIn,
  MessageCircle,
  Mic,
  Radio,
  Send,
  Star,
  User,
  CheckCircle2,
  Archive,
  Calendar,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { clsx } from '@/utils/helpers'
import { useAuth } from '@/contexts/AuthContext'
import { fetchApi, type RequestOptions } from '@/lib/api-client'
import { getAccessToken } from '@/utils/tokenStore'
import { t } from '@/i18n'
import { useBranding } from '@/contexts/BrandingContext'

// ---------------------------------------------------------------------------
// Types — mirrors MetisLib Pydantic schemas
// ---------------------------------------------------------------------------

interface AuthorSummary {
  indie_author_id: number | null
  pen_name: string | null
  bio: string | null
  profile_image_url: string | null
  guest_author_name: string | null
  guest_author_bio: string | null
  guest_author_photo_url: string | null
}

interface AmaQuestion {
  id: number
  question_text: string
  patron_display_name: string | null
  moderation_status: string
  trust_auto_approved: boolean
  answer_text: string | null
  answered_at: string | null
  upvote_count: number
  is_featured: boolean
  display_order: number | null
  patron_has_upvoted: boolean
  created_at: string
}

interface AmaSession {
  id: number
  library_id: number
  status: string // 'upcoming' | 'live' | 'grace_period' | 'archived'
  title: string
  description: string | null
  scheduled_start: string
  scheduled_end: string | null
  grace_period_hours: number
  grace_period_ends_at: string | null
  max_questions_per_patron: number
  total_questions: number
  total_answered: number
  author: AuthorSummary
  created_by_name: string | null
  created_at: string
  updated_at: string
}

interface AmaDetailResponse {
  session: AmaSession
  questions: AmaQuestion[]
}

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

function authOpts(extra?: Partial<RequestOptions>): RequestOptions {
  const token = getAccessToken()
  return { ...(token ? { token } : {}), ...extra } as RequestOptions
}

async function getSessionDetail(sessionId: number): Promise<AmaDetailResponse> {
  return fetchApi<AmaDetailResponse>(`/amas/sessions/${sessionId}`, authOpts())
}

async function submitQuestion(
  sessionId: number,
  questionText: string,
  displayName?: string,
): Promise<AmaQuestion> {
  return fetchApi<AmaQuestion>(`/amas/sessions/${sessionId}/questions`, {
    method: 'POST',
    body: JSON.stringify({
      question_text: questionText,
      ...(displayName ? { display_name: displayName } : {}),
    }),
    ...authOpts(),
  })
}

async function toggleUpvote(
  questionId: number,
): Promise<{ upvoted: boolean; upvote_count: number }> {
  return fetchApi<{ upvoted: boolean; upvote_count: number }>(
    `/amas/questions/${questionId}/upvote`,
    { method: 'POST', ...authOpts() },
  )
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const STATUS_META: Record<string, { label: string; color: string; icon: typeof Radio }> = {
  upcoming: { label: 'Upcoming', color: 'bg-status-info-500/10 text-status-info-700 dark:text-status-info-300', icon: Calendar },
  live: { label: 'Live Now', color: 'bg-status-danger-500/10 text-status-danger-600 dark:text-status-danger-400', icon: Radio },
  grace_period: { label: 'Grace Period', color: 'bg-status-warning-500/10 text-status-warning-700 dark:text-status-warning-300', icon: Clock },
  archived: { label: 'Archived', color: 'bg-earth-200/60 text-lsc-dark/70 dark:bg-earth-700/60 dark:text-lsc-cream/60', icon: Archive },
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString(undefined, {
    hour: 'numeric',
    minute: '2-digit',
  })
}

function formatRelativeTime(iso: string): string {
  const target = new Date(iso).getTime()
  const now = Date.now()
  const diff = target - now

  if (diff <= 0) return 'now'

  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (days > 0) return `${days}d ${hours % 24}h`
  if (hours > 0) return `${hours}h ${minutes % 60}m`
  if (minutes > 0) return `${minutes}m`
  return `${seconds}s`
}

function getAuthorName(author: AuthorSummary): string {
  return author.pen_name || author.guest_author_name || 'Author'
}

function getAuthorPhoto(author: AuthorSummary): string | null {
  return author.profile_image_url || author.guest_author_photo_url || null
}

function getAuthorBio(author: AuthorSummary): string | null {
  return author.bio || author.guest_author_bio || null
}

function isAcceptingQuestions(status: string): boolean {
  return status === 'live' || status === 'grace_period'
}

function isInteractive(status: string): boolean {
  return status !== 'archived'
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function CountdownBanner({ scheduledStart }: { scheduledStart: string }) {
  const [timeLeft, setTimeLeft] = useState(formatRelativeTime(scheduledStart))
  const [isPast, setIsPast] = useState(() => new Date(scheduledStart).getTime() <= Date.now())

  useEffect(() => {
    const iv = setInterval(() => {
      setTimeLeft(formatRelativeTime(scheduledStart))
      setIsPast(new Date(scheduledStart).getTime() <= Date.now())
    }, 1000)
    return () => clearInterval(iv)
  }, [scheduledStart])

  return (
    <div className="flex items-center gap-3 rounded-xl bg-status-info-500/10 dark:bg-status-info-900/20 border border-status-info-300/30 dark:border-status-info-700/30 px-5 py-4">
      <Clock className="w-5 h-5 text-status-info-600 dark:text-status-info-400 flex-shrink-0" />
      <div>
        <p className="text-sm font-medium text-status-info-800 dark:text-status-info-200">
          {isPast ? 'Starting soon' : `Starts in ${timeLeft}`}
        </p>
        <p className="text-xs text-status-info-700/70 dark:text-status-info-300/70 mt-0.5">
          {formatDate(scheduledStart)} at {formatTime(scheduledStart)}
        </p>
      </div>
    </div>
  )
}

function LiveIndicator() {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="relative flex h-2.5 w-2.5">
        <span className="motion-safe:animate-ping absolute inline-flex h-full w-full rounded-full bg-status-danger-500 opacity-75" />
        <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-status-danger-600" />
      </span>
      <span className="text-xs font-semibold text-status-danger-600 dark:text-status-danger-400 uppercase tracking-wide">
        Live
      </span>
    </span>
  )
}

function QuestionCard({
  question,
  canInteract,
  user,
  onUpvote,
  upvotingId,
}: {
  question: AmaQuestion
  canInteract: boolean
  user: { first_name: string } | null
  onUpvote: (questionId: number) => void
  upvotingId: number | null
}) {
  const isAnswered = !!question.answer_text
  const isUpvoting = upvotingId === question.id

  return (
    <div
      className={clsx(
        'rounded-xl border p-4 sm:p-5 transition-all',
        isAnswered
          ? 'bg-emerald-50/50 dark:bg-emerald-950/20 border-emerald-200/50 dark:border-emerald-800/30'
          : 'bg-lsc-white dark:bg-earth-800/50 border-lsc-border dark:border-earth-700/50',
        question.is_featured && 'ring-2 ring-status-warning-400/40 dark:ring-status-warning-500/30',
      )}
    >
      {/* Featured badge */}
      {question.is_featured && (
        <div className="flex items-center gap-1 mb-2">
          <Star className="w-3.5 h-3.5 text-status-warning-500 fill-status-warning-500" />
          <span className="text-xs font-medium text-status-warning-700 dark:text-status-warning-400">Featured</span>
        </div>
      )}

      <div className="flex gap-3 sm:gap-4">
        {/* Upvote column */}
        <div className="flex flex-col items-center gap-1 flex-shrink-0 min-w-[40px]">
          <button
            onClick={() => onUpvote(question.id)}
            disabled={!canInteract || !user || isUpvoting}
            aria-label={`${question.patron_has_upvoted ? 'Remove upvote from' : 'Upvote'} question`}
            aria-pressed={question.patron_has_upvoted}
            className={clsx(
              'flex items-center justify-center w-9 h-9 rounded-lg transition-all',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose/50',
              question.patron_has_upvoted
                ? 'bg-lsc-rose/10 text-lsc-rose dark:bg-lsc-rose/20'
                : canInteract && user
                  ? 'hover:bg-lsc-rose/10 text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-rose'
                  : 'text-lsc-dark/20 dark:text-lsc-cream/20 cursor-default',
              isUpvoting && 'opacity-50',
            )}
          >
            {isUpvoting ? (
              <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
            ) : (
              <ChevronUp className="w-5 h-5" />
            )}
          </button>
          <span
            className={clsx(
              'text-sm font-semibold tabular-nums',
              question.patron_has_upvoted
                ? 'text-lsc-rose'
                : 'text-lsc-dark/70 dark:text-lsc-cream/50',
            )}
          >
            {question.upvote_count}
          </span>
        </div>

        {/* Content column */}
        <div className="flex-1 min-w-0">
          <p className="text-sm sm:text-base text-lsc-dark dark:text-lsc-cream leading-relaxed">
            {question.question_text}
          </p>

          <div className="flex items-center gap-2 mt-2">
            <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50">
              {question.patron_display_name || 'Anonymous'}
            </span>
            <span className="text-xs text-lsc-dark/30 dark:text-lsc-cream/60">
              {formatTime(question.created_at)}
            </span>
          </div>

          {/* Author answer */}
          {isAnswered && (
            <div className="mt-3 pl-3 border-l-2 border-emerald-400/50 dark:border-emerald-500/40">
              <div className="flex items-center gap-1.5 mb-1">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                <span className="text-xs font-medium text-emerald-700 dark:text-emerald-400">
                  Author's Answer
                </span>
                {question.answered_at && (
                  <span className="text-xs text-emerald-600/60 dark:text-emerald-400/60">
                    {formatTime(question.answered_at)}
                  </span>
                )}
              </div>
              <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80 leading-relaxed">
                {question.answer_text}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function QuestionForm({
  sessionId,
  user,
  maxLength = 2000,
  onSubmitted,
}: {
  sessionId: number
  user: { first_name: string } | null
  maxLength?: number
  onSubmitted: () => void
}) {
  const [text, setText] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const mutation = useMutation({
    mutationFn: () => submitQuestion(sessionId, text.trim(), user?.first_name),
    onSuccess: () => {
      setText('')
      toast.success(t('toast.amaDetail.questionSubmitted'))
      onSubmitted()
      if (textareaRef.current) textareaRef.current.focus()
    },
    onError: (err: Error) => {
      toast.error(err.message || t('toast.amaDetail.couldNotSubmitQuestion'))
    },
  })

  const charCount = text.length
  const canSubmit = charCount > 0 && charCount <= maxLength && !mutation.isPending

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (canSubmit) mutation.mutate()
  }

  if (!user) {
    return (
      <div className="rounded-xl border border-lsc-border dark:border-earth-700/50 bg-lsc-white dark:bg-earth-800/50 p-5 text-center">
        <LogIn className="w-6 h-6 mx-auto mb-2 text-lsc-rose/70" />
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
          Sign in to ask a question
        </p>
        <Link
          to="/login"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-lsc-rose text-white text-sm font-medium hover:bg-lsc-rose-dark transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose/50"
        >
          <LogIn className="w-4 h-4" />
          Sign In
        </Link>
      </div>
    )
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-xl border border-lsc-border dark:border-earth-700/50 bg-lsc-white dark:bg-earth-800/50 p-4 sm:p-5"
    >
      <label htmlFor="ama-question" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
        Your Question
      </label>
      <textarea
        ref={textareaRef}
        id="ama-question"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={t('placeholder.amaDetail.whatWouldYouLike')}
        maxLength={maxLength}
        rows={3}
        className={clsx(
          'w-full resize-none rounded-lg border px-3 py-2.5 text-sm',
          'bg-lsc-cream/30 dark:bg-earth-900/40',
          'border-lsc-border dark:border-earth-700/50',
          'text-lsc-dark dark:text-lsc-cream',
          'placeholder:text-lsc-dark/70 dark:placeholder:text-lsc-cream/40',
          'focus:outline-none focus:ring-2 focus:ring-lsc-rose/40 focus:border-lsc-rose/40',
          'transition-colors',
        )}
      />
      <div className="flex items-center justify-between mt-3">
        <span
          className={clsx(
            'text-xs tabular-nums',
            charCount > maxLength * 0.9
              ? 'text-status-danger-500'
              : 'text-lsc-dark/70 dark:text-lsc-cream/60',
          )}
        >
          {charCount} / {maxLength}
        </span>
        <button
          type="submit"
          disabled={!canSubmit}
          className={clsx(
            'inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose/50',
            canSubmit
              ? 'bg-lsc-rose text-white hover:bg-lsc-rose-dark'
              : 'bg-lsc-dark/10 dark:bg-lsc-cream/10 text-lsc-dark/30 dark:text-lsc-cream/60 cursor-not-allowed',
          )}
        >
          {mutation.isPending ? (
            <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
          ) : (
            <Send className="w-4 h-4" />
          )}
          Submit
        </button>
      </div>
    </form>
  )
}

// ---------------------------------------------------------------------------
// Main Page Component
// ---------------------------------------------------------------------------

export default function AmaDetailPage(): React.ReactElement {
  const branding = useBranding()
  const { sessionId } = useParams<{ sessionId: string }>()
  const id = Number(sessionId)

  const { user } = useAuth()

  // Upvote in-flight tracking
  const [upvotingId, setUpvotingId] = useState<number | null>(null)

  // ------- Data fetching -------
  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<AmaDetailResponse>({
    queryKey: ['ama-session', id],
    queryFn: () => getSessionDetail(id),
    enabled: !isNaN(id),
    staleTime: 30_000,
    refetchInterval: (query) => {
      // Poll while the session is live. (No SSE endpoint exists on the
      // backend; polling IS the live-update mechanism.)
      const status = query.state.data?.session?.status
      if (status === 'live' || status === 'grace_period') {
        return 15_000
      }
      return false
    },
  })

  const session = data?.session
  const questions = data?.questions

  // ------- Sort questions: featured first, then by upvotes desc -------
  const sortedQuestions = useMemo(() => {
    if (!questions) return []
    return [...questions]
      .filter((q) => q.moderation_status === 'approved')
      .sort((a, b) => {
        // Featured first
        if (a.is_featured !== b.is_featured) return a.is_featured ? -1 : 1
        // Answered first (optional, nice for archives)
        if (!!a.answer_text !== !!b.answer_text) return a.answer_text ? -1 : 1
        // Then by upvotes descending
        if (b.upvote_count !== a.upvote_count) return b.upvote_count - a.upvote_count
        // Tie-break by creation time
        return new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      })
  }, [questions])

  // ------- Live updates -------
  // The backend AMA router (/api/v1/amas/*) is a thin proxy to MetisLib and
  // exposes no SSE stream endpoint, so we do not open an EventSource here.
  // Live updates are driven by the refetchInterval polling above, which runs
  // every 15s while the session is live or in grace_period.

  // ------- Upvote handler -------
  const handleUpvote = useCallback(
    async (questionId: number) => {
      if (!user) {
        toast.error(t('toast.amaDetail.signInToUpvote'))
        return
      }
      setUpvotingId(questionId)
      try {
        await toggleUpvote(questionId)
        // Refetch to get updated state
        await refetch()
      } catch (err) {
        toast.error(err instanceof Error ? err.message : t('toast.amaDetail.couldNotToggleUpvote'))
      } finally {
        setUpvotingId(null)
      }
    },
    [user, refetch],
  )

  // ------- Page title -------
  useEffect(() => {
    if (session) {
      document.title = `${session.title} — AMA | ${branding.library_short_name}`
    }
    return () => {
      document.title = branding.library_name
    }
  }, [session])

  // Guard against invalid route params (kept below the hooks so hook order
  // stays stable; the query above is enabled:!isNaN(id) so it never fetches).
  if (!sessionId || isNaN(id)) {
    return <Navigate to="/amas" replace />
  }

  // ------- Loading state -------
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
      </div>
    )
  }

  // ------- Error state -------
  if (isError || !session) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4 px-4 text-center">
        <AlertCircle className="w-12 h-12 text-status-danger-500/70" />
        <h1 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          AMA Session Not Found
        </h1>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60 max-w-md">
          {(error as Error)?.message || 'This session may have been removed or is not yet available.'}
        </p>
        <Link
          to="/events"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-lsc-rose text-white text-sm font-medium hover:bg-lsc-rose-dark transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Events
        </Link>
      </div>
    )
  }

  const fallbackMeta = { label: 'Upcoming', color: 'bg-status-info-500/10 text-status-info-700 dark:text-status-info-300', icon: Calendar }
  const statusMeta = STATUS_META[session.status] ?? fallbackMeta
  const StatusIcon = statusMeta.icon
  const authorName = getAuthorName(session.author)
  const authorPhoto = getAuthorPhoto(session.author)
  const authorBio = getAuthorBio(session.author)
  const canAsk = isAcceptingQuestions(session.status)
  const canInteract = isInteractive(session.status)
  const answeredCount = sortedQuestions.filter((q) => !!q.answer_text).length

  return (
    <div className="max-w-3xl mx-auto space-y-6 pb-12">
      {/* Back link */}
      <Link
        to="/events"
        className="inline-flex items-center gap-1 text-sm text-lsc-rose hover:underline"
      >
        <ArrowLeft className="w-4 h-4" />
        Events
      </Link>

      {/* Session header */}
      <header className="space-y-4">
        {/* Status badge row */}
        <div className="flex flex-wrap items-center gap-3">
          <span
            className={clsx(
              'inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold',
              statusMeta.color,
            )}
          >
            {session.status === 'live' ? (
              <LiveIndicator />
            ) : (
              <>
                <StatusIcon className="w-3.5 h-3.5" />
                {statusMeta.label}
              </>
            )}
          </span>

        </div>

        {/* Title */}
        <h1 className="text-2xl sm:text-3xl font-serif font-bold text-lsc-dark dark:text-lsc-cream leading-tight">
          {session.title}
        </h1>

        {/* Author card */}
        <div className="flex items-center gap-3">
          {authorPhoto ? (
            <img
              src={authorPhoto}
              alt={authorName}
              className="w-12 h-12 rounded-full object-cover border-2 border-lsc-border dark:border-earth-700"
            />
          ) : (
            <div className="w-12 h-12 rounded-full bg-lsc-rose/10 dark:bg-lsc-rose/20 flex items-center justify-center">
              <User className="w-6 h-6 text-lsc-rose/60" />
            </div>
          )}
          <div>
            <p className="font-medium text-lsc-dark dark:text-lsc-cream">
              {authorName}
            </p>
            {authorBio && (
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 line-clamp-1" title={authorBio}>
                {authorBio}
              </p>
            )}
          </div>
        </div>

        {/* Description */}
        {session.description && (
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 leading-relaxed">
            {session.description}
          </p>
        )}

        {/* Time & stats */}
        <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/50">
          <span className="flex items-center gap-1">
            <Calendar className="w-3.5 h-3.5" />
            {formatDate(session.scheduled_start)}
          </span>
          <span className="flex items-center gap-1">
            <Clock className="w-3.5 h-3.5" />
            {formatTime(session.scheduled_start)}
            {session.scheduled_end && ` — ${formatTime(session.scheduled_end)}`}
          </span>
          <span className="flex items-center gap-1">
            <MessageCircle className="w-3.5 h-3.5" />
            {session.total_questions} question{session.total_questions !== 1 ? 's' : ''}
          </span>
          {session.total_answered > 0 && (
            <span className="flex items-center gap-1">
              <Mic className="w-3.5 h-3.5" />
              {session.total_answered} answered
            </span>
          )}
        </div>
      </header>

      {/* Countdown for upcoming sessions */}
      {session.status === 'upcoming' && (
        <CountdownBanner scheduledStart={session.scheduled_start} />
      )}

      {/* Grace period notice */}
      {session.status === 'grace_period' && session.grace_period_ends_at && (
        <div className="flex items-center gap-3 rounded-xl bg-status-warning-500/10 dark:bg-status-warning-900/20 border border-status-warning-300/30 dark:border-status-warning-700/30 px-5 py-4">
          <Clock className="w-5 h-5 text-status-warning-600 dark:text-status-warning-400 flex-shrink-0" />
          <div>
            <p className="text-sm font-medium text-status-warning-800 dark:text-status-warning-200">
              Grace period — questions still open
            </p>
            <p className="text-xs text-status-warning-700/70 dark:text-status-warning-300/70 mt-0.5">
              Closes {formatDate(session.grace_period_ends_at)} at {formatTime(session.grace_period_ends_at)}
            </p>
          </div>
        </div>
      )}

      {/* Archived notice */}
      {session.status === 'archived' && (
        <div className="flex items-center gap-3 rounded-xl bg-lsc-cream/50 dark:bg-earth-800/50 border border-lsc-border dark:border-earth-700/50 px-5 py-4">
          <Archive className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/60 flex-shrink-0" />
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
            This AMA has ended. Browse the questions and answers below.
          </p>
        </div>
      )}

      {/* Question form (only when accepting questions) */}
      {canAsk && (
        <section aria-label={t('aria.amaDetail.submitAQuestion')}>
          <QuestionForm
            sessionId={id}
            user={user}
            maxLength={2000}
            onSubmitted={() => refetch()}
          />
        </section>
      )}

      {/* Questions list */}
      <section aria-label={t('aria.amaDetail.questionsAndAnswers')}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
            Questions
            {sortedQuestions.length > 0 && (
              <span className="ml-2 text-sm font-normal text-lsc-dark/70 dark:text-lsc-cream/50">
                ({sortedQuestions.length})
              </span>
            )}
          </h2>
          {answeredCount > 0 && (
            <span className="text-xs text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" />
              {answeredCount} answered
            </span>
          )}
        </div>

        {sortedQuestions.length === 0 ? (
          <div className="text-center py-12 rounded-xl border border-dashed border-lsc-border dark:border-earth-700/50">
            <MessageCircle className="w-10 h-10 mx-auto mb-3 text-lsc-dark/20 dark:text-lsc-cream/20" />
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/50">
              {session.status === 'upcoming'
                ? 'Questions will appear once the session goes live.'
                : session.status === 'archived'
                  ? 'No questions were submitted for this session.'
                  : 'No questions yet — be the first to ask!'}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {sortedQuestions.map((q) => (
              <QuestionCard
                key={q.id}
                question={q}
                canInteract={canInteract}
                user={user}
                onUpvote={handleUpvote}
                upvotingId={upvotingId}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
