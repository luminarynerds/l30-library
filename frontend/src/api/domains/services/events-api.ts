/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'

// ==================== Events Types ====================

export interface Event {
  /**
   * Persisted event PK. When the backend was called with
   * `expand_recurrence=true`, virtual recurrence instances arrive with
   * `id` null at runtime; callers opting into expansion MUST guard with
   * `is_virtual_instance` before treating `id` as defined.
   */
  id: number
  title: string
  description: string | null
  start_time: string
  end_time: string | null
  location: string | null
  is_virtual: boolean
  virtual_link?: string | null
  audience: string | null
  category: string | null
  /** ISO 639-1 code of the language the program is conducted in; null = unspecified. */
  event_language?: string | null
  tags: string[] | null
  max_attendees: number | null
  registration_required: boolean
  registration_count: number
  spots_remaining: number | null
  image_url: string | null
  is_featured: boolean
  series_id: string | null
  series_name: string | null
  created_at: string
  average_rating: number | null
  review_count: number
  branch_id?: number | null
  /** Display name of the hosting branch; resolved server-side from branch_id. */
  branch_name?: string | null
  accessibility_notes?: string | null
  wheelchair_accessible?: boolean
  asl_provided?: boolean
  captioning_provided?: boolean
  assistive_listening?: boolean
  sensory_friendly?: boolean
  large_print_available?: boolean
  // Structured sensory descriptors. The string
  // fields hold a fixed lowercase vocabulary; null/undefined = not specified.
  lighting?: string | null
  noise_level?: string | null
  crowd_size?: string | null
  quiet_space_available?: boolean
  // Photo release flag — drives the consent checkbox in RegistrationModal.
  photos_will_be_taken?: boolean
  // Optional recurrence + audience metadata (read-only on the patron side).
  recurrence_rule?: string | null
  min_age?: number | null
  max_age?: number | null
  caregiver_required?: boolean
  // Set to true by the backend when this row was synthesized from RRULE
  // expansion (id will be null, parent_event_id is the source row's PK).
  is_virtual_instance?: boolean
  parent_event_id?: number | null
}

export interface EventsResult {
  data: Event[]
  pagination: {
    page: number
    per_page: number
    total: number
    total_pages: number
    has_next: boolean
    has_previous: boolean
  }
}

type LegacyEventsResult = {
  items?: Event[]
  total?: number
  page?: number
  per_page?: number
}

function normalizeEventsResult(payload: EventsResult | Event[] | LegacyEventsResult): EventsResult {
  // Current API contract: { data, pagination }
  if (!Array.isArray(payload) && 'data' in payload && 'pagination' in payload) {
    return payload
  }

  // Backward compatibility for old payload shapes used by tests/legacy backends.
  if (Array.isArray(payload)) {
    return {
      data: payload,
      pagination: {
        page: 1,
        per_page: payload.length,
        total: payload.length,
        total_pages: payload.length > 0 ? 1 : 0,
        has_next: false,
        has_previous: false,
      },
    }
  }

  const items = payload.items ?? []
  const page = payload.page ?? 1
  const perPage = payload.per_page ?? (items.length || 20)
  const total = payload.total ?? items.length
  const totalPages = Math.ceil(total / Math.max(perPage, 1))

  return {
    data: items,
    pagination: {
      page,
      per_page: perPage,
      total,
      total_pages: totalPages,
      has_next: page < totalPages,
      has_previous: page > 1,
    },
  }
}

export interface RegistrationCreate {
  patron_name: string
  /** Optional when a phone number is given — the API requires at least one. */
  patron_email?: string
  patron_phone?: string
  reminder_requested?: boolean
  accommodation_requested?: boolean
  accommodation_details?: string | null
  // Photo-release consent. null = not asked (event has
  // photos_will_be_taken=false); true/false = patron's explicit answer.
  photo_release_granted?: boolean | null
  turnstile_token?: string
}

export interface Registration {
  id: number
  event_id: number
  patron_name: string
  patron_email: string
  patron_phone: string | null
  registered_at: string
  status: string
  reminder_requested: boolean
  waitlist_position: number | null
  accommodation_requested?: boolean
  accommodation_details?: string | null
  accommodation_acknowledged_at?: string | null
  accommodation_acknowledged_by?: number | null
}

export interface RegistrationListResult {
  registrations: Registration[]
  total: number
  waitlist_count: number
  spots_remaining: number | null
}

// ==================== Review Types ====================

export interface EventReviewCreate {
  patron_email: string
  rating: number
  comment?: string
}

