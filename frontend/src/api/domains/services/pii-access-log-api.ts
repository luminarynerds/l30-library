/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * PII Access Log API client.
 *
 * Fire-and-forget audit-log write for staff PII surfaces. The hook layer
 * (see `usePiiAccessLog`) is the preferred caller — it gives you a stable
 * callback identity that's safe inside `useEffect` / `useQuery` callbacks.
 *
 * Failure mode: server-side errors are logged as a Sentry breadcrumb so
 * the calling component never sees a thrown error. PII audit failures
 * must NEVER break the surface the patron PII is being viewed on.
 */
import api from '@/lib/api-client'
import { addBreadcrumb } from '@/lib/sentry-lazy'

export type PIIAccessAction = 'read' | 'reveal' | 'export' | 'print'

export interface LogPiiAccessPayload {
  patronId: number
  subjectType: string
  action: PIIAccessAction
  subjectId?: number | null
  reason?: string | null
}

export interface PIIAccessLogReadResponse {
  id: number
  user_id: number
  patron_id: number | null
  subject_type: string | null
  subject_id: number | null
  action: string | null
  reason: string | null
  accessed_at: string
}

export async function logPiiAccess(
  payload: LogPiiAccessPayload,
): Promise<PIIAccessLogReadResponse | null> {
  const body: Record<string, unknown> = {
    patron_id: payload.patronId,
    subject_type: payload.subjectType,
    action: payload.action,
  }
  if (payload.subjectId !== undefined && payload.subjectId !== null) {
    body.subject_id = payload.subjectId
  }
  if (payload.reason !== undefined && payload.reason !== null) {
    body.reason = payload.reason
  }

  try {
    return await api.post<PIIAccessLogReadResponse>('/api/v1/pii-access-log/', body)
  } catch (err) {
    // Fail-soft. We don't want the staff surface to see a 500 just
    // because the audit-log endpoint hiccuped.
    addBreadcrumb({
      category: 'pii_access_log',
      level: 'warning',
      message: 'logPiiAccess failed',
      data: {
        patron_id: payload.patronId,
        subject_type: payload.subjectType,
        action: payload.action,
        error: err instanceof Error ? err.message : String(err),
      },
    })
    return null
  }
}
