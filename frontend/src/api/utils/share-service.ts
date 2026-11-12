/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
/**
 * Social sharing utilities for generating share URLs and tracking shares
 */

import { fetchApi } from '@/lib/api-client'

export type SharePlatform = 'bluesky' | 'mastodon' | 'reddit' | 'email' | 'copy_link' | 'whatsapp' | 'telegram'
export type ShareableResourceType = 'book' | 'event' | 'reading_list' | 'author_profile' | 'staff_pick'

export interface ShareableResource {
  type: ShareableResourceType
  id: number
  title: string
  description?: string
  author?: string
  date?: string
  url: string
  imageUrl?: string
}

export interface ShareStats {
  resource_type: ShareableResourceType
  resource_id: number
  total_shares: number
  bluesky_shares: number
  mastodon_shares: number
  reddit_shares: number
  email_shares: number
  copy_link_shares: number
  whatsapp_shares: number
  telegram_shares: number
  last_shared_at: string | null
}

export interface SharingConfig {
  sharing_enabled: boolean
  share_buttons_enabled: boolean
  share_counts_enabled: boolean
  bluesky_enabled: boolean
  mastodon_enabled: boolean
  email_enabled: boolean
  copy_link_enabled: boolean
  utm_tracking_enabled: boolean
  utm_source?: string | null
  utm_medium?: string | null
}

/** Cached config with expiry to avoid hitting the API on every share. */
let _configCache: { data: SharingConfig; expiresAt: number } | null = null
let _configInflight: Promise<SharingConfig | null> | null = null
const CONFIG_CACHE_TTL_MS = 5 * 60 * 1000 // 5 minutes

export async function fetchSharingConfig(): Promise<SharingConfig | null> {
  if (_configCache && Date.now() < _configCache.expiresAt) {
    return _configCache.data
  }

  // Deduplicate in-flight requests (prevents N calls when N components mount simultaneously)
  if (_configInflight) {
    return _configInflight
  }

  _configInflight = (async () => {
    try {
      const data = await fetchApi<SharingConfig>('/sharing/config', { method: 'GET' })
      _configCache = { data, expiresAt: Date.now() + CONFIG_CACHE_TTL_MS }
      return data
    } catch {
      return null
    } finally {
      _configInflight = null
    }
  })()

  return _configInflight
}

export function appendUtmParams(
  url: string,
  platform: SharePlatform,
  config: SharingConfig,
): string {
  if (!config.utm_tracking_enabled) return url

  try {
    const parsed = new URL(url)
    if (config.utm_source) parsed.searchParams.set('utm_source', config.utm_source)
    if (config.utm_medium) parsed.searchParams.set('utm_medium', config.utm_medium)
    parsed.searchParams.set('utm_campaign', platform)
    return parsed.toString()
  } catch {
    // If the URL can't be parsed (e.g. relative path), fall back to string concatenation
    const separator = url.includes('?') ? '&' : '?'
    const parts: string[] = []
    if (config.utm_source) parts.push(`utm_source=${encodeURIComponent(config.utm_source)}`)
    if (config.utm_medium) parts.push(`utm_medium=${encodeURIComponent(config.utm_medium)}`)
    parts.push(`utm_campaign=${encodeURIComponent(platform)}`)
    return `${url}${separator}${parts.join('&')}`
  }
}

export function generateBlueskyShareUrl(resource: ShareableResource): string {
  const baseUrl = 'https://bsky.app/intent/compose'
  const text = `${generateShareText(resource)}\${resource.url}`
  const params = new URLSearchParams({ text })
  return `${baseUrl}?${params.toString()}`
}

export function generateMastodonShareUrl(resource: ShareableResource): string {
  const baseUrl = 'https://mastodon.social/share'
  const text = `${generateShareText(resource)}\${resource.url}`
  const params = new URLSearchParams({ text })
  return `${baseUrl}?${params.toString()}`
}

export function generateRedditShareUrl(resource: ShareableResource): string {
  const baseUrl = 'https://reddit.com/submit'
  const params = new URLSearchParams({
    url: resource.url,
    title: resource.title,
  })
  return `${baseUrl}?${params.toString()}`
}

export function generateEmailShareUrl(resource: ShareableResource): string {
  const subject = encodeURIComponent(`Check out: ${resource.title}`)
  const body = encodeURIComponent(`${generateShareText(resource)}\\${resource.url}`)
  return `mailto:?subject=${subject}&body=${body}`
}

export function generateWhatsAppShareUrl(resource: ShareableResource): string {
  const baseUrl = 'https://wa.me/'
  const text = encodeURIComponent(`${generateShareText(resource)}\${resource.url}`)
  return `${baseUrl}?text=${text}`
}

export function generateTelegramShareUrl(resource: ShareableResource): string {
  const baseUrl = 'https://t.me/share/url'
  const params = new URLSearchParams({
    url: resource.url,
    text: generateShareText(resource),
  })
  return `${baseUrl}?${params.toString()}`
}

