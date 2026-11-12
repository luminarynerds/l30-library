/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { getFocusTimeAnalytics, getFocusTimeBlocks } from '@/api/focus-time-api'
import {
  BarChart3,
  TrendingUp,
  Clock,
  Target,
  AlertCircle,
  CheckCircle2,
} from 'lucide-react'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useTranslation } from '@/i18n'

interface AnalyticsMetrics {
  totalBlocks: number
  completedBlocks: number
  cancelledBlocks: number
  overriddenBlocks: number
  totalHours: number
  completionRate: number
  interruptionRate: number
  avgDuration: number
}

const MetricCard: React.FC<{
  icon: React.ReactNode
  label: string
  value: string | number
  unit?: string
  trend?: number
  color?: 'success' | 'accent' | 'warning' | 'danger'
}> = ({ icon, label, value, unit = '', trend, color = 'accent' }) => {
  const bgColor = {
    success: 'bg-status-success-50 dark:bg-status-success-900/20 border-status-success-200 dark:border-status-success-800',
    accent: 'bg-earth-50 dark:bg-earth-800/20 border-lsc-border dark:border-earth-700',
    warning: 'bg-status-warning-50 dark:bg-status-warning-900/20 border-status-warning-200 dark:border-status-warning-800',
    danger: 'bg-status-danger-50 dark:bg-status-danger-900/20 border-status-danger-200 dark:border-status-danger-800',
  }[color]

  const textColor = {
    success: 'text-status-success-900 dark:text-status-success-200',
    accent: 'text-earth-900 dark:text-lsc-rose-light/80',
    warning: 'text-status-warning-900 dark:text-status-warning-200',
    danger: 'text-status-danger-900 dark:text-status-danger-200',
  }[color]

  const iconColor = {
    success: 'text-status-success-600',
    accent: 'text-lsc-rose dark:text-lsc-rose-light',
    warning: 'text-status-warning-600',
    danger: 'text-status-danger-600',
  }[color]

  return (
    <Card className={`${bgColor} border`}>
      <CardContent className="pt-4">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">{label}</p>
            <div className={`text-2xl font-bold ${textColor}`}>
              {value}
              {unit && <span className="text-sm ml-1">{unit}</span>}
            </div>
            {trend !== undefined && (
              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                {trend > 0 ? '↑' : '↓'} {Math.abs(trend)}% from last period
              </p>
            )}
          </div>
          <div className={`${iconColor} p-2`}>{icon}</div>
        </div>
      </CardContent>
    </Card>
  )
}

