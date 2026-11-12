/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { api } from '@/lib/api-client'

export interface PatronCategory {
  id: number
  code: string
  label: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface PatronCategoryCreatePayload {
  code: string
  label: string
  is_active?: boolean
}

export interface PatronCategoryUpdatePayload {
  code?: string
  label?: string
  is_active?: boolean
}

export function listPatronCategories(includeInactive = false): Promise<PatronCategory[]> {
  const qs = includeInactive ? '?include_inactive=true' : ''
  return api.get<PatronCategory[]>(`/admin/patron-categories${qs}`)
}

export function getPatronCategory(id: number): Promise<PatronCategory> {
  return api.get<PatronCategory>(`/admin/patron-categories/${id}`)
}

export function createPatronCategory(
  payload: PatronCategoryCreatePayload,
): Promise<PatronCategory> {
  return api.post<PatronCategory>('/admin/patron-categories', payload)
}

export function updatePatronCategory(
  id: number,
  payload: PatronCategoryUpdatePayload,
): Promise<PatronCategory> {
  return api.put<PatronCategory>(`/admin/patron-categories/${id}`, payload)
}

export function removePatronCategory(id: number): Promise<void> {
  return api.delete<void>(`/admin/patron-categories/${id}`)
}
