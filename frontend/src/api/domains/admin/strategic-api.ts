/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'
import { getAccessToken } from '../../../utils/tokenStore'
import { API_BASE } from '@/api/types'

// ==================== Shared Types ====================

export type GoalStatus = 'not_started' | 'on_track' | 'at_risk' | 'delayed' | 'completed'
export type PlanStatus = 'draft' | 'active' | 'archived'
export type MilestoneType = 'achievement' | 'event' | 'celebration' | 'recognition'

// ==================== Template Types ====================

export interface TemplateMetric {
  name: string
  unit?: string
  target_placeholder?: string
}

export interface GoalTemplate {
  id: number
  name: string
  description?: string
  category?: string
  suggested_timeline_months?: number
  default_metrics: TemplateMetric[]
  is_system_template: boolean
}

export interface TemplateCreateData {
  name: string
  description?: string
  category?: string
  suggested_timeline_months?: number
  default_metrics?: TemplateMetric[]
  is_system_template?: boolean
}

export interface TemplateUpdateData {
  name?: string
  description?: string
  category?: string
  suggested_timeline_months?: number
  default_metrics?: TemplateMetric[]
  is_system_template?: boolean
}

export interface SeedTemplatesResult {
  message: string
  total_templates: number
  created: number
  skipped: number
}

// ==================== Plan Types ====================

export interface StrategicPlanGoalRef {
  id: number
  title: string
}

export interface StrategicPlan {
  id: number
  title: string
  description?: string
  period_start: string
  period_end: string
  mission?: string
  vision?: string
  values: string[]
  status: PlanStatus
  last_reviewed?: string
  next_review?: string
  created_at: string
  goals: StrategicPlanGoalRef[]
}

export interface PlanSummary {
  id: number
  title: string
  status: PlanStatus
  period_start: string
  period_end: string
  goal_count: number
  overall_progress: number
}

export interface PaginatedPlanSummary {
  items: PlanSummary[]
  total: number
  page: number
  per_page: number
  total_pages: number
}

export interface PlanCreateData {
  title: string
  description?: string
  period_start: string
  period_end: string
  mission?: string
  vision?: string
  values?: string[]
  status?: PlanStatus
}

export interface PlanUpdateData {
  title?: string
  description?: string
  period_start?: string
  period_end?: string
  mission?: string
  vision?: string
  values?: string[]
  status?: PlanStatus
  next_review?: string
}

// ==================== Goal Types ====================

export interface GoalMetric {
  name: string
  current: number
  target: number
  unit?: string
}

export interface GoalUpdate {
  date: string
  progress: number
  note?: string
  updated_by?: string
}

export interface StrategicGoal {
  id: number
  plan_id: number
  title: string
  description?: string
  public_description?: string
  category?: string
  department?: string
  target_date?: string
  progress: number
  status: GoalStatus
  metrics: GoalMetric[]
  owner?: string
  priority: number
  is_public: boolean
  staff_can_update: boolean
  completed_date?: string
  updates: GoalUpdate[]
  created_at: string
}

export interface PaginatedGoalResponse {
  items: StrategicGoal[]
  total: number
  page: number
  per_page: number
  total_pages: number
}

export interface GoalCreateData {
  title: string
  description?: string
  public_description?: string
  category?: string
  department?: string
  target_date?: string
  progress?: number
  status?: GoalStatus
  metrics?: GoalMetric[]
  owner?: string
  priority?: number
  is_public?: boolean
  staff_can_update?: boolean
}


export interface ProgressUpdateData {
  progress: number
  note?: string
  status?: GoalStatus
}

export interface ReorderGoalsData {
  goal_ids: number[]
}

// ==================== Milestone Types ====================

export interface StrategicMilestone {
  id: number
  plan_id: number
  title: string
  description?: string
  achieved_date?: string
  celebration_text?: string
  impact_story?: string
  photo_url?: string
  is_public: boolean
  is_featured: boolean
  display_order: number
  milestone_type: MilestoneType
  goal_id?: number
  created_at: string
}

export interface PaginatedMilestoneResponse {
  items: StrategicMilestone[]
  total: number
  page: number
  per_page: number
  total_pages: number
}

