/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'
import FocusTrap from 'focus-trap-react'
import { X, CheckCircle, XCircle, MinusCircle } from 'lucide-react'
import type { VoteItem } from './VotingSection'

interface VotingDetailModalProps {
  vote: VoteItem
  onClose: () => void
}

export default function VotingDetailModal({
  vote,
  onClose,
}: VotingDetailModalProps): React.ReactElement {
  const totalVotes = (vote.votes_for || 0) + (vote.votes_against || 0) + (vote.votes_abstain || 0)
  const forPercent = totalVotes > 0 ? ((vote.votes_for || 0) / totalVotes) * 100 : 0
  const againstPercent = totalVotes > 0 ? ((vote.votes_against || 0) / totalVotes) * 100 : 0
  const abstainPercent = totalVotes > 0 ? ((vote.votes_abstain || 0) / totalVotes) * 100 : 0

  const votesFor = vote.votes_for || 0
  const votesAgainst = vote.votes_against || 0
  const isTie = votesFor === votesAgainst && totalVotes > 0
  const noVotes = totalVotes === 0
  const passed = votesFor > votesAgainst


  return (
    <FocusTrap active={true} focusTrapOptions={{ escapeDeactivates: true, onDeactivate: onClose }}>
      <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="vote-detail-title">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-lsc-white dark:bg-earth-800 border-b border-earth-200 dark:border-earth-700 p-6 flex items-center justify-between">
          <h2 id="vote-detail-title" className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
            Vote Details
          </h2>
          <button
            onClick={onClose}
            aria-label="Close vote details"
            className="p-2 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg transition-colors"
          >
            <X className="w-6 h-6 text-lsc-dark dark:text-lsc-cream" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Title and Status */}
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h3 className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                {vote.title}
              </h3>
              <span
                className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(
                  vote.status
                )}`}
              >
                {vote.status}
              </span>
            </div>
            {vote.description && (
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{vote.description}</p>
            )}
          </div>

          {/* Result Status */}
          {vote.status === 'closed' && (
            <div
              className={`p-4 rounded-lg ${
                noVotes
                  ? 'bg-earth-100 dark:bg-earth-900/30'
                  : isTie
                  ? 'bg-status-warning-100 dark:bg-status-warning-900/30'
                  : passed
                  ? 'bg-status-success-100 dark:bg-status-success-900/30'
                  : 'bg-status-danger-100 dark:bg-status-danger-900/30'
              }`}
            >
              <div className="flex items-center gap-2 mb-1">
                {noVotes ? (
                  <MinusCircle className="w-5 h-5 text-earth-600 dark:text-earth-400" />
                ) : isTie ? (
                  <MinusCircle className="w-5 h-5 text-status-warning-700 dark:text-status-warning-300" />
                ) : passed ? (
                  <CheckCircle className="w-5 h-5 text-status-success-700 dark:text-status-success-300" />
                ) : (
                  <XCircle className="w-5 h-5 text-status-danger-700 dark:text-status-danger-300" />
                )}
                <span
                  className={`font-semibold ${
                    noVotes
                      ? 'text-earth-600 dark:text-earth-300'
                      : isTie
                      ? 'text-status-warning-800 dark:text-status-warning-200'
                      : passed
                      ? 'text-status-success-800 dark:text-status-success-200'
                      : 'text-status-danger-800 dark:text-status-danger-200'
                  }`}
                >
                  {noVotes ? 'No votes cast' : isTie ? 'Tied' : passed ? 'Motion Passed' : 'Motion Failed'}
                </span>
              </div>
              <p
                className={`text-sm ${
                  noVotes
                    ? 'text-earth-600 dark:text-earth-400'
                    : isTie
                    ? 'text-status-warning-700 dark:text-status-warning-300'
                    : passed
                    ? 'text-status-success-700 dark:text-status-success-300'
                    : 'text-status-danger-700 dark:text-status-danger-300'
                }`}
              >
                {vote.votes_for || 0} votes for, {vote.votes_against || 0} votes against,{' '}
                {vote.votes_abstain || 0} abstentions
              </p>
            </div>
          )}

          {/* Vote Results */}
          <div className="space-y-4">
            <h4 className="font-semibold text-lsc-dark dark:text-lsc-cream">Vote Results</h4>

            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-status-success-700 dark:text-status-success-300">
                  For ({vote.votes_for || 0})
                </span>
                <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  {forPercent.toFixed(1)}%
                </span>
              </div>
              <div className="w-full bg-earth-200 dark:bg-earth-700 rounded-full h-3">
                <div
                  className="bg-status-success-600 h-3 rounded-full transition-all"
                  style={{ width: `${forPercent}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-status-danger-700 dark:text-status-danger-300">
                  Against ({vote.votes_against || 0})
                </span>
                <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  {againstPercent.toFixed(1)}%
                </span>
              </div>
              <div className="w-full bg-earth-200 dark:bg-earth-700 rounded-full h-3">
                <div
                  className="bg-status-danger-600 h-3 rounded-full transition-all"
                  style={{ width: `${againstPercent}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-status-warning-700 dark:text-status-warning-300">
                  Abstain ({vote.votes_abstain || 0})
                </span>
                <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  {abstainPercent.toFixed(1)}%
                </span>
              </div>
              <div className="w-full bg-earth-200 dark:bg-earth-700 rounded-full h-3">
                <div
                  className="bg-status-warning-600 h-3 rounded-full transition-all"
                  style={{ width: `${abstainPercent}%` }}
                />
              </div>
            </div>

            <div className="pt-2 border-t border-earth-200 dark:border-earth-700">
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                Total Votes: <span className="font-semibold">{totalVotes}</span>
              </p>
            </div>
          </div>

          {/* Dates */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-4 border-t border-earth-200 dark:border-earth-700">
            <div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                Created
              </p>
              <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                {new Date(vote.created_date).toLocaleDateString()}
              </p>
            </div>
            {vote.due_date && (
              <div>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  Due Date
                </p>
                <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                  {new Date(vote.due_date).toLocaleDateString()}
                </p>
              </div>
            )}
          </div>

          {/* Close Button */}
          <div className="pt-4 border-t border-earth-200 dark:border-earth-700">
            <button
              onClick={onClose}
            aria-label="Close vote details"
              className="w-full px-4 py-2 rounded-lg border border-earth-200 dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors font-medium"
            >
              Close
            </button>
          </div>
        </div>
      </div>
      </div>
    </FocusTrap>
  )
}

function getStatusColor(status: string) {
  switch (status) {
    case 'open':
      return 'bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light'
    case 'closed':
      return 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300'
    case 'pending':
      return 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300'
    default:
      return 'bg-earth-100 text-earth-800 dark:bg-earth-900/30 dark:text-earth-300'
  }
}
