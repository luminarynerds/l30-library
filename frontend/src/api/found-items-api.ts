/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from "@/lib/api-client"

export interface FoundItemStorageLocation {
  id: number
  location_name: string
  location_code: string
  description: string | null
  branch: string | null
  max_items: number | null
  current_item_count: number
  is_secure_storage: boolean
  is_active: boolean
}

export interface FoundItem {
  id: number
  description: string
  category: string
  color: string | null
  brand_or_label: string | null
  size: string | null
  condition: string | null
  additional_details: string | null
  location_found: string
  location_details: string | null
  date_found: string
  storage_location_id: number | null
  storage_location: FoundItemStorageLocation | null
  secure_storage_flag: boolean
  estimated_value: string | null
  status: string
  retention_period_days: number
  retention_end_date: string
  disposal_method: string | null
  disposed_at: string | null
  disposal_notes: string | null
  staff_notes: string | null
  found_by_id: number
  logged_by_id: number
  created_at: string | null
  updated_at: string | null
}

export interface FoundItemListResponse {
  items: FoundItem[]
  total: number
  limit: number
  offset: number
}

export async function listFoundItems(params?: {
  status?: string
  category?: string
  location_found?: string
  limit?: number
  offset?: number
}): Promise<FoundItemListResponse> {
  const sp = new URLSearchParams()
  if (params?.status) sp.set("status", params.status)
  if (params?.category) sp.set("category", params.category)
  if (params?.location_found) sp.set("location_found", params.location_found)
  if (params?.limit) sp.set("limit", String(params.limit))
  if (params?.offset) sp.set("offset", String(params.offset))
  const q = sp.toString()
  return fetchApi<FoundItemListResponse>(`/found-items${q ? `?${q}` : ""}`)
}

export async function getFoundItem(id: number): Promise<FoundItem> {
  return fetchApi<FoundItem>(`/found-items/${id}`)
}
