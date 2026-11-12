/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { DollarSign, TrendingUp, TrendingDown, Download } from 'lucide-react'
import toast from 'react-hot-toast'
import { fetchApi } from '@/api/fetchApi'
import { useTranslation} from '@/i18n'
import { AdminShell } from '../components/shells/AdminShell'

interface FinancialData {
  month: string
  revenue: number
  expenses: number
  fine: number
}

interface Fund {
  id: number
  name: string
  balance: number
  budget: number
}

export default function FinancialReportsPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user, token } = useAuth()
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [fines, setFines] = useState<FinancialData[]>([])
  const [funds, setFunds] = useState<Fund[]>([])
  const [totalRevenue, setTotalRevenue] = useState(0)
  const [totalExpenses, setTotalExpenses] = useState(0)

  const loadFinancialData = async () => {
    if (!token) return
    setIsLoading(true)
    setError(null)
    try {
      const [revenueRes, fundsRes] = await Promise.allSettled([
        fetchApi('/financial/reports/revenue-summary'),
        fetchApi('/financial/board/funds'),
      ])

      if (revenueRes.status === 'fulfilled') {
        try {
          const data = revenueRes.value
          const items = (data.monthly_breakdown || []).map((m: { month: string; revenue: number }) => ({
            month: m.month,
            revenue: m.revenue,
            expenses: 0,
            fine: m.revenue,
          }))
          setFines(items)
          setTotalRevenue(data.total_revenue || 0)
          setTotalExpenses(0)
        } catch (parseErr) {
          Sentry.captureException(parseErr instanceof Error ? parseErr : new Error(String(parseErr)))
          setError('Failed to parse financial data from server.')
        }
      } else {
        Sentry.captureException(revenueRes.reason instanceof Error ? revenueRes.reason : new Error(String(revenueRes.reason)))
        setError('Failed to load financial data. Server returned an error.')
      }

      if (fundsRes.status === 'fulfilled') {
        try {
          const data = fundsRes.value
          const fundItems = (data.funds || []).map((f: { id: number; name: string; available_amount: number; allocated_amount: number }) => ({
            id: f.id,
            name: f.name,
            balance: f.available_amount,
            budget: f.allocated_amount,
          }))
          setFunds(fundItems)
        } catch (parseErr) {
          Sentry.captureException(parseErr instanceof Error ? parseErr : new Error(String(parseErr)))
          setError('Failed to parse fund data from server.')
        }
      } else {
        // Funds endpoint may return 501 if not yet configured - that's ok
        const reason = fundsRes.reason as { status?: number } | undefined
        if (reason?.status !== 501) {
          setError('Failed to load fund data. Server returned an error.')
        }
      }
    } catch (_err) {
      Sentry.captureException(_err instanceof Error ? _err : new Error(String(_err)))
      setError('Unable to load financial data. Please try again later.')
      toast.error(t('financialReports.failedToLoadFinancialData'))
    } finally {
      setIsLoading(false)
    }
  }


  useEffect(() => {
    if (!user || !['admin', 'super_admin'].includes(user.role)) {
      toast.error(t('toast.adminAPIStatus.adminAccessRequired'))
      return
    }
    loadFinancialData()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user])

  const handleExportCSV = () => {
    const headers = ['Month', 'Revenue', 'Expenses', 'Fines']
    const rows = fines.map((item) => [item.month, item.revenue, item.expenses, item.fine])
    const csv = [headers, ...rows].map((r) => r.join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `financial-report-${new Date().toISOString().split('T')[0]}.csv`
    a.click()
  }

  if (!user || !['admin', 'super_admin'].includes(user.role)) {
    return (
      <AdminShell title="Financial Reports">
        <div className="text-center py-12">
          <p className="text-lsc-dark dark:text-lsc-cream">Admin access required</p>
        </div>
      </AdminShell>
    )
  }

  if (error) {
    return (
      <AdminShell title="Financial Reports">
        <div className="text-center py-12">
          <p className="text-earth-600 dark:text-earth-400">Unable to load financial data. Please try again later.</p>
          <button onClick={loadFinancialData} className="mt-4 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90">
            Retry
          </button>
        </div>
      </AdminShell>
    );
  }

  return (
    <AdminShell title="Financial Reports" subtitle={t('financialReports.revenueExpensesAndFundManagement')} loading={isLoading} actions={
      <button onClick={handleExportCSV} className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl flex items-center gap-2 transition-colors">
        <Download className="w-5 h-5" />
        Export CSV
      </button>
    }>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border-l-4 border-status-success-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm font-medium">Total Revenue</p>
              <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream mt-1">${totalRevenue.toLocaleString()}</p>
            </div>
            <TrendingUp className="w-12 h-12 text-status-success-500 opacity-20" />
          </div>
        </div>

        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border-l-4 border-status-danger-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm font-medium">Total Expenses</p>
              <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream mt-1">${totalExpenses.toLocaleString()}</p>
            </div>
            <TrendingDown className="w-12 h-12 text-status-danger-500 opacity-20" />
          </div>
        </div>

        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border-l-4 border-lsc-rose">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm font-medium">Net Balance</p>
              <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream mt-1">${(totalRevenue - totalExpenses).toLocaleString()}</p>
            </div>
            <DollarSign className="w-12 h-12 text-lsc-rose opacity-20" />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl">
          <div className="p-6 border-b border-lsc-border dark:border-earth-700">
            <h2 className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Fines by Month</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-lsc-cream dark:bg-lsc-brown">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark dark:text-lsc-cream">Month</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-lsc-dark dark:text-lsc-cream">Fines</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                {fines.map((item, idx) => (
                  <tr key={idx} className="hover:bg-lsc-cream dark:hover:bg-lsc-brown/50">
                    <td className="px-4 py-3 text-sm text-lsc-dark dark:text-lsc-cream">{item.month}</td>
                    <td className="px-4 py-3 text-sm text-right font-medium text-lsc-dark dark:text-lsc-cream">${item.fine.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl">
          <div className="p-6 border-b border-lsc-border dark:border-earth-700">
            <h2 className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Funds</h2>
          </div>
          <div className="p-6 space-y-4">
            {funds.map((fund) => (
              <div key={fund.id} className="border border-lsc-border dark:border-earth-700 rounded-xl p-4">
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">{fund.name}</h3>
                  <span className="text-sm font-semibold text-lsc-rose">${fund.balance.toLocaleString()}</span>
                </div>
                <div className="w-full bg-lsc-cream dark:bg-lsc-brown rounded-full h-2">
                  <div className="bg-lsc-rose rounded-full h-2" style={{ width: `${Math.min((fund.balance / fund.budget) * 100, 100)}%` }} />
                </div>
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">Budget: ${fund.budget.toLocaleString()}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AdminShell>
  )
}
