/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
// Re-export barrel for backward compatibility
export {
  getMyCheckouts,
  getMyHolds,
  getMyHistory,
  getMyFinesSummary,
  renewCheckout,
  cancelHold,
} from '@/api/domains/circulation/circulation-api'
export type {
  Checkout,
  Hold,
  FinesSummary,
} from '@/api/domains/circulation/circulation-api'

export {
  getMyFavorites,
  removeFavorite,
  getMyLists,
  createList,
  getList,
  deleteList,
  removeFromList,
  updateListPrivacy,
} from '@/api/collections-api'
export type {
  Favorite,
  ReadingList,
  ReadingListWithItems,
} from '@/api/collections-api'

export type { Event } from '@/api/events-api'

export { fetchApi as api } from '@/lib/api-client'

// Stub types and functions for event registration
export interface MyEventRegistration {
  id: number
  event_id: number
  event_title: string
  event_date?: string
  event_start_time?: string
  event_end_time?: string
  event_location?: string
  event_category?: string
  registered_at?: string
  reminder_requested?: boolean
  status: string
}

export interface RegistrationCreate {
  event_id?: number
  name?: string
  email?: string
  notes?: string
  patron_name?: string
  patron_email?: string
  patron_phone?: string
  reminder_requested?: boolean
  // Photo-release consent; null = not asked.
  photo_release_granted?: boolean | null
}

export type Registration = MyEventRegistration

export async function getMyEventRegistrations(): Promise<MyEventRegistration[]> {
  const { fetchApi } = await import('@/lib/api-client')
  return fetchApi<MyEventRegistration[]>('/events/my-registrations')
}

export async function registerForEvent(data: RegistrationCreate): Promise<Registration> {
  const { fetchApi } = await import('@/lib/api-client')
  return fetchApi<Registration>(`/events/${data.event_id}/register`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}
