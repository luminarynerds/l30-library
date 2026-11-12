/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { api } from '@/lib/api-client'
import type { ItemType } from '@/api/domains/catalog/catalog-api'

// Roles that can scope a circulation policy. Matches backend UserRole enum.
// (UI-facing UserRole in @/constants/userManagement is a narrower subset.)
export type CirculationPolicyRole =
  | 'super_admin'
  | 'admin'
  | 'director'
  | 'legal'
  | 'staff'
  | 'patron'
  | 'teacher'
  | 'child'
  | 'bookmobile'
  | 'homebond'

export const CIRCULATION_POLICY_ROLES: readonly CirculationPolicyRole[] = [
  'super_admin',
  'admin',
  'director',
  'legal',
  'staff',
  'patron',
  'teacher',
  'child',
  'bookmobile',
  'homebond',
] as const

export type BookBinding =
  | 'hardback'
  | 'paperback'
  | 'mass_market'
  | 'board_book'
  | 'spiral'
  | 'library_binding'
  | 'other'

export const BOOK_BINDINGS: readonly BookBinding[] = [
  'hardback',
  'paperback',
  'mass_market',
  'board_book',
  'spiral',
  'library_binding',
  'other',
] as const

// All known item types (mirrors @/api/domains/catalog ItemType, kept literal here
// so the matrix UI doesn't depend on the catalog page's exact union shape).
export const CIRCULATION_POLICY_ITEM_TYPES: readonly ItemType[] = [
  'book',
  'audiobook',
  'ebook',
  'dvd',
  'bluray',
  'cd',
  'vinyl',
  'magazine',
  'game',
  'equipment',
  'kit',
  'other',
] as const

export interface CirculationPolicyResponse {
  id: number
  library_system_id: number
  role: CirculationPolicyRole | null
  item_type: ItemType | null
  binding: BookBinding | null
  collection_id: number | null
  loan_period_days: number | null
  max_renewals: number | null
  overdue_fine_per_day: string | null
  max_fine: string | null
  grace_period_days: number | null
  hold_pickup_days: number | null
  fine_free: boolean | null
  active: boolean
  notes: string | null
  created_at: string
  updated_at: string | null
}

export interface CirculationPolicyCreate {
  library_system_id: number
  role?: CirculationPolicyRole | null
  item_type?: ItemType | null
  binding?: BookBinding | null
  collection_id?: number | null
  loan_period_days?: number | null
  max_renewals?: number | null
  overdue_fine_per_day?: string | null
  max_fine?: string | null
  grace_period_days?: number | null
  hold_pickup_days?: number | null
  fine_free?: boolean | null
  active?: boolean
  notes?: string | null
}

export type CirculationPolicyUpdate = Partial<Omit<CirculationPolicyCreate, 'library_system_id'>>

export interface CirculationPolicyListParams {
  library_system_id?: number
  role?: CirculationPolicyRole
  item_type?: ItemType
  binding?: BookBinding
  collection_id?: number
  active?: boolean
}

// Provenance: per-field, which policy row supplied the resolved value.
export interface ResolvedFieldProvenance {
  policy_id: number | null
  scope: string  // e.g. 'format default for "book"' or 'system default'
}

export interface ResolvedPolicyResponse {
  loan_period_days: number
  max_renewals: number
  overdue_fine_per_day: string
  max_fine: string
  grace_period_days: number
  hold_pickup_days: number
  fine_free: boolean
  provenance: {
    loan_period_days: ResolvedFieldProvenance
    max_renewals: ResolvedFieldProvenance
    overdue_fine_per_day: ResolvedFieldProvenance
    max_fine: ResolvedFieldProvenance
    grace_period_days: ResolvedFieldProvenance
    hold_pickup_days: ResolvedFieldProvenance
    fine_free: ResolvedFieldProvenance
  }
}

export interface PreviewPolicyParams {
  user_id?: number
  item_id?: number
  collection_id?: number
  // Synthetic preview (no real user/item): pass scope axes directly.
  role?: CirculationPolicyRole
  item_type?: ItemType
  binding?: BookBinding
  library_system_id?: number
}

const BASE = '/staff/circulation-policies'

export async function listCirculationPolicies(
  params: CirculationPolicyListParams = {},
): Promise<CirculationPolicyResponse[]> {
  return api.get<CirculationPolicyResponse[]>(BASE, { params: params as Record<string, unknown> })
}

export async function getCirculationPolicy(id: number): Promise<CirculationPolicyResponse> {
  return api.get<CirculationPolicyResponse>(`${BASE}/${id}`)
}

export async function createCirculationPolicy(
  body: CirculationPolicyCreate,
): Promise<CirculationPolicyResponse> {
  return api.post<CirculationPolicyResponse>(BASE, body)
}

export async function updateCirculationPolicy(
  id: number,
  body: CirculationPolicyUpdate,
): Promise<CirculationPolicyResponse> {
  return api.put<CirculationPolicyResponse>(`${BASE}/${id}`, body)
}

export async function deleteCirculationPolicy(id: number): Promise<void> {
  await api.delete<void>(`${BASE}/${id}`)
}

export async function previewCirculationPolicy(
  params: PreviewPolicyParams,
): Promise<ResolvedPolicyResponse> {
  return api.get<ResolvedPolicyResponse>(`${BASE}/preview`, {
    params: params as Record<string, unknown>,
  })
}

// ==================== Display helpers ====================

const BINDING_LABELS: Record<BookBinding, string> = {
  hardback: 'Hardback',
  paperback: 'Paperback',
  mass_market: 'Mass market',
  board_book: 'Board book',
  spiral: 'Spiral',
  library_binding: 'Library binding',
  other: 'Other',
}

const ITEM_TYPE_LABELS: Record<ItemType, string> = {
  book: 'Book',
  audiobook: 'Audiobook',
  ebook: 'eBook',
  dvd: 'DVD',
  bluray: 'Blu-ray',
  cd: 'CD',
  vinyl: 'Vinyl',
  magazine: 'Magazine',
  game: 'Game',
  equipment: 'Equipment',
  kit: 'Kit',
  other: 'Other',
}

const ROLE_LABELS: Record<CirculationPolicyRole, string> = {
  super_admin: 'Super admin',
  admin: 'Admin',
  director: 'Director',
  legal: 'Legal',
  staff: 'Staff',
  patron: 'Patron',
  teacher: 'Teacher',
  child: 'Child',
  bookmobile: 'Bookmobile',
  homebond: 'Homebound',
}

export function bindingLabel(binding: BookBinding): string {
  return BINDING_LABELS[binding]
}

export function itemTypeLabel(itemType: ItemType): string {
  return ITEM_TYPE_LABELS[itemType]
}

export function roleLabel(role: CirculationPolicyRole): string {
  return ROLE_LABELS[role]
}

export function describeScope(p: Pick<CirculationPolicyResponse, 'role' | 'item_type' | 'binding' | 'collection_id'>): {
  role: string
  itemType: string
  binding: string
  collection: string
} {
  return {
    role: p.role ? ROLE_LABELS[p.role] : '—',
    itemType: p.item_type ? ITEM_TYPE_LABELS[p.item_type] : '—',
    binding: p.binding ? BINDING_LABELS[p.binding] : '—',
    collection: p.collection_id !== null ? `#${p.collection_id}` : '—',
  }
}