export const FocusTimeAnalyticsDashboard: React.FC = () => {
  const { t } = useTranslation()
  const [period, setPeriod] = useState('30') // days

  // Fetch analytics data
  const { data: analyticsData, isLoading: analyticsLoading } = useQuery({
    queryKey: ['focusTimeAnalytics', period],
    queryFn: () => {
      const now = new Date()
      const startDate = new Date(now.getTime() - parseInt(period) * 24 * 60 * 60 * 1000)
      return getFocusTimeAnalytics({
        start_date: startDate.toISOString(),
        end_date: now.toISOString(),
      })
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
  })

  // Fetch blocks for detailed metrics
  const { data: blocksData } = useQuery({
    queryKey: ['focusTimeBlocks', period],
    queryFn: () => getFocusTimeBlocks(),
    staleTime: 1000 * 60 * 5,
  })

  // Calculate additional metrics
  const calculateMetrics = (): AnalyticsMetrics => {
    const summary = analyticsData?.summary
    if (!summary) {
      return {
        totalBlocks: 0,
        completedBlocks: 0,
        cancelledBlocks: 0,
        overriddenBlocks: 0,
        totalHours: 0,
        completionRate: 0,
        interruptionRate: 0,
        avgDuration: 0,
      }
    }

    const total = summary.total_blocks || 1
    const interrupted = summary.overridden_blocks || 0
    const avgDuration = total > 0 ? summary.total_hours / total : 0

    return {
      totalBlocks: summary.total_blocks,
      completedBlocks: summary.completed_blocks,
      cancelledBlocks: summary.cancelled_blocks,
      overriddenBlocks: summary.overridden_blocks,
      totalHours: summary.total_hours,
      completionRate: summary.completion_rate,
      interruptionRate: total > 0 ? (interrupted / total) * 100 : 0,
      avgDuration: avgDuration,
    }
  }

  const metrics = calculateMetrics()

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-serif font-bold mb-2">Focus Time Analytics</h2>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('components.staff.focusTimeAnalyticsDashboard.trackYourDeepWorkPatterns')}</p>
      </div>

      {/* Period Selector */}
      <div className="flex gap-2">
        <span className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 py-2">Time Period:</span>
        <Select value={period} onValueChange={setPeriod}>
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="7">Last 7 Days</SelectItem>
            <SelectItem value="30">Last 30 Days</SelectItem>
            <SelectItem value="90">Last 90 Days</SelectItem>
            <SelectItem value="365">Last Year</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Key Metrics */}
      {analyticsLoading ? (
        <Card>
          <CardContent className="pt-6">
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-center">Loading analytics...</p>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MetricCard
              icon={<Target className="w-6 h-6" />}
              label="Total Blocks"
              value={metrics.totalBlocks}
              color="accent"
            />
            <MetricCard
              icon={<CheckCircle2 className="w-6 h-6" />}
              label="Completed"
              value={metrics.completedBlocks}
              color="success"
            />
            <MetricCard
              icon={<AlertCircle className="w-6 h-6" />}
              label="Interrupted"
              value={metrics.overriddenBlocks}
              color="warning"
            />
            <MetricCard
              icon={<Clock className="w-6 h-6" />}
              label="Total Hours"
              value={metrics.totalHours.toFixed(1)}
              unit="h"
              color="accent"
            />
          </div>

          {/* Success Rate */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="w-5 h-5" />
                Completion Rate
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <div className="flex justify-between mb-2">
                  <span className="text-sm font-semibold">Success Rate</span>
                  <span className="text-sm font-bold text-status-success-600">
                    {metrics.completionRate.toFixed(1)}%
                  </span>
                </div>
                <div className="w-full bg-earth-200 dark:bg-earth-600 rounded-full h-3">
                  <div
                    className="bg-status-success-600 h-3 rounded-full transition-all duration-300"
                    style={{ width: `${Math.min(metrics.completionRate, 100)}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between mb-2">
                  <span className="text-sm font-semibold">Interruption Rate</span>
                  <span className="text-sm font-bold text-status-warning-600">
                    {metrics.interruptionRate.toFixed(1)}%
                  </span>
                </div>
                <div className="w-full bg-earth-200 dark:bg-earth-600 rounded-full h-3">
                  <div
                    className="bg-status-warning-600 h-3 rounded-full transition-all duration-300"
                    style={{ width: `${Math.min(metrics.interruptionRate, 100)}%` }}
                  />
                </div>
              </div>

              <div className="pt-4 border-t">
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  {metrics.completionRate > 80
                    ? '✓ Great job protecting your focus time! You maintain high completion rates.'
                    : metrics.completionRate > 60
                      ? '✓ Good progress. Consider scheduling focus blocks at less-interrupted times.'
                      : '⚠ Your focus time is frequently interrupted. Consider longer advance notice or different times.'}
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Work Type Breakdown */}
          {blocksData?.blocks && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="w-5 h-5" />
                  Focus Work Breakdown
                </CardTitle>
              </CardHeader>
              <CardContent>
                {(() => {
                  const workTypeStats: Record<string, { count: number; hours: number }> = {}

                  blocksData.blocks.forEach((block) => {
                    const type = block.work_type || 'Other'
                    if (!workTypeStats[type]) {
                      workTypeStats[type] = { count: 0, hours: 0 }
                    }
                    workTypeStats[type].count++
                    const duration =
                      (new Date(block.end_time).getTime() -
                        new Date(block.start_time).getTime()) /
                      (1000 * 60 * 60)
                    workTypeStats[type].hours += duration
                  })

                  const types = Object.entries(workTypeStats)
                    .sort((a, b) => b[1].hours - a[1].hours)
                    .slice(0, 6)

                  if (types.length === 0) {
                    return <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('components.staff.focusTimeAnalyticsDashboard.noFocusBlocksYet')}</p>
                  }

                  const maxHours = Math.max(...types.map((t) => t[1].hours))

                  return (
                    <div className="space-y-3">
                      {types.map(([type, stats]) => (
                        <div key={type}>
                          <div className="flex justify-between mb-1">
                            <span className="text-sm font-semibold capitalize">
                              {type.replace(/_/g, ' ')}
                            </span>
                            <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                              {stats.count} blocks · {stats.hours.toFixed(1)}h
                            </span>
                          </div>
                          <div className="w-full bg-earth-200 dark:bg-earth-600 rounded-full h-2">
                            <div
                              className="bg-lsc-rose h-2 rounded-full"
                              style={{
                                width: `${(stats.hours / maxHours) * 100}%`,
                              }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  )
                })()}
              </CardContent>
            </Card>
          )}

          {/* Insights */}
          <Card>
            <CardHeader>
              <CardTitle>Insights & Recommendations</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-2">
                {metrics.completionRate > 80 && (
                  <div className="flex gap-3 p-3 bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-800 rounded">
                    <CheckCircle2 className="w-5 h-5 text-status-success-600 flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-status-success-900 dark:text-status-success-200">
                      <strong>Excellent protection:</strong> You've successfully completed{' '}
                      {metrics.completionRate.toFixed(0)}% of your focus blocks. Keep up this
                      pattern!
                    </p>
                  </div>
                )}

                {metrics.interruptionRate > 30 && (
                  <div className="flex gap-3 p-3 bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded">
                    <AlertCircle className="w-5 h-5 text-status-warning-600 flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-status-warning-900 dark:text-status-warning-200">
                      <strong>High interruption rate:</strong> {metrics.interruptionRate.toFixed(0)}
                      % of your blocks are interrupted. Consider scheduling during slower periods
                      or extending advance notice to managers.
                    </p>
                  </div>
                )}

                {metrics.avgDuration < 1 && (
                  <div className="flex gap-3 p-3 bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded">
                    <AlertCircle className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-earth-900 dark:text-lsc-rose-light/80">
                      <strong>Short blocks:</strong> Your average focus block is{' '}
                      {(metrics.avgDuration * 60).toFixed(0)} minutes. Consider scheduling longer
                      blocks (2+ hours) to build better momentum.
                    </p>
                  </div>
                )}

                {metrics.totalBlocks < 4 && (
                  <div className="flex gap-3 p-3 bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded">
                    <AlertCircle className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-earth-900 dark:text-lsc-rose-light/80">
                      <strong>Low volume:</strong> You're scheduling less than 1 block per week.
                      Consider using focus time more regularly for better workflow.
                    </p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
