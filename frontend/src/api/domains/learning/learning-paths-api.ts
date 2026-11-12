/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'
import { getAccessToken } from '@/utils/tokenStore'

// Types - aligned with backend schemas
export interface LearningPath {
  id: number
  title: string
  description: string | null
  thumbnail_url: string | null
  status: 'draft' | 'published' | 'archived'
  is_public: boolean
  estimated_hours: number | null
  difficulty: 'beginner' | 'intermediate' | 'advanced' | null
  tags: string[]
  enforce_prerequisites: boolean
  created_at: string
  updated_at: string | null
  created_by_id: number | null
}

export interface LearningPathCourse {
  id: number
  learning_path_id: number
  course_id: number
  sort_order: number
  is_required: boolean
  prerequisite_course_ids: number[]
  description: string | null
  created_at: string
  // Extended fields from PathCourseWithDetails (only present in detail responses)
  course_title?: string | null
  course_thumbnail?: string | null
  course_estimated_minutes?: number | null
  course_difficulty?: string | null
  is_completed?: boolean
  can_access?: boolean
}

export interface LearningPathDetail extends LearningPath {
  courses: LearningPathCourse[]
  total_courses: number
  required_courses: number
  optional_courses: number
  total_minutes: number
  is_enrolled: boolean
  enrollment_progress: number
}

export interface LearningPathEnrollment {
  id: number
  user_id: number
  learning_path_id: number
  status: 'not_started' | 'in_progress' | 'completed'
  progress_percentage: number
  completed_course_ids: number[]
  enrolled_at: string
  started_at: string | null
  completed_at: string | null
  last_accessed_at: string | null
}

export interface LearningPathEnrollmentDetail extends LearningPathEnrollment {
  path_title: string
  path_thumbnail: string | null
  path_description: string | null
  total_courses: number
  completed_courses: number
  next_course_id: number | null
}

export interface LearningPathCreateData {
  title: string
  description?: string
  thumbnail_url?: string
  status?: string
  is_public?: boolean
  estimated_hours?: number
  difficulty?: string
  tags?: string[]
  enforce_prerequisites?: boolean
  courses?: PathCourseCreateData[]
}

export interface LearningPathUpdateData {
  title?: string
  description?: string
  thumbnail_url?: string
  status?: string
  is_public?: boolean
  estimated_hours?: number
  difficulty?: string
  tags?: string[]
  enforce_prerequisites?: boolean
}

export interface PathCourseCreateData {
  course_id: number
  sort_order?: number
  is_required?: boolean
  prerequisite_course_ids?: number[]
  description?: string
}

export interface PathCourseUpdateData {
  sort_order?: number
  is_required?: boolean
  prerequisite_course_ids?: number[]
  description?: string
}

// Public API
export async function getLearningPaths(params?: {
  status?: string
  is_public?: boolean
  skip?: number
  limit?: number
}): Promise<LearningPath[]> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  if (params?.status) searchParams.set('status', params.status)
  if (params?.is_public !== undefined) searchParams.set('is_public', String(params.is_public))
  if (params?.skip !== undefined) searchParams.set('skip', params.skip.toString())
  if (params?.limit) searchParams.set('limit', params.limit.toString())
  const query = searchParams.toString() ? `?${searchParams}` : ''
  try {
    return await fetchApi<LearningPath[]>(`/learning-paths${query}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function getLearningPath(id: number): Promise<LearningPathDetail> {
  const token = getAccessToken()
  try {
    return await fetchApi<LearningPathDetail>(`/learning-paths/${id}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function enrollInLearningPath(pathId: number): Promise<LearningPathEnrollment> {
  const token = getAccessToken()
  try {
    return await fetchApi<LearningPathEnrollment>(`/learning-paths/${pathId}/enroll`, {
      method: 'POST',
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function getMyLearningPathEnrollments(): Promise<LearningPathEnrollmentDetail[]> {
  const token = getAccessToken()
  try {
    return await fetchApi<LearningPathEnrollmentDetail[]>('/learning-paths/enrollments/my', { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function updateLearningPathProgress(pathId: number, data: { course_id: number; completed: boolean }): Promise<LearningPathEnrollment> {
  const token = getAccessToken()
  try {
    return await fetchApi<LearningPathEnrollment>(`/learning-paths/${pathId}/progress`, {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

// Admin API
export async function createLearningPath(data: LearningPathCreateData): Promise<LearningPath> {
  const token = getAccessToken()
  try {
    return await fetchApi<LearningPath>('/learning-paths', {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function updateLearningPath(id: number, data: LearningPathUpdateData): Promise<LearningPath> {
  const token = getAccessToken()
  try {
    return await fetchApi<LearningPath>(`/learning-paths/${id}`, {
      method: 'PUT',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function deleteLearningPath(id: number): Promise<void> {
  const token = getAccessToken()
  try {
    await fetchApi<void>(`/learning-paths/${id}`, {
      method: 'DELETE',
      ...(token ? { token } : {}),
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function addCourseToPath(pathId: number, data: PathCourseCreateData): Promise<LearningPathCourse> {
  const token = getAccessToken()
  try {
    return await fetchApi<LearningPathCourse>(`/learning-paths/${pathId}/courses`, {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function updatePathCourse(pathCourseId: number, data: PathCourseUpdateData): Promise<LearningPathCourse> {
  const token = getAccessToken()
  try {
    return await fetchApi<LearningPathCourse>(`/learning-paths/courses/${pathCourseId}`, {
      method: 'PUT',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function removePathCourse(pathCourseId: number): Promise<void> {
  const token = getAccessToken()
  try {
    await fetchApi<void>(`/learning-paths/courses/${pathCourseId}`, {
      method: 'DELETE',
      ...(token ? { token } : {}),
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

// Waitlist (Coming Soon)
export interface WaitlistStatus {
  joined: boolean
  waitlist_count: number
}

export async function getWaitlistStatus(pathId: number): Promise<WaitlistStatus> {
  const token = getAccessToken()
  try {
    return await fetchApi<WaitlistStatus>(`/learning-paths/${pathId}/waitlist`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function joinWaitlist(pathId: number): Promise<WaitlistStatus> {
  const token = getAccessToken()
  try {
    return await fetchApi<WaitlistStatus>(`/learning-paths/${pathId}/waitlist`, {
      method: 'POST',
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}
