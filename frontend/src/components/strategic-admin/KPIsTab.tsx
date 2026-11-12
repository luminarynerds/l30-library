/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from 'react'
import { Plus, Edit2, Trash2, TrendingUp, TrendingDown, Minus, AlertTriangle, CheckCircle2 } from 'lucide-react'
import * as Sentry from '@/lib/sentry-lazy'
import toast from 'react-hot-toast'
import ConfirmDialog from '@/components/ConfirmDialog'
import KPIModal from './KPIModal'
import {
  StrategicKPI,
  KPIAlert,
  getKpis,
  createKpi,
  updateKpi,
  deleteKpi,
  recordKpiValue,
  acknowledgeKpiAlert,
  resolveKpiAlert,
} from '@/api/domains/admin/strategic-api'

interface Props {
  planId: number
  isAdmin: boolean
}

type KPIForm = Partial<StrategicKPI> & { name: string }

const categoryColors: Record<string, string> = {
  Financial: 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300',
  Operational: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300',
  Customer: 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300',
  Learning: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300',
}

const alertSeverityColors: Record<string, string> = {
  info: 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-700 text-blue-800 dark:text-blue-200',
  warning: 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-700 text-yellow-800 dark:text-yellow-200',
  critical: 'bg-status-danger-50 dark:bg-status-danger-900/20 border-status-danger-200 dark:border-status-danger-700 text-status-danger-800 dark:text-status-danger-200',
}

function blankKPI(): KPIForm {
  return { name: '', description: '', category: '', unit_of_measure: '', frequency: 'monthly', data_source: '' }
}

function formatValue(val?: string, unit?: string): string {
  if (val == null || val === '') return '—'
  const n = parseFloat(val)
  if (isNaN(n)) return val
  return unit ? `${n.toLocaleString()} ${unit}` : n.toLocaleString()
}

function varianceColor(variance?: string): string {
  if (!variance) return 'text-lsc-dark/60 dark:text-lsc-cream/60'
  const n = parseFloat(variance)
  if (isNaN(n)) return 'text-lsc-dark/60 dark:text-lsc-cream/60'
  return n >= 0 ? 'text-status-success-600 dark:text-status-success-400' : 'text-status-danger-600 dark:text-status-danger-400'
}

function TrendIcon({ direction }: { direction?: string }) {
  if (direction === 'up') return <TrendingUp className="h-4 w-4 inline" aria-label="trending up" />
  if (direction === 'down') return <TrendingDown className="h-4 w-4 inline" aria-label="trending down" />
  return <Minus className="h-4 w-4 inline" aria-label="stable" />
}

function activeAlerts(kpi: StrategicKPI): KPIAlert[] {
  return kpi.alerts.filter((a) => !a.acknowledged && !a.resolved)
}

interface RecordValueState {
  kpiId: number
  value: string
  notes: string
  is_estimated: boolean
}

