/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { fetchApi, isApiError } from '@/lib/api-client'

export interface TechClass {
  id?: number
  title: string
  date: string
  time: string
  location: string
  level: string
  description: string
  instructor?: string
  capacity?: number
  enrolled?: number
}

export interface QuickLink {
  name: string
  url: string
}

export interface QuickAccessSection {
  title: string
  icon?: string
  links: QuickLink[]
}

export interface TechHelpOption {
  id?: number
  title: string
  description: string
  schedule: string
  location?: string
  phone?: string
  icon?: string
}

export interface TechResource {
  id?: number
  title: string
  description: string
  category: string
  format: string
  duration?: string
  href?: string
  difficulty_level?: string
}

export interface TechFacility {
  id: number
  label: string
  value: string
}

export interface TechFacilitySection {
  kind: string
  facilities: TechFacility[]
}

function reportAndRethrow(error: unknown): never {
  if (isApiError(error)) {
    Sentry.captureException(new Error(error.detail))
  } else {
    Sentry.captureException(error)
  }
  throw error
}

export async function getUpcomingClasses(): Promise<TechClass[]> {
  try {
    return await fetchApi<TechClass[]>('/tech-support/classes')
  } catch (error: unknown) {
    reportAndRethrow(error)
  }
}

export async function getTechHelpOptions(lang?: string): Promise<TechHelpOption[]> {
  try {
    const qs = lang && lang !== 'en' ? `?lang=${encodeURIComponent(lang)}` : ''
    return await fetchApi<TechHelpOption[]>(`/tech-support/help-options${qs}`)
  } catch (error: unknown) {
    reportAndRethrow(error)
  }
}

export async function getQuickAccessSections(): Promise<QuickAccessSection[]> {
  try {
    return await fetchApi<QuickAccessSection[]>('/tech-support/quick-links')
  } catch (error: unknown) {
    reportAndRethrow(error)
  }
}

export async function getTechResources(category?: string): Promise<TechResource[]> {
  try {
    const params = category ? `?category=${category}` : ''
    return await fetchApi<TechResource[]>(`/tech-support/resources${params}`)
  } catch (error: unknown) {
    reportAndRethrow(error)
  }
}

export async function getTechFacilities(): Promise<TechFacilitySection[]> {
  try {
    return await fetchApi<TechFacilitySection[]>('/tech-support/facilities')
  } catch (error: unknown) {
    reportAndRethrow(error)
  }
}
