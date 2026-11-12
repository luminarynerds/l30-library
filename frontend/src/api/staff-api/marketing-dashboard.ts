/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from '@/lib/api-client'

export interface NewsletterStatus {
  id: number | null
  name: string | null
  subject: string | null
  status: string | null
  scheduled_for: string | null
  section_progress: number
}

export interface SocialQueueSummary {
  scheduled_count: number
  draft_count: number
}

export interface InFlight {
  newsletter: NewsletterStatus
  social_queue: SocialQueueSummary
}

export interface Last30Days {
  newsletter_open_rate: number
  posts_published: number
  subscriber_count: number
}

export interface NeedsPromoProgram {
  id: number
  title: string
  program_date: string
  audience: string
  location: string | null
  has_marketing_campaign: boolean
}

export interface MarketingDashboardData {
  in_flight: InFlight
  last_30_days: Last30Days
  needs_promo: NeedsPromoProgram[]
}

export async function getMarketingDashboard(token: string): Promise<MarketingDashboardData> {
  return fetchApi<MarketingDashboardData>('/staff/marketing/dashboard', { token })
}
