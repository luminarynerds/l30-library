/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
/**
 * Shift Swap Board
 *
 * Main page for staff to post and claim shift swaps.
 * Features:
 * - Post shifts to give away or pick up
 * - Filter by date, location, shift type
 * - One-click "I'll Take It" claim
 * - Partial shift coverage
 * - Standing "I want extra hours" preferences
 * - Match notifications when compatible swaps exist
 * - Karma/reliability score for swappers
 */

import React, { useState, useEffect, useCallback, useRef, type KeyboardEvent } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { shiftSwapApi } from '../api/shift-swap-api'
import ShiftSwapBoardView from '../components/shift-swap/ShiftSwapBoardView'
import CreateListingModal from '../components/shift-swap/CreateListingModal'
import ListingDetailsModal, { type ClaimSubmitPayload } from '../components/shift-swap/ListingDetailsModal'
import ShiftSwapNotifications from '../components/shift-swap/ShiftSwapNotifications'
import PreferencesPanel from '../components/shift-swap/PreferencesPanel'
import ReliabilityScore from '../components/shift-swap/ReliabilityScore'
import MatchesPanel from '../components/shift-swap/MatchesPanel'
import '../styles/shift-swap-board.css'
import { useTranslation } from '@/i18n'
import { AdminShell } from '../components/shells/AdminShell'

export interface Listing {
  id: number
  user_id: number
  branch_id: number
  listing_type: 'giving_away' | 'looking_for'
  shift_date: string
  shift_start_time: string
  shift_end_time: string
  shift_type: 'opening' | 'closing' | 'mid_day' | 'full_day' | 'partial'
  is_partial: boolean
  partial_description?: string
  status: 'open' | 'claimed' | 'completed' | 'withdrawn' | 'expired'
  description?: string
  created_at: string
  updated_at: string
  user_name?: string
  branch_name?: string
  claims_count?: number
  is_owner?: boolean
  has_claimed?: boolean
}

export interface ShiftSwapMatch {
  id: number
  giver_listing_id: number
  taker_listing_id: number
  compatibility_score: number
  status: 'pending_notification' | 'notified' | 'accepted' | 'rejected' | 'completed'
  notified_at?: string
  accepted_at?: string
  rejected_at?: string
  rejection_reason?: string
  created_at: string
  giver_listing?: Listing
  taker_listing?: Listing
}

interface Notification {
  id: number
  user_id: number
  notification_type: string
  title: string
  message: string
  is_read: boolean
  created_at: string
}

