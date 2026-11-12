/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Donation Intake Workflow API client.
 *
 * Provides access to donation logging, review, processing,
 * and statistics for staff use.
 */

import { API_BASE } from '@/api/types'

const BASE = `${API_BASE}/donations`

// ============ Types ============

export type DonationStatus = 'pending' | 'under_review' | 'accepted' | 'declined' | 'processed'

export interface DonationRecord {
  id: number
  donor_name: string | null
  donor_email: string | null
  donor_phone: string | null
  donor_address: string | null
  is_anonymous: boolean
  tax_receipt_requested: boolean
  tax_receipt_sent: boolean
  title: string | null
  author: string | null
  isbn: string | null
  material_type: string | null
  quantity: number
  condition_notes: string | null
  estimated_value: number | null
  status: DonationStatus
  received_date: string
  received_by_id: number | null
  received_by_name: string | null
  reviewed_by_id: number | null
  reviewed_by_name: string | null
  reviewed_at: string | null
  decline_reason: string | null
  staff_notes: string | null
  catalog_item_id: number | null
  item_copy_id: number | null
  created_at: string
  updated_at: string | null
}

export interface DonationCreate {
  donor_name?: string
  donor_email?: string
  donor_phone?: string
  donor_address?: string
  is_anonymous?: boolean
  tax_receipt_requested?: boolean
  title?: string
  author?: string
  isbn?: string
  material_type?: string
  quantity?: number
  condition_notes?: string
  estimated_value?: number
  received_date?: string
  staff_notes?: string
}

export interface DonationUpdate {
  donor_name?: string
  donor_email?: string
  donor_phone?: string
  donor_address?: string
  is_anonymous?: boolean
  tax_receipt_requested?: boolean
  tax_receipt_sent?: boolean
  title?: string
  author?: string
  isbn?: string
  material_type?: string
  quantity?: number
  condition_notes?: string
  estimated_value?: number
  staff_notes?: string
}

export interface DonationReviewRequest {
  action: 'accept' | 'decline'
  decline_reason?: string
  staff_notes?: string
}

export interface DonationProcessRequest {
  catalog_item_id?: number
  create_new_catalog_item?: boolean
  location?: string
}

export interface DonationStats {
  total: number
  by_status: Record<DonationStatus, number>
}

// ============ API Helper ============

async function apiFetch<T>(token: string, endpoint: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(BASE + endpoint, {
    ...options,
    headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + token, ...options.headers },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(err.detail || err.error?.message || 'Request failed')
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

// ============ API Functions ============

export function listDonations(
  token: string,
  params: {
    status?: DonationStatus
    date_from?: string
    date_to?: string
    page?: number
    per_page?: number
  } = {}
): Promise<DonationRecord[]> {
  const searchParams = new URLSearchParams()
  if (params.status) searchParams.set('status', params.status)
  if (params.date_from) searchParams.set('date_from', params.date_from)
  if (params.date_to) searchParams.set('date_to', params.date_to)
  if (params.page) searchParams.set('page', String(params.page))
  if (params.per_page) searchParams.set('per_page', String(params.per_page))
  const qs = searchParams.toString()
  return apiFetch<DonationRecord[]>(token, qs ? '?' + qs : '')
}

export function getDonation(token: string, id: number): Promise<DonationRecord> {
  return apiFetch<DonationRecord>(token, `/${id}`)
}

export function createDonation(token: string, data: DonationCreate): Promise<DonationRecord> {
  return apiFetch<DonationRecord>(token, '', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function updateDonation(token: string, id: number, data: DonationUpdate): Promise<DonationRecord> {
  return apiFetch<DonationRecord>(token, `/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export function reviewDonation(
  token: string,
  id: number,
  data: DonationReviewRequest
): Promise<DonationRecord> {
  return apiFetch<DonationRecord>(token, `/${id}/review`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function processDonation(
  token: string,
  id: number,
  data: DonationProcessRequest
): Promise<DonationRecord> {
  return apiFetch<DonationRecord>(token, `/${id}/process`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function getDonationStats(token: string): Promise<DonationStats> {
  return apiFetch<DonationStats>(token, '/stats')
}
