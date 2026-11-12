/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect } from 'react'
import { useBranding } from '@/contexts/BrandingContext'

export function usePageTitle(title: string, description?: string): void {
  const branding = useBranding()
  const siteName = branding.library_name || 'Library'

  useEffect(() => {
    document.title = title ? `${title} | ${siteName}` : siteName

    let previousDescription: string | undefined
    if (description) {
      let meta = document.querySelector('meta[name="description"]') as HTMLMetaElement | null
      if (!meta) {
        meta = document.createElement('meta')
        meta.name = 'description'
        document.head.appendChild(meta)
      }
      previousDescription = meta.content
      meta.content = description
    }

    return () => {
      document.title = siteName
      if (description) {
        const meta = document.querySelector('meta[name="description"]') as HTMLMetaElement | null
        if (meta && previousDescription !== undefined) {
          meta.content = previousDescription
        }
      }
    }
  }, [title, description, siteName])
}