export const ShiftSwapBoard: React.FC = () => {
  const { t } = useTranslation()
  const { user } = useAuth()
  const [listings, setListings] = useState<Listing[]>([])
  const [matches, setMatches] = useState<ShiftSwapMatch[]>([])
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [selectedListing, setSelectedListing] = useState<Listing | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showListingDetails, setShowListingDetails] = useState(false)
  const [showPreferences, setShowPreferences] = useState(false)
  const [loading, setLoading] = useState(true)
  const [matchesLoading, setMatchesLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState<'board' | 'my-swaps' | 'matches'>('board')

  const TAB_IDS: Array<'board' | 'my-swaps' | 'matches'> = ['board', 'my-swaps', 'matches']
  const tabRefs = useRef<Record<string, HTMLButtonElement | null>>({})
  const onTablistKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    const idx = TAB_IDS.indexOf(tab)
    if (idx < 0) return
    let nextIdx: number | null = null
    if (e.key === 'ArrowRight') nextIdx = (idx + 1) % TAB_IDS.length
    else if (e.key === 'ArrowLeft') nextIdx = (idx - 1 + TAB_IDS.length) % TAB_IDS.length
    else if (e.key === 'Home') nextIdx = 0
    else if (e.key === 'End') nextIdx = TAB_IDS.length - 1
    if (nextIdx === null) return
    e.preventDefault()
    const nextId = TAB_IDS[nextIdx]
    if (!nextId) return
    setTab(nextId)
    requestAnimationFrame(() => {
      tabRefs.current[nextId]?.focus()
    })
  }

  // Filter states
  const [filterBranch, setFilterBranch] = useState<number | null>(null)
  const [filterType, setFilterType] = useState<'giving_away' | 'looking_for' | null>(null)
  const [filterShiftType, setFilterShiftType] = useState<string | null>(null)
  const [filterDateFrom, setFilterDateFrom] = useState<string>('')
  const [filterDateTo, setFilterDateTo] = useState<string>('')

  const loadListings = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const params: Record<string, string | number> = {}
      if (filterBranch) params.branch_id = filterBranch
      if (filterType) params.listing_type = filterType
      if (filterShiftType) params.shift_type = filterShiftType
      if (filterDateFrom) params.date_from = filterDateFrom
      if (filterDateTo) params.date_to = filterDateTo

      const response = await shiftSwapApi.getListings(params)
      setListings(response.listings)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load listings')
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
    } finally {
      setLoading(false)
    }
  }, [filterBranch, filterType, filterShiftType, filterDateFrom, filterDateTo])

  const loadNotifications = useCallback(async () => {
    try {
      const response = await shiftSwapApi.getNotifications()
      setNotifications(response.notifications)
    } catch (err: unknown) {
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
    }
  }, [])

  const loadMatches = useCallback(async () => {
    try {
      setMatchesLoading(true)
      const response = await shiftSwapApi.getMatches()
      setMatches(response.matches)
    } catch (err: unknown) {
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
    } finally {
      setMatchesLoading(false)
    }
  }, [])

  // Load listings
  useEffect(() => {
    loadListings()
    loadNotifications()
    const interval = setInterval(loadNotifications, 30000)
    return () => clearInterval(interval)
  }, [loadListings, loadNotifications])

  // Load matches when tab changes
  useEffect(() => {
    if (tab === 'matches') {
      loadMatches()
    }
  }, [tab, loadMatches])

  const handleCreateListing = async (data: Record<string, unknown>) => {
    try {
      await shiftSwapApi.createListing(data)
      setShowCreateModal(false)
      loadListings()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create listing')
    }
  }

  const handleClaimShift = async (listingId: number, claimData: ClaimSubmitPayload) => {
    try {
      await shiftSwapApi.claimShift(listingId, claimData)
      setShowListingDetails(false)
      setSelectedListing(null)
      loadListings()
      loadNotifications()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to claim shift')
    }
  }

  const handleQuickClaim = async (listing: Listing) => {
    try {
      await shiftSwapApi.claimShift(listing.id, {})
      loadListings()
      loadNotifications()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to claim shift')
    }
  }

  const handleWithdrawListing = async (listingId: number) => {
    if (!window.confirm('Withdraw this shift listing? Anyone who has claimed it will be notified.')) {
      return
    }
    try {
      await shiftSwapApi.withdrawListing(listingId)
      setShowListingDetails(false)
      setSelectedListing(null)
      loadListings()
      loadNotifications()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to withdraw listing')
    }
  }

  const handleListingClick = (listing: Listing) => {
    setSelectedListing(listing)
    setShowListingDetails(true)
  }

  const handleNotificationClick = async (notification: Notification) => {
    if (!notification.is_read) {
      try {
        await shiftSwapApi.markNotificationRead(notification.id)
        loadNotifications()
      } catch (err: unknown) {
        Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
      }
    }
    loadListings()
  }

  const handleAcceptMatch = async (matchId: number) => {
    try {
      await shiftSwapApi.acceptMatch(matchId)
      loadMatches()
      loadNotifications()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to accept match')
    }
  }

  const handleRejectMatch = async (matchId: number) => {
    try {
      await shiftSwapApi.rejectMatch(matchId)
      loadMatches()
      loadNotifications()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to reject match')
    }
  }

  const handleRunMatching = async () => {
    try {
      await shiftSwapApi.runMatching()
      loadMatches()
      loadNotifications()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to run matching')
    }
  }

  const myListings = listings.filter(l => l.user_id === user?.id && l.status !== 'completed')
  const availableListings = listings.filter(l => l.user_id !== user?.id && l.status === 'open')
  const activeMatches = matches.filter(m => m.status === 'notified' || m.status === 'pending_notification')

  return (

    <AdminShell title="Shift Swap Board">    <div className="shift-swap-board">
      <header className="board-header">
        <div className="header-actions">
          {user && (
            <>
              <ReliabilityScore userId={user.id} />
              <ShiftSwapNotifications
                notifications={notifications}
                onNotificationClick={handleNotificationClick}
              />
              <button
                className="btn btn-primary"
                onClick={() => setShowCreateModal(true)}
              >
                + Post Shift
              </button>
              <button
                className="btn btn-secondary"
                onClick={() => setShowPreferences(!showPreferences)}
              >
                Preferences
              </button>
            </>
          )}
        </div>
      </header>

      {error && (
        <div className="alert alert-error" role="alert">
          {error}
          <button onClick={() => setError(null)} className="close">
            &times;
          </button>
        </div>
      )}

      {showPreferences && <PreferencesPanel onClose={() => setShowPreferences(false)} />}

      <div className="board-tabs" role="tablist" aria-label="Shift swap views" onKeyDown={onTablistKeyDown}>
        <button
          ref={(el) => { tabRefs.current['board'] = el }}
          role="tab"
          id="shift-swap-tab-board"
          aria-selected={tab === 'board'}
          aria-controls="shift-swap-panel-board"
          tabIndex={tab === 'board' ? 0 : -1}
          className={`tab ${tab === 'board' ? 'active' : ''}`}
          onClick={() => setTab('board')}
        >
          All Shifts
        </button>
        <button
          ref={(el) => { tabRefs.current['my-swaps'] = el }}
          role="tab"
          id="shift-swap-tab-my-swaps"
          aria-selected={tab === 'my-swaps'}
          aria-controls="shift-swap-panel-my-swaps"
          tabIndex={tab === 'my-swaps' ? 0 : -1}
          className={`tab ${tab === 'my-swaps' ? 'active' : ''}`}
          onClick={() => setTab('my-swaps')}
        >
          My Swaps ({myListings.length})
        </button>
        <button
          ref={(el) => { tabRefs.current['matches'] = el }}
          role="tab"
          id="shift-swap-tab-matches"
          aria-selected={tab === 'matches'}
          aria-controls="shift-swap-panel-matches"
          tabIndex={tab === 'matches' ? 0 : -1}
          className={`tab ${tab === 'matches' ? 'active' : ''}`}
          onClick={() => setTab('matches')}
        >
          Matches {activeMatches.length > 0 && (
            <span className="tab-badge">{activeMatches.length}</span>
          )}
        </button>
      </div>

      {tab === 'board' && (
        <div role="tabpanel" id="shift-swap-panel-board" aria-labelledby="shift-swap-tab-board">
          <div className="filters">
            <div className="filter-group">
              <label htmlFor="filter-type">Listing Type:</label>
              <select
                id="filter-type"
                value={filterType || ''}
                onChange={(e) => setFilterType((e.target.value as 'giving_away' | 'looking_for') || null)}
              >
                <option value="">All</option>
                <option value="giving_away">Giving Away</option>
                <option value="looking_for">Looking For</option>
              </select>
            </div>

            <div className="filter-group">
              <label htmlFor="filter-shift-type">Shift Type:</label>
              <select
                id="filter-shift-type"
                value={filterShiftType || ''}
                onChange={(e) => setFilterShiftType(e.target.value || null)}
              >
                <option value="">All Types</option>
                <option value="opening">Opening</option>
                <option value="closing">Closing</option>
                <option value="mid_day">Mid-Day</option>
                <option value="full_day">Full Day</option>
                <option value="partial">Partial</option>
              </select>
            </div>

            <div className="filter-group">
              <label htmlFor="filter-branch">Location:</label>
              <select
                id="filter-branch"
                value={filterBranch || ''}
                onChange={(e) => setFilterBranch(e.target.value ? parseInt(e.target.value) : null)}
              >
                <option value="">All Locations</option>
                <option value="1">Main Branch</option>
                <option value="2">Downtown Branch</option>
                <option value="3">Westside Branch</option>
              </select>
            </div>

            <div className="filter-group">
              <label htmlFor="filter-date-from">Date From:</label>
              <input
                id="filter-date-from"
                type="date"
                value={filterDateFrom}
                onChange={(e) => setFilterDateFrom(e.target.value)}
              />
            </div>

            <div className="filter-group">
              <label htmlFor="filter-date-to">Date To:</label>
              <input
                id="filter-date-to"
                type="date"
                value={filterDateTo}
                onChange={(e) => setFilterDateTo(e.target.value)}
              />
            </div>

            <button className="btn btn-secondary" onClick={() => {
              setFilterBranch(null)
              setFilterType(null)
              setFilterShiftType(null)
              setFilterDateFrom('')
              setFilterDateTo('')
            }}>
              Clear Filters
            </button>
          </div>

          {loading ? (
            <div className="loading">Loading shifts...</div>
          ) : availableListings.length === 0 ? (
            <div className="empty-state">
              <p>{t('shiftSwapBoard.noShiftsAvailableForSwapping')}</p>
              <p className="text-muted">{t('shiftSwapBoard.checkBackLaterOrPost')}</p>
            </div>
          ) : (
            <ShiftSwapBoardView
              listings={availableListings}
              onListingClick={handleListingClick}
              onQuickClaim={handleQuickClaim}
              currentUserId={user?.id}
              isLoading={loading}
            />
          )}
        </div>
      )}

      {tab === 'my-swaps' && (
        <div role="tabpanel" id="shift-swap-panel-my-swaps" aria-labelledby="shift-swap-tab-my-swaps" className="my-swaps-section">
          {myListings.length === 0 ? (
            <div className="empty-state">
              <p>{t('shiftSwapBoard.youHavenTPostedAny')}</p>
              <button
                className="btn btn-primary"
                onClick={() => setShowCreateModal(true)}
              >
                Post Your First Shift
              </button>
            </div>
          ) : (
            <ShiftSwapBoardView
              listings={myListings}
              onListingClick={handleListingClick}
              onWithdraw={handleWithdrawListing}
              currentUserId={user?.id}
              isLoading={loading}
            />
          )}
        </div>
      )}

      {tab === 'matches' && (
        <div role="tabpanel" id="shift-swap-panel-matches" aria-labelledby="shift-swap-tab-matches">
          <MatchesPanel
            matches={matches}
            loading={matchesLoading}
            onAccept={handleAcceptMatch}
            onReject={handleRejectMatch}
            onRunMatching={handleRunMatching}
            onRefresh={loadMatches}
          />
        </div>
      )}

      {showCreateModal && (
        <CreateListingModal
          onClose={() => setShowCreateModal(false)}
          onSubmit={handleCreateListing}
        />
      )}

      {showListingDetails && selectedListing && (
        <ListingDetailsModal
          listing={selectedListing}
          currentUserId={user?.id}
          onClose={() => {
            setShowListingDetails(false)
            setSelectedListing(null)
          }}
          onClaim={handleClaimShift}
          onWithdraw={handleWithdrawListing}
          onRefresh={loadListings}
        />
      )}
    </div>
  </AdminShell>
  )
}

export default ShiftSwapBoard
