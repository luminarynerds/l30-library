/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Radio, Tag, Package, AlertTriangle } from "lucide-react"
import type { DashboardStats } from "./staff-rfid-types"

interface Props {
  dashboardStats: DashboardStats
}

export function DashboardTab({ dashboardStats }: Props) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-lsc-cream dark:bg-lsc-brown rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-lsc-rose/10 rounded-lg"><Radio className="w-5 h-5 text-lsc-rose" /></div>
            <div>
              <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{dashboardStats.total_readers}</p>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Readers</p>
            </div>
          </div>
          <div className="mt-2 flex gap-2 text-xs">
            <span className="text-status-success-600">{dashboardStats.readers_online} online</span>
            <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{dashboardStats.readers_offline} offline</span>
            {dashboardStats.readers_error > 0 && <span className="text-status-danger-600">{dashboardStats.readers_error} error</span>}
          </div>
        </div>
        <div className="bg-lsc-cream dark:bg-lsc-brown rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-earth-500/10 rounded-lg"><Tag className="w-5 h-5 text-earth-600" /></div>
            <div>
              <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{dashboardStats.active_tags}</p>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Active Tags</p>
            </div>
          </div>
          <p className="mt-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{dashboardStats.total_tags} total registered</p>
        </div>
        <div className="bg-lsc-cream dark:bg-lsc-brown rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-status-success-500/10 rounded-lg"><Package className="w-5 h-5 text-status-success-500" /></div>
            <div>
              <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{dashboardStats.items_processed_today}</p>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Items Today</p>
            </div>
          </div>
          <p className="mt-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{dashboardStats.total_sessions_today} sessions</p>
        </div>
        <div className="bg-lsc-cream dark:bg-lsc-brown rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-status-danger-500/10 rounded-lg"><AlertTriangle className="w-5 h-5 text-status-danger-500" /></div>
            <div>
              <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{dashboardStats.unresolved_alerts}</p>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Open Alerts</p>
            </div>
          </div>
          <p className="mt-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{dashboardStats.security_alerts_today} today</p>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div>
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3">Recent Sessions</h3>
          {dashboardStats.recent_sessions.length === 0 ? (
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">No recent sessions</p>
          ) : (
            <div className="space-y-2">
              {dashboardStats.recent_sessions.slice(0, 5).map((session) => (
                <div key={session.id} className="flex items-center justify-between p-3 bg-lsc-cream/50 dark:bg-lsc-brown/50 rounded-lg">
                  <div>
                    <p className="font-medium text-sm text-lsc-dark dark:text-lsc-cream">{session.session_type.replace(/_/g, " ")}</p>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{session.reader_name} • {session.operator_name}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">{session.tags_processed} items</p>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{new Date(session.started_at).toLocaleTimeString()}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
        <div>
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3">Open Security Alerts</h3>
          {dashboardStats.recent_alerts.length === 0 ? (
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">No open alerts</p>
          ) : (
            <div className="space-y-2">
              {dashboardStats.recent_alerts.slice(0, 5).map((alert) => (
                <div key={alert.id} className="flex items-center justify-between p-3 bg-status-danger-50 dark:bg-status-danger-900/20 rounded-lg">
                  <div>
                    <p className="font-medium text-sm text-status-danger-700 dark:text-status-danger-300">{alert.alert_type.replace(/_/g, " ")}</p>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{alert.item_title || alert.tag_id || "Unknown"}</p>
                  </div>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{alert.reader_location}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
