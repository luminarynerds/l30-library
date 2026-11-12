/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from '@/lib/api-client'
import type { CatalogItem } from '@/api/domains/catalog/catalog-api'

export interface ReviewRecord {
  id: number
  catalog_item_id: number
  catalog_item: CatalogItem
  rating: number | null
  title: string | null
  body: string | null
  is_staff_review: boolean
  is_published: boolean
  reviewer_name: string | null
  created_at: string
  updated_at: string
}

export interface AggregateRating {
  average_rating: number | null
  rating_count: number
}

export interface CatalogItemReviews {
  aggregate: AggregateRating
  staff_reviews: ReviewRecord[]
  user_rating: number | null
}

export async function upsertReview(
  token: string,
  catalogItemId: number,
  data: { rating?: number; title?: string; body?: string },
): Promise<ReviewRecord> {
  return fetchApi<ReviewRecord>(`/reviews/${catalogItemId}`, {
    method: 'PUT',
    token,
    body: data,
  })
}

export async function deleteReview(
  token: string,
  catalogItemId: number,
): Promise<void> {
  await fetchApi(`/reviews/${catalogItemId}`, { method: 'DELETE', token })
}

export async function getCatalogItemReviews(
  catalogItemId: number,
  token?: string,
): Promise<CatalogItemReviews> {
  return fetchApi<CatalogItemReviews>(`/reviews/catalog-item/${catalogItemId}`, {
    ...(token ? { token } : {}),
  })
}

export async function getMyReviews(
  token: string,
  limit = 50,
  offset = 0,
): Promise<ReviewRecord[]> {
  return fetchApi<ReviewRecord[]>('/reviews/me', { token, params: { limit, offset } })
}

export async function getStaffReviews(
  limit = 50,
  offset = 0,
): Promise<ReviewRecord[]> {
  return fetchApi<ReviewRecord[]>('/reviews/staff', { params: { limit, offset } })
}

export async function publishReview(token: string, reviewId: number): Promise<ReviewRecord> {
  return fetchApi<ReviewRecord>(`/reviews/${reviewId}/publish`, { method: 'POST', token })
}

export async function unpublishReview(token: string, reviewId: number): Promise<ReviewRecord> {
  return fetchApi<ReviewRecord>(`/reviews/${reviewId}/unpublish`, { method: 'POST', token })
}
