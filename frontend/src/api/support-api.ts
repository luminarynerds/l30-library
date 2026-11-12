/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Support Tickets API Service
 * Handles creation and management of support tickets and escalations.
 *
 * Triage helpers (listTriageTickets, patchTriageTicket, postTriageResponse,
 * listTriageEvents) power the staff /staff/support/triage page.
 */

import { fetchApi } from '@/lib/api-client'
import { getAccessToken } from '../utils/tokenStore'

// ============================================================
// Types
// ============================================================

export interface SupportTicketCreateData {
  name: string
  email: string
  phone?: string
  guide: string
  step: number
  totalSteps: number
  issue: string
  method: 'email' | 'phone' | 'visit'
  timestamp: string
  category?: string
  // Honeypot. Always leave blank in real submissions.
  website_url?: string
}

export interface SupportTicket extends SupportTicketCreateData {
  id: string
  status: 'open' | 'in_progress' | 'resolved' | 'closed'
  created_at: string
  updated_at: string
}

export interface SupportTicketResponse {
  ticket_id: string
  status: string
  reference_number: string
  message: string
  // Populated for patron-contact-page submissions; undefined for escalation
  // modal submissions where no category was provided.
  category?: string | null
  response_route?: string | null
  sla_business_days?: number | null
}

// Payload shape accepted by submitContactMessage(). Mirrors the patron
// contact page form. Fields are optional to support anonymous / under-13 /
// no-reply paths; server enforces per-method requirements.
export interface ContactSubmissionData {
  name?: string
  email?: string
  phone?: string
  issueDescription: string
  contactMethod: 'email' | 'phone' | 'visit' | 'none'
  category: string
  isAnonymous: boolean
  subjectLine?: string
  // Honeypot pass-through. Real submissions leave this undefined; the
  // form populates it when a bot fills the hidden field. The server
  // logs the IP and returns a fake ack without persisting.
  websiteUrl?: string
  // Cloudflare Turnstile token from the contact form widget.
  turnstileToken?: string
  timestamp: string
}

// ----- Triage types ----------------------------------------------------------

export type TicketStatus = 'open' | 'in_progress' | 'resolved' | 'closed'

export interface TriageTicket {
  id: number
  ticket_number: string
  name: string
  email: string
  phone: string | null
  guide_title: string | null
  step_number: number | null
  total_steps: number | null
  issue_description: string
  contact_method: string
  status: TicketStatus
  category: string | null
  submitted_at: string
  updated_at: string
  resolved_at: string | null
  assigned_to_id: number | null
  internal_notes: string | null
  sla_business_days: number | null
  age_business_days: number | null
  sla_breached: boolean
}

export interface TriageListResponse {
  tickets: TriageTicket[]
  total: number
}

export interface TriageEvent {
  id: number
  event_type: string
  actor_identifier: string | null
  from_value: string | null
  to_value: string | null
  note: string | null
  created_at: string
}

export interface TriageFilters {
  status_filter?: string
  category?: string
  search?: string
  submitted_from?: string // YYYY-MM-DD
  submitted_to?: string
  assigned_to_id?: number
  sla_breached?: boolean
  limit?: number
  offset?: number
}

// ============================================================
// API Functions
// ============================================================

export async function createSupportTicket(
  data: SupportTicketCreateData
): Promise<SupportTicketResponse> {
  const token = getAccessToken()

  const payload = {
    name: data.name,
    email: data.email,
    phone: data.phone || null,
    guide_title: data.guide,
    step_number: data.step,
    total_steps: data.totalSteps,
    issue_description: data.issue,
    contact_method: data.method,
    category: data.category,
    timestamp: data.timestamp,
    website_url: data.website_url,
  }

  return fetchApi<SupportTicketResponse>('/support/tickets', {
    method: 'POST',
    body: payload,
    ...(token ? { token } : {}),
  })
}

export async function submitContactMessage(
  data: ContactSubmissionData
): Promise<SupportTicketResponse> {
  const token = getAccessToken()

  const payload = {
    name: data.name,
    email: data.email,
    phone: data.phone,
    issue_description: data.issueDescription,
    contact_method: data.contactMethod,
    category: data.category,
    subject_line: data.subjectLine,
    is_anonymous: data.isAnonymous,
    website_url: data.websiteUrl,
    turnstile_token: data.turnstileToken,
    timestamp: data.timestamp,
  }

  return fetchApi<SupportTicketResponse>('/support/tickets', {
    method: 'POST',
    body: payload,
    ...(token ? { token } : {}),
  })
}

