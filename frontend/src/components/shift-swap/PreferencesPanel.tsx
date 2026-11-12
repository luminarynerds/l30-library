/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Preferences Panel
 *
 * Allows staff to manage their shift swap preferences
 */

import React, { useState, useEffect } from 'react'
import { shiftSwapApi } from '../../api/shift-swap-api'
import { useTranslation} from '@/i18n'
import FocusTrap from 'focus-trap-react'

interface Props {
  onClose: () => void
}

export const PreferencesPanel: React.FC<Props> = ({ onClose }) => {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [preferences, setPreferences] = useState({
    wants_extra_hours: false,
    preferred_shift_types: [] as string[],
    preferred_branches: [] as number[],
    preferred_days_of_week: [] as string[],
    days_available: [] as string[],
    earliest_available_time: '',
    latest_available_time: '',
    max_extra_hours_per_week: 10,
    max_consecutive_days: 5,
    auto_claim_compatible: false,
    notify_on_new_matches: true,
    notes: '',
  })

  const daysOfWeek = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
  const shiftTypes = ['opening', 'closing', 'mid_day', 'full_day', 'partial']

  const loadPreferences = async () => {
    try {
      setLoading(true)
      const data = await shiftSwapApi.getPreferences()
      setPreferences(data)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load preferences')
    } finally {
      setLoading(false)
    }
  }


  useEffect(() => {
    loadPreferences()
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSaving(true)

    try {
      await shiftSwapApi.updatePreferences(preferences)
      alert('Preferences saved!')
      onClose()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to save preferences')
    } finally {
      setSaving(false)
    }
  }

  const toggleArray = <T extends string | number>(array: T[], value: T): T[] => {
    if (array.includes(value)) {
      return array.filter(item => item !== value)
    } else {
      return [...array, value]
    }
  }

  if (loading) {
    return (
      <div className="preferences-panel-overlay" onClick={onClose} onKeyDown={(e) => { if (e.key === 'Escape') onClose() }} role="presentation">
        <FocusTrap active={true} focusTrapOptions={{ escapeDeactivates: false, allowOutsideClick: true, returnFocusOnDeactivate: true, fallbackFocus: () => document.body }}>
        {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events */}
        <div className="preferences-panel" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true" aria-label={t('aria.shift-swap.shiftSwapPreferences')}>
          <div className="loading" role="status">Loading preferences...</div>
        </div>
        </FocusTrap>
      </div>
    )
  }

  return (
    <div className="preferences-panel-overlay" onClick={onClose} onKeyDown={(e) => { if (e.key === 'Escape') onClose() }} role="presentation">
      <FocusTrap active={true} focusTrapOptions={{ escapeDeactivates: false, allowOutsideClick: true, returnFocusOnDeactivate: true, fallbackFocus: () => document.body }}>
      {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events */}
      <div className="preferences-panel" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true" aria-labelledby="preferences-title">
        <header className="panel-header">
          <h2 id="preferences-title">Shift Swap Preferences</h2>
          <button className="close-btn" onClick={onClose} aria-label={t('aria.events.closePreferences')}>×</button>
        </header>

        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleSubmit} className="preferences-form">
          <div className="form-section">
            <h3>Extra Hours</h3>
            <div className="form-group checkbox">
              <input
                id="wants_extra_hours"
                type="checkbox"
                checked={preferences.wants_extra_hours}
                onChange={(e) => setPreferences({
                  ...preferences,
                  wants_extra_hours: e.target.checked
                })}
              />
              <label htmlFor="wants_extra_hours">{t('components.shiftSwap.preferencesPanel.iWantToPickUp')}</label>
            </div>

            {preferences.wants_extra_hours && (
              <>
                <div className="form-row">
                  <div className="form-group">
                    <label htmlFor="max_extra_hours">{t('components.shiftSwap.preferencesPanel.maxHoursPerWeek')}</label>
                    <input
                      id="max_extra_hours"
                      type="number"
                      min="1"
                      max="40"
                      value={preferences.max_extra_hours_per_week}
                      onChange={(e) => setPreferences({
                        ...preferences,
                        max_extra_hours_per_week: parseInt(e.target.value)
                      })}
                    />
                  </div>
                  <div className="form-group">
                    <label htmlFor="max_consecutive">Max consecutive days:</label>
                    <input
                      id="max_consecutive"
                      type="number"
                      min="1"
                      max="7"
                      value={preferences.max_consecutive_days}
                      onChange={(e) => setPreferences({
                        ...preferences,
                        max_consecutive_days: parseInt(e.target.value)
                      })}
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label>Preferred Days:</label>
                  <div className="checkbox-group">
                    {daysOfWeek.map(day => (
                      <label key={day} className="checkbox-inline">
                        <input
                          type="checkbox"
                          checked={preferences.days_available.includes(day)}
                          onChange={(_e) => setPreferences({
                            ...preferences,
                            days_available: toggleArray(preferences.days_available, day)
                          })}
                        />
                        {day}
                      </label>
                    ))}
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label htmlFor="earliest_time">Earliest time:</label>
                    <input
                      id="earliest_time"
                      type="time"
                      value={preferences.earliest_available_time}
                      onChange={(e) => setPreferences({
                        ...preferences,
                        earliest_available_time: e.target.value
                      })}
                    />
                  </div>
                  <div className="form-group">
                    <label htmlFor="latest_time">Latest time:</label>
                    <input
                      id="latest_time"
                      type="time"
                      value={preferences.latest_available_time}
                      onChange={(e) => setPreferences({
                        ...preferences,
                        latest_available_time: e.target.value
                      })}
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label>Preferred Shift Types:</label>
                  <div className="checkbox-group">
                    {shiftTypes.map(type => (
                      <label key={type} className="checkbox-inline">
                        <input
                          type="checkbox"
                          checked={preferences.preferred_shift_types.includes(type)}
                          onChange={(_e) => setPreferences({
                            ...preferences,
                            preferred_shift_types: toggleArray(preferences.preferred_shift_types, type)
                          })}
                        />
                        {type}
                      </label>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>

          <div className="form-section">
            <h3>Notifications</h3>
            <div className="form-group checkbox">
              <input
                id="notify_matches"
                type="checkbox"
                checked={preferences.notify_on_new_matches}
                onChange={(e) => setPreferences({
                  ...preferences,
                  notify_on_new_matches: e.target.checked
                })}
              />
              <label htmlFor="notify_matches">{t('components.shiftSwap.preferencesPanel.notifyMeWhenCompatibleSwaps')}</label>
            </div>

            <div className="form-group checkbox">
              <input
                id="auto_claim"
                type="checkbox"
                checked={preferences.auto_claim_compatible}
                onChange={(e) => setPreferences({
                  ...preferences,
                  auto_claim_compatible: e.target.checked
                })}
              />
              <label htmlFor="auto_claim">{t('components.shiftSwap.preferencesPanel.automaticallyClaimCompatibleSwaps')}</label>
            </div>
          </div>

          <div className="form-section">
            <div className="form-group">
              <label htmlFor="notes">Additional Notes:</label>
              <textarea
                id="notes"
                value={preferences.notes}
                onChange={(e) => setPreferences({
                  ...preferences,
                  notes: e.target.value
                })}
                placeholder={t('components.shiftSwap.preferencesPanel.anyOtherPreferencesOrNotes')}
                rows={3}
              />
            </div>
          </div>

          <div className="panel-actions">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onClose}
              disabled={saving}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={saving}
            >
              {saving ? 'Saving...' : 'Save Preferences'}
            </button>
          </div>
        </form>
      </div>
      </FocusTrap>
    </div>
  )
}

export default PreferencesPanel
