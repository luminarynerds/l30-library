/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Learning Paths API Client
 * Handles all learning-related API calls (courses, lessons, progress tracking)
 */

import { fetchApi } from '@/lib/api-client'
import { getAccessToken } from '@/utils/tokenStore'

// Type definitions
export interface Course {
  id: number
  title: string
  description?: string
  thumbnail_url?: string
  difficulty: 'beginner' | 'intermediate' | 'advanced'
  estimated_minutes?: number
  is_published: boolean
  module_count?: number
  lesson_count?: number
  xp_reward: number
}

export interface Lesson {
  id: number
  module_id: number
  title: string
  lesson_type: 'article' | 'video' | 'quiz' | 'sandbox' | 'lab'
   
  content: Record<string, unknown>
  estimated_minutes?: number
  xp_reward: number
  summary?: string
}

export interface QuizQuestion {
  id: number
  lesson_id: number
  question_text: string
  question_type: string
  options: Array<{ id: string; text: string }>
  difficulty_level: number
}

export interface LessonProgress {
  id: number
  user_id: number
  lesson_id: number
  status: 'not_started' | 'in_progress' | 'completed'
  progress_percentage: number
  completed_at?: string
}

export interface QuizQuestionFeedback {
  question_id: number
  correct: boolean
  selected_answer?: string
  correct_answer?: string
  explanation?: string
}

export interface QuizResult {
  attempt_id?: number
  score: number
  passed: boolean
  total_questions: number
  correct_answers: number
  percentage?: number
  feedback?: QuizQuestionFeedback[]
  xp_earned?: number
}

// API Endpoints
export const learningAPI = {
  // Courses
  listCourses: async (published_only: boolean = true) => {
    const token = getAccessToken()
    const params = published_only ? '?published=true' : ''
    return fetchApi(`/learning/courses${params}`, { ...(token ? { token } : {}) })
  },

  getCourse: async (courseId: number) => {
    const token = getAccessToken()
    return fetchApi(`/learning/courses/${courseId}`, { ...(token ? { token } : {}) })
  },

  // Enrollment
  enrollCourse: async (courseId: number) => {
    const token = getAccessToken()
    return fetchApi(`/learning/courses/${courseId}/enroll`, {
      method: 'POST',
      ...(token ? { token } : {}),
    })
  },

  getEnrollments: async () => {
    const token = getAccessToken()
    return fetchApi('/learning/my-courses', { ...(token ? { token } : {}) })
  },

  // Lessons
  getLesson: async (lessonId: number) => {
    const token = getAccessToken()
    return fetchApi(`/learning/lessons/${lessonId}`, { ...(token ? { token } : {}) })
  },

  updateLessonProgress: async (lessonId: number, progress: Partial<LessonProgress>) => {
    const token = getAccessToken()
    return fetchApi(`/learning/lessons/${lessonId}/progress`, {
      method: 'PUT',
      body: progress,
      ...(token ? { token } : {}),
    })
  },

  // Quiz
  submitQuiz: async (lessonId: number, answers: Record<string, string>) => {
    const token = getAccessToken()
    return fetchApi(`/learning/lessons/${lessonId}/quiz/submit`, {
      method: 'POST',
      body: { answers },
      ...(token ? { token } : {}),
    })
  },

  // Progress tracking
  getUserProgress: async (courseId: number) => {
    const token = getAccessToken()
    return fetchApi(`/learning/progress/${courseId}`, { ...(token ? { token } : {}) })
  },

  // Certificates
  getCertificates: async () => {
    const token = getAccessToken()
    return fetchApi('/learning/certificates', { ...(token ? { token } : {}) })
  },

  verifyCertificate: async (certificateId: string) => {
    const token = getAccessToken()
    return fetchApi(`/learning/certificates/${certificateId}/verify`, { ...(token ? { token } : {}) })
  },

  downloadCertificatePDF: async (courseId: number) => {
    const token = getAccessToken()
    return fetchApi(`/learning/courses/${courseId}/certificate/pdf`, { ...(token ? { token } : {}) })
  },
}

export default learningAPI