export interface MilestoneCreateData {
  title: string
  description?: string
  achieved_date?: string
  celebration_text?: string
  impact_story?: string
  photo_url?: string
  is_public?: boolean
  is_featured?: boolean
  display_order?: number
  milestone_type?: MilestoneType
  goal_id?: number
}

export interface MilestoneUpdateData {
  title?: string
  description?: string
  achieved_date?: string
  celebration_text?: string
  impact_story?: string
  photo_url?: string
  is_public?: boolean
  is_featured?: boolean
  display_order?: number
  milestone_type?: MilestoneType
  goal_id?: number
}

// ==================== Dashboard & Analytics Types ====================

export interface GoalStatusBreakdown {
  not_started: number
  on_track: number
  at_risk: number
  delayed: number
  completed: number
}

export interface DepartmentBreakdown {
  department: string
  count: number
  progress: number
}

export interface CategoryBreakdown {
  category: string
  count: number
  progress: number
}

export interface RecentProgressUpdate {
  goal_id: number
  goal_title: string
  progress: number
  note?: string
  updated_at: string
  updated_by?: string
}

export interface UpcomingDeadline {
  goal_id: number
  title: string
  target_date: string
  progress: number
  status: GoalStatus
  days_remaining: number
}

export interface AtRiskGoal {
  id: number
  title: string
  status: GoalStatus
  progress: number
  target_date?: string
  reason: string
}

export interface DashboardResponse {
  has_active_plan: boolean
  plan?: {
    id: number
    title: string
    period: string
    mission?: string
    vision?: string
    values: string[]
  }
  progress?: {
    overall: number
    total_goals: number
    completed: number
    on_track: number
    at_risk: number
    delayed: number
    not_started: number
  }
  by_category?: Record<string, { count: number; progress: number }>
  next_review?: string
}

export interface AnalyticsResponse {
  overall_progress: number
  goals_by_status: GoalStatusBreakdown
  goals_by_department: DepartmentBreakdown[]
  goals_by_category: CategoryBreakdown[]
  recent_progress_updates: RecentProgressUpdate[]
  upcoming_deadlines: UpcomingDeadline[]
  at_risk_goals: AtRiskGoal[]
  total_goals: number
  plan_period?: string
}

// ==================== Board Report Types ====================

export interface BoardReportGoal {
  id: number
  title: string
  description?: string
  category?: string
  department?: string
  progress: number
  status: GoalStatus
  target_date?: string
  owner?: string
  recent_updates: GoalUpdate[]
}

export interface BoardReportMilestone {
  id: number
  title: string
  description?: string
  achieved_date?: string
  celebration_text?: string
  milestone_type: MilestoneType
}

export interface BoardReportResponse {
  generated_at: string
  plan_id: number
  plan_title: string
  plan_period: string
  mission?: string
  vision?: string
  overall_progress: number
  status_summary: GoalStatusBreakdown
  goals_by_category: Record<string, { count: number; progress: number }>
  goals: BoardReportGoal[]
  milestones: BoardReportMilestone[]
  key_achievements: string[]
  areas_of_concern: string[]
}

// ==================== Public / Our Story Types ====================

export interface TimelineEvent {
  year: number
  title: string
  description?: string
  image_url?: string
}

export interface PublicGoalProgress {
  id: number
  title: string
  description?: string
  category?: string
  progress: number
  status: GoalStatus
}

export interface PublicMilestone {
  id: number
  title: string
  celebration_text?: string
  impact_story?: string
  photo_url?: string
  achieved_date?: string
  milestone_type: MilestoneType
}

export interface OurStoryResponse {
  has_plan: boolean
  library_name: string
  mission?: string
  vision?: string
  values: string[]
  story_intro?: string
  hero_image_url?: string
  history_timeline: TimelineEvent[]
  goals: PublicGoalProgress[]
  milestones: PublicMilestone[]
  plan_period?: string
}

// ==================== Import/Export Types ====================

export interface ImportPlanData {
  title: string
  description?: string
  period_start: string
  period_end: string
  mission?: string
  vision?: string
  values?: string[]
  story_intro?: string
  hero_image_url?: string
  history_timeline?: TimelineEvent[]
  goals?: GoalCreateData[]
  milestones?: MilestoneCreateData[]
}

