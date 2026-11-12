/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Matches Panel
 *
 * Displays system-generated matches between compatible shift swap listings.
 * Users can accept or reject matches, and trigger on-demand matching.
 */

import React from 'react'
import { ShiftSwapMatch, Listing } from '../../pages/ShiftSwapBoard'
import { useTranslation, getCurrentLocale } from '@/i18n'
import { parseDate } from '@/utils/format-utils'

interface Props {
  matches: ShiftSwapMatch[]
  loading: boolean
  onAccept: (matchId: number) => Promise<void>
  onReject: (matchId: number) => Promise<void>
  onRunMatching: () => Promise<void>
  onRefresh: () => void
}

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

const getCompatibilityColor = (score: number) => {
  if (score >= 80) return '#27AE60'
  if (score >= 60) return '#F39C12'
  return '#E74C3C'
}

const getCompatibilityLabel = (score: number) => {
  if (score >= 80) return 'Excellent Match'
  if (score >= 60) return 'Good Match'
  return 'Possible Match'
}

const getStatusLabel = (status: string) => {
  switch (status) {
    case 'pending_notification': return 'New'
    case 'notified': return 'Pending'
    case 'accepted': return 'Accepted'
    case 'rejected': return 'Declined'
    case 'completed': return 'Completed'
    default: return status
  }
}

const getStatusClass = (status: string) => {
  switch (status) {
    case 'pending_notification':
    case 'notified': return 'badge-yellow'
    case 'accepted': return 'badge-green'
    case 'rejected': return 'badge-red'
    case 'completed': return 'badge-blue'
    default: return 'badge-gray'
  }
}

const ListingSummary: React.FC<{ listing?: Listing | undefined; label: string }> = ({ listing, label }) => {
  if (!listing) return <div className="match-listing-summary">No listing data</div>

  return (
    <div className="match-listing-summary">
      <div className="match-listing-label">{label}</div>
      <div className="match-listing-date">{formatDate(listing.shift_date)}</div>
      <div className="match-listing-time">
        {formatTime(listing.shift_start_time)} - {formatTime(listing.shift_end_time)}
      </div>
      <div className="match-listing-type">{listing.shift_type.replace('_', ' ')}</div>
      {listing.branch_name && (
        <div className="match-listing-branch">{listing.branch_name}</div>
      )}
      {listing.is_partial && listing.partial_description && (
        <div className="match-listing-partial">Partial: {listing.partial_description}</div>
      )}
    </div>
  )
}

