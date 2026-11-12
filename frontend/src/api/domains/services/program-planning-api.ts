/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from '@/lib/api-client'

// ==================== Types ====================

export interface TemplateBudgetItem {
  id: number
  description: string
  category: string
  estimated_amount: number
  notes: string | null
}

export interface TemplateSupplyItem {
  id: number
  item_name: string
  quantity: number
  unit: string | null
  estimated_cost: number | null
  vendor_suggestion: string | null
  notes: string | null
}

export interface TemplateMarketingMilestone {
  id: number
  milestone_type: string
  description: string
  days_before_program: number
  notes: string | null
}

export interface ProgramTemplate {
  id: number
  name: string
  description: string | null
  category: string
  target_audience: string
  program_type: string
  default_duration_minutes: number
  recommended_capacity: number | null
  registration_required: boolean
  room_type_needed: string | null
  equipment_needed: string[] | null
  estimated_budget: number | null
  marketing_lead_days: number | null
  volunteers_needed: number
  volunteer_roles_needed: string[] | null
  target_attendance: number | null
  success_metrics: Record<string, unknown> | null
  is_active: boolean
  times_used: number
  source_program_id: number | null
  created_by_id: number | null
  created_at: string
  updated_at: string
  template_budget_items: TemplateBudgetItem[]
  template_supply_items: TemplateSupplyItem[]
  template_marketing_milestones: TemplateMarketingMilestone[]
}

export interface ProgramTemplateListItem {
  id: number
  name: string
  description: string | null
  category: string
  target_audience: string
  program_type: string
  is_active: boolean
  times_used: number
  created_at: string
}

export interface ProgramBudgetItem {
  id: number
  plan_id: number
  description: string
  category: string
  estimated_amount: number
  actual_amount: number | null
  is_paid: boolean
  paid_date: string | null
  receipt_reference: string | null
  vendor: string | null
  notes: string | null
  created_at: string
}

export interface ProgramSupplyItem {
  id: number
  plan_id: number
  item_name: string
  quantity_needed: number
  quantity_on_hand: number
  unit: string | null
  estimated_cost: number | null
  actual_cost: number | null
  status: string
  vendor: string | null
  order_date: string | null
  expected_delivery: string | null
  assigned_to_id: number | null
  notes: string | null
  created_at: string
}

export interface ProgramRoomBooking {
  id: number
  plan_id: number
  room_id: number | null
  reservation_id: number | null
  status: string
  setup_notes: string | null
  setup_time_minutes: number | null
  teardown_time_minutes: number | null
  created_at: string
}

export interface ProgramEquipmentBooking {
  id: number
  plan_id: number
  equipment_id: number | null
  equipment_type_requested: string
  quantity: number
  status: string
  notes: string | null
  created_at: string
}

export interface ProgramMarketingMilestone {
  id: number
  plan_id: number
  milestone_type: string
  description: string
  due_date: string
  completed: boolean
  completed_at: string | null
  completed_by_id: number | null
  assigned_to_id: number | null
  notes: string | null
  created_at: string
}

export interface ProgramVolunteerAssignment {
  id: number
  plan_id: number
  volunteer_id: number | null
  user_id: number | null
  role: string
  status: string
  confirmed_at: string | null
  hours_worked: number | null
  notes: string | null
  created_at: string
}

export interface ProgramEvaluation {
  id: number
  plan_id: number
  overall_rating: string | null
  content_quality_rating: string | null
  logistics_rating: string | null
  engagement_rating: string | null
  expected_attendance: number | null
  actual_attendance: number | null
  new_patron_count: number | null
  repeat_attendee_count: number | null
  budget_variance: number | null
  cost_per_attendee: number | null
  staff_notes: string | null
  what_went_well: string | null
  what_to_improve: string | null
  attendee_feedback_summary: string | null
  recommend_repeat: boolean | null
  recommended_changes: string | null
  comparison_metrics: Record<string, unknown> | null
  evaluated_by_id: number | null
  evaluated_at: string | null
  created_at: string
}

export interface ProgramPlan {
  id: number
  program_id: number
  template_id: number | null
  copied_from_program_id: number | null
  planning_notes: string | null
  planning_complete: boolean
  planning_completed_at: string | null
  total_budget: number
  total_spent: number
  created_by_id: number | null
  created_at: string
  updated_at: string
}

export interface ProgramPlanDetail extends ProgramPlan {
  budget_items: ProgramBudgetItem[]
  supply_items: ProgramSupplyItem[]
  room_bookings: ProgramRoomBooking[]
  equipment_bookings: ProgramEquipmentBooking[]
  marketing_milestones: ProgramMarketingMilestone[]
  volunteer_assignments: ProgramVolunteerAssignment[]
  evaluation: ProgramEvaluation | null
}