export interface ImportPlanResult {
  message: string
  plan_id: number
  goals_imported: number
  milestones_imported: number
}

export interface ExportedPlan {
  title: string
  description?: string
  period_start: string
  period_end: string
  mission?: string
  vision?: string
  values: string[]
  story_intro?: string
  hero_image_url?: string
  history_timeline: TimelineEvent[]
  goals: GoalCreateData[]
  milestones: MilestoneCreateData[]
}

// ==================== Staff Goals View Types ====================

export interface StaffGoalView {
  id: number
  title: string
  description?: string
  category?: string
  department?: string
  progress: number
  status: GoalStatus
  can_update: boolean
  target_date?: string
  metrics: GoalMetric[]
}

export interface StaffGoalsResponse {
  has_plan: boolean
  plan_title?: string
  mission?: string
  goals: StaffGoalView[]
}

// ==================== Comment Types ====================

export interface CommentUserInfo {
  id: number
  email: string
  name?: string
}

export interface Comment {
  id: number
  goal_id: number
  user_id: number
  content: string
  parent_id?: number
  created_at: string
  updated_at?: string
  user?: CommentUserInfo
  replies: Comment[]
}

export interface CommentCreateData {
  content: string
  parent_id?: number
}

export interface CommentUpdateData {
  content: string
}

// ==================== Notification Types ====================

export type NotificationType = 'goal_update' | 'milestone_achieved' | 'deadline_approaching' | 'comment_reply' | 'general'

export interface Notification {
  id: number
  user_id: number
  notification_type: NotificationType
  title: string
  message?: string
  link?: string
  related_goal_id?: number
  related_milestone_id?: number
  is_read: boolean
  created_at: string
}

export interface UnreadCountResponse {
  unread_count: number
}

export interface MarkAllReadResponse {
  message: string
  count: number
}

// ==================== Attachment Types ====================

export interface Attachment {
  id: number
  goal_id?: number
  milestone_id?: number
  filename: string
  file_url: string
  file_type?: string
  file_size?: number
  uploaded_by_id?: number
  created_at: string
}

// ==================== Template API ====================

