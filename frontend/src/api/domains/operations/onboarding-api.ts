/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Staff Onboarding API Service
 *
 * Handles all API calls for staff onboarding functionality including:
 * - Onboarding initialization and management
 * - Pre-arrival checklist
 * - Orientation scheduling
 * - Training module assignments
 * - Policy acknowledgments
 * - System access provisioning
 * - Check-in meetings
 * - Feedback collection
 * - Probation tracking
 */

import { api } from '@/lib/api-client';
import { API_BASE } from '@/api/types'

const BASE_URL = `${API_BASE}/onboarding`;

// Type definitions
export interface OnboardingUpdate {
  department?: string
  position?: string
  start_date?: string
  expected_completion_date?: string
  manager_id?: number
  buddy_mentor_id?: number
  probation_end_date?: string
  status?: string
  actual_completion_date?: string
  completion_notes?: string
  probation_status?: string
  notes?: string
}

export const onboardingApi = {
  // ========================================================================
  // Staff Onboarding Profile Management
  // ========================================================================

  /**
   * Create a new staff onboarding record
   */
  createOnboarding: async (data: {
    user_id: number;
    department: string;
    position: string;
    start_date: string;
    expected_completion_date: string;
    manager_id?: number;
    buddy_mentor_id?: number;
    probation_end_date?: string;
  }) => {
    return await api.post(BASE_URL, data);
  },

  /**
   * Get current user's onboarding record
   */
  getMyOnboarding: async () => {
    return await api.get(`${BASE_URL}/me`);
  },

  /**
   * Get onboarding record by ID (staff only)
   */
  getOnboarding: async (onboardingId: number) => {
    return await api.get(`${BASE_URL}/${onboardingId}`);
  },

  /**
   * Update onboarding record
   */
  updateOnboarding: async (onboardingId: number, data: OnboardingUpdate) => {
    return await api.patch(`${BASE_URL}/${onboardingId}`, data);
  },

  /**
   * List all onboarding records (staff only)
   */
  listOnboardings: async (filters?: {
    status?: string;
    department?: string;
    skip?: number;
    limit?: number;
  }) => {
    const params = new URLSearchParams();
    if (filters) {
      if (filters.status) params.append('status', filters.status);
      if (filters.department) params.append('department', filters.department);
      if (filters.skip) params.append('skip', filters.skip.toString());
      if (filters.limit) params.append('limit', filters.limit.toString());
    }
    return await api.get(`${BASE_URL}?${params}`);
  },

  /**
   * Get onboarding progress summary (staff only)
   */
  getProgressSummary: async () => {
    return await api.get(`${BASE_URL}/progress/summary`);
  },

  // ========================================================================
  // Pre-Arrival Checklist
  // ========================================================================

  /**
   * Create a pre-arrival checklist item
   */
  createChecklistItem: async (onboardingId: number, data: {
    title: string;
    description?: string;
    category: string;
    assigned_to_id?: number;
    notes?: string;
  }) => {
    return await api.post(
      `${BASE_URL}/${onboardingId}/pre-arrival-checklist`,
      data
    );
  },

  /**
   * Update a pre-arrival checklist item
   */
  updateChecklistItem: async (
    onboardingId: number,
    itemId: number,
    data: {
      status?: string;
      completed_at?: string;
      notes?: string;
      evidence_url?: string;
    }
  ) => {
    return await api.patch(
      `${BASE_URL}/${onboardingId}/pre-arrival-checklist/${itemId}`,
      data
    );
  },

  // ========================================================================
  // Orientation Schedule
  // ========================================================================

  /**
   * Create an orientation schedule item
   */
  createOrientationItem: async (onboardingId: number, data: {
    activity_title: string;
    description?: string;
    scheduled_time: string;
    duration_minutes: number;
    location?: string;
    facilitator_id?: number;
  }) => {
    return await api.post(
      `${BASE_URL}/${onboardingId}/orientation`,
      data
    );
  },

  // ========================================================================
  // Training Modules
  // ========================================================================

  /**
   * Create a training module
   */
  createTrainingModule: async (data: {
    title: string;
    description?: string;
    category: string;
    duration_minutes: number;
    is_mandatory?: boolean;
    content_url?: string;
    delivery_type: string;
    passing_score?: number;
    order?: number;
  }) => {
    return await api.post(`${BASE_URL}/training-modules`, data);
  },

  /**
   * Assign a training module to a staff member
   */
  assignTrainingModule: async (onboardingId: number, data: {
    training_module_id: number;
    due_date: string;
  }) => {
    return await api.post(
      `${BASE_URL}/${onboardingId}/training-assignments`,
      data
    );
  },

  /**
   * Update a training module assignment
   */
  updateTrainingAssignment: async (
    onboardingId: number,
    assignmentId: number,
    data: {
      status?: string;
      score?: number;
      passed?: boolean;
      verified_by_id?: number;
      verified_at?: string;
      notes?: string;
    }
  ) => {
    return await api.patch(
      `${BASE_URL}/${onboardingId}/training-assignments/${assignmentId}`,
      data
    );
  },

  // ========================================================================
  // Policies
  // ========================================================================

  /**
   * Create a new policy
   */
  createPolicy: async (data: {
    title: string;
    content: string;
    category: string;
    effective_date: string;
    description?: string;
    version?: string;
    is_mandatory?: boolean;
  }) => {
    return await api.post(`${BASE_URL}/policies`, data);
  },

  /**
   * List all policies
   */
  listPolicies: async (category?: string) => {
    const params = new URLSearchParams();
    if (category) params.append('category', category);
    return await api.get(`${BASE_URL}/policies?${params}`);
  },

  /**
   * Acknowledge a policy
   */
  acknowledgePolicy: async (onboardingId: number, policyId: number) => {
    return await api.post(
      `${BASE_URL}/${onboardingId}/acknowledge-policy`,
      { policy_id: policyId }
    );
  },

  // ========================================================================
  // System Access
  // ========================================================================

  /**
   * Create a system access record
   */
  createSystemAccess: async (data: {
    system_name: string;
    access_type: string;
    description?: string;
    provisioning_instructions?: string;
    deprovisioning_instructions?: string;
  }) => {
    return await api.post(`${BASE_URL}/systems`, data);
  },

  /**
   * List all system access records
   */
  listSystems: async (accessType?: string) => {
    const params = new URLSearchParams();
    if (accessType) params.append('access_type', accessType);
    return await api.get(`${BASE_URL}/systems?${params}`);
  },

  /**
   * Request system access provisioning
   */
  requestSystemAccess: async (onboardingId: number, systemAccessId: number) => {
    return await api.post(
      `${BASE_URL}/${onboardingId}/request-access`,
      { system_access_id: systemAccessId }
    );
  },

  /**
   * Update system access provisioning status
   */
  updateSystemAccess: async (
    onboardingId: number,
    provisioningId: number,
    data: {
      status?: string;
      provisioned_by_id?: number;
      provisioned_at?: string;
      credentials_provided?: boolean;
      credentials_provided_at?: string;
      revoked_by_id?: number;
      revoked_at?: string;
      revocation_reason?: string;
      notes?: string;
    }
  ) => {
    return await api.patch(
      `${BASE_URL}/${onboardingId}/system-access/${provisioningId}`,
      data
    );
  },

  // ========================================================================
  // Check-in Meetings
  // ========================================================================

  /**
   * Schedule a check-in meeting
   */
  scheduleCheckInMeeting: async (onboardingId: number, data: {
    period: string;
    scheduled_date: string;
    scheduled_time?: string;
    scheduled_with_id?: number;
    topics?: string[];
    preparation_notes?: string;
  }) => {
    return await api.post(
      `${BASE_URL}/${onboardingId}/check-in-meetings`,
      data
    );
  },

  /**
   * Complete a check-in meeting
   */
  completeCheckInMeeting: async (
    onboardingId: number,
    meetingId: number,
    data: {
      scheduled_date?: string;
      scheduled_time?: string;
      scheduled_with_id?: number;
      topics?: string[];
      preparation_notes?: string;
      completed_at?: string;
      location?: string;
      meeting_notes?: string;
      feedback_from_new_hire?: string;
      feedback_from_manager?: string;
      action_items?: string[];
      next_steps?: string;
    }
  ) => {
    return await api.patch(
      `${BASE_URL}/${onboardingId}/check-in-meetings/${meetingId}`,
      data
    );
  },

  // ========================================================================
  // Feedback
  // ========================================================================

  /**
   * Submit onboarding feedback
   */
  submitFeedback: async (onboardingId: number, data: {
    feedback_type: string;
    rating?: number;
    comments?: string;
    is_anonymous?: boolean;
  }) => {
    return await api.post(
      `${BASE_URL}/${onboardingId}/feedback`,
      data
    );
  },
};