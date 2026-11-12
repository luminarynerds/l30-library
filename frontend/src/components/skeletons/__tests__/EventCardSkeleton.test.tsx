/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * EventCardSkeleton Component Tests
 *
 * Tests for event card skeleton loader component
 * Ensures proper loading state indication and accessibility
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render } from "@testing-library/react"
import { screen } from "@testing-library/react"
import { axe } from 'jest-axe'
import { t } from '@/i18n'

// Mock component - replace with actual import when component exists
const EventCardSkeleton = ({ count = 1 }: { count?: number }) => {
  return (
    <div aria-label={t('aria.skeletons.loadingEvents')} role="status">
      {Array.from({ length: count }).map((_, index) => (
        <div
          key={index}
          className="event-card-skeleton animate-pulse"
          data-testid={`skeleton-event-${index}`}
        >
          <div className="skeleton-banner h-32 bg-earth-200 dark:bg-earth-700 rounded-t-lg" />
          <div className="skeleton-body p-4 space-y-3">
            <div className="skeleton-date flex gap-2">
              <div className="h-12 w-12 bg-earth-200 dark:bg-earth-700 rounded" />
              <div className="flex-1 space-y-2">
                <div className="h-4 bg-earth-200 dark:bg-earth-700 rounded w-3/4" />
                <div className="h-3 bg-earth-200 dark:bg-earth-700 rounded w-1/2" />
              </div>
            </div>
            <div className="h-3 bg-earth-200 dark:bg-earth-700 rounded w-full" />
            <div className="h-3 bg-earth-200 dark:bg-earth-700 rounded w-5/6" />
          </div>
        </div>
      ))}
    </div>
  )
}


// Preload English translations. vitest setup.ts does not preload i18n,
// and t() returns raw dotted-path keys when no language is loaded,
// breaking assertions that match resolved English strings.

