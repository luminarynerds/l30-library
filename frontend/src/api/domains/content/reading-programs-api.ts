/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'

// ==================== Reading Programs Types ====================

export interface ReadingProgram {
  id: number
  name: string
  description: string | null
  program_type: 'summer' | 'winter' | 'year_round' | 'special'
  age_group: string | null
  target_age_min: number | null
  target_age_max: number | null
  start_date: string
  end_date: string
  reading_goal_type: string | null // 'minutes', 'books', 'pages'
  reading_goal_value: number | null
  is_active: boolean
  created_at: string
  created_by_id: number | null
  registration_count: number
  total_minutes_read: number
  total_books_read: number
}

export interface ReadingProgramsResult {
  items: ReadingProgram[]
  total: number
  limit: number
  offset: number
}

export interface ReadingProgramFilters {
  active_only?: boolean
  program_type?: 'summer' | 'winter' | 'year_round' | 'special' | undefined
}

export interface ReadingRegistrationCreate {
  program_id: number
  goal_target?: number | undefined
}

export interface ReadingRegistration {
  id: number
  user_id: number
  program_id: number
  registered_at: string
  goal_target: number | null
  total_minutes: number
  total_books: number
  total_pages: number
  progress_percentage: number
}

export interface ProgramProgress {
  registration: ReadingRegistration
  program: ReadingProgram
  log_entries: ReadingLogEntry[]
  achievements: ReadingProgramAchievement[]
  total_minutes: number
  total_books: number
  total_pages: number
  days_participated: number
  completion_percentage: number
}

export interface ReadingLogEntry {
  id: number
  registration_id: number
  logged_at: string
  // Actual reading date for paper-log/redeemed entries (issue #828).
  // Null for direct self-logs; prefer this for display when present.
  entry_date: string | null
  books_read: number
  minutes_read: number
  pages_read: number
  title: string | null
  author: string | null
  notes: string | null
  rating: number | null
  book_cover_url: string | null
}

export interface ReadingProgramAchievement {
  id: number
  user_id: number
  program_id: number
  badge_id: string
  badge_name: string
  badge_description: string | null
  unlocked_at: string
}

export interface LogEntryWithAchievementsResponse {
  log_entry: ReadingLogEntry
  new_achievements: ReadingProgramAchievement[]
  achievements_earned: number
}

export interface JoinProgramRequest {
  program_id: number
}

export interface LogProgramReadingRequest {
  program_id: number
  book_title?: string
  pages_read?: number
  reading_minutes?: number
  notes?: string
}

// ==================== Reading Programs Functions ====================

export async function getReadingPrograms(filters: ReadingProgramFilters = {}): Promise<ReadingProgram[]> {
  try {
    const params = new URLSearchParams()

    if (filters.active_only) params.set('active_only', 'true')
    if (filters.program_type) params.set('program_type', filters.program_type)

    const response = await fetchApi<ReadingProgramsResult>(`/reading-programs/programs?${params}`)
    return response.items
  } catch {
    throw new Error('Failed to fetch reading programs')
  }
}

export async function getReadingProgram(programId: number): Promise<ReadingProgram> {
  try {
    return await fetchApi<ReadingProgram>(`/reading-programs/programs/${programId}`)
  } catch {
    throw new Error('Failed to fetch reading program')
  }
}

export async function registerForProgram(
  token: string,
  data: ReadingRegistrationCreate
): Promise<ReadingRegistration> {
  try {
    return await fetchApi<ReadingRegistration>('/reading-programs/registrations', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Registration failed')
    }
    throw error
  }
}

export async function getMyRegistrations(token: string): Promise<ReadingRegistration[]> {
  try {
    return await fetchApi<ReadingRegistration[]>('/reading-programs/registrations/my', { token })
  } catch {
    throw new Error('Failed to fetch registrations')
  }
}

export async function createLogEntry(
  token: string,
  data: {
    registration_id: number
    books_read?: number
    minutes_read?: number
    pages_read?: number
    title?: string
    author?: string
    notes?: string
    rating?: number
    book_cover_url?: string
  }
): Promise<ReadingLogEntry> {
  try {
    return await fetchApi<ReadingLogEntry>('/reading-programs/log-entries', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create log entry')
    }
    throw error
  }
}

export async function getProgramProgress(token: string, registrationId: number): Promise<ProgramProgress> {
  try {
    return await fetchApi<ProgramProgress>(`/reading-programs/progress/${registrationId}`, { token })
  } catch {
    throw new Error('Failed to fetch progress')
  }
}

export async function createLogEntryWithAchievements(
  token: string,
  data: {
    registration_id: number
    books_read?: number
    minutes_read?: number
    pages_read?: number
    title?: string
    author?: string
    notes?: string
    rating?: number
    book_cover_url?: string
  }
): Promise<LogEntryWithAchievementsResponse> {
  try {
    return await fetchApi<LogEntryWithAchievementsResponse>('/reading-programs/log-entries-with-achievements', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create log entry with achievements')
    }
    throw error
  }
}

export async function joinProgram(
  token: string,
  data: JoinProgramRequest
): Promise<ReadingRegistration> {
  try {
    return await fetchApi<ReadingRegistration>('/reading-programs/join', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to join program')
    }
    throw error
  }
}

export async function logProgramReading(
  token: string,
  data: LogProgramReadingRequest
): Promise<ReadingLogEntry> {
  try {
    return await fetchApi<ReadingLogEntry>('/reading-programs/log-reading', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to log reading')
    }
    throw error
  }
}

// ==================== Admin Functions ====================

