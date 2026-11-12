/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { API_BASE } from '@/api/types'
import { getAccessToken } from '@/utils/tokenStore'

// Types
export interface Course {
  id: number
  title: string
  description: string | null
  thumbnail_url: string | null
  access_level: 'patron' | 'staff' | 'admin'
  is_published: boolean
  estimated_minutes: number | null
  difficulty: 'beginner' | 'intermediate' | 'advanced'
  sensory_warning: string | null
  xp_reward: number
  created_at: string
  updated_at: string | null
  module_count?: number
  lesson_count?: number
}

// Lifecycle stage values mirror backend CourseLifecycleStage (lowercase
// enum, models/learning.py). It is the single source of truth; the
// `is_published` field above is a read-only API-contract convenience
// derived server-side as `lifecycle_stage === 'published'` (PR-C4
// dropped the stored column + its compat shim).
export type CourseLifecycleStage =
  | 'draft'
  | 'published'
  | 'archived'

// Admin-only list item: GET /learning/admin/courses returns CourseListItemAdmin
// (backend schemas/learning.py: CourseListItemAdmin). Extra fields power the
// inline enrollment column + the impact-aware delete confirm. Patron-facing
// /learning/courses keeps Course so per-course enrollment counts aren't
// leaked to learners.
export interface CourseListItemAdmin extends Course {
  enrollment_count: number
  completion_count: number
  in_progress_count: number
  last_activity_at: string | null
  lifecycle_stage: CourseLifecycleStage
  last_reviewed_at: string | null
  review_due_at: string | null
  last_reviewed_by: { id: number; display_name: string } | null
  is_review_due: boolean
}

// One row of the append-only course_stage_transitions audit log.
export interface CourseStageTransitionRow {
  id: number
  from_stage: CourseLifecycleStage | null
  to_stage: CourseLifecycleStage
  actor: { id: number; display_name: string } | null
  note: string | null
  created_at: string
}

// Structured 400 detail from POST .../transition. authFetch() flattens
// dict detail to "[object Object]", so transitionCourseStage() uses its
// own fetch path and throws this instead — the badge menu needs
// allowed_targets / enrollment_count / requires_confirm to drive the
// confirm + "you may move to: X" toasts without string-sniffing.
export class CourseStageTransitionError extends Error {
  allowedTargets?: CourseLifecycleStage[]
  enrollmentCount?: number
  requiresConfirm?: boolean
  status: number
  constructor(
    message: string,
    status: number,
    extra?: {
      allowedTargets?: CourseLifecycleStage[]
      enrollmentCount?: number
      requiresConfirm?: boolean
    },
  ) {
    super(message)
    this.name = 'CourseStageTransitionError'
    this.status = status
    if (extra?.allowedTargets) this.allowedTargets = extra.allowedTargets
    if (extra?.enrollmentCount !== undefined) this.enrollmentCount = extra.enrollmentCount
    if (extra?.requiresConfirm !== undefined) this.requiresConfirm = extra.requiresConfirm
  }
}

export interface CourseCloneData {
  new_title: string
  include_unpublished_lessons: boolean
}

export interface Module {
  id: number
  course_id: number
  title: string
  description: string | null
  sort_order: number
  lessons: Lesson[]
}

export interface Lesson {
  id: number
  module_id: number
  title: string
  lesson_type: 'article' | 'video' | 'quiz' | 'sandbox' | 'lab'
  content: Record<string, unknown>
  estimated_minutes: number | null
  sensory_notes: string | null
  xp_reward: number
  sort_order: number
  summary?: string | null
  visual_aid_url?: string | null
  audio_narration_url?: string | null
  facilitator_notes?: string | null
}

export interface QuizQuestion {
  id: number
  lesson_id: number
  question_text: string
  question_type: string
  options: QuizOption[]
  explanation: string | null
  sort_order: number
}

export interface QuizOption {
  text: string
  is_correct: boolean
}

export interface LessonResource {
  id: number
  lesson_id: number
  title: string
  description: string | null
  resource_type: 'pdf' | 'checklist' | 'script' | 'video' | 'audio' | 'link'
  url: string
  sort_order: number
}

export interface CourseWithModules extends Course {
  modules: Module[]
}

// Create/Update types
export interface CourseCreateData {
  title: string
  description?: string
  thumbnail_url?: string
  access_level?: 'patron' | 'staff' | 'admin'
  estimated_minutes?: number
  difficulty?: 'beginner' | 'intermediate' | 'advanced'
  sensory_warning?: string
  xp_reward?: number
}

export interface CourseUpdateData {
  title?: string
  description?: string
  thumbnail_url?: string
  access_level?: 'patron' | 'staff' | 'admin'
  estimated_minutes?: number
  difficulty?: 'beginner' | 'intermediate' | 'advanced'
  sensory_warning?: string
  xp_reward?: number
}

