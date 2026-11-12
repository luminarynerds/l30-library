/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from '@/lib/api-client'
import { API_BASE } from '@/api/types'

/**
 * Financial Reports API Service
 *
 * Provides functions for fetching financial reports from the backend API.
 * All functions require admin authentication.
 */

// ==================== Types ====================

export interface RevenueSummary {
  total_revenue: number
  count: number
  by_type: Record<string, number>
  monthly_breakdown: Array<{ month: string; amount: number }>
}

export interface FineTrends {
  daily_data: Array<{ date: string; collected: number; outstanding: number }>
  total_collected: number
  total_outstanding: number
  collection_rate: number
}

export interface PaymentMethods {
  methods: Array<{
    method: string
    count: number
    amount: number
    percentage: number
  }>
}

export interface WaivedFines {
  fines: Array<{
    fine_id: number
    patron_name: string
    amount: number
    waived_date: string
    waived_by: string
  }>
  total_waived: number
}

export interface OutstandingBalance {
  patron_id: number
  patron_name: string
  balance: number
  days_overdue: number
}

export interface OutstandingBalances {
  total_outstanding: number
  by_age: Record<string, number>
  delinquent_accounts: OutstandingBalance[]
}

export interface BudgetVsActual {
  year: number
  monthly: Array<{
    month: string
    budget: number
    actual: number
  }>
  total_budget: number
  total_actual: number
  variance_percentage: number
}

export interface MonthlyReportGeneration {
  report_id: string
  year: number
  month: number
  generated_at: string
  status: string
  file_path?: string
  file_size?: number
}

// ==================== API Functions ====================

export async function getRevenueSummary(
  token: string,
  startDate?: string,
  endDate?: string,
  useCache = true
): Promise<RevenueSummary> {
  const params = new URLSearchParams()
  if (startDate) params.append('start_date', startDate)
  if (endDate) params.append('end_date', endDate)
  params.append('use_cache', useCache.toString())

  return fetchApi<RevenueSummary>(`/financial/reports/revenue-summary?${params}`, {
    token,
  })
}

export async function getFineTrends(
  token: string,
  days = 90,
  useCache = true
): Promise<FineTrends> {
  const params = new URLSearchParams()
  params.append('days', days.toString())
  params.append('use_cache', useCache.toString())

  return fetchApi<FineTrends>(`/financial/reports/fine-trends?${params}`, {
    token,
  })
}

export async function getPaymentMethods(
  token: string,
  startDate?: string,
  endDate?: string,
  useCache = true
): Promise<PaymentMethods> {
  const params = new URLSearchParams()
  if (startDate) params.append('start_date', startDate)
  if (endDate) params.append('end_date', endDate)
  params.append('use_cache', useCache.toString())

  return fetchApi<PaymentMethods>(`/financial/reports/payment-methods?${params}`, {
    token,
  })
}

export async function getWaivedFines(
  token: string,
  startDate?: string,
  endDate?: string,
  limit = 100,
  offset = 0
): Promise<WaivedFines> {
  const params = new URLSearchParams()
  if (startDate) params.append('start_date', startDate)
  if (endDate) params.append('end_date', endDate)
  params.append('limit', limit.toString())
  params.append('offset', offset.toString())

  return fetchApi<WaivedFines>(`/financial/reports/waived-fines?${params}`, {
    token,
  })
}

export async function getOutstandingBalances(
  token: string,
  minimumBalance = 0.01,
  limit = 100,
  offset = 0
): Promise<OutstandingBalances> {
  const params = new URLSearchParams()
  params.append('minimum_balance', minimumBalance.toString())
  params.append('limit', limit.toString())
  params.append('offset', offset.toString())

  return fetchApi<OutstandingBalances>(`/financial/reports/outstanding-balances?${params}`, {
    token,
  })
}

export async function getBudgetVsActual(
  token: string,
  year?: number,
  useCache = true
): Promise<BudgetVsActual> {
  const params = new URLSearchParams()
  if (year) params.append('year', year.toString())
  params.append('use_cache', useCache.toString())

  return fetchApi<BudgetVsActual>(`/financial/reports/budget-vs-actual?${params}`, {
    token,
  })
}

export async function exportReport(
  token: string,
  reportType: string,
  format: 'csv' | 'json' = 'csv',
  startDate?: string,
  endDate?: string
): Promise<Blob> {
  const params = new URLSearchParams()
  params.append('format', format)
  if (startDate) params.append('start_date', startDate)
  if (endDate) params.append('end_date', endDate)

  const response = await fetch(
    `${API_BASE}/financial/reports/export/${reportType}?${params}`,
    {
      headers: { Authorization: `Bearer ${token}` },
    }
  )

  if (!response.ok) {
    throw new Error(`Failed to export report: ${response.statusText}`)
  }

  return response.blob()
}

