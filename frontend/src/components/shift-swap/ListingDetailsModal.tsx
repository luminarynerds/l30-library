/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Listing Details Modal
 *
 * Shows full details of a shift swap listing and allows claiming
 */

import React, { useState } from 'react'
import { Modal } from '../ui/Modal'
import { Listing } from '../../pages/ShiftSwapBoard'
import { useTranslation, getCurrentLocale } from '@/i18n'
import { parseDate } from '@/utils/format-utils'

export interface ClaimSubmitPayload {
  swap_shift_date?: string | null
  swap_shift_start_time?: string | null
  swap_shift_end_time?: string | null
  message?: string | null
}

interface Props {
  listing: Listing
  currentUserId?: number
  onClose: () => void
  onClaim: (listingId: number, claimData: ClaimSubmitPayload) => Promise<void>
  onWithdraw?: (listingId: number) => Promise<void>
  onRefresh: () => Promise<void>
}

export const ListingDetailsModal: React.FC<Props> = ({
  listing,
  currentUserId,
  onClose,
  onClaim,
  onWithdraw,
  onRefresh: _onRefresh,
}) => {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(false)
  const [withdrawing, setWithdrawing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showClaimForm, setShowClaimForm] = useState(false)
  const [claimData, setClaimData] = useState({
    swap_shift_date: '',
    swap_shift_start_time: '',
    swap_shift_end_time: '',
    message: '',
  })

  const isOwner =
    listing.is_owner === true ||
    (currentUserId !== undefined && listing.user_id === currentUserId)

  const formatDate = (dateStr: string) => {
    const date = parseDate(dateStr)
    if (date === null) return '-'
    return date.toLocaleDateString(getCurrentLocale(), {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })
  }

  const formatTime = (timeStr: string) => {
    const [hours = '0', minutes = '00'] = timeStr.split(':')
    const hour = parseInt(hours)
    const ampm = hour >= 12 ? 'PM' : 'AM'
    const displayHour = hour % 12 || 12
    return `${displayHour}:${minutes} ${ampm}`
  }

  const handleClaimChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target
    setClaimData({ ...claimData, [name]: value })
  }

  const handleSubmitClaim = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const payload: ClaimSubmitPayload = {
        swap_shift_date: claimData.swap_shift_date || null,
        swap_shift_start_time: claimData.swap_shift_start_time || null,
        swap_shift_end_time: claimData.swap_shift_end_time || null,
        message: claimData.message || null,
      }
      await onClaim(listing.id, payload)
      setShowClaimForm(false)
      onClose()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to claim shift')
    } finally {
      setLoading(false)
    }
  }

  const handleWithdraw = async () => {
    if (!onWithdraw) return
    setError(null)
    setWithdrawing(true)
    try {
      await onWithdraw(listing.id)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to withdraw listing')
    } finally {
      setWithdrawing(false)
    }
  }

  return (
    <Modal
      isOpen={true}
      onClose={onClose}
      title="Shift Details"
      size="lg"
    >
      {error && <div className="alert alert-error">{error}</div>}

      <div className="listing-details">
        <div className="detail-section">
          <h3>Shift Information</h3>
          <div className="detail-row">
            <span className="label">Type:</span>
            <span className="value">
              {listing.listing_type === 'giving_away' ? '📤 Offering' : '📥 Seeking'}
            </span>
          </div>
          <div className="detail-row">
            <span className="label">Date:</span>
            <span className="value">{formatDate(listing.shift_date)}</span>
          </div>
          <div className="detail-row">
            <span className="label">Time:</span>
            <span className="value">
              {formatTime(listing.shift_start_time)} - {formatTime(listing.shift_end_time)}
            </span>
          </div>
          <div className="detail-row">
            <span className="label">Shift Type:</span>
            <span className="value">{listing.shift_type.toUpperCase()}</span>
          </div>
          {listing.is_partial && listing.partial_description && (
            <div className="detail-row">
              <span className="label">Coverage:</span>
              <span className="value">{listing.partial_description}</span>
            </div>
          )}
          <div className="detail-row">
            <span className="label">Location:</span>
            <span className="value">{listing.branch_name}</span>
          </div>
          <div className="detail-row">
            <span className="label">Status:</span>
            <span className="value">{listing.status}</span>
          </div>
        </div>

        <div className="detail-section">
          <h3>Staff Member</h3>
          <div className="detail-row">
            <span className="label">Name:</span>
            <span className="value">{listing.user_name}</span>
          </div>
        </div>

        {listing.description && (
          <div className="detail-section">
            <h3>Notes</h3>
            <p>{listing.description}</p>
          </div>
        )}

        {listing.claims_count && listing.claims_count > 0 && (
          <div className="detail-section">
            <h3>Interest</h3>
            <p>{listing.claims_count} person{listing.claims_count > 1 ? 's' : ''} interested</p>
          </div>
        )}
      </div>

      {!showClaimForm && listing.status === 'open' && !isOwner && (
        <div className="action-section">
          <button
            className="btn btn-primary btn-lg"
            onClick={() => setShowClaimForm(true)}
          >
            {listing.listing_type === 'giving_away' ? "I'll Take It!" : 'I Can Help!'}
          </button>
        </div>
      )}

      {!showClaimForm && listing.status === 'open' && isOwner && onWithdraw && (
        <div className="action-section">
          <button
            className="btn btn-danger btn-lg"
            onClick={handleWithdraw}
            disabled={withdrawing}
          >
            {withdrawing ? 'Withdrawing...' : 'Withdraw Listing'}
          </button>
        </div>
      )}

      {showClaimForm && (
        <form onSubmit={handleSubmitClaim} className="claim-form">
          <h3>Claim This Shift</h3>

          {listing.listing_type === 'giving_away' && (
            <>
              <p className="form-help-text">
                If you're swapping, specify the shift you're offering in return:
              </p>
              <div className="form-group">
                <label htmlFor="swap_shift_date">Your Shift Date</label>
                <input
                  id="swap_shift_date"
                  type="date"
                  name="swap_shift_date"
                  value={claimData.swap_shift_date}
                  onChange={handleClaimChange}
                />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="swap_shift_start_time">Start Time</label>
                  <input
                    id="swap_shift_start_time"
                    type="time"
                    name="swap_shift_start_time"
                    value={claimData.swap_shift_start_time}
                    onChange={handleClaimChange}
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="swap_shift_end_time">End Time</label>
                  <input
                    id="swap_shift_end_time"
                    type="time"
                    name="swap_shift_end_time"
                    value={claimData.swap_shift_end_time}
                    onChange={handleClaimChange}
                  />
                </div>
              </div>
            </>
          )}

          <div className="form-group">
            <label htmlFor="message">{t('components.shiftSwap.listingDetails.messageToStaffMember')}</label>
            <textarea
              id="message"
              name="message"
              value={claimData.message}
              onChange={handleClaimChange}
              placeholder={t('components.shiftSwap.listingDetails.anyNotesAboutYourAvailability')}
              rows={3}
            />
          </div>

          <div className="form-actions">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setShowClaimForm(false)}
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading}
            >
              {loading ? 'Claiming...' : 'Submit Claim'}
            </button>
          </div>
        </form>
      )}
    </Modal>
  )
}

export default ListingDetailsModal
