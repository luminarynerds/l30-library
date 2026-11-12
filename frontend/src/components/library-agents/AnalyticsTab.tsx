/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { BarChart2, MessageCircle, ThumbsUp, TrendingUp, BookOpen, Users, Bot } from 'lucide-react'
import type { AgentStats } from '../../api/library-agents-api'

function StatCard({
  label,
  value,
  icon: Icon,
  sublabel,
}: {
  label: string
  value: string | number
  icon: React.ElementType
  sublabel?: string
}) {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{label}</p>
          <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream mt-1">{value}</p>
          {sublabel && (
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">{sublabel}</p>
          )}
        </div>
        <div className="w-10 h-10 rounded-xl bg-lsc-cream dark:bg-lsc-brown flex items-center justify-center flex-shrink-0">
          <Icon className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
        </div>
      </div>
    </div>
  )
}

export function AnalyticsTab({ stats, isLoading }: { stats: AgentStats | null; isLoading: boolean }) {
  if (isLoading) {
    return (
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {[1, 2, 3, 4, 5, 6].map(i => (
          <div key={i} className="h-28 bg-lsc-cream dark:bg-earth-800 rounded-xl motion-safe:animate-pulse" aria-hidden="true" />
        ))}
      </div>
    )
  }

  if (!stats) {
    return (
      <div className="text-center py-10 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
        <BarChart2 className="w-12 h-12 mx-auto mb-3 opacity-40" aria-hidden="true" />
        Unable to load analytics.
      </div>
    )
  }

  const helpRate = stats.avg_helpfulness_rate * 100

  return (
    <div className="space-y-6">
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <StatCard label="Total Agents" value={stats.total_agents} icon={Bot} sublabel={`${stats.active_agents} active`} />
        <StatCard label="Total Conversations" value={stats.total_conversations.toLocaleString()} icon={MessageCircle} />
        <StatCard label="Feedback Received" value={stats.total_feedback.toLocaleString()} icon={ThumbsUp} />
        <StatCard
          label="Avg Helpfulness Rate"
          value={`${helpRate.toFixed(1)}%`}
          icon={TrendingUp}
          sublabel={stats.total_feedback > 0 ? `Based on ${stats.total_feedback} ratings` : 'No feedback yet'}
        />
        <StatCard label="Knowledge Base Entries" value={stats.knowledge_base_entries.toLocaleString()} icon={BookOpen} />
        <StatCard label="Active Agents" value={stats.active_agents} icon={Users} />
      </div>

      {stats.total_feedback > 0 && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
            Overall Helpfulness
          </h3>
          <div className="flex items-center gap-3">
            <ThumbsUp className="w-4 h-4 text-status-success-600 flex-shrink-0" aria-hidden="true" />
            <div className="flex-1">
              <div className="h-3 bg-lsc-cream dark:bg-earth-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-status-success-500 rounded-full transition-all"
                  style={{ width: `${Math.min(helpRate, 100)}%` }}
                  role="progressbar"
                  aria-valuenow={Math.round(helpRate)}
                  aria-valuemin={0}
                  aria-valuemax={100}
                />
              </div>
            </div>
            <span className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream w-12 text-right">
              {helpRate.toFixed(0)}%
            </span>
          </div>
          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
            {stats.total_feedback} total ratings across all conversations
          </p>
        </div>
      )}

      <div className="bg-lsc-cream dark:bg-lsc-dark/20 border border-lsc-border dark:border-earth-700 rounded-xl p-5">
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          <strong className="text-lsc-dark dark:text-lsc-cream">Note:</strong> Per-agent analytics (conversation trends, top intents) are available via the API at{' '}
          <code className="text-xs bg-lsc-cream dark:bg-earth-700 px-1 py-0.5 rounded">/library-agents/admin/{'{agent_id}'}/analytics</code>.
          Extended reporting dashboards are planned for a future release.
        </p>
      </div>
    </div>
  )
}