export interface EventReview {
  id: number
  event_id: number
  patron_email: string
  rating: number
  comment: string | null
  created_at: string
}

export interface EventReviewSummary {
  event_id: number
  average_rating: number | null
  total_reviews: number
  rating_distribution: Record<number, number>
}

export interface EventReviewDetailResponse {
  id: number
  event_id: number
  patron_email: string
  rating: number
  comment: string | null
  moderation_status: string
  moderated_by: string | null
  moderated_at: string | null
  moderation_reason: string | null
  is_removed: number
  removal_reason: string | null
  removed_by: string | null
  removed_at: string | null
  created_at: string
  updated_at: string
}

export interface ReviewModerationAction {
  action: 'approve' | 'reject' | 'remove'
  reason?: string
}

export interface EventReviewEditRequest {
  comment: string
  reason?: string
}

export type EventWhenWindow = 'today' | 'weekend' | 'week'

export function whenToRange(
  when: EventWhenWindow,
  now: Date = new Date(),
): { starts_after?: string; starts_before?: string } {
  if (when === 'today') {
    const start = new Date(now)
    start.setHours(0, 0, 0, 0)
    const end = new Date(now)
    end.setHours(23, 59, 59, 999)
    return { starts_after: start.toISOString(), starts_before: end.toISOString() }
  }
  if (when === 'weekend') {
    // getDay(): 0=Sun..6=Sat. Use this week's Sat+Sun when today is the
    // weekend, otherwise the upcoming weekend. The `upcoming` floor keeps
    // already-passed weekend events out.
    const day = now.getDay()
    const daysUntilSat = day === 0 ? -1 : 6 - day
    const sat = new Date(now)
    sat.setDate(sat.getDate() + daysUntilSat)
    sat.setHours(0, 0, 0, 0)
    const sun = new Date(sat)
    sun.setDate(sun.getDate() + 1)
    sun.setHours(23, 59, 59, 999)
    return { starts_after: sat.toISOString(), starts_before: sun.toISOString() }
  }
  // 'week' — the next 7 days from now.
  const end = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000)
  return { starts_after: now.toISOString(), starts_before: end.toISOString() }
}

export interface EventFilters {
  upcoming?: boolean
  category?: string
  /**
   * Multi-select audience filter with OR semantics: an event matches if its
   * `audience` value is in this list. Sent as repeated `audiences` query
   * params, e.g. `?audiences=children&audiences=teens`.
   */
  audiences?: string[]
  tag?: string
  featured_only?: boolean
  series_id?: string
  search?: string
  page?: number
  per_page?: number
  /**
   * Time-window quick filter. Semantic on the client (drives the quick-chip
   * `aria-pressed` state and deep links); `getEvents` expands it into the
   * concrete `starts_after` / `starts_before` instants the backend filters
   * on, computed in the patron's local timezone.
   */
  when?: EventWhenWindow
  /** Only drop-in events (those that need no registration). */
  drop_in?: boolean
  /**
   * Accessibility provisions an event must ALL provide (AND semantics).
   * Values are Event accessibility column names — e.g. `wheelchair_accessible`,
   * `asl_provided` — sent as repeated `accessibility` query params.
   */
  accessibility?: string[]
  /**
   * Program languages to match (OR semantics, like `audiences`). Values are
   * ISO 639-1 codes sent as repeated `languages` query params.
   */
  languages?: string[]
  /**
   * Hosting branches to match (OR semantics, like `audiences`). Sent as
   * repeated `branch_ids` query params.
   */
  branch_ids?: number[]
  /**
   * When true, recurring events (those with `recurrence_rule`) are expanded
   * into virtual instances within a 183-day horizon by the backend.
   * Virtual instances have `id=null` and `is_virtual_instance=true`, with
   * the parent's PK in `parent_event_id`. Default false to preserve the
   * legacy "one row per persisted event" semantics.
   */
  expand_recurrence?: boolean
}

export interface RelatedEventsResult {
  items: Event[]
  source_event_id: number
}

export interface EventCreate {
  title: string
  description?: string
  category?: string
  audience?: string
  event_language?: string
  location?: string
  start_time: string
  end_time?: string
  registration_required: boolean
  max_attendees?: number | null
  tags?: string[]
  image_url?: string
  is_featured?: boolean
  is_virtual?: boolean
  virtual_link?: string
  series_id?: string
  series_name?: string
  branch_id?: number | null
  accessibility_notes?: string
  wheelchair_accessible?: boolean
  asl_provided?: boolean
  captioning_provided?: boolean
  assistive_listening?: boolean
  sensory_friendly?: boolean
  large_print_available?: boolean
  // Structured sensory descriptors.
  lighting?: string | null
  noise_level?: string | null
  crowd_size?: string | null
  quiet_space_available?: boolean
}


