/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { API_BASE as API_ROOT } from '@/api/types'
import { fetchApi } from '@/api/fetchApi'
import { type OrderTemplate, type TemplateItem } from '@/api/order-templates-api'

export const API_BASE = `${API_ROOT}/acquisition`
export const RELEASES_API = `${API_BASE}/releases`

export interface Fund { id: number; code: string; name: string; fiscal_year: number; allocated_amount: number; encumbered_amount: number; spent_amount: number; available_amount: number; status: string }
export interface Vendor { id: number; name: string; contact_name: string | null; email: string | null; phone: string | null; is_active: boolean }
export interface SelectionItem { id: number; title: string; author: string | null; isbn: string | null; cover_url: string | null; priority: string; source: string; status?: string; estimated_price?: number; notes?: string }
export interface PurchaseOrder { id: number; po_number: string; vendor_name: string | null; fund_name: string | null; status: string; total_amount: number; total_items: number; has_backorders: boolean; created_at?: string | null }
export interface PurchaseOrderItem { id: number; title: string; author: string | null; isbn: string | null; quantity: number; unit_price: number; notes: string | null; backordered_quantity: number | null; expected_ship_date: string | null }
export interface PurchaseOrderDetail { id: number; po_number: string; vendor_id: number | null; vendor_name: string | null; fund_id: number | null; fund_name: string | null; status: string; total_amount: number; total_items: number; has_backorders: boolean; notes: string | null; items: PurchaseOrderItem[]; created_by_id: number }
export interface ExternalSearchResult { source: string; source_id: string; title: string; author: string | null; isbn: string | null; cover_url: string | null }

export { type OrderTemplate, type TemplateItem }

export async function apiFetch<T>(_token: string, endpoint: string, options: RequestInit = {}): Promise<T> {
  // _token kept for backward compat; fetchApi reads from tokenStore internally.
  // Compute path relative to API_ROOT (which fetchApi prepends).
  // Releases endpoints arrive as absolute URLs starting with `${API_ROOT}/acquisition/releases`;
  // other endpoints arrive as relative paths (e.g. "/funds") that need the "/acquisition" prefix.
  const path = endpoint.startsWith(`${API_BASE}/releases`)
    ? endpoint.slice(API_ROOT.length)
    : `/acquisition${endpoint}`
  try {
    return await fetchApi(path, options)
  } catch (err) {
    let detail: unknown = (err as { message?: string })?.message || 'Request failed'
    if (Array.isArray(detail)) {
      detail = (detail as Array<{ msg?: string }>).map((d) => d.msg || JSON.stringify(d)).join('; ')
    } else if (typeof detail === 'object' && detail !== null) {
      detail = JSON.stringify(detail)
    }
    throw new Error(String(detail))
  }
}

export const formatMoney = (n: number) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n)