export interface SuccessMetric {
  program_id: number
  program_title: string
  program_date: string
  attendance: number | null
  target_attendance: number | null
  attendance_rate: number | null
  total_budget: number | null
  total_spent: number | null
  cost_per_attendee: number | null
  overall_rating: string | null
  recommend_repeat: boolean | null
}

export interface SuccessMetricsResponse {
  programs: SuccessMetric[]
  summary: Record<string, unknown> | null
}

// ==================== API Functions ====================

const BASE = '/program-planning'

export async function listTemplates(params?: {
  category?: string
  active_only?: boolean
  skip?: number
  limit?: number
}): Promise<ProgramTemplateListItem[]> {
  const searchParams = new URLSearchParams()
  if (params?.category) searchParams.set('category', params.category)
  if (params?.active_only !== undefined) searchParams.set('active_only', String(params.active_only))
  if (params?.skip) searchParams.set('skip', String(params.skip))
  if (params?.limit) searchParams.set('limit', String(params.limit))
  const qs = searchParams.toString()
  return fetchApi(`${BASE}/templates${qs ? `?${qs}` : ''}`)
}

export async function getTemplate(templateId: number): Promise<ProgramTemplate> {
  return fetchApi(`${BASE}/templates/${templateId}`)
}

export async function createTemplate(data: Partial<ProgramTemplate>, token?: string): Promise<ProgramTemplate> {
  return fetchApi(`${BASE}/templates`, { method: 'POST', body: data, token })
}

export async function updateTemplate(templateId: number, data: Partial<ProgramTemplate>, token?: string): Promise<ProgramTemplate> {
  return fetchApi(`${BASE}/templates/${templateId}`, { method: 'PATCH', body: data, token })
}

export async function deleteTemplate(templateId: number, token?: string): Promise<void> {
  return fetchApi(`${BASE}/templates/${templateId}`, { method: 'DELETE', skipJsonParse: true, token })
}

export async function createTemplateFromProgram(programId: number, templateName: string, token?: string): Promise<ProgramTemplate> {
  return fetchApi(`${BASE}/templates/from-program/${programId}?template_name=${encodeURIComponent(templateName)}`, { method: 'POST', token })
}

export async function createPlan(data: {
  program_id: number
  template_id?: number
  copied_from_program_id?: number
  planning_notes?: string
}): Promise<ProgramPlan> {
  return fetchApi(`${BASE}/plans`, { method: 'POST', body: data })
}

export async function getPlan(planId: number): Promise<ProgramPlanDetail> {
  return fetchApi(`${BASE}/plans/${planId}`)
}

export async function getPlanByProgram(programId: number): Promise<ProgramPlanDetail> {
  return fetchApi(`${BASE}/plans/by-program/${programId}`)
}

export async function updatePlan(planId: number, data: {
  planning_notes?: string
  planning_complete?: boolean
}): Promise<ProgramPlan> {
  return fetchApi(`${BASE}/plans/${planId}`, { method: 'PATCH', body: data })
}

export async function copyProgram(data: {
  source_program_id: number
  new_title: string
  new_program_date: string
  new_start_time: string
  new_end_time?: string
  branch_id?: number
  copy_budget?: boolean
  copy_supplies?: boolean
  copy_marketing_timeline?: boolean
  copy_volunteer_roles?: boolean
  notes?: string
}): Promise<{ program_id: number; plan_id: number }> {
  return fetchApi(`${BASE}/copy-program`, { method: 'POST', body: data })
}

export async function addBudgetItem(data: {
  plan_id: number
  description: string
  category: string
  estimated_amount: number
  actual_amount?: number
  vendor?: string
  notes?: string
}): Promise<ProgramBudgetItem> {
  return fetchApi(`${BASE}/budget-items`, { method: 'POST', body: data })
}

export async function updateBudgetItem(itemId: number, data: Partial<ProgramBudgetItem>): Promise<ProgramBudgetItem> {
  return fetchApi(`${BASE}/budget-items/${itemId}`, { method: 'PATCH', body: data })
}

export async function deleteBudgetItem(itemId: number): Promise<void> {
  return fetchApi(`${BASE}/budget-items/${itemId}`, { method: 'DELETE', skipJsonParse: true })
}

export async function getSupplyChecklist(planId: number): Promise<ProgramSupplyItem[]> {
  return fetchApi(`${BASE}/supply-items/${planId}`)
}

