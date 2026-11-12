/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
/**
 * Reliability Score
 *
 * Displays user's shift swap karma/reliability score
 */

import React, { useState, useEffect } from 'react'
import { shiftSwapApi } from '../../api/shift-swap-api'

interface Props {
  userId: number
}

interface ScoreData {
  reliability_score: number
  completion_rate: number
  total_completed_swaps: number
  total_swap_claims: number
  called_out_after_swap_count: number
}

export const ReliabilityScore: React.FC<Props> = ({ userId }) => {
  const [score, setScore] = useState<ScoreData | null>(null)
  const [loading, setLoading] = useState(true)
  const [showTooltip, setShowTooltip] = useState(false)

  const loadScore = async () => {
    try {
      setLoading(true)
      const data = await shiftSwapApi.getReliability(userId)
      setScore(data)
    } catch (err: unknown) {
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
    } finally {
      setLoading(false)
    }
  }


  useEffect(() => {
    loadScore()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId])

  if (loading) {
    return <div className="reliability-score loading">Loading...</div>
  }

  if (!score) {
    return null
  }

  const getScoreColor = (score: number) => {
    if (score >= 90) return '#27AE60' // Green
    if (score >= 75) return '#F39C12' // Orange
    if (score >= 50) return '#E67E22' // Dark Orange
    return '#E74C3C' // Red
  }

  const getScoreBadge = (score: number) => {
    if (score >= 90) return '⭐⭐⭐ Excellent'
    if (score >= 75) return '⭐⭐ Good'
    if (score >= 50) return '⭐ Fair'
    return '⚠️ Low'
  }

  return (
    <div className="reliability-score">
      <div
        className="score-button"
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
      >
        <span
          className="score-circle"
          style={{ backgroundColor: getScoreColor(score.reliability_score) }}
        >
          {Math.round(score.reliability_score)}
        </span>
        <span className="score-label">Reliability</span>
      </div>

      {showTooltip && (
        <div className="score-tooltip">
          <div className="tooltip-content">
            <h4>{getScoreBadge(score.reliability_score)}</h4>
            <ul>
              <li>Completed swaps: {score.total_completed_swaps}</li>
              <li>Completion rate: {Math.round(score.completion_rate)}%</li>
              <li>Claims: {score.total_swap_claims}</li>
              {score.called_out_after_swap_count > 0 && (
                <li className="warning">
                  Called out: {score.called_out_after_swap_count}
                </li>
              )}
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}

export default ReliabilityScore