export interface ReadingProgramCreateData {
  name: string
  description?: string
  program_type?: 'summer' | 'winter' | 'year_round' | 'special'
  age_group?: string
  target_age_min?: number
  target_age_max?: number
  start_date: string // ISO date string
  end_date: string // ISO date string
  reading_goal_type?: 'minutes' | 'books' | 'pages'
  reading_goal_value?: number
  is_active?: boolean
}

export async function createReadingProgram(
  token: string,
  data: ReadingProgramCreateData
): Promise<ReadingProgram> {
  try {
    return await fetchApi<ReadingProgram>('/reading-programs/programs', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create program')
    }
    throw error
  }
}

export async function updateReadingProgram(
  token: string,
  programId: number,
  data: ReadingProgramCreateData
): Promise<ReadingProgram> {
  try {
    return await fetchApi<ReadingProgram>(`/reading-programs/programs/${programId}`, {
      method: 'PUT',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update program')
    }
    throw error
  }
}

export async function deleteReadingProgram(token: string, programId: number): Promise<void> {
  try {
    await fetchApi<void>(`/reading-programs/programs/${programId}`, {
      method: 'DELETE',
      token,
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete program')
    }
    throw error
  }
}


// ==================== Program Booklist (Recommended Reads) ====================

export interface BooklistCatalogItem {
  id: number
  title: string
  author: string | null
  cover_url: string | null
  status: string
  available_for_hold: boolean
}

export interface ProgramBooklistItem {
  id: number
  program_id: number
  display_order: number
  note: string | null
  added_at: string
  catalog_item: BooklistCatalogItem
}

export interface ProgramBooklistResponse {
  items: ProgramBooklistItem[]
}

export interface ProgramBooklistItemCreate {
  catalog_item_id: number
  display_order?: number
  note?: string | null
}

export interface ProgramBooklistItemUpdate {
  display_order?: number
  note?: string | null
}

export interface ProgramBooklistReorderEntry {
  item_id: number
  display_order: number
}

export async function getProgramBooklist(programId: number): Promise<ProgramBooklistResponse> {
  try {
    return await fetchApi<ProgramBooklistResponse>(
      `/reading-programs/programs/${programId}/booklist`,
    )
  } catch {
    throw new Error('Failed to fetch program booklist')
  }
}

export async function addProgramBooklistItem(
  token: string,
  programId: number,
  data: ProgramBooklistItemCreate,
): Promise<ProgramBooklistItem> {
  try {
    return await fetchApi<ProgramBooklistItem>(
      `/reading-programs/programs/${programId}/booklist`,
      { method: 'POST', token, body: data },
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 409) throw new Error('Item already on this booklist')
      throw new Error(error.detail || 'Failed to add to booklist')
    }
    throw error
  }
}

export async function updateProgramBooklistItem(
  token: string,
  programId: number,
  itemId: number,
  data: ProgramBooklistItemUpdate,
): Promise<ProgramBooklistItem> {
  try {
    return await fetchApi<ProgramBooklistItem>(
      `/reading-programs/programs/${programId}/booklist/${itemId}`,
      { method: 'PATCH', token, body: data },
    )
  } catch (error: unknown) {
    if (isApiError(error)) throw new Error(error.detail || 'Failed to update booklist item')
    throw error
  }
}

export async function deleteProgramBooklistItem(
  token: string,
  programId: number,
  itemId: number,
): Promise<void> {
  try {
    await fetchApi<void>(
      `/reading-programs/programs/${programId}/booklist/${itemId}`,
      { method: 'DELETE', token, skipJsonParse: true },
    )
  } catch (error: unknown) {
    if (isApiError(error)) throw new Error(error.detail || 'Failed to remove booklist item')
    throw error
  }
}

export async function reorderProgramBooklist(
  token: string,
  programId: number,
  order: ProgramBooklistReorderEntry[],
): Promise<ProgramBooklistResponse> {
  try {
    return await fetchApi<ProgramBooklistResponse>(
      `/reading-programs/programs/${programId}/booklist/reorder`,
      { method: 'PUT', token, body: { order } },
    )
  } catch (error: unknown) {
    if (isApiError(error)) throw new Error(error.detail || 'Failed to reorder booklist')
    throw error
  }
}

// ==================== Paper Log / Kiosk Claim Code ====================

export interface PaperLogRedeemEntry {
  entry_date: string
  title?: string | null
  author?: string | null
  books_read?: number
  minutes_read?: number
  pages_read?: number
  notes?: string | null
}

export interface PaperLogRedeemRequest {
  code: string
  entries: PaperLogRedeemEntry[]
}

export interface PaperLogRedeemResponse {
  registration_id: number
  program_id: number
  entries_created: number
  new_achievements: number
  total_books: number
  total_minutes: number
  total_pages: number
  goal_percent: number
}

export async function downloadPaperLogPdf(
  token: string,
  programId: number,
  registrationId: number,
): Promise<void> {
  const API_BASE = (import.meta as unknown as { env: Record<string, string | undefined> }).env.VITE_API_BASE || "/api/v1"
  const url = `${API_BASE}/reading-programs/programs/${programId}/registrations/${registrationId}/log.pdf`
  const res = await fetch(url, {
    credentials: "include",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) {
    throw new Error(`Failed to download reading log (status ${res.status})`)
  }
  const blob = await res.blob()
  const objectUrl = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = objectUrl
  a.download = `reading-log-${registrationId}.pdf`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  setTimeout(() => URL.revokeObjectURL(objectUrl), 1000)
}

export async function redeemPaperLog(
  token: string,
  payload: PaperLogRedeemRequest,
): Promise<PaperLogRedeemResponse> {
  try {
    return await fetchApi<PaperLogRedeemResponse>("/reading-programs/redeem", {
      method: "POST",
      token,
      body: payload,
    })
  } catch (error: unknown) {
    if (isApiError(error)) throw error
    throw error
  }
}
