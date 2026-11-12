/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { api } from './api';
import { API_BASE } from '@/api/types'

export interface ContentFlag {
  id: number;
  review_id: number;
  review_type: string;
  flag_type: string;
  confidence_score: number;
  analysis_details: Record<string, unknown>;
  status: string;
  resolved_by?: string;
  resolved_at?: string;
  resolution_notes?: string;
  is_correct_flag?: boolean;
  staff_feedback?: string;
  created_at: string;
  updated_at: string;
  review_content?: ContentFlagReviewContent | null;
}

export interface ContentFlagReviewContent {
  review_id: number;
  review_type: string;
  comment: string | null;
  rating: number | null;
  patron_email: string | null;
  moderation_status: string | null;
  is_removed: number | null;
  event_id?: number | null;
  event_title?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface EventReviewEditRequest {
  comment: string;
  reason?: string;
}

export interface EventReviewDetail {
  id: number;
  event_id: number;
  patron_email: string;
  rating: number;
  comment: string | null;
  moderation_status: string;
  moderated_by: string | null;
  moderated_at: string | null;
  moderation_reason: string | null;
  is_removed: number;
  removal_reason: string | null;
  removed_by: string | null;
  removed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface FlagStatistics {
  total_flags: number;
  avg_confidence: number;
  high_confidence_flags: number;
  false_positives: number;
  false_negatives: number;
  false_positive_rate: number;
}

export interface FlagsFeedback {
  status: 'resolved' | 'false_positive' | 'false_negative';
  is_correct_flag?: boolean;
  resolution_notes?: string;
  staff_feedback?: string;
}

export interface FlagListResponse {
  items: ContentFlag[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export const contentFlagService = {
  async getFlaggedContent(
    page: number = 1,
    perPage: number = 20,
    filters?: {
      review_type?: string;
      status?: string;
      min_score?: number;
    }
  ): Promise<FlagListResponse> {
    const params = new URLSearchParams({
      page: page.toString(),
      per_page: perPage.toString(),
    });

    if (filters?.review_type) {
      params.append('review_type', filters.review_type);
    }
    if (filters?.status) {
      params.append('status', filters.status);
    }
    if (filters?.min_score) {
      params.append('min_score', filters.min_score.toString());
    }

    return api.get<FlagListResponse>(
      `${API_BASE}/admin/content-flags/?${params}`
    );
  },

  async getFlagDetails(flagId: number): Promise<ContentFlag> {
    return api.get<ContentFlag>(
      `${API_BASE}/admin/content-flags/${flagId}`
    );
  },

  async submitFeedback(flagId: number, feedback: FlagsFeedback): Promise<ContentFlag> {
    return api.post<ContentFlag>(
      `${API_BASE}/admin/content-flags/${flagId}/feedback`,
      feedback
    );
  },

  async resolveFlag(flagId: number, feedback: FlagsFeedback): Promise<ContentFlag> {
    return api.patch<ContentFlag>(
      `${API_BASE}/admin/content-flags/${flagId}/resolve`,
      feedback
    );
  },

  async moderateEventReview(
    reviewId: number,
    action: 'approve' | 'reject' | 'remove',
    reason?: string
  ): Promise<EventReviewDetail> {
    return api.post<EventReviewDetail>(
      `${API_BASE}/events/reviews/${reviewId}/moderate`,
      { action, reason }
    );
  },

  async editEventReview(
    reviewId: number,
    edit: EventReviewEditRequest
  ): Promise<EventReviewDetail> {
    return api.patch<EventReviewDetail>(
      `${API_BASE}/events/reviews/${reviewId}/edit`,
      edit
    );
  },

  async getStatistics(days: number = 30): Promise<FlagStatistics> {
    return api.get<FlagStatistics>(
      `${API_BASE}/admin/content-flags/statistics/summary?days=${days}`
    );
  },

  async getStatisticsByType(days: number = 30): Promise<Record<string, unknown>> {
    return api.get<Record<string, unknown>>(
      `${API_BASE}/admin/content-flags/statistics/by-type?days=${days}`
    );
  },

  async getStatisticsByReviewType(days: number = 30): Promise<Record<string, unknown>> {
    return api.get<Record<string, unknown>>(
      `${API_BASE}/admin/content-flags/statistics/by-review-type?days=${days}`
    );
  },
};