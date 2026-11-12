/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { usePanicAlert } from '../contexts/PanicAlertContext'
import {
  Bell,
  AlertCircle,
  CheckCircle,
  Clock,
  Loader2,
  RefreshCw,
  MapPin,
  AlertTriangle,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { acknowledgePanicAlert, resolvePanicAlert } from '../api/panic-alert-api'
import { useTranslation} from '@/i18n'
import { AdminShell } from '../components/shells/AdminShell'
import { PanicAlertSoundSettings } from '../components/PanicAlertSoundSettings'
import PageContainer from '@/components/layout/PageContainer'

export default function StaffPanicAlertsPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user } = useAuth()
  const { activeAlerts, activeAlertsLoading, loadActiveAlerts } = usePanicAlert()

  const [resolving, setResolving] = useState<Record<number, boolean>>({})
  const [acknowledging, setAcknowledging] = useState<Record<number, boolean>>({})
  const [resolutionNotes, setResolutionNotes] = useState<Record<number, string>>({})
  const [expandedAlert, setExpandedAlert] = useState<number | null>(null)

  // Load alerts on mount and set up polling
  useEffect(() => {
    void loadActiveAlerts()

    // Refresh every 10 seconds
    const interval = setInterval(() => {
      void loadActiveAlerts()
    }, 10000)

    return () => clearInterval(interval)
  }, [loadActiveAlerts])

  // Check if user has permission to manage alerts
  const canManageAlerts =
    user && ['staff', 'admin', 'super_admin'].includes(user.role)

  if (!canManageAlerts) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-cream-50 dark:bg-earth-900">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 text-status-danger-500 mx-auto mb-4" />
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">Staff-Only Area</h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('staffPanicAlerts.youDoNotHavePermission')}</p>
        </div>
      </div>
    )
  }

  const handleAcknowledge = async (alertId: number) => {
    setAcknowledging((prev) => ({ ...prev, [alertId]: true }))
    try {
      await acknowledgePanicAlert(alertId)
      toast.success(t('toast.adminLinkHealth.alertAcknowledged'))
      await loadActiveAlerts()
    } catch (error: unknown) {
      toast.error(t('staffPanicAlerts.failedToAcknowledgeAlert'))
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    } finally {
      setAcknowledging((prev) => ({ ...prev, [alertId]: false }))
    }
  }

  const handleResolve = async (alertId: number) => {
    if (!resolutionNotes[alertId]?.trim()) {
      toast.error(t('staffPanicAlerts.pleaseEnterResolutionNotes'))
      return
    }

    setResolving((prev) => ({ ...prev, [alertId]: true }))
    try {
      await resolvePanicAlert(alertId, resolutionNotes[alertId])
      toast.success(t('toast.adminLinkHealth.alertResolved'))
      setResolutionNotes((prev) => {
        const updated = { ...prev }
        delete updated[alertId]
        return updated
      })
      await loadActiveAlerts()
    } catch (error: unknown) {
      toast.error(t('staffPanicAlerts.failedToResolveAlert'))
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    } finally {
      setResolving((prev) => ({ ...prev, [alertId]: false }))
    }
  }

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffSecs = Math.floor(diffMs / 1000)

    if (diffSecs < 60) return `${diffSecs}s ago`
    if (diffMins < 60) return `${diffMins}m ago`
    return date.toLocaleTimeString()
  }

  const getSourceLabel = (source: string) => {
    const labels: Record<string, string> = {
      keyboard_shortcut: 'Keyboard (Ctrl+Shift+H)',
      hidden_ui_button: 'Button',
      mobile_gesture: 'Mobile Shake',
      physical_button: 'Physical Button',
    }
    return labels[source] || source
  }

  return (

    <AdminShell title="Panic Alerts">    <div className="min-h-screen bg-cream-50 dark:bg-earth-900">
      <PageContainer className="py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <Bell className="w-8 h-8 text-status-danger-600" />
              <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                Panic Alerts Management
              </h1>
            </div>
            <button
              onClick={() => void loadActiveAlerts()}
              disabled={activeAlertsLoading}
              className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-earth-400 text-white rounded-lg transition-colors"
            >
              {activeAlertsLoading ? (
                <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
              Refresh
            </button>
          </div>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            Monitor and respond to staff panic alerts. Silent cry for help that needs
            your attention.
          </p>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 font-medium">Active Alerts</p>
                <p className="text-3xl font-bold text-status-danger-600">
                  {activeAlerts.length}
                </p>
              </div>
              <AlertCircle className="w-10 h-10 text-status-danger-500 opacity-20" />
            </div>
          </div>

          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 font-medium">Acknowledged</p>
                <p className="text-3xl font-bold text-status-warning-600">
                  {activeAlerts.filter((a) => a.status === 'acknowledged').length}
                </p>
              </div>
              <Clock className="w-10 h-10 text-status-warning-500 opacity-20" />
            </div>
          </div>

          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 font-medium">Last Updated</p>
                <p className="text-sm font-mono text-lsc-dark/70 dark:text-lsc-cream/70">
                  {new Date().toLocaleTimeString()}
                </p>
              </div>
              <Clock className="w-10 h-10 text-earth-600 opacity-20" />
            </div>
          </div>
        </div>

        {/* Notification preferences */}
        <div className="mb-8">
          <PanicAlertSoundSettings />
        </div>

        {/* Alerts List */}
        <div className="space-y-4">
          {activeAlertsLoading && activeAlerts.length === 0 ? (
            <div className="text-center py-12">
              <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-dark/70 dark:text-lsc-cream/70 mx-auto mb-4" />
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">Loading active alerts...</p>
            </div>
          ) : activeAlerts.length === 0 ? (
            <div className="text-center py-12 bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700">
              <CheckCircle className="w-12 h-12 text-status-success-500 mx-auto mb-4" />
              <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
                No Active Alerts
              </h3>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
                All is well. No staff members need assistance right now.
              </p>
            </div>
          ) : (
            activeAlerts.map((alert) => (
              <div
                key={alert.id}
                className={`rounded-lg border p-6 transition-all ${
                  expandedAlert === alert.id
                    ? 'bg-lsc-white dark:bg-earth-800 border-lsc-rose'
                    : 'bg-lsc-white dark:bg-earth-800 border-lsc-border hover:border-lsc-border dark:border-earth-700'
                }`}
              >
                {/* Alert Header */}
                <div
                  onClick={() =>
                    setExpandedAlert(expandedAlert === alert.id ? null : alert.id)
                  } tabIndex={0} role="button" onKeyDown={(e: React.KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); (() =>
                    setExpandedAlert(expandedAlert === alert.id ? null : alert.id))(); } }}
                  className="cursor-pointer"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-start gap-4 flex-1">
                      {/* Status Badge */}
                      <div className="mt-1" aria-hidden="true">
                        {alert.status === 'active' && (
                          <div className="w-3 h-3 rounded-full bg-status-danger-500 motion-safe:animate-pulse" />
                        )}
                        {alert.status === 'acknowledged' && (
                          <div className="w-3 h-3 rounded-full bg-status-warning-500" />
                        )}
                      </div>

                      {/* Main Info */}
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <h3 className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream">
                            Alert #{alert.id}
                          </h3>
                          <span className={`px-2 py-1 text-xs font-semibold rounded-full capitalize ${
                            alert.status === "active"
                              ? "bg-status-danger-200 text-status-danger-800 dark:bg-status-danger-900/40 dark:text-status-danger-300"
                              : "bg-status-warning-200 text-status-warning-800 dark:bg-status-warning-900/40 dark:text-status-warning-300"
                          }`}>
                            {alert.status}
                          </span>
                          <span className="px-2 py-1 text-xs font-medium rounded bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70">
                            {getSourceLabel(alert.activation_source)}
                          </span>
                        </div>

                        <div className="flex flex-wrap gap-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                          <div className="flex items-center gap-1">
                            <Clock className="w-4 h-4" />
                            <span>{formatTime(alert.created_at)}</span>
                          </div>
                          {alert.branch_id && (
                            <div className="flex items-center gap-1">
                              <MapPin className="w-4 h-4" />
                              <span>Branch {alert.branch_id}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Expand Indicator */}
                    <div className="text-lsc-dark/70 dark:text-lsc-cream/70">
                      {expandedAlert === alert.id ? '▼' : '▶'}
                    </div>
                  </div>
                </div>

                {/* Expanded Details */}
                {expandedAlert === alert.id && (
                  <div className="mt-6 space-y-4 border-t border-lsc-border dark:border-earth-700 pt-4">
                    {/* Situation Notes */}
                    {alert.triggered_by_user_id && (
                      <div>
                        <p className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                          Triggered By
                        </p>
                        <p className="text-lsc-dark dark:text-lsc-cream">Staff Member ID: {alert.triggered_by_user_id}</p>
                      </div>
                    )}

                    {/* Action Buttons */}
                    <div className="flex gap-2 pt-4">
                      {alert.status === 'active' && (
                        <button
                          onClick={() => void handleAcknowledge(alert.id)}
                          disabled={acknowledging[alert.id]}
                          className="flex items-center gap-2 px-4 py-2 bg-status-warning-100 hover:bg-status-warning-200 disabled:bg-earth-200 dark:bg-earth-600 text-status-warning-900 dark:text-status-warning-200 rounded-lg transition-colors font-medium"
                        >
                          {acknowledging[alert.id] ? (
                            <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                          ) : (
                            <Clock className="w-4 h-4" />
                          )}
                          I'm on the way
                        </button>
                      )}

                      {alert.status !== 'resolved' && (
                        <div className="flex-1 flex gap-2">
                          <input
                            type="text"
                            placeholder={t('staffPanicAlerts.howWasThisResolved')}
                            value={resolutionNotes[alert.id] || ''}
                            onChange={(e) =>
                              setResolutionNotes((prev) => ({
                                ...prev,
                                [alert.id]: e.target.value,
                              }))
                            }
                            className="flex-1 px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg text-sm bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream placeholder:text-lsc-dark/50 dark:placeholder:text-lsc-cream/50 focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                          />
                          <button
                            onClick={() => void handleResolve(alert.id)}
                            disabled={resolving[alert.id]}
                            className="flex items-center gap-2 px-4 py-2 bg-status-success-100 hover:bg-status-success-200 disabled:bg-earth-200 dark:bg-earth-600 text-status-success-900 dark:text-status-success-200 rounded-lg transition-colors font-medium"
                          >
                            {resolving[alert.id] ? (
                              <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                            ) : (
                              <CheckCircle className="w-4 h-4" />
                            )}
                            Resolved
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </PageContainer>
    </div>
  </AdminShell>
  )
}
