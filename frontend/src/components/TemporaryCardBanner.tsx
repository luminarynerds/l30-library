/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'

export default function TemporaryCardBanner(): React.ReactElement | null {
  const { user } = useAuth()
  const [now] = useState(() => Date.now())

  if (!user || user.card_type !== 'temporary') return null

  const trialExpired = user.card_trial_expires_at
    ? new Date(user.card_trial_expires_at) <= new Date(now)
    : false

  const daysLeft = user.card_trial_expires_at
    ? Math.max(0, Math.ceil((new Date(user.card_trial_expires_at).getTime() - now) / (1000 * 60 * 60 * 24)))
    : 0

  return (
    <div
      className={`px-4 py-3 rounded-lg mb-4 ${
        trialExpired
          ? 'bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800'
          : 'bg-status-info-50 dark:bg-status-info-900/20 border border-status-info-200 dark:border-status-info-800'
      }`}
      role="status"
      aria-live="polite"
    >
      {trialExpired ? (
        <p className="text-sm text-status-warning-800 dark:text-status-warning-200">
          Your temporary card has expired. Visit the library to get a full card and access everything.
        </p>
      ) : (
        <p className="text-sm text-status-info-800 dark:text-status-info-200">
          {daysLeft === 1
            ? 'Your temporary card expires tomorrow.'
            : `Your temporary card expires in ${daysLeft} days.`}
          {' '}Visit the library to get your full card.
        </p>
      )}
    </div>
  )
}
