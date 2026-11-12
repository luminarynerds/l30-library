/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Shift Swap Board View
 *
 * Displays shift swap listings in a grid with one-click claim support
 */

import React, { useState } from 'react'
import { Listing } from '../../pages/ShiftSwapBoard'
import { parseDate } from '@/utils/format-utils'
import { getCurrentLocale } from '@/i18n'

interface Props {
  listings: Listing[]
  onListingClick: (listing: Listing) => void
  onQuickClaim?: (listing: Listing) => Promise<void>
  onWithdraw?: (listingId: number) => Promise<void>
  currentUserId?: number
  isLoading?: boolean
}

export const ShiftSwapBoardView: React.FC<Props> = ({
  listings,
  onListingClick,
  onQuickClaim,
  onWithdraw,
  currentUserId,
  isLoading: _isLoading = false,
}) => {
  const [claimingId, setClaimingId] = useState<number | null>(null)
  const [withdrawingId, setWithdrawingId] = useState<number | null>(null)

  const formatDate = (dateStr: string) => {
    const date = parseDate(dateStr)
    if (date === null) return '-'
    return date.toLocaleDateString(getCurrentLocale(), { weekday: 'short', month: 'short', day: 'numeric' })
  }

  const formatTime = (timeStr: string) => {
    const [hours = '0', minutes = '00'] = timeStr.split(':')
    const hour = parseInt(hours)
    const ampm = hour >= 12 ? 'PM' : 'AM'
    const displayHour = hour % 12 || 12
    return `${displayHour}:${minutes} ${ampm}`
  }

  const getShiftTypeColor = (type: string) => {
    switch (type) {
      case 'opening': return '#FF6B6B'
      case 'closing': return '#4ECDC4'
      case 'mid_day': return '#95E1D3'
      case 'full_day': return '#6C5CE7'
      case 'partial': return '#FFE66D'
      default: return '#999'
    }
  }

  const getShiftTypeLabel = (type: string) => {
    switch (type) {
      case 'opening': return 'Opening'
      case 'closing': return 'Closing'
      case 'mid_day': return 'Mid-Day'
      case 'full_day': return 'Full Day'
      case 'partial': return 'Partial'
      default: return type
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'open': return <span className="badge badge-green">Open</span>
      case 'claimed': return <span className="badge badge-yellow">Claimed</span>
      case 'completed': return <span className="badge badge-blue">Completed</span>
      case 'withdrawn': return <span className="badge badge-gray">Withdrawn</span>
      case 'expired': return <span className="badge badge-red">Expired</span>
      default: return null
    }
  }

  const handleQuickClaim = async (e: React.MouseEvent, listing: Listing) => {
    e.stopPropagation()
    if (!onQuickClaim || claimingId) return

    setClaimingId(listing.id)
    try {
      await onQuickClaim(listing)
    } finally {
      setClaimingId(null)
    }
  }

  const handleWithdraw = async (e: React.MouseEvent, listing: Listing) => {
    e.stopPropagation()
    if (!onWithdraw || withdrawingId) return

    setWithdrawingId(listing.id)
    try {
      await onWithdraw(listing.id)
    } finally {
      setWithdrawingId(null)
    }
  }

  return (
    <div className="shift-swap-board-view">
      <div className="listings-grid">
        {listings.map((listing) => (
          <div
            key={listing.id}
            className="listing-card"
            onClick={() => onListingClick(listing)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                onListingClick(listing)
              }
            }}
          >
            <div className="card-header">
              <div className="shift-type-badge" style={{ backgroundColor: getShiftTypeColor(listing.shift_type) }}>
                {getShiftTypeLabel(listing.shift_type)}
              </div>
              <div className="listing-type-badge">
                {listing.listing_type === 'giving_away' ? 'Offering' : 'Seeking'}
              </div>
            </div>

            <div className="card-body">
              <div className="date-time">
                <span className="date">{formatDate(listing.shift_date)}</span>
                <span className="time">
                  {formatTime(listing.shift_start_time)} - {formatTime(listing.shift_end_time)}
                </span>
              </div>

              {listing.is_partial && listing.partial_description && (
                <div className="partial-info">
                  <small>Partial: {listing.partial_description}</small>
                </div>
              )}

              <div className="branch-info">
                <span className="branch-name">{listing.branch_name || 'Branch'}</span>
              </div>

              {listing.description && (
                <p className="description">{listing.description.substring(0, 100)}</p>
              )}

              <div className="staff-info">
                <span className="staff-name">{listing.user_name || 'Staff Member'}</span>
              </div>
            </div>

            <div className="card-footer">
              <div className="status">
                {getStatusBadge(listing.status)}
              </div>
              {(() => {
                const isOwner = currentUserId !== undefined && listing.user_id === currentUserId
                if (isOwner) {
                  return onWithdraw && listing.status === 'open' ? (
                    <button
                      className="btn btn-sm btn-danger"
                      onClick={(e) => handleWithdraw(e, listing)}
                      disabled={withdrawingId === listing.id}
                    >
                      {withdrawingId === listing.id ? 'Withdrawing...' : 'Withdraw'}
                    </button>
                  ) : null
                }
                if (listing.status !== 'open' || !onQuickClaim) return null
                if (listing.listing_type === 'giving_away') {
                  return (
                    <button
                      className="btn btn-sm btn-take-it"
                      onClick={(e) => handleQuickClaim(e, listing)}
                      disabled={claimingId === listing.id}
                    >
                      {claimingId === listing.id ? 'Claiming...' : "I'll Take It"}
                    </button>
                  )
                }
                return (
                  <button
                    className="btn btn-sm btn-help"
                    onClick={(e) => handleQuickClaim(e, listing)}
                    disabled={claimingId === listing.id}
                  >
                    {claimingId === listing.id ? 'Claiming...' : 'I Can Help'}
                  </button>
                )
              })()}
              {listing.claims_count && listing.claims_count > 0 && (
                <span className="claims-badge">{listing.claims_count} claim{listing.claims_count > 1 ? 's' : ''}</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default ShiftSwapBoardView
