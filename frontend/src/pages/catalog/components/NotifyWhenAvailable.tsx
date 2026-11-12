/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from 'react'
import { Bell, BellRing, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { Button } from '@/components/ui/Button'
import { apiClient } from '@/lib/api-client'
import { useAuth } from '@/contexts/AuthContext'
import { useUnifiedAccessibility } from '@/features/accessibility/hooks/useUnifiedAccessibility'

interface NotifyWhenAvailableProps {
  itemId: number
  itemStatus: string
}

export function NotifyWhenAvailable({ itemId, itemStatus }: NotifyWhenAvailableProps): React.ReactElement | null {
  const { user, token } = useAuth()
  const { announceToScreenReader } = useUnifiedAccessibility()
  const [isWatching, setIsWatching] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [checked, setChecked] = useState(false)

  const isUnavailable = itemStatus === 'checked_out' || itemStatus === 'on_hold'
  const shouldShow = !!user && !!token && isUnavailable

  useEffect(() => {
    if (!shouldShow) return
    let cancelled = false
    apiClient<{ watching: boolean }>(`/catalog/items/${itemId}/watch`)
      .then((data) => {
        if (!cancelled) {
          setIsWatching(data.watching)
          setChecked(true)
        }
      })
      .catch(() => {
        if (!cancelled) setChecked(true)
      })
    return () => { cancelled = true }
  }, [itemId, shouldShow])

  const handleToggle = useCallback(async () => {
    setIsLoading(true)
    try {
      if (isWatching) {
        await apiClient(`/catalog/items/${itemId}/watch`, { method: 'DELETE', skipJsonParse: true })
        setIsWatching(false)
        toast.success('You will no longer be notified')
        announceToScreenReader('Notification removed')
      } else {
        await apiClient(`/catalog/items/${itemId}/watch`, { method: 'POST' })
        setIsWatching(true)
        toast.success('We will notify you when this becomes available')
        announceToScreenReader('You will be notified when available')
      }
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Could not update notification. Please try again.'
      toast.error(message)
      announceToScreenReader(message)
    } finally {
      setIsLoading(false)
    }
  }, [itemId, isWatching, announceToScreenReader])

  if (!shouldShow || !checked) return null

  return (
    <Button
      variant="secondary"
      size="sm"
      onClick={handleToggle}
      disabled={isLoading}
      aria-pressed={isWatching}
      aria-label={isWatching ? 'Stop watching for availability' : 'Notify me when available'}
    >
      {isLoading ? (
        <Loader2 className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" />
      ) : isWatching ? (
        <BellRing className="w-4 h-4" aria-hidden="true" />
      ) : (
        <Bell className="w-4 h-4" aria-hidden="true" />
      )}
      {isWatching ? 'Watching' : 'Notify me'}
    </Button>
  )
}