export const MatchesPanel: React.FC<Props> = ({
  matches,
  loading,
  onAccept,
  onReject,
  onRunMatching,
  onRefresh,
}) => {
  const { t } = useTranslation()
  const [runningMatch, setRunningMatch] = React.useState(false)
  const [actionInProgress, setActionInProgress] = React.useState<number | null>(null)

  const activeMatches = matches.filter(m => m.status === 'notified' || m.status === 'pending_notification')
  const acceptedMatches = matches.filter(m => m.status === 'accepted')
  const pastMatches = matches.filter(m => m.status === 'rejected' || m.status === 'completed')

  const handleRunMatching = async () => {
    setRunningMatch(true)
    try {
      await onRunMatching()
    } finally {
      setRunningMatch(false)
    }
  }

  const handleAccept = async (matchId: number) => {
    setActionInProgress(matchId)
    try {
      await onAccept(matchId)
    } finally {
      setActionInProgress(null)
    }
  }

  const handleReject = async (matchId: number) => {
    setActionInProgress(matchId)
    try {
      await onReject(matchId)
    } finally {
      setActionInProgress(null)
    }
  }

  if (loading) {
    return (
      <div className="matches-section">
        <div className="loading">Finding compatible swaps...</div>
      </div>
    )
  }

  return (
    <div className="matches-section">
      <div className="matches-header">
        <p className="matches-description">
          The system automatically finds compatible swap opportunities based on your listings and preferences.
        </p>
        <div className="matches-actions">
          <button
            className="btn btn-primary"
            onClick={handleRunMatching}
            disabled={runningMatch}
          >
            {runningMatch ? 'Finding Matches...' : 'Find New Matches'}
          </button>
          <button className="btn btn-secondary" onClick={onRefresh}>
            Refresh
          </button>
        </div>
      </div>

      {activeMatches.length > 0 && (
        <div className="matches-group">
          <h3>Active Matches ({activeMatches.length})</h3>
          <div className="matches-list">
            {activeMatches.map((match) => (
              <div key={match.id} className="match-card">
                <div className="match-card-header">
                  <div
                    className="compatibility-score"
                    style={{ backgroundColor: getCompatibilityColor(match.compatibility_score) }}
                  >
                    {Math.round(match.compatibility_score)}%
                  </div>
                  <span className="compatibility-label">
                    {getCompatibilityLabel(match.compatibility_score)}
                  </span>
                  <span className={`badge ${getStatusClass(match.status)}`}>
                    {getStatusLabel(match.status)}
                  </span>
                </div>

                <div className="match-card-body">
                  <div className="match-listings">
                    <ListingSummary listing={match.giver_listing} label="Offering" />
                    <div className="match-arrow">
                      <span className="arrow-icon" aria-hidden="true">&harr;</span>
                    </div>
                    <ListingSummary listing={match.taker_listing} label="Seeking" />
                  </div>
                </div>

                <div className="match-card-footer">
                  <button
                    className="btn btn-sm btn-accept"
                    onClick={() => handleAccept(match.id)}
                    disabled={actionInProgress === match.id}
                  >
                    {actionInProgress === match.id ? 'Processing...' : 'Accept Match'}
                  </button>
                  <button
                    className="btn btn-sm btn-reject"
                    onClick={() => handleReject(match.id)}
                    disabled={actionInProgress === match.id}
                  >
                    Decline
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {acceptedMatches.length > 0 && (
        <div className="matches-group">
          <h3>Accepted Matches ({acceptedMatches.length})</h3>
          <div className="matches-list">
            {acceptedMatches.map((match) => (
              <div key={match.id} className="match-card match-card-accepted">
                <div className="match-card-header">
                  <div
                    className="compatibility-score"
                    style={{ backgroundColor: getCompatibilityColor(match.compatibility_score) }}
                  >
                    {Math.round(match.compatibility_score)}%
                  </div>
                  <span className={`badge ${getStatusClass(match.status)}`}>
                    {getStatusLabel(match.status)}
                  </span>
                </div>
                <div className="match-card-body">
                  <div className="match-listings">
                    <ListingSummary listing={match.giver_listing} label="Offering" />
                    <div className="match-arrow">
                      <span className="arrow-icon" aria-hidden="true">&harr;</span>
                    </div>
                    <ListingSummary listing={match.taker_listing} label="Seeking" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {pastMatches.length > 0 && (
        <div className="matches-group">
          <h3>Past Matches ({pastMatches.length})</h3>
          <div className="matches-list">
            {pastMatches.map((match) => (
              <div key={match.id} className="match-card match-card-past">
                <div className="match-card-header">
                  <div
                    className="compatibility-score compatibility-score-faded"
                    style={{ backgroundColor: getCompatibilityColor(match.compatibility_score) }}
                  >
                    {Math.round(match.compatibility_score)}%
                  </div>
                  <span className={`badge ${getStatusClass(match.status)}`}>
                    {getStatusLabel(match.status)}
                  </span>
                </div>
                <div className="match-card-body">
                  <div className="match-listings">
                    <ListingSummary listing={match.giver_listing} label="Offering" />
                    <div className="match-arrow">
                      <span className="arrow-icon" aria-hidden="true">&harr;</span>
                    </div>
                    <ListingSummary listing={match.taker_listing} label="Seeking" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {matches.length === 0 && (
        <div className="empty-state">
          <p>{t('components.shiftSwap.matchesPanel.noMatchesFoundYet')}</p>
          <p className="text-muted">
            Post a shift listing, then click "Find New Matches" to discover compatible swaps.
          </p>
        </div>
      )}
    </div>
  )
}

export default MatchesPanel
