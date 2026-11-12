/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { useTranslation} from '@/i18n'
import { useAuth } from '../contexts/AuthContext'

import {
  getStreamingAvailability,
  checkoutStreamingContent,
  CatalogStreamingAvailability,
  StreamingCatalogItem,
  StreamingService,
  formatServiceName,
  formatContentType,
  formatDuration,
} from '../api/streaming-api'
import {
  Play,
  Smartphone,
  Globe,
  Loader2,
  AlertCircle,
  CheckCircle,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useAccessibility } from '@/features/accessibility/hooks/useAccessibility'

interface StreamingAvailabilityProps {
  catalogItemId: number
  catalogItemTitle?: string
  compact?: boolean
}

export default function StreamingAvailability({
  catalogItemId,
  catalogItemTitle: _catalogItemTitle,
  compact = false,
}: StreamingAvailabilityProps) {
  const { t } = useTranslation()
  const { token, isAuthenticated } = useAuth()
  const { announceToScreenReader } = useAccessibility()
  const [loading, setLoading] = useState(true)
  const [availability, setAvailability] = useState<CatalogStreamingAvailability | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [checkingOut, setCheckingOut] = useState<number | null>(null)

  useEffect(() => {
    async function fetchAvailability() {
      if (!token) {
        setLoading(false)
        return
      }
      try {
        const data = await getStreamingAvailability(token, catalogItemId)
        setAvailability(data)
        setError(null)
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : 'Failed to check streaming availability'
        if (message.includes('404') || message.includes('not found')) {
          setAvailability(null)
        } else {
          setError(message)
          announceToScreenReader(message)
        }
      } finally {
        setLoading(false)
      }
    }

    fetchAvailability()
  }, [token, catalogItemId, announceToScreenReader])

  const handleCheckout = async (item: StreamingCatalogItem) => {
    if (!token) {
      toast.error(t('components.streamingAvailability.pleaseSignInToCheck'))
      announceToScreenReader('Please sign in to check out streaming content')
      return
    }

    setCheckingOut(item.id)
    try {
      await checkoutStreamingContent(token, item.id)
      toast.success(t('toast.streamingAvailability.titleCheckedOutSuccessfully', { title: item.title }))
      announceToScreenReader(`Checked out ${item.title}`)
      // Open the streaming link
      if (item.web_deep_link) {
        window.open(item.web_deep_link, '_blank')
      }
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Unable to check out. Please try again.'
      toast.error(message)
      announceToScreenReader(message)
    } finally {
      setCheckingOut(null)
    }
  }

  if (loading) {
    return (
      <div className={`flex items-center gap-2 ${compact ? 'text-sm' : ''}`} role="status" aria-live="polite" aria-label={t('aria.streamingAvailability.checkingStreamingAvailability')}>
        <Loader2 className="w-4 h-4 motion-safe:animate-spin motion-reduce:animate-none text-status-info-500" aria-hidden="true" />
        <span className="text-lsc-dark/70 dark:text-lsc-cream/70">Checking streaming...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div
        className={`text-sm text-status-danger-600 ${compact ? 'text-xs' : ''}`}
        role="status"
        aria-live="polite"
      >
        {error}
      </div>
    )
  }

  if (!availability || !availability.has_streaming) {
    return null // Don't show anything if no streaming available
  }

  if (compact) {
    return (
      <div className="flex items-center gap-2 flex-wrap">
        {availability.streaming_options.map((option) => {
          const serviceLabel = option.service_name ? formatServiceName(option.service_name as StreamingService) : 'streaming service'
          return (
            <a
              key={option.id}
              href={option.web_deep_link || '#'}
              target="_blank"
              rel="noopener noreferrer"
              className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                option.service_name === 'palace'
                  ? 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300 hover:bg-status-success-200 dark:hover:bg-status-success-900/50'
                  : 'bg-status-info-100 dark:bg-status-info-900/30 text-status-info-700 dark:text-status-info-300 hover:bg-status-info-200 dark:hover:bg-status-info-900/50'
              }`}
              aria-label={`Stream on ${serviceLabel}`}
            >
              <Play className="w-3.5 h-3.5" aria-hidden="true" />
              {serviceLabel}
            </a>
          )
        })}
      </div>
    )
  }

  return (
    <div className="bg-gradient-to-r from-category-50 to-blue-50 dark:from-category-900/20 dark:to-blue-900/20 rounded-lg border border-category-100 dark:border-category-800 p-4">
      <div className="flex items-center gap-2 mb-3">
        <Play className="w-5 h-5 text-category-600" />
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Streaming Available</h3>
      </div>

      <div className="space-y-3">
        {availability.streaming_options.map((option) => {
          const serviceLabel = option.service_name ? formatServiceName(option.service_name as StreamingService) : 'streaming service'
          return (
          <div
            key={option.id}
            className="bg-lsc-white dark:bg-earth-800 rounded-lg p-4 flex items-center justify-between"
          >
            <div className="flex items-center gap-4">
              <div
                className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                  option.service_name === 'palace' ? 'bg-status-success-100 dark:bg-status-success-900/30' : 'bg-status-info-100 dark:bg-status-info-900/30'
                }`}
              >
                <Play
                  className={`w-6 h-6 ${
                    option.service_name === 'palace' ? 'text-status-success-600' : 'text-status-info-600'
                  }`}
                />
              </div>
              <div>
                <p className="font-medium text-lsc-dark dark:text-lsc-cream">{serviceLabel}</p>
                <div className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  <span>{formatContentType(option.content_type)}</span>
                  {option.duration_minutes && (
                    <>
                      <span>•</span>
                      <span>{formatDuration(option.duration_minutes)}</span>
                    </>
                  )}
                </div>
                {option.is_available ? (
                  <div className="flex items-center gap-1 text-sm text-status-success-600 mt-1">
                    <CheckCircle className="w-3.5 h-3.5" />
                    Available now
                  </div>
                ) : (
                  <div className="flex items-center gap-1 text-sm text-status-warning-600 mt-1">
                    <AlertCircle className="w-3.5 h-3.5" />
                    Currently unavailable
                  </div>
                )}
              </div>
            </div>

            <div className="flex items-center gap-2">
              {isAuthenticated ? (
                <>
                  <button
                    onClick={() => handleCheckout(option)}
                    disabled={checkingOut === option.id || !option.is_available}
                    aria-label={`Borrow on ${serviceLabel}`}
                    className={`px-4 py-2 rounded-lg flex items-center gap-2 text-sm font-medium transition-colors ${
                      option.is_available
                        ? 'bg-status-info-600 text-white hover:bg-status-info-700'
                        : 'bg-earth-200 dark:bg-earth-600 text-lsc-dark/70 dark:text-lsc-cream/70 cursor-not-allowed'
                    }`}
                  >
                    {checkingOut === option.id ? (
                      <Loader2 className="w-4 h-4 motion-safe:animate-spin motion-reduce:animate-none" aria-hidden="true" />
                    ) : (
                      <Play className="w-4 h-4" aria-hidden="true" />
                    )}
                    Borrow
                  </button>
                  {option.web_deep_link && (
                    <a
                      href={option.web_deep_link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-earth-700 dark:hover:text-earth-200 hover:bg-earth-100 dark:hover:bg-earth-700 rounded-lg transition-colors"
                      aria-label={`Open ${serviceLabel} in browser`}
                    >
                      <Globe className="w-5 h-5" aria-hidden="true" />
                    </a>
                  )}
                  {option.app_deep_link && (
                    <a
                      href={option.app_deep_link}
                      className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-earth-700 dark:hover:text-earth-200 hover:bg-earth-100 dark:hover:bg-earth-700 rounded-lg transition-colors"
                      aria-label={`Open ${serviceLabel} in app`}
                    >
                      <Smartphone className="w-5 h-5" aria-hidden="true" />
                    </a>
                  )}
                </>
              ) : (
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('components.streamingAvailability.signInToCheckOut')}</p>
              )}
            </div>
          </div>
        )})}
      </div>

      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-3">
        Streaming checkouts count toward your monthly limit and expire automatically.
      </p>
    </div>
  )
}

// Compact badge component for use in lists
export function StreamingBadge({ catalogItemId }: { catalogItemId: number }) {
  const { token } = useAuth()
  const [hasStreaming, setHasStreaming] = useState<boolean | null>(null)

  useEffect(() => {
    async function check() {
      if (!token) return
      try {
        const data = await getStreamingAvailability(token, catalogItemId)
        setHasStreaming(data.has_streaming)
      } catch {
        setHasStreaming(false)
      }
    }
    check()
  }, [token, catalogItemId])

  if (hasStreaming === null || !hasStreaming) return null

  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-category-100 dark:bg-category-900/30 text-category-700 dark:text-category-300 text-xs font-medium rounded-full">
      <Play className="w-3 h-3" />
      Streaming
    </span>
  )
}
