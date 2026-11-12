/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export interface PullListItem {
  hold_id: number
  item_id: number
  item_title: string
  item_author: string | null
  call_number: string | null
  shelf_location: string | null
  barcode: string | null
  patron_name: string
  patron_initials: string
  patron_library_card: string | null
  hold_expires_at: string | null
  hold_created_at: string
  days_until_expiry: number | null
  shelf_slot: string | null
  patron_on_way: boolean
  qr_pickup_code: string | null
  no_show_count: number
}

export interface LocationGroup {
  location: string
  items: PullListItem[]
  item_count: number
}

export interface PullListResponse {
  locations: LocationGroup[]
  total_items: number
  generated_at: string
}

export interface CapacityStatus {
  branch_id: number
  branch_name: string
  ready_holds_count: number
  capacity_limit: number
  capacity_percentage: number
  is_at_capacity: boolean
  is_over_warning: boolean
  warning_threshold_percentage: number
  available_slots: number
  expiring_today_count?: number
  expiring_tomorrow_count?: number
}

export interface ExpiringHold {
  hold_id: number
  item_id: number
  item_title: string
  item_author: string | null
  patron_name: string
  patron_initials: string
  shelf_slot: string | null
  expires_at: string | null
  hours_until_expiry: number | null
  patron_on_way: boolean
  patron_library_card: string | null
}

export interface ExpiringHoldsResponse {
  holds: ExpiringHold[]
  total_expiring: number
  generated_at: string
}

export interface MarkNotPickedUpResponse {
  hold_id: number
  status: string
  no_show_count: number
  next_hold_promoted: boolean
  next_hold?: { hold_id: number; patron_name: string; shelf_slot: string | null }
}

export type ViewMode = "pull-list" | "expiring" | "expired"


export interface ExpiredHold {
  hold_id: number
  item_id: number
  item_title: string
  item_author: string | null
  patron_name: string
  patron_initials: string
  shelf_slot: string | null
  expires_at: string | null
  patron_library_card: string | null
  no_show_count: number
}

export interface ShelfSlotUpdateResponse {
  hold_id: number
  shelf_slot: string | null
  message: string
}

export interface FulfillHoldResponse {
  hold_id: number
  status: string
  message: string
}

export interface PatronOnWayToggleResponse {
  hold_id: number
  patron_on_way: boolean
  message: string
}