// ---- Bulk-create recurring series (parent + N real children with parent_event_id) ----
// Mirror of backend EventBulkCreateRequest / EventBulkCreateResponse /
// EventBulkCreateDryRunResponse in app/schemas/event.py. The backend enforces:
//   - hard cap of 52 child rows per call
//   - +366d horizon even if RRULE UNTIL is further out
//   - atomic insert (parent + all children rollback together)

export interface EventBulkCreateRequest extends EventCreate {
  recurrence_rule: string
  dry_run?: boolean
  // Fields that EventCreate doesn't yet declare but the bulk endpoint accepts:
  presenters?: Array<{ name: string; bio?: string; fee?: string; program_partner_id?: number | null }>
  program_partner_id?: number | null
  photos_will_be_taken?: boolean
  min_age?: number | null
  max_age?: number | null
  caregiver_required?: boolean
  accessibility_notes?: string
}

export interface EventBulkInstancePreview {
  start_time: string
  end_time: string | null
}

export interface EventBulkCreateDryRunResponse {
  count: number
  first_start: string | null
  last_start: string | null
  instances: EventBulkInstancePreview[]
}

export interface EventBulkCreateResponse {
  parent_id: number
  child_ids: number[]
  count: number
}

// ==================== Events Functions ====================

export async function getEventTags(): Promise<string[]> {
  try {
    return await fetchApi<string[]>('/events/tags')
  } catch {
    return []
  }
}

export async function getEventCategories(): Promise<string[]> {
  try {
    return await fetchApi<string[]>('/events/categories')
  } catch {
    return []
  }
}

export async function getEventAudiences(): Promise<string[]> {
  try {
    return await fetchApi<string[]>('/events/audiences')
  } catch {
    return []
  }
}

export async function getEvents(filters: EventFilters = {}): Promise<EventsResult> {
  try {
    const params = new URLSearchParams()

    // Default upcoming to true if not specified
    params.set('upcoming', String(filters.upcoming !== undefined ? filters.upcoming : true))

    if (filters.category) params.set('category', filters.category)
    if (filters.audiences && filters.audiences.length > 0) {
      for (const a of filters.audiences) params.append('audiences', a)
    }
    if (filters.tag) params.set('tag', filters.tag)
    if (filters.featured_only) params.set('featured_only', 'true')
    if (filters.series_id) params.set('series_id', filters.series_id)
    if (filters.search) params.set('search', filters.search)
    if (filters.page) params.set('page', String(filters.page))
    // The events endpoint paginates via PaginationParams whose field is `page_size`
    // (no `per_page` alias), capped at 100. Sending `per_page` was silently ignored
    // -> every caller got the default 20. Map to `page_size` and clamp to the API max.
    if (filters.per_page) params.set('page_size', String(Math.min(filters.per_page, 100)))
    if (filters.expand_recurrence) params.set('expand_recurrence', 'true')
    if (filters.drop_in) params.set('drop_in', 'true')
    if (filters.accessibility && filters.accessibility.length > 0) {
      for (const a of filters.accessibility) params.append('accessibility', a)
    }
    if (filters.languages && filters.languages.length > 0) {
      for (const l of filters.languages) params.append('languages', l)
    }
    if (filters.branch_ids && filters.branch_ids.length > 0) {
      for (const b of filters.branch_ids) params.append('branch_ids', String(b))
    }
    if (filters.when) {
      const { starts_after, starts_before } = whenToRange(filters.when)
      if (starts_after) params.set('starts_after', starts_after)
      if (starts_before) params.set('starts_before', starts_before)
    }

    const response = await fetchApi<EventsResult | Event[] | LegacyEventsResult>(`/events?${params}`)
    return normalizeEventsResult(response)
  } catch {
    throw new Error('Failed to fetch events')
  }
}


export async function getEventById(eventId: number): Promise<Event> {
  return await fetchApi<Event>(`/events/${eventId}`)
}

export async function getRelatedEvents(eventId: number, limit = 3): Promise<RelatedEventsResult> {
  try {
    return await fetchApi<RelatedEventsResult>(`/events/${eventId}/related?limit=${limit}`)
  } catch {
    return { items: [], source_event_id: eventId }
  }
}

