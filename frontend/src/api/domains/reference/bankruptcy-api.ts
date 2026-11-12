/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { fetchApi, isApiError } from '@/lib/api-client'

export interface BankruptcyFiling {
  docket_id: number
  case_name: string
  docket_number: string
  date_filed: string | null
  court_name: string
  court_id: string
  chapter: string | null
  trustee: string | null
  courtlistener_url: string
}

export interface BankruptcyCourt {
  id: string
  short_name: string
  full_name: string
}

export interface BankruptcySearchResponse {
  filings: BankruptcyFiling[]
  source: string
  source_url: string
}

export async function getRecentFilings(courtId?: string, days = 7): Promise<BankruptcySearchResponse> {
  try {
    const params = new URLSearchParams()
    if (courtId) params.set('court_id', courtId)
    params.set('days', String(days))
    return await fetchApi<BankruptcySearchResponse>(`/legal/bankruptcy/recent?${params}`)
  } catch (error: unknown) {
    if (isApiError(error)) Sentry.captureException(new Error((error as Error).message))
    return { filings: [], source: "CourtListener / RECAP Archive", source_url: "https://www.courtlistener.com/recap/" }
  }
}

export async function searchFilings(query: string, courtId?: string): Promise<BankruptcySearchResponse> {
  try {
    const params = new URLSearchParams({ q: query })
    if (courtId) params.set('court_id', courtId)
    return await fetchApi<BankruptcySearchResponse>(`/legal/bankruptcy/search?${params}`)
  } catch (error: unknown) {
    if (isApiError(error)) Sentry.captureException(new Error((error as Error).message))
    return { filings: [], source: "CourtListener / RECAP Archive", source_url: "https://www.courtlistener.com/recap/" }
  }
}

export async function getBankruptcyCourts(): Promise<BankruptcyCourt[]> {
  try {
    return await fetchApi<BankruptcyCourt[]>('/legal/bankruptcy/courts')
  } catch (error: unknown) {
    if (isApiError(error)) Sentry.captureException(new Error((error as Error).message))
    return []
  }
}
