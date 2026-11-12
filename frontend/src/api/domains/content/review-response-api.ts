/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Review Response API Service
 * Handles API calls for author/staff responses to reviews
 */

import { api } from '@/lib/api-client'

export type ModerationStatus = 'pending' | 'approved' | 'rejected'
export type ReviewType = 'event' | 'strain' | 'indie-ebook'

export interface ReviewResponse {
  id: number
  review_id?: number
  borrow_id?: number
  author_id: number
  author_name: string | null
  author_email: string | null
  is_staff_response: boolean
  content: string
  moderation_status: ModerationStatus
  moderated_by_id?: number
  moderated_at?: string
  moderation_reason?: string
  created_at: string
  updated_at: string
}

export interface CreateReviewResponseRequest {
  content: string
}

export interface UpdateReviewResponseRequest {
  content: string
}

export interface ApproveReviewResponseRequest {
  approved: boolean
  reason?: string
}

// Extended types for the staff UI with parent review info
export interface PendingReviewItem {
  review_id: number
  review_type: ReviewType
  review_content: string
  review_rating: number
  review_created_at: string
  reviewer_name: string | null
  // Related item info (event, strain, or ebook)
  item_id: number
  item_title: string
  item_type: string
  // Existing responses
  response_count: number
  has_staff_response: boolean
}

export interface PendingResponseItem {
  id: number
  review_type: ReviewType
  review_id?: number
  borrow_id?: number
  content: string
  author_name: string | null
  author_email: string | null
  is_staff_response: boolean
  moderation_status: ModerationStatus
  created_at: string
  // Parent review info
  review_content: string
  review_rating: number
  reviewer_name: string | null
  // Item info
  item_title: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  pages: number
}

export interface ReviewResponseStats {
  pending_moderation: number
  total_responses: number
  responses_by_type: {
    event: number
    strain: number
    'indie-ebook': number
  }
  responses_today: number
  avg_response_time_hours: number
}

// Staff management functions
export const reviewResponseStaffAPI = {
  // Get statistics for dashboard
  getStats: () =>
    api.get<ReviewResponseStats>('/review-responses/staff/stats'),

  // Get pending responses awaiting moderation (across all types)
  getPendingResponses: (page = 1, perPage = 20) =>
    api.get<PaginatedResponse<PendingResponseItem>>('/review-responses/staff/pending', {
      params: { page, per_page: perPage }
    }),

  // Get reviews that need staff response (no staff response yet)
  getReviewsNeedingResponse: (reviewType?: ReviewType, page = 1, perPage = 20) =>
    api.get<PaginatedResponse<PendingReviewItem>>('/review-responses/staff/reviews-needing-response', {
      params: { review_type: reviewType, page, per_page: perPage }
    }),

  // Batch approve multiple responses
  batchApprove: (responseIds: number[], reviewType: ReviewType) =>
    api.post('/review-responses/staff/batch-approve', {
      response_ids: responseIds,
      review_type: reviewType
    }),

  // Batch reject multiple responses
  batchReject: (responseIds: number[], reviewType: ReviewType, reason: string) =>
    api.post('/review-responses/staff/batch-reject', {
      response_ids: responseIds,
      review_type: reviewType,
      reason
    }),
}

// Event review responses
export const eventReviewResponseAPI = {
  create: (reviewId: number, data: CreateReviewResponseRequest) =>
    api.post<ReviewResponse>(`/review-responses/event/${reviewId}`, data),

  get: (reviewId: number, approvedOnly = true) =>
    api.get<ReviewResponse[]>(`/review-responses/event/${reviewId}`, {
      params: { approved_only: approvedOnly }
    }),

  update: (responseId: number, data: UpdateReviewResponseRequest) =>
    api.put<ReviewResponse>(`/review-responses/event-response/${responseId}`, data),

  delete: (responseId: number) =>
    api.delete(`/review-responses/event-response/${responseId}`),

  approve: (responseId: number, data: ApproveReviewResponseRequest) =>
    api.post<ReviewResponse>(`/review-responses/event-response/${responseId}/approve`, data),
}

// Strain review responses
export const strainReviewResponseAPI = {
  create: (reviewId: number, data: CreateReviewResponseRequest) =>
    api.post<ReviewResponse>(`/review-responses/strain/${reviewId}`, data),

  get: (reviewId: number, approvedOnly = true) =>
    api.get<ReviewResponse[]>(`/review-responses/strain/${reviewId}`, {
      params: { approved_only: approvedOnly }
    }),

  update: (responseId: number, data: UpdateReviewResponseRequest) =>
    api.put<ReviewResponse>(`/review-responses/strain-response/${responseId}`, data),

  delete: (responseId: number) =>
    api.delete(`/review-responses/strain-response/${responseId}`),

  approve: (responseId: number, data: ApproveReviewResponseRequest) =>
    api.post<ReviewResponse>(`/review-responses/strain-response/${responseId}/approve`, data),
}

// Indie ebook review responses
export const indieEbookReviewResponseAPI = {
  create: (borrowId: number, data: CreateReviewResponseRequest) =>
    api.post<ReviewResponse>(`/review-responses/indie-ebook/${borrowId}`, data),

  get: (borrowId: number, approvedOnly = true) =>
    api.get<ReviewResponse[]>(`/review-responses/indie-ebook/${borrowId}`, {
      params: { approved_only: approvedOnly }
    }),

  update: (responseId: number, data: UpdateReviewResponseRequest) =>
    api.put<ReviewResponse>(`/review-responses/indie-ebook-response/${responseId}`, data),

  delete: (responseId: number) =>
    api.delete(`/review-responses/indie-ebook-response/${responseId}`),

  approve: (responseId: number, data: ApproveReviewResponseRequest) =>
    api.post<ReviewResponse>(`/review-responses/indie-ebook-response/${responseId}/approve`, data),
}
