/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Patron Communication API
 *
 * Staff-only endpoints for managing:
 * - Patron notes (internal staff notes)
 * - Patron messages (email/SMS communication history)
 * - Message templates
 */

import { fetchApi, isApiError } from '@/lib/api-client'

// ==================== Enums ====================

export type NoteCategory = 'general' | 'account' | 'behavior' | 'special_needs' | 'payment'
export type MessageType = 'overdue_notice' | 'hold_ready' | 'fine_reminder' | 'account_blocked' | 'welcome_new_patron' | 'custom'
export type MessageChannel = 'email' | 'sms'

// ==================== Note Types ====================

export interface PatronNote {
  id: number
  patron_id: number
  author_id: number | null
  author_name: string | null
  category: NoteCategory
  content: string
  created_at: string
  updated_at: string | null
}

export interface PatronNoteCreate {
  content: string
  category?: NoteCategory
}

export interface PatronNoteUpdate {
  content?: string
  category?: NoteCategory
}

export interface PatronNoteListResponse {
  notes: PatronNote[]
  total: number
}

// ==================== Message Types ====================

export interface PatronMessage {
  id: number
  patron_id: number
  sender_id: number | null
  sender_name: string | null
  message_type: MessageType
  channel: MessageChannel
  subject: string
  body: string
  recipient_email: string | null
  recipient_phone: string | null
  sent_at: string
  delivered: boolean
  delivery_error: string | null
}

export interface PatronMessageCreate {
  message_type?: MessageType
  channel?: MessageChannel
  subject: string
  body: string
}

export interface PatronMessageListResponse {
  messages: PatronMessage[]
  total: number
}

export interface MessageTemplate {
  id: string
  name: string
  subject: string
  body: string
}

// ==================== Note Functions ====================

export async function getPatronNotes(
  token: string,
  patronId: number,
  options?: {
    skip?: number
    limit?: number
    category?: NoteCategory
  }
): Promise<PatronNoteListResponse> {
  try {
    const params = new URLSearchParams()
    if (options?.skip !== undefined) params.set('skip', options.skip.toString())
    if (options?.limit !== undefined) params.set('limit', options.limit.toString())
    if (options?.category) params.set('category', options.category)
    const queryString = params.toString() ? `?${params.toString()}` : ''
    return await fetchApi<PatronNoteListResponse>(`/staff/patrons/${patronId}/notes${queryString}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch patron notes')
    }
    throw error
  }
}

export async function createPatronNote(
  token: string,
  patronId: number,
  data: PatronNoteCreate
): Promise<PatronNote> {
  try {
    return await fetchApi<PatronNote>(`/staff/patrons/${patronId}/notes`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create note')
    }
    throw error
  }
}

export async function updatePatronNote(
  token: string,
  patronId: number,
  noteId: number,
  data: PatronNoteUpdate
): Promise<PatronNote> {
  try {
    return await fetchApi<PatronNote>(`/staff/patrons/${patronId}/notes/${noteId}`, {
      method: 'PUT',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update note')
    }
    throw error
  }
}

export async function deletePatronNote(
  token: string,
  patronId: number,
  noteId: number
): Promise<void> {
  try {
    await fetchApi<void>(`/staff/patrons/${patronId}/notes/${noteId}`, {
      method: 'DELETE',
      token,
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete note')
    }
    throw error
  }
}

// ==================== Message Functions ====================

export async function getMessageTemplates(token: string): Promise<MessageTemplate[]> {
  try {
    return await fetchApi<MessageTemplate[]>('/staff/patrons/messages/templates', { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch message templates')
    }
    throw error
  }
}

export async function getPatronMessages(
  token: string,
  patronId: number,
  options?: {
    skip?: number
    limit?: number
    message_type?: MessageType
  }
): Promise<PatronMessageListResponse> {
  try {
    const params = new URLSearchParams()
    if (options?.skip !== undefined) params.set('skip', options.skip.toString())
    if (options?.limit !== undefined) params.set('limit', options.limit.toString())
    if (options?.message_type) params.set('message_type', options.message_type)
    const queryString = params.toString() ? `?${params.toString()}` : ''
    return await fetchApi<PatronMessageListResponse>(`/staff/patrons/${patronId}/messages${queryString}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch patron messages')
    }
    throw error
  }
}