export async function addSupplyItem(data: {
  plan_id: number
  item_name: string
  quantity_needed?: number
  quantity_on_hand?: number
  unit?: string
  estimated_cost?: number
  vendor?: string
  notes?: string
}): Promise<ProgramSupplyItem> {
  return fetchApi(`${BASE}/supply-items`, { method: 'POST', body: data })
}

export async function updateSupplyItem(itemId: number, data: Partial<ProgramSupplyItem>): Promise<ProgramSupplyItem> {
  return fetchApi(`${BASE}/supply-items/${itemId}`, { method: 'PATCH', body: data })
}

export async function deleteSupplyItem(itemId: number): Promise<void> {
  return fetchApi(`${BASE}/supply-items/${itemId}`, { method: 'DELETE', skipJsonParse: true })
}

export async function createRoomBooking(data: {
  plan_id: number
  room_id?: number
  setup_notes?: string
}): Promise<ProgramRoomBooking> {
  return fetchApi(`${BASE}/room-bookings`, { method: 'POST', body: data })
}

export async function createEquipmentBooking(data: {
  plan_id: number
  equipment_id?: number
  equipment_type_requested: string
  quantity?: number
  notes?: string
}): Promise<ProgramEquipmentBooking> {
  return fetchApi(`${BASE}/equipment-bookings`, { method: 'POST', body: data })
}

export async function updateEquipmentBooking(bookingId: number, data: Partial<ProgramEquipmentBooking>): Promise<ProgramEquipmentBooking> {
  return fetchApi(`${BASE}/equipment-bookings/${bookingId}`, { method: 'PATCH', body: data })
}

export async function addMarketingMilestone(data: {
  plan_id: number
  milestone_type: string
  description: string
  due_date: string
  assigned_to_id?: number
  notes?: string
}): Promise<ProgramMarketingMilestone> {
  return fetchApi(`${BASE}/marketing-milestones`, { method: 'POST', body: data })
}

export async function updateMarketingMilestone(milestoneId: number, data: Partial<ProgramMarketingMilestone>): Promise<ProgramMarketingMilestone> {
  return fetchApi(`${BASE}/marketing-milestones/${milestoneId}`, { method: 'PATCH', body: data })
}

export async function getMarketingReminders(daysAhead?: number): Promise<ProgramMarketingMilestone[]> {
  const qs = daysAhead ? `?days_ahead=${daysAhead}` : ''
  return fetchApi(`${BASE}/marketing-reminders${qs}`)
}

export async function assignVolunteer(data: {
  plan_id: number
  volunteer_id?: number
  user_id?: number
  role: string
  notes?: string
}): Promise<ProgramVolunteerAssignment> {
  return fetchApi(`${BASE}/volunteer-assignments`, { method: 'POST', body: data })
}

export async function updateVolunteerAssignment(assignmentId: number, data: Partial<ProgramVolunteerAssignment>): Promise<ProgramVolunteerAssignment> {
  return fetchApi(`${BASE}/volunteer-assignments/${assignmentId}`, { method: 'PATCH', body: data })
}

export async function deleteVolunteerAssignment(assignmentId: number): Promise<void> {
  return fetchApi(`${BASE}/volunteer-assignments/${assignmentId}`, { method: 'DELETE', skipJsonParse: true })
}

export async function createEvaluation(data: Partial<ProgramEvaluation> & { plan_id: number }): Promise<ProgramEvaluation> {
  return fetchApi(`${BASE}/evaluations`, { method: 'POST', body: data })
}

export async function updateEvaluation(evalId: number, data: Partial<ProgramEvaluation>): Promise<ProgramEvaluation> {
  return fetchApi(`${BASE}/evaluations/${evalId}`, { method: 'PATCH', body: data })
}

export async function getEvaluationByPlan(planId: number): Promise<ProgramEvaluation> {
  return fetchApi(`${BASE}/evaluations/by-plan/${planId}`)
}

export async function getSuccessMetrics(params?: {
  program_type?: string
  date_from?: string
  date_to?: string
  program_ids?: number[]
  limit?: number
}): Promise<SuccessMetricsResponse> {
  const searchParams = new URLSearchParams()
  if (params?.program_type) searchParams.set('program_type', params.program_type)
  if (params?.date_from) searchParams.set('date_from', params.date_from)
  if (params?.date_to) searchParams.set('date_to', params.date_to)
  if (params?.program_ids) searchParams.set('program_ids', params.program_ids.join(','))
  if (params?.limit) searchParams.set('limit', String(params.limit))
  const qs = searchParams.toString()
  return fetchApi(`${BASE}/success-metrics${qs ? `?${qs}` : ''}`)
}