export async function listTemplates(category?: string): Promise<GoalTemplate[]> {
  const token = getAccessToken()
  const params = new URLSearchParams()
  if (category) params.set('category', category)
  const query = params.toString() ? `?${params}` : ''
  try {
    return await fetchApi<GoalTemplate[]>(`/strategic/templates${query}`, {
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch templates')
    }
    throw error
  }
}

export async function getTemplate(templateId: number): Promise<GoalTemplate> {
  const token = getAccessToken()
  try {
    return await fetchApi<GoalTemplate>(`/strategic/templates/${templateId}`, {
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch template')
    }
    throw error
  }
}

export async function createTemplate(data: TemplateCreateData): Promise<GoalTemplate> {
  const token = getAccessToken()
  try {
    return await fetchApi<GoalTemplate>('/strategic/templates', {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create template')
    }
    throw error
  }
}

export async function updateTemplate(
  templateId: number,
  data: TemplateUpdateData
): Promise<GoalTemplate> {
  const token = getAccessToken()
  try {
    return await fetchApi<GoalTemplate>(`/strategic/templates/${templateId}`, {
      method: 'PUT',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update template')
    }
    throw error
  }
}

export async function deleteTemplate(templateId: number): Promise<void> {
  const token = getAccessToken()
  try {
    await fetchApi<void>(`/strategic/templates/${templateId}`, {
      method: 'DELETE',
      ...(token ? { token } : {}),
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete template')
    }
    throw error
  }
}

export async function seedDefaultTemplates(): Promise<SeedTemplatesResult> {
  const token = getAccessToken()
  try {
    return await fetchApi<SeedTemplatesResult>('/strategic/templates/seed', {
      method: 'POST',
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to seed templates')
    }
    throw error
  }
}

// ==================== Plan API ====================

export async function getActivePlan(): Promise<StrategicPlan | null> {
  const token = getAccessToken()
  try {
    return await fetchApi<StrategicPlan>('/strategic/plans/active', {
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error) && error.status === 404) {
      return null
    }
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch active plan')
    }
    throw error
  }
}

export async function listPlans(params?: {
  plan_status?: PlanStatus
  page?: number
  per_page?: number
}): Promise<PaginatedPlanSummary> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  if (params?.plan_status) searchParams.set('plan_status', params.plan_status)
  if (params?.page) searchParams.set('page', String(params.page))
  if (params?.per_page) searchParams.set('per_page', String(params.per_page))
  const query = searchParams.toString() ? `?${searchParams}` : ''
  try {
    return await fetchApi<PaginatedPlanSummary>(`/strategic/plans${query}`, {
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch plans')
    }
    throw error
  }
}

export async function getPlan(planId: number): Promise<StrategicPlan> {
  const token = getAccessToken()
  try {
    return await fetchApi<StrategicPlan>(`/strategic/plans/${planId}`, {
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch plan')
    }
    throw error
  }
}

export async function createPlan(data: PlanCreateData): Promise<StrategicPlan> {
  const token = getAccessToken()
  try {
    return await fetchApi<StrategicPlan>('/strategic/plans', {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create plan')
    }
    throw error
  }
}

export async function updatePlan(
  planId: number,
  data: PlanUpdateData
): Promise<StrategicPlan> {
  const token = getAccessToken()
  try {
    return await fetchApi<StrategicPlan>(`/strategic/plans/${planId}`, {
      method: 'PUT',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update plan')
    }
    throw error
  }
}

export async function activatePlan(planId: number): Promise<{ message: string }> {
  const token = getAccessToken()
  try {
    return await fetchApi<{ message: string }>(`/strategic/plans/${planId}/activate`, {
      method: 'POST',
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to activate plan')
    }
    throw error
  }
}

export async function deletePlan(planId: number): Promise<{ message: string }> {
  const token = getAccessToken()
  try {
    return await fetchApi<{ message: string }>(`/strategic/plans/${planId}`, {
      method: 'DELETE',
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete plan')
    }
    throw error
  }
}

// ==================== Goal API ====================

export async function listGoals(
  planId: number,
  params?: {
    page?: number
    per_page?: number
    goal_status?: GoalStatus
    category?: string
  }
): Promise<PaginatedGoalResponse> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  if (params?.page) searchParams.set('page', String(params.page))
  if (params?.per_page) searchParams.set('per_page', String(params.per_page))
  if (params?.goal_status) searchParams.set('goal_status', params.goal_status)
  if (params?.category) searchParams.set('category', params.category)
  const query = searchParams.toString() ? `?${searchParams}` : ''
  try {
    return await fetchApi<PaginatedGoalResponse>(
      `/strategic/plans/${planId}/goals${query}`,
      {
        ...(token ? { token } : {}),
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch goals')
    }
    throw error
  }
}


export async function updateGoalProgress(
  goalId: number,
  data: ProgressUpdateData
): Promise<StrategicGoal> {
  const token = getAccessToken()
  try {
    return await fetchApi<StrategicGoal>(`/strategic/goals/${goalId}/progress`, {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update goal progress')
    }
    throw error
  }
}

export async function deleteGoal(goalId: number): Promise<{ message: string }> {
  const token = getAccessToken()
  try {
    return await fetchApi<{ message: string }>(`/strategic/goals/${goalId}`, {
      method: 'DELETE',
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete goal')
    }
    throw error
  }
}

export async function reorderGoals(
  planId: number,
  data: ReorderGoalsData
): Promise<{ message: string }> {
  const token = getAccessToken()
  try {
    return await fetchApi<{ message: string }>(
      `/strategic/plans/${planId}/goals/reorder`,
      {
        method: 'PUT',
        ...(token ? { token } : {}),
        body: data,
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to reorder goals')
    }
    throw error
  }
}

// ==================== Milestone API ====================

export async function listMilestones(
  planId: number,
  params?: {
    page?: number
    per_page?: number
    include_private?: boolean
  }
): Promise<PaginatedMilestoneResponse> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  if (params?.page) searchParams.set('page', String(params.page))
  if (params?.per_page) searchParams.set('per_page', String(params.per_page))
  if (params?.include_private) searchParams.set('include_private', 'true')
  const query = searchParams.toString() ? `?${searchParams}` : ''
  try {
    return await fetchApi<PaginatedMilestoneResponse>(
      `/strategic/plans/${planId}/milestones${query}`,
      {
        ...(token ? { token } : {}),
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch milestones')
    }
    throw error
  }
}

export async function createMilestone(
  planId: number,
  data: MilestoneCreateData
): Promise<StrategicMilestone> {
  const token = getAccessToken()
  try {
    return await fetchApi<StrategicMilestone>(
      `/strategic/plans/${planId}/milestones`,
      {
        method: 'POST',
        ...(token ? { token } : {}),
        body: data,
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create milestone')
    }
    throw error
  }
}

export async function updateMilestone(
  milestoneId: number,
  data: MilestoneUpdateData
): Promise<StrategicMilestone> {
  const token = getAccessToken()
  try {
    return await fetchApi<StrategicMilestone>(
      `/strategic/milestones/${milestoneId}`,
      {
        method: 'PUT',
        ...(token ? { token } : {}),
        body: data,
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update milestone')
    }
    throw error
  }
}

export async function deleteMilestone(milestoneId: number): Promise<{ message: string }> {
  const token = getAccessToken()
  try {
    return await fetchApi<{ message: string }>(`/strategic/milestones/${milestoneId}`, {
      method: 'DELETE',
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete milestone')
    }
    throw error
  }
}

// ==================== Dashboard & Analytics API ====================

export async function getStrategicDashboard(): Promise<DashboardResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<DashboardResponse>('/strategic/dashboard', {
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch dashboard')
    }
    throw error
  }
}

export async function getAnalytics(): Promise<AnalyticsResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<AnalyticsResponse>('/strategic/analytics', {
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch analytics')
    }
    throw error
  }
}

export async function getBoardReport(planId: number): Promise<BoardReportResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<BoardReportResponse>(
      `/strategic/plans/${planId}/board-report`,
      {
        ...(token ? { token } : {}),
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch board report')
    }
    throw error
  }
}

// ==================== Public / Our Story API ====================

export async function getOurStory(): Promise<OurStoryResponse> {
  try {
    return await fetchApi<OurStoryResponse>('/strategic/our-story')
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch our story')
    }
    throw error
  }
}

// ==================== Import/Export API ====================

export async function exportPlan(planId: number): Promise<ExportedPlan> {
  const token = getAccessToken()
  try {
    return await fetchApi<ExportedPlan>(`/strategic/plans/${planId}/export`, {
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to export plan')
    }
    throw error
  }
}

export async function importPlan(data: ImportPlanData): Promise<ImportPlanResult> {
  const token = getAccessToken()
  try {
    return await fetchApi<ImportPlanResult>('/strategic/import', {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to import plan')
    }
    throw error
  }
}

// ==================== Staff Goals API ====================

export async function getStaffGoals(): Promise<StaffGoalsResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<StaffGoalsResponse>('/strategic/staff/my-goals', {
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch staff goals')
    }
    throw error
  }
}

// ==================== Comment API ====================

export async function listComments(goalId: number): Promise<Comment[]> {
  const token = getAccessToken()
  try {
    return await fetchApi<Comment[]>(`/strategic/goals/${goalId}/comments`, {
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch comments')
    }
    throw error
  }
}

export async function createComment(
  goalId: number,
  data: CommentCreateData
): Promise<Comment> {
  const token = getAccessToken()
  try {
    return await fetchApi<Comment>(`/strategic/goals/${goalId}/comments`, {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create comment')
    }
    throw error
  }
}

export async function updateComment(
  commentId: number,
  data: CommentUpdateData
): Promise<Comment> {
  const token = getAccessToken()
  try {
    return await fetchApi<Comment>(`/strategic/comments/${commentId}`, {
      method: 'PUT',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update comment')
    }
    throw error
  }
}

export async function deleteComment(commentId: number): Promise<{ message: string }> {
  const token = getAccessToken()
  try {
    return await fetchApi<{ message: string }>(`/strategic/comments/${commentId}`, {
      method: 'DELETE',
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete comment')
    }
    throw error
  }
}

// ==================== Notification API ====================

export async function listNotifications(params?: {
  page?: number
  per_page?: number
  unread_only?: boolean
}): Promise<Notification[]> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  if (params?.page) searchParams.set('page', String(params.page))
  if (params?.per_page) searchParams.set('per_page', String(params.per_page))
  if (params?.unread_only) searchParams.set('unread_only', 'true')
  const query = searchParams.toString() ? `?${searchParams}` : ''
  try {
    return await fetchApi<Notification[]>(`/strategic/notifications${query}`, {
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch notifications')
    }
    throw error
  }
}

export async function markNotificationRead(
  notificationId: number
): Promise<{ message: string }> {
  const token = getAccessToken()
  try {
    return await fetchApi<{ message: string }>(
      `/strategic/notifications/${notificationId}/read`,
      {
        method: 'PUT',
        ...(token ? { token } : {}),
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to mark notification as read')
    }
    throw error
  }
}

export async function markAllNotificationsRead(): Promise<MarkAllReadResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<MarkAllReadResponse>(
      '/strategic/notifications/mark-all-read',
      {
        method: 'POST',
        ...(token ? { token } : {}),
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to mark all notifications as read')
    }
    throw error
  }
}

export async function getUnreadNotificationCount(): Promise<UnreadCountResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<UnreadCountResponse>(
      '/strategic/notifications/unread-count',
      {
        ...(token ? { token } : {}),
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch unread notification count')
    }
    throw error
  }
}

// ==================== Attachment API ====================

export async function listAttachments(goalId: number): Promise<Attachment[]> {
  const token = getAccessToken()
  try {
    return await fetchApi<Attachment[]>(
      `/strategic/goals/${goalId}/attachments`,
      {
        ...(token ? { token } : {}),
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch attachments')
    }
    throw error
  }
}

export async function uploadAttachment(
  goalId: number,
  file: File
): Promise<Attachment> {
  const token = getAccessToken()
  const formData = new FormData()
  formData.append('file', file)

  try {
    const response = await fetch(
      `${import.meta.env.VITE_API_URL || ''}${API_BASE}/strategic/goals/${goalId}/attachments`,
      {
        method: 'POST',
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: formData,
      }
    )

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || 'Failed to upload attachment')
    }

    return await response.json()
  } catch (error: unknown) {
    if (error instanceof Error) {
      throw error
    }
    throw new Error('Failed to upload attachment')
  }
}

export async function deleteAttachment(
  attachmentId: number
): Promise<{ message: string }> {
  const token = getAccessToken()
  try {
    return await fetchApi<{ message: string }>(
      `/strategic/attachments/${attachmentId}`,
      {
        method: 'DELETE',
        ...(token ? { token } : {}),
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete attachment')
    }
    throw error
  }
}

// ==================== Initiative Types ====================

export type InitiativeStatus =
  | 'planning'
  | 'approved'
  | 'in_progress'
  | 'on_hold'
  | 'completed'
  | 'cancelled'

export type BoardDecisionType = 'approval' | 'funding' | 'amendment' | 'closure'

export interface InitiativeMilestone {
  id: number
  initiative_id: number
  title: string
  description?: string
  target_date?: string
  completion_date?: string
  dependencies: number[]
  completed: boolean
  completion_notes?: string
  deliverables: string[]
}

export interface BoardDecisionLink {
  id: number
  initiative_id: number
  meeting_date: string
  meeting_reference?: string
  decision_type?: BoardDecisionType
  decision_summary?: string
  vote_result?: string
  minutes_url?: string
  resolution_number?: string
}

export interface StrategicInitiative {
  id: number
  plan_id: number
  title: string
  description?: string
  business_case?: string
  expected_outcomes: string[]
  status: InitiativeStatus
  start_date?: string
  target_completion_date?: string
  actual_completion_date?: string
  estimated_budget?: string
  actual_cost?: string
  assigned_leader_id?: number
  team_members: number[]
  priority?: number
  strategic_alignment_score?: number
  board_approved?: boolean
  board_approval_date?: string
  board_meeting_reference?: string
  completion_percentage?: number
  milestones: InitiativeMilestone[]
  board_decisions: BoardDecisionLink[]
}

export interface InitiativeCreateData {
  title: string
  description?: string
  business_case?: string
  expected_outcomes?: string[]
  status?: InitiativeStatus
  start_date?: string
  target_completion_date?: string
  estimated_budget?: string
  assigned_leader_id?: number
  team_members?: number[]
  priority?: number
  strategic_alignment_score?: number
}

export interface InitiativeUpdateData {
  title?: string
  description?: string
  business_case?: string
  expected_outcomes?: string[]
  status?: InitiativeStatus
  start_date?: string
  target_completion_date?: string
  actual_completion_date?: string
  estimated_budget?: string
  actual_cost?: string
  assigned_leader_id?: number
  team_members?: number[]
  priority?: number
  strategic_alignment_score?: number
  completion_percentage?: number
}

export interface InitiativeMilestoneCreateData {
  title: string
  description?: string
  target_date?: string
  dependencies?: number[]
  deliverables?: string[]
}

export interface BoardDecisionLinkCreateData {
  meeting_date: string
  decision_type: BoardDecisionType
  meeting_reference?: string
  decision_summary?: string
  vote_result?: string
  minutes_url?: string
  resolution_number?: string
}

// ==================== Initiative API ====================

export async function getInitiatives(
  planId: number,
  status?: InitiativeStatus
): Promise<StrategicInitiative[]> {
  const token = getAccessToken()
  const params = new URLSearchParams()
  if (status) params.set('status', status)
  const query = params.toString() ? `?${params}` : ''
  try {
    return await fetchApi<StrategicInitiative[]>(
      `/strategic/plans/${planId}/initiatives${query}`,
      { ...(token ? { token } : {}) }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch initiatives')
    }
    throw error
  }
}

export async function createInitiative(
  planId: number,
  data: InitiativeCreateData
): Promise<StrategicInitiative> {
  const token = getAccessToken()
  try {
    return await fetchApi<StrategicInitiative>(
      `/strategic/plans/${planId}/initiatives`,
      { method: 'POST', ...(token ? { token } : {}), body: data }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create initiative')
    }
    throw error
  }
}

export async function updateInitiative(
  id: number,
  data: InitiativeUpdateData
): Promise<StrategicInitiative> {
  const token = getAccessToken()
  try {
    return await fetchApi<StrategicInitiative>(
      `/strategic/initiatives/${id}`,
      { method: 'PATCH', ...(token ? { token } : {}), body: data }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update initiative')
    }
    throw error
  }
}

export async function deleteInitiative(id: number): Promise<void> {
  const token = getAccessToken()
  try {
    await fetchApi<void>(`/strategic/initiatives/${id}`, {
      method: 'DELETE',
      ...(token ? { token } : {}),
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete initiative')
    }
    throw error
  }
}

export async function createInitiativeMilestone(
  initiativeId: number,
  data: InitiativeMilestoneCreateData
): Promise<InitiativeMilestone> {
  const token = getAccessToken()
  try {
    return await fetchApi<InitiativeMilestone>(
      `/strategic/initiatives/${initiativeId}/milestones`,
      { method: 'POST', ...(token ? { token } : {}), body: data }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create initiative milestone')
    }
    throw error
  }
}

export async function completeInitiativeMilestone(
  milestoneId: number,
  notes?: string
): Promise<InitiativeMilestone> {
  const token = getAccessToken()
  try {
    return await fetchApi<InitiativeMilestone>(
      `/strategic/milestones/${milestoneId}/complete`,
      { method: 'POST', ...(token ? { token } : {}), body: { completion_notes: notes ?? null } }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to complete milestone')
    }
    throw error
  }
}

export async function linkBoardDecision(
  initiativeId: number,
  data: BoardDecisionLinkCreateData
): Promise<BoardDecisionLink> {
  const token = getAccessToken()
  try {
    return await fetchApi<BoardDecisionLink>(
      `/strategic/initiatives/${initiativeId}/board-decisions`,
      { method: 'POST', ...(token ? { token } : {}), body: data }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to link board decision')
    }
    throw error
  }
}
// ==================== KPI Types ====================

export interface KPIValue {
  id: number
  kpi_id: number
  value: string
  recorded_date?: string
  notes?: string
  recorded_by_id?: number
  is_estimated: boolean
  data_quality_score?: number
}

export interface KPIAlert {
  id: number
  kpi_id: number
  severity: string
  message: string
  triggered_at: string
  threshold_violated?: string
  actual_value?: string
  expected_value?: string
  acknowledged: boolean
  acknowledged_by_id?: number
  acknowledged_at?: string
  resolved: boolean
  resolution_notes?: string
}

export interface StrategicKPI {
  id: number
  plan_id: number
  name: string
  description?: string
  category?: string
  unit_of_measure?: string
  target_value?: string
  baseline_value?: string
  current_value?: string
  threshold_red?: string
  threshold_yellow?: string
  threshold_green?: string
  frequency?: string
  data_source?: string
  responsible_person_id?: number
  outcome_indicator_id?: number
  is_active: boolean
  last_updated?: string
  trend_direction?: string
  variance_percentage?: string
  values: KPIValue[]
  alerts: KPIAlert[]
}

export interface KPICreateData {
  name: string
  description?: string
  category?: string
  unit_of_measure?: string
  target_value?: string
  baseline_value?: string
  threshold_red?: string
  threshold_yellow?: string
  threshold_green?: string
  frequency?: string
  data_source?: string
  outcome_indicator_id?: number
}

export interface KPIUpdateData {
  name?: string
  description?: string
  category?: string
  unit_of_measure?: string
  target_value?: string
  baseline_value?: string
  threshold_red?: string
  threshold_yellow?: string
  threshold_green?: string
  frequency?: string
  data_source?: string
  outcome_indicator_id?: number
  is_active?: boolean
}

// ==================== KPI API ====================

export async function getKpis(
  planId: number,
  activeOnly?: boolean
): Promise<StrategicKPI[]> {
  const token = getAccessToken()
  const params = new URLSearchParams()
  if (activeOnly !== undefined) params.set('active_only', String(activeOnly))
  const query = params.toString() ? `?${params}` : ''
  try {
    return await fetchApi<StrategicKPI[]>(
      `/strategic/plans/${planId}/kpis${query}`,
      { ...(token ? { token } : {}) }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch KPIs')
    }
    throw error
  }
}

export async function createKpi(
  planId: number,
  data: KPICreateData
): Promise<StrategicKPI> {
  const token = getAccessToken()
  try {
    return await fetchApi<StrategicKPI>(
      `/strategic/plans/${planId}/kpis`,
      { method: 'POST', ...(token ? { token } : {}), body: data }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create KPI')
    }
    throw error
  }
}

export async function updateKpi(
  id: number,
  data: KPIUpdateData
): Promise<StrategicKPI> {
  const token = getAccessToken()
  try {
    return await fetchApi<StrategicKPI>(
      `/strategic/kpis/${id}`,
      { method: 'PATCH', ...(token ? { token } : {}), body: data }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update KPI')
    }
    throw error
  }
}

export async function deleteKpi(id: number): Promise<void> {
  const token = getAccessToken()
  try {
    await fetchApi<void>(`/strategic/kpis/${id}`, {
      method: 'DELETE',
      ...(token ? { token } : {}),
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete KPI')
    }
    throw error
  }
}

export async function recordKpiValue(
  kpiId: number,
  data: { value: string; notes?: string; is_estimated?: boolean }
): Promise<KPIValue> {
  const token = getAccessToken()
  try {
    return await fetchApi<KPIValue>(
      `/strategic/kpis/${kpiId}/values`,
      { method: 'POST', ...(token ? { token } : {}), body: data }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to record KPI value')
    }
    throw error
  }
}

export async function acknowledgeKpiAlert(alertId: number): Promise<KPIAlert> {
  const token = getAccessToken()
  try {
    return await fetchApi<KPIAlert>(
      `/strategic/kpi-alerts/${alertId}/acknowledge`,
      { method: 'POST', ...(token ? { token } : {}) }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to acknowledge alert')
    }
    throw error
  }
}

export async function resolveKpiAlert(
  alertId: number,
  resolutionNotes?: string
): Promise<KPIAlert> {
  const token = getAccessToken()
  try {
    return await fetchApi<KPIAlert>(
      `/strategic/kpi-alerts/${alertId}/resolve`,
      { method: 'POST', ...(token ? { token } : {}), body: { resolution_notes: resolutionNotes ?? null } }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to resolve alert')
    }
    throw error
  }
}
