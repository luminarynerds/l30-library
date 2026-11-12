/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useTranslation} from '@/i18n'
import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../contexts/AuthContext'
import {
  getStreamingDashboardStats,
  getBudgets,
  getServiceConfigs,
  updateServiceConfig,
  createBudget,
  StreamingDashboardStats,
  StreamingBudget,
  StreamingServiceConfig,
  formatServiceName,
  formatContentType,
  type StreamingContentType,
} from '../api/streaming-api'
import {
  Play,
  DollarSign,
  Users,
  TrendingUp,
  BarChart3,
  Settings,
  RefreshCw,
  Loader2,
  Film,
  Headphones,
  BookOpen,
  Music,
  AlertTriangle,
  CheckCircle,
  Pencil,
  Plus,
  X,
  Save,
} from 'lucide-react'
import toast from 'react-hot-toast'
import PageContainer from '@/components/layout/PageContainer'

type TabType = 'overview' | 'budgets' | 'settings'

export default function StaffStreamingPage() {
  const { t } = useTranslation()
  const { token, user } = useAuth()
  const [activeTab, setActiveTab] = useState<TabType>('overview')
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState<StreamingDashboardStats | null>(null)
  const [budgets, setBudgets] = useState<StreamingBudget[]>([])
  const [configs, setConfigs] = useState<StreamingServiceConfig[]>([])
  const [refreshing, setRefreshing] = useState(false)

  const isAdmin = user && ['admin', 'super_admin'].includes(user.role)

  const fetchData = useCallback(async () => {
    if (!token) return
    try {
      const [statsData, budgetsData, configsData] = await Promise.all([
        getStreamingDashboardStats(token),
        getBudgets(token),
        getServiceConfigs(token),
      ])
      setStats(statsData)
      setBudgets(budgetsData)
      setConfigs(configsData)
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('staffStreaming.failedToLoadStreamingData'))
    } finally {
      setLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handleRefresh = async () => {
    setRefreshing(true)
    await fetchData()
    setRefreshing(false)
    toast.success(t('toast.staffStreaming.dataRefreshed'))
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-status-info-600" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-lsc-cream dark:bg-earth-900">
      {/* Header */}
      <div className="bg-lsc-white dark:bg-earth-800 border-b">
        <PageContainer width="wide" className="py-6">
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              {t('staffStreaming.streamingServices', 'Streaming Services')}
            </h1>
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="flex items-center gap-2 px-4 py-2 bg-status-info-600 text-white rounded-lg hover:bg-status-info-700 disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'motion-safe:animate-spin' : ''}`} />
              Refresh
            </button>
          </div>

          {/* Tabs */}
          <div className="flex gap-4 mt-6">
            {[
              { id: 'overview', label: 'Overview', icon: BarChart3 },
              { id: 'budgets', label: 'Budgets', icon: DollarSign },
              ...(isAdmin ? [{ id: 'settings', label: 'Settings', icon: Settings }] : []),
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as TabType)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                  activeTab === tab.id
                    ? 'bg-status-info-100 dark:bg-status-info-900/30 text-status-info-700 dark:text-status-info-300'
                    : 'text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-100 dark:hover:bg-earth-700'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
          </div>
        </PageContainer>
      </div>

      {/* Content */}
      <PageContainer width="wide" className="py-6">
        {activeTab === 'overview' && stats && <OverviewTab stats={stats} />}
        {activeTab === 'budgets' && <BudgetsTab budgets={budgets} configs={configs} onUpdate={fetchData} />}
        {activeTab === 'settings' && isAdmin && (
          <SettingsTab configs={configs} onUpdate={fetchData} />
        )}
      </PageContainer>
    </div>
  )
}

// Overview Tab Component
function OverviewTab({ stats }: { stats: StreamingDashboardStats }) {
  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={Play}
          label="Checkouts This Month"
          value={stats.total_checkouts_this_month?.toLocaleString() || '0'}
          color="accent"
        />
        <StatCard
          icon={DollarSign}
          label="Cost This Month"
          value={`$${parseFloat(stats.total_cost_this_month).toFixed(2)}`}
          color="success"
        />
        <StatCard
          icon={Users}
          label="Unique Patrons"
          value={stats.unique_patrons_this_month.toLocaleString()}
          color="category"
        />
        <StatCard
          icon={TrendingUp}
          label="Avg Cost per Checkout"
          value={`$${parseFloat(stats.average_cost_per_checkout).toFixed(2)}`}
          color="warning"
        />
      </div>

      {/* Budget Utilization */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-6">
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Budget Utilization</h3>
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <div className="flex justify-between text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
              <span>Spent: ${parseFloat(stats.total_budget_spent).toFixed(2)}</span>
              <span>
                Allocated: ${parseFloat(stats.total_budget_allocated).toFixed(2)}
              </span>
            </div>
            <div className="h-4 bg-earth-200 dark:bg-earth-600 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${
                  stats.budget_utilization_percentage > 90
                    ? 'bg-status-danger-500'
                    : stats.budget_utilization_percentage > 75
                    ? 'bg-status-warning-500'
                    : 'bg-status-success-500'
                }`}
                style={{ width: `${Math.min(stats.budget_utilization_percentage, 100)}%` }}
              />
            </div>
          </div>
          <div className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
            {stats.budget_utilization_percentage.toFixed(1)}%
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Service Breakdown */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-6">
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">By Service</h3>
          <div className="space-y-4">
            {stats.service_stats.map((service) => (
              <div key={service.service} className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div
                    className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                      service.service === 'palace' ? 'bg-status-success-100 dark:bg-status-success-900/30' : 'bg-status-info-100 dark:bg-status-info-900/30'
                    }`}
                  >
                    <Play
                      className={`w-5 h-5 ${
                        service.service === 'palace' ? 'text-status-success-600' : 'text-status-info-600'
                      }`}
                    />
                  </div>
                  <div>
                    <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                      {formatServiceName(service.service as 'palace')}
                    </p>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      {service.unique_patrons} patrons
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-semibold text-lsc-dark dark:text-lsc-cream">{service.checkouts} checkouts</p>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">${service.cost.toFixed(2)}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Content Type Breakdown */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-6">
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">By Content Type</h3>
          <div className="space-y-3">
            {Object.entries(stats.checkouts_by_content_type)
              .sort(([, a], [, b]) => b - a)
              .map(([type, count]) => {
                const total = Object.values(stats.checkouts_by_content_type).reduce(
                  (a, b) => a + b,
                  0
                )
                const percentage = total > 0 ? (count / total) * 100 : 0
                return (
                  <div key={type} className="flex items-center gap-3">
                    <ContentTypeIcon type={type} />
                    <div className="flex-1">
                      <div className="flex justify-between mb-1">
                        <span className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
                          {formatContentType(type as StreamingContentType)}
                        </span>
                        <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{count}</span>
                      </div>
                      <div className="h-2 bg-earth-200 dark:bg-earth-600 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-status-info-500 rounded-full"
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </div>
                  </div>
                )
              })}
          </div>
        </div>
      </div>

      {/* Top Titles */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-6">
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Top Titles</h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-sm text-lsc-dark/70 dark:text-lsc-cream/70 border-b">
                <th className="pb-3 font-medium">Rank</th>
                <th className="pb-3 font-medium">Title</th>
                <th className="pb-3 font-medium">Type</th>
                <th className="pb-3 font-medium text-right">Checkouts</th>
              </tr>
            </thead>
            <tbody>
              {stats.top_titles.map((title, index) => (
                <tr key={index} className="border-b last:border-0">
                  <td className="py-3 text-lsc-dark/70 dark:text-lsc-cream/70">#{index + 1}</td>
                  <td className="py-3 font-medium text-lsc-dark dark:text-lsc-cream">{title.title}</td>
                  <td className="py-3 text-lsc-dark/70 dark:text-lsc-cream/70">
                    {title.content_type ? formatContentType(title.content_type) : 'N/A'}
                  </td>
                  <td className="py-3 text-right font-semibold text-lsc-dark dark:text-lsc-cream">
                    {title.checkouts}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Daily Trend */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-6">
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Daily Checkouts Trend</h3>
        <div className="h-64 flex items-end gap-1">
          {stats.checkouts_trend.slice(-30).map((day) => {
            const maxCheckouts = Math.max(...stats.checkouts_trend.map((d) => d.checkouts), 1)
            const height = (day.checkouts / maxCheckouts) * 100
            return (
              <div
                key={day.date}
                className="flex-1 bg-status-info-500 rounded-t hover:bg-status-info-600 transition-colors cursor-pointer group relative"
                style={{ height: `${height}%`, minHeight: '4px' }}
                title={`${day.date}: ${day.checkouts} checkouts`}
              >
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-earth-800 text-white text-xs rounded opacity-0 group-hover:opacity-100 whitespace-nowrap">
                  {day.checkouts} checkouts
                  <br />
                  {new Date(day.date).toLocaleDateString()}
                </div>
              </div>
            )
          })}
        </div>
        <div className="flex justify-between text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
          <span>30 days ago</span>
          <span>Today</span>
        </div>
      </div>
    </div>
  )
}

// Budgets Tab Component
// Budgets Tab Component
function BudgetsTab({ budgets, configs, onUpdate }: { budgets: StreamingBudget[]; configs: StreamingServiceConfig[]; onUpdate: () => void }) {
  const { t } = useTranslation();
  const currentYear = new Date().getFullYear()
  const { token } = useAuth()
  const [showCreate, setShowCreate] = useState(false)
  const [createForm, setCreateForm] = useState({
    service_config_id: '',
    monthly_amount: '',
    fiscal_year: String(currentYear),
  })
  const [creating, setCreating] = useState(false)

  const handleCreateBudget = async () => {
    if (!token || !createForm.service_config_id || !createForm.monthly_amount) return
    setCreating(true)
    try {
      await createBudget(token, {
        service_config_id: Number(createForm.service_config_id),
        fiscal_year: Number(createForm.fiscal_year),
        allocated_amount: createForm.monthly_amount,
      })
      toast.success('Budget created')
      setShowCreate(false)
      setCreateForm({ service_config_id: '', monthly_amount: '', fiscal_year: String(currentYear) })
      onUpdate()
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error('Failed to create budget')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow">
        <div className="p-6 border-b flex items-center justify-between">
          <div>
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Streaming Budgets</h3>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{t('staffStreaming.viewBudgetAllocationAndUtilization')}</p>
          </div>
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="flex items-center gap-1 px-3 py-2 bg-status-info-600 text-white rounded-lg hover:bg-status-info-700 text-sm"
          >
            <Plus className="w-4 h-4" />
            Create Budget
          </button>
        </div>
        {showCreate && (
          <div className="p-6 border-b bg-earth-50 dark:bg-earth-900/50">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              <div>
                <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Service</label>
                <select
                  value={createForm.service_config_id}
                  onChange={(e) => setCreateForm({ ...createForm, service_config_id: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream border-lsc-border dark:border-earth-600 focus:ring-2 focus:ring-status-info-500 focus:border-status-info-500 text-sm"
                >
                  <option value="">Select service...</option>
                  {configs.map((c) => (
                    <option key={c.id} value={c.id}>
                      {formatServiceName(c.service)}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Monthly Amount ($)</label>
                <input
                  type="number"
                  step="0.01"
                  value={createForm.monthly_amount}
                  onChange={(e) => setCreateForm({ ...createForm, monthly_amount: e.target.value })}
                  placeholder="0.00"
                  className="w-full px-3 py-2 border rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream border-lsc-border dark:border-earth-600 focus:ring-2 focus:ring-status-info-500 focus:border-status-info-500 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Fiscal Year</label>
                <input
                  type="text"
                  value={createForm.fiscal_year}
                  onChange={(e) => setCreateForm({ ...createForm, fiscal_year: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream border-lsc-border dark:border-earth-600 focus:ring-2 focus:ring-status-info-500 focus:border-status-info-500 text-sm"
                />
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleCreateBudget}
                disabled={creating || !createForm.service_config_id || !createForm.monthly_amount}
                className="flex items-center gap-1 px-4 py-2 bg-status-info-600 text-white rounded-lg hover:bg-status-info-700 disabled:opacity-50 text-sm"
              >
                <Save className="w-4 h-4" />
                {creating ? 'Creating...' : 'Create'}
              </button>
              <button
                onClick={() => setShowCreate(false)}
                className="px-4 py-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-100 dark:hover:bg-earth-700 rounded-lg"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
        <div className="divide-y">
          {budgets.length === 0 ? (
            <div className="p-8 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
              <DollarSign className="w-12 h-12 mx-auto mb-4 text-earth-300" />
              <p>{t('staffStreaming.noBudgetsConfiguredYet')}</p>
              <p className="text-sm">{t('staffStreaming.contactAnAdministratorToSet')}</p>
            </div>
          ) : (
            budgets
              .filter((b) => b.fiscal_year === currentYear)
              .map((budget) => (
                <div key={budget.id} className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                          budget.service_name === 'palace' ? 'bg-status-success-100 dark:bg-status-success-900/30' : 'bg-status-info-100 dark:bg-status-info-900/30'
                        }`}
                      >
                        <Play
                          className={`w-5 h-5 ${
                            budget.service_name === 'palace'
                              ? 'text-status-success-600'
                              : 'text-status-info-600'
                          }`}
                        />
                      </div>
                      <div>
                        <h4 className="font-medium text-lsc-dark dark:text-lsc-cream">
                          {budget.service_name
                            ? formatServiceName(budget.service_name as 'palace')
                            : 'Unknown Service'}
                        </h4>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                          FY {budget.fiscal_year}
                          {budget.fiscal_month && ` - Month ${budget.fiscal_month}`}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {budget.utilization_percentage > 90 ? (
                        <AlertTriangle className="w-5 h-5 text-status-danger-500" />
                      ) : budget.utilization_percentage > 75 ? (
                        <AlertTriangle className="w-5 h-5 text-status-warning-500" />
                      ) : (
                        <CheckCircle className="w-5 h-5 text-status-success-500" />
                      )}
                      <span
                        className={`text-lg font-bold ${
                          budget.utilization_percentage > 90
                            ? 'text-status-danger-600'
                            : budget.utilization_percentage > 75
                            ? 'text-status-warning-600'
                            : 'text-status-success-600'
                        }`}
                      >
                        {budget.utilization_percentage.toFixed(1)}% used
                      </span>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                    <div>
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Allocated</p>
                      <p className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                        ${parseFloat(budget.allocated_amount).toLocaleString()}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Spent</p>
                      <p className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                        ${parseFloat(budget.spent_amount).toLocaleString()}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Remaining</p>
                      <p className="text-lg font-semibold text-status-success-600">
                        ${parseFloat(budget.remaining_amount).toLocaleString()}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Checkouts</p>
                      <p className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                        {budget.current_checkouts}
                        {budget.max_checkouts && ` / ${budget.max_checkouts}`}
                      </p>
                    </div>
                  </div>

                  <div className="h-3 bg-earth-200 dark:bg-earth-600 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        budget.utilization_percentage > 90
                          ? 'bg-status-danger-500'
                          : budget.utilization_percentage > 75
                          ? 'bg-status-warning-500'
                          : 'bg-status-success-500'
                      }`}
                      style={{ width: `${Math.min(budget.utilization_percentage, 100)}%` }}
                    />
                  </div>
                </div>
              ))
          )}
        </div>
      </div>
    </div>
  )
}

// Settings Tab Component (Admin only)
function SettingsTab({
  configs,
  onUpdate,
}: {
  configs: StreamingServiceConfig[]
  onUpdate: () => void
}) {
  const { t } = useTranslation()
  const { token } = useAuth()
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editForm, setEditForm] = useState<{
    is_active: boolean
    api_base_url: string
    library_id: string
    cost_per_checkout: string
    web_deep_link_template: string
  }>({ is_active: true, api_base_url: '', library_id: '', cost_per_checkout: '', web_deep_link_template: '' })
  const [saving, setSaving] = useState(false)

  const startEdit = (config: StreamingServiceConfig) => {
    setEditingId(config.id)
    setEditForm({
      is_active: config.is_active,
      api_base_url: config.api_base_url,
      library_id: config.library_id || '',
      cost_per_checkout: config.cost_per_checkout,
      web_deep_link_template: config.web_deep_link_template || '',
    })
  }

  const cancelEdit = () => {
    setEditingId(null)
  }

  const saveEdit = async () => {
    if (!token || editingId === null) return
    setSaving(true)
    try {
      const updates: Parameters<typeof updateServiceConfig>[2] = {
        is_active: editForm.is_active,
        api_base_url: editForm.api_base_url,
        cost_per_checkout: editForm.cost_per_checkout,
      }
      if (editForm.library_id) updates.library_id = editForm.library_id
      if (editForm.web_deep_link_template) updates.web_deep_link_template = editForm.web_deep_link_template
      await updateServiceConfig(token, editingId, updates)
      toast.success('Configuration updated')
      setEditingId(null)
      onUpdate()
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error('Failed to update configuration')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow">
        <div className="p-6 border-b">
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Service Configurations</h3>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
            Manage streaming service API connections and settings
          </p>
        </div>
        <div className="divide-y">
          {configs.length === 0 ? (
            <div className="p-8 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
              <Settings className="w-12 h-12 mx-auto mb-4 text-earth-300" />
              <p>{t('staffStreaming.noStreamingServicesConfiguredYet')}</p>
            </div>
          ) : (
            configs.map((config) => (
              <div key={config.id} className="p-6">
                {editingId === config.id ? (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                        {formatServiceName(config.service)}
                      </h4>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={saveEdit}
                          disabled={saving}
                          className="flex items-center gap-1 px-3 py-1.5 bg-status-info-600 text-white rounded-lg hover:bg-status-info-700 disabled:opacity-50 text-sm"
                        >
                          <Save className="w-3.5 h-3.5" />
                          {saving ? 'Saving...' : 'Save'}
                        </button>
                        <button
                          onClick={cancelEdit}
                          className="flex items-center gap-1 px-3 py-1.5 bg-earth-200 dark:bg-earth-600 text-lsc-dark/70 dark:text-lsc-cream/70 rounded-lg hover:bg-earth-300 dark:hover:bg-earth-500 text-sm"
                        >
                          <X className="w-3.5 h-3.5" />
                          Cancel
                        </button>
                      </div>
                    </div>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={editForm.is_active}
                        onChange={(e) => setEditForm({ ...editForm, is_active: e.target.checked })}
                        className="w-4 h-4 rounded border-lsc-border text-status-info-600 focus:ring-status-info-500"
                      />
                      <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Active</span>
                    </label>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">API Base URL</label>
                        <input
                          type="text"
                          value={editForm.api_base_url}
                          onChange={(e) => setEditForm({ ...editForm, api_base_url: e.target.value })}
                          className="w-full px-3 py-2 border rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream border-lsc-border dark:border-earth-600 focus:ring-2 focus:ring-status-info-500 focus:border-status-info-500 text-sm font-mono"
                        />
                      </div>
                      <div>
                        <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Library ID</label>
                        <input
                          type="text"
                          value={editForm.library_id}
                          onChange={(e) => setEditForm({ ...editForm, library_id: e.target.value })}
                          className="w-full px-3 py-2 border rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream border-lsc-border dark:border-earth-600 focus:ring-2 focus:ring-status-info-500 focus:border-status-info-500 text-sm"
                        />
                      </div>
                      <div>
                        <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Cost per Checkout</label>
                        <input
                          type="number"
                          step="0.01"
                          value={editForm.cost_per_checkout}
                          onChange={(e) => setEditForm({ ...editForm, cost_per_checkout: e.target.value })}
                          className="w-full px-3 py-2 border rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream border-lsc-border dark:border-earth-600 focus:ring-2 focus:ring-status-info-500 focus:border-status-info-500 text-sm"
                        />
                      </div>
                      <div>
                        <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Web Deep Link Template</label>
                        <input
                          type="text"
                          value={editForm.web_deep_link_template}
                          onChange={(e) => setEditForm({ ...editForm, web_deep_link_template: e.target.value })}
                          className="w-full px-3 py-2 border rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream border-lsc-border dark:border-earth-600 focus:ring-2 focus:ring-status-info-500 focus:border-status-info-500 text-sm font-mono"
                        />
                      </div>
                    </div>
                  </div>
                ) : (
                  <>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div
                      className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                        config.service === 'palace' ? 'bg-status-success-100 dark:bg-status-success-900/30' : 'bg-status-info-100 dark:bg-status-info-900/30'
                      }`}
                    >
                      <Play
                        className={`w-6 h-6 ${
                          config.service === 'palace' ? 'text-status-success-600' : 'text-status-info-600'
                        }`}
                      />
                    </div>
                    <div>
                      <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                        {formatServiceName(config.service)}
                      </h4>
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        Library ID: {config.library_id || 'Not configured'}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                        <button
                          onClick={() => startEdit(config)}
                          className="flex items-center gap-1 px-3 py-1.5 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-100 dark:hover:bg-earth-700 rounded-lg transition-colors"
                        >
                          <Pencil className="w-3.5 h-3.5" />
                          Edit
                        </button>
                    <span
                      className={`px-3 py-1 rounded-full text-sm font-medium ${
                        config.is_active
                          ? 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-300'
                          : 'bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70'
                      }`}
                    >
                      {config.is_active ? 'Active' : 'Inactive'}
                    </span>
                    <div className="text-right">
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Cost per checkout</p>
                      <p className="font-semibold text-lsc-dark dark:text-lsc-cream">
                        ${parseFloat(config.cost_per_checkout).toFixed(2)}
                      </p>
                    </div>
                  </div>
                </div>
                <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70">API Base URL</p>
                    <p className="text-lsc-dark dark:text-lsc-cream font-mono text-xs truncate" title={config.api_base_url}>
                      {config.api_base_url}
                    </p>
                  </div>
                  <div>
                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70">Last Updated</p>
                    <p className="text-lsc-dark dark:text-lsc-cream">
                      {new Date(config.updated_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
                    </>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}

// Helper Components
function StatCard({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: React.ElementType
  label: string
  value: string
  color: 'accent' | 'success' | 'category' | 'warning'
}) {
  const colors = {
    accent: 'bg-status-info-100 dark:bg-status-info-900/30 text-status-info-600',
    success: 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-600',
    category: 'bg-category-100 dark:bg-category-900/30 text-category-600',
    warning: 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-600',
  }

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-6">
      <div className="flex items-center gap-4">
        <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${colors[color]}`}>
          <Icon className="w-6 h-6" />
        </div>
        <div>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{label}</p>
          <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{value}</p>
        </div>
      </div>
    </div>
  )
}

function ContentTypeIcon({ type }: { type: string }) {
  const icons: Record<string, React.ElementType> = {
    movie: Film,
    tv_series: Film,
    tv_episode: Film,
    documentary: Film,
    audiobook: Headphones,
    ebook: BookOpen,
    music_album: Music,
    comic: BookOpen,
  }

  const Icon = icons[type] || Play

  return (
    <div className="w-8 h-8 rounded bg-earth-100 dark:bg-earth-700 flex items-center justify-center">
      <Icon className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
    </div>
  )
}