export async function registerForEvent(eventId: number, data: RegistrationCreate): Promise<Registration> {
  try {
    return await fetchApi<Registration>(`/events/${eventId}/register`, {
      method: 'POST',
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Registration failed')
    }
    throw error
  }
}

// ==================== Series registration ====================

export interface SeriesRegistrationOutcome {
  event_id: number
  start_time: string
  status: 'registered' | 'already_registered' | 'waitlisted' | 'capacity_full' | 'error'
  registration_id: number | null
  waitlist_position: number | null
  error: string | null
}

export interface SeriesRegistrationResult {
  series_id: string
  series_name: string
  total_upcoming: number
  registered_count: number
  already_registered_count: number
  waitlisted_count: number
  failed_count: number
  outcomes: SeriesRegistrationOutcome[]
}

export async function registerForSeries(
  seriesId: string,
  data: RegistrationCreate,
): Promise<SeriesRegistrationResult> {
  try {
    return await fetchApi<SeriesRegistrationResult>(
      `/events/series/${encodeURIComponent(seriesId)}/register`,
      { method: 'POST', body: data },
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Series registration failed')
    }
    throw error
  }
}


// PR #999: waitlist API
export interface WaitlistJoinRequest {
  email: string
  name?: string | null
  registrant_count?: number
  notes?: string | null
  turnstile_token?: string | null
}

export interface WaitlistJoinResult {
  id: number
  event_id: number
  email: string
  position: number
  status: string
  created_at: string
  cancel_token: string
}

export interface WaitlistPositionResult {
  event_id: number
  email: string
  position: number
  status: string
}

export async function joinEventWaitlist(
  eventId: number,
  data: WaitlistJoinRequest,
): Promise<WaitlistJoinResult> {
  try {
    return await fetchApi<WaitlistJoinResult>(`/events/${eventId}/waitlist`, {
      method: 'POST',
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to join waitlist')
    }
    throw error
  }
}

export async function getEventWaitlistPosition(
  eventId: number,
  email: string,
): Promise<WaitlistPositionResult> {
  return await fetchApi<WaitlistPositionResult>(
    `/events/${eventId}/waitlist/position?email=${encodeURIComponent(email)}`,
    { method: 'GET' },
  )
}

export async function leaveEventWaitlist(
  eventId: number,
  email: string,
  token: string,
): Promise<void> {
  await fetchApi<void>(
    `/events/${eventId}/waitlist?email=${encodeURIComponent(email)}&token=${encodeURIComponent(token)}`,
    { method: 'DELETE', skipJsonParse: true },
  )
}

export async function cancelRegistration(eventId: number, registrationId: number, patronEmail: string): Promise<void> {
  try {
    await fetchApi<void>(`/events/${eventId}/register/${registrationId}`, {
      method: 'DELETE',
      body: JSON.stringify({ patron_email: patronEmail }),
      headers: { 'Content-Type': 'application/json' },
      skipJsonParse: true,
    })
  } catch {
    throw new Error('Failed to cancel registration')
  }
}

export async function createEvent(token: string, data: EventCreate): Promise<Event> {
  const payload = {
    ...data,
    max_attendees: data.max_attendees ? Number(data.max_attendees) : null,
  }

  try {
    return await fetchApi<Event>('/events', {
      method: 'POST',
      token,
      body: payload,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create event')
    }
    throw error
  }
}

export async function bulkCreateRecurringEvents(
  token: string,
  data: EventBulkCreateRequest,
): Promise<EventBulkCreateResponse | EventBulkCreateDryRunResponse> {
  const payload = {
    ...data,
    max_attendees: data.max_attendees ? Number(data.max_attendees) : null,
  }
  try {
    return await fetchApi<EventBulkCreateResponse | EventBulkCreateDryRunResponse>(
      '/events/bulk-from-recurrence',
      { method: 'POST', token, body: payload },
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create recurring series')
    }
    throw error
  }
}

export async function updateEvent(token: string, eventId: number, data: EventCreate): Promise<Event> {
  const payload = {
    ...data,
    max_attendees: data.max_attendees ? Number(data.max_attendees) : null,
  }

  try {
    return await fetchApi<Event>(`/events/${eventId}`, {
      method: 'PUT',
      token,
      body: payload,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update event')
    }
    throw error
  }
}

export async function deleteEvent(token: string, eventId: number): Promise<void> {
  try {
    await fetchApi<void>(`/events/${eventId}`, {
      method: 'DELETE',
      token,
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete event')
    }
    throw error
  }
}

// ==================== Review Functions ====================

export async function submitEventReview(eventId: number, data: EventReviewCreate): Promise<EventReview> {
  try {
    return await fetchApi<EventReview>(`/events/${eventId}/reviews`, {
      method: 'POST',
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to submit review')
    }
    throw error
  }
}

export async function getEventReviews(eventId: number, page = 1, perPage = 20): Promise<EventReview[]> {
  try {
    const response = await fetchApi<{ data: EventReview[]; pagination: unknown }>(`/events/${eventId}/reviews?page=${page}&page_size=${perPage}`)
    return response.data
  } catch {
    throw new Error('Failed to fetch reviews')
  }
}

export async function getEventReviewSummary(eventId: number): Promise<EventReviewSummary> {
  try {
    return await fetchApi<EventReviewSummary>(`/events/${eventId}/reviews/summary`)
  } catch {
    throw new Error('Failed to fetch review summary')
  }
}

// ==================== Admin Registration Functions ====================


// ==================== Roster / Attendance Reconciliation ====================

export async function getEvent(eventId: number): Promise<Event> {
  return await fetchApi<Event>(`/events/${eventId}`)
}

export async function getEventRegistrations(
  token: string,
  eventId: number,
  options: { includeWaitlist?: boolean; page?: number; perPage?: number } = {}
): Promise<RegistrationListResult> {
  const params = new URLSearchParams()
  if (options.includeWaitlist) params.set('include_waitlist', 'true')
  if (options.page) params.set('page', String(options.page))
  if (options.perPage) params.set('per_page', String(options.perPage))
  const qs = params.toString()
  return await fetchApi<RegistrationListResult>(
    `/events/${eventId}/registrations${qs ? `?${qs}` : ''}`,
    { token }
  )
}

export async function acknowledgeAccommodation(
  token: string,
  eventId: number,
  registrationId: number
): Promise<void> {
  try {
    await fetchApi<{ ok: boolean }>(
      `/events/${eventId}/registrations/${registrationId}/acknowledge-accommodation`,
      { method: 'POST', token }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to acknowledge accommodation')
    }
    throw error
  }
}

export async function markRegistrationNoShow(
  token: string,
  eventId: number,
  registrationId: number
): Promise<{ id: number; status: string }> {
  try {
    return await fetchApi<{ id: number; status: string }>(
      `/events/${eventId}/registrations/${registrationId}/mark-no-show`,
      { method: 'POST', token }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to mark no-show')
    }
    throw error
  }
}

export async function markRegistrationAttended(
  token: string,
  eventId: number,
  registrationId: number
): Promise<{
  id: number
  session_id: number
  registration_id: number
  check_in_method: string
  checked_in_at: string | null
}> {
  try {
    return await fetchApi(
      `/events/${eventId}/registrations/${registrationId}/check-in`,
      { method: 'POST', token }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to mark attended')
    }
    throw error
  }
}

export async function adminCancelRegistration(
  token: string,
  eventId: number,
  registrationId: number
): Promise<void> {
  try {
    await fetchApi<void>(`/events/${eventId}/registrations/${registrationId}/admin`, {
      method: 'DELETE',
      token,
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to cancel registration')
    }
    throw error
  }
}

// ==================== Review Moderation Functions ====================

export async function moderateEventReview(
  token: string,
  reviewId: number,
  action: ReviewModerationAction
): Promise<EventReviewDetailResponse> {
  try {
    return await fetchApi<EventReviewDetailResponse>(`/events/reviews/${reviewId}/moderate`, {
      method: 'POST',
      token,
      body: action,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to moderate review')
    }
    throw error
  }
}

export async function editEventReview(
  token: string,
  reviewId: number,
  data: EventReviewEditRequest
): Promise<EventReviewDetailResponse> {
  try {
    return await fetchApi<EventReviewDetailResponse>(`/events/reviews/${reviewId}/edit`, {
      method: 'PATCH',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to edit review')
    }
    throw error
  }
}

export async function hideEventReview(
  token: string,
  reviewId: number
): Promise<EventReviewDetailResponse> {
  try {
    return await fetchApi<EventReviewDetailResponse>(`/events/reviews/${reviewId}/hide`, {
      method: 'PATCH',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to hide review')
    }
    throw error
  }
}

export async function deleteEventReview(token: string, reviewId: number): Promise<void> {
  try {
    await fetchApi<void>(`/events/reviews/${reviewId}`, {
      method: 'DELETE',
      token,
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete review')
    }
    throw error
  }
}
