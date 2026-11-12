/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Create Listing Modal
 *
 * Modal for staff to post a new shift swap listing
 */

import React, { useState } from 'react'
import { Modal } from '../ui/Modal'
import { useTranslation} from '@/i18n'

interface Props {
  onClose: () => void
  onSubmit: (data: { branch_id: number; listing_type: string; shift_date: string; shift_start_time: string; shift_end_time: string; shift_type: string; is_partial: boolean; partial_description: string; description: string; expires_at: string }) => Promise<void>
}

export const CreateListingModal: React.FC<Props> = ({ onClose, onSubmit }) => {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [formData, setFormData] = useState({
    branch_id: '',
    listing_type: 'giving_away',
    shift_date: '',
    shift_start_time: '',
    shift_end_time: '',
    shift_type: 'opening',
    is_partial: false,
    partial_description: '',
    description: '',
  })

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target
    const checkInput = e.target as HTMLInputElement
    setFormData({
      ...formData,
      [name]: type === 'checkbox' ? checkInput.checked : value,
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      // Set expiration to 30 days from now
      const expiresAt = new Date()
      expiresAt.setDate(expiresAt.getDate() + 30)

      await onSubmit({
        ...formData,
        branch_id: parseInt(formData.branch_id),
        expires_at: expiresAt.toISOString(),
      })
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create listing')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal
      isOpen={true}
      onClose={onClose}
      title={t('components.shiftSwap.createListing.postAShiftSwap')}
    >
      <form onSubmit={handleSubmit} className="form">
        {error && <div className="alert alert-error">{error}</div>}

        <div className="form-group">
          <label htmlFor="listing_type">I want to...</label>
          <select
            id="listing_type"
            name="listing_type"
            value={formData.listing_type}
            onChange={handleChange}
            required
          >
            <option value="giving_away">{t('components.shiftSwap.createListing.giveAwayAShift')}</option>
            <option value="looking_for">Find Someone's Shift</option>
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="branch_id">Location *</label>
          <select
            id="branch_id"
            name="branch_id"
            value={formData.branch_id}
            onChange={handleChange}
            required
          >
            <option value="">Select a branch</option>
            <option value="1">Main Branch</option>
            <option value="2">Downtown Branch</option>
            <option value="3">Westside Branch</option>
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="shift_date">Shift Date *</label>
          <input
            id="shift_date"
            type="date"
            name="shift_date"
            value={formData.shift_date}
            onChange={handleChange}
            required
          />
        </div>

        <div className="form-row">
          <div className="form-group">
            <label htmlFor="shift_start_time">Start Time *</label>
            <input
              id="shift_start_time"
              type="time"
              name="shift_start_time"
              value={formData.shift_start_time}
              onChange={handleChange}
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="shift_end_time">End Time *</label>
            <input
              id="shift_end_time"
              type="time"
              name="shift_end_time"
              value={formData.shift_end_time}
              onChange={handleChange}
              required
            />
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="shift_type">Shift Type *</label>
          <select
            id="shift_type"
            name="shift_type"
            value={formData.shift_type}
            onChange={handleChange}
            required
          >
            <option value="opening">Opening Shift</option>
            <option value="closing">Closing Shift</option>
            <option value="mid_day">Mid-Day Shift</option>
            <option value="full_day">Full Day</option>
            <option value="partial">Partial Coverage</option>
          </select>
        </div>

        <div className="form-group checkbox">
          <input
            id="is_partial"
            type="checkbox"
            name="is_partial"
            checked={formData.is_partial}
            onChange={handleChange}
          />
          <label htmlFor="is_partial">{t('components.shiftSwap.createListing.thisIsPartialCoverage')}</label>
        </div>

        {formData.is_partial && (
          <div className="form-group">
            <label htmlFor="partial_description">{t('components.shiftSwap.createListing.coverageDetailsEGPm')}</label>
            <input
              id="partial_description"
              type="text"
              name="partial_description"
              value={formData.partial_description}
              onChange={handleChange}
              placeholder={t('placeholder.shift-swap.egCover25pmIll')}
            />
          </div>
        )}

        <div className="form-group">
          <label htmlFor="description">Additional Notes</label>
          <textarea
            id="description"
            name="description"
            value={formData.description}
            onChange={handleChange}
            placeholder={t('components.shiftSwap.createListing.anySpecialNotesOrPreferences')}
            rows={3}
          />
        </div>

        <div className="modal-actions">
          <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? 'Posting...' : 'Post Shift'}
          </button>
        </div>
      </form>
    </Modal>
  )
}

export default CreateListingModal
