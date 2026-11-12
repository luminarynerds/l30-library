/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * API client for Usage Statistics (IMLS/PLA Reporting)
 */

import { fetchApi, isApiError } from '@/lib/api-client'
import { getAccessToken } from '@/utils/tokenStore'
import { API_BASE as API_ROOT } from '@/api/types'


// TypeScript Interfaces

export interface UsageStatisticsDashboard {
  period_start: string
  period_end: string
  period_type: string
  branch_location: string | null
  circulation: CirculationStatisticsSummary
  collection: CollectionStatisticsSummary
  patron: PatronStatisticsSummary
  program: ProgramStatisticsSummary
  computer: ComputerUsageSummary
  reference: ReferenceStatisticsSummary
  visits: VisitStatisticsSummary
}

export interface CirculationStatisticsSummary {
  total_checkouts: number
  total_renewals: number
  total_returns: number
  physical_checkouts: number
  digital_checkouts: number
  unique_borrowers: number
  avg_checkouts_per_borrower: number
  checkouts_by_type?: Record<string, number>
}

export interface CollectionStatisticsSummary {
  total_physical_items: number
  total_digital_items: number
  total_titles: number
  physical_titles: number
  digital_titles: number
  items_by_type?: Record<string, number>
}

export interface PatronStatisticsSummary {
  total_registered: number
  new_registrations: number
  renewed_cards: number
  expired_cards: number
  active_borrowers: number
  registrations_by_type?: Record<string, number>
}

export interface ProgramStatisticsSummary {
  total_programs: number
  total_sessions: number
  total_attendance: number
  unique_attendees: number
  avg_attendance_per_session: number
  programs_by_type?: Record<string, number>
}

export interface ComputerUsageSummary {
  total_sessions: number
  unique_users: number
  total_hours_used: number
  avg_session_length_minutes: number
  wifi_sessions: number
  wifi_unique_devices: number
  print_jobs: number
  pages_printed: number
}

export interface ReferenceStatisticsSummary {
  total_questions: number
  questions_by_type?: Record<string, number>
  questions_by_method?: Record<string, number>
  avg_duration_minutes: number
}

export interface VisitStatisticsSummary {
  total_visits: number
  avg_visits_per_day: number
  peak_day_visits: number
  peak_day_date: string | null
}

export interface MonthOverMonthTrend {
  period: string
  value: number
  change_from_previous: number | null
  percent_change: number | null
}

export interface YearOverYearTrend {
  year: number
  period: string
  value: number
  change_from_previous_year: number | null
  percent_change: number | null
}

export interface StatisticalReport {
  id: number
  report_name: string
  report_type: string
  file_format: string
  file_path: string | null
  status: string
  created_at: string
  completed_at: string | null
  download_count: number
  generated_by_id: number
}

export interface IMLSSurveyData {
  fiscal_year: number
  branch_location: string | null
  circulation: {
    total_circulation: number
    physical_circulation: number
    digital_circulation: number
  }
  collection: {
    print_materials: number
    electronic_materials: number
    audio_materials: number
    video_materials: number
  }
  patron: {
    registered_borrowers: number
    total_cardholders: number
  }
  programs: {
    total_programs: number
    total_attendance: number
    children_programs: number
    ya_programs: number
    adult_programs: number
  }
  visits: {
    total_visits: number
  }
  reference: {
    reference_transactions: number
  }
  computer_usage: {
    computer_sessions: number
    wifi_sessions: number
  }
}

// Values are the backend PeriodType StrEnum values (schemas/usage_statistics.py) — lowercase.
export type PeriodType = "daily" | "weekly" | "monthly" | "quarterly" | "yearly"
export type ExportFormat = "csv" | "xlsx" | "pdf"

// API Functions

export async function fetchDashboard(
  periodStart: string,
  periodEnd: string,
  periodType: PeriodType = "monthly",
  branchLocation?: string
): Promise<UsageStatisticsDashboard> {
  const params = new URLSearchParams({
    period_start: periodStart,
    period_end: periodEnd,
    period_type: periodType,
  })
  if (branchLocation) params.append("branch_location", branchLocation)

  return fetchApi<UsageStatisticsDashboard>(`/usage-statistics/dashboard?${params}`)
}

