/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

export default function ScrollToTop(): null {
  const { pathname } = useLocation()

  useEffect(() => {
    window.scrollTo(0, 0)
    // Staff/admin routes use an overflow-auto container instead of window scroll
    const main = document.getElementById('main-content')
    if (main) main.scrollTop = 0

    // Keep <link rel="canonical"> and og:url synced to the current route. The
    // static shell ships canonical="https://l30.org/" on every page; crawlers
    // on the nginx bot allowlist get a server-injected canonical, but every
    // other client (and unlisted bots) would otherwise see each route declare
    // itself a duplicate of the homepage. Pages that set a more specific
    // canonical via usePageMeta run their effect after this one, so their
    // value wins for the page's lifetime.
    const href = window.location.origin + (pathname === '/' ? '/' : pathname.replace(/\/+$/, ''))
    const canonical = document.querySelector('link[rel="canonical"]')
    if (canonical) canonical.setAttribute('href', href)
    const ogUrl = document.querySelector('meta[property="og:url"]')
    if (ogUrl) ogUrl.setAttribute('content', href)
  }, [pathname])

  return null
}
