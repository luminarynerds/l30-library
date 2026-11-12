/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { renderHook } from '@testing-library/react'
import { usePageMeta } from '../usePageMeta'

// Mock the branding context so the hook resolves a deterministic origin/name
// without dragging in the real provider, which fetches /branding at boot.
vi.mock('@/contexts/BrandingContext', () => ({
  useBranding: () => ({
    library_name: 'L30 Library',
    library_short_name: 'L30',
    domain: 'https://l30.org',
  }),
}))

function setupHead(): void {
  document.head.innerHTML = `
    <title>L30 - Community Library</title>
    <meta name="description" content="default" />
    <link rel="canonical" href="https://l30.org/" />
    <meta property="og:url" content="https://l30.org/" />
    <meta property="og:title" content="default" />
    <meta property="og:description" content="default" />
    <meta property="og:image" content="https://l30.org/og-image.png" />
    <meta property="og:type" content="website" />
    <meta name="twitter:description" content="default" />
  `
}

describe('usePageMeta', () => {
  beforeEach(() => {
    setupHead()
    document.title = 'L30 - Community Library'
  })

  it('updates canonical link to match canonicalPath against the branding origin', () => {
    renderHook(() =>
      usePageMeta({
        title: 'Events & Programs',
        description: 'Browse upcoming events',
        canonicalPath: '/events',
      }),
    )

    const canonical = document.querySelector('link[rel="canonical"]')
    expect(canonical?.getAttribute('href')).toBe('https://l30.org/events')
  })

  it('updates og:url to match canonicalPath against the branding origin', () => {
    renderHook(() =>
      usePageMeta({
        title: 'Events & Programs',
        canonicalPath: '/events',
      }),
    )

    const ogUrl = document.querySelector('meta[property="og:url"]')
    expect(ogUrl?.getAttribute('content')).toBe('https://l30.org/events')
  })

  it('changes canonical and og:url when canonicalPath changes between renders', () => {
    const { rerender } = renderHook(
      ({ path }: { path: string }) =>
        usePageMeta({
          title: 'page',
          canonicalPath: path,
        }),
      { initialProps: { path: '/events' } },
    )

    expect(document.querySelector('link[rel="canonical"]')?.getAttribute('href')).toBe(
      'https://l30.org/events',
    )

    rerender({ path: '/events/detail/42' })

    expect(document.querySelector('link[rel="canonical"]')?.getAttribute('href')).toBe(
      'https://l30.org/events/detail/42',
    )
    expect(document.querySelector('meta[property="og:url"]')?.getAttribute('content')).toBe(
      'https://l30.org/events/detail/42',
    )
  })

  it('restores defaults on unmount so the next page is not poisoned', () => {
    const { unmount } = renderHook(() =>
      usePageMeta({
        title: 'Some Event',
        canonicalPath: '/events/detail/1',
      }),
    )

    expect(document.querySelector('link[rel="canonical"]')?.getAttribute('href')).toBe(
      'https://l30.org/events/detail/1',
    )

    unmount()

    expect(document.querySelector('link[rel="canonical"]')?.getAttribute('href')).toBe(
      'https://l30.org/',
    )
    expect(document.querySelector('meta[property="og:url"]')?.getAttribute('content')).toBe(
      'https://l30.org/',
    )
  })
})