export async function downloadReport(
  token: string,
  reportType: string,
  format: 'csv' | 'json' = 'csv',
  startDate?: string,
  endDate?: string
): Promise<void> {
  const blob = await exportReport(token, reportType, format, startDate, endDate)
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url

  const timestamp = new Date().toISOString().split('T')[0]
  const extension = format === 'csv' ? 'csv' : 'json'
  link.download = `${reportType}-${timestamp}.${extension}`

  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

// ==================== Board-Specific Functions ====================

export interface BoardDashboardSummary {
  total_revenue: number
  total_collected: number
  total_outstanding: number
  collection_rate: number
  collection_rate_percentage: number
  outstanding_balance: number
  delinquent_count: number
  budget_variance: number
  budget_variance_percentage: number
}

export interface Fund {
  id: number
  name: string
  code?: string
  description: string
  fiscal_year?: number
  allocated_amount?: number
  current_balance?: number
  balance: number
  allocated: number
  spent: number
  remaining: number
  utilization_percentage: number
}

export interface FundOverview {
  funds: Fund[]
  total_balance: number
  total_allocated: number
  total_spent: number
}

export interface AcquisitionSpending {
  year: number
  total_spending: number
  by_category: Array<{
    category: string
    spent: number
    budget: number
  }>
  top_vendors: Array<{
    name: string
    spending: number
    orders: number
  }>
  budget_utilization: number
}

export interface FinancialHealth {
  collection_effectiveness: {
    rate: number
    status: string
  }
  days_sales_outstanding: number
  cash_flow_status: {
    collected: number
    outstanding: number
    receivables: number
  }
  liquidity_indicators: {
    current_ratio: number
    quick_ratio: number
  }
  delinquency_status: {
    accounts_30_days: number
    accounts_60_days: number
    accounts_90_plus_days: number
  }
  overall_health_score: number
}

export async function getBoardDashboardSummary(
  token: string
): Promise<BoardDashboardSummary> {
  return fetchApi<BoardDashboardSummary>('/financial/board/dashboard-summary', {
    token,
  })
}

export async function getBoardFunds(token: string): Promise<FundOverview> {
  return fetchApi<FundOverview>('/financial/board/funds', {
    token,
  })
}

export async function getAcquisitionSpending(
  token: string,
  year?: number
): Promise<AcquisitionSpending> {
  const params = new URLSearchParams()
  if (year) params.append('year', year.toString())

  return fetchApi<AcquisitionSpending>(`/financial/board/acquisition-spending?${params}`, {
    token,
  })
}

export async function getFinancialHealth(token: string): Promise<FinancialHealth> {
  return fetchApi<FinancialHealth>('/financial/board/financial-health', {
    token,
  })
}

// ==================== Monthly Reports Functions ====================

export interface MonthlyReport {
  report_id: string
  year: number
  month: number
  generated_date: string
  file_size: number
}

export interface MonthlyReportList {
  reports: MonthlyReport[]
  total_count: number
  limit: number
  offset: number
}

export async function generateMonthlyReport(
  token: string,
  year: number,
  month: number
): Promise<MonthlyReportGeneration> {
  const params = new URLSearchParams()
  params.append('year', year.toString())
  params.append('month', month.toString())

  return fetchApi<MonthlyReportGeneration>(`/financial/board/reports/monthly/generate?${params}`, {
    method: 'POST',
    token,
  })
}

export async function listMonthlyReports(
  token: string,
  year?: number,
  limit = 12,
  offset = 0
): Promise<MonthlyReportList> {
  const params = new URLSearchParams()
  if (year) params.append('year', year.toString())
  params.append('limit', limit.toString())
  params.append('offset', offset.toString())

  return fetchApi<MonthlyReportList>(`/financial/board/reports/monthly?${params}`, {
    token,
  })
}

export async function downloadMonthlyReport(
  token: string,
  reportId: string,
  format: 'pdf' | 'csv' | 'json' = 'pdf'
): Promise<Blob> {
  const params = new URLSearchParams()
  params.append('format', format)

  const response = await fetch(
    `${API_BASE}/financial/board/reports/monthly/${reportId}/download?${params}`,
    {
      headers: { Authorization: `Bearer ${token}` },
    }
  )

  if (!response.ok) {
    throw new Error(`Failed to download monthly report: ${response.statusText}`)
  }

  return response.blob()
}

export async function saveMonthlyReportAsFile(
  token: string,
  reportId: string,
  format: 'pdf' | 'csv' | 'json' = 'pdf'
): Promise<void> {
  const blob = await downloadMonthlyReport(token, reportId, format)
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url

  const extension = format === 'pdf' ? 'pdf' : format === 'csv' ? 'csv' : 'json'
  link.download = `monthly_report_${reportId}.${extension}`

  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}
