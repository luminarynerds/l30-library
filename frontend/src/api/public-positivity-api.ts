/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { API_BASE as API_ROOT } from '@/api/types'
export interface PatronSubmission {
  entry_type: string
  text: string
  patron_name?: string
  patron_email?: string
}

export interface PatronSubmissionResponse {
  message: string
  id: number
}

const API_BASE = `${API_ROOT}/public/positivity`

export async function submitPatronPositivity(
  submission: PatronSubmission
): Promise<PatronSubmissionResponse> {
  const response = await fetch(API_BASE, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(submission),
  })

  if (!response.ok) {
    const data = await response.json().catch(() => null)
    throw new Error(data?.detail || `Submission failed: ${response.statusText}`)
  }

  return response.json()
}