/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from '@/lib/api-client'

export interface MetricValue {
  value: number
  prev?: number
}

export interface WebsiteAnalyticsStats {
  pageviews: MetricValue
  visitors: MetricValue
  visits: MetricValue
  bounces: MetricValue
  totaltime: MetricValue
}

export interface PageviewsPoint {
  x: string
  y: number
}

export interface PageviewsSeries {
  pageviews: PageviewsPoint[]
  sessions: PageviewsPoint[]
}

export interface MetricRow {
  x: string
  y: number
}

export type WebsiteMetricType =
  | 'path'
  | 'referrer'
  | 'browser'
  | 'os'
  | 'device'
  | 'country'
  | 'city'
  | 'language'
  | 'event'

export interface ActiveVisitors {
  visitors: number
}

function qs(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') search.set(k, String(v))
  }
  const s = search.toString()
  return s ? `?${s}` : ''
}

export async function getWebsiteAnalyticsStats(days: number): Promise<WebsiteAnalyticsStats> {
  return fetchApi<WebsiteAnalyticsStats>(`/admin/website-analytics/stats${qs({ days })}`)
}

export async function getWebsiteAnalyticsPageviews(
  days: number,
  unit: 'hour' | 'day' | 'month' = 'day',
): Promise<PageviewsSeries> {
  return fetchApi<PageviewsSeries>(`/admin/website-analytics/pageviews${qs({ days, unit })}`)
}

export async function getWebsiteAnalyticsMetrics(
  type: WebsiteMetricType,
  days: number,
  limit = 10,
): Promise<MetricRow[]> {
  return fetchApi<MetricRow[]>(`/admin/website-analytics/metrics/${type}${qs({ days, limit })}`)
}

export async function getWebsiteAnalyticsActive(): Promise<ActiveVisitors> {
  return fetchApi<ActiveVisitors>(`/admin/website-analytics/active`)
}