export async function getSupportTicket(ticketId: string): Promise<SupportTicket> {
  const token = getAccessToken()

  return fetchApi<SupportTicket>(`/support/tickets/${ticketId}`, {
    method: 'GET',
    ...(token ? { token } : {}),
  })
}

export async function listUserSupportTickets(): Promise<SupportTicket[]> {
  const token = getAccessToken()

  const response = await fetchApi<{ tickets: SupportTicket[] }>('/support/tickets/user/me', {
    method: 'GET',
    ...(token ? { token } : {}),
  })

  return response.tickets
}

export async function updateSupportTicketStatus(
  ticketId: string,
  status: string
): Promise<SupportTicket> {
  const token = getAccessToken()

  return fetchApi<SupportTicket>(`/support/tickets/${ticketId}`, {
    method: 'PATCH',
    body: { status },
    ...(token ? { token } : {}),
  })
}

export async function addSupportTicketNote(
  ticketId: string,
  note: string
): Promise<SupportTicket> {
  const token = getAccessToken()

  return fetchApi<SupportTicket>(`/support/tickets/${ticketId}/notes`, {
    method: 'POST',
    body: { note },
    ...(token ? { token } : {}),
  })
}

export async function closeSupportTicket(ticketId: string): Promise<SupportTicket> {
  const token = getAccessToken()

  return fetchApi<SupportTicket>(`/support/tickets/${ticketId}/close`, {
    method: 'POST',
    ...(token ? { token } : {}),
  })
}

// ----- Triage helpers --------------------------------------------------------

function _buildQuery(filters: TriageFilters): string {
  const params = new URLSearchParams()
  Object.entries(filters).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    params.set(key, String(value))
  })
  const qs = params.toString()
  return qs ? `?${qs}` : ''
}

export async function listTriageTickets(
  filters: TriageFilters = {}
): Promise<TriageListResponse> {
  const token = getAccessToken()
  return fetchApi<TriageListResponse>(
    `/support/tickets${_buildQuery(filters)}`,
    {
      method: 'GET',
      ...(token ? { token } : {}),
    }
  )
}

export async function getTriageTicket(ticketId: number): Promise<TriageTicket> {
  const token = getAccessToken()
  return fetchApi<TriageTicket>(`/support/tickets/${ticketId}`, {
    method: 'GET',
    ...(token ? { token } : {}),
  })
}

export interface TriagePatchPayload {
  status?: TicketStatus
  category?: string
  assigned_to_id?: number // -1 to release
  internal_notes?: string
}

export async function patchTriageTicket(
  ticketId: number,
  payload: TriagePatchPayload
): Promise<TriageTicket> {
  const token = getAccessToken()
  return fetchApi<TriageTicket>(`/support/tickets/${ticketId}`, {
    method: 'PATCH',
    body: payload,
    ...(token ? { token } : {}),
  })
}

export async function postTriageResponse(
  ticketId: number,
  body: string,
  setStatus?: 'in_progress' | 'resolved' | 'closed'
): Promise<TriageTicket> {
  const token = getAccessToken()
  return fetchApi<TriageTicket>(`/support/tickets/${ticketId}/responses`, {
    method: 'POST',
    body: { body, set_status: setStatus },
    ...(token ? { token } : {}),
  })
}

export async function listTriageEvents(ticketId: number): Promise<TriageEvent[]> {
  const token = getAccessToken()
  return fetchApi<TriageEvent[]>(`/support/tickets/${ticketId}/events`, {
    method: 'GET',
    ...(token ? { token } : {}),
  })
}

export const SUPPORT_CATEGORIES: Array<{ value: string; label: string }> = [
  { value: 'reference', label: 'Reference / research help' },
  { value: 'circulation', label: 'Account or library card' },
  { value: 'programs_events', label: 'Programs & events' },
  { value: 'youth', label: 'Children & families' },
  { value: 'teen', label: 'Teens' },
  { value: 'acquisitions', label: 'Suggest a purchase' },
  { value: 'ill', label: 'Interlibrary loan' },
  { value: 'accessibility', label: 'Accessibility / ADA' },
  { value: 'discrimination', label: 'Discrimination complaint' },
  { value: 'book_concern', label: 'Concern about a book or program' },
  { value: 'records_request', label: 'Records request (FOIA)' },
  { value: 'board', label: 'Board of Trustees' },
  { value: 'donation', label: 'Donation or memorial' },
  { value: 'website_bug', label: 'Website bug' },
  { value: 'general', label: 'General inquiry' },
]
