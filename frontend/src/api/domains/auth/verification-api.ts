/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Author Identity Verification API client
 */
import { apiClient } from '@/lib/api-client'
import { getAccessToken } from '@/utils/tokenStore'

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1'

// --- Types ---

export type EvidenceType = 'government_id' | 'social_profile' | 'publication_link'
export type EvidenceStatus = 'pending' | 'approved' | 'rejected' | 'additional_needed'

export interface VerificationLevelResponse {
  current_level: number
  level_name: string
  requirements_met: string[]
  requirements_remaining: string[]
  next_level_requirements: string[]
}

export interface EvidenceResponse {
  id: number
  evidence_type: EvidenceType
  status: EvidenceStatus
  url?: string
  has_file: boolean
  notes?: string
  reviewer_notes?: string
  created_at: string
  reviewed_at?: string
}

export interface VerificationQueueItem {
  id: number
  author_id: number
  author_pen_name: string
  evidence_type: EvidenceType
  status: EvidenceStatus
  url?: string
  has_file: boolean
  notes?: string
  created_at: string
}

// --- Author endpoints ---

export function getMyLevel(): Promise<VerificationLevelResponse> {
  return apiClient<VerificationLevelResponse>('/indie/verification/my-level')
}

export function submitEvidence(data: {
  evidence_type: EvidenceType
  url: string
  notes?: string
}): Promise<EvidenceResponse> {
  return apiClient<EvidenceResponse>('/indie/verification/evidence', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function uploadEvidenceFile(
  file: File,
  evidenceType: EvidenceType,
  notes?: string,
): Promise<EvidenceResponse> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('evidence_type', evidenceType)
  if (notes) formData.append('notes', notes)

  const token = getAccessToken()
  const res = await fetch(`${API_BASE}/indie/verification/evidence/upload`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  })

  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail || detail
    } catch { /* ignore */ }
    throw new Error(detail)
  }

  return res.json()
}

export function getMyEvidence(): Promise<EvidenceResponse[]> {
  return apiClient<EvidenceResponse[]>('/indie/verification/my-evidence')
}

// --- Staff endpoints ---

export function getVerificationQueue(): Promise<VerificationQueueItem[]> {
  return apiClient<VerificationQueueItem[]>('/indie/verification/staff/queue')
}

export function reviewEvidence(
  evidenceId: number,
  data: { status: 'approved' | 'rejected' | 'additional_needed'; notes?: string },
): Promise<EvidenceResponse> {
  return apiClient<EvidenceResponse>(`/indie/verification/staff/review/${evidenceId}`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}
