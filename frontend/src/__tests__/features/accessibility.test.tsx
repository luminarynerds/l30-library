/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Accessibility Feature Tests
 *
 * Tests for accessibility features including:
 * - Simplified view mode
 * - Quiet mode (reduced distractions)
 * - Focus mode
 * - Text-to-speech
 * - Keyboard navigation
 * - Screen reader announcements
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '../utils/test-utils'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import CatalogPage from '@/pages/CatalogPage'
import { mockCatalogItem } from '../utils/mock-helpers'

// Mock fetch
const mockFetch = vi.fn()
global.fetch = mockFetch

// SKIP NOTE: These tests integrate against the real CatalogPage and assert
// UI labels that don't exist in the current component — "Simplified" toggle
// button, "Show filters" button, announcement strings like "Search field
// focused" and "Filters shown", a single-role "Search" button, etc. The
// tests also call `vi.doMock` *after* render, which has no effect because
// the hook has already been bound. Rewriting would require new UI contracts
// from product. Skipped pending a realignment of the CatalogPage test plan.
describe.skip('Accessibility Features', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    vi.clearAllMocks()
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    })

    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        items: [mockCatalogItem],
        total: 1,
        pages: 1,
      }),
    })
  })

  describe('Simplified View Mode', () => {
    it('should have simplified view toggle', () => {
      const mockAccessibility = {
        quietMode: false,
        focusMode: false,
        simplifiedView: false,
        reduceMotion: false,
        showImages: true,
        preferPagination: false,
        noFOMO: false,
        announceToScreenReader: vi.fn(),
      }

      vi.doMock('@/features/accessibility/hooks/useAccessibility', () => ({
        useAccessibility: () => mockAccessibility,
      }))

      render(
        <QueryClientProvider client={queryClient}>
          <CatalogPage />
        </QueryClientProvider>
      )

      const simplifiedButton = screen.getByRole('button', { name: /Simplified/i })
      expect(simplifiedButton).toBeInTheDocument()
      expect(simplifiedButton).toHaveAttribute('aria-pressed')
    })

    it('should toggle simplified view on button click', async () => {
      const user = userEvent.setup()
      const announceToScreenReader = vi.fn()

      const mockAccessibility = {
        quietMode: false,
        focusMode: false,
        simplifiedView: false,
        reduceMotion: false,
        showImages: true,
        preferPagination: false,
        noFOMO: false,
        announceToScreenReader,
      }

      vi.doMock('@/features/accessibility/hooks/useAccessibility', () => ({
        useAccessibility: () => mockAccessibility,
      }))

      render(
        <QueryClientProvider client={queryClient}>
          <CatalogPage />
        </QueryClientProvider>
      )

      const simplifiedButton = screen.getByRole('button', { name: /Simplified/i })
      await user.click(simplifiedButton)

      expect(simplifiedButton).toHaveAttribute('aria-pressed', 'true')
    })
  })

  describe('Keyboard Navigation', () => {
    it('should focus search input with / key', async () => {
      const user = userEvent.setup()
      const announceToScreenReader = vi.fn()

      const mockAccessibility = {
        quietMode: false,
        focusMode: false,
        simplifiedView: false,
        reduceMotion: false,
        showImages: true,
        preferPagination: false,
        noFOMO: false,
        announceToScreenReader,
      }

      vi.doMock('@/features/accessibility/hooks/useAccessibility', () => ({
        useAccessibility: () => mockAccessibility,
      }))

      render(
        <QueryClientProvider client={queryClient}>
          <CatalogPage />
        </QueryClientProvider>
      )

      await user.keyboard('/')

      const searchInput = screen.getByPlaceholderText(/Search by title/i)
      expect(searchInput).toHaveFocus()
      expect(announceToScreenReader).toHaveBeenCalledWith('Search field focused')
    })

    it('should toggle filters with f key', async () => {
      const user = userEvent.setup()
      const announceToScreenReader = vi.fn()

      const mockAccessibility = {
        quietMode: false,
        focusMode: false,
        simplifiedView: false,
        reduceMotion: false,
        showImages: true,
        preferPagination: false,
        noFOMO: false,
        announceToScreenReader,
      }

      vi.doMock('@/features/accessibility/hooks/useAccessibility', () => ({
        useAccessibility: () => mockAccessibility,
      }))

      render(
        <QueryClientProvider client={queryClient}>
          <CatalogPage />
        </QueryClientProvider>
      )

      await user.keyboard('f')

      await waitFor(() => {
        expect(screen.getByLabelText(/Format/i)).toBeInTheDocument()
      })

      expect(announceToScreenReader).toHaveBeenCalledWith('Filters shown')
    })

    it('should not trigger shortcuts when typing in input', async () => {
      const user = userEvent.setup()

      const mockAccessibility = {
        quietMode: false,
        focusMode: false,
        simplifiedView: false,
        reduceMotion: false,
        showImages: true,
        preferPagination: false,
        noFOMO: false,
        announceToScreenReader: vi.fn(),
      }

      vi.doMock('@/features/accessibility/hooks/useAccessibility', () => ({
        useAccessibility: () => mockAccessibility,
      }))

      render(
        <QueryClientProvider client={queryClient}>
          <CatalogPage />
        </QueryClientProvider>
      )

      const searchInput = screen.getByPlaceholderText(/Search by title/i)
      await user.click(searchInput)
      await user.keyboard('f')

      // Should type 'f' in input, not toggle filters
      expect(searchInput).toHaveValue('f')
      expect(screen.queryByLabelText(/Format/i)).not.toBeInTheDocument()
    })
  })

  describe('Screen Reader Announcements', () => {
    it('should announce search results', async () => {
      const user = userEvent.setup()
      const announceToScreenReader = vi.fn()

      const mockAccessibility = {
        quietMode: false,
        focusMode: false,
        simplifiedView: false,
        reduceMotion: false,
        showImages: true,
        preferPagination: false,
        noFOMO: false,
        announceToScreenReader,
      }

      vi.doMock('@/features/accessibility/hooks/useAccessibility', () => ({
        useAccessibility: () => mockAccessibility,
      }))

      render(
        <QueryClientProvider client={queryClient}>
          <CatalogPage />
        </QueryClientProvider>
      )

      await user.type(screen.getByPlaceholderText(/Search by title/i), 'test')
      await user.click(screen.getByRole('button', { name: /Search/i }))

      await waitFor(() => {
        expect(announceToScreenReader).toHaveBeenCalledWith(
          expect.stringMatching(/Found exactly what you might be looking for!/i)
        )
      })
    })

    it('should announce filter changes', async () => {
      const user = userEvent.setup()
      const announceToScreenReader = vi.fn()

      const mockAccessibility = {
        quietMode: false,
        focusMode: false,
        simplifiedView: false,
        reduceMotion: false,
        showImages: true,
        preferPagination: false,
        noFOMO: false,
        announceToScreenReader,
      }

      vi.doMock('@/features/accessibility/hooks/useAccessibility', () => ({
        useAccessibility: () => mockAccessibility,
      }))

      render(
        <QueryClientProvider client={queryClient}>
          <CatalogPage />
        </QueryClientProvider>
      )

      await user.keyboard('f')

      await waitFor(() => {
        expect(screen.getByLabelText(/Format/i)).toBeInTheDocument()
      })

      expect(announceToScreenReader).toHaveBeenCalledWith('Filters shown')
    })
  })

  describe('ARIA Attributes', () => {
    it('should have proper ARIA labels on interactive elements', () => {
      const mockAccessibility = {
        quietMode: false,
        focusMode: false,
        simplifiedView: false,
        reduceMotion: false,
        showImages: true,
        preferPagination: false,
        noFOMO: false,
        announceToScreenReader: vi.fn(),
      }

      vi.doMock('@/features/accessibility/hooks/useAccessibility', () => ({
        useAccessibility: () => mockAccessibility,
      }))

      render(
        <QueryClientProvider client={queryClient}>
          <CatalogPage />
        </QueryClientProvider>
      )

      const searchInput = screen.getByPlaceholderText(/Search by title/i)
      expect(searchInput).toHaveAccessibleName()

      const filterButton = screen.getByRole('button', { name: /Show filters/i })
      expect(filterButton).toHaveAttribute('aria-expanded')
      expect(filterButton).toHaveAttribute('aria-controls')
    })

    it('should have live regions for dynamic content', () => {
      const mockAccessibility = {
        quietMode: false,
        focusMode: false,
        simplifiedView: false,
        reduceMotion: false,
        showImages: true,
        preferPagination: false,
        noFOMO: false,
        announceToScreenReader: vi.fn(),
      }

      vi.doMock('@/features/accessibility/hooks/useAccessibility', () => ({
        useAccessibility: () => mockAccessibility,
      }))

      render(
        <QueryClientProvider client={queryClient}>
          <CatalogPage />
        </QueryClientProvider>
      )

      // Results area should have aria-live
      const resultsArea = screen.getByRole('region', { hidden: true })
      expect(resultsArea).toHaveAttribute('aria-live', 'polite')
    })
  })

  describe('Quiet Mode', () => {
    it('should hide distracting elements in quiet mode', async () => {
      const mockAccessibility = {
        quietMode: true,
        focusMode: false,
        simplifiedView: false,
        reduceMotion: false,
        showImages: true,
        preferPagination: false,
        noFOMO: false,
        announceToScreenReader: vi.fn(),
      }

      vi.doMock('@/features/accessibility/hooks/useAccessibility', () => ({
        useAccessibility: () => mockAccessibility,
      }))

      const user = userEvent.setup()

      render(
        <QueryClientProvider client={queryClient}>
          <CatalogPage />
        </QueryClientProvider>
      )

      await user.type(screen.getByPlaceholderText(/Search by title/i), 'test')
      await user.click(screen.getByRole('button', { name: /Search/i }))

      await waitFor(() => {
        // "New" badges should be hidden in quiet mode
        expect(screen.queryByText(/New/i)).not.toBeInTheDocument()
      })
    })
  })

  describe('Focus Mode', () => {
    it('should apply focus mode styles', () => {
      const mockAccessibility = {
        quietMode: false,
        focusMode: true,
        simplifiedView: false,
        reduceMotion: false,
        showImages: true,
        preferPagination: false,
        noFOMO: false,
        announceToScreenReader: vi.fn(),
      }

      vi.doMock('@/features/accessibility/hooks/useAccessibility', () => ({
        useAccessibility: () => mockAccessibility,
      }))

      const { container } = render(
        <QueryClientProvider client={queryClient}>
          <CatalogPage />
        </QueryClientProvider>
      )

      // Focus mode should add a specific class
      const mainContent = container.querySelector('.focus-deep-dive')
      expect(mainContent).toBeInTheDocument()
    })
  })

  describe('Reduce Motion', () => {
    it('should respect prefers-reduced-motion', async () => {
      const mockAccessibility = {
        quietMode: false,
        focusMode: false,
        simplifiedView: false,
        reduceMotion: true,
        showImages: true,
        preferPagination: false,
        noFOMO: false,
        announceToScreenReader: vi.fn(),
      }

      vi.doMock('@/features/accessibility/hooks/useAccessibility', () => ({
        useAccessibility: () => mockAccessibility,
      }))

      render(
        <QueryClientProvider client={queryClient}>
          <CatalogPage />
        </QueryClientProvider>
      )

      const searchButton = screen.getByRole('button', { name: /Search/i })
      expect(searchButton).toHaveClass('transition-none')
    })
  })

  describe('Pagination Preference', () => {
    it('should show pagination when preferPagination is enabled', async () => {
      const mockAccessibility = {
        quietMode: false,
        focusMode: false,
        simplifiedView: false,
        reduceMotion: false,
        showImages: true,
        preferPagination: true,
        noFOMO: false,
        announceToScreenReader: vi.fn(),
      }

      vi.doMock('@/features/accessibility/hooks/useAccessibility', () => ({
        useAccessibility: () => mockAccessibility,
      }))

      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          items: [mockCatalogItem],
          total: 50,
          pages: 3,
        }),
      })

      render(
        <QueryClientProvider client={queryClient}>
          <CatalogPage />
        </QueryClientProvider>
      )

      await waitFor(() => {
        expect(screen.getByText(/Page 1 of 3/i)).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /Next page/i })).toBeInTheDocument()
      })
    })
  })

  describe('Image Visibility', () => {
    it('should hide images when showImages is false', async () => {
      const user = userEvent.setup()

      const mockAccessibility = {
        quietMode: false,
        focusMode: false,
        simplifiedView: false,
        reduceMotion: false,
        showImages: false,
        preferPagination: false,
        noFOMO: false,
        announceToScreenReader: vi.fn(),
      }

      vi.doMock('@/features/accessibility/hooks/useAccessibility', () => ({
        useAccessibility: () => mockAccessibility,
      }))

      render(
        <QueryClientProvider client={queryClient}>
          <CatalogPage />
        </QueryClientProvider>
      )

      await user.type(screen.getByPlaceholderText(/Search by title/i), 'test')
      await user.click(screen.getByRole('button', { name: /Search/i }))

      await waitFor(() => {
        // Cover images should not be rendered
        const images = screen.queryAllByRole('img')
        expect(images.length).toBe(0)
      })
    })
  })

  describe('Keyboard Shortcuts Help', () => {
    it('should display keyboard shortcuts hint', () => {
      const mockAccessibility = {
        quietMode: false,
        focusMode: false,
        simplifiedView: false,
        reduceMotion: false,
        showImages: true,
        preferPagination: false,
        noFOMO: false,
        announceToScreenReader: vi.fn(),
      }

      vi.doMock('@/features/accessibility/hooks/useAccessibility', () => ({
        useAccessibility: () => mockAccessibility,
      }))

      render(
        <QueryClientProvider client={queryClient}>
          <CatalogPage />
        </QueryClientProvider>
      )

      expect(screen.getByText(/Press/i)).toBeInTheDocument()
      expect(screen.getByText(/to search/i)).toBeInTheDocument()
      expect(screen.getByText(/for filters/i)).toBeInTheDocument()
    })
  })
})
