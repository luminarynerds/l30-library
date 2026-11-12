/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import React, { useCallback, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  DollarSign,
  TrendingUp,
  AlertCircle,
  Download,
  Eye,
  EyeOff,
  BarChart3,
  Calendar,
  Lock,
} from 'lucide-react'
import { format, subMonths, startOfMonth, endOfMonth, differenceInDays } from 'date-fns'
import toast from 'react-hot-toast'
import clsx from 'clsx'

import { useAuth } from '../contexts/AuthContext'
import { fetchApi } from '../lib/api-client'
import { getAccessToken } from '@/utils/tokenStore'
import { useTranslation, getCurrentLocale } from '@/i18n'
import { AdminShell } from '../components/shells/AdminShell'

// ==================== Types ====================



interface RevenueSummaryData {
  total_revenue: number
  count: number
  by_type: Record<string, number>
  monthly_breakdown: Array<{ month: string; amount: number }>
}

interface FineTrendsData {
  daily_data: Array<{ date: string; collected: number; outstanding: number }>
  total_collected: number
  total_outstanding: number
  collection_rate: number
}

interface PaymentMethodsData {
  methods: Array<{
    method: string
    count: number
    amount: number
    percentage: number
  }>
}

interface OutstandingBalancesData {
  total_outstanding: number
  by_age: Record<string, number>
  delinquent_accounts: Array<{
    patron_id: number
    patron_name: string
    balance: number
    days_overdue: number
  }>
}

interface BudgetVsActualData {
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

// ==================== Stat Card Component ====================

interface StatCardProps {
  title: string
  value: string | number
  unit?: string
  icon: React.ReactNode
  color: 'blue' | 'green' | 'red' | 'yellow' | 'purple' | 'accent' | 'success' | 'danger' | 'warning' | 'category'
  trend?: { value: number; direction: 'up' | 'down' }
  loading?: boolean
  onClick?: () => void
}

const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  unit,
  icon,
  color,
  trend,
  loading,
  onClick,
}) => {
  const colorMap: Record<NonNullable<StatCardProps['color']>, string> = {
    blue: 'bg-earth-50 dark:bg-earth-800/20 text-lsc-rose dark:text-lsc-rose-light border-lsc-border dark:border-earth-700',
    green: 'bg-status-success-50 dark:bg-status-success-900/20 text-status-success-600 border-status-success-200 dark:border-status-success-800',
    red: 'bg-status-danger-50 dark:bg-status-danger-900/20 text-status-danger-600 border-status-danger-200 dark:border-status-danger-800',
    yellow: 'bg-status-warning-50 dark:bg-status-warning-900/20 text-status-warning-600 border-status-warning-200 dark:border-status-warning-800',
    purple: 'bg-category-50 dark:bg-category-900/20 text-category-600 border-category-200 dark:border-category-800',
    // Semantic aliases
    accent: 'bg-earth-50 dark:bg-earth-800/20 text-lsc-rose dark:text-lsc-rose-light border-lsc-border dark:border-earth-700',
    success: 'bg-status-success-50 dark:bg-status-success-900/20 text-status-success-600 border-status-success-200 dark:border-status-success-800',
    danger: 'bg-status-danger-50 dark:bg-status-danger-900/20 text-status-danger-600 border-status-danger-200 dark:border-status-danger-800',
    warning: 'bg-status-warning-50 dark:bg-status-warning-900/20 text-status-warning-600 border-status-warning-200 dark:border-status-warning-800',
    category: 'bg-category-50 dark:bg-category-900/20 text-category-600 border-category-200 dark:border-category-800',
  }

  return (
    <div
      onClick={onClick} tabIndex={onClick ? 0 : undefined} role={onClick ? "button" : undefined} onKeyDown={onClick ? (e: React.KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick?.(); } } : undefined}
      className={clsx(
        'p-6 rounded-lg border',
        colorMap[color],
        onClick && 'cursor-pointer hover:shadow-lg transition-shadow'
      )}
    >
      <div className="flex justify-between items-start">
        <div className="flex-1">
          <p className="text-sm font-medium opacity-75">{title}</p>
          {loading ? (
            <div className="mt-2 h-8 bg-earth-200 dark:bg-earth-600 rounded motion-safe:animate-pulse w-24" />
          ) : (
            <div className="mt-2 flex items-baseline gap-2">
              <p className="text-3xl font-bold">{value}</p>
              {unit && <span className="text-sm opacity-75">{unit}</span>}
            </div>
          )}
          {trend && (
            <p
              className={clsx(
                'text-xs font-medium mt-2',
                trend.direction === 'up' ? 'text-status-success-600' : 'text-status-danger-600'
              )}
            >
              {trend.direction === 'up' ? '↑' : '↓'} {Math.abs(trend.value)}%
            </p>
          )}
        </div>
        <div className="text-2xl opacity-50">{icon}</div>
      </div>
    </div>
  )
}

