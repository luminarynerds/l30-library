/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from '@/lib/api-client'

export interface ActiveCheckout {
  service: string
  title: string
  due_date: string
}

export interface DownloadQuota {
  service: string
  used: number
  limit: number
  period: string
}

export interface RecentService {
  service: string
  last_used: string
}

export interface DigitalActivitySummary {
  active_checkouts: ActiveCheckout[]
  download_quotas: DownloadQuota[]
  recent_services: RecentService[]
}

export async function getDigitalActivity(authToken: string): Promise<DigitalActivitySummary> {
  return fetchApi<DigitalActivitySummary>('/patron/digital-activity', { token: authToken })
}