function generateShareText(resource: ShareableResource): string {
  switch (resource.type) {
    case 'book':
      return `Check out "${resource.title}"${resource.author ? ` by ${resource.author}` : ''} on L30 Library${resource.description ? `: ${resource.description}` : ''}`

    case 'event':
      return `Join "${resource.title}" at L30 Library${resource.date ? ` on ${resource.date}` : ''}${resource.description ? `: ${resource.description}` : ''}`

    case 'reading_list':
      return `Check out this reading list: "${resource.title}"${resource.description ? ` - ${resource.description}` : ''} on L30 Library`

    case 'author_profile':
      return `Discover author "${resource.title}" on L30 Library${resource.description ? `: ${resource.description}` : ''}`

    case 'staff_pick':
      return `Staff pick: "${resource.title}"${resource.description ? ` - ${resource.description}` : ''} on L30 Library`

    default:
      return `Check this out on L30 Library: ${resource.title}`
  }
}

export function getShareUrl(platform: SharePlatform, resource: ShareableResource): string {
  switch (platform) {
    case 'bluesky':
      return generateBlueskyShareUrl(resource)
    case 'mastodon':
      return generateMastodonShareUrl(resource)
    case 'reddit':
      return generateRedditShareUrl(resource)
    case 'email':
      return generateEmailShareUrl(resource)
    case 'whatsapp':
      return generateWhatsAppShareUrl(resource)
    case 'telegram':
      return generateTelegramShareUrl(resource)
    case 'copy_link':
      return resource.url
    default:
      return resource.url
  }
}

export function openShareWindow(url: string, platform: SharePlatform, _title: string = 'Share'): Window | null {
  // Use default dimensions for social media share windows
  const width = 600
  const height = 400
  const left = (window.innerWidth - width) / 2
  const top = (window.innerHeight - height) / 2

  // Email doesn't need a window
  if (platform === 'email') {
    window.location.href = url
    return null
  }

  return window.open(
    url,
    `share-${platform}`,
    `width=${width},height=${height},left=${left},top=${top},resizable=yes,scrollbars=yes`
  )
}

export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    // Use modern Clipboard API if available
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text)
      return true
    }

    // Fallback for older browsers
    const textArea = document.createElement('textarea')
    textArea.value = text
    textArea.style.position = 'fixed'
    textArea.style.left = '-999999px'
    document.body.appendChild(textArea)
    textArea.focus()
    textArea.select()

    const success = document.execCommand('copy')
    document.body.removeChild(textArea)
    return success
  } catch (error: unknown) {
    Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    return false
  }
}

export async function trackShare(
  resourceType: ShareableResourceType,
  resourceId: number,
  platform: SharePlatform
): Promise<{ success: boolean; message?: string }> {
  try {
    const params = new URLSearchParams({
      resource_type: resourceType,
      resource_id: String(resourceId),
      platform: platform,
    })
    return await fetchApi<{ success: boolean; message?: string }>(`/sharing/track?${params.toString()}`, {
      method: 'POST',
    })
  } catch (error: unknown) {
    Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    // Don't throw - just log the error. Sharing should work even if tracking fails
    return { success: false, message: 'Failed to track share' }
  }
}

export async function getShareStats(
  resourceType: ShareableResourceType,
  resourceId: number
): Promise<ShareStats | null> {
  try {
    return await fetchApi<ShareStats>(
      `/sharing/stats/${resourceType}/${resourceId}`,
      { method: 'GET' }
    )
  } catch (error: unknown) {
    Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    return null
  }
}

export async function shareResource(
  platform: SharePlatform,
  resource: ShareableResource
): Promise<boolean> {
  // Track the share in the background (don't wait for it)
  trackShare(resource.type, resource.id, platform).catch(error => {
    Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
  })

  // Fetch sharing config to apply UTM params (uses cache, non-blocking on failure)
  const config = await fetchSharingConfig()

  // Build a resource copy with UTM-tagged URL when config is available
  const taggedResource: ShareableResource = config
    ? { ...resource, url: appendUtmParams(resource.url, platform, config) }
    : resource

  // Get the share URL
  const shareUrl = getShareUrl(platform, taggedResource)

  // Open share window or copy to clipboard
  if (platform === 'copy_link') {
    return await copyToClipboard(taggedResource.url)
  } else if (platform === 'email') {
    window.location.href = shareUrl
    return true
  } else {
    openShareWindow(shareUrl, platform, resource.title)
    return true
  }
}

export function getCurrentPageUrl(): string {
  return window.location.href
}

export function buildShareableResource(
  type: ShareableResourceType,
  id: number,
  title: string,
  options?: {
    description?: string
    author?: string
    date?: string
    imageUrl?: string
    customUrl?: string
  }
): ShareableResource {
  return {
    type,
    id,
    title,
    ...(options?.description !== undefined ? { description: options.description } : {}),
    ...(options?.author !== undefined ? { author: options.author } : {}),
    ...(options?.date !== undefined ? { date: options.date } : {}),
    ...(options?.imageUrl !== undefined ? { imageUrl: options.imageUrl } : {}),
    url: options?.customUrl || getCurrentPageUrl(),
  }
}