// ==================== Filter Panel Component ====================

interface FilterPanelProps {
  startDate: Date
  endDate: Date
  onDateRangeChange: (start: Date, end: Date) => void
  isLoading: boolean
}

const FilterPanel: React.FC<FilterPanelProps> = ({
  startDate,
  endDate,
  onDateRangeChange,
  isLoading,
}) => {
  const handlePredefinedRange = (months: number) => {
    const end = endOfMonth(new Date())
    const start = startOfMonth(subMonths(new Date(), months))
    onDateRangeChange(start, end)
  }

  return (
    <div className="bg-lsc-white dark:bg-earth-800 p-4 mb-6 rounded-lg border border-lsc-border dark:border-earth-700 shadow-sm">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-2">
          <Calendar className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
          <span className="text-sm font-medium">
            {format(startDate, 'MMM d, yyyy')} - {format(endDate, 'MMM d, yyyy')}
          </span>
        </div>
        <div className="flex gap-2 flex-wrap">
          {[
            { label: 'Last Month', months: 1 },
            { label: 'Last 3 Months', months: 3 },
            { label: 'Last Year', months: 12 },
          ].map((range) => (
            <button
              key={range.months}
              onClick={() => handlePredefinedRange(range.months)}
              disabled={isLoading}
              className="px-3 py-2 text-sm font-medium bg-earth-100 dark:bg-earth-700 hover:bg-earth-200 dark:hover:bg-earth-600 text-lsc-dark/70 dark:text-lsc-cream/70 rounded disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {range.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

// ==================== Data Table Component ====================

interface TableProps {
  title: string
  headers: string[]
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  rows: Array<Record<string, any>>
  loading?: boolean
  onExport?: () => void
}

const DataTable: React.FC<TableProps> = ({
  title,
  headers,
  rows,
  loading,
  onExport,
}) => {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 p-6 mb-6 rounded-lg border border-lsc-border dark:border-earth-700 shadow-sm">
      <div className="flex justify-between items-center mb-4">
        <h3 className="font-serif text-lg font-semibold">{title}</h3>
        {onExport && (
          <button
            onClick={onExport}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-earth-100 dark:bg-earth-700 hover:bg-earth-200 dark:hover:bg-earth-600 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm font-medium rounded disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Download className="w-4 h-4" />
            Export
          </button>
        )}
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-12 bg-earth-200 dark:bg-earth-600 rounded motion-safe:animate-pulse" />
          ))}
        </div>
      ) : rows.length === 0 ? (
        <p className="text-center text-lsc-dark/70 dark:text-lsc-cream/70 py-8">No data available</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-lsc-border dark:border-earth-700 bg-earth-50 dark:bg-earth-900">
                {headers.map((header) => (
                  <th
                    key={header}
                    className="px-4 py-3 text-left font-medium text-lsc-dark/70 dark:text-lsc-cream/70"
                  >
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, idx) => (
                <tr key={idx} className="border-b border-lsc-border dark:border-earth-700 hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800">
                  {headers.map((header) => (
                    <td
                      key={`${idx}-${header}`}
                      className="px-4 py-3 text-earth-800 dark:text-earth-100"
                    >
                      {typeof row[header] === 'number'
                        ? row[header].toLocaleString(getCurrentLocale(), {
                            style: header.toLowerCase().includes('amount') ||
                              header.toLowerCase().includes('balance')
                              ? 'currency'
                              : 'decimal',
                            currency: 'USD',
                            minimumFractionDigits: 0,
                            maximumFractionDigits: 2,
                          })
                        : row[header]}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// ==================== Dashboard Body Component ====================

interface TreasurerDashboardBodyProps {
  startDate: Date
  endDate: Date
  setStartDate: (d: Date) => void
  setEndDate: (d: Date) => void
  hideSensitiveData: boolean
  setHideSensitiveData: (v: boolean) => void
}


const TreasurerDashboardBody: React.FC<TreasurerDashboardBodyProps> = ({
  startDate,
  endDate,
  setStartDate,
  setEndDate,
  hideSensitiveData,
  setHideSensitiveData,
}) => {
  const { t } = useTranslation();

  // ==================== API Queries ====================

  const { data: revenueSummary, isLoading: revenueLoading } = useQuery({
    queryKey: [
      'board-revenue-summary',
      format(startDate, 'yyyy-MM-dd'),
      format(endDate, 'yyyy-MM-dd'),
    ],
    queryFn: async () => {
      return fetchApi<RevenueSummaryData>(
        `/financial/reports/revenue-summary?start_date=${format(
          startDate,
          'yyyy-MM-dd'
        )}&end_date=${format(endDate, 'yyyy-MM-dd')}`
      )
    },
    staleTime: 5 * 60 * 1000,
  })

  const { data: fineTrends, isLoading: trendsLoading } = useQuery({
    queryKey: [
      'board-fine-trends',
      format(startDate, 'yyyy-MM-dd'),
      format(endDate, 'yyyy-MM-dd'),
    ],
    queryFn: async () => {
      return fetchApi<FineTrendsData>(`/financial/reports/fine-trends?days=${differenceInDays(endDate, startDate) || 90}`)
    },
    staleTime: 5 * 60 * 1000,
  })

  const { data: paymentMethods, isLoading: paymentLoading } = useQuery({
    queryKey: [
      'board-payment-methods',
      format(startDate, 'yyyy-MM-dd'),
      format(endDate, 'yyyy-MM-dd'),
    ],
    queryFn: async () => {
      return fetchApi<PaymentMethodsData>(
        `/financial/reports/payment-methods?start_date=${format(
          startDate,
          'yyyy-MM-dd'
        )}&end_date=${format(endDate, 'yyyy-MM-dd')}`
      )
    },
    staleTime: 5 * 60 * 1000,
  })

  const { data: outstandingBalances, isLoading: balancesLoading } = useQuery({
    queryKey: ['board-outstanding-balances'],
    queryFn: async () => {
      return fetchApi<OutstandingBalancesData>(
        '/financial/reports/outstanding-balances?minimum_balance=0.01'
      )
    },
    staleTime: 5 * 60 * 1000,
  })

  const { data: budgetVsActual, isLoading: budgetLoading } = useQuery({
    queryKey: ['board-budget-vs-actual'],
    queryFn: async () => {
      return fetchApi<BudgetVsActualData>('/financial/reports/budget-vs-actual')
    },
    staleTime: 5 * 60 * 1000,
  })

  const { data: funds, isLoading: fundsLoading } = useQuery({
    queryKey: ['board-funds'],
    queryFn: async () => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      return fetchApi<any>('/financial/board/funds')
    },
    staleTime: 10 * 60 * 1000,
  })

  const { data: acquisitionSpending, isLoading: acquisitionLoading } = useQuery({
    queryKey: ['board-acquisition-spending'],
    queryFn: async () => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      return fetchApi<any>(`/financial/board/acquisition-spending?year=${new Date().getFullYear()}`)
    },
    staleTime: 10 * 60 * 1000,
  })

  // ==================== Export Handlers ====================

  const handleExport = useCallback(
    async (reportType: string) => {
      try {
        const token = getAccessToken()
        // eslint-disable-next-line no-restricted-syntax -- CSV report export, blob response
        const response = await fetch(
          `/api/v1/financial/reports/export/${reportType}?format=csv&start_date=${format(
            startDate,
            'yyyy-MM-dd'
          )}&end_date=${format(endDate, 'yyyy-MM-dd')}`,
          {
            headers: {
              ...(token ? { Authorization: `Bearer ${token}` } : {}),
            },
          }
        )

        if (!response.ok) {
          throw new Error(`Export failed: ${response.statusText}`)
        }

        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = `${reportType}-${format(new Date(), 'yyyy-MM-dd')}.csv`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        window.URL.revokeObjectURL(url)

        toast.success(t('toast.boardTreasurerDashboard.reporttypeExportedSuccessfully', { reportType: reportType }))
      } catch (error: unknown) {
        Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
        toast.error(t('boardTreasurerDashboard.failedToExportReport'))
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [startDate, endDate]
  )

  // ==================== Format Helpers ====================

  const formatCurrency = (amount: number) => {
    if (hideSensitiveData) {
      return '••••••'
    }
    return amount.toLocaleString(getCurrentLocale(), {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    })
  }

  // API returns decimal (0.05 = 5%), multiply by 100 for display
  const formatPercentage = (value: number) => {
    return `${(value * 100).toFixed(1)}%`
  }

  // ==================== Render ====================

  return (

    <AdminShell
      title="Board Treasurer Dashboard"
      subtitle="Comprehensive financial analysis and reporting"
      actions={
        <button
          onClick={() => setHideSensitiveData(!hideSensitiveData)}
          className="flex items-center gap-2 px-4 py-2 bg-earth-100 dark:bg-earth-700 hover:bg-earth-200 dark:hover:bg-earth-600 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm font-medium rounded transition-colors"
        >
          {hideSensitiveData ? (
            <>
              <Eye className="w-4 h-4" />
              Show Data
            </>
          ) : (
            <>
              <EyeOff className="w-4 h-4" />
              Hide Data
            </>
          )}
        </button>
      }
    >
        {/* Filter Panel */}
        <FilterPanel
          startDate={startDate}
          endDate={endDate}
          onDateRangeChange={(start, end) => {
            setStartDate(start)
            setEndDate(end)
          }}
          isLoading={
            revenueLoading ||
            trendsLoading ||
            paymentLoading ||
            balancesLoading ||
            budgetLoading
          }
        />

        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatCard
            title="Total Revenue"
            value={formatCurrency(revenueSummary?.total_revenue || 0)}
            icon={<DollarSign className="w-6 h-6" />}
            color="success"
            loading={revenueLoading}
          />
          <StatCard
            title="Collection Rate"
            value={formatPercentage(fineTrends?.collection_rate || 0)}
            icon={<TrendingUp className="w-6 h-6" />}
            color="accent"
            loading={trendsLoading}
          />
          <StatCard
            title="Outstanding Balance"
            value={formatCurrency(outstandingBalances?.total_outstanding || 0)}
            icon={<AlertCircle className="w-6 h-6" />}
            color="danger"
            loading={balancesLoading}
          />
          <StatCard
            title="Budget Variance"
            value={formatPercentage(
              Math.abs(budgetVsActual?.variance_percentage || 0)
            )}
            icon={<BarChart3 className="w-6 h-6" />}
            color="yellow"
            loading={budgetLoading}
            trend={{
              value:
                (budgetVsActual?.variance_percentage || 0) > 0 ? 5 : -3,
              direction: (budgetVsActual?.variance_percentage || 0) > 0 ? 'up' : 'down',
            }}
          />
        </div>

        {/* Revenue Summary */}
        <DataTable
          title="Revenue by Type"
          headers={['Type', 'Amount', 'Count']}
          rows={
            revenueSummary?.by_type
              ? Object.entries(revenueSummary.by_type).map(([type, data]) => {
                  const item = data as unknown as { count: number; total: number }
                  return {
                    Type: type,
                    Amount: hideSensitiveData ? '••••••' : (item?.total ?? data),
                    Count: item?.count ?? 0,
                  }
                })
              : []
          }
          loading={revenueLoading}
          onExport={() => handleExport('revenue_summary')}
        />

        {/* Payment Methods */}
        <DataTable
          title="Payment Methods Breakdown"
          headers={['Method', 'Count', 'Amount', 'Percentage']}
          rows={
            paymentMethods
              ? Object.entries(
                  (paymentMethods as unknown as { payment_methods?: Record<string, { count: number; total: number; percentage: number }> }).payment_methods ?? paymentMethods.methods ?? {}
                ).map(([name, data]) => {
                  const item = typeof data === 'object' ? data : { count: 0, total: 0, percentage: 0 }
                  return {
                    Method: name,
                    Count: item.count ?? 0,
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    Amount: hideSensitiveData ? '••••••' : (item.total ?? (item as any).amount ?? 0),
                    Percentage: formatPercentage((item.percentage ?? 0) / 100),
                  }
                })
              : []
          }
          loading={paymentLoading}
          onExport={() => handleExport('payment_methods')}
        />

        {/* Outstanding Balances by Age */}
        <DataTable
          title={t('boardTreasurerDashboard.outstandingBalancesByAge')}
          headers={['Age Category', 'Amount']}
          rows={
            outstandingBalances?.by_age
              ? Object.entries(outstandingBalances.by_age).map(
                  ([category, amount]) => ({
                    'Age Category': category,
                    Amount: hideSensitiveData ? '••••••' : (amount as number),
                  })
                )
              : []
          }
          loading={balancesLoading}
          onExport={() => handleExport('outstanding_balances')}
        />

        {/* Top Delinquent Accounts */}
        {outstandingBalances?.delinquent_accounts &&
          outstandingBalances.delinquent_accounts.length > 0 && (
            <DataTable
              title={t('boardTreasurerDashboard.topDelinquentAccountsDaysOverdue')}
              headers={['Patron', 'Balance', 'Days Overdue']}
              rows={outstandingBalances.delinquent_accounts
                .slice(0, 10)
                .map((account) => ({
                  Patron: account.patron_name,
                  Balance: hideSensitiveData ? '••••••' : account.balance,
                  'Days Overdue': account.days_overdue,
                }))}
              loading={balancesLoading}
            />
          )}

        {/* Budget vs Actual */}
        <DataTable
          title={t('boardTreasurerDashboard.budgetVsActualAnalysis')}
          headers={['Month', 'Budget', 'Actual', 'Variance']}
          rows={
            budgetVsActual?.monthly
              ? budgetVsActual.monthly.map((month) => ({
                  Month: month.month,
                  Budget: hideSensitiveData ? '••••••' : month.budget,
                  Actual: hideSensitiveData ? '••••••' : month.actual,
                  Variance: hideSensitiveData
                    ? '••••••'
                    : ((month.actual - month.budget) / month.budget * 100).toFixed(1) + '%',
                }))
              : []
          }
          loading={budgetLoading}
          onExport={() => handleExport('budget_vs_actual')}
        />

        {/* Fund Management */}
        <DataTable
          title="Fund Management & Allocations"
          headers={['Fund Name', 'Balance', 'Allocated', 'Spent', 'Utilization']}
          rows={
            funds?.funds
              ? funds.funds.map((fund: { name: string; balance: number; allocated: number; spent: number; utilization_percentage: number }) => ({
                  'Fund Name': fund.name,
                  Balance: hideSensitiveData ? '••••••' : fund.balance,
                  Allocated: hideSensitiveData ? '••••••' : fund.allocated,
                  Spent: hideSensitiveData ? '••••••' : fund.spent,
                  Utilization: `${fund.utilization_percentage.toFixed(1)}%`,
                }))
              : []
          }
          loading={fundsLoading}
        />

        {/* Acquisition Spending */}
        <DataTable
          title={t('boardTreasurerDashboard.acquisitionSpendingByCategory')}
          headers={['Category', 'Spent', 'Budget', 'Utilization']}
          rows={
            acquisitionSpending?.by_category
              ? acquisitionSpending.by_category.map((cat: { category: string; spent: number; budget: number }) => ({
                  Category: cat.category,
                  Spent: hideSensitiveData ? '••••••' : cat.spent,
                  Budget: hideSensitiveData ? '••••••' : cat.budget,
                  Utilization: `${((cat.spent / cat.budget) * 100).toFixed(1)}%`,
                }))
              : []
          }
          loading={acquisitionLoading}
        />

        {/* Top Vendors */}
        <DataTable
          title="Top Acquisition Vendors"
          headers={['Vendor', 'Spending', 'Orders']}
          rows={
            acquisitionSpending?.top_vendors
              ? acquisitionSpending.top_vendors.map((vendor: { name: string; spending: number; orders: number }) => ({
                  Vendor: vendor.name,
                  Spending: hideSensitiveData ? '••••••' : vendor.spending,
                  Orders: vendor.orders,
                }))
              : []
          }
          loading={acquisitionLoading}
        />

        {/* Summary Statistics */}
        <div className="bg-earth-50 dark:bg-earth-800/20 p-6 rounded-lg border border-lsc-border dark:border-earth-700">
          <h3 className="font-serif text-lg font-semibold mb-4 text-lsc-dark dark:text-lsc-cream">
            Financial Summary
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Collected</p>
              <p className="text-2xl font-bold text-lsc-rose dark:text-lsc-rose-light">
                {formatCurrency(fineTrends?.total_collected || 0)}
              </p>
            </div>
            <div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Outstanding</p>
              <p className="text-2xl font-bold text-status-danger-600">
                {formatCurrency(fineTrends?.total_outstanding || 0)}
              </p>
            </div>
            {budgetVsActual && (
              <>
                <div>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Budget</p>
                  <p className="text-2xl font-bold text-status-success-600">
                    {formatCurrency(budgetVsActual.total_budget ?? 0)}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Actual</p>
                  <p className="text-2xl font-bold text-status-success-600">
                    {formatCurrency(budgetVsActual.total_actual ?? 0)}
                  </p>
                </div>
              </>
            )}
          </div>
        </div>
    </AdminShell>
  )
}

// ==================== Main Component ====================

export const BoardTreasurerDashboardPage: React.FC = () => {
  const { t } = useTranslation();
  const { user } = useAuth()
  const [startDate, setStartDate] = useState(
    startOfMonth(subMonths(new Date(), 3))
  )
  const [endDate, setEndDate] = useState(endOfMonth(new Date()))
  const [hideSensitiveData, setHideSensitiveData] = useState(false)

  // Permission check
  if (
    !user ||
    !['admin', 'super_admin'].includes(user.role)
  ) {
    return (
      <div className="min-h-screen bg-lsc-cream dark:bg-earth-900 flex items-center justify-center">
        <div className="text-center">
          <Lock className="w-16 h-16 text-status-danger-600 mx-auto mb-4" />
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">Staff-Only Area</h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('boardTreasurerDashboard.youDonTHavePermission')}</p>
        </div>
      </div>
    )
  }

  return (
    <TreasurerDashboardBody
      startDate={startDate}
      endDate={endDate}
      setStartDate={setStartDate}
      setEndDate={setEndDate}
      hideSensitiveData={hideSensitiveData}
      setHideSensitiveData={setHideSensitiveData}
    />
  )
}

export default BoardTreasurerDashboardPage
