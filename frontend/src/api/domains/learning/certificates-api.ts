/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'
import { getAccessToken } from '@/utils/tokenStore'
import { API_BASE } from '@/api/types'

// Types
export interface Certificate {
  id: number
  user_id: number
  course_id: number
  course_title: string
  certificate_number: string
  issued_at: string
  user_name: string
  completion_date: string
}

export interface CertificateVerification {
  certificate_number: string
  user_name: string
  recipient_first_name?: string
  course_title: string
  issued_at: string
  is_valid: boolean
}

// Certificate API
export async function issueCertificate(courseId: number): Promise<Certificate> {
  const token = getAccessToken()
  try {
    return await fetchApi<Certificate>(`/learning/courses/${courseId}/certificate`, {
      method: 'POST',
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function getMyCertificates(): Promise<Certificate[]> {
  const token = getAccessToken()
  try {
    return await fetchApi<Certificate[]>('/learning/certificates', { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function verifyCertificate(certificateNumber: string): Promise<CertificateVerification> {
  const token = getAccessToken()
  try {
    return await fetchApi<CertificateVerification>(`/learning/certificates/${encodeURIComponent(certificateNumber)}/verify`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function downloadCertificate(courseId: number): Promise<Blob> {
  const token = getAccessToken()
  const res = await fetch(`${API_BASE}/learning/certificates/${courseId}/download`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) throw new Error('Download failed')
  return res.blob()
}