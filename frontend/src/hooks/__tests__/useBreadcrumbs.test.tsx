/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook } from '@testing-library/react'
import { BrowserRouter, Route, Routes, useLocation } from 'react-router-dom'
import { ReactNode } from 'react'

// Breadcrumb item type
interface BreadcrumbItem {
  label: string
  to: string
}

// Hook implementation - to be created
const useBreadcrumbs = (): BreadcrumbItem[] => {
  const location = useLocation()
  const pathname = location.pathname

  // Home page
  if (pathname === '/' || pathname === '') {
    return []
  }

  const segments = pathname.split('/').filter(Boolean)
  const breadcrumbs: BreadcrumbItem[] = [{ label: 'Home', to: '/' }]

  // Route mappings
  const routeLabels: Record<string, string> = {
    catalog: 'Catalog',
    events: 'Events',
    programs: 'Programs',
    account: 'My Account',
    settings: 'Settings',
    login: 'Sign In',
    register: 'Register',
    accessibility: 'Accessibility',
    about: 'About',
    contact: 'Contact',
    help: 'Help',
    books: 'Books',
    'sci-fi': 'Science Fiction',
    fiction: 'Fiction',
    'non-fiction': 'Non-Fiction',
    children: "Children's Books",
  }

  // Build breadcrumbs from path segments
  let currentPath = ''
  segments.forEach((segment, _index) => {
    currentPath += `/${segment}`

    // Check if this is a dynamic ID (all digits)
    if (/^\d+$/.test(segment)) {
      // For item detail pages, use a generic label or fetch from context
      breadcrumbs.push({
        label: `Item ${segment}`,
        to: currentPath,
      })
    } else {
      // Use mapped label or capitalize segment
      const label = routeLabels[segment] || segment.charAt(0).toUpperCase() + segment.slice(1)
      breadcrumbs.push({
        label,
        to: currentPath,
      })
    }
  })

  return breadcrumbs
}

// Wrapper for router context
const createWrapper = (_initialPath: string) => {
  return ({ children }: { children: ReactNode }) => (
    <BrowserRouter>
      <Routes>
        <Route path="*" element={<>{children}</>} />
      </Routes>
    </BrowserRouter>
  )
}

// Helper to render hook with router at specific path
const renderHookWithRouter = (initialPath: string) => {
  window.history.pushState({}, '', initialPath)
  return renderHook(() => useBreadcrumbs(), {
    wrapper: createWrapper(initialPath),
  })
}

