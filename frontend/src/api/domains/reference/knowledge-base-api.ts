/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from '@/lib/api-client'

export interface KnowledgeBaseEntry {
  id: number
  category: string
  entry_type?: string
  title: string
  summary?: string | null
  content: string
  tags: string | string[] | null
  is_featured: boolean
  view_count: number
  helpful_count: number
  added_by_name: string | null
  created_at: string
  updated_at: string
}

export interface KnowledgeBasePaginatedResponse {
  items: KnowledgeBaseEntry[]
  total: number
}

export interface ReadAlikePaginatedResponse {
  items: ReadAlike[]
  total: number
}

export interface ReadAlike {
  id: number
  if_you_liked: string
  if_you_liked_author: string | null
  then_try: string
  then_try_author: string | null
  reason: string
  added_by_name: string | null
  created_at: string
  then_try_catalog_id?: number | null
  then_try_cover_url?: string | null
}

export interface KnowledgeBaseCategoryCounts {
  categories: Record<string, number>
  types: Record<string, number>
}

export async function getKnowledgeBaseCategoryCounts(): Promise<KnowledgeBaseCategoryCounts> {
  return fetchApi<KnowledgeBaseCategoryCounts>('/knowledge/categories/counts')
}

export async function getKnowledgeBaseEntries(params?: {
  category?: string
  search?: string
  q?: string
  entry_type?: string
  featured_only?: boolean
  limit?: number
  page?: number
  per_page?: number
}): Promise<KnowledgeBasePaginatedResponse> {
  const searchParams = new URLSearchParams()
  if (params?.category) searchParams.append('category', params.category)
  if (params?.search) searchParams.append('search', params.search)
  if (params?.q) searchParams.append('q', params.q)
  if (params?.entry_type) searchParams.append('entry_type', params.entry_type)
  if (params?.featured_only) searchParams.append('featured_only', 'true')
  if (params?.limit) searchParams.append('limit', String(params.limit))
  if (params?.page) searchParams.append('page', String(params.page))
  if (params?.per_page) searchParams.append('per_page', String(params.per_page))
  const qs = searchParams.toString()
  const result = await fetchApi<KnowledgeBaseEntry[] | KnowledgeBasePaginatedResponse>(`/knowledge${qs ? `?${qs}` : ''}`)
  if (Array.isArray(result)) {
    return { items: result, total: result.length }
  }
  return result
}

export async function getKnowledgeBaseEntry(id: number): Promise<KnowledgeBaseEntry> {
  return fetchApi(`/knowledge/${id}`)
}

export async function markEntryHelpful(id: number): Promise<void> {
  return fetchApi(`/knowledge/${id}/helpful`, { method: 'POST' })
}

export async function getReadAlikes(params?: {
  title?: string
  author?: string
}): Promise<ReadAlikePaginatedResponse> {
  const searchParams = new URLSearchParams()
  const searchParts = [params?.title, params?.author].filter(Boolean).join(' ')
  if (searchParts) searchParams.append('search', searchParts)
  const qs = searchParams.toString()
  const result = await fetchApi<ReadAlike[] | ReadAlikePaginatedResponse>(`/knowledge/read-alikes${qs ? `?${qs}` : ''}`)
  if (Array.isArray(result)) {
    return { items: result, total: result.length }
  }
  return result
}

export async function getFAQs(params?: {
  category?: string
  search?: string
}): Promise<KnowledgeBaseEntry[]> {
  const searchParams = new URLSearchParams()
  if (params?.category) searchParams.append('category', params.category)
  if (params?.search) searchParams.append('search', params.search)
  const qs = searchParams.toString()
  return fetchApi(`/knowledge/faqs${qs ? `?${qs}` : ''}`)
}
