/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
// ==================== Genealogy Services API ====================
// API client for genealogy inquiries, training courses, and community archives

import { api } from '@/lib/api-client'
import { API_BASE } from '@/api/types'

const BASE = `${API_BASE}/genealogy`

// ============================================================================
// Types
// ============================================================================

export interface GenealogyInquiry {
  id: number
  user_id: number | null
  first_name: string
  last_name: string
  email: string
  phone: string | null
  preferred_contact: string
  research_topic: string
  description: string
  current_challenges: string | null
  status: 'new' | 'in_progress' | 'responded' | 'closed'
  response_from_genealogist: string | null
  responded_at: string | null
  responded_by: number | null
  created_at: string
  updated_at: string
}

export interface GenealogyInquiryCreate {
  first_name: string
  last_name: string
  email: string
  phone?: string | null
  preferred_contact: string
  research_topic: string
  description: string
  current_challenges?: string | null
}

export interface GenealogyInquirySummary {
  id: number
  first_name: string
  last_name: string
  email: string
  research_topic: string
  status: string
  created_at: string
}

export interface GenealogyTrainingCourse {
  id: number
  title: string
  description: string
  duration_minutes: number
  difficulty_level: 'beginner' | 'intermediate' | 'advanced'
  next_session_day: string | null
  next_session_time: string | null
  modules: string | null
  prerequisites: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CourseEnrollment {
  id: number
  user_id: number
  course_id: number
  status: 'registered' | 'attended' | 'completed' | 'cancelled'
  enrolled_at: string
  attended_at: string | null
  completed_at: string | null
}

export interface CourseEnrollmentWithCourse extends CourseEnrollment {
  course?: GenealogyTrainingCourse
}

export interface CommunityArchiveSubmission {
  id: number
  user_id: number | null
  submitter_name: string
  submitter_email: string
  submitter_phone: string | null
  submitter_relationship: string | null
  material_type: string
  title: string
  description: string
  date_or_period: string | null
  location: string | null
  people_involved: string | null
  historical_significance: string | null
  file_url: string | null
  file_type: string | null
  is_public: boolean
  access_level: string
  status: 'submitted' | 'under_review' | 'approved' | 'published' | 'rejected'
  review_notes: string | null
  creative_commons_license: string
  published_at: string | null
  created_at: string
}

export interface CommunityArchiveSubmissionPublic {
  id: number
  submitter_name: string
  material_type: string
  title: string
  description: string
  date_or_period: string | null
  location: string | null
  file_url: string | null
  file_type: string | null
  published_at: string
}

export interface CommunityArchiveSubmissionCreate {
  submitter_name: string
  submitter_email: string
  submitter_phone?: string | null
  submitter_relationship?: string | null
  material_type: string
  title: string
  description: string
  date_or_period?: string | null
  location?: string | null
  people_involved?: string | null
  historical_significance?: string | null
  is_public?: boolean
  access_level?: string
  submitter_owns_material?: boolean
  has_permission?: boolean | null
  permission_details?: string | null
  creative_commons_license?: string
}

export interface GenealogyDashboard {
  active_courses: number
  pending_inquiries: number
  published_submissions: number
  latest_courses: GenealogyTrainingCourse[]
  latest_submissions: CommunityArchiveSubmissionPublic[]
}

// ============================================================================
// Inquiries API
// ============================================================================

export const genealogyInquiriesApi = {
  async create(data: GenealogyInquiryCreate): Promise<GenealogyInquiry> {
    return api.post(`${BASE}/inquiries`, data)
  },

  async list(params?: { status?: string; skip?: number; limit?: number }): Promise<GenealogyInquirySummary[]> {
    const query = new URLSearchParams()
    if (params?.status) query.set('status', params.status)
    if (params?.skip !== undefined) query.set('skip', String(params.skip))
    if (params?.limit !== undefined) query.set('limit', String(params.limit))
    const qs = query.toString()
    return api.get(`${BASE}/inquiries${qs ? `?${qs}` : ''}`)
  },

  async get(inquiryId: number): Promise<GenealogyInquiry> {
    return api.get(`${BASE}/inquiries/${inquiryId}`)
  },

  async update(inquiryId: number, data: { response_from_genealogist?: string; status?: string }): Promise<GenealogyInquiry> {
    return api.put(`${BASE}/inquiries/${inquiryId}`, data)
  },
}

// ============================================================================
// Training Courses API
// ============================================================================

export const genealogyCoursesApi = {
  async list(params?: { level?: string }): Promise<GenealogyTrainingCourse[]> {
    const query = new URLSearchParams()
    if (params?.level) query.set('level', params.level)
    const qs = query.toString()
    return api.get(`${BASE}/courses${qs ? `?${qs}` : ''}`)
  },

  async get(courseId: number): Promise<GenealogyTrainingCourse> {
    return api.get(`${BASE}/courses/${courseId}`)
  },
}

// ============================================================================
// Enrollment API
// ============================================================================

export const genealogyEnrollmentApi = {
  async enroll(courseId: number): Promise<CourseEnrollment> {
    return api.post(`${BASE}/enrollment`, { course_id: courseId })
  },

  async getMyEnrollments(): Promise<CourseEnrollment[]> {
    return api.get(`${BASE}/my-enrollments`)
  },
}

// ============================================================================
// Community Archives API
// ============================================================================

export const genealogyArchivesApi = {
  async submit(data: CommunityArchiveSubmissionCreate): Promise<CommunityArchiveSubmission> {
    return api.post(`${BASE}/archives/submit`, data)
  },

  async listPublic(params?: {
    material_type?: string
    location?: string
    skip?: number
    limit?: number
  }): Promise<CommunityArchiveSubmissionPublic[]> {
    const query = new URLSearchParams()
    if (params?.material_type) query.set('material_type', params.material_type)
    if (params?.location) query.set('location', params.location)
    if (params?.skip !== undefined) query.set('skip', String(params.skip))
    if (params?.limit !== undefined) query.set('limit', String(params.limit))
    const qs = query.toString()
    return api.get(`${BASE}/archives/public${qs ? `?${qs}` : ''}`)
  },

  async get(submissionId: number): Promise<CommunityArchiveSubmission> {
    return api.get(`${BASE}/archives/${submissionId}`)
  },
}

// ============================================================================
// Dashboard API
// ============================================================================

export const genealogyDashboardApi = {
  async get(): Promise<GenealogyDashboard> {
    return api.get(`${BASE}/dashboard`)
  },
}