export async function fetchCirculationSummary(
  periodStart: string,
  periodEnd: string,
  periodType: PeriodType = "monthly",
  branchLocation?: string
): Promise<CirculationStatisticsSummary> {
  const params = new URLSearchParams({
    period_start: periodStart,
    period_end: periodEnd,
    period_type: periodType,
  })
  if (branchLocation) params.append("branch_location", branchLocation)

  return fetchApi<CirculationStatisticsSummary>(`/usage-statistics/circulation/summary?${params}`)
}

export async function fetchCollectionSummary(
  snapshotDate?: string,
  branchLocation?: string
): Promise<CollectionStatisticsSummary> {
  const params = new URLSearchParams()
  if (snapshotDate) params.append("snapshot_date", snapshotDate)
  if (branchLocation) params.append("branch_location", branchLocation)

  return fetchApi<CollectionStatisticsSummary>(`/usage-statistics/collection/summary?${params}`)
}

export async function fetchPatronSummary(
  periodStart: string,
  periodEnd: string,
  periodType: PeriodType = "monthly",
  branchLocation?: string
): Promise<PatronStatisticsSummary> {
  const params = new URLSearchParams({
    period_start: periodStart,
    period_end: periodEnd,
    period_type: periodType,
  })
  if (branchLocation) params.append("branch_location", branchLocation)

  return fetchApi<PatronStatisticsSummary>(`/usage-statistics/patron/summary?${params}`)
}

export async function fetchProgramSummary(
  periodStart: string,
  periodEnd: string,
  periodType: PeriodType = "monthly",
  branchLocation?: string
): Promise<ProgramStatisticsSummary> {
  const params = new URLSearchParams({
    period_start: periodStart,
    period_end: periodEnd,
    period_type: periodType,
  })
  if (branchLocation) params.append("branch_location", branchLocation)

  return fetchApi<ProgramStatisticsSummary>(`/usage-statistics/program/summary?${params}`)
}

export async function fetchMonthOverMonthTrends(
  metric: string,
  months: number = 12,
  branchLocation?: string
): Promise<MonthOverMonthTrend[]> {
  const params = new URLSearchParams({
    metric,
    months: months.toString(),
  })
  if (branchLocation) params.append("branch_location", branchLocation)

  return fetchApi<MonthOverMonthTrend[]>(`/usage-statistics/trends/month-over-month?${params}`)
}

export async function fetchYearOverYearTrends(
  metric: string,
  years: number = 3,
  branchLocation?: string
): Promise<YearOverYearTrend[]> {
  const params = new URLSearchParams({
    metric,
    years: years.toString(),
  })
  if (branchLocation) params.append("branch_location", branchLocation)

  return fetchApi<YearOverYearTrend[]>(`/usage-statistics/trends/year-over-year?${params}`)
}

export async function exportStatistics(
  format: ExportFormat,
  periodStart: string,
  periodEnd: string,
  includeCharts: boolean = false
): Promise<StatisticalReport> {
  return fetchApi<StatisticalReport>('/usage-statistics/export', {
    method: 'POST',
    body: JSON.stringify({
      export_format: format,
      period_start: periodStart,
      period_end: periodEnd,
      include_charts: includeCharts,
    }),
  })
}

export async function generateIMLSSurvey(
  fiscalYear: number,
  branchLocation?: string
): Promise<StatisticalReport> {
  const params = new URLSearchParams()
  if (branchLocation) params.append("branch_location", branchLocation)

  return fetchApi<StatisticalReport>(`/usage-statistics/imls-survey/${fiscalYear}?${params}`, {
    method: 'POST',
  })
}

export async function fetchIMLSSurveyData(
  fiscalYear: number,
  branchLocation?: string
): Promise<IMLSSurveyData> {
  const params = new URLSearchParams()
  if (branchLocation) params.append("branch_location", branchLocation)

  return fetchApi<IMLSSurveyData>(`/usage-statistics/imls-survey/${fiscalYear}/data?${params}`)
}

