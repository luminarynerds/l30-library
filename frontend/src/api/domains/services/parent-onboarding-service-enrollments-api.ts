/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Service Enrollments API client for the parent-onboarding subdomain.
 *
 * Pure move from parent-onboarding-api.ts; no behaviour change.
 * Re-exported from parent-onboarding-api.ts barrel.
 */
import api from '@/lib/api-client';
import { API_BASE } from '@/api/types'
// EnrollmentFacilitationStatus moved here from parent-onboarding-api.ts barrel
export type EnrollmentFacilitationStatus =
  | 'identified'
  | 'contacted'
  | 'application_started'
  | 'application_submitted'
  | 'enrolled'
  | 'denied'
  | 'withdrawn';

// ============================================================================
// Helper Functions (local copy — identical to parent-onboarding-api.ts)
// ============================================================================

function buildQueryString(params?: Record<string, unknown>): string {
  if (!params) return '';
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      searchParams.append(key, String(value));
    }
  });
  const queryString = searchParams.toString();
  return queryString ? `?${queryString}` : '';
}

// ============================================================================
// Types
// ============================================================================

export interface ServiceEnrollment {
  id: number;
  patron_id: number;
  patron_name?: string;
  service_name: string;
  service_provider?: string;
  status: EnrollmentFacilitationStatus;
  coordinator_id?: number;
  coordinator_name?: string;
  identified_date: string;
  contacted_date?: string;
  application_date?: string;
  enrollment_date?: string;
  denial_reason?: string;
  withdrawal_reason?: string;
  notes?: string;
  follow_up_date?: string;
  created_at: string;
  updated_at?: string;
}

// ============================================================================
// Service Enrollments API
// ============================================================================

export async function createServiceEnrollment(data: {
  patron_id: number;
  service_name: string;
  service_provider?: string;
  coordinator_id?: number;
  notes?: string;
}): Promise<ServiceEnrollment> {
  return api.post<ServiceEnrollment>(`${API_BASE}/parent-onboarding/service-enrollments`, data);
}

export async function listServiceEnrollments(params?: {
  status?: EnrollmentFacilitationStatus;
  patron_id?: number;
  coordinator_id?: number;
  search?: string;
  limit?: number;
  offset?: number;
}): Promise<{ enrollments: ServiceEnrollment[]; total: number }> {
  return api.get(`${API_BASE}/parent-onboarding/service-enrollments${buildQueryString(params)}`);
}

export async function updateServiceEnrollmentStatus(id: number, data: {
  status: EnrollmentFacilitationStatus;
  denial_reason?: string;
  withdrawal_reason?: string;
  notes?: string;
}): Promise<ServiceEnrollment> {
  return api.post<ServiceEnrollment>(`${API_BASE}/parent-onboarding/service-enrollments/${id}/status`, data);
}
