/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Volunteer Management API Service
 *
 * Handles all API calls for volunteer management functionality
 */

import { api } from '@/lib/api-client';
import { API_BASE } from '@/api/types'

const BASE_URL = `${API_BASE}/volunteers`;

// ========================================================================
// Type Definitions
// ========================================================================

export interface VolunteerProfileUpdate {
  phone?: string
  email?: string
  address?: string
  emergency_contact_name?: string
  emergency_contact_phone?: string
  interests?: string[]
  availability_notes?: string
}

export interface VolunteerApplication {
  first_name: string
  last_name: string
  email: string
  phone: string
  address?: string
  interests: string[]
  skills?: string[]
  why_volunteer: string
  background_check_consent: boolean
  availability?: string
}

export interface ApplicationApprovalData {
  start_date?: string
  assigned_coordinator_id?: number
  initial_roles?: string[]
  orientation_scheduled?: string
}

/** Payload for POST /shifts. Field names/requiredness mirror ShiftCreateRequest. */
export interface ShiftCreateData {
  title: string
  role_category: string
  shift_date: string
  start_time: string
  end_time: string
  duration_hours: number
  description?: string
  location?: string
  volunteers_needed?: number
  required_skills?: string[]
}

/** Payload for PATCH /shifts/{id}. All fields optional (partial update). */
export interface ShiftUpdateData {
  title?: string
  role_category?: string
  shift_date?: string
  start_time?: string
  end_time?: string
  duration_hours?: number
  description?: string
  location?: string
  volunteers_needed?: number
  required_skills?: string[]
}

/** Row shape returned by GET /shifts/staff. */
export interface StaffShift {
  id: number
  title: string
  description?: string | null
  role_category: string
  shift_date: string
  start_time: string
  end_time: string
  location?: string | null
  volunteers_needed: number
  volunteers_signed_up: number
  spots_available: number
  cancelled: boolean
}

/** Row shape returned by GET /hour-logs (staff queue). */
export interface PendingHourLog {
  id: number
  volunteer_id: number
  volunteer_name: string | null
  log_date: string
  hours: number
  activity_type: string
  description?: string | null
  status: string
}

export interface HourLog {
  log_date: string
  hours: number
  activity_type: string
  description?: string
  shift_signup_id?: number
}

export interface VolunteerSkill {
  skill_name: string
  proficiency_level?: string
  years_of_experience?: number
  description?: string
}

// Plain-language labels for HourLogStatus enum values.
export const HOUR_LOG_STATUS_LABELS: Record<string, string> = {
  pending: 'Draft',
  submitted: 'Awaiting verification',
  verified: 'Verified',
  rejected: 'Not approved',
}

// Plain-language labels for VolunteerRoleCategory enum values.
export const ROLE_CATEGORY_LABELS: Record<string, string> = {
  delivery: 'Delivery',
  programming: 'Programming',
  tech_support: 'Tech Support',
  shelving: 'Shelving',
  reader_advisory: 'Reader Advisory',
  administrative: 'Administrative',
  patron_services: 'Patron Services',
  community_outreach: 'Community Outreach',
  cataloging: 'Cataloging',
  makerspace: 'Makerspace',
  other: 'Other',
}