export interface ModuleCreateData {
  course_id: number
  title: string
  description?: string
  sort_order?: number
}

export interface ModuleUpdateData {
  title?: string
  description?: string
  sort_order?: number
}

export interface LessonCreateData {
  module_id: number
  title: string
  lesson_type: 'article' | 'video' | 'quiz' | 'sandbox' | 'lab'
  content: Record<string, unknown>
  estimated_minutes?: number
  sensory_notes?: string
  xp_reward?: number
  sort_order?: number
  summary?: string
  visual_aid_url?: string
  audio_narration_url?: string
  facilitator_notes?: string
}

export interface LessonUpdateData {
  title?: string
  lesson_type?: 'article' | 'video' | 'quiz' | 'sandbox' | 'lab'
  content?: Record<string, unknown>
  estimated_minutes?: number
  sensory_notes?: string
  xp_reward?: number
  sort_order?: number
  summary?: string
  visual_aid_url?: string
  audio_narration_url?: string
  facilitator_notes?: string
}

export interface QuizQuestionCreateData {
  lesson_id: number
  question_text: string
  question_type?: string
  options: QuizOption[]
  explanation?: string
  sort_order?: number
}

export interface QuizQuestionUpdateData {
  question_text?: string
  question_type?: string
  options?: QuizOption[]
  explanation?: string
  sort_order?: number
}

export interface LessonResourceCreateData {
  lesson_id: number
  title: string
  description?: string
  resource_type: 'pdf' | 'checklist' | 'script' | 'video' | 'audio' | 'link'
  url: string
  sort_order?: number
}

// Enrollment types
export interface CourseEnrollment {
  id: number
  user_id: number
  course_id: number
  status: 'enrolled' | 'in_progress' | 'completed'
  enrolled_at: string
  started_at: string | null
  completed_at: string | null
  progress_percentage: number
}

// Lesson completion types
export interface LessonCompletion {
  id: number
  user_id: number
  lesson_id: number
  completed_at: string
  xp_earned: number
}

// Quiz types
export interface QuizAttempt {
  id: number
  user_id: number
  lesson_id: number
  started_at: string
  completed_at: string | null
  score: number | null
  passed: boolean | null
  answers: Record<string, unknown>
}

export interface QuizSubmission {
  answers: Record<number, string | string[]>
}

export interface QuizResult {
  attempt_id: number
  score: number
  passed: boolean
  total_questions: number
  correct_answers: number
  xp_earned: number
  feedback: QuizQuestionFeedback[]
  weighted_score?: number
}

export interface QuizQuestionFeedback {
  question_id: number
  is_correct: boolean
  correct_answer: string | string[]
  explanation: string | null
}

// External resource types
export interface ExternalResource {
  id: number
  title: string
  description: string | null
  url: string
  resource_type: 'article' | 'video' | 'podcast' | 'book' | 'course' | 'tool' | 'other'
  difficulty: 'beginner' | 'intermediate' | 'advanced' | null
  estimated_minutes: number | null
  tags: string[]
  is_featured: boolean
  click_count: number
  completion_count: number
  average_rating: number | null
  created_at: string
  updated_at: string | null
}

export interface ExternalResourceCreateData {
  title: string
  description?: string
  url: string
  resource_type: 'article' | 'video' | 'podcast' | 'book' | 'course' | 'tool' | 'other'
  difficulty?: 'beginner' | 'intermediate' | 'advanced'
  estimated_minutes?: number
  tags?: string[]
  is_featured?: boolean
}

export interface ExternalResourceRating {
  id: number
  user_id: number
  resource_id: number
  rating: number
  review: string | null
  created_at: string
}

// Helper function for authenticated requests
async function authFetch(url: string, options?: RequestInit) {
  const token = getAccessToken()
  const headers: Record<string, string> = {
    ...(options?.headers as Record<string, string> || {}),
  }
  if (token) headers['Authorization'] = `Bearer ${token}`
  if (options?.body) headers['Content-Type'] = 'application/json'

  const res = await fetch(url, { ...options, headers })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(err.detail || 'Request failed')
  }
  return res.status === 204 ? null : res.json()
}

// ============ COURSES API ============

export async function getCourses(params?: {
  access_level?: string
  include_unpublished?: boolean
}): Promise<Course[]> {
  const searchParams = new URLSearchParams()
  if (params?.access_level) searchParams.set('access_level', params.access_level)
  if (params?.include_unpublished) searchParams.set('include_unpublished', 'true')
  const query = searchParams.toString() ? `?${searchParams}` : ''
  return authFetch(`${API_BASE}/learning/courses${query}`)
}

export async function getAllCoursesAdmin(): Promise<CourseListItemAdmin[]> {
  return authFetch(`${API_BASE}/learning/admin/courses`)
}

