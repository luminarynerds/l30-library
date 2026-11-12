/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Shift Swap API Service
 *
 * Handles all API calls related to shift swapping
 */

import { api } from '@/lib/api-client'
import { API_BASE } from '@/api/types'

// Type definitions for Shift Swap API
interface QueryParams {
  [key: string]: string | number | boolean | undefined | null
}

interface ShiftListing {
  shift_id?: number
  original_date?: string
  original_start_time?: string
  original_end_time?: string
  reason?: string
  notes?: string
}

interface ShiftListingUpdate {
  notes?: string
  status?: string
}

interface ClaimData {
  message?: string | null
  swap_shift_date?: string | null
  swap_shift_start_time?: string | null
  swap_shift_end_time?: string | null
  proposed_trade_shift_id?: number
}

interface ApprovalData {
  approval_notes?: string
}

interface SwapPreferences {
  auto_approve_trusted?: boolean
  notification_email?: boolean
  notification_sms?: boolean
  min_reliability_score?: number
  blacklist_user_ids?: number[]
  wants_extra_hours?: boolean
  preferred_shift_types?: string[]
  preferred_branches?: number[]
  preferred_days_of_week?: string[]
  days_available?: string[]
  earliest_available_time?: string
  latest_available_time?: string
  max_extra_hours_per_week?: number
  max_consecutive_days?: number
  auto_claim_compatible?: boolean
  unavailable_dates?: string[]
  notes?: string
}

const buildQueryString = (params?: QueryParams): string => {
  if (!params) return ''
  const searchParams = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      searchParams.set(key, String(value))
    }
  })
  const qs = searchParams.toString()
  return qs ? `?${qs}` : ''
}

export const shiftSwapApi = {
  // Listings
  async getListings(params?: QueryParams) {
    return await api.get(`${API_BASE}/shift-swap/listings${buildQueryString(params)}`)
  },

  async getListing(listingId: number) {
    return await api.get(`${API_BASE}/shift-swap/listings/${listingId}`)
  },

  async createListing(data: ShiftListing) {
    return await api.post(`${API_BASE}/shift-swap/listings`, data)
  },

  async updateListing(listingId: number, data: ShiftListingUpdate) {
    return await api.put(`${API_BASE}/shift-swap/listings/${listingId}`, data)
  },

  async withdrawListing(listingId: number) {
    return await api.post(`${API_BASE}/shift-swap/listings/${listingId}/withdraw`)
  },

  // Claims
  async claimShift(listingId: number, data: ClaimData) {
    return await api.post(`${API_BASE}/shift-swap/claims`, {
      listing_id: listingId,
      ...data,
    })
  },

  async getListingClaims(listingId: number) {
    return await api.get(`${API_BASE}/shift-swap/listings/${listingId}/claims`)
  },

  async approveClaim(claimId: number, data?: ApprovalData) {
    return await api.post(
      `${API_BASE}/shift-swap/claims/${claimId}/approve`,
      data || {}
    )
  },

  async rejectClaim(claimId: number, reason: string) {
    return await api.post(`${API_BASE}/shift-swap/claims/${claimId}/reject`, {
      rejection_reason: reason,
    })
  },

  // Preferences
  async getPreferences() {
    return await api.get(`${API_BASE}/shift-swap/preferences`)
  },

  async createPreferences(data: SwapPreferences) {
    return await api.post(`${API_BASE}/shift-swap/preferences`, data)
  },

  async updatePreferences(data: Partial<SwapPreferences>) {
    return await api.put(`${API_BASE}/shift-swap/preferences`, data)
  },

  // Reliability Score
  async getReliability(userId?: number) {
    const endpoint = userId ? `${API_BASE}/shift-swap/reliability/${userId}` : `${API_BASE}/shift-swap/reliability`
    return await api.get(endpoint)
  },

  // Notifications
  async getNotifications(params?: QueryParams) {
    return await api.get(`${API_BASE}/shift-swap/notifications${buildQueryString(params)}`)
  },

  async markNotificationRead(notificationId: number) {
    return await api.put(`${API_BASE}/shift-swap/notifications/${notificationId}/read`, {})
  },

  // Matches
  async getMatches() {
    return await api.get(`${API_BASE}/shift-swap/matches`)
  },

  async acceptMatch(matchId: number) {
    return await api.post(`${API_BASE}/shift-swap/matches/${matchId}/accept`)
  },

  async rejectMatch(matchId: number) {
    return await api.post(`${API_BASE}/shift-swap/matches/${matchId}/reject`)
  },

  async runMatching() {
    return await api.post(`${API_BASE}/shift-swap/matches/run`)
  },

  // Dashboard
  async getDashboard() {
    return await api.get(`${API_BASE}/shift-swap/dashboard`)
  },
}