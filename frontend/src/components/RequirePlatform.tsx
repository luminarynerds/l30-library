/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import type { ReactElement, ReactNode } from 'react'
import { Navigate } from 'react-router-dom'

// L30 vendor/marketing pages (the director pitch, librarian outreach) belong only on
// the platform's own domain. A library self-hosting L30 on its own domain never
// renders them; they redirect home. Hostname-based, so it needs no per-instance
// feature flag or migration: l30.org shows them, every other host does not.
// localhost/127.0.0.1 are included so the pages work in local development.
const PLATFORM_HOSTS = new Set(['l30.org', 'www.l30.org', 'localhost', '127.0.0.1'])

export function isPlatformHost(): boolean {
  if (typeof window === 'undefined') return false
  return PLATFORM_HOSTS.has(window.location.hostname)
}

export default function RequirePlatform({ children }: { children: ReactNode }): ReactElement {
  return isPlatformHost() ? <>{children}</> : <Navigate to="/" replace />
}
