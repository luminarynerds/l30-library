/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

import { api } from '@/lib/api-client'
import { API_BASE as API_ROOT } from '@/api/types'

export type StaffStatus = 'available' | 'on_break' | 'needs_help' | 'off_duty'

export interface StaffPresenceResponse {
  status: StaffStatus
  status_changed_at: string | null
  shift_started_at: string | null
  break_started_at: string | null
}

export interface HelpRequestResponse {
  notified_count: number
  message: string
}

const API_BASE = `${API_ROOT}/staff/presence`

export async function getMyPresence(): Promise<StaffPresenceResponse> {
  return api.get(`${API_BASE}/me`)
}

export async function updatePresenceStatus(status: StaffStatus): Promise<StaffPresenceResponse> {
  return api.put(`${API_BASE}/status`, { status })
}

export async function requestHelp(message?: string): Promise<HelpRequestResponse> {
  return api.post(`${API_ROOT}/staff/help/request`, message ? { message } : undefined)
}

export interface DeskScheduleStaff {
  staff_id: number
  staff_name: string
  scheduled_start: string | null
  scheduled_end: string | null
  scheduled_hours: number | null
  shift_type: string | null
  presence_status: string
  clock_in_time: string | null
}

export interface DeskScheduleResponse {
  date: string
  on_duty: DeskScheduleStaff[]
  on_break: DeskScheduleStaff[]
  scheduled_not_present: DeskScheduleStaff[]
  present_unscheduled: DeskScheduleStaff[]
  coverage_note: string | null
}

export async function getDeskScheduleToday(): Promise<DeskScheduleResponse> {
  return api.get(`${API_ROOT}/staff/desk-schedule/today`)
}

export interface BreakEntry {
  start: string | null
  end: string | null
  duration_minutes: number | null
}

export interface TimesheetDayResponse {
  shift_date: string
  clock_in: string | null
  clock_out: string | null
  breaks: BreakEntry[]
  total_worked_hours: number | null
  total_break_minutes: number
  scheduled_hours: number | null
  status: string
}

export interface TimesheetSummaryResponse {
  start_date: string
  end_date: string
  days: TimesheetDayResponse[]
  total_worked_hours: number
  total_scheduled_hours: number
  total_break_minutes: number
}

export async function getTimesheetToday(): Promise<TimesheetDayResponse> {
  return api.get(`${API_ROOT}/staff/timesheet/today`)
}

export async function getTimesheetSummary(startDate: string, endDate: string): Promise<TimesheetSummaryResponse> {
  return api.get(`${API_ROOT}/staff/timesheet/summary?start_date=${startDate}&end_date=${endDate}`)
}

// ---------------------------------------------------------------------------
// Open shifts (missing clock-out) + manager-only time entry edit
// ---------------------------------------------------------------------------

export interface OpenShiftEntry {
  shift_date: string
  clock_in: string
  days_ago: number
}

export async function getMyOpenShifts(days = 7): Promise<OpenShiftEntry[]> {
  return api.get(`${API_ROOT}/staff/timesheet/open-shifts/me?days=${days}`)
}

export interface TimeEntry {
  id: number
  entry_type: string
  recorded_at: string
  duration_minutes: number | null
  notes: string | null
}

export async function adminListEntries(staffId: number, dateISO?: string): Promise<TimeEntry[]> {
  const qs = dateISO ? `?date=${dateISO}` : ""
  return api.get(`${API_ROOT}/staff/timesheet/staff/${staffId}/entries${qs}`)
}

export async function adminCreateEntry(input: {
  staff_id: number
  entry_type: string
  recorded_at: string
  shift_date: string
  notes?: string
}): Promise<TimeEntry> {
  return api.post(`${API_ROOT}/staff/timesheet/entries`, input)
}

export async function adminUpdateEntry(
  entryId: number,
  input: { recorded_at?: string; notes?: string },
): Promise<TimeEntry> {
  return api.patch(`${API_ROOT}/staff/timesheet/entries/${entryId}`, input)
}

export async function adminDeleteEntry(entryId: number): Promise<void> {
  return api.delete(`${API_ROOT}/staff/timesheet/entries/${entryId}`)
}

// ---------------------------------------------------------------------------
// Manager-only pay-rate history endpoints
// ---------------------------------------------------------------------------

export interface PayRateEntry {
  id: number
  staff_id: number
  hourly_rate: number
  effective_from: string
  effective_to: string | null
  notes: string | null
  created_at: string
}

export interface CurrentPayRateEntry {
  staff_id: number
  staff_name: string
  role: string
  hourly_rate: number | null
  effective_from: string | null
}

export async function listCurrentPayRates(): Promise<CurrentPayRateEntry[]> {
  return api.get(`${API_ROOT}/staff/pay-rates/active`)
}

export async function getPayRateHistory(staffId: number): Promise<PayRateEntry[]> {
  return api.get(`${API_ROOT}/staff/pay-rates/${staffId}`)
}

export async function setPayRate(input: {
  staff_id: number
  hourly_rate: number
  effective_from: string
  notes?: string
}): Promise<PayRateEntry> {
  return api.post(`${API_ROOT}/staff/pay-rates`, input)
}

export async function amendPayRate(
  rateId: number,
  input: { notes?: string; effective_from?: string },
): Promise<PayRateEntry> {
  return api.patch(`${API_ROOT}/staff/pay-rates/${rateId}`, input)
}

export async function deletePayRate(rateId: number): Promise<void> {
  return api.delete(`${API_ROOT}/staff/pay-rates/${rateId}`)
}