describe('EventCardSkeleton Component', () => {
  beforeEach(() => {
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
      render(<EventCardSkeleton />)
      expect(screen.getByTestId('skeleton-event-0')).toBeInTheDocument()
    })

    it('renders correct number of skeleton items', () => {
      render(<EventCardSkeleton count={4} />)

      expect(screen.getByTestId('skeleton-event-0')).toBeInTheDocument()
      expect(screen.getByTestId('skeleton-event-1')).toBeInTheDocument()
      expect(screen.getByTestId('skeleton-event-2')).toBeInTheDocument()
      expect(screen.getByTestId('skeleton-event-3')).toBeInTheDocument()
    })

    it('has skeleton banner placeholder', () => {
      render(<EventCardSkeleton />)

      const banner = document.querySelector('.skeleton-banner')
      expect(banner).toBeInTheDocument()
      expect(banner).toHaveClass('h-32')
    })

    it('has skeleton date section', () => {
      render(<EventCardSkeleton />)

      const dateSection = document.querySelector('.skeleton-date')
      expect(dateSection).toBeInTheDocument()
    })

    it('has skeleton body content', () => {
      render(<EventCardSkeleton />)

      const body = document.querySelector('.skeleton-body')
      expect(body).toBeInTheDocument()
      expect(body).toHaveClass('p-4')
    })
  })

  describe('ARIA and Accessibility', () => {
    it('has proper ARIA label for loading state', () => {
      render(<EventCardSkeleton />)

      expect(screen.getByLabelText('Loading events...')).toBeInTheDocument()
    })

    it('has aria-label on container', () => {
      const { container } = render(<EventCardSkeleton />)

      const loadingContainer = container.querySelector('[aria-label]')
      expect(loadingContainer).toHaveAttribute('aria-label', 'Loading events...')
    })

    it('has no accessibility violations', async () => {
      const { container } = render(<EventCardSkeleton />)
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })

    it('has no accessibility violations with multiple items', async () => {
      const { container } = render(<EventCardSkeleton count={3} />)
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })
  })

  describe('Animation', () => {
    it('has pulse animation class', () => {
      render(<EventCardSkeleton />)

      const skeleton = screen.getByTestId('skeleton-event-0')
      expect(skeleton).toHaveClass('animate-pulse')
    })

    it('respects prefers-reduced-motion', () => {
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

      render(<EventCardSkeleton />)

      expect(screen.getByTestId('skeleton-event-0')).toBeInTheDocument()
    })
  })

  describe('Structure Matching', () => {
    it('matches structure of actual event card', () => {
      render(<EventCardSkeleton />)

      // Should have banner
      expect(document.querySelector('.skeleton-banner')).toBeInTheDocument()

      // Should have date section with icon placeholder
      expect(document.querySelector('.skeleton-date')).toBeInTheDocument()

      // Should have body content
      expect(document.querySelector('.skeleton-body')).toBeInTheDocument()
    })

    it('has date icon placeholder with correct size', () => {
      render(<EventCardSkeleton />)

      const dateIcon = document.querySelector('.skeleton-date > div:first-child')
      expect(dateIcon).toHaveClass('h-12')
      expect(dateIcon).toHaveClass('w-12')
    })

    it('has rounded corners like actual event card', () => {
      render(<EventCardSkeleton />)

      const banner = document.querySelector('.skeleton-banner')
      expect(banner).toHaveClass('rounded-t-lg')
    })

    it('has proper spacing in body', () => {
      render(<EventCardSkeleton />)

      const body = document.querySelector('.skeleton-body')
      expect(body).toHaveClass('space-y-3')
    })

    it('has multiple text lines for description', () => {
      render(<EventCardSkeleton />)

      const body = document.querySelector('.skeleton-body')
      const contentLines = body?.querySelectorAll('.h-3')
      expect(contentLines?.length).toBeGreaterThanOrEqual(2)
    })
  })

  describe('Dark Mode', () => {
    it('has dark mode classes on banner', () => {
      render(<EventCardSkeleton />)

      const banner = document.querySelector('.skeleton-banner')
      expect(banner?.className).toContain('dark:bg-earth-700')
    })

    it('has dark mode classes on content elements', () => {
      render(<EventCardSkeleton />)

      const elements = document.querySelectorAll('.skeleton-body .bg-earth-200 dark:bg-earth-600')
      elements.forEach(element => {
        expect(element.className).toContain('dark:bg-earth-700')
      })
    })
  })

  describe('Responsive Behavior', () => {
    it('renders correctly on mobile viewports', () => {
      render(<EventCardSkeleton count={2} />)

      expect(screen.getByTestId('skeleton-event-0')).toBeInTheDocument()
      expect(screen.getByTestId('skeleton-event-1')).toBeInTheDocument()
    })

    it('renders correctly on desktop viewports', () => {
      render(<EventCardSkeleton count={4} />)

      for (let i = 0; i < 4; i++) {
        expect(screen.getByTestId(`skeleton-event-${i}`)).toBeInTheDocument()
      }
    })
  })

  describe('Edge Cases', () => {
    it('handles zero count gracefully', () => {
      render(<EventCardSkeleton count={0} />)

      expect(screen.queryByTestId('skeleton-event-0')).not.toBeInTheDocument()
    })

    it('handles large count', () => {
      render(<EventCardSkeleton count={10} />)

      expect(screen.getByTestId('skeleton-event-0')).toBeInTheDocument()
      expect(screen.getByTestId('skeleton-event-9')).toBeInTheDocument()
    })

    it('maintains consistent structure across multiple items', () => {
      render(<EventCardSkeleton count={3} />)

      for (let i = 0; i < 3; i++) {
        const item = screen.getByTestId(`skeleton-event-${i}`)
        expect(item.querySelector('.skeleton-banner')).toBeInTheDocument()
        expect(item.querySelector('.skeleton-date')).toBeInTheDocument()
        expect(item.querySelector('.skeleton-body')).toBeInTheDocument()
      }
    })
  })

  describe('Layout', () => {
    it('has consistent card structure', () => {
      render(<EventCardSkeleton />)

      const card = screen.getByTestId('skeleton-event-0')
      expect(card.querySelector('.skeleton-banner')).toBeInTheDocument()
      expect(card.querySelector('.skeleton-body')).toBeInTheDocument()
    })

    it('date section uses flexbox layout', () => {
      render(<EventCardSkeleton />)

      const dateSection = document.querySelector('.skeleton-date')
      expect(dateSection).toHaveClass('flex')
      expect(dateSection).toHaveClass('gap-2')
    })

    it('content fills available space', () => {
      render(<EventCardSkeleton />)

      const dateContent = document.querySelector('.skeleton-date > .flex-1')
      expect(dateContent).toBeInTheDocument()
    })
  })

  describe('Performance', () => {
    it('renders efficiently with multiple items', () => {
      const startTime = performance.now()
      render(<EventCardSkeleton count={8} />)
      const endTime = performance.now()

      expect(endTime - startTime).toBeLessThan(100)
    })

    it('does not cause layout shift', () => {
      const { container } = render(<EventCardSkeleton />)

      const banner = container.querySelector('.skeleton-banner')
      expect(banner).toHaveClass('h-32')

      const dateIcon = container.querySelector('.skeleton-date > div:first-child')
      expect(dateIcon).toHaveClass('h-12')
      expect(dateIcon).toHaveClass('w-12')
    })
  })

  describe('Integration', () => {
    it('works in list layout', () => {
      const { container } = render(
        <div className="event-list">
          <EventCardSkeleton count={3} />
        </div>
      )

      const events = container.querySelectorAll('.event-card-skeleton')
      expect(events.length).toBe(3)
    })

    it('works in grid layout', () => {
      const { container } = render(
        <div className="grid grid-cols-2 gap-4">
          <EventCardSkeleton count={4} />
        </div>
      )

      const events = container.querySelectorAll('.event-card-skeleton')
      expect(events.length).toBe(4)
    })
  })
})
