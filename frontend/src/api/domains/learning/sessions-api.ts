/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { API_BASE } from '@/api/types'
import { getAccessToken } from '@/utils/tokenStore'

export interface ModuleSession {
  id: number
  module_id: number
  title: string | null
  scheduled_at: string
  duration_minutes: number
  location: string | null
  facilitator_id: number | null
  max_participants: number | null
  materials: string[]
  notes: string | null
  is_cancelled: boolean
  rsvp_count: number
  created_at: string | null
  updated_at: string | null
}

export interface SessionRSVP {
  id: number
  session_id: number
  user_id: number
  status: string
  responded_at: string | null
}

async function authFetch(url: string, options?: RequestInit) {
  const token = getAccessToken()
  const headers: Record<string, string> = {
    ...(options?.headers as Record<string, string> || {}),
  }
  if (token) headers['Authorization'] = `Bearer ${token}`
  if (options?.body) headers['Content-Type'] = 'application/json'
  const res = await fetch(url, { ...options, headers })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(err.detail || 'Request failed')
  }
  return res.status === 204 ? null : res.json()
}

export async function getModuleSessions(moduleId: number): Promise<ModuleSession[]> {
  return authFetch(`${API_BASE}/learning/modules/${moduleId}/sessions`)
}

export async function createModuleSession(moduleId: number, data: {
  title?: string
  scheduled_at: string
  duration_minutes: number
  location?: string
  max_participants?: number
  materials?: string[]
  notes?: string
}): Promise<ModuleSession> {
  return authFetch(`${API_BASE}/learning/modules/${moduleId}/sessions`, {
    method: 'POST',
    body: JSON.stringify({ ...data, module_id: moduleId }),
  })
}

export async function updateModuleSession(sessionId: number, data: Partial<ModuleSession>): Promise<ModuleSession> {
  return authFetch(`${API_BASE}/learning/sessions/${sessionId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function cancelModuleSession(sessionId: number): Promise<void> {
  return authFetch(`${API_BASE}/learning/sessions/${sessionId}`, {
    method: 'DELETE',
  })
}

export async function rsvpToSession(sessionId: number, status: string = 'attending'): Promise<SessionRSVP> {
  return authFetch(`${API_BASE}/learning/sessions/${sessionId}/rsvp`, {
    method: 'POST',
    body: JSON.stringify({ status }),
  })
}

export async function getUpcomingSessions(): Promise<ModuleSession[]> {
  return authFetch(`${API_BASE}/learning/sessions/upcoming`)
}
