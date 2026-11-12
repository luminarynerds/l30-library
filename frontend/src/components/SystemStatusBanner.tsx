/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * SystemStatusBanner - Transparent real-time system health display
 *
 * Shows honest, clear status information to both staff and patrons.
 * Automatically polls for status updates and displays non-intrusive
 * banners when issues are detected. Honesty about tech problems
 * reduces stress for everyone.
 */
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  AlertTriangle,
  CheckCircle,
  Clock,
  Info,
  WifiOff,
  X,
  ChevronDown,
  ChevronUp,
  type LucideIcon,
} from 'lucide-react'
import { getHealthSummary, getSystemStatus, getRecentRecoveries } from '@/api/system-status-api'
import type { HealthLevel } from '@/api/system-status-api'
import { t, useTranslation } from '@/i18n'

// Polling interval: 30 seconds when there are issues, 2 minutes when healthy
const HEALTHY_POLL_INTERVAL = 120_000
const ISSUE_POLL_INTERVAL = 30_000

export default function SystemStatusBanner() {
  const { language } = useTranslation()
  const [dismissed, setDismissed] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const [showRecovery, setShowRecovery] = useState(false)

  // Fetch health summary (lightweight, public)
  const { data: health } = useQuery({
    queryKey: ['system-health-summary'],
    queryFn: getHealthSummary,
    refetchInterval: (query) => {
      const h = query.state.data?.health
      return h && h !== 'healthy' ? ISSUE_POLL_INTERVAL : HEALTHY_POLL_INTERVAL
    },
    retry: 1,
    staleTime: 15_000,
  })

  // Fetch full status only when there are issues
  const hasIssues = health && health.health !== 'healthy'
  const { data: fullStatus } = useQuery({
    queryKey: ['system-status-full'],
    queryFn: getSystemStatus,
    enabled: !!hasIssues,
    refetchInterval: ISSUE_POLL_INTERVAL,
    retry: 1,
  })

  // Fetch recent recoveries to show "we're back" message
  const { data: recoveries } = useQuery({
    queryKey: ['system-recent-recoveries'],
    queryFn: () => getRecentRecoveries(2), // Last 2 hours
    refetchInterval: HEALTHY_POLL_INTERVAL,
    retry: 1,
  })

  // Show recovery banner briefly after issues resolve
  useEffect(() => {
    if (recoveries?.recoveries && recoveries.recoveries.length > 0 && !hasIssues) {
      setShowRecovery(true)
      setDismissed(false)
      const timer = setTimeout(() => setShowRecovery(false), 60_000) // Auto-hide after 1 min
      return () => clearTimeout(timer)
    }
    setShowRecovery(false)
  }, [recoveries, hasIssues])

  // Reset dismissed state when status changes
  useEffect(() => {
    if (hasIssues) {
      setDismissed(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [health?.health])

  // Don't show anything if healthy and no recent recoveries
  if (!hasIssues && !showRecovery) {
    return null
  }

  // Don't show if user dismissed
  if (dismissed) {
    return null
  }

  // Recovery banner: "We're back!"
  if (showRecovery && !hasIssues) {
    const latest = recoveries?.recoveries?.[0]
    return (
      <div
        className="bg-status-success-50 dark:bg-status-success-900/20 border-b border-status-success-200 dark:border-status-success-800 px-4 py-2"
        role="status"
        aria-live="polite"
      >
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2 text-status-success-800 dark:text-status-success-300 text-sm">
            <CheckCircle className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
            <span className="font-medium">We're back!</span>
            <span className="text-status-success-700 dark:text-status-success-300">
              {latest
                ? `"${latest.title}" has been resolved${
                    latest.duration_minutes
                      ? ` (took ${latest.duration_minutes} min)`
                      : ''
                  }.`
                : 'All systems are back to normal.'}
            </span>
          </div>
          <button
            onClick={() => setDismissed(true)}
            className="text-status-success-600 hover:text-status-success-800 dark:text-status-success-300 p-1"
            aria-label={t('aria.systemStatusBanner.dismissRecoveryNotification')}
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>
    )
  }

  // Issue banner
  const bannerConfig = getBannerConfig(health?.health || 'healthy')

  return (
    <div
      className={`${bannerConfig.bg} border-b ${bannerConfig.border} px-4 py-2`}
      role="alert"
      aria-live="assertive"
    >
      <div className="max-w-7xl mx-auto">
        {/* Main status line */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm">
            <bannerConfig.icon
              className={`w-4 h-4 flex-shrink-0 ${bannerConfig.iconColor}`}
              aria-hidden="true"
            />
            <span className={`font-medium ${bannerConfig.textColor}`}>
              {bannerConfig.label}
            </span>
            <span className={bannerConfig.subtextColor}>
              {health?.message}
            </span>
            {fullStatus?.active_issues && fullStatus.active_issues.length > 0 && (
              <button
                onClick={() => setExpanded(!expanded)}
                className={`ml-2 ${bannerConfig.subtextColor} hover:underline flex items-center gap-1`}
                aria-expanded={expanded}
              >
                {expanded ? (
                  <>Less <ChevronUp className="w-3 h-3" /></>
                ) : (
                  <>Details <ChevronDown className="w-3 h-3" /></>
                )}
              </button>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Link
              to="/system-status"
              className={`text-xs ${bannerConfig.subtextColor} hover:underline`}
            >
              Status page
            </Link>
            <button
              onClick={() => setDismissed(true)}
              className={`${bannerConfig.subtextColor} hover:${bannerConfig.textColor} p-1`}
              aria-label={t('aria.systemStatusBanner.dismissStatusNotification')}
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Expanded details */}
        {expanded && fullStatus?.active_issues && (
          <div className="mt-2 space-y-2">
            {fullStatus.active_issues.map((issue) => (
              <div
                key={issue.id}
                className={`text-sm ${bannerConfig.subtextColor} pl-6`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <span className="font-medium">{issue.title}</span>
                    {issue.patron_message && (
                      <p className="mt-0.5">{issue.patron_message}</p>
                    )}
                  </div>
                  {issue.estimated_fix_time && (
                    <div className="flex items-center gap-1 text-xs flex-shrink-0 ml-4">
                      <Clock className="w-3 h-3" aria-hidden="true" />
                      <span>
                        Est. fix: {new Date(issue.estimated_fix_time).toLocaleTimeString(language, {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                    </div>
                  )}
                </div>
                {issue.degraded_features && issue.degraded_features.length > 0 && (
                  <p className="text-xs mt-1">
                    Affected: {issue.degraded_features.join(', ')}
                  </p>
                )}
              </div>
            ))}
            {fullStatus.offline_mode_recommended && (
              <p className={`text-xs ${bannerConfig.textColor} pl-6 font-medium`}>
                Staff can help with paper forms while we work on this.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Banner configuration by health level
// ---------------------------------------------------------------------------

interface BannerConfig {
  bg: string
  border: string
  icon: LucideIcon
  iconColor: string
  textColor: string
  subtextColor: string
  label: string
}

function getBannerConfig(health: HealthLevel): BannerConfig {
  switch (health) {
    case 'outage':
      return {
        bg: 'bg-status-danger-50 dark:bg-status-danger-900/20',
        border: 'border-status-danger-200 dark:border-status-danger-800',
        icon: WifiOff,
        iconColor: 'text-status-danger-600',
        textColor: 'text-status-danger-800 dark:text-status-danger-300',
        subtextColor: 'text-status-danger-700 dark:text-status-danger-300',
        label: 'Service Disruption',
      }
    case 'slow':
      return {
        bg: 'bg-status-warning-50 dark:bg-status-warning-900/20',
        border: 'border-status-warning-200 dark:border-status-warning-800',
        icon: Clock,
        iconColor: 'text-status-warning-600',
        textColor: 'text-status-warning-800 dark:text-status-warning-300',
        subtextColor: 'text-status-warning-700 dark:text-status-warning-300',
        label: 'Running Slow',
      }
    case 'degraded':
      return {
        bg: 'bg-status-warning-50 dark:bg-status-warning-900/20',
        border: 'border-status-warning-200 dark:border-status-warning-800',
        icon: AlertTriangle,
        iconColor: 'text-status-warning-600',
        textColor: 'text-status-warning-800 dark:text-status-warning-300',
        subtextColor: 'text-status-warning-700 dark:text-status-warning-300',
        label: 'Degraded Performance',
      }
    default:
      return {
        bg: 'bg-earth-50 dark:bg-earth-800/20',
        border: 'border-lsc-border dark:border-earth-700',
        icon: Info,
        iconColor: 'text-lsc-rose dark:text-lsc-rose-light',
        textColor: 'text-earth-800 dark:text-lsc-rose-light',
        subtextColor: 'text-lsc-rose dark:text-lsc-rose-light',
        label: 'System Notice',
      }
  }
}
