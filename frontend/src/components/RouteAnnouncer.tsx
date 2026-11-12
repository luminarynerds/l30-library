/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { useBranding } from '@/contexts/BrandingContext'

export default function RouteAnnouncer(): React.ReactElement {
  const location = useLocation()
  const branding = useBranding()
  const [announcement, setAnnouncement] = useState('')
  const isFirstRender = useRef(true)
  // Title this component last wrote, so a stale auto-title from the previous
  // route is never mistaken for a page-owned title on the next one.
  const lastAutoTitle = useRef<string | null>(null)

  useEffect(() => {
    const isInitialLoad = isFirstRender.current
    isFirstRender.current = false

    if (!isInitialLoad) {
      // Move focus to the main content region so keyboard/SR users land on the
      // new page instead of staying on a now-stale control. preventScroll avoids
      // scroll-jank (main is tabIndex=-1 and would otherwise be scrolled into view).
      const main = document.getElementById('main-content')
      if (main) {
        main.focus({ preventScroll: true })
      }
    }

    // Small delay to let the new page render (and set document.title if it
    // manages its own, like the indie pages do)
    const timeoutId = setTimeout(() => {
      const siteName = branding.library_name?.trim() || 'Library'
      const pageOwnsTitle =
        document.title !== 'Library' &&
        document.title !== siteName &&
        document.title !== lastAutoTitle.current

      let pageTitle: string
      if (pageOwnsTitle) {
        // Strip a site suffix for the announcement
        pageTitle = document.title.replace(/ [-|] .*$/, '').trim()
      } else {
        // Derive: h1, then pathname
        const heading = document.querySelector('h1')
        const headingText = heading?.textContent?.trim()
        if (headingText) {
          pageTitle = headingText
        } else {
          const pathSegments = location.pathname.split('/').filter(Boolean)
          if (pathSegments.length === 0) {
            pageTitle = 'Home'
          } else {
            const lastSegment = pathSegments[pathSegments.length - 1] || 'page'
            pageTitle = lastSegment
              .replace(/-/g, ' ')
              .replace(/\b\w/g, (char) => char.toUpperCase())
          }
        }
        // WCAG 2.4.2: every route gets a descriptive title. Pages that manage
        // their own title are left alone; everything else gets "<Page> - <Site>".
        const autoTitle =
          pageTitle === 'Home' ? siteName : `${pageTitle} - ${siteName}`
        document.title = autoTitle
        lastAutoTitle.current = autoTitle
      }

      // Skip announcing the initial page load — screen readers already
      // announce the first page. The title still gets set above.
      if (!isInitialLoad) {
        setAnnouncement(`Navigated to ${pageTitle}`)
      }
    }, 100)

    return () => clearTimeout(timeoutId)
    // branding.library_name intentionally omitted: re-running on a late
    // branding fetch would re-title mid-visit; the next navigation picks it up.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.pathname])

  return (
    <div
      role="status"
      aria-live="polite"
      aria-atomic="true"
      className="sr-only"
    >
      {announcement}
    </div>
  )
}
