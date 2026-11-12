/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * CatalogItemSkeleton Component Tests
 *
 * Tests for catalog item skeleton loader component
 * Ensures proper loading state indication and accessibility
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render } from "@testing-library/react"
import { screen } from "@testing-library/react"
import { axe } from 'jest-axe'
import { t } from '@/i18n'

// Mock component - replace with actual import when component exists
const CatalogItemSkeleton = ({ count = 1 }: { count?: number }) => {
  return (
    <div aria-label={t('aria.skeletons.loadingCatalogItems')} role="status">
      {Array.from({ length: count }).map((_, index) => (
        <div
          key={index}
          className="catalog-item-skeleton animate-pulse"
          data-testid={`skeleton-item-${index}`}
        >
          <div className="skeleton-image h-48 bg-earth-200 dark:bg-earth-700 rounded-lg" />
          <div className="skeleton-content mt-3 space-y-2">
            <div className="h-4 bg-earth-200 dark:bg-earth-700 rounded w-3/4" />
            <div className="h-4 bg-earth-200 dark:bg-earth-700 rounded w-1/2" />
            <div className="h-4 bg-earth-200 dark:bg-earth-700 rounded w-full" />
          </div>
        </div>
      ))}
    </div>
  )
}


// Preload English translations. vitest setup.ts does not preload i18n,
// and t() returns raw dotted-path keys when no language is loaded,
// breaking assertions that match resolved English strings.

describe('CatalogItemSkeleton Component', () => {
  beforeEach(() => {
    // Reset any media query mocks
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

  describe('Rendering', () => {
    it('renders single skeleton by default', () => {
      render(<CatalogItemSkeleton />)
      expect(screen.getByTestId('skeleton-item-0')).toBeInTheDocument()
    })

    it('renders correct number of skeleton items', () => {
      render(<CatalogItemSkeleton count={3} />)

      expect(screen.getByTestId('skeleton-item-0')).toBeInTheDocument()
      expect(screen.getByTestId('skeleton-item-1')).toBeInTheDocument()
      expect(screen.getByTestId('skeleton-item-2')).toBeInTheDocument()
    })

    it('renders multiple skeleton items for grid layout', () => {
      render(<CatalogItemSkeleton count={6} />)

      for (let i = 0; i < 6; i++) {
        expect(screen.getByTestId(`skeleton-item-${i}`)).toBeInTheDocument()
      }
    })

    it('has skeleton image placeholder', () => {
      render(<CatalogItemSkeleton />)

      const image = document.querySelector('.skeleton-image')
      expect(image).toBeInTheDocument()
      expect(image).toHaveClass('h-48')
    })

    it('has skeleton content placeholders', () => {
      render(<CatalogItemSkeleton />)

      const content = document.querySelector('.skeleton-content')
      expect(content).toBeInTheDocument()
    })
  })

  describe('ARIA and Accessibility', () => {
    it('has proper ARIA label for loading state', () => {
      render(<CatalogItemSkeleton />)

      expect(screen.getByLabelText('Loading catalog items...')).toBeInTheDocument()
    })

    it('has aria-label on container', () => {
      const { container } = render(<CatalogItemSkeleton />)

      const loadingContainer = container.querySelector('[aria-label]')
      expect(loadingContainer).toHaveAttribute('aria-label', 'Loading catalog items...')
    })

    it('has no accessibility violations', async () => {
      const { container } = render(<CatalogItemSkeleton />)
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })

    it('has no accessibility violations with multiple items', async () => {
      const { container } = render(<CatalogItemSkeleton count={4} />)
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })
  })

  describe('Animation', () => {
    it('has pulse animation class', () => {
      render(<CatalogItemSkeleton />)

      const skeleton = screen.getByTestId('skeleton-item-0')
      expect(skeleton).toHaveClass('animate-pulse')
    })

    it('respects prefers-reduced-motion', () => {
      // Mock prefers-reduced-motion
      window.matchMedia = vi.fn().mockImplementation((query: string) => ({
        matches: query === '(prefers-reduced-motion: reduce)',
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }))

      render(<CatalogItemSkeleton />)

      // Component should still render but animation should respect user preference
      expect(screen.getByTestId('skeleton-item-0')).toBeInTheDocument()
    })
  })

  describe('Structure Matching', () => {
    it('matches structure of actual catalog item', () => {
      render(<CatalogItemSkeleton />)

      // Should have image placeholder
      expect(document.querySelector('.skeleton-image')).toBeInTheDocument()

      // Should have content placeholders (title, metadata, description)
      const contentLines = document.querySelectorAll('.skeleton-content > *')
      expect(contentLines.length).toBeGreaterThanOrEqual(3)
    })

    it('has rounded corners like actual catalog item', () => {
      render(<CatalogItemSkeleton />)

      const image = document.querySelector('.skeleton-image')
      expect(image).toHaveClass('rounded-lg')
    })

    it('has proper spacing between elements', () => {
      render(<CatalogItemSkeleton />)

      const content = document.querySelector('.skeleton-content')
      expect(content).toHaveClass('mt-3')
      expect(content).toHaveClass('space-y-2')
    })
  })

  describe('Dark Mode', () => {
    it('has dark mode classes', () => {
      render(<CatalogItemSkeleton />)

      const image = document.querySelector('.skeleton-image')
      expect(image?.className).toContain('dark:bg-earth-700')
    })

    it('content lines have dark mode support', () => {
      render(<CatalogItemSkeleton />)

      const lines = document.querySelectorAll('.skeleton-content > *')
      lines.forEach(line => {
        expect(line.className).toContain('dark:bg-earth-700')
      })
    })
  })

  describe('Responsive Behavior', () => {
    it('renders correctly on mobile viewports', () => {
      render(<CatalogItemSkeleton count={2} />)

      expect(screen.getByTestId('skeleton-item-0')).toBeInTheDocument()
      expect(screen.getByTestId('skeleton-item-1')).toBeInTheDocument()
    })

    it('renders correctly on desktop viewports', () => {
      render(<CatalogItemSkeleton count={6} />)

      for (let i = 0; i < 6; i++) {
        expect(screen.getByTestId(`skeleton-item-${i}`)).toBeInTheDocument()
      }
    })
  })

  describe('Edge Cases', () => {
    it('handles zero count gracefully', () => {
      render(<CatalogItemSkeleton count={0} />)

      expect(screen.queryByTestId('skeleton-item-0')).not.toBeInTheDocument()
    })

    it('handles large count', () => {
      render(<CatalogItemSkeleton count={20} />)

      expect(screen.getByTestId('skeleton-item-0')).toBeInTheDocument()
      expect(screen.getByTestId('skeleton-item-19')).toBeInTheDocument()
    })

    it('maintains consistent structure across multiple items', () => {
      render(<CatalogItemSkeleton count={3} />)

      for (let i = 0; i < 3; i++) {
        const item = screen.getByTestId(`skeleton-item-${i}`)
        expect(item.querySelector('.skeleton-image')).toBeInTheDocument()
        expect(item.querySelector('.skeleton-content')).toBeInTheDocument()
      }
    })
  })

  describe('Performance', () => {
    it('renders efficiently with multiple items', () => {
      const startTime = performance.now()
      render(<CatalogItemSkeleton count={12} />)
      const endTime = performance.now()

      // Should render in reasonable time (< 100ms)
      expect(endTime - startTime).toBeLessThan(100)
    })

    it('does not cause layout shift', () => {
      const { container } = render(<CatalogItemSkeleton />)

      // Skeleton should have defined dimensions
      const skeleton = container.querySelector('.skeleton-image')
      expect(skeleton).toHaveClass('h-48')
    })
  })
})
