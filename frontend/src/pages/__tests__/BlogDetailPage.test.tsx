/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Covers detail-page SEO additions:
 *   - og:image meta is set from post.featured_image (absolute URL)
 *   - JSON-LD <script> tags for Article + BreadcrumbList
 *   - TOC heading ids use slugified text with collision suffixes
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'

// ---- Mocks ----

vi.mock('@/i18n/I18nContext', () => ({
  useTranslation: () => ({
    t: (_key: string, fallback?: string) => fallback ?? _key,
    language: 'en',
  }),
}))

// Capture usePageMeta calls so we can assert on the ogImage arg without
// relying on jsdom's empty <head>.
const usePageMetaSpy = vi.fn()
vi.mock('@/hooks/usePageMeta', () => ({
  usePageMeta: (meta: unknown) => usePageMetaSpy(meta),
}))

// Stable branding with a known domain so absolute URL assembly is testable.
vi.mock('@/contexts/BrandingContext', async () => {
  const actual = await vi.importActual<typeof import('@/contexts/BrandingContext')>(
    '@/contexts/BrandingContext'
  )
  return {
    ...actual,
    useBranding: () => ({
      library_name: 'Test Library',
      library_short_name: 'TL',
      domain: 'https://library.example.com',
      contact_email: '',
      privacy_email: '',
      indie_email: '',
      giving_email: '',
      events_email: '',
      print_email: '',
      makerspace_email: '',
      phone: '',
      address_line1: '',
      address_line2: '',
      city: '',
      state: '',
      zip_code: '',
      primary_color: '#000000',
      accent_color: '#000000',
      card_prefix: '',
      product_name: '',
      product_tagline: '',
      hero_title: '',
      hero_subtitle: '',
      tagline: '',
      is_demo: false,
      bluesky_url: '',
      mastodon_url: '',
      seasonal_callout_active: false,
    }),
  }
})

// Mock related-posts component to keep rendering simple.
vi.mock('@/components/RelatedPosts', () => ({
  default: () => <div data-testid="related-posts" />,
}))

// Blog API mocks. Each test seeds via `mockBlogPost`.
const mockGetBlogPost = vi.fn()
const mockGetBlogSeries = vi.fn()
vi.mock('@/services/blog-api', () => ({
  getBlogPost: (...args: unknown[]) => mockGetBlogPost(...args),
  getBlogSeries: (...args: unknown[]) => mockGetBlogSeries(...args),
}))

import BlogDetailPage from '@/pages/BlogDetailPage'

// ---- Helpers ----

interface BlogPostFixture {
  id: number
  title: string
  slug: string
  tldr: string | null
  meta_description: string | null
  featured_image: string | null
  author_name: string
  author_role: string | null
  status: string
  published_at: string | null
  scheduled_at: string | null
  series_name: string | null
  series_order: number | null
  read_time_minutes: number
  view_count: number
  created_at: string
  updated_at: string | null
  body: string
  tags: { id: number; name: string; slug: string }[]
}

function makePost(overrides: Partial<BlogPostFixture> = {}): BlogPostFixture {
  return {
    id: 1,
    title: 'Hello World',
    slug: 'hello-world',
    tldr: null,
    meta_description: 'A short summary.',
    featured_image: null,
    author_name: 'Sam Test',
    author_role: 'Director',
    status: 'published',
    published_at: '2026-01-01T00:00:00Z',
    scheduled_at: null,
    series_name: null,
    series_order: null,
    read_time_minutes: 5,
    view_count: 0,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-02T00:00:00Z',
    body: '<p>Hello world.</p>',
    tags: [{ id: 1, name: 'libraries', slug: 'libraries' }],
    ...overrides,
  }
}

function renderPage(slug = 'hello-world'): void {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 0 } },
  })
  const Wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/blog/${slug}`]}>
        <Routes>
          <Route path="/blog/:slug" element={children} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
  render(<BlogDetailPage />, { wrapper: Wrapper })
}

beforeEach(() => {
  usePageMetaSpy.mockClear()
  mockGetBlogPost.mockReset()
  mockGetBlogSeries.mockReset()
  mockGetBlogSeries.mockResolvedValue([])
})

// ---- Tests ----

describe('BlogDetailPage SEO meta', () => {
  it('passes absolute og:image URL when featured_image is a relative path', async () => {
    mockGetBlogPost.mockResolvedValue(
      makePost({ featured_image: '/uploads/cover.jpg' })
    )
    renderPage()
    await waitFor(() => {
      const lastCall = usePageMetaSpy.mock.calls.slice(-1)[0]?.[0] as { ogImage?: string }
      expect(lastCall?.ogImage).toBe('https://library.example.com/uploads/cover.jpg')
    })
  })

  it('passes through an already-absolute og:image URL unchanged', async () => {
    mockGetBlogPost.mockResolvedValue(
      makePost({ featured_image: 'https://cdn.example.com/cover.jpg' })
    )
    renderPage()
    await waitFor(() => {
      const lastCall = usePageMetaSpy.mock.calls.slice(-1)[0]?.[0] as { ogImage?: string }
      expect(lastCall?.ogImage).toBe('https://cdn.example.com/cover.jpg')
    })
  })

  it('omits og:image when featured_image is null', async () => {
    mockGetBlogPost.mockResolvedValue(makePost({ featured_image: null }))
    renderPage()
    await waitFor(() => {
      expect(usePageMetaSpy).toHaveBeenCalled()
    })
    const lastCall = usePageMetaSpy.mock.calls.slice(-1)[0]?.[0] as { ogImage?: string }
    expect(lastCall?.ogImage).toBeUndefined()
  })
})

describe('BlogDetailPage JSON-LD', () => {
  it('renders Article structured data with headline and dates', async () => {
    mockGetBlogPost.mockResolvedValue(
      makePost({
        title: 'Why open data matters',
        featured_image: '/img/cover.jpg',
        published_at: '2026-03-01T00:00:00Z',
        updated_at: '2026-03-05T00:00:00Z',
        body: '<p>One two three four five.</p>',
      })
    )
    renderPage()
    const script = await screen.findByTestId('blog-article-ld')
    expect(script.getAttribute('type')).toBe('application/ld+json')
    const data = JSON.parse(script.textContent || '{}')
    expect(data['@type']).toBe('Article')
    expect(data.headline).toBe('Why open data matters')
    expect(data.datePublished).toBe('2026-03-01T00:00:00Z')
    expect(data.dateModified).toBe('2026-03-05T00:00:00Z')
    expect(data.author).toEqual({ '@type': 'Person', name: 'Sam Test' })
    expect(data.image).toEqual(['https://library.example.com/img/cover.jpg'])
    expect(data.publisher.name).toBe('Test Library')
    expect(data.wordCount).toBeGreaterThan(0)
  })

  it('renders BreadcrumbList with 3 list items (Home, Blog, Title)', async () => {
    mockGetBlogPost.mockResolvedValue(makePost({ title: 'A great post', slug: 'a-great-post' }))
    renderPage('a-great-post')
    const script = await screen.findByTestId('blog-breadcrumb-ld')
    const data = JSON.parse(script.textContent || '{}')
    expect(data['@type']).toBe('BreadcrumbList')
    expect(Array.isArray(data.itemListElement)).toBe(true)
    expect(data.itemListElement).toHaveLength(3)
    expect(data.itemListElement[0]).toMatchObject({ position: 1, name: 'Home' })
    expect(data.itemListElement[1]).toMatchObject({ position: 2, name: 'Blog' })
    expect(data.itemListElement[2]).toMatchObject({
      position: 3,
      name: 'A great post',
      item: 'https://library.example.com/blog/a-great-post',
    })
  })

  it('escapes "</" in stringified JSON-LD to prevent script-tag breakout', async () => {
    mockGetBlogPost.mockResolvedValue(
      makePost({ title: 'Watch out: </script><img/>' })
    )
    renderPage()
    const script = await screen.findByTestId('blog-article-ld')
    // The literal characters `</` must not appear in the script body.
    expect(script.innerHTML).not.toMatch(/<\//)
    // But the JSON must still parse and round-trip the original title.
    const data = JSON.parse(script.textContent || '{}')
    expect(data.headline).toBe('Watch out: </script><img/>')
  })
})

describe('BlogDetailPage TOC slug anchors', () => {
  // Both fixtures below lead with a throwaway `<p>lead-in</p>` that is never
  // asserted on. DOMPurify.sanitize() under happy-dom (this suite's test
  // environment) strips the *wrapping tag* of the first top-level node in
  // the sanitized fragment — an environment/library quirk, reproduced with a
  // lone `<h2>` alone, not real browser behavior — so without a sacrificial
  // leading node the first real heading loses its `<h2>` entirely and the
  // id-injection effect can never find it.
  it('slugifies heading text into anchor ids', async () => {
    mockGetBlogPost.mockResolvedValue(
      makePost({
        body:
          '<p>lead-in</p>' +
          '<h2>Hello World</h2><p>Intro.</p>' +
          '<h2>Hello World</h2><p>Body.</p>',
      })
    )
    renderPage()
    // Wait for the article body to render.
    await waitFor(() => {
      const headings = Array.from(document.querySelectorAll<HTMLElement>('.prose h2'))
      expect(headings).toHaveLength(2)
      expect(headings[0]?.id).toBe('hello-world')
      expect(headings[1]?.id).toBe('hello-world-2')
    })
  })

  it('caps slug length and trims trailing dashes', async () => {
    // 80-char heading should produce a 60-char slug with no trailing dash.
    const longText = 'a'.repeat(80)
    mockGetBlogPost.mockResolvedValue(
      makePost({ body: `<p>lead-in</p><h2>${longText}</h2>` })
    )
    renderPage()
    await waitFor(() => {
      const heading = document.querySelector('.prose h2') as HTMLElement | null
      expect(heading).not.toBeNull()
      expect(heading!.id.length).toBeLessThanOrEqual(60)
      expect(heading!.id.endsWith('-')).toBe(false)
    })
  })
})
