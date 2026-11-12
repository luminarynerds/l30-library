/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { RefreshCw } from "lucide-react"
import { useTranslation } from "@/i18n"
import { SectionCard, AIStatCard } from "./ai-settings-primitives"
import type { UsageLogEntry, UsageSummary } from "./types"

interface AuditTabProps {
  usageLogs: UsageLogEntry[]
  usageSummary: UsageSummary | null
  onRefresh: () => void
}

export function AuditTab({ usageLogs, usageSummary, onRefresh }: AuditTabProps) {
  const { t } = useTranslation()

  return (
    <div className="space-y-6">
      {usageSummary && (
        <SectionCard>
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Last {usageSummary.period_days} Days Summary</h3>
          <div className="grid md:grid-cols-5 gap-3">
            <AIStatCard value={usageSummary.total_requests} label="Total Requests" color="default" />
            <AIStatCard value={usageSummary.successful} label="Successful" color="success" />
            <AIStatCard value={usageSummary.blocked} label="Blocked" color="warning" />
            <AIStatCard value={usageSummary.failed} label="Failed" color="danger" />
            <AIStatCard value={`${usageSummary.block_rate}%`} label="Block Rate" color="accent" />
          </div>
          {Object.keys(usageSummary.tool_usage).length > 0 && (
            <div className="mt-4">
              <p className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">Per-Tool Breakdown</p>
              <div className="grid md:grid-cols-3 gap-2">
                {Object.entries(usageSummary.tool_usage).map(([tid, data]) => (
                  <div key={tid} className="bg-lsc-cream dark:bg-earth-700 rounded-lg p-3 text-sm">
                    <p className="font-mono font-semibold text-lsc-dark dark:text-lsc-cream">{tid}</p>
                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{data.total} requests | {data.blocked} blocked | {data.tokens} tokens</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </SectionCard>
      )}

      <SectionCard>
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Recent AI Usage</h3>
          <button onClick={onRefresh} className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark flex items-center gap-1">
            <RefreshCw className="h-4 w-4" /> Refresh
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-lsc-border dark:border-earth-700 text-left">
                <th className="pb-2 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Time</th>
                <th className="pb-2 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Tool</th>
                <th className="pb-2 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Model</th>
                <th className="pb-2 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Status</th>
                <th className="pb-2 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Speed</th>
                <th className="pb-2 font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Prompt</th>
              </tr>
            </thead>
            <tbody>
              {usageLogs.map((log) => (
                <tr key={log.id} className="border-b border-lsc-border/50 dark:border-earth-700/50">
                  <td className="py-2 text-lsc-dark/70 dark:text-lsc-cream/70 whitespace-nowrap">
                    {log.created_at ? new Date(log.created_at).toLocaleString() : "—"}
                  </td>
                  <td className="py-2 font-mono text-lsc-dark dark:text-lsc-cream">{log.tool_id || "—"}</td>
                  <td className="py-2 font-mono text-lsc-dark/70 dark:text-lsc-cream/70">{log.model_used || "—"}</td>
                  <td className="py-2">
                    {log.was_blocked ? (
                      <span className="px-2 py-0.5 rounded-full text-xs bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-300">Blocked</span>
                    ) : log.success ? (
                      <span className="px-2 py-0.5 rounded-full text-xs bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300">OK</span>
                    ) : (
                      <span className="px-2 py-0.5 rounded-full text-xs bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300">Error</span>
                    )}
                  </td>
                  <td className="py-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                    {log.generation_time_ms ? `${(log.generation_time_ms / 1000).toFixed(1)}s` : "—"}
                  </td>
                  <td className="py-2 text-lsc-dark/70 dark:text-lsc-cream/60 max-w-xs truncate" title={log.prompt_preview || "—"}>
                    {log.prompt_preview || "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {usageLogs.length === 0 && (
            <p className="text-center text-lsc-dark/70 dark:text-lsc-cream/60 py-8">{t('admin.adminAISettings.noAiUsageLoggedYet')}</p>
          )}
        </div>
      </SectionCard>
    </div>
  )
}
