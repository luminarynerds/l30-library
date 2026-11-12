/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
/**
 * Social sharing button component
 * Displays share buttons for multiple platforms with icons and tracking
 */

import React, { useEffect, useMemo, useState } from 'react'
import { Copy, Mail, Share2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { Button } from '@/components/ui/Button'
import {
  shareResource,
  getShareStats,
  buildShareableResource,
  type ShareableResourceType,
  type ShareStats,
  type SharePlatform,
} from '@/api/share-service'
import { useTranslation} from '@/i18n'
import { useSharingConfig } from '@/hooks/useSharingConfig'
import { clean } from '@/lib/utils'

interface ShareButtonProps {
  /**
   * Type of resource being shared
   */
  resourceType: ShareableResourceType

  /**
   * ID of the resource
   */
  resourceId: number

  /**
   * Title of the resource
   */
  title: string

  /**
   * Description of the resource (optional)
   */
  description?: string

  /**
   * Author of the resource (for books)
   */
  author?: string

  /**
   * Date of the resource (for events)
   */
  date?: string

  /**
   * Image URL for the resource
   */
  imageUrl?: string

  /**
   * Custom URL to share (defaults to current page)
   */
  customUrl?: string

  /**
   * Variant of the button
   */
  variant?: 'default' | 'outline' | 'ghost' | 'compact'

  /**
   * Show share count
   */
  showCount?: boolean

  /**
   * Show only specific platforms (defaults to all common ones)
   */
  platforms?: SharePlatform[]

  /**
   * Callback when share is successful
   */
  onShare?: (platform: SharePlatform) => void

  /**
   * Additional CSS classes
   */
  className?: string
}

const BlueskyIcon = ({ className }: { className?: string }) => (
  <svg viewBox="0 0 24 24" fill="currentColor" className={className} aria-hidden="true">
    <path d="M12 10.8c-1.087-2.114-4.046-6.053-6.798-7.995C2.566.944 1.561 1.266.902 1.565.139 1.908 0 3.08 0 3.768c0 .69.378 5.65.624 6.479.785 2.627 3.601 3.476 6.153 3.13-4.4.647-8.28 2.757-3.6 9.42C7.5 28 17.5 18.5 12 10.8Zm0 0c1.087-2.114 4.046-6.053 6.798-7.995C21.434.944 22.439 1.266 23.098 1.565 23.861 1.908 24 3.08 24 3.768c0 .69-.378 5.65-.624 6.479-.785 2.627-3.601 3.476-6.153 3.13 4.4.647 8.28 2.757 3.6 9.42C16.5 28 6.5 18.5 12 10.8Z" />
  </svg>
)

const MastodonIcon = ({ className }: { className?: string }) => (
  <svg viewBox="0 0 24 24" fill="currentColor" className={className} aria-hidden="true">
    <path d="M23.268 5.313c-.35-2.578-2.617-4.61-5.304-5.004C17.51.242 15.792 0 11.813 0h-.03c-3.98 0-4.835.242-5.288.309C3.882.692 1.496 2.518.917 5.127.64 6.412.61 7.837.661 9.143c.074 1.874.088 3.745.26 5.611.118 1.24.325 2.47.62 3.68.55 2.237 2.777 4.098 4.96 4.857 2.336.792 4.849.923 7.256.38.265-.061.527-.132.786-.213.585-.184 1.27-.39 1.774-.753a.057.057 0 0 0 .023-.043v-1.809a.052.052 0 0 0-.02-.041.053.053 0 0 0-.046-.01 20.282 20.282 0 0 1-4.709.547c-2.73 0-3.463-1.284-3.674-1.818a5.593 5.593 0 0 1-.319-1.433.053.053 0 0 1 .066-.054 19.648 19.648 0 0 0 4.636.536c.562 0 1.124-.012 1.68-.047 2.11-.134 4.356-.413 4.737-3.636.015-.13.032-.263.032-.398 0-.12.048-2.585-.003-3.393ZM19.636 13.19H16.64V7.564c0-1.19-.494-1.793-1.488-1.793-1.097 0-1.646.717-1.646 2.134v2.926h-2.976V7.905c0-1.417-.55-2.134-1.646-2.134-.994 0-1.489.604-1.489 1.793v5.625H4.364V7.362c0-1.19.303-2.135.91-2.834.627-.7 1.447-1.058 2.464-1.058 1.177 0 2.067.45 2.654 1.35L12 6.878l1.608-2.058c.587-.9 1.477-1.35 2.654-1.35 1.017 0 1.837.359 2.464 1.058.607.7.91 1.644.91 2.834v5.828Z" />
  </svg>
)

const DEFAULT_PLATFORMS: SharePlatform[] = ['copy_link', 'bluesky', 'mastodon', 'email']

const PLATFORM_CONFIG: Record<
  SharePlatform,
  {
    label: string
    icon: React.ReactNode
    color: string
  }
> = {
  bluesky: {
    label: 'Bluesky',
    icon: <BlueskyIcon className="w-4 h-4" />,
    color: 'bg-sky-500 hover:bg-sky-600',
  },
  mastodon: {
    label: 'Mastodon',
    icon: <MastodonIcon className="w-4 h-4" />,
    color: 'bg-lsc-rose hover:bg-lsc-rose/90',
  },
  reddit: {
    label: 'Reddit',
    icon: <Share2 aria-hidden="true" className="w-4 h-4" />,
    color: 'bg-status-warning-600 hover:bg-status-warning-700',
  },
  email: {
    label: 'Email',
    icon: <Mail aria-hidden="true" className="w-4 h-4" />,
    color: 'bg-earth-600 hover:bg-earth-700',
  },
  copy_link: {
    label: 'Copy Link',
    icon: <Copy aria-hidden="true" className="w-4 h-4" />,
    color: 'bg-earth-700 hover:bg-earth-800',
  },
  whatsapp: {
    label: 'WhatsApp',
    icon: <Share2 aria-hidden="true" className="w-4 h-4" />,
    color: 'bg-status-success-600 hover:bg-status-success-700',
  },
  telegram: {
    label: 'Telegram',
    icon: <Share2 aria-hidden="true" className="w-4 h-4" />,
    color: 'bg-sky-400 hover:bg-sky-500',
  },
}

export const ShareButton: React.FC<ShareButtonProps> = ({
  resourceType,
  resourceId,
  title,
  description,
  author,
  date,
  imageUrl,
  customUrl,
  variant = 'default',
  showCount = true,
  platforms = DEFAULT_PLATFORMS,
  onShare,
  className = '',
}) => {
  const { t } = useTranslation()
  const [isOpen, setIsOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [stats, setStats] = useState<ShareStats | null>(null)
  const [shareInProgress, setShareInProgress] = useState<SharePlatform | null>(null)
  const { data: sharingConfig } = useSharingConfig()

  // Filter platforms based on admin config
  const enabledPlatforms = useMemo(() => {
    if (!sharingConfig) return platforms
    const enabledMap: Record<string, boolean> = {
      bluesky: sharingConfig.bluesky_enabled,
      mastodon: sharingConfig.mastodon_enabled,
      email: sharingConfig.email_enabled,
      copy_link: sharingConfig.copy_link_enabled,
    }
    return platforms.filter((p) => enabledMap[p] !== false)
  }, [platforms, sharingConfig])

  // Respect global sharing toggles
  const shouldShow = !sharingConfig || (sharingConfig.sharing_enabled && sharingConfig.share_buttons_enabled)
  const shouldShowCounts = showCount && (!sharingConfig || sharingConfig.share_counts_enabled)

  // Fetch share statistics lazily when share popup opens (not on mount)
  useEffect(() => {
    if (!isOpen) return
    if (stats) return // Already loaded

    const loadStats = async () => {
      try {
        const statsData = await getShareStats(resourceType, resourceId)
        setStats(statsData)
      } catch (error: unknown) {
        // Silently fail - share stats are non-critical
        console.debug('Share stats unavailable:', error)
      }
    }

    loadStats()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, resourceType, resourceId])

  const handleShare = async (platform: SharePlatform) => {
    try {
      setShareInProgress(platform)
      setIsLoading(true)

      const resource = buildShareableResource(resourceType, resourceId, title, clean({
        description,
        author,
        date,
        imageUrl,
        customUrl,
      }))

      const success = await shareResource(platform, resource)

      if (success) {
        toast.success(t('toast.shareButton.sharedToLabelSuccessfully', { label: PLATFORM_CONFIG[platform].label }))
        onShare?.(platform)

        // Update stats optimistically
        setStats(prev => {
          if (!prev) return prev
          return {
            ...prev,
            total_shares: prev.total_shares + 1,
            [`${platform}_shares` as keyof ShareStats]: ((prev[`${platform}_shares` as keyof ShareStats] as number) + 1) as number,
          } as ShareStats
        })
      } else {
        toast.error(t('components.shareButton.unableToSharePleaseTry'))
      }

      setIsOpen(false)
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('components.shareButton.unableToSharePleaseTry2'))
    } finally {
      setShareInProgress(null)
      setIsLoading(false)
    }
  }

  // If sharing is disabled globally, render nothing
  if (!shouldShow) return null

  const totalShares = stats?.total_shares || 0

  if (variant === 'compact') {
    return (
      <div className={`relative flex items-center gap-1 ${className}`}>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="p-1.5 rounded-full transition-colors text-lsc-dark/40 dark:text-lsc-cream/40 hover:text-lsc-dark/70 dark:hover:text-lsc-cream/70"
          aria-label={title ? `Share ${title}` : t('aria.shareButton.shareThisItem')}
          aria-expanded={isOpen}
          disabled={isLoading}
        >
          <Share2 aria-hidden="true" className="w-3.5 h-3.5" />
        </button>
        {shouldShowCounts && totalShares > 0 && (
          <span className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70">{totalShares}</span>
        )}

        {isOpen && (
          <div className="absolute right-0 top-full mt-1 bg-lsc-white dark:bg-earth-800 rounded-lg shadow-lg border border-lsc-border dark:border-earth-700 p-2 z-50 flex gap-1">
            {enabledPlatforms.map(platform => (
              <button
                key={platform}
                onClick={() => handleShare(platform)}
                disabled={isLoading || shareInProgress === platform}
                className={`p-2 rounded text-white ${PLATFORM_CONFIG[platform].color} transition-colors disabled:opacity-50`}
                title={PLATFORM_CONFIG[platform].label}
              >
                {PLATFORM_CONFIG[platform].icon}
              </button>
            ))}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className={`flex flex-col gap-3 ${className}`}>
      <div className="flex items-center gap-2">
        <Button
          onClick={() => setIsOpen(!isOpen)}
          variant={variant}
          disabled={isLoading}
          className="flex items-center gap-2"
        >
          <Share2 aria-hidden="true" className="w-4 h-4" />
          Share
          {shouldShowCounts && totalShares > 0 && (
            <span className="ml-1 inline-block bg-opacity-20 px-2 py-0.5 rounded text-sm font-medium">
              ({totalShares})
            </span>
          )}
        </Button>
      </div>

      {isOpen && (
        <div className="flex flex-wrap gap-2">
          {enabledPlatforms.map(platform => (
            <button
              key={platform}
              onClick={() => handleShare(platform)}
              disabled={isLoading || shareInProgress === platform}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-white text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
                PLATFORM_CONFIG[platform].color
              }`}
              title={PLATFORM_CONFIG[platform].label}
            >
              {shareInProgress === platform ? (
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full motion-safe:animate-spin motion-reduce:animate-none" aria-hidden="true" />
              ) : (
                PLATFORM_CONFIG[platform].icon
              )}
              {PLATFORM_CONFIG[platform].label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export default ShareButton
