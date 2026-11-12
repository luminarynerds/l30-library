/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect } from 'react'
import { useBranding } from '@/contexts/BrandingContext'

interface PageMeta {
  title?: string
  description?: string
  canonicalPath?: string
  ogTitle?: string
  ogDescription?: string
  ogImage?: string
  ogType?: string
}

function setMetaTag(selector: string, content: string): void {
  const el = document.querySelector(selector)
  if (el) el.setAttribute('content', content)
}

export function usePageMeta(meta: PageMeta): void {
  const branding = useBranding()
  const siteName = branding.library_name || 'Library'
  const baseUrl = branding.domain || ''
  const defaultDescription = `${siteName} - Search the catalog, reserve a room, check your holds, find events.`
  const defaultOgImage = `${baseUrl}/og-image.png`

  useEffect(() => {
    // Title
    document.title = meta.title ? `${meta.title} | ${siteName}` : siteName

    // Meta description
    if (meta.description) {
      setMetaTag('meta[name="description"]', meta.description)
    }

    // Canonical URL
    if (meta.canonicalPath) {
      const canonical = document.querySelector('link[rel="canonical"]')
      if (canonical) canonical.setAttribute('href', `${baseUrl}${meta.canonicalPath}`)
    }

    // OG tags
    setMetaTag('meta[property="og:url"]', `${baseUrl}${meta.canonicalPath || '/'}`)
    if (meta.ogTitle || meta.title) {
      setMetaTag('meta[property="og:title"]', meta.ogTitle || `${meta.title} | ${siteName}`)
    }
    if (meta.ogDescription || meta.description) {
      setMetaTag('meta[property="og:description"]', meta.ogDescription || meta.description || defaultDescription)
    }
    if (meta.ogImage) {
      setMetaTag('meta[property="og:image"]', meta.ogImage)
    }
    if (meta.ogType) {
      setMetaTag('meta[property="og:type"]', meta.ogType)
    }

    // Twitter
    if (meta.description) {
      setMetaTag('meta[name="twitter:description"]', meta.description)
    }

    return () => {
      document.title = siteName
      setMetaTag('meta[name="description"]', defaultDescription)
      const canonical = document.querySelector('link[rel="canonical"]')
      if (canonical) canonical.setAttribute('href', baseUrl + '/')
      setMetaTag('meta[property="og:url"]', baseUrl + '/')
      setMetaTag('meta[property="og:title"]', `${branding.library_short_name} - ${siteName}`)
      setMetaTag('meta[property="og:description"]', defaultDescription)
      setMetaTag('meta[property="og:image"]', defaultOgImage)
      setMetaTag('meta[property="og:type"]', 'website')
      setMetaTag('meta[name="twitter:description"]', defaultDescription)
    }
  }, [meta.title, meta.description, meta.canonicalPath, meta.ogTitle, meta.ogDescription, meta.ogImage, meta.ogType, siteName, baseUrl, defaultDescription, defaultOgImage, branding.library_short_name])
}