export async function fetchReports(
  reportType?: string,
  status?: string,
  limit: number = 20
): Promise<StatisticalReport[]> {
  const params = new URLSearchParams({ limit: limit.toString() })
  if (reportType) params.append("report_type", reportType)
  if (status) params.append("status", status)

  return fetchApi<StatisticalReport[]>(`/usage-statistics/reports?${params}`)
}

export async function downloadReport(reportId: number): Promise<void> {
  const token = getAccessToken()
  const response = await fetch(`${API_ROOT}/usage-statistics/reports/${reportId}/download`, {
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })
  if (!response.ok) throw new Error("Failed to download report")

  const blob = await response.blob()
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = response.headers.get("Content-Disposition")?.split("filename=")[1] || "report"
  document.body.appendChild(a)
  a.click()
  window.URL.revokeObjectURL(url)
  a.remove()
}

// ============================================================================
// Request Types for POST Endpoints
// ============================================================================

export interface CirculationStatisticsCreate {
  period_start: string
  period_end: string
  period_type: PeriodType
  branch_location?: string | null
  checkouts_by_item_type?: Record<string, number> | null
  renewals_by_item_type?: Record<string, number> | null
  holds_placed_by_item_type?: Record<string, number> | null
  holds_filled_by_item_type?: Record<string, number> | null
  total_checkouts?: number
  total_renewals?: number
  total_holds_placed?: number
  total_holds_filled?: number
  total_returns?: number
  items_loaned_to_other_libraries?: number
  items_borrowed_from_other_libraries?: number
  in_house_use_count?: number
  collection_turnover_rate?: number | null
  notes?: string | null
}

export interface CirculationStatisticsResponse extends CirculationStatisticsCreate {
  id: number
  generated_at: string
  created_at: string
}

export interface CollectionStatisticsCreate {
  snapshot_date: string
  branch_location?: string | null
  items_owned_by_format?: Record<string, number> | null
  items_owned_by_collection?: Record<string, number> | null
  items_owned_by_subject?: Record<string, number> | null
  items_added_by_format?: Record<string, number> | null
  items_withdrawn_by_format?: Record<string, number> | null
  items_withdrawn_by_reason?: Record<string, number> | null
  total_items_owned?: number
  total_titles_owned?: number
  total_items_added?: number
  total_items_withdrawn?: number
  electronic_titles?: number
  electronic_databases?: number
  print_materials?: number
  audio_materials?: number
  video_materials?: number
  other_materials?: number
  current_serial_subscriptions?: number
  total_collection_value?: number | null
  notes?: string | null
}

export interface CollectionStatisticsResponse extends CollectionStatisticsCreate {
  id: number
  generated_at: string
  created_at: string
}

export interface PatronStatisticsCreate {
  period_start: string
  period_end: string
  period_type: PeriodType
  branch_location?: string | null
  total_registered_patrons?: number
  new_registrations?: number
  expired_cards?: number
  renewed_cards?: number
  active_borrowers?: number
  active_patrons_any_service?: number
  patrons_by_age_group?: Record<string, number> | null
  patrons_by_patron_type?: Record<string, number> | null
  patrons_by_zip_code?: Record<string, number> | null
  avg_checkouts_per_active_patron?: number | null
  avg_visits_per_active_patron?: number | null
  resident_patrons?: number
  non_resident_patrons?: number
  notes?: string | null
}

export interface PatronStatisticsResponse extends PatronStatisticsCreate {
  id: number
  generated_at: string
  created_at: string
}

export interface ProgramStatisticsCreate {
  period_start: string
  period_end: string
  period_type: PeriodType
  branch_location?: string | null
  events_by_category?: Record<string, number> | null
  events_by_age_group?: Record<string, number> | null
  attendance_by_category?: Record<string, number> | null
  attendance_by_age_group?: Record<string, number> | null
  total_programs_offered?: number
  total_program_attendance?: number
  avg_attendance_per_program?: number | null
  childrens_programs_count?: number
  childrens_program_attendance?: number
  young_adult_programs_count?: number
  young_adult_program_attendance?: number
  adult_programs_count?: number
  adult_program_attendance?: number
  outreach_programs_count?: number
  outreach_program_attendance?: number
  virtual_programs_count?: number
  virtual_program_attendance?: number
  reading_program_participants?: number
  reading_program_completions?: number
  notes?: string | null
}