export const volunteerApi = {
  // ========================================================================
  // Volunteer Profile Management
  // ========================================================================

  /**
   * Get current user's volunteer profile
   */
  getVolunteerProfile: async () => {
    return await api.get(`${BASE_URL}/me`);
  },

  /**
   * Get volunteer profile by ID
   */
  getVolunteerById: async (volunteerId: number) => {
    return await api.get(`${BASE_URL}/${volunteerId}`);
  },

  /**
   * Update volunteer profile
   */
  updateVolunteerProfile: async (volunteerId: number, data: VolunteerProfileUpdate) => {
    return await api.patch(`${BASE_URL}/${volunteerId}`, data);
  },

  // ========================================================================
  // Volunteer Application
  // ========================================================================

  /**
   * Submit a volunteer application
   */
  submitApplication: async (applicationData: VolunteerApplication) => {
    return await api.post(`${BASE_URL}/apply`, applicationData);
  },

  /**
   * Submit application for review
   */
  submitApplicationForReview: async (applicationId: number) => {
    return await api.post(`${BASE_URL}/apply/submit/${applicationId}`);
  },

  /**
   * Get my application status (staff only)
   */
  getApplicationStatus: async (applicationId: number) => {
    return await api.get(`${BASE_URL}/applications/${applicationId}`);
  },

  /**
   * List volunteer applications (staff only)
   */
  listApplications: async (status?: string) => {
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    return await api.get(`${BASE_URL}/applications?${params}`);
  },

  /**
   * Review volunteer application (staff only)
   */
  reviewApplication: async (
    applicationId: number,
    status: string,
    reviewNotes?: string,
    approvalData?: ApplicationApprovalData
  ) => {
    return await api.post(
      `${BASE_URL}/applications/${applicationId}/review`,
      {
        status,
        review_notes: reviewNotes,
        approval_data: approvalData,
      }
    );
  },

  // ========================================================================
  // Background Check
  // ========================================================================

  /**
   * Initiate background check (staff only)
   */
  initiateBackgroundCheck: async (
    volunteerId: number,
    checkType: string,
    providerName?: string
  ) => {
    return await api.post(
      `${BASE_URL}/background-checks/${volunteerId}`,
      {
        check_type: checkType,
        provider_name: providerName,
      }
    );
  },

  /**
   * Get background check status
   */
  getBackgroundCheckStatus: async (volunteerId: number) => {
    return await api.get(`${BASE_URL}/${volunteerId}/background-check`);
  },

  // ========================================================================
  // Training
  // ========================================================================

  /**
   * Get volunteer training records
   */
  getTraining: async (volunteerId?: number) => {
    const url = volunteerId
      ? `${BASE_URL}/${volunteerId}/training`
      : `${BASE_URL}/me/training`;
    return await api.get(url);
  },

  /**
   * Assign training to volunteer (staff only)
   */
  assignTraining: async (volunteerId: number, trainingTypeId: number) => {
    return await api.post(
      `${BASE_URL}/${volunteerId}/training/${trainingTypeId}`
    );
  },

  /**
   * Mark training as completed (staff only)
   */
  completeTraining: async (
    volunteerId: number,
    trainingId: number,
    trainerId?: number,
    completionNotes?: string
  ) => {
    return await api.post(
      `${BASE_URL}/${volunteerId}/training/${trainingId}/complete`,
      {
        trainer_id: trainerId,
        completion_notes: completionNotes,
      }
    );
  },

  // ========================================================================
  // Shifts
  // ========================================================================

  /**
   * Create a volunteer shift (staff only)
   */
  createShift: async (shiftData: ShiftCreateData) => {
    return await api.post(`${BASE_URL}/shifts`, shiftData);
  },

  /**
   * Edit a volunteer shift (partial update, staff only)
   */
  updateShift: async (shiftId: number, updates: ShiftUpdateData) => {
    return await api.patch(`${BASE_URL}/shifts/${shiftId}`, updates);
  },

  /**
   * Soft-cancel a shift; signups/history are kept (staff only)
   */
  cancelShift: async (shiftId: number) => {
    return await api.post(`${BASE_URL}/shifts/${shiftId}/cancel`);
  },

  /**
   * Get available shifts for sign-up
   */
  getAvailableShifts: async (roleCategory?: string, fromDate?: string) => {
    const params = new URLSearchParams();
    if (roleCategory) params.append('role_category', roleCategory);
    if (fromDate) params.append('from_date', fromDate);
    // Backend wraps the list in a pagination envelope; callers want the array.
    const response = await api.get(`${BASE_URL}/shifts?${params}`);
    return response?.shifts ?? [];
  },

  /**
   * List shifts for staff management (staff only). Unlike getAvailableShifts,
   * can optionally include cancelled shifts.
   */
  listShiftsStaff: async (opts?: {
    roleCategory?: string
    fromDate?: string
    includeCancelled?: boolean
    page?: number
    limit?: number
  }) => {
    const params = new URLSearchParams();
    if (opts?.roleCategory) params.append('role_category', opts.roleCategory);
    if (opts?.fromDate) params.append('from_date', opts.fromDate);
    if (opts?.includeCancelled) params.append('include_cancelled', 'true');
    if (opts?.page) params.append('page', String(opts.page));
    if (opts?.limit) params.append('limit', String(opts.limit));
    return await api.get(`${BASE_URL}/shifts/staff?${params}`);
  },

  /**
   * Get my signed up shifts
   */
  getMyShifts: async () => {
    return await api.get(`${BASE_URL}/me/shifts`);
  },

  /**
   * Sign up for a shift
   */
  signupForShift: async (shiftId: number) => {
    return await api.post(`${BASE_URL}/shifts/${shiftId}/signup`);
  },

  /**
   * Confirm shift signup (staff only)
   */
  confirmShiftSignup: async (signupId: number) => {
    return await api.post(
      `${BASE_URL}/signups/${signupId}/confirm`
    );
  },

  /**
   * Cancel shift signup
   */
  cancelShiftSignup: async (signupId: number) => {
    return await api.delete(`${BASE_URL}/signups/${signupId}`);
  },

  // ========================================================================
  // Hour Logging
  // ========================================================================

  /**
   * Log volunteer hours
   */
  logHours: async (volunteerId: number, logData: HourLog) => {
    return await api.post(
      `${BASE_URL}/${volunteerId}/hours/log`,
      logData
    );
  },

  /**
   * Submit hour log for verification
   */
  submitHourLog: async (logId: number) => {
    return await api.post(
      `${BASE_URL}/hour-logs/${logId}/submit`
    );
  },

  /**
   * Verify hours (staff only)
   */
  verifyHours: async (logId: number, verificationNotes?: string) => {
    return await api.post(
      `${BASE_URL}/hour-logs/${logId}/verify`,
      {
        verification_notes: verificationNotes,
      }
    );
  },

  /**
   * Cross-volunteer hour-log queue for staff review (staff only)
   */
  listPendingHourLogs: async (status: string = 'submitted', opts?: { page?: number; limit?: number }) => {
    const params = new URLSearchParams();
    params.append('status', status);
    if (opts?.page) params.append('page', String(opts.page));
    if (opts?.limit) params.append('limit', String(opts.limit));
    return await api.get(`${BASE_URL}/hour-logs?${params}`);
  },

  /**
   * Reject a submitted hour log; requires a reason (staff only)
   */
  rejectHours: async (logId: number, reason: string) => {
    return await api.post(
      `${BASE_URL}/hour-logs/${logId}/reject`,
      { reason }
    );
  },

  /**
   * Get volunteer hour logs and summary
   */
  getHourLogs: async (volunteerId?: number) => {
    const url = volunteerId
      ? `${BASE_URL}/${volunteerId}/hours`
      : `${BASE_URL}/me/hours`;
    return await api.get(url);
  },

  /**
   * Get hours summary
   */
  getHoursSummary: async () => {
    return await api.get(`${BASE_URL}/me/hours/summary`);
  },

  // ========================================================================
  // Skills
  // ========================================================================

  /**
   * Add skill to volunteer profile
   */
  addSkill: async (volunteerId: number, skillData: VolunteerSkill) => {
    return await api.post(
      `${BASE_URL}/${volunteerId}/skills`,
      skillData
    );
  },

  /**
   * Get volunteer skills
   */
  getSkills: async (volunteerId?: number) => {
    const url = volunteerId
      ? `${BASE_URL}/${volunteerId}/skills`
      : `${BASE_URL}/me/skills`;
    return await api.get(url);
  },

  /**
   * Get skill-matched opportunities
   */
  getSkillMatches: async (volunteerId?: number) => {
    const url = volunteerId
      ? `${BASE_URL}/${volunteerId}/skill-matches`
      : `${BASE_URL}/me/skill-matches`;
    return await api.get(url);
  },

  // ========================================================================
  // Milestones
  // ========================================================================

  /**
   * Get volunteer milestones
   */
  getMilestones: async (volunteerId?: number) => {
    const url = volunteerId
      ? `${BASE_URL}/${volunteerId}/milestones`
      : `${BASE_URL}/me/milestones`;
    return await api.get(url);
  },

  // ========================================================================
  // Appreciation
  // ========================================================================

  /**
   * Record appreciation/gift for volunteer (staff only)
   */
  recordAppreciation: async (
    volunteerId: number,
    appreciationType: string,
    description: string,
    reason?: string,
    occasion?: string,
    madePublic?: boolean
  ) => {
    return await api.post(
      `${BASE_URL}/${volunteerId}/appreciation`,
      {
        appreciation_type: appreciationType,
        description,
        reason,
        occasion,
        made_public: madePublic,
      }
    );
  },

  /**
   * Get appreciation history
   */
  getAppreciation: async (volunteerId?: number) => {
    const url = volunteerId
      ? `${BASE_URL}/${volunteerId}/appreciation`
      : `${BASE_URL}/me/appreciation`;
    return await api.get(url);
  },

  // ========================================================================
  // Reports & Analytics
  // ========================================================================

  /**
   * Get volunteer statistics (staff only)
   */
  getVolunteerStats: async (volunteerId: number) => {
    return await api.get(
      `${BASE_URL}/${volunteerId}/stats`
    );
  },

  /**
   * Get volunteer program overview (staff only)
   */
  getVolunteerProgramOverview: async () => {
    return await api.get(`${BASE_URL}/program/overview`);
  },

  /**
   * Get volunteer roster (staff only)
   */
  getRoster: async () => {
    return await api.get(`${BASE_URL}/roster`);
  },

  /**
   * Export volunteer hours report (staff only)
   */
  exportHoursReport: async (volunteerId?: number, format: string = 'csv') => {
    const url = volunteerId
      ? `${BASE_URL}/${volunteerId}/hours/export?format=${format}`
      : `${BASE_URL}/hours/export?format=${format}`;
    return await api.get(url);
  },
};