/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { AlertTriangle, CheckCircle, Clock, DollarSign, RefreshCw } from 'lucide-react'
import { StatCard, StatGrid, StatusBadge } from '@/components/admin'
import type { SubscriptionDashboard } from '../../api/databases-api'
import { parseDate } from '@/utils/format-utils'

interface DashboardTabProps {
  dashboard: SubscriptionDashboard | undefined
  isLoading: boolean
}

export function DashboardTab({ dashboard, isLoading }: DashboardTabProps): React.ReactElement {
  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <RefreshCw
          className="h-8 w-8 text-lsc-rose dark:text-lsc-rose-light motion-safe:animate-spin"
          aria-hidden="true"
        />
      </div>
    )
  }

  if (!dashboard) {
    return (
      <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
        Unable to load dashboard data.
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <StatGrid columns={4}>
        <StatCard
          title="Active Subscriptions"
          value={dashboard.total_active}
          icon={CheckCircle}
          color="success"
        />
        <StatCard
          title="Expiring Soon"
          value={dashboard.total_expiring_soon}
          icon={AlertTriangle}
          color="amber"
        />
        <StatCard title="Expired" value={dashboard.total_expired} icon={Clock} color="danger" />
        <StatCard
          title="Total Annual Cost"
          value={`$${parseFloat(dashboard.total_annual_cost).toLocaleString()}`}
          icon={DollarSign}
          color="accent"
        />
      </StatGrid>

      {dashboard.expiring_alerts.length > 0 && (
        <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-lg p-6">
          <h3 className="font-serif text-lg font-semibold text-status-warning-800 dark:text-status-warning-200 flex items-center gap-2 mb-4">
            <AlertTriangle className="h-5 w-5" aria-hidden="true" />
            Subscriptions Requiring Attention ({dashboard.expiring_alerts.length})
          </h3>
          <div className="space-y-3">
            {dashboard.expiring_alerts.map((alert) => (
              <div
                key={alert.id}
                className="flex items-center justify-between bg-lsc-white dark:bg-earth-800 rounded-lg p-4 border border-status-warning-100 dark:border-status-warning-900"
              >
                <div>
                  <h4 className="font-medium text-lsc-dark dark:text-lsc-cream">{alert.name}</h4>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    {alert.vendor_name && `${alert.vendor_name} • `}
                    Expires: {parseDate(alert.subscription_end)?.toLocaleDateString() ?? '-'}
                  </p>
                </div>
                <div className="text-right">
                  <StatusBadge
                    label={`${alert.days_until_expiry} days left`}
                    tone={
                      alert.days_until_expiry <= 7
                        ? 'danger'
                        : alert.days_until_expiry <= 30
                          ? 'warning'
                          : 'neutral'
                    }
                    size="sm"
                  />
                  {alert.annual_cost && (
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                      ${parseFloat(alert.annual_cost).toLocaleString()}/year
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
