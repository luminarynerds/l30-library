/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Journey Analytics Dashboard
 *
 * Real-time analytics dashboard for patron journeys.
 * Displays funnel metrics, drop-off analysis, and segmentation data.
 *
 * Displays 5 patron journeys:
 * - Search→Hold
 * - Register
 * - Renewal
 * - Account Self-Service
 * - Staff Check-in
 */

import React, { useState, useEffect, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/Button'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { API_BASE } from '@/api/types';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import toast from 'react-hot-toast'
import {
  Activity,
  AlertTriangle,
  RefreshCw,
} from 'lucide-react'
import { fetchApi } from '@/lib/api-client'
import { clsx as cn } from '@/utils/helpers'
import { AdminShell } from '../components/shells/AdminShell'
import { t } from '@/i18n'

// Journey types
const JOURNEYS = {
  search_to_hold: 'Search→Hold',
  register: 'Register',
  renewal: 'Renewal',
  account_self_service: 'Account Self-Service',
  staff_checkin: 'Staff Check-in',
}

type JourneyType = keyof typeof JOURNEYS

interface FunnelStage {
  stage_name: string
  event_count: number
  unique_sessions: number
  completion_rate: number
  avg_time_to_stage_ms: number
  median_time_to_stage_ms: number
  p95_time_to_stage_ms: number
  error_count: number
  error_rate: number
}

interface JourneyFunnel {
  journey_type: string
  segment_key?: string
  total_sessions: number
  completed_sessions: number
  overall_completion_rate: number
  avg_time_to_completion_ms: number
  stages: FunnelStage[]
  timestamp: string
}

interface DropOffPoint {
  stage: string
  dropoff_count: number
  dropoff_rate: number
  time_at_stage_ms: number
  primary_reason?: string
  segment_breakdown: Record<string, number>
}

interface JourneyDropOff {
  journey_type: string
  total_dropoffs: number
  overall_abandonment_rate: number
  dropoff_points: DropOffPoint[]
  most_problematic_stage: string
  timestamp: string
}

interface SegmentMetrics {
  segment_name: string
  segment_key: string
  device_type?: string
  user_type?: string
  accessibility_mode?: boolean
  total_sessions: number
  completed_sessions: number
  completion_rate: number
  avg_completion_time_ms: number
  error_rate: number
  abandonment_rate: number
}

interface RegressionAlert {
  alert_id: number
  journey_type: string
  alert_type: string
  severity: string
  current_value: number
  baseline_value: number
  percent_change: number
  description: string
  segment_affected?: string
  created_at: string
  is_resolved: boolean
}

interface DashboardData {
  timestamp: string
  time_period: string
  journeys: Record<string, JourneyFunnel | null>
  segments: SegmentMetrics[]
  dropoffs: Record<string, JourneyDropOff>
  alerts: RegressionAlert[]
  real_time_enabled: boolean
  next_real_time_update_in_seconds: number
}

// Funnel Chart Component
const FunnelChart: React.FC<{
  stages: FunnelStage[]
  completionRate: number
  journeyType: string
}> = ({ stages, completionRate, journeyType }) => {
  const funnelData = stages.map((stage, idx) => ({
    stage: stage.stage_name,
    count: stage.unique_sessions,
    rate: stage.completion_rate,
    order: idx,
  }))

  if (funnelData.length === 0) {
    return (
      <div className="p-8 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
        No funnel data available
      </div>
    )
  }

  // Calculate max width for proportional rendering
  const maxCount = Math.max(...funnelData.map(d => d.count), 1)

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center mb-4">
        <h3 className="font-serif text-lg font-semibold">{JOURNEYS[journeyType as JourneyType]}</h3>
        <div className="text-2xl font-bold text-lsc-rose dark:text-lsc-rose-light">
          {completionRate.toFixed(1)}%
        </div>
      </div>

      <div className="space-y-3">
        {funnelData.map((item, idx) => (
          <div key={idx} className="space-y-1">
            <div className="flex justify-between text-sm">
              <span className="font-medium">{item.stage}</span>
              <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{item.count} sessions</span>
            </div>
            <div className="h-8 bg-earth-100 dark:bg-earth-700 rounded-lg overflow-hidden">
              <div
                className={cn(
                  'h-full flex items-center px-2 text-white text-xs font-semibold transition-all',
                  'bg-gradient-to-r from-blue-500 to-blue-600'
                )}
                style={{
                  width: `${(item.count / maxCount) * 100}%`,
                }}
              >
                {item.rate.toFixed(0)}%
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Time metrics */}
      <div className="grid grid-cols-3 gap-4 pt-4 border-t">
        <div className="text-center">
          <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Avg Time</div>
          <div className="font-semibold">
            {((stages[stages.length - 1]?.avg_time_to_stage_ms ?? 0) / 1000).toFixed(1)}s
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Median Time</div>
          <div className="font-semibold">
            {((stages[stages.length - 1]?.median_time_to_stage_ms ?? 0) / 1000).toFixed(1)}s
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Error Rate</div>
          <div className="font-semibold">
            {(
              (stages.reduce((sum, s) => sum + s.error_count, 0) /
                stages.reduce((sum, s) => sum + s.event_count, 0)) *
              100
            ).toFixed(1)}%
          </div>
        </div>
      </div>
    </div>
  )
}

// Drop-off Analysis Component
const DropOffAnalysis: React.FC<{
  journey_type: string
  dropoff_points: DropOffPoint[]
  abandonment_rate: number
}> = ({ journey_type: _journey_type, dropoff_points, abandonment_rate }) => {
  if (dropoff_points.length === 0) {
    return (
      <div className="p-8 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
        No drop-off data available
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center mb-4">
        <h3 className="font-serif text-lg font-semibold">Drop-off Points</h3>
        <div className="text-2xl font-bold text-status-danger-600">
          {abandonment_rate.toFixed(1)}%
        </div>
      </div>

      <div className="space-y-3">
        {dropoff_points
          .sort((a, b) => b.dropoff_count - a.dropoff_count)
          .slice(0, 5)
          .map((point, idx) => (
            <div key={idx} className="border-l-4 border-status-danger-500 pl-3 py-2">
              <div className="flex justify-between mb-1">
                <span className="font-medium text-sm">{point.stage}</span>
                <span className="text-status-danger-600 font-semibold">
                  {point.dropoff_count} users
                </span>
              </div>
              <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                {point.dropoff_rate.toFixed(1)}% abandonment rate
              </div>
              {point.primary_reason && (
                <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                  Reason: {point.primary_reason}
                </div>
              )}
            </div>
          ))}
      </div>
    </div>
  )
}

// Alerts Component
const AlertsPanel: React.FC<{ alerts: RegressionAlert[] }> = ({ alerts }) => {
  if (alerts.length === 0) {
    return (
      <Alert className="bg-status-success-50 dark:bg-status-success-900/20 border-status-success-200 dark:border-status-success-800">
        <Activity className="h-4 w-4 text-status-success-600" />
        <AlertTitle>All Systems Healthy</AlertTitle>
        <AlertDescription>
          No regressions detected in the last 24 hours.
        </AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="space-y-3">
      {alerts.map((alert) => (
        <Alert
          key={alert.alert_id}
          className={cn(
            alert.severity === 'high'
              ? 'bg-status-danger-50 dark:bg-status-danger-900/20 border-status-danger-200 dark:border-status-danger-800'
              : alert.severity === 'medium'
                ? 'bg-status-warning-50 dark:bg-status-warning-900/20 border-status-warning-200 dark:border-status-warning-800'
                : 'bg-earth-50 dark:bg-earth-800/20 border-lsc-border dark:border-earth-700'
          )}
        >
          <AlertTriangle
            className={cn(
              'h-4 w-4',
              alert.severity === 'high'
                ? 'text-status-danger-600'
                : alert.severity === 'medium'
                  ? 'text-status-warning-600'
                  : 'text-lsc-rose dark:text-lsc-rose-light'
            )}
          />
          <AlertTitle className="text-sm">
            {JOURNEYS[alert.journey_type as JourneyType]}
          </AlertTitle>
          <AlertDescription className="text-xs mt-1">
            {alert.description}
          </AlertDescription>
        </Alert>
      ))}
    </div>
  )
}

// Segment Metrics Component
const SegmentMetricsView: React.FC<{
  segments: SegmentMetrics[]
}> = ({ segments }) => {
  if (segments.length === 0) {
    return (
      <div className="p-8 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
        No segment data available
      </div>
    )
  }

  const deviceSegments = segments.filter(s => s.device_type)
  const userTypeSegments = segments.filter(s => s.user_type)
  const accessibilitySegments = segments.filter(s => s.accessibility_mode)

  return (
    <div className="space-y-6">
      {deviceSegments.length > 0 && (
        <div>
          <h3 className="font-serif text-lg font-semibold mb-3">By Device</h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            {deviceSegments.map((seg, idx) => (
              <Card key={idx}>
                <CardContent className="pt-4">
                  <div className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                    {seg.device_type}
                  </div>
                  <div className="text-2xl font-bold text-lsc-rose dark:text-lsc-rose-light mb-2">
                    {seg.completion_rate.toFixed(1)}%
                  </div>
                  <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                    {seg.total_sessions} sessions
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {userTypeSegments.length > 0 && (
        <div>
          <h3 className="font-serif text-lg font-semibold mb-3">By User Type</h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            {userTypeSegments.map((seg, idx) => (
              <Card key={idx}>
                <CardContent className="pt-4">
                  <div className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                    {seg.user_type}
                  </div>
                  <div className="text-2xl font-bold text-lsc-rose dark:text-lsc-rose-light mb-2">
                    {seg.completion_rate.toFixed(1)}%
                  </div>
                  <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                    {seg.total_sessions} sessions
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {accessibilitySegments.length > 0 && (
        <div>
          <h3 className="font-serif text-lg font-semibold mb-3">Accessibility Mode</h3>
          <Card>
            <CardContent className="pt-4">
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Completion Rate</div>
                  <div className="text-2xl font-bold text-lsc-rose dark:text-lsc-rose-light">
                    {accessibilitySegments[0]!.completion_rate.toFixed(1)}%
                  </div>
                </div>
                <div>
                  <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Sessions</div>
                  <div className="text-2xl font-bold text-lsc-rose dark:text-lsc-rose-light">
                    {accessibilitySegments[0]!.total_sessions}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Error Rate</div>
                  <div className="text-2xl font-bold text-status-danger-600">
                    {accessibilitySegments[0]!.error_rate.toFixed(1)}%
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}

// Main Dashboard Component
export const JourneyAnalyticsDashboard: React.FC = () => {
  const [timePeriod, setTimePeriod] = useState('24') // hours
  const [selectedJourney, setSelectedJourney] = useState<JourneyType>('search_to_hold')
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [refreshCountdown, setRefreshCountdown] = useState(30)

  // Fetch dashboard data
  const { data: dashboardData, isLoading, refetch } = useQuery<DashboardData>({
    queryKey: ['journeyDashboard', timePeriod],
    queryFn: async (): Promise<DashboardData> => {
      const response = await fetchApi<unknown>(`${API_BASE}/analytics/journeys?hours=${timePeriod}`, {
        method: 'GET',
      })
      return (response as Record<string, unknown>).data as DashboardData
    },
    staleTime: 1000 * 30, // 30 seconds
    refetchInterval: autoRefresh ? 1000 * 30 : false,
  })

  // Auto-refresh countdown
  useEffect(() => {
    if (!autoRefresh || !dashboardData) return

    const interval = setInterval(() => {
      setRefreshCountdown(prev => {
        if (prev <= 1) {
          refetch()
          return 30
        }
        return prev - 1
      })
    }, 1000)

    return () => clearInterval(interval)
  }, [autoRefresh, dashboardData, refetch])

  const handleManualRefresh = useCallback(() => {
    refetch()
    toast.success(t('toast.journeyAnalyticsDashboard.dashboardRefreshed'))
    setRefreshCountdown(30)
  }, [refetch])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="motion-safe:animate-spin mb-4">
            <RefreshCw className="h-8 w-8 text-lsc-rose dark:text-lsc-rose-light" />
          </div>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">Loading analytics...</p>
        </div>
      </div>
    )
  }

  const currentJourneyData = dashboardData?.journeys?.[selectedJourney]
  const currentDropOffData = dashboardData?.dropoffs?.[selectedJourney]

  return (

    <AdminShell title="Journey Analytics Dashboard">    <div className="min-h-screen bg-lsc-cream dark:bg-earth-900 p-4 sm:p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              Journey Analytics Dashboard
            </h1>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              Real-time patron journey metrics and insights
            </p>
          </div>

          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleManualRefresh}
              disabled={isLoading}
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>
        </div>

        {/* Controls */}
        <div className="flex flex-col sm:flex-row gap-4">
          <Select value={timePeriod} onValueChange={setTimePeriod}>
            <SelectTrigger className="w-full sm:w-48">
              <SelectValue placeholder={t('placeholder.journeyAnalyticsDashboard.selectTimePeriod')} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1">Last 1 hour</SelectItem>
              <SelectItem value="24">Last 24 hours</SelectItem>
              <SelectItem value="168">Last 7 days</SelectItem>
              <SelectItem value="720">Last 30 days</SelectItem>
            </SelectContent>
          </Select>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="autoRefresh"
              checked={autoRefresh}
              onChange={e => setAutoRefresh(e.target.checked)}
              className="w-4 h-4"
            />
            <label
              htmlFor="autoRefresh"
              className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 cursor-pointer"
            >
              Auto-refresh ({refreshCountdown}s)
            </label>
          </div>
        </div>

        {/* Alerts */}
        {dashboardData?.alerts && dashboardData.alerts.length > 0 && (
          <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-lg p-4">
            <AlertsPanel alerts={dashboardData.alerts} />
          </div>
        )}

        {/* Funnels */}
        <div>
          <h2 className="text-2xl font-serif font-bold mb-4">Journey Funnels</h2>
          <Tabs value={selectedJourney} onValueChange={v => setSelectedJourney(v as JourneyType)}>
            <TabsList>
              {(Object.keys(JOURNEYS) as JourneyType[]).map(journey => (
                <TabsTrigger key={journey} value={journey} className="text-xs sm:text-sm">
                  {JOURNEYS[journey]}
                </TabsTrigger>
              ))}
            </TabsList>

            {(Object.keys(JOURNEYS) as JourneyType[]).map(journey => (
              <TabsContent key={journey} value={journey}>
                <Card>
                  <CardContent className="pt-6">
                    {currentJourneyData && currentJourneyData.journey_type === journey ? (
                      <FunnelChart
                        stages={currentJourneyData.stages}
                        completionRate={currentJourneyData.overall_completion_rate}
                        journeyType={journey}
                      />
                    ) : (
                      <div className="p-8 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
                        No data available for this journey
                      </div>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>
            ))}
          </Tabs>
        </div>

        {/* Drop-offs & Segments */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Drop-offs */}
          <Card>
            <CardHeader>
              <CardTitle>Drop-off Analysis</CardTitle>
            </CardHeader>
            <CardContent>
              {currentDropOffData ? (
                <DropOffAnalysis
                  journey_type={selectedJourney}
                  dropoff_points={currentDropOffData.dropoff_points}
                  abandonment_rate={currentDropOffData.overall_abandonment_rate}
                />
              ) : (
                <div className="p-8 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
                  No drop-off data
                </div>
              )}
            </CardContent>
          </Card>

          {/* Segmentation */}
          <Card>
            <CardHeader>
              <CardTitle>Segmentation Analysis</CardTitle>
            </CardHeader>
            <CardContent>
              {dashboardData?.segments && dashboardData.segments.length > 0 ? (
                <SegmentMetricsView segments={dashboardData.segments} />
              ) : (
                <div className="p-8 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
                  No segmentation data
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Footer */}
        <div className="text-center text-sm text-lsc-dark/70 dark:text-lsc-cream/70 py-4">
          Last updated: {dashboardData?.timestamp && new Date(dashboardData.timestamp).toLocaleString()}
        </div>
      </div>
    </div>
  </AdminShell>
  )
}

export default JourneyAnalyticsDashboard