export interface ProgramStatisticsResponse extends ProgramStatisticsCreate {
  id: number
  generated_at: string
  created_at: string
}

export interface ComputerUsageCreate {
  period_start: string
  period_end: string
  period_type: PeriodType
  branch_location?: string | null
  total_sessions?: number
  unique_users?: number
  total_hours_used?: number
  avg_session_length_minutes?: number | null
  sessions_by_hour_of_day?: Record<string, number> | null
  sessions_by_day_of_week?: Record<string, number> | null
  sessions_by_workstation?: Record<string, number> | null
  wifi_sessions?: number
  wifi_unique_devices?: number
  print_jobs?: number
  pages_printed?: number
  copy_jobs?: number
  pages_copied?: number
  notes?: string | null
}

export interface ComputerUsageResponse extends ComputerUsageCreate {
  id: number
  generated_at: string
  created_at: string
}

export type QuestionType = "directional" | "ready_reference" | "research" | "readers_advisory" | "technical"
export type ContactMethod = "in_person" | "phone" | "email" | "chat" | "text" | "social_media" | "video"

export interface ReferenceQuestionCreate {
  question_type: QuestionType
  contact_method: ContactMethod
  branch_location?: string | null
  duration_minutes?: number | null
  patron_type?: string | null
  subject_area?: string | null
  was_referred?: boolean
  referred_to?: string | null
  notes?: string | null
  asked_at?: string | null
}

export interface ReferenceQuestionResponse extends ReferenceQuestionCreate {
  id: number
  asked_at: string
  answered_by_id: number | null
  created_at: string
}

export type CountSource = "door_counter" | "manual" | "estimated"

export interface VisitCountCreate {
  count_date: string
  branch_location?: string | null
  door_count: number
  count_source: CountSource
  counts_by_hour?: Record<string, number> | null
  adjustment_factor?: number | null
  weather_notes?: string | null
  special_circumstances?: string | null
}

export interface VisitCountResponse extends VisitCountCreate {
  id: number
  adjusted_count: number | null
  recorded_by_id: number | null
  created_at: string
}

export interface PeerLibraryCreate {
  library_name: string
  library_id?: string | null
  state?: string | null
  city?: string | null
  population_served?: number | null
  total_operating_expenditure?: number | null
  total_staff_fte?: number | null
  collection_size?: number | null
  service_area_sq_miles?: number | null
  is_our_library?: boolean
  notes?: string | null
}

export interface PeerLibraryResponse extends PeerLibraryCreate {
  id: number
  is_active: boolean
  added_by_id: number | null
  created_at: string
}

export interface PeerComparisonDataCreate {
  data_year: number
  data_source?: string | null
  total_circulation?: number | null
  total_visits?: number | null
  registered_borrowers?: number | null
  total_programs?: number | null
  total_program_attendance?: number | null
  reference_transactions?: number | null
  computer_uses?: number | null
  print_collection?: number | null
  electronic_collection?: number | null
  audio_collection?: number | null
  video_collection?: number | null
  total_operating_revenue?: number | null
  total_operating_expenditure?: number | null
  collection_expenditure?: number | null
  staff_expenditure?: number | null
  total_staff_fte?: number | null
  librarian_fte?: number | null
  circulation_per_capita?: number | null
  visits_per_capita?: number | null
  expenditure_per_capita?: number | null
  additional_metrics?: Record<string, unknown> | null
  notes?: string | null
}

export interface PeerComparisonDataResponse extends PeerComparisonDataCreate {
  id: number
  peer_library_id: number
  imported_at: string
  imported_by_id: number | null
  created_at: string
}

