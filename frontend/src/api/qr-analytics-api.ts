/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * QR analytics API client.
 *
 * Backs the /staff/qr-scans dashboard. Two endpoints, both staff-gated
 * server-side; see backend/app/api/v1/qr_analytics.py for the shape rationale.
 */
import { fetchApi } from '@/lib/api-client'

export interface QrAnalyticsRow {
  slug: string
  pageviews: number
  /** Optional because Umami's `type=query` metric does not break visitors out per query string. */
  visitors?: number
}

export interface QrAnalyticsByMonthSeries {
  slug: string
  /** Per-month counts, aligned to the top-level `months` array (oldest first). */
  counts: number[]
}

export interface QrAnalyticsByMonth {
  /** `YYYY-MM` labels, oldest first. */
  months: string[]
  series: QrAnalyticsByMonthSeries[]
}

function qs(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') search.set(k, String(v))
  }
  const s = search.toString()
  return s ? `?${s}` : ''
}

export async function getQrAnalytics(days: number): Promise<QrAnalyticsRow[]> {
  return fetchApi<QrAnalyticsRow[]>(`/admin/qr-analytics${qs({ days })}`)
}

export async function getQrAnalyticsByMonth(months: number): Promise<QrAnalyticsByMonth> {
  return fetchApi<QrAnalyticsByMonth>(`/admin/qr-analytics/by-month${qs({ months })}`)
}
