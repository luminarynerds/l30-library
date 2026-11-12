/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from '@/lib/api-client'
import { API_BASE } from '@/api/types'

/**
 * Annual Reports API Service
 *
 * Provides functions for generating, managing, and exporting state annual reports.
 * All functions require staff/admin authentication.
 */

// ==================== Types ====================

export interface AnnualReportMetrics {
  total_checkouts?: number
  total_renewals?: number
  total_registered_patrons?: number
  active_patrons?: number
  total_programs_offered?: number
  total_program_attendance?: number
  total_items_owned?: number
  total_library_visits?: number
  public_computer_stations?: number
  total_staff_fte?: number | null
  total_operating_revenue?: number
  total_operating_expenditure?: number
  [key: string]: number | string | boolean | null | undefined
}

export interface AnnualReportValidationError {
  field: string
  message: string
  type?: string
}

export interface WebsiteTrafficMetricRow {
  label: string | null
  count: number
}

export interface WebsiteTrafficSection {
  available: boolean
  pageviews: number | null
  visitors: number | null
  visits: number | null
  bounces: number | null
  totaltime: number | null
  top_pages: WebsiteTrafficMetricRow[]
  top_referrers: WebsiteTrafficMetricRow[]
  top_countries: WebsiteTrafficMetricRow[]
}

export interface AnnualReport {
  id: number
  fiscal_year: number
  state_code: string
  library_name: string
  library_id?: string
  status: 'draft' | 'generated' | 'validated' | 'submitted' | 'rejected'
  is_validated: boolean
  validation_errors?: AnnualReportValidationError[]
  website_traffic?: WebsiteTrafficSection | null
  generated_at: string
  last_modified_at?: string
  submitted_to_state_at?: string
  submission_status?: string
  // All metrics - allow any additional metric fields
  [key: string]:
    | number
    | string
    | boolean
    | null
    | undefined
    | AnnualReportValidationError[]
    | WebsiteTrafficSection
}

export interface GenerateReportRequest {
  fiscal_year: number
  state_code: string
  library_name: string
  library_id?: string
}

export interface GenerateReportResponse {
  id: number
  fiscal_year: number
  state_code: string
  library_name: string
  library_id?: string
  status: string
  is_validated: boolean
  total_checkouts?: number
  total_registered_patrons?: number
  total_programs_offered?: number
  generated_at: string
  last_modified_at?: string
}

export interface ReportListResponse {
  reports: AnnualReport[]
  count: number
}

export interface ValidationResponse {
  report_id: number
  is_valid: boolean
  errors: AnnualReportValidationError[]
  error_count: number
}

export interface YoYComparison {
  report_id: number
  current_year: Record<string, number | string | boolean | null | undefined>
  prior_year: Record<string, number | string | boolean | null | undefined>
  growth_percent: Record<string, number | null>
}

export interface FinanceRevenueLines {
  local: number
  state: number
  federal: number
  other: number
}

export interface FinanceExpenditureLines {
  salaries: number
  benefits: number
  print: number
  electronic: number
  other: number
}

export interface FinanceEntryPayload {
  total_operating_revenue: number
  revenue: FinanceRevenueLines
  total_operating_expenditure: number
  expenditure: FinanceExpenditureLines
  capital_outlay: number
  capital_revenue?: FinanceRevenueLines
}

export interface FinanceEntryResponse {
  report_id: number
  // Pydantic serializes Decimal columns to strings in JSON responses.
  total_operating_revenue: string
  total_operating_expenditure: string
  capital_outlay: string
  data_source: string
}

export interface ReconciliationField {
  field: string
  // Numeric counts (ints), not Decimal money, so these stay numbers in JSON.
  report_value: number | null
  live_source_value: number | null
  drift: number | null
}

export interface ReconciliationResponse {
  report_id: number
  fields: ReconciliationField[]
}

export interface CertifyResponse {
  report_id: number
  status: string
  is_validated: boolean
  validated_by_id: number | null
}

// ==================== API Functions ====================

export async function enterAnnualReportFinance(
  token: string,
  reportId: number,
  payload: FinanceEntryPayload
): Promise<FinanceEntryResponse> {
  return fetchApi(`/annual-reports/${reportId}/finance`, {
    method: 'PATCH',
    headers: { Authorization: `Bearer ${token}` },
    body: payload,
  })
}

export async function getReconciliation(
  token: string,
  reportId: number
): Promise<ReconciliationResponse> {
  return fetchApi(`/annual-reports/${reportId}/reconciliation`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}` },
  })
}

export async function certifyAnnualReport(
  token: string,
  reportId: number
): Promise<CertifyResponse> {
  return fetchApi(`/annual-reports/${reportId}/certify`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  })
}

export async function generateAnnualReport(
  token: string,
  data: GenerateReportRequest
): Promise<GenerateReportResponse> {
  const params = new URLSearchParams({
    fiscal_year: data.fiscal_year.toString(),
    state_code: data.state_code,
    library_name: data.library_name,
    ...(data.library_id && { library_id: data.library_id }),
  })

  return fetchApi(`/annual-reports/generate?${params}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    timeoutMs: 60000,
  })
}

export async function listAnnualReports(
  token: string,
  fiscalYear?: number,
  stateCode?: string
): Promise<ReportListResponse> {
  const params = new URLSearchParams()
  if (fiscalYear) params.append('fiscal_year', fiscalYear.toString())
  if (stateCode) params.append('state_code', stateCode)

  return fetchApi(`/annual-reports?${params}`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}` },
  })
}

export async function getAnnualReport(token: string, reportId: number): Promise<AnnualReport> {
  return fetchApi(`/annual-reports/${reportId}`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}` },
  })
}

export async function validateAnnualReport(
  token: string,
  reportId: number,
  stateCode?: string
): Promise<ValidationResponse> {
  const params = stateCode ? `?state_code=${stateCode}` : ''

  return fetchApi(`/annual-reports/${reportId}/validate${params}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  })
}

export async function getYoYComparison(token: string, reportId: number): Promise<YoYComparison> {
  return fetchApi(`/annual-reports/${reportId}/comparison`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}` },
  })
}

export async function exportAsExcel(token: string, reportId: number): Promise<Blob> {
  const response = await fetch(`${API_BASE}/annual-reports/${reportId}/export/excel`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}` },
  })

  if (!response.ok) {
    throw new Error('Failed to export report as Excel')
  }

  return response.blob()
}

export async function exportAsPdf(token: string, reportId: number): Promise<Blob> {
  const response = await fetch(`${API_BASE}/annual-reports/${reportId}/export/pdf`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}` },
  })

  if (!response.ok) {
    throw new Error('Failed to export report as PDF')
  }

  return response.blob()
}

export async function exportAsXml(token: string, reportId: number): Promise<Blob> {
  const response = await fetch(`${API_BASE}/annual-reports/${reportId}/export/xml`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}` },
  })

  if (!response.ok) {
    throw new Error('Failed to export report as XML')
  }

  return response.blob()
}

// ==================== Utility Functions ====================

export function downloadFile(blob: Blob, filename: string): void {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  window.URL.revokeObjectURL(url)
}

export function formatCurrency(value: number | undefined): string {
  if (value === undefined || value === null) return 'N/A'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
  }).format(value)
}

export function formatNumber(value: number | undefined): string {
  if (value === undefined || value === null) return 'N/A'
  return new Intl.NumberFormat('en-US').format(value)
}

export function formatPercent(value: number | undefined): string {
  if (value === undefined || value === null) return 'N/A'
  return `${value.toFixed(1)}%`
}