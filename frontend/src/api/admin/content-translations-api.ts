/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { api } from '@/lib/api-client'

export interface ContentTranslationField {
  field: string
  source: string
  value: string | null
}

export interface ContentTranslationRecord {
  id: number
  display_name: string
  fields: ContentTranslationField[]
}

export interface ContentTranslationGroup {
  content_type: string
  label: string
  records: ContentTranslationRecord[]
}

export interface ContentTranslationsResponse {
  language: string
  groups: ContentTranslationGroup[]
}

export function getContentTranslations(language: string): Promise<ContentTranslationsResponse> {
  return api.get<ContentTranslationsResponse>('/staff/content-translations', {
    params: { lang: language },
  })
}

export function updateContentTranslation(
  contentType: string,
  recordId: number,
  language: string,
  values: Record<string, string>,
): Promise<ContentTranslationRecord> {
  return api.put<ContentTranslationRecord>(
    `/staff/content-translations/${contentType}/${recordId}`,
    { language, values },
  )
}
