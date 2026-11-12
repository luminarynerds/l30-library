/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Calendar, MapPin, Users, CheckCircle, AlertTriangle, Loader2 } from 'lucide-react'
import { fetchApi } from '@/lib/api-client'
import { usePageMeta } from '@/hooks/usePageMeta'
import { useAuth } from '@/contexts/AuthContext'
import { TurnstileWidget } from '@/components/TurnstileWidget'
import PageContainer from '@/components/layout/PageContainer'

interface SeriesOccurrence {
  event_id: number
  start_time: string
  end_time: string | null
  location: string | null
  is_published: boolean
  max_attendees: number | null
  spots_remaining: number | null
  registration_required: boolean
}

interface SeriesDetail {
  series_id: string
  series_name: string
  description: string | null
  category: string | null
  audience: string | null
  min_age: number | null
  max_age: number | null
  presenters: Array<{ name: string; bio?: string | null }> | null
  recurrence_summary: string | null
  upcoming_count: number
  occurrences: SeriesOccurrence[]
}

interface SeriesRegistrationOutcome {
  event_id: number
  start_time: string
  status: 'registered' | 'already_registered' | 'waitlisted' | 'capacity_full' | 'error'
  registration_id: number | null
  waitlist_position: number | null
  error: string | null
}

interface SeriesRegistrationResponse {
  series_id: string
  series_name: string
  total_upcoming: number
  registered_count: number
  already_registered_count: number
  waitlisted_count: number
  failed_count: number
  outcomes: SeriesRegistrationOutcome[]
}

interface SeriesRegistrationCreate {
  patron_name: string
  patron_email: string
  patron_phone?: string
  reminder_requested?: boolean
  turnstile_token?: string
}

async function getSeries(seriesId: string): Promise<SeriesDetail> {
  return await fetchApi<SeriesDetail>(`/events/series/${encodeURIComponent(seriesId)}`)
}

async function registerForSeries(
  seriesId: string,
  payload: SeriesRegistrationCreate,
): Promise<SeriesRegistrationResponse> {
  return await fetchApi<SeriesRegistrationResponse>(
    `/events/series/${encodeURIComponent(seriesId)}/register`,
    { method: 'POST', body: payload },
  )
}

function formatDateTime(isoStr: string): string {
  const d = new Date(isoStr)
  return d.toLocaleString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function ageRangeLabel(minAge: number | null, maxAge: number | null): string | null {
  if (minAge == null && maxAge == null) return null
  if (minAge != null && maxAge != null) return `Ages ${minAge}–${maxAge}`
  if (minAge != null) return `Ages ${minAge}+`
  return `Up to age ${maxAge}`
}

export default function EventSeriesPage(): React.ReactElement {
  const { seriesId = '' } = useParams<{ seriesId: string }>()
  const queryClient = useQueryClient()
  const { user } = useAuth()

  const [name, setName] = useState(
    user?.first_name && user?.last_name ? `${user.first_name} ${user.last_name}` : '',
  )
  const [email, setEmail] = useState(user?.email || '')
  const [phone, setPhone] = useState(user?.phone || '')
  const [reminderRequested, setReminderRequested] = useState(false)
  const [resultSummary, setResultSummary] = useState<SeriesRegistrationResponse | null>(null)
  const [turnstileToken, setTurnstileToken] = useState('')

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['event-series', seriesId],
    queryFn: () => getSeries(seriesId),
    enabled: seriesId.length > 0,
  })

  usePageMeta({
    title: data ? `${data.series_name} — Series` : 'Event series',
    description: data?.description || 'Register for this recurring event series.',
  })

  const mutation = useMutation({
    mutationFn: () =>
      registerForSeries(seriesId, {
        patron_name: name,
        patron_email: email,
        patron_phone: phone || undefined,
        reminder_requested: reminderRequested,
        turnstile_token: turnstileToken || undefined,
      }),
    onSuccess: (resp) => {
      setResultSummary(resp)
      queryClient.invalidateQueries({ queryKey: ['event-series', seriesId] })
      queryClient.invalidateQueries({ queryKey: ['events'] })
      queryClient.invalidateQueries({ queryKey: ['my-registrations'] })
    },
  })

  if (isLoading) {
    return (
      <PageContainer className="py-8">
        <div role="status" aria-live="polite" className="flex items-center gap-2 text-gray-600">
          <Loader2 className="animate-spin h-5 w-5" aria-hidden="true" />
          Loading series…
        </div>
      </PageContainer>
    )
  }

  if (isError || !data) {
    return (
      <PageContainer className="py-8">
        <div role="alert" className="rounded border border-red-200 bg-red-50 p-4 text-red-900">
          <h1 className="font-semibold text-lg flex items-center gap-2">
            <AlertTriangle className="h-5 w-5" aria-hidden="true" />
            Series not found
          </h1>
          <p className="mt-2">
            {(error as Error | undefined)?.message ||
              'This series has no upcoming sessions, or the link is incorrect.'}
          </p>
          <p className="mt-4">
            <Link to="/events" className="underline">
              Back to all events
            </Link>
          </p>
        </div>
      </PageContainer>
    )
  }

  const ageLabel = ageRangeLabel(data.min_age, data.max_age)
  const occurrencesToShow = data.occurrences.slice(0, 8)

  return (
    <PageContainer className="py-8">
      <nav aria-label="Breadcrumb" className="mb-4 text-sm text-gray-600">
        <Link to="/events" className="underline">
          Events
        </Link>
        <span aria-hidden="true"> / </span>
        <span aria-current="page">{data.series_name}</span>
      </nav>

      <header className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">{data.series_name}</h1>
        {data.recurrence_summary && (
          <p className="mt-2 text-gray-700 flex items-center gap-2">
            <Calendar className="h-4 w-4" aria-hidden="true" />
            {data.recurrence_summary}
          </p>
        )}
        <div className="mt-2 flex flex-wrap gap-3 text-sm text-gray-700">
          {data.audience && <span>Audience: {data.audience}</span>}
          {ageLabel && <span>{ageLabel}</span>}
          {data.category && <span>Category: {data.category}</span>}
        </div>
        {data.description && <p className="mt-4 text-gray-800">{data.description}</p>}
        {data.presenters && data.presenters.length > 0 && (
          <p className="mt-2 text-sm text-gray-700">
            Presented by {data.presenters.map((p) => p.name).join(', ')}
          </p>
        )}
      </header>

      <section aria-labelledby="upcoming-heading" className="mb-8">
        <h2 id="upcoming-heading" className="text-xl font-semibold mb-3">
          Upcoming sessions
        </h2>
        <ul className="divide-y divide-gray-200 border border-gray-200 rounded">
          {occurrencesToShow.map((o) => (
            <li key={o.event_id} className="p-3 flex flex-wrap justify-between items-center gap-3">
              <div>
                <div className="font-medium text-gray-900">{formatDateTime(o.start_time)}</div>
                {o.location && (
                  <div className="text-sm text-gray-600 flex items-center gap-1">
                    <MapPin className="h-3.5 w-3.5" aria-hidden="true" />
                    {o.location}
                  </div>
                )}
                {o.spots_remaining != null && (
                  <div className="text-sm text-gray-600 flex items-center gap-1">
                    <Users className="h-3.5 w-3.5" aria-hidden="true" />
                    {o.spots_remaining} spots remaining
                  </div>
                )}
              </div>
              <Link
                to={`/events/detail/${o.event_id}`}
                className="text-sm underline text-blue-700"
              >
                Register for this date only
              </Link>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="series-register-heading" className="border-t border-gray-200 pt-6">
        <h2 id="series-register-heading" className="text-xl font-semibold mb-3">
          Register for the series — all {data.upcoming_count} sessions
        </h2>

        {resultSummary ? (
          <div role="status" aria-live="polite" className="rounded border border-green-200 bg-green-50 p-4">
            <h3 className="font-semibold text-green-900 flex items-center gap-2">
              <CheckCircle className="h-5 w-5" aria-hidden="true" />
              You are registered for the series
            </h3>
            <p className="mt-2 text-sm text-green-900">
              {resultSummary.registered_count} new registration
              {resultSummary.registered_count === 1 ? '' : 's'}
              {resultSummary.already_registered_count > 0 &&
                `, ${resultSummary.already_registered_count} already in place`}
              {resultSummary.waitlisted_count > 0 &&
                `, ${resultSummary.waitlisted_count} waitlisted`}
              {resultSummary.failed_count > 0 &&
                `, ${resultSummary.failed_count} could not be processed`}
              .
            </p>
            <p className="mt-3">
              <Link to="/events" className="underline text-sm">
                Back to all events
              </Link>
            </p>
          </div>
        ) : (
          <form
            onSubmit={(e) => {
              e.preventDefault()
              setResultSummary(null)
              mutation.mutate()
            }}
            className="space-y-3"
          >
            <div>
              <label htmlFor="series-name" className="block text-sm font-medium text-gray-700">
                Name
              </label>
              <input
                id="series-name"
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="mt-1 w-full rounded border border-gray-300 px-3 py-2"
              />
            </div>
            <div>
              <label htmlFor="series-email" className="block text-sm font-medium text-gray-700">
                Email
              </label>
              <input
                id="series-email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 w-full rounded border border-gray-300 px-3 py-2"
              />
            </div>
            <div>
              <label htmlFor="series-phone" className="block text-sm font-medium text-gray-700">
                Phone (optional)
              </label>
              <input
                id="series-phone"
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="mt-1 w-full rounded border border-gray-300 px-3 py-2"
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                id="series-reminders"
                type="checkbox"
                checked={reminderRequested}
                onChange={(e) => setReminderRequested(e.target.checked)}
              />
              <label htmlFor="series-reminders" className="text-sm text-gray-700">
                Remind me before each session
              </label>
            </div>

            {mutation.isError && (
              <div role="alert" className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-900">
                {(mutation.error as Error).message || 'Registration failed. Please try again.'}
              </div>
            )}

            <div>
              <TurnstileWidget onVerify={setTurnstileToken} />
            </div>

            <button
              type="submit"
              disabled={mutation.isPending || !turnstileToken}
              className="inline-flex items-center gap-2 rounded bg-blue-700 px-4 py-2 text-white font-medium hover:bg-blue-800 disabled:opacity-60"
            >
              {mutation.isPending && (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              )}
              Register for all {data.upcoming_count} sessions
            </button>
          </form>
        )}

        {seriesId && (
          <div className="mt-6">
            <a
              href={`/api/v1/events/series/${encodeURIComponent(seriesId)}/calendar.ics`}
              download={`series-${seriesId}.ics`}
              rel="noopener"
              className="inline-flex items-center gap-2 rounded border border-blue-700 px-4 py-2 text-blue-700 font-medium hover:bg-blue-50"
            >
              Add the series to my calendar (.ics)
            </a>
          </div>
        )}
      </section>
    </PageContainer>
  )
}
