/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'
import { getAccessToken } from '@/utils/tokenStore'

// Types
export interface Skill {
  id: number
  name: string
  description: string | null
  category: string
  difficulty_level: 'beginner' | 'intermediate' | 'advanced' | 'expert'
  estimated_hours: number | null
  prerequisites: number[]
  status: 'active' | 'inactive'
  created_at: string
  updated_at: string
}

export interface SkillGapAnalysis {
  skill_id: number
  skill_name: string
  required_level: number
  current_level: number
  gap: number
  priority: 'low' | 'medium' | 'high'
  recommended_training: string[]
}

export interface AssessmentQuestion {
  id: number
  skill_id: number
  question: string
  question_type: 'multiple_choice' | 'true_false' | 'short_answer'
  options: string[] | null
  correct_answer: string
  explanation: string | null
  difficulty: number
  order: number
}

export interface UserSkillProgress {
  user_id: number
  user_name: string
  skill_id: number
  skill_name: string
  current_level: number
  assessed_at: string | null
  training_completed: number
  training_total: number
}

export interface Cohort {
  id: number
  name: string
  description: string | null
  start_date: string
  end_date: string | null
  status: 'planned' | 'active' | 'completed' | 'cancelled'
  max_members: number | null
  member_count: number
  created_by: number
  created_at: string
  updated_at: string
}

export interface CohortMember {
  user_id: number
  user_name: string
  email: string
  joined_at: string
  role: 'member' | 'facilitator'
  progress_percentage: number
}

export interface CohortTraining {
  id: number
  cohort_id: number
  training_id: number
  training_name: string
  due_date: string | null
  required: boolean
  order: number
}

export interface SkillCreateData {
  name: string
  description?: string
  category: string
  difficulty_level: string
  estimated_hours?: number
  prerequisites?: number[]
}

export interface SkillUpdateData {
  name?: string
  description?: string
  category?: string
  difficulty_level?: string
  estimated_hours?: number
  prerequisites?: number[]
  status?: string
}

export interface CohortCreateData {
  name: string
  description?: string
  start_date: string
  end_date?: string
  max_members?: number
}

export interface CohortUpdateData {
  name?: string
  description?: string
  start_date?: string
  end_date?: string
  max_members?: number
  status?: string
}

