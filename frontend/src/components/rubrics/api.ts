/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
// Rubrics API Service

import { fetchApi } from '@/api/fetchApi';
import type {
  Rubric,
  RubricAssessment,
  RubricAssessmentCreatePayload,
  RubricAssessmentUpdatePayload,
  RubricCreatePayload,
  RubricCriterionCreatePayload,
  RubricUsageStats,
} from './types';

export const rubricsApi = {
  // List rubrics
  async list(params?: {
    category?: string;
    is_featured?: boolean;
    search?: string;
    skip?: number;
    limit?: number;
  }): Promise<Rubric[]> {
    const searchParams = new URLSearchParams();
    if (params?.category) searchParams.set('category', params.category);
    if (params?.is_featured !== undefined) searchParams.set('is_featured', String(params.is_featured));
    if (params?.search) searchParams.set('search', params.search);
    if (params?.skip) searchParams.set('skip', String(params.skip));
    if (params?.limit) searchParams.set('limit', String(params.limit));

    const path = searchParams.toString() ? `/rubrics?${searchParams}` : '/rubrics';
    return fetchApi(path);
  },

  // Get categories
  async getCategories(): Promise<string[]> {
    return fetchApi('/rubrics/categories');
  },

  // Get single rubric with criteria
  async get(id: number): Promise<Rubric> {
    return fetchApi(`/rubrics/${id}`);
  },

  // Create rubric (admin/staff)
  async create(data: RubricCreatePayload): Promise<Rubric> {
    return fetchApi('/rubrics', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // Update rubric (admin/staff)
  async update(id: number, data: Partial<RubricCreatePayload>): Promise<Rubric> {
    return fetchApi(`/rubrics/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  // Delete rubric (admin)
  async delete(id: number): Promise<void> {
    await fetchApi(`/rubrics/${id}`, { method: 'DELETE' });
  },

  // Add criterion to rubric
  async addCriterion(rubricId: number, data: RubricCriterionCreatePayload): Promise<Rubric> {
    return fetchApi(`/rubrics/${rubricId}/criteria`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // Update criterion
  async updateCriterion(
    rubricId: number,
    criterionId: number,
    data: Partial<RubricCriterionCreatePayload>
  ): Promise<Rubric> {
    return fetchApi(`/rubrics/${rubricId}/criteria/${criterionId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  // Delete criterion
  async deleteCriterion(rubricId: number, criterionId: number): Promise<void> {
    await fetchApi(`/rubrics/${rubricId}/criteria/${criterionId}`, { method: 'DELETE' });
  },

  // ===== ASSESSMENTS =====

  // Create assessment
  async createAssessment(rubricId: number, data: RubricAssessmentCreatePayload): Promise<RubricAssessment> {
    return fetchApi(`/rubrics/${rubricId}/assessments`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  // List my assessments for a rubric
  async listAssessments(rubricId: number): Promise<RubricAssessment[]> {
    return fetchApi(`/rubrics/${rubricId}/assessments`);
  },

  // Get assessment with rubric details
  async getAssessment(rubricId: number, assessmentId: number): Promise<RubricAssessment> {
    return fetchApi(`/rubrics/${rubricId}/assessments/${assessmentId}`);
  },

  // Update assessment
  async updateAssessment(
    rubricId: number,
    assessmentId: number,
    data: RubricAssessmentUpdatePayload
  ): Promise<RubricAssessment> {
    return fetchApi(`/rubrics/${rubricId}/assessments/${assessmentId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  // Delete assessment
  async deleteAssessment(rubricId: number, assessmentId: number): Promise<void> {
    await fetchApi(`/rubrics/${rubricId}/assessments/${assessmentId}`, { method: 'DELETE' });
  },

  // Get rubric stats (admin/staff)
  async getStats(rubricId: number): Promise<RubricUsageStats> {
    return fetchApi(`/rubrics/${rubricId}/stats`);
  },
};