export default function KPIsTab({ planId, isAdmin }: Props) {
  const [kpis, setKpis] = useState<StrategicKPI[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState<KPIForm>(blankKPI())

  const [deleteConfirm, setDeleteConfirm] = useState<{ id: number; name: string } | null>(null)

  const [recordState, setRecordState] = useState<RecordValueState | null>(null)

  const load = useCallback(async () => {
    setLoadError(null)
    setLoading(true)
    try {
      const data = await getKpis(planId)
      setKpis(data)
    } catch (err) {
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
      setLoadError(err instanceof Error ? err.message : 'Failed to load KPIs')
    } finally {
      setLoading(false)
    }
  }, [planId])

  useEffect(() => { load() }, [load])

  const openAdd = () => {
    setEditing(blankKPI())
    setShowModal(true)
  }

  const openEdit = (kpi: StrategicKPI) => {
    setEditing({ ...kpi })
    setShowModal(true)
  }

  const saveKpi = async () => {
    if (!editing.name) return
    try {
      if (editing.id) {
        const updated = await updateKpi(editing.id, {
          name: editing.name,
          description: editing.description,
          category: editing.category,
          unit_of_measure: editing.unit_of_measure,
          target_value: editing.target_value,
          baseline_value: editing.baseline_value,
          threshold_red: editing.threshold_red,
          threshold_yellow: editing.threshold_yellow,
          threshold_green: editing.threshold_green,
          frequency: editing.frequency,
          data_source: editing.data_source,
          is_active: editing.is_active,
        })
        setKpis((prev) => prev.map((k) => (k.id === updated.id ? updated : k)))
        toast.success('KPI updated')
      } else {
        const created = await createKpi(planId, {
          name: editing.name,
          description: editing.description,
          category: editing.category,
          unit_of_measure: editing.unit_of_measure,
          target_value: editing.target_value,
          baseline_value: editing.baseline_value,
          threshold_red: editing.threshold_red,
          threshold_yellow: editing.threshold_yellow,
          threshold_green: editing.threshold_green,
          frequency: editing.frequency,
          data_source: editing.data_source,
        })
        setKpis((prev) => [...prev, created])
        toast.success('KPI created')
      }
      setShowModal(false)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to save KPI')
    }
  }

  const confirmDelete = async (id: number) => {
    try {
      await deleteKpi(id)
      setKpis((prev) => prev.filter((k) => k.id !== id))
      setDeleteConfirm(null)
      toast.success('KPI deleted')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to delete KPI')
    }
  }

  const submitRecordValue = async () => {
    if (!recordState || !recordState.value) return
    const { kpiId, value, notes, is_estimated } = recordState
    try {
      const updated = await recordKpiValue(kpiId, {
        value,
        notes: notes || undefined,
        is_estimated,
      })
      // Refresh the KPI to get updated current_value, trend, alerts
      const refreshed = await getKpis(planId)
      setKpis(refreshed)
      void updated
      setRecordState(null)
      toast.success('Value recorded')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to record value')
    }
  }

  const doAcknowledge = async (alert: KPIAlert) => {
    try {
      const updated = await acknowledgeKpiAlert(alert.id)
      setKpis((prev) =>
        prev.map((k) => ({
          ...k,
          alerts: k.alerts.map((a) => (a.id === updated.id ? updated : a)),
        }))
      )
      toast.success('Alert acknowledged')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to acknowledge alert')
    }
  }

  const doResolve = async (alert: KPIAlert) => {
    try {
      const updated = await resolveKpiAlert(alert.id)
      setKpis((prev) =>
        prev.map((k) => ({
          ...k,
          alerts: k.alerts.map((a) => (a.id === updated.id ? updated : a)),
        }))
      )
      toast.success('Alert resolved')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to resolve alert')
    }
  }

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow">
      <div className="px-6 py-4 border-b border-lsc-border dark:border-earth-700 flex justify-between items-center">
        <h2 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Key Performance Indicators</h2>
        <button
          onClick={openAdd}
          className="flex items-center gap-2 px-3 py-1.5 bg-lsc-rose text-white rounded-xl text-sm hover:bg-lsc-rose"
        >
          <Plus className="h-4 w-4" /> Add KPI
        </button>
      </div>

      <div className="divide-y divide-lsc-border dark:divide-earth-700">
        {loading ? (
          <div className="p-8 text-center text-lsc-dark/70 dark:text-lsc-cream/70">Loading KPIs...</div>
        ) : loadError ? (
          <div className="p-8 text-center">
            <p className="text-sm text-status-danger-600 dark:text-status-danger-400 mb-3">{loadError}</p>
            <button
              onClick={load}
              className="px-3 py-1.5 text-sm bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream rounded-xl hover:bg-lsc-rose hover:text-white"
            >
              Retry
            </button>
          </div>
        ) : kpis.length === 0 ? (
          <div className="p-8 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
            No KPIs yet. Add your first performance indicator.
          </div>
        ) : (
          kpis.map((kpi) => {
            const alerts = activeAlerts(kpi)
            const recentValues = [...kpi.values]
              .sort((a, b) => (b.recorded_date ?? '').localeCompare(a.recorded_date ?? ''))
              .slice(0, 5)

            return (
              <div
                key={kpi.id}
                className={`p-4 ${!kpi.is_active ? 'opacity-60' : ''}`}
              >
                {/* Alerts */}
                {alerts.map((alert) => (
                  <div
                    key={alert.id}
                    className={`mb-3 px-3 py-2 rounded-lg border text-sm flex items-start gap-2 ${alertSeverityColors[alert.severity] ?? alertSeverityColors.info}`}
                  >
                    <AlertTriangle className="h-4 w-4 mt-0.5 flex-shrink-0" aria-hidden="true" />
                    <span className="flex-1">{alert.message}</span>
                    <div className="flex gap-1 flex-shrink-0">
                      <button
                        onClick={() => doAcknowledge(alert)}
                        className="text-xs px-2 py-0.5 rounded bg-white/50 dark:bg-black/20 hover:bg-white/80 dark:hover:bg-black/40"
                        aria-label="Acknowledge alert"
                      >
                        Ack
                      </button>
                      <button
                        onClick={() => doResolve(alert)}
                        className="text-xs px-2 py-0.5 rounded bg-white/50 dark:bg-black/20 hover:bg-white/80 dark:hover:bg-black/40"
                        aria-label="Resolve alert"
                      >
                        Resolve
                      </button>
                    </div>
                  </div>
                ))}

                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">{kpi.name}</h3>
                      {kpi.category && (
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${categoryColors[kpi.category] ?? 'bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream'}`}>
                          {kpi.category}
                        </span>
                      )}
                      {!kpi.is_active && (
                        <span className="px-2 py-0.5 rounded text-xs bg-lsc-cream dark:bg-lsc-brown text-lsc-dark/50 dark:text-lsc-cream/50">
                          Inactive
                        </span>
                      )}
                    </div>

                    {kpi.description && (
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 line-clamp-2 mb-2">
                        {kpi.description}
                      </p>
                    )}

                    {/* Current value + trend */}
                    <div className="flex items-baseline gap-3 mb-2">
                      <span className="text-2xl font-semibold text-lsc-dark dark:text-lsc-cream">
                        {formatValue(kpi.current_value ?? undefined, kpi.unit_of_measure ?? undefined)}
                      </span>
                      {kpi.trend_direction && (
                        <span className={varianceColor(kpi.variance_percentage)}>
                          <TrendIcon direction={kpi.trend_direction} />
                        </span>
                      )}
                      {kpi.variance_percentage && (
                        <span className={`text-sm ${varianceColor(kpi.variance_percentage)}`}>
                          {parseFloat(kpi.variance_percentage) >= 0 ? '+' : ''}{parseFloat(kpi.variance_percentage).toFixed(1)}% vs baseline
                        </span>
                      )}
                    </div>

                    <div className="flex gap-2 flex-wrap text-xs mb-2">
                      {kpi.target_value && (
                        <span className="px-2 py-0.5 bg-lsc-cream dark:bg-lsc-brown rounded text-lsc-dark dark:text-lsc-cream">
                          Target: {formatValue(kpi.target_value, kpi.unit_of_measure ?? undefined)}
                        </span>
                      )}
                      {kpi.frequency && (
                        <span className="px-2 py-0.5 bg-lsc-cream dark:bg-lsc-brown rounded text-lsc-dark dark:text-lsc-cream capitalize">
                          {kpi.frequency}
                        </span>
                      )}
                      {kpi.data_source && (
                        <span className="px-2 py-0.5 bg-lsc-cream dark:bg-lsc-brown rounded text-lsc-dark dark:text-lsc-cream">
                          {kpi.data_source}
                        </span>
                      )}
                    </div>

                    {/* Recent values sparkline (text chips) */}
                    {recentValues.length > 0 && (
                      <div className="flex gap-1 flex-wrap mb-2">
                        {recentValues.map((v) => (
                          <span
                            key={v.id}
                            className="px-2 py-0.5 text-xs bg-lsc-cream dark:bg-lsc-brown rounded text-lsc-dark/70 dark:text-lsc-cream/70"
                            title={v.notes ?? undefined}
                          >
                            {v.recorded_date ? new Date(v.recorded_date).toLocaleDateString() : '?'}: {formatValue(String(v.value), kpi.unit_of_measure ?? undefined)}
                            {v.is_estimated && ' ~'}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Record value inline form */}
                    {recordState?.kpiId === kpi.id && (
                      <div className="mt-3 p-3 bg-lsc-cream dark:bg-lsc-brown rounded-xl space-y-2">
                        <div className="flex gap-2 items-end">
                          <div className="flex-1">
                            <label className="block text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                              Value {kpi.unit_of_measure ? `(${kpi.unit_of_measure})` : ''}
                            </label>
                            <input
                              type="number"
                              step="any"
                              value={recordState.value}
                              onChange={(e) => setRecordState({ ...recordState, value: e.target.value })}
                              className="w-full px-3 py-1.5 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream text-sm"
                              autoFocus
                            />
                          </div>
                          <button
                            onClick={submitRecordValue}
                            disabled={!recordState.value}
                            className="px-3 py-1.5 bg-lsc-rose text-white rounded-xl text-sm disabled:opacity-50"
                          >
                            Save
                          </button>
                          <button
                            onClick={() => setRecordState(null)}
                            className="px-3 py-1.5 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-xl text-sm"
                          >
                            Cancel
                          </button>
                        </div>
                        <div>
                          <input
                            type="text"
                            value={recordState.notes}
                            onChange={(e) => setRecordState({ ...recordState, notes: e.target.value })}
                            placeholder="Notes (optional)"
                            className="w-full px-3 py-1.5 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream text-sm"
                          />
                        </div>
                        <label className="flex items-center gap-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={recordState.is_estimated}
                            onChange={(e) => setRecordState({ ...recordState, is_estimated: e.target.checked })}
                            className="h-3.5 w-3.5 rounded border-lsc-border"
                          />
                          Estimated value
                        </label>
                      </div>
                    )}
                  </div>

                  <div className="flex gap-1 flex-shrink-0">
                    <button
                      onClick={() =>
                        setRecordState(
                          recordState?.kpiId === kpi.id
                            ? null
                            : { kpiId: kpi.id, value: '', notes: '', is_estimated: false }
                        )
                      }
                      className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded"
                      title="Record value"
                      aria-label={`Record value for ${kpi.name}`}
                    >
                      <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                    </button>
                    <button
                      onClick={() => openEdit(kpi)}
                      className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded"
                      aria-label={`Edit KPI ${kpi.name}`}
                    >
                      <Edit2 className="h-4 w-4" aria-hidden="true" />
                    </button>
                    {isAdmin && (
                      <button
                        onClick={() => setDeleteConfirm({ id: kpi.id, name: kpi.name })}
                        className="p-2 text-status-danger-600 hover:bg-status-danger-100 dark:hover:bg-status-danger-900/30 rounded"
                        aria-label={`Delete KPI ${kpi.name}`}
                      >
                        <Trash2 className="h-4 w-4" aria-hidden="true" />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )
          })
        )}
      </div>

      {showModal && (
        <KPIModal
          editing={editing}
          setEditing={setEditing}
          onSave={saveKpi}
          onClose={() => setShowModal(false)}
        />
      )}

      <ConfirmDialog
        isOpen={!!deleteConfirm}
        title="Delete KPI?"
        message={`Are you sure you want to delete "${deleteConfirm?.name}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        confirmVariant="danger"
        onConfirm={() => { if (deleteConfirm) confirmDelete(deleteConfirm.id) }}
        onCancel={() => setDeleteConfirm(null)}
      />
    </div>
  )
}