// Skills API
export async function getSkills(params?: {
  category?: string
  difficulty_level?: string
  status?: string
  page?: number
  per_page?: number
}): Promise<{ items: Skill[]; total: number }> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  if (params?.category) searchParams.set('category', params.category)
  if (params?.difficulty_level) searchParams.set('difficulty_level', params.difficulty_level)
  if (params?.status) searchParams.set('status', params.status)
  if (params?.page) searchParams.set('page', params.page.toString())
  if (params?.per_page) searchParams.set('per_page', params.per_page.toString())
  const query = searchParams.toString() ? `?${searchParams}` : ''
  try {
    return await fetchApi<{ items: Skill[]; total: number }>(`/training/skills${query}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function getSkill(id: number): Promise<Skill> {
  const token = getAccessToken()
  try {
    return await fetchApi<Skill>(`/training/skills/${id}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function createSkill(data: SkillCreateData): Promise<Skill> {
  const token = getAccessToken()
  try {
    return await fetchApi<Skill>('/training/skills', {
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

export async function updateSkill(id: number, data: SkillUpdateData): Promise<Skill> {
  const token = getAccessToken()
  try {
    return await fetchApi<Skill>(`/training/skills/${id}`, {
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

export async function deleteSkill(id: number): Promise<void> {
  const token = getAccessToken()
  try {
    await fetchApi<void>(`/training/skills/${id}`, {
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

export async function getSkillGapAnalysis(): Promise<SkillGapAnalysis[]> {
  const token = getAccessToken()
  try {
    return await fetchApi<SkillGapAnalysis[]>('/training/skills/gap-analysis', { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function getSkillAssessmentQuestions(skillId: number): Promise<AssessmentQuestion[]> {
  const token = getAccessToken()
  try {
    return await fetchApi<AssessmentQuestion[]>(`/training/skills/${skillId}/questions`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function createAssessmentQuestion(skillId: number, data: Omit<AssessmentQuestion, 'id' | 'skill_id'>): Promise<AssessmentQuestion> {
  const token = getAccessToken()
  try {
    return await fetchApi<AssessmentQuestion>(`/training/skills/${skillId}/questions`, {
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

export async function deleteAssessmentQuestion(skillId: number, questionId: number): Promise<void> {
  const token = getAccessToken()
  try {
    await fetchApi<void>(`/training/skills/${skillId}/questions/${questionId}`, {
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

export async function reorderAssessmentQuestions(skillId: number, questionIds: number[]): Promise<void> {
  const token = getAccessToken()
  try {
    await fetchApi<void>(`/training/skills/${skillId}/questions/reorder`, {
      method: 'POST',
      ...(token ? { token } : {}),
      body: { question_ids: questionIds },
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function getUsersBySkillLevel(skillId: number, params?: { min_level?: number; max_level?: number }): Promise<UserSkillProgress[]> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  if (params?.min_level) searchParams.set('min_level', params.min_level.toString())
  if (params?.max_level) searchParams.set('max_level', params.max_level.toString())
  const query = searchParams.toString() ? `?${searchParams}` : ''
  try {
    return await fetchApi<UserSkillProgress[]>(`/training/skills/${skillId}/users${query}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

// Cohorts API
export async function getCohorts(params?: {
  status?: string
  page?: number
  per_page?: number
}): Promise<{ items: Cohort[]; total: number }> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  if (params?.status) searchParams.set('status', params.status)
  if (params?.page) searchParams.set('page', params.page.toString())
  if (params?.per_page) searchParams.set('per_page', params.per_page.toString())
  const query = searchParams.toString() ? `?${searchParams}` : ''
  try {
    const data = await fetchApi<Cohort[] | { items: Cohort[]; total: number }>(`/cohorts${query}`, { ...(token ? { token } : {}) })
    if (Array.isArray(data)) return { items: data, total: data.length }
    return data
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function getCohort(id: number): Promise<Cohort & { members: CohortMember[]; trainings: CohortTraining[] }> {
  const token = getAccessToken()
  try {
    return await fetchApi<Cohort & { members: CohortMember[]; trainings: CohortTraining[] }>(`/cohorts/${id}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function createCohort(data: CohortCreateData): Promise<Cohort> {
  const token = getAccessToken()
  try {
    return await fetchApi<Cohort>('/cohorts', {
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

export async function updateCohort(id: number, data: CohortUpdateData): Promise<Cohort> {
  const token = getAccessToken()
  try {
    return await fetchApi<Cohort>(`/cohorts/${id}`, {
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

export async function deleteCohort(id: number): Promise<void> {
  const token = getAccessToken()
  try {
    await fetchApi<void>(`/cohorts/${id}`, {
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

export async function addCohortMember(cohortId: number, data: { user_id: number; role?: string }): Promise<CohortMember> {
  const token = getAccessToken()
  try {
    return await fetchApi<CohortMember>(`/cohorts/${cohortId}/members`, {
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

export async function removeCohortMember(cohortId: number, userId: number): Promise<void> {
  const token = getAccessToken()
  try {
    await fetchApi<void>(`/cohorts/${cohortId}/members/${userId}`, {
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

export async function addCohortTraining(cohortId: number, data: { training_id: number; due_date?: string; required?: boolean }): Promise<CohortTraining> {
  const token = getAccessToken()
  try {
    return await fetchApi<CohortTraining>(`/cohorts/${cohortId}/trainings`, {
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

export async function removeCohortTraining(cohortId: number, trainingId: number): Promise<void> {
  const token = getAccessToken()
  try {
    await fetchApi<void>(`/cohorts/${cohortId}/trainings/${trainingId}`, {
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
