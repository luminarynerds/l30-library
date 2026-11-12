/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import type { DatabaseCategory } from '../../api/databases-api'

export interface SubFormState {
  name: string
  category: DatabaseCategory
  vendor_id: string
  access_url: string
  subscription_start: string
  subscription_end: string
  annual_cost: string
  is_active: boolean
  is_featured: boolean
  notes: string
}

export interface ProxyConfig {
  id: number
  name: string
  proxy_type: string
  ezproxy_base_url?: string
  is_active: boolean
  is_default: boolean
}
