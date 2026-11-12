/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import type React from 'react'

export function StatCard({ label, value, icon: Icon, sublabel, color }: {
  label: string; value: string | number; icon: React.ElementType; sublabel?: string; color?: string
}) {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{label}</p>
          <p className={`text-2xl font-bold mt-1 ${color || 'text-lsc-dark dark:text-lsc-cream'}`}>{value}</p>
          {sublabel && <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">{sublabel}</p>}
        </div>
        <div className="w-10 h-10 rounded-xl bg-lsc-cream dark:bg-lsc-brown flex items-center justify-center flex-shrink-0">
          <Icon className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
        </div>
      </div>
    </div>
  )
}

export function ProgressBar({ value, max, label }: { value: number; max: number; label: string }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0
  const color = pct >= 100 ? 'bg-status-success-500' : pct >= 50 ? 'bg-lsc-rose' : 'bg-status-warning-500'
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{label}</span>
        <span className="font-medium text-lsc-dark dark:text-lsc-cream">{value.toLocaleString()} / {max.toLocaleString()}</span>
      </div>
      <div className="w-full h-2.5 bg-earth-200 dark:bg-earth-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-500 ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">{pct.toFixed(1)}% ready</p>
    </div>
  )
}

export function BucketBadge({ bucket }: { bucket: string }) {
  const styles: Record<string, string> = {
    approved: 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300',
    review: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300',
    rejected: 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-300',
  }
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${styles[bucket] || 'bg-lsc-cream text-lsc-dark'}`}>
      {bucket}
    </span>
  )
}

export function ScoreBar({ score }: { score: number }) {
  const color = score >= 80 ? 'bg-status-success-500' : score >= 40 ? 'bg-status-warning-500' : 'bg-status-danger-500'
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 bg-earth-200 dark:bg-earth-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-xs font-medium text-lsc-dark dark:text-lsc-cream">{score}</span>
    </div>
  )
}