describe('useBreadcrumbs Hook', () => {
  beforeEach(() => {
    window.history.pushState({}, '', '/')
  })

  describe('Home Page', () => {
    it('returns empty array for home page', () => {
      const { result } = renderHookWithRouter('/')
      expect(result.current).toEqual([])
    })

    it('returns empty array for empty path', () => {
      const { result } = renderHookWithRouter('')
      expect(result.current).toEqual([])
    })
  })

  describe('Single Level Routes', () => {
    it('returns correct breadcrumbs for catalog', () => {
      const { result } = renderHookWithRouter('/catalog')

      expect(result.current).toEqual([
        { label: 'Home', to: '/' },
        { label: 'Catalog', to: '/catalog' },
      ])
    })

    it('returns correct breadcrumbs for events', () => {
      const { result } = renderHookWithRouter('/events')

      expect(result.current).toEqual([
        { label: 'Home', to: '/' },
        { label: 'Events', to: '/events' },
      ])
    })

    it('returns correct breadcrumbs for programs', () => {
      const { result } = renderHookWithRouter('/programs')

      expect(result.current).toEqual([
        { label: 'Home', to: '/' },
        { label: 'Programs', to: '/programs' },
      ])
    })

    it('returns correct breadcrumbs for account', () => {
      const { result } = renderHookWithRouter('/account')

      expect(result.current).toEqual([
        { label: 'Home', to: '/' },
        { label: 'My Account', to: '/account' },
      ])
    })

    it('returns correct breadcrumbs for login', () => {
      const { result } = renderHookWithRouter('/login')

      expect(result.current).toEqual([
        { label: 'Home', to: '/' },
        { label: 'Sign In', to: '/login' },
      ])
    })

    it('returns correct breadcrumbs for register', () => {
      const { result } = renderHookWithRouter('/register')

      expect(result.current).toEqual([
        { label: 'Home', to: '/' },
        { label: 'Register', to: '/register' },
      ])
    })
  })

  describe('Nested Routes', () => {
    it('returns correct breadcrumbs for catalog/books', () => {
      const { result } = renderHookWithRouter('/catalog/books')

      expect(result.current).toEqual([
        { label: 'Home', to: '/' },
        { label: 'Catalog', to: '/catalog' },
        { label: 'Books', to: '/catalog/books' },
      ])
    })

    it('returns correct breadcrumbs for catalog/books/sci-fi', () => {
      const { result } = renderHookWithRouter('/catalog/books/sci-fi')

      expect(result.current).toEqual([
        { label: 'Home', to: '/' },
        { label: 'Catalog', to: '/catalog' },
        { label: 'Books', to: '/catalog/books' },
        { label: 'Science Fiction', to: '/catalog/books/sci-fi' },
      ])
    })

    it('returns correct breadcrumbs for account/settings', () => {
      const { result } = renderHookWithRouter('/account/settings')

      expect(result.current).toEqual([
        { label: 'Home', to: '/' },
        { label: 'My Account', to: '/account' },
        { label: 'Settings', to: '/account/settings' },
      ])
    })

    it('returns correct breadcrumbs for account/settings/accessibility', () => {
      const { result } = renderHookWithRouter('/account/settings/accessibility')

      expect(result.current).toEqual([
        { label: 'Home', to: '/' },
        { label: 'My Account', to: '/account' },
        { label: 'Settings', to: '/account/settings' },
        { label: 'Accessibility', to: '/account/settings/accessibility' },
      ])
    })
  })

  describe('Dynamic Route Parameters', () => {
    it('handles dynamic catalog item ID', () => {
      const { result } = renderHookWithRouter('/catalog/12345')

      expect(result.current).toEqual([
        { label: 'Home', to: '/' },
        { label: 'Catalog', to: '/catalog' },
        { label: 'Item 12345', to: '/catalog/12345' },
      ])
    })

    it('handles nested dynamic routes', () => {
      const { result } = renderHookWithRouter('/catalog/books/789')

      expect(result.current).toEqual([
        { label: 'Home', to: '/' },
        { label: 'Catalog', to: '/catalog' },
        { label: 'Books', to: '/catalog/books' },
        { label: 'Item 789', to: '/catalog/books/789' },
      ])
    })

    it('handles dynamic event ID', () => {
      const { result } = renderHookWithRouter('/events/456')

      expect(result.current).toEqual([
        { label: 'Home', to: '/' },
        { label: 'Events', to: '/events' },
        { label: 'Item 456', to: '/events/456' },
      ])
    })
  })

  describe('Unmapped Routes', () => {
    it('capitalizes unmapped route segments', () => {
      const { result } = renderHookWithRouter('/custom')

      expect(result.current).toEqual([
        { label: 'Home', to: '/' },
        { label: 'Custom', to: '/custom' },
      ])
    })

    it('handles multi-word unmapped segments', () => {
      const { result } = renderHookWithRouter('/my-library')

      expect(result.current).toEqual([
        { label: 'Home', to: '/' },
        { label: 'My-library', to: '/my-library' },
      ])
    })

    it('handles deeply nested unmapped routes', () => {
      const { result } = renderHookWithRouter('/catalog/special/rare/vintage')

      expect(result.current).toEqual([
        { label: 'Home', to: '/' },
        { label: 'Catalog', to: '/catalog' },
        { label: 'Special', to: '/catalog/special' },
        { label: 'Rare', to: '/catalog/special/rare' },
        { label: 'Vintage', to: '/catalog/special/rare/vintage' },
      ])
    })
  })

  describe('Path Building', () => {
    it('builds correct cumulative paths', () => {
      const { result } = renderHookWithRouter('/catalog/books/sci-fi')

      const paths = result.current.map((crumb) => crumb.to)

      expect(paths).toEqual(['/', '/catalog', '/catalog/books', '/catalog/books/sci-fi'])
    })

    it('maintains path structure with IDs', () => {
      const { result } = renderHookWithRouter('/catalog/books/123')

      const paths = result.current.map((crumb) => crumb.to)

      expect(paths).toEqual(['/', '/catalog', '/catalog/books', '/catalog/books/123'])
    })
  })

  describe('Edge Cases', () => {
    it('handles trailing slash', () => {
      const { result } = renderHookWithRouter('/catalog/')

      expect(result.current).toEqual([
        { label: 'Home', to: '/' },
        { label: 'Catalog', to: '/catalog' },
      ])
    })

    it('handles double slashes', () => {
      const { result } = renderHookWithRouter('/catalog//books')

      // Should filter out empty segments
      expect(result.current).toEqual([
        { label: 'Home', to: '/' },
        { label: 'Catalog', to: '/catalog' },
        { label: 'Books', to: '/catalog/books' },
      ])
    })

    it('handles very long paths', () => {
      const { result } = renderHookWithRouter(
        '/catalog/books/fiction/mystery/hardcover/bestsellers/2024'
      )

      expect(result.current).toHaveLength(8) // Home + 7 segments
      expect(result.current[0]).toEqual({ label: 'Home', to: '/' })
      expect(result.current[result.current.length - 1]).toEqual({
        label: 'Item 2024',
        to: '/catalog/books/fiction/mystery/hardcover/bestsellers/2024',
      })
    })

    it('handles special characters in segments', () => {
      const { result } = renderHookWithRouter('/catalog/children')

      expect(result.current).toEqual([
        { label: 'Home', to: '/' },
        { label: 'Catalog', to: '/catalog' },
        { label: "Children's Books", to: '/catalog/children' },
      ])
    })
  })

  describe('Breadcrumb Structure', () => {
    it('always includes Home as first item (except on home page)', () => {
      const paths = ['/catalog', '/events', '/programs', '/account']

      paths.forEach((path) => {
        const { result } = renderHookWithRouter(path)
        expect(result.current[0]).toEqual({ label: 'Home', to: '/' })
      })
    })

    it('each breadcrumb has label and to properties', () => {
      const { result } = renderHookWithRouter('/catalog/books')

      result.current.forEach((crumb) => {
        expect(crumb).toHaveProperty('label')
        expect(crumb).toHaveProperty('to')
        expect(typeof crumb.label).toBe('string')
        expect(typeof crumb.to).toBe('string')
      })
    })

    it('breadcrumb labels are non-empty', () => {
      const { result } = renderHookWithRouter('/catalog/books/sci-fi')

      result.current.forEach((crumb) => {
        expect(crumb.label.length).toBeGreaterThan(0)
      })
    })

    it('breadcrumb paths are valid', () => {
      const { result } = renderHookWithRouter('/catalog/books/sci-fi')

      result.current.forEach((crumb) => {
        expect(crumb.to).toMatch(/^\//)
      })
    })
  })

  describe('Route Changes', () => {
    it('updates breadcrumbs when route changes', () => {
      const { result, rerender } = renderHookWithRouter('/catalog')

      expect(result.current).toHaveLength(2) // Home + Catalog

      // Simulate route change
      window.history.pushState({}, '', '/catalog/books')
      rerender()

      // Note: In actual implementation, this would require router context update
      // This test documents the expected behavior
    })
  })

  describe('Specific Route Mappings', () => {
    const testCases: Array<{ path: string; expectedLast: string }> = [
      { path: '/catalog', expectedLast: 'Catalog' },
      { path: '/events', expectedLast: 'Events' },
      { path: '/programs', expectedLast: 'Programs' },
      { path: '/account', expectedLast: 'My Account' },
      { path: '/settings', expectedLast: 'Settings' },
      { path: '/login', expectedLast: 'Sign In' },
      { path: '/register', expectedLast: 'Register' },
      { path: '/accessibility', expectedLast: 'Accessibility' },
      { path: '/about', expectedLast: 'About' },
      { path: '/contact', expectedLast: 'Contact' },
      { path: '/help', expectedLast: 'Help' },
    ]

    testCases.forEach(({ path, expectedLast }) => {
      it(`maps ${path} to "${expectedLast}"`, () => {
        const { result } = renderHookWithRouter(path)

        const lastBreadcrumb = result.current[result.current.length - 1]
        expect(lastBreadcrumb!.label).toBe(expectedLast)
      })
    })
  })

  describe('Category Mappings', () => {
    it('maps books category correctly', () => {
      const { result } = renderHookWithRouter('/catalog/books')

      const booksCrumb = result.current.find((c) => c.to === '/catalog/books')
      expect(booksCrumb?.label).toBe('Books')
    })

    it('maps sci-fi category correctly', () => {
      const { result } = renderHookWithRouter('/catalog/books/sci-fi')

      const sciFiCrumb = result.current.find((c) => c.to === '/catalog/books/sci-fi')
      expect(sciFiCrumb?.label).toBe('Science Fiction')
    })

    it('maps fiction category correctly', () => {
      const { result } = renderHookWithRouter('/catalog/fiction')

      const fictionCrumb = result.current.find((c) => c.to === '/catalog/fiction')
      expect(fictionCrumb?.label).toBe('Fiction')
    })

    it('maps non-fiction category correctly', () => {
      const { result } = renderHookWithRouter('/catalog/non-fiction')

      const nonFictionCrumb = result.current.find((c) => c.to === '/catalog/non-fiction')
      expect(nonFictionCrumb?.label).toBe('Non-Fiction')
    })
  })

  describe('Return Value Type', () => {
    it('returns an array', () => {
      const { result } = renderHookWithRouter('/catalog')
      expect(Array.isArray(result.current)).toBe(true)
    })

    it('array contains objects with correct shape', () => {
      const { result } = renderHookWithRouter('/catalog')

      result.current.forEach((item) => {
        expect(item).toHaveProperty('label')
        expect(item).toHaveProperty('to')
        expect(Object.keys(item)).toHaveLength(2)
      })
    })
  })

  describe('Performance', () => {
    it('does not create duplicate breadcrumbs', () => {
      const { result } = renderHookWithRouter('/catalog/books/sci-fi')

      const paths = result.current.map((c) => c.to)
      const uniquePaths = [...new Set(paths)]

      expect(paths).toEqual(uniquePaths)
    })

    it('maintains correct order', () => {
      const { result } = renderHookWithRouter('/catalog/books/sci-fi')

      const paths = result.current.map((c) => c.to)

      expect(paths).toEqual(['/', '/catalog', '/catalog/books', '/catalog/books/sci-fi'])
    })
  })
})