export async function sendPatronMessage(
  token: string,
  patronId: number,
  data: PatronMessageCreate
): Promise<PatronMessage> {
  try {
    return await fetchApi<PatronMessage>(`/staff/patrons/${patronId}/messages`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to send message')
    }
    throw error
  }
}

// ==================== Helper Functions ====================

export function getNoteCategoryLabel(category: NoteCategory): string {
  switch (category) {
    case 'general':
      return 'General'
    case 'account':
      return 'Account'
    case 'behavior':
      return 'Behavior'
    case 'special_needs':
      return 'Special Needs'
    case 'payment':
      return 'Payment'
    default:
      return category
  }
}

export function getMessageTypeLabel(type: MessageType): string {
  switch (type) {
    case 'overdue_notice':
      return 'Overdue Notice'
    case 'hold_ready':
      return 'Hold Ready'
    case 'fine_reminder':
      return 'Fine Reminder'
    case 'account_blocked':
      return 'Account Blocked'
    case 'welcome_new_patron':
      return 'Welcome'
    case 'custom':
      return 'Custom'
    default:
      return type
  }
}

export function getMessageChannelLabel(channel: MessageChannel): string {
  switch (channel) {
    case 'email':
      return 'Email'
    case 'sms':
      return 'SMS'
    default:
      return channel
  }
}

export function getNoteCategoryColor(category: NoteCategory): string {
  switch (category) {
    case 'general':
      return 'bg-earth-100 dark:bg-earth-800 text-earth-700 dark:text-earth-300'
    case 'account':
      return 'bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light'
    case 'behavior':
      return 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-400'
    case 'special_needs':
      return 'bg-category-100 dark:bg-category-900/30 text-category-700 dark:text-category-400'
    case 'payment':
      return 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-400'
    default:
      return 'bg-earth-100 dark:bg-earth-800 text-earth-700 dark:text-earth-300'
  }
}

export function getMessageTypeColor(type: MessageType): string {
  switch (type) {
    case 'overdue_notice':
      return 'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-400'
    case 'hold_ready':
      return 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-400'
    case 'fine_reminder':
      return 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-400'
    case 'account_blocked':
      return 'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-400'
    case 'welcome_new_patron':
      return 'bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light'
    case 'custom':
      return 'bg-category-100 dark:bg-category-900/30 text-category-700 dark:text-category-400'
    default:
      return 'bg-earth-100 dark:bg-earth-800 text-earth-700 dark:text-earth-300'
  }
}

export function getNoteCategories(): { value: NoteCategory; label: string }[] {
  return [
    { value: 'general', label: 'General' },
    { value: 'account', label: 'Account' },
    { value: 'behavior', label: 'Behavior' },
    { value: 'special_needs', label: 'Special Needs' },
    { value: 'payment', label: 'Payment' },
  ]
}

export function getMessageTypes(): { value: MessageType; label: string }[] {
  return [
    { value: 'custom', label: 'Custom Message' },
    { value: 'overdue_notice', label: 'Overdue Notice' },
    { value: 'hold_ready', label: 'Hold Ready' },
    { value: 'fine_reminder', label: 'Fine Reminder' },
    { value: 'account_blocked', label: 'Account Blocked' },
    { value: 'welcome_new_patron', label: 'Welcome New Patron' },
  ]
}

export function getMessageChannels(): { value: MessageChannel; label: string }[] {
  return [
    { value: 'email', label: 'Email' },
    { value: 'sms', label: 'SMS' },
  ]
}
