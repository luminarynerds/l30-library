/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { api } from '@/lib/api-client'
import { API_BASE } from '@/api/types'

interface QueryParams {
  [key: string]: string | number | boolean | undefined | null
}

const buildQueryString = (params?: QueryParams): string => {
  if (!params) return ''
  const searchParams = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      searchParams.set(key, String(value))
    }
  })
  const qs = searchParams.toString()
  return qs ? `?${qs}` : ''
}

export interface MyShift {
  shift_id: number
  branch_id: number
  shift_date: string
  shift_type: string
  status: string
  scheduled_start: string
  scheduled_end: string
  scheduled_hours: number
  is_holiday: boolean
  is_weekend: boolean
  has_open_swap: boolean
  has_open_callout: boolean
}

export interface MyShiftsResponse {
  shifts: MyShift[]
  range_start: string
  range_end: string
}

export const fairSchedulingApi = {
  // Dashboard
  async getDashboard() {
    return await api.get(`${API_BASE}/fair-scheduling/dashboard`)
  },

  // My Shifts (current user)
  async getMyShifts(params?: { days_ahead?: number; include_today?: boolean }): Promise<MyShiftsResponse> {
    return await api.get(`${API_BASE}/fair-scheduling/me/shifts${buildQueryString(params)}`)
  },

  // Schedule Generation
  async generate(data: { branch_id: number; period_start: string; period_end: string; solver_config?: Record<string, unknown> }) {
    return await api.post(`${API_BASE}/fair-scheduling/generate`, data)
  },

  async getGenerations() {
    return await api.get(`${API_BASE}/fair-scheduling/generations`)
  },

  async getGeneration(generationId: number) {
    return await api.get(`${API_BASE}/fair-scheduling/generations/${generationId}`)
  },

  async publishGeneration(generationId: number) {
    return await api.post(`${API_BASE}/fair-scheduling/generations/${generationId}/publish`)
  },

  // Explanations
  async getExplanations(generationId: number) {
    return await api.get(`${API_BASE}/fair-scheduling/explanations/${generationId}`)
  },

  async getStaffExplanation(staffId: number) {
    return await api.get(`${API_BASE}/fair-scheduling/explanations/staff/${staffId}`)
  },

  // Preference Learning
  async learnPreferences(data: { branch_id?: number; staff_ids?: number[] }) {
    return await api.post(`${API_BASE}/fair-scheduling/preferences/learn`, data)
  },

  async getLearnedPreferences(staffId: number) {
    return await api.get(`${API_BASE}/fair-scheduling/preferences/learned/${staffId}`)
  },

  async confirmPreference(preferenceId: number) {
    return await api.post(`${API_BASE}/fair-scheduling/preferences/${preferenceId}/confirm`)
  },

  // Call-Out Coverage
  async createCallout(data: { branch_id: number; original_shift_id: number; callout_staff_id: number; callout_reason?: string; urgency?: string }) {
    return await api.post(`${API_BASE}/fair-scheduling/callout`, data)
  },

  async getOpenCallouts() {
    return await api.get(`${API_BASE}/fair-scheduling/callout/open`)
  },

  async getCalloutCandidates(requestId: number) {
    return await api.get(`${API_BASE}/fair-scheduling/callout/${requestId}/candidates`)
  },

  async assignCallout(requestId: number, data: { covering_staff_id: number; notes?: string }) {
    return await api.post(`${API_BASE}/fair-scheduling/callout/${requestId}/assign`, data)
  },

  async respondToCallout(requestId: number, data: { response: string; notes?: string }) {
    return await api.post(`${API_BASE}/fair-scheduling/callout/${requestId}/respond`, data)
  },

  // Fatigue Monitoring
  async getStaffFatigue(staffId: number) {
    return await api.get(`${API_BASE}/fair-scheduling/fatigue/${staffId}`)
  },

  async getStaffFatigueHistory(staffId: number) {
    return await api.get(`${API_BASE}/fair-scheduling/fatigue/${staffId}/history`)
  },

  async getTeamFatigue(branchId: number) {
    return await api.get(`${API_BASE}/fair-scheduling/fatigue/team/${branchId}`)
  },

  // Payroll
  async generatePayroll(data: { branch_id?: number; pay_period_start: string; pay_period_end: string }) {
    return await api.post(`${API_BASE}/fair-scheduling/payroll/generate`, data)
  },

  async exportPayroll(data: { branch_id?: number; pay_period_start: string; pay_period_end: string; export_format?: string }) {
    return await api.post(`${API_BASE}/fair-scheduling/payroll/export`, data)
  },

  async getPayrollSummary(params?: QueryParams) {
    return await api.get(`${API_BASE}/fair-scheduling/payroll/summary${buildQueryString(params)}`)
  },

  async approvePayroll(data: { batch_id?: string; pay_period_start?: string; pay_period_end?: string }) {
    return await api.post(`${API_BASE}/fair-scheduling/payroll/approve`, data)
  },

  // Staff Scheduling Profiles
  async createProfile(data: {
    staff_id: number
    branch_id?: number
    employment_type: string
    contracted_hours_per_week: number
    min_hours_per_week: number
    max_hours_per_week: number
    skills?: string[]
    hire_date?: string
    seniority_level?: number
    max_consecutive_days?: number
    min_hours_between_shifts?: number
    max_weekend_shifts_per_month?: number
    max_closing_shifts_per_week?: number
  }) {
    return await api.post(`${API_BASE}/fair-scheduling/profiles`, data)
  },

  async getProfile(staffId: number) {
    return await api.get(`${API_BASE}/fair-scheduling/profiles/${staffId}`)
  },

  async updateProfile(staffId: number, data: Record<string, unknown>) {
    return await api.put(`${API_BASE}/fair-scheduling/profiles/${staffId}`, data)
  },
}

// ---------------------------------------------------------------------------
// Payroll policy (admin-only, single row)
// ---------------------------------------------------------------------------

export interface PayrollPolicy {
  overtime_multiplier: number
  holiday_multiplier: number
  weekend_differential: number
  evening_differential: number
  default_ot_threshold_hours: number
  evening_start_local: string
  updated_by_id: number | null
  updated_at: string
}

export type PayrollPolicyUpdate = Partial<Omit<PayrollPolicy, 'updated_by_id' | 'updated_at'>>

export async function getPayrollPolicy(): Promise<PayrollPolicy> {
  return await api.get(`${API_BASE}/fair-scheduling/payroll/policy`)
}

export async function updatePayrollPolicy(input: PayrollPolicyUpdate): Promise<PayrollPolicy> {
  return await api.put(`${API_BASE}/fair-scheduling/payroll/policy`, input)
}
