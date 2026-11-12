/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Layout Component Integration Tests
 *
 * Tests for main Layout component including:
 * - Breadcrumb navigation
 * - Mobile/desktop navigation switching
 * - Content density settings
 * - Skip links
 * - Bottom navigation
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render } from "@testing-library/react"
import { screen, within } from "@testing-library/react"
import { axe } from 'jest-axe'
import { BrowserRouter, MemoryRouter } from 'react-router-dom'

// Mock Layout component - replace with actual import when available
const Layout = ({ children }: { children: React.ReactNode }) => {
  const [contentDensity, _setContentDensity] = React.useState<'comfortable' | 'compact' | 'spacious'>('comfortable')
  const location = window.location.pathname

  React.useEffect(() => {
    document.documentElement.setAttribute('data-content-density', contentDensity)
  }, [contentDensity])

  const isHomePage = location === '/' || location === '/home'
  const isMobile = window.innerWidth < 768

  return (
    <div className="layout-container">
      {/* Skip Link */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-lsc-rose focus:text-white focus:rounded"
      >
        Skip to main content
      </a>

      {/* Header */}
      <header className="layout-header">
        <h1>Library System</h1>
      </header>

      {/* Breadcrumbs - hidden on home page */}
      {!isHomePage && (
        <nav aria-label={t('aria.breadcrumb.breadcrumb')} className="breadcrumb-nav">
          <ol className="flex gap-2">
            <li><a href="/">Home</a></li>
            <li aria-hidden="true">/</li>
            <li aria-current="page">Current Page</li>
          </ol>
        </nav>
      )}

      {/* Mobile Navigation */}
      {isMobile && (
        <nav aria-label={t('aria.__tests__.mobileNavigation')} className="mobile-nav">
          <ul className="flex justify-around">
            <li><a href="/" className="min-h-[44px] flex items-center">Home</a></li>
            <li><a href="/catalog" className="min-h-[44px] flex items-center">Catalog</a></li>
            <li><a href="/events" className="min-h-[44px] flex items-center">Events</a></li>
            <li><a href="/more" className="min-h-[44px] flex items-center">More</a></li>
          </ul>
        </nav>
      )}

      {/* Desktop Navigation */}
      {!isMobile && (
        <nav aria-label={t('aria.__tests__.desktopNavigation')} className="desktop-nav">
          <ul className="flex gap-4">
            <li><a href="/">Home</a></li>
            <li><a href="/catalog">Catalog</a></li>
            <li><a href="/events">Events</a></li>
            <li><a href="/programs">Programs</a></li>
            <li><a href="/account">Account</a></li>
          </ul>
        </nav>
      )}

      {/* Main Content */}
      <main id="main-content" className="layout-main">
        {children}
      </main>

      {/* Bottom Navigation - Mobile Only */}
      {isMobile && (
        <nav aria-label={t('aria.__tests__.bottomNavigation')} className="bottom-nav fixed bottom-0 left-0 right-0 bg-lsc-white dark:bg-lsc-dark shadow-top">
          <ul className="flex justify-around items-center py-2">
            <li>
              <a
                href="/"
                className="flex flex-col items-center min-h-[44px] min-w-[44px] justify-center"
                aria-label={t('aria.__tests__.home')}
              >
                Home
              </a>
            </li>
            <li>
              <a
                href="/catalog"
                className="flex flex-col items-center min-h-[44px] min-w-[44px] justify-center"
                aria-label={t('aria.__tests__.catalog')}
              >
                Catalog
              </a>
            </li>
            <li>
              <a
                href="/events"
                className="flex flex-col items-center min-h-[44px] min-w-[44px] justify-center"
                aria-label={t('aria.__tests__.events')}
              >
                Events
              </a>
            </li>
            <li>
              <a
                href="/more"
                className="flex flex-col items-center min-h-[44px] min-w-[44px] justify-center"
                aria-label={t('aria.__tests__.more')}
              >
                More
              </a>
            </li>
          </ul>
        </nav>
      )}
    </div>
  )
}

import React from 'react'
import { t } from '@/i18n'

describe('Layout Component', () => {
  // Preload English translations. vitest setup.ts does not preload i18n,
  // and t() returns raw dotted-path keys (e.g. aria.__tests__.mobileNavigation)
  // when no language is loaded — breaking getByRole({ name: 'Mobile navigation' }).

  beforeEach(() => {
    // Reset window size
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 1024,
    })

    // Mock matchMedia
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }))
  })

  describe('Skip Link', () => {
    it('renders skip link for keyboard navigation', () => {
      render(
        <BrowserRouter>
          <Layout>Content</Layout>
        </BrowserRouter>
      )

      const skipLink = screen.getByText('Skip to main content')
      expect(skipLink).toBeInTheDocument()
    })

    it('skip link has correct href', () => {
      render(
        <BrowserRouter>
          <Layout>Content</Layout>
        </BrowserRouter>
      )

      const skipLink = screen.getByText('Skip to main content')
      expect(skipLink).toHaveAttribute('href', '#main-content')
    })

    it('skip link is visually hidden by default', () => {
      render(
        <BrowserRouter>
          <Layout>Content</Layout>
        </BrowserRouter>
      )

      const skipLink = screen.getByText('Skip to main content')
      expect(skipLink).toHaveClass('sr-only')
    })

    it('skip link becomes visible on focus', () => {
      render(
        <BrowserRouter>
          <Layout>Content</Layout>
        </BrowserRouter>
      )

      const skipLink = screen.getByText('Skip to main content')
      expect(skipLink).toHaveClass('focus:not-sr-only')
    })

    it('main content has matching id', () => {
      render(
        <BrowserRouter>
          <Layout>Content</Layout>
        </BrowserRouter>
      )

      const main = document.getElementById('main-content')
      expect(main).toBeInTheDocument()
    })
  })

  describe('Breadcrumbs', () => {
    it('shows breadcrumbs on non-home pages', () => {
      Object.defineProperty(window, 'location', {
        writable: true,
        value: { pathname: '/catalog' },
      })

      render(
        <MemoryRouter initialEntries={['/catalog']}>
          <Layout>Content</Layout>
        </MemoryRouter>
      )

      expect(screen.getByRole('navigation', { name: 'Breadcrumb' })).toBeInTheDocument()
    })

    it('hides breadcrumbs on home page', () => {
      Object.defineProperty(window, 'location', {
        writable: true,
        value: { pathname: '/' },
      })

      render(
        <MemoryRouter initialEntries={['/']}>
          <Layout>Content</Layout>
        </MemoryRouter>
      )

      expect(screen.queryByRole('navigation', { name: 'Breadcrumb' })).not.toBeInTheDocument()
    })

    it('breadcrumb has proper structure', () => {
      Object.defineProperty(window, 'location', {
        writable: true,
        value: { pathname: '/catalog' },
      })

      render(
        <MemoryRouter initialEntries={['/catalog']}>
          <Layout>Content</Layout>
        </MemoryRouter>
      )

      const breadcrumb = screen.getByRole('navigation', { name: 'Breadcrumb' })
      const list = within(breadcrumb).getByRole('list')
      expect(list).toBeInTheDocument()
    })

    it('current page has aria-current attribute', () => {
      Object.defineProperty(window, 'location', {
        writable: true,
        value: { pathname: '/catalog' },
      })

      render(
        <MemoryRouter initialEntries={['/catalog']}>
          <Layout>Content</Layout>
        </MemoryRouter>
      )

      const currentPage = screen.getByText('Current Page')
      expect(currentPage.closest('li')).toHaveAttribute('aria-current', 'page')
    })
  })

  describe('Mobile Navigation', () => {
    beforeEach(() => {
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 375,
      })
    })

    it('renders on small screens', () => {
      render(
        <BrowserRouter>
          <Layout>Content</Layout>
        </BrowserRouter>
      )

      expect(screen.getByRole('navigation', { name: 'Mobile navigation' })).toBeInTheDocument()
    })

    it('has all navigation items', () => {
      render(
        <BrowserRouter>
          <Layout>Content</Layout>
        </BrowserRouter>
      )

      const mobileNav = screen.getByRole('navigation', { name: 'Mobile navigation' })
      const links = within(mobileNav).getAllByRole('link')

      expect(links.length).toBeGreaterThanOrEqual(4)
    })

    it('navigation items have minimum touch targets', () => {
      render(
        <BrowserRouter>
          <Layout>Content</Layout>
        </BrowserRouter>
      )

      const mobileNav = screen.getByRole('navigation', { name: 'Mobile navigation' })
      const links = within(mobileNav).getAllByRole('link')

      links.forEach(link => {
        expect(link).toHaveClass('min-h-[44px]')
      })
    })
  })

  describe('Desktop Navigation', () => {
    it('renders on large screens', () => {
      render(
        <BrowserRouter>
          <Layout>Content</Layout>
        </BrowserRouter>
      )

      expect(screen.getByRole('navigation', { name: 'Desktop navigation' })).toBeInTheDocument()
    })

    it('does not render on small screens', () => {
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 375,
      })

      render(
        <BrowserRouter>
          <Layout>Content</Layout>
        </BrowserRouter>
      )

      expect(screen.queryByRole('navigation', { name: 'Desktop navigation' })).not.toBeInTheDocument()
    })

    it('has all navigation items', () => {
      render(
        <BrowserRouter>
          <Layout>Content</Layout>
        </BrowserRouter>
      )

      const desktopNav = screen.getByRole('navigation', { name: 'Desktop navigation' })
      const links = within(desktopNav).getAllByRole('link')

      expect(links.length).toBeGreaterThanOrEqual(4)
    })
  })

  describe('Bottom Navigation', () => {
    beforeEach(() => {
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 375,
      })
    })

    it('renders on mobile viewports', () => {
      render(
        <BrowserRouter>
          <Layout>Content</Layout>
        </BrowserRouter>
      )

      expect(screen.getByRole('navigation', { name: 'Bottom navigation' })).toBeInTheDocument()
    })

    it('does not render on desktop', () => {
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 1024,
      })

      render(
        <BrowserRouter>
          <Layout>Content</Layout>
        </BrowserRouter>
      )

      expect(screen.queryByRole('navigation', { name: 'Bottom navigation' })).not.toBeInTheDocument()
    })

    it('has exactly 4 navigation items', () => {
      render(
        <BrowserRouter>
          <Layout>Content</Layout>
        </BrowserRouter>
      )

      const bottomNav = screen.getByRole('navigation', { name: 'Bottom navigation' })
      const links = within(bottomNav).getAllByRole('link')

      expect(links).toHaveLength(4)
    })

    it('all items have 44px minimum touch targets', () => {
      render(
        <BrowserRouter>
          <Layout>Content</Layout>
        </BrowserRouter>
      )

      const bottomNav = screen.getByRole('navigation', { name: 'Bottom navigation' })
      const links = within(bottomNav).getAllByRole('link')

      links.forEach(link => {
        expect(link).toHaveClass('min-h-[44px]')
        expect(link).toHaveClass('min-w-[44px]')
      })
    })

    it('is fixed at bottom of viewport', () => {
      render(
        <BrowserRouter>
          <Layout>Content</Layout>
        </BrowserRouter>
      )

      const bottomNav = screen.getByRole('navigation', { name: 'Bottom navigation' })
      expect(bottomNav).toHaveClass('fixed')
      expect(bottomNav).toHaveClass('bottom-0')
    })

    it('spans full width', () => {
      render(
        <BrowserRouter>
          <Layout>Content</Layout>
        </BrowserRouter>
      )

      const bottomNav = screen.getByRole('navigation', { name: 'Bottom navigation' })
      expect(bottomNav).toHaveClass('left-0')
      expect(bottomNav).toHaveClass('right-0')
    })

    it('has proper aria-labels on items', () => {
      render(
        <BrowserRouter>
          <Layout>Content</Layout>
        </BrowserRouter>
      )

      const bottomNav = screen.getByRole('navigation', { name: 'Bottom navigation' })
      const links = bottomNav.querySelectorAll('a')
      const linkNames = Array.from(links).map(link => link.getAttribute('aria-label') || link.textContent?.trim())
      expect(linkNames).toContain('Home')
      expect(linkNames).toContain('Catalog')
      expect(linkNames).toContain('Events')
    })
  })

  describe('Content Density', () => {
    it('applies content density attribute to document', () => {
      render(
        <BrowserRouter>
          <Layout>Content</Layout>
        </BrowserRouter>
      )

      expect(document.documentElement).toHaveAttribute('data-content-density')
    })

    it('defaults to comfortable density', () => {
      render(
        <BrowserRouter>
          <Layout>Content</Layout>
        </BrowserRouter>
      )

      expect(document.documentElement).toHaveAttribute('data-content-density', 'comfortable')
    })
  })

  describe('Main Content Area', () => {
    it('renders children in main element', () => {
      render(
        <BrowserRouter>
          <Layout>
            <div data-testid="test-content">Test Content</div>
          </Layout>
        </BrowserRouter>
      )

      const main = screen.getByRole('main')
      expect(within(main).getByTestId('test-content')).toBeInTheDocument()
    })

    it('main has correct id for skip link', () => {
      render(
        <BrowserRouter>
          <Layout>Content</Layout>
        </BrowserRouter>
      )

      const main = screen.getByRole('main')
      expect(main).toHaveAttribute('id', 'main-content')
    })
  })

  describe('Responsive Behavior', () => {
    it('shows mobile navigation on mobile viewport', () => {
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 375,
      })

      render(
        <BrowserRouter>
          <Layout>Content</Layout>
        </BrowserRouter>
      )

      expect(screen.getByRole('navigation', { name: 'Mobile navigation' })).toBeInTheDocument()
      expect(screen.queryByRole('navigation', { name: 'Desktop navigation' })).not.toBeInTheDocument()
    })

    it('shows desktop navigation on desktop viewport', () => {
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 1024,
      })

      render(
        <BrowserRouter>
          <Layout>Content</Layout>
        </BrowserRouter>
      )

      expect(screen.getByRole('navigation', { name: 'Desktop navigation' })).toBeInTheDocument()
      expect(screen.queryByRole('navigation', { name: 'Mobile navigation' })).not.toBeInTheDocument()
    })

    it('shows bottom navigation only on mobile', () => {
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 375,
      })

      render(
        <BrowserRouter>
          <Layout>Content</Layout>
        </BrowserRouter>
      )

      expect(screen.getByRole('navigation', { name: 'Bottom navigation' })).toBeInTheDocument()
    })
  })

  describe('Keyboard Navigation', () => {
    it('all navigation links are keyboard accessible', () => {
      render(
        <BrowserRouter>
          <Layout>Content</Layout>
        </BrowserRouter>
      )

      const desktopNav = screen.getByRole('navigation', { name: 'Desktop navigation' })
      const links = within(desktopNav).getAllByRole('link')

      links.forEach(link => {
        link.focus()
        expect(document.activeElement).toBe(link)
      })
    })

    it('skip link is keyboard accessible', () => {
      render(
        <BrowserRouter>
          <Layout>Content</Layout>
        </BrowserRouter>
      )

      const skipLink = screen.getByText('Skip to main content')
      skipLink.focus()
      expect(document.activeElement).toBe(skipLink)
    })
  })

  describe('Accessibility Compliance', () => {
    it('has no accessibility violations (desktop)', async () => {
      const { container } = render(
        <BrowserRouter>
          <Layout>
            <h2>Page Content</h2>
            <p>This is the main content</p>
          </Layout>
        </BrowserRouter>
      )

      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })

    it('has no accessibility violations (mobile)', async () => {
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 375,
      })

      const { container } = render(
        <BrowserRouter>
          <Layout>
            <h2>Page Content</h2>
            <p>This is the main content</p>
          </Layout>
        </BrowserRouter>
      )

      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })

    it('all navigation elements have proper labels', () => {
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 375,
      })

      render(
        <BrowserRouter>
          <Layout>Content</Layout>
        </BrowserRouter>
      )

      expect(screen.getByRole('navigation', { name: 'Mobile navigation' })).toBeInTheDocument()
      expect(screen.getByRole('navigation', { name: 'Bottom navigation' })).toBeInTheDocument()
    })

    it('maintains proper heading hierarchy', () => {
      render(
        <BrowserRouter>
          <Layout>
            <h2>Section Title</h2>
            <p>Content</p>
          </Layout>
        </BrowserRouter>
      )

      const h1 = screen.getByRole('heading', { level: 1 })
      expect(h1).toBeInTheDocument()

      const h2 = screen.getByRole('heading', { level: 2 })
      expect(h2).toBeInTheDocument()
    })
  })

  describe('Dark Mode', () => {
    it('bottom navigation has dark mode styles', () => {
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 375,
      })

      render(
        <BrowserRouter>
          <Layout>Content</Layout>
        </BrowserRouter>
      )

      const bottomNav = screen.getByRole('navigation', { name: 'Bottom navigation' })
      expect(bottomNav.className).toContain('dark:bg-lsc-dark')
    })
  })

  describe('Edge Cases', () => {
    it('handles empty children', () => {
      render(
        <BrowserRouter>
          <Layout>{null}</Layout>
        </BrowserRouter>
      )

      const main = screen.getByRole('main')
      expect(main).toBeInTheDocument()
    })

    it('handles multiple child elements', () => {
      render(
        <BrowserRouter>
          <Layout>
            <div>First</div>
            <div>Second</div>
            <div>Third</div>
          </Layout>
        </BrowserRouter>
      )

      expect(screen.getByText('First')).toBeInTheDocument()
      expect(screen.getByText('Second')).toBeInTheDocument()
      expect(screen.getByText('Third')).toBeInTheDocument()
    })

    it('renders correctly with different route paths', () => {
      const paths = ['/catalog', '/events', '/programs', '/account']

      paths.forEach(path => {
        Object.defineProperty(window, 'location', {
          writable: true,
          value: { pathname: path },
        })

        const { unmount } = render(
          <MemoryRouter initialEntries={[path]}>
            <Layout>Content for {path}</Layout>
          </MemoryRouter>
        )

        expect(screen.getByRole('navigation', { name: 'Breadcrumb' })).toBeInTheDocument()
        unmount()
      })
    })
  })

  describe('Integration', () => {
    it('skip link navigates to main content', () => {
      render(
        <BrowserRouter>
          <Layout>
            <h2>Main Content</h2>
          </Layout>
        </BrowserRouter>
      )

      const skipLink = screen.getByText('Skip to main content')
      const main = screen.getByRole('main')

      expect(skipLink.getAttribute('href')).toBe('#main-content')
      expect(main.id).toBe('main-content')
    })

    it('navigation and content work together', () => {
      render(
        <BrowserRouter>
          <Layout>
            <h2>Page Title</h2>
            <p>Page content goes here</p>
          </Layout>
        </BrowserRouter>
      )

      // Navigation should be present
      expect(screen.getByRole('navigation', { name: 'Desktop navigation' })).toBeInTheDocument()

      // Content should be in main
      const main = screen.getByRole('main')
      expect(within(main).getByText('Page Title')).toBeInTheDocument()
      expect(within(main).getByText('Page content goes here')).toBeInTheDocument()
    })
  })
})
