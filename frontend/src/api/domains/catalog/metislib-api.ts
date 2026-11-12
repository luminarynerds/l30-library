/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { apiClient } from '@/lib/api-client'

export interface MetisLibEbook {
  id: number
  title: string
  author_name: string
  description: string | null
  isbn: string | null
  cover_url: string | null
  source_type: 'open_access' | 'indie'
  format: string
  language: string | null
  page_count: number | null
  average_rating: number | null
  total_ratings: number
  entry_type?: 'ebook' | 'indie_ebook'
  available_copies?: number
  total_copies?: number
}

export interface MetisLibCatalogResponse {
  items: MetisLibEbook[]
  total: number
  page: number
  pages: number
}

export interface MetisLibBorrowResponse {
  access_id: number
  ebook_id: number
  status: string
  expires_at: string | null
  download_url: string
}

export interface MetisLibCheckout {
  access_id: number
  ebook_id: number
  title: string
  author_name: string
  cover_url: string | null
  format: string
  status: string
  expires_at: string | null
  download_url: string | null
}

export async function browseMetisLibEbooks(params: {
  q?: string
  source_type?: 'open_access' | 'indie'
  page?: number
  per_page?: number
}): Promise<MetisLibCatalogResponse> {
   
  return apiClient<MetisLibCatalogResponse>('/ebooks', { params: params as Record<string, string | number | boolean | undefined> })
}

export async function getMetisLibEbook(id: number, entryType?: 'ebook' | 'indie_ebook'): Promise<MetisLibEbook> {
  const params = entryType ? `?entry_type=${entryType}` : ''
  return apiClient<MetisLibEbook>(`/ebooks/${id}${params}`)
}

export async function getMetisLibFeatured(): Promise<MetisLibCatalogResponse> {
  return apiClient<MetisLibCatalogResponse>('/ebooks/featured')
}

export async function getMetisLibPopular(limit = 20): Promise<MetisLibCatalogResponse> {
  return apiClient<MetisLibCatalogResponse>(`/ebooks/popular?limit=${limit}`)
}

export async function getMetisLibCollections(): Promise<{ items: Array<{ id: number; title: string; description: string }>; total: number }> {
  return apiClient('/ebooks/collections')
}

export async function borrowMetisLibEbook(ebookId: number): Promise<MetisLibBorrowResponse> {
  return apiClient<MetisLibBorrowResponse>(`/ebooks/${ebookId}/borrow`, { method: 'POST' })
}

export async function placeMetisLibHold(ebookId: number): Promise<{ hold_id: number; position: number; status: string }> {
  return apiClient(`/ebooks/${ebookId}/hold`, { method: 'POST' })
}

export interface MetisLibHoldStatus {
  on_hold: boolean
  position?: number
  total_waiting?: number
  status?: 'waiting' | 'ready'
  hold_id?: number
  kind?: string
  ready_until?: string | null
}

export async function getMetisLibHoldStatus(ebookId: number): Promise<MetisLibHoldStatus> {
  return apiClient<MetisLibHoldStatus>(`/ebooks/${ebookId}/hold/status`)
}

export async function leaveMetisLibHold(ebookId: number): Promise<{ status: string }> {
  return apiClient(`/ebooks/${ebookId}/hold`, { method: 'DELETE' })
}

export async function getMetisLibDownloadUrl(ebookId: number): Promise<{ download_url: string }> {
  return apiClient(`/ebooks/${ebookId}/download`)
}

export async function returnMetisLibEbook(accessId: number, rating?: number): Promise<{ status: string }> {
  const body = rating ? { rating } : {}
  return apiClient(`/ebooks/${accessId}/return`, { method: 'POST', body: JSON.stringify(body) })
}

export async function getMyMetisLibCheckouts(): Promise<MetisLibCheckout[]> {
  const result = await apiClient<MetisLibCheckout[] | { items: MetisLibCheckout[] }>('/ebooks/me/checkouts')
  return Array.isArray(result) ? result : result.items || []
}

export async function overflowPurchase(ebookId: number): Promise<{ checkout_url: string; session_id: string }> {
  return apiClient(`/ebooks/${ebookId}/buy`, { method: 'POST' })
}
