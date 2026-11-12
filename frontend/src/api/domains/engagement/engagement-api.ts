/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { API_BASE } from '@/api/types'
import { getAccessToken } from '@/utils/tokenStore'

// ============ Types (mirror backend schemas/engagement.py) ============

export type SurveyPlacement =
  | 'entry_pulse'
  | 'embedded_lesson'
  | 'pre_certificate'
  | 'longitudinal'

export type SurveyQuestionType =
  | 'likert'
  | 'single_choice'
  | 'multi_choice'
  | 'free_text'
  | 'scenario'

export type SurveyResponseStatus =
  | 'pending'
  | 'in_progress'
  | 'completed'
  | 'skipped'
  | 'expired'

export interface LikertOptions {
  min: number
  max: number
  min_label?: string
  max_label?: string
}

export interface ChoiceOption {
  text: string
  value: string
  is_correct?: boolean | null
}

export interface ScenarioOptions {
  artifact: string
  expected_flags: string[]
  // labels rendered as the multi-select choices
  flag_choices?: { value: string; text: string }[]
}

export type QuestionOptions =
  | LikertOptions
  | ChoiceOption[]
  | ScenarioOptions
  | { max_length?: number }
  | null

export interface SurveyQuestion {
  id: number
  survey_id: number
  question_text: string
  question_type: SurveyQuestionType
  options: QuestionOptions
  is_optional: boolean
  is_demographic: boolean
  sort_order: number
  branching_rules: unknown[] | null
}

export interface Survey {
  id: number
  title: string
  description: string | null
  placement: SurveyPlacement
  course_id: number | null
  lesson_id: number | null
  blocks_progression: boolean
  triggers_remediation: boolean
  is_anonymous: boolean
  is_published: boolean
  estimated_minutes: number | null
  trigger_offset_days: number | null
  consent_copy: string | null
  questions: SurveyQuestion[]
}

export interface SurveyAnswer {
  question_id: number
  value: unknown
}

export interface SurveyOutcomePublic {
  outcome_type: string
  target: string | null
  status: string
}

export interface SurveyResponseResult {
  response_id: number
  status: SurveyResponseStatus
  score: number | null
  derived_track: string | null
  blocked: boolean
  outcomes: SurveyOutcomePublic[]
  next_url: string | null
}

export interface PendingSurvey {
  survey_id: number
  title: string
  placement: SurveyPlacement
  course_id: number | null
  estimated_minutes: number | null
  consent_copy: string | null
  delivery_token: string | null
}

export interface UserDemographicsUpdate {
  primary_language?: string | null
  is_native_english?: boolean | null
  age_range?: string | null
  underserved_self_id?: boolean | null
  zip_code?: string | null
}

export interface BadgeView {
  id: number
  name: string
  description: string | null
  category: string | null
  icon_url: string | null
}

export interface UserBadgeView {
  id: number
  badge: BadgeView
  earned_at: string
  earned_for: string | null
}

// ============ HTTP helpers ============

async function authFetch(url: string, options?: RequestInit) {
  const token = getAccessToken()
  const headers: Record<string, string> = {
    ...((options?.headers as Record<string, string>) || {}),
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

// Magic-link variant: no auth header. Public endpoint.
async function publicFetch(url: string, options?: RequestInit) {
  const headers: Record<string, string> = {
    ...((options?.headers as Record<string, string>) || {}),
  }
  if (options?.body) headers['Content-Type'] = 'application/json'
  const res = await fetch(url, { ...options, headers })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }))
    const wrapped = new Error(err.detail || 'Request failed') as Error & {
      status?: number
    }
    wrapped.status = res.status
    throw wrapped
  }
  return res.status === 204 ? null : res.json()
}

// ============ API calls ============

export async function listMyPendingSurveys(courseId?: number): Promise<PendingSurvey[]> {
  const qs = courseId !== undefined ? `?course_id=${courseId}` : ''
  return authFetch(`${API_BASE}/engagement/me/pending${qs}`)
}

export async function getSurvey(surveyId: number): Promise<Survey> {
  return authFetch(`${API_BASE}/engagement/surveys/${surveyId}`)
}

export async function submitSurveyResponse(
  surveyId: number,
  answers: SurveyAnswer[],
): Promise<SurveyResponseResult> {
  return authFetch(`${API_BASE}/engagement/surveys/${surveyId}/responses`, {
    method: 'POST',
    body: JSON.stringify({ answers }),
  })
}

export async function getSurveyByToken(token: string): Promise<Survey> {
  return publicFetch(`${API_BASE}/engagement/surveys/respond/${token}`)
}

export async function submitSurveyByToken(
  token: string,
  answers: SurveyAnswer[],
): Promise<SurveyResponseResult> {
  return publicFetch(`${API_BASE}/engagement/surveys/respond/${token}`, {
    method: 'POST',
    body: JSON.stringify({ answers }),
  })
}

export async function upsertMyDemographics(
  payload: UserDemographicsUpdate,
): Promise<unknown> {
  return authFetch(`${API_BASE}/engagement/me/demographics`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function listMyBadges(): Promise<UserBadgeView[]> {
  return authFetch(`${API_BASE}/engagement/me/badges`)
}
