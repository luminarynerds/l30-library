/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { WifiOff } from 'lucide-react'
import { useOnlineStatus } from '@/hooks/useServiceWorker'
import { useOfflineCheckout } from '@/hooks/useOfflineCheckout'
import { useAuth } from '@/contexts/AuthContext'

export default function FrontDeskOfflineChip() {
  const isOnline = useOnlineStatus()
  const { user } = useAuth()
  const staffId = user?.id?.toString() || ''
  const { queueStats } = useOfflineCheckout(staffId)
  const pending = queueStats.pending

  if (isOnline) return null

  const label =
    pending > 0
      ? `Offline · ${pending} action${pending === 1 ? '' : 's'} queued, will sync when back online`
      : 'Offline'

  return (
    <span
      role="status"
      aria-live="polite"
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-xs font-medium bg-status-warning-50 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-300 border border-status-warning-200 dark:border-status-warning-800"
    >
      <WifiOff className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
      {label}
    </span>
  )
}