export interface StatisticsSettingsCreate {
  branch_location?: string | null
  auto_generate_daily?: boolean
  auto_generate_weekly?: boolean
  auto_generate_monthly?: boolean
  auto_generate_yearly?: boolean
  fiscal_year_start_month?: number
  legal_service_area_population?: number | null
  population_data_year?: number | null
  door_counter_enabled?: boolean
  door_counter_adjustment_factor?: number
  reference_sampling_enabled?: boolean
  reference_sample_weeks?: number[] | null
  reference_extrapolation_factor?: number | null
  imls_library_id?: string | null
  state_library_id?: string | null
}

export interface StatisticsSettingsResponse extends StatisticsSettingsCreate {
  id: number
  is_active: boolean
  created_by_id: number | null
  created_at: string
  updated_at: string | null
}

// ============================================================================
// POST API Functions
// ============================================================================

export async function recordCirculationStats(
  data: CirculationStatisticsCreate
): Promise<CirculationStatisticsResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<CirculationStatisticsResponse>('/usage-statistics/circulation', {
      method: 'POST',
      body: JSON.stringify(data),
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || `Request failed with status ${error.status}`)
    }
    throw error
  }
}

export async function recordCollectionStats(
  data: CollectionStatisticsCreate
): Promise<CollectionStatisticsResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<CollectionStatisticsResponse>('/usage-statistics/collection', {
      method: 'POST',
      body: JSON.stringify(data),
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || `Request failed with status ${error.status}`)
    }
    throw error
  }
}

export async function recordPatronStats(
  data: PatronStatisticsCreate
): Promise<PatronStatisticsResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<PatronStatisticsResponse>('/usage-statistics/patron', {
      method: 'POST',
      body: JSON.stringify(data),
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || `Request failed with status ${error.status}`)
    }
    throw error
  }
}

export async function recordProgramStats(
  data: ProgramStatisticsCreate
): Promise<ProgramStatisticsResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<ProgramStatisticsResponse>('/usage-statistics/program', {
      method: 'POST',
      body: JSON.stringify(data),
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || `Request failed with status ${error.status}`)
    }
    throw error
  }
}

export async function recordComputerUsage(
  data: ComputerUsageCreate
): Promise<ComputerUsageResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<ComputerUsageResponse>('/usage-statistics/computer', {
      method: 'POST',
      body: JSON.stringify(data),
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || `Request failed with status ${error.status}`)
    }
    throw error
  }
}

export async function recordReferenceQuestion(
  data: ReferenceQuestionCreate
): Promise<ReferenceQuestionResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<ReferenceQuestionResponse>('/usage-statistics/reference/questions', {
      method: 'POST',
      body: JSON.stringify(data),
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || `Request failed with status ${error.status}`)
    }
    throw error
  }
}

export async function recordVisitCount(
  data: VisitCountCreate
): Promise<VisitCountResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<VisitCountResponse>('/usage-statistics/visits/count', {
      method: 'POST',
      body: JSON.stringify(data),
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || `Request failed with status ${error.status}`)
    }
    throw error
  }
}

export async function addPeerLibrary(
  data: PeerLibraryCreate
): Promise<PeerLibraryResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<PeerLibraryResponse>('/usage-statistics/peers', {
      method: 'POST',
      body: JSON.stringify(data),
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || `Request failed with status ${error.status}`)
    }
    throw error
  }
}

export async function addPeerData(
  peerId: number,
  data: PeerComparisonDataCreate
): Promise<PeerComparisonDataResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<PeerComparisonDataResponse>(`/usage-statistics/peers/${peerId}/data`, {
      method: 'POST',
      body: JSON.stringify(data),
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || `Request failed with status ${error.status}`)
    }
    throw error
  }
}

export async function saveStatisticsSettings(
  data: StatisticsSettingsCreate
): Promise<StatisticsSettingsResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<StatisticsSettingsResponse>('/usage-statistics/settings', {
      method: 'POST',
      body: JSON.stringify(data),
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || `Request failed with status ${error.status}`)
    }
    throw error
  }
}