// PATCH /learning/admin/courses/{id}/publish — backend response is
// CourseListItem (not Admin), so DO NOT replace the whole row in local state.
// Caller should merge `is_published` + `updated_at` onto the existing
// CourseListItemAdmin to preserve enrollment aggregates.
export async function togglePublish(
  courseId: number,
  isPublished: boolean,
): Promise<Course> {
  return authFetch(`${API_BASE}/learning/admin/courses/${courseId}/publish`, {
    method: 'PATCH',
    body: JSON.stringify({ is_published: isPublished }),
  })
}

// POST /learning/admin/courses/{id}/clone — returns a freshly-minted draft
// CourseListItem. The new row's enrollment aggregates are all zero by
// definition, so callers can safely default them on insert.
export async function cloneCourse(
  courseId: number,
  payload: CourseCloneData,
): Promise<Course> {
  return authFetch(`${API_BASE}/learning/admin/courses/${courseId}/clone`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

// POST /learning/admin/courses/{id}/transition — moves a course to a new
// lifecycle stage and returns the full refreshed CourseListItemAdmin row
// (safe to splice into the grid wholesale, unlike togglePublish). On 400
// the backend detail is a dict; we surface it as CourseStageTransitionError
// so callers can branch on requiresConfirm / allowedTargets.
export async function transitionCourseStage(
  courseId: number,
  body: { to_stage: CourseLifecycleStage; note?: string; confirm?: boolean },
): Promise<CourseListItemAdmin> {
  const token = getAccessToken()
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await fetch(
    `${API_BASE}/learning/admin/courses/${courseId}/transition`,
    { method: 'POST', headers, body: JSON.stringify(body) },
  )
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }))
    const d = err?.detail
    if (d && typeof d === 'object') {
      throw new CourseStageTransitionError(
        typeof d.message === 'string' ? d.message : 'Transition failed',
        res.status,
        {
          ...(Array.isArray(d.allowed_targets)
            ? { allowedTargets: d.allowed_targets as CourseLifecycleStage[] }
            : {}),
          ...(typeof d.enrollment_count === 'number'
            ? { enrollmentCount: d.enrollment_count }
            : {}),
          ...(typeof d.requires_confirm === 'boolean'
            ? { requiresConfirm: d.requires_confirm }
            : {}),
        },
      )
    }
    throw new CourseStageTransitionError(
      typeof d === 'string' ? d : 'Transition failed',
      res.status,
    )
  }
  return res.json()
}

export async function getCourseReviewQueue(): Promise<{
  due_count: number
  soonest_due_at: string | null
  courses: CourseListItemAdmin[]
}> {
  return authFetch(`${API_BASE}/learning/admin/courses/review-queue`)
}

export async function getCourseStageHistory(
  courseId: number,
): Promise<CourseStageTransitionRow[]> {
  return authFetch(`${API_BASE}/learning/admin/courses/${courseId}/transitions`)
}

export async function getCourse(id: number): Promise<CourseWithModules> {
  return authFetch(`${API_BASE}/learning/courses/${id}`)
}

export async function createCourse(data: CourseCreateData): Promise<Course> {
  return authFetch(`${API_BASE}/learning/courses`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateCourse(id: number, data: CourseUpdateData): Promise<Course> {
  return authFetch(`${API_BASE}/learning/courses/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteCourse(id: number): Promise<void> {
  return authFetch(`${API_BASE}/learning/courses/${id}`, {
    method: 'DELETE',
  })
}

// ============ MODULES API ============

export async function createModule(data: ModuleCreateData): Promise<Module> {
  return authFetch(`${API_BASE}/learning/courses/${data.course_id}/modules`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateModule(id: number, data: ModuleUpdateData): Promise<Module> {
  return authFetch(`${API_BASE}/learning/modules/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteModule(id: number): Promise<void> {
  return authFetch(`${API_BASE}/learning/modules/${id}`, {
    method: 'DELETE',
  })
}

export async function reorderModules(courseId: number, moduleIds: number[]): Promise<void> {
  return authFetch(`${API_BASE}/learning/courses/${courseId}/modules/reorder`, {
    method: 'POST',
    body: JSON.stringify({ module_ids: moduleIds }),
  })
}

// ============ LESSONS API ============

export async function getLesson(id: number): Promise<Lesson & { quiz_questions?: QuizQuestion[] }> {
  return authFetch(`${API_BASE}/learning/lessons/${id}`)
}

export async function createLesson(data: LessonCreateData): Promise<Lesson> {
  return authFetch(`${API_BASE}/learning/modules/${data.module_id}/lessons`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

// POST /learning/admin/modules/{module_id}/lessons/stub -- creates an empty
// lesson row that the admin then navigates into the rich editor to fill in.
// W2-A: replaces the LessonFormModal raw-JSON-textarea path.
export async function createStubLesson(moduleId: number): Promise<Lesson> {
  return authFetch(`${API_BASE}/learning/admin/modules/${moduleId}/lessons/stub`, {
    method: 'POST',
  })
}

export async function duplicateLesson(lessonId: number): Promise<Lesson> {
  return authFetch(`${API_BASE}/learning/admin/lessons/${lessonId}/duplicate`, {
    method: 'POST',
  })
}

export async function updateLesson(id: number, data: LessonUpdateData): Promise<Lesson> {
  return authFetch(`${API_BASE}/learning/lessons/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteLesson(id: number): Promise<void> {
  return authFetch(`${API_BASE}/learning/lessons/${id}`, {
    method: 'DELETE',
  })
}

export async function reorderLessons(moduleId: number, lessonIds: number[]): Promise<void> {
  return authFetch(`${API_BASE}/learning/modules/${moduleId}/lessons/reorder`, {
    method: 'POST',
    body: JSON.stringify({ lesson_ids: lessonIds }),
  })
}

// ============ QUIZ QUESTIONS API ============

export async function createQuizQuestion(data: QuizQuestionCreateData): Promise<QuizQuestion> {
  return authFetch(`${API_BASE}/learning/lessons/${data.lesson_id}/questions`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateQuizQuestion(id: number, data: QuizQuestionUpdateData): Promise<QuizQuestion> {
  return authFetch(`${API_BASE}/learning/questions/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteQuizQuestion(id: number): Promise<void> {
  return authFetch(`${API_BASE}/learning/questions/${id}`, {
    method: 'DELETE',
  })
}

// ============ LESSON RESOURCES API ============

export async function createLessonResource(data: LessonResourceCreateData): Promise<LessonResource> {
  return authFetch(`${API_BASE}/learning/lessons/${data.lesson_id}/resources`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function deleteLessonResource(id: number): Promise<void> {
  return authFetch(`${API_BASE}/learning/resources/${id}`, {
    method: 'DELETE',
  })
}

// ============ BULK IMPORT API ============

export interface CourseImportData {
  title: string
  description?: string
  access_level?: string
  difficulty?: string
  estimated_minutes?: number
  modules: {
    title: string
    description?: string
    lessons: {
      title: string
      lesson_type: string
      content: Record<string, unknown>
      estimated_minutes?: number
    }[]
  }[]
}

export async function importCourse(data: CourseImportData): Promise<Course> {
  return authFetch(`${API_BASE}/learning/courses/import`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function importCoursesFromJson(courses: CourseImportData[]): Promise<{ imported: number; errors: string[] }> {
  return authFetch(`${API_BASE}/learning/courses/import/bulk`, {
    method: 'POST',
    body: JSON.stringify({ courses }),
  })
}

// ============ ENROLLMENT API ============

export async function enrollInCourse(courseId: number): Promise<CourseEnrollment> {
  return authFetch(`${API_BASE}/learning/courses/${courseId}/enroll`, {
    method: 'POST',
  })
}

// ============ LESSON PROGRESS API ============

export async function completeLesson(lessonId: number): Promise<LessonCompletion> {
  return authFetch(`${API_BASE}/learning/lessons/${lessonId}/complete`, {
    method: 'POST',
  })
}

// ============ QUIZ API ============

export async function startQuiz(lessonId: number): Promise<QuizAttempt> {
  return authFetch(`${API_BASE}/learning/lessons/${lessonId}/quiz/start`, {
    method: 'POST',
  })
}

export async function attemptQuiz(lessonId: number, data: QuizSubmission): Promise<QuizAttempt> {
  return authFetch(`${API_BASE}/learning/lessons/${lessonId}/quiz/attempt`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function submitQuiz(lessonId: number, data: QuizSubmission): Promise<QuizResult> {
  return authFetch(`${API_BASE}/learning/lessons/${lessonId}/quiz/submit`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

// ============ EXTERNAL RESOURCES API ============

export async function createExternalResource(data: ExternalResourceCreateData): Promise<ExternalResource> {
  return authFetch(`${API_BASE}/learning/external-resources`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function trackResourceClick(resourceId: number): Promise<{ click_count: number }> {
  return authFetch(`${API_BASE}/learning/external-resources/${resourceId}/click`, {
    method: 'POST',
  })
}

export async function completeExternalResource(resourceId: number): Promise<{ completion_count: number }> {
  return authFetch(`${API_BASE}/learning/external-resources/${resourceId}/complete`, {
    method: 'POST',
  })
}

export async function rateExternalResource(resourceId: number, data: { rating: number; review?: string }): Promise<ExternalResourceRating> {
  return authFetch(`${API_BASE}/learning/external-resources/${resourceId}/rate`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}