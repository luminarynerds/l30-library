/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useCallback, useEffect } from 'react'
import { Bookmark } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { useReadingStatus } from '@/hooks/useReadingStatus'
import { useShelfStatusMap } from '@/hooks/useShelfStatusMap'
import { useUnifiedAccessibility } from '@/features/accessibility/hooks/useUnifiedAccessibility'
import { useOrganizationFeatures } from '@/contexts/OrganizationFeaturesContext'
import ShelfStatusPicker from './ShelfStatusPicker'
import { showShelfToast } from './ShelfToast'
import { clsx } from '@/utils/helpers'
import type { ShelfStatus } from '@/api/domains/content/reading-status-api'

/** Fill color by shelf status. */
const STATUS_FILL: Record<ShelfStatus, string> = {
  currently_reading: 'text-status-success-500 dark:text-status-success-400',
  want_to_read: 'text-status-info-500 dark:text-status-info-400',
  on_hold: 'text-status-warning-500 dark:text-status-warning-400',
  finished: 'text-lsc-dark/70 dark:text-lsc-cream/70',
  did_not_finish: 'text-lsc-dark/70 dark:text-lsc-cream/70',
}

const STATUS_LABELS: Record<ShelfStatus, string> = {
  want_to_read: 'Want to Read',
  currently_reading: 'Currently Reading',
  on_hold: 'On Hold',
  finished: 'Finished',
  did_not_finish: 'Did Not Finish',
}

interface ShelfBookmarkProps {
  catalogItemId: number
  /** Additional CSS classes on the wrapper. */
  className?: string
}

export default function ShelfBookmark({ catalogItemId, className }: ShelfBookmarkProps) {
  const { user } = useAuth()
  const navigate = useNavigate()
  const { isFeatureEnabled } = useOrganizationFeatures()
  const shelfMap = useShelfStatusMap()
  const { handleSetStatus, handleRemove, isUpdating } = useReadingStatus(catalogItemId)
  const { announceToScreenReader } = useUnifiedAccessibility()
  const [showPicker, setShowPicker] = useState(false)
  const [isMobile, setIsMobile] = useState(() => typeof window !== 'undefined' && window.matchMedia('(max-width: 640px)').matches)

  useEffect(() => {
    const mq = window.matchMedia('(max-width: 640px)')
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches)
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [])

  const currentStatus = shelfMap.get(catalogItemId)
  const isShelved = !!currentStatus

  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault()
      e.stopPropagation()

      if (!user) {
        navigate(`/login?returnTo=${encodeURIComponent(window.location.pathname)}`)
        return
      }

      if (isShelved) {
        setShowPicker(true)
      } else {
        handleSetStatus('want_to_read')
        announceToScreenReader('Added to Want to Read shelf')
        showShelfToast({
          status: 'want_to_read',
          onUndo: () => handleRemove(),
          onChange: (newStatus) => handleSetStatus(newStatus),
        })
      }
    },
    [user, isShelved, handleSetStatus, handleRemove, navigate, announceToScreenReader],
  )

  // Feature-flag gate must run AFTER all hooks so the call count is stable
  // across renders (rule-of-hooks; previously caused React #310 when the flag
  // hydrated from false -> true).
  if (!isFeatureEnabled('reading_shelf_enabled')) return null

  const ariaLabel = isShelved
    ? `On your ${STATUS_LABELS[currentStatus!]} shelf. Change status.`
    : 'Add to shelf'

  return (
    <div className={clsx('relative', className)}>
      <button
        onClick={handleClick}
        disabled={isUpdating}
        aria-label={ariaLabel}
        className={clsx(
          'flex items-center justify-center w-9 h-9 rounded-lg transition-all',
          'backdrop-blur-sm bg-black/30 hover:bg-black/50',
          'focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-1',
          'disabled:opacity-50',
        )}
      >
        <Bookmark
          className={clsx(
            'w-5 h-5 transition-colors',
            isShelved
              ? clsx('fill-current', STATUS_FILL[currentStatus!])
              : 'text-white/90 hover:text-white',
          )}
          aria-hidden="true"
        />
      </button>

      {showPicker && (
        <ShelfStatusPicker
          currentStatus={currentStatus}
          variant={isMobile ? 'sheet' : 'popover'}
          onSelect={(status) => {
            handleSetStatus(status)
            announceToScreenReader(`Moved to ${STATUS_LABELS[status]}`)
            showShelfToast({
              status,
              onUndo: () => handleRemove(),
              onChange: (s) => handleSetStatus(s),
            })
          }}
          onRemove={() => handleRemove()}
          onClose={() => setShowPicker(false)}
        />
      )}
    </div>
  )
}
