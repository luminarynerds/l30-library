/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { api } from '@/lib/api-client'

export interface HomepageQuotePublic {
  id: number
  quote_text: string
  attribution: string | null
}

export interface HomepageQuoteAdmin extends HomepageQuotePublic {
  locale: string
  is_active: boolean
  display_order: number
}

export interface HomepageQuoteCreate {
  locale: string
  quote_text: string
  attribution?: string | null
  is_active?: boolean
  display_order?: number
}

export interface HomepageQuoteUpdate {
  locale?: string
  quote_text?: string
  attribution?: string | null
  is_active?: boolean
  display_order?: number
}

export async function getHomepageQuotes(locale: string): Promise<HomepageQuotePublic[]> {
  return api.get(`/homepage-quotes?locale=${encodeURIComponent(locale)}`)
}

export async function adminListHomepageQuotes(locale?: string): Promise<HomepageQuoteAdmin[]> {
  const qs = locale ? `?locale=${encodeURIComponent(locale)}` : ''
  return api.get(`/admin/homepage-quotes${qs}`)
}

export async function adminCreateHomepageQuote(data: HomepageQuoteCreate): Promise<HomepageQuoteAdmin> {
  return api.post('/admin/homepage-quotes', data)
}

export async function adminUpdateHomepageQuote(id: number, data: HomepageQuoteUpdate): Promise<HomepageQuoteAdmin> {
  return api.put(`/admin/homepage-quotes/${id}`, data)
}

export async function adminDeleteHomepageQuote(id: number): Promise<void> {
  await api.delete(`/admin/homepage-quotes/${id}`)
}
