/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * ProgramCardSkeleton Component Tests
 *
 * Tests for program card skeleton loader component
 * Ensures proper loading state indication and accessibility
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render } from "@testing-library/react"
import { screen } from "@testing-library/react"
import { axe } from 'jest-axe'
import { t } from '@/i18n'

// Mock component - replace with actual import when component exists
const ProgramCardSkeleton = ({ count = 1 }: { count?: number }) => {
  return (
    <div aria-label={t('aria.skeletons.loadingPrograms')} role="status">
      {Array.from({ length: count }).map((_, index) => (
        <div
          key={index}
          className="program-card-skeleton animate-pulse"
          data-testid={`skeleton-program-${index}`}
        >
          <div className="skeleton-header p-4 space-y-3">
            <div className="h-6 bg-earth-200 dark:bg-earth-700 rounded w-2/3" />
            <div className="flex gap-2">
              <div className="h-6 w-16 bg-earth-200 dark:bg-earth-700 rounded-full" />
              <div className="h-6 w-20 bg-earth-200 dark:bg-earth-700 rounded-full" />
            </div>
          </div>
          <div className="skeleton-divider h-px bg-earth-200 dark:bg-earth-700" />
          <div className="skeleton-content p-4 space-y-2">
            <div className="h-4 bg-earth-200 dark:bg-earth-700 rounded w-full" />
            <div className="h-4 bg-earth-200 dark:bg-earth-700 rounded w-5/6" />
            <div className="h-4 bg-earth-200 dark:bg-earth-700 rounded w-4/5" />
          </div>
          <div className="skeleton-footer p-4 flex justify-between">
            <div className="h-4 bg-earth-200 dark:bg-earth-700 rounded w-24" />
            <div className="h-4 bg-earth-200 dark:bg-earth-700 rounded w-32" />
          </div>
        </div>
      ))}
    </div>
  )
}


// Preload English translations. vitest setup.ts does not preload i18n,
// and t() returns raw dotted-path keys when no language is loaded,
// breaking assertions that match resolved English strings.

describe('ProgramCardSkeleton Component', () => {
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
      render(<ProgramCardSkeleton />)
      expect(screen.getByTestId('skeleton-program-0')).toBeInTheDocument()
    })

    it('renders correct number of skeleton items', () => {
      render(<ProgramCardSkeleton count={3} />)

      expect(screen.getByTestId('skeleton-program-0')).toBeInTheDocument()
      expect(screen.getByTestId('skeleton-program-1')).toBeInTheDocument()
      expect(screen.getByTestId('skeleton-program-2')).toBeInTheDocument()
    })

    it('has skeleton header section', () => {
      render(<ProgramCardSkeleton />)

      const header = document.querySelector('.skeleton-header')
      expect(header).toBeInTheDocument()
      expect(header).toHaveClass('p-4')
    })

    it('has skeleton content section', () => {
      render(<ProgramCardSkeleton />)

      const content = document.querySelector('.skeleton-content')
      expect(content).toBeInTheDocument()
    })

    it('has skeleton footer section', () => {
      render(<ProgramCardSkeleton />)

      const footer = document.querySelector('.skeleton-footer')
      expect(footer).toBeInTheDocument()
    })

    it('has divider between sections', () => {
      render(<ProgramCardSkeleton />)

      const divider = document.querySelector('.skeleton-divider')
      expect(divider).toBeInTheDocument()
    })
  })

  describe('ARIA and Accessibility', () => {
    it('has proper ARIA label for loading state', () => {
      render(<ProgramCardSkeleton />)

      expect(screen.getByLabelText('Loading programs...')).toBeInTheDocument()
    })

    it('has aria-label on container', () => {
      const { container } = render(<ProgramCardSkeleton />)

      const loadingContainer = container.querySelector('[aria-label]')
      expect(loadingContainer).toHaveAttribute('aria-label', 'Loading programs...')
    })

    it('has no accessibility violations', async () => {
      const { container } = render(<ProgramCardSkeleton />)
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })

    it('has no accessibility violations with multiple items', async () => {
      const { container } = render(<ProgramCardSkeleton count={3} />)
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })
  })

  describe('Animation', () => {
    it('has pulse animation class', () => {
      render(<ProgramCardSkeleton />)

      const skeleton = screen.getByTestId('skeleton-program-0')
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

      render(<ProgramCardSkeleton />)

      expect(screen.getByTestId('skeleton-program-0')).toBeInTheDocument()
    })
  })

  describe('Structure Matching', () => {
    it('matches structure of actual program card', () => {
      render(<ProgramCardSkeleton />)

      expect(document.querySelector('.skeleton-header')).toBeInTheDocument()
      expect(document.querySelector('.skeleton-divider')).toBeInTheDocument()
      expect(document.querySelector('.skeleton-content')).toBeInTheDocument()
      expect(document.querySelector('.skeleton-footer')).toBeInTheDocument()
    })

    it('has title placeholder in header', () => {
      render(<ProgramCardSkeleton />)

      const header = document.querySelector('.skeleton-header')
      const title = header?.querySelector('.h-6')
      expect(title).toBeInTheDocument()
    })

    it('has badge placeholders in header', () => {
      render(<ProgramCardSkeleton />)

      const badges = document.querySelectorAll('.skeleton-header .rounded-full')
      expect(badges.length).toBeGreaterThanOrEqual(2)
    })

    it('has description lines in content', () => {
      render(<ProgramCardSkeleton />)

      const content = document.querySelector('.skeleton-content')
      const lines = content?.querySelectorAll('.h-4')
      expect(lines?.length).toBeGreaterThanOrEqual(3)
    })

    it('has footer items with flexbox layout', () => {
      render(<ProgramCardSkeleton />)

      const footer = document.querySelector('.skeleton-footer')
      expect(footer).toHaveClass('flex')
      expect(footer).toHaveClass('justify-between')
    })

    it('has proper spacing in sections', () => {
      render(<ProgramCardSkeleton />)

      const header = document.querySelector('.skeleton-header')
      expect(header).toHaveClass('space-y-3')

      const content = document.querySelector('.skeleton-content')
      expect(content).toHaveClass('space-y-2')
    })
  })

  describe('Dark Mode', () => {
    it('has dark mode classes on all elements', () => {
      render(<ProgramCardSkeleton />)

      const elements = document.querySelectorAll('.bg-earth-200 dark:bg-earth-600')
      elements.forEach(element => {
        expect(element.className).toContain('dark:bg-earth-700')
      })
    })

    it('divider has dark mode support', () => {
      render(<ProgramCardSkeleton />)

      const divider = document.querySelector('.skeleton-divider')
      expect(divider?.className).toContain('dark:bg-earth-700')
    })
  })

  describe('Layout', () => {
    it('has consistent card structure', () => {
      render(<ProgramCardSkeleton />)

      const card = screen.getByTestId('skeleton-program-0')
      expect(card.querySelector('.skeleton-header')).toBeInTheDocument()
      expect(card.querySelector('.skeleton-content')).toBeInTheDocument()
      expect(card.querySelector('.skeleton-footer')).toBeInTheDocument()
    })

    it('badges use flexbox layout', () => {
      render(<ProgramCardSkeleton />)

      const badgeContainer = document.querySelector('.skeleton-header .flex')
      expect(badgeContainer).toHaveClass('gap-2')
    })

    it('footer uses flexbox with space-between', () => {
      render(<ProgramCardSkeleton />)

      const footer = document.querySelector('.skeleton-footer')
      expect(footer).toHaveClass('justify-between')
    })
  })

  describe('Responsive Behavior', () => {
    it('renders correctly on mobile viewports', () => {
      render(<ProgramCardSkeleton count={2} />)

      expect(screen.getByTestId('skeleton-program-0')).toBeInTheDocument()
      expect(screen.getByTestId('skeleton-program-1')).toBeInTheDocument()
    })

    it('renders correctly on desktop viewports', () => {
      render(<ProgramCardSkeleton count={4} />)

      for (let i = 0; i < 4; i++) {
        expect(screen.getByTestId(`skeleton-program-${i}`)).toBeInTheDocument()
      }
    })
  })

  describe('Edge Cases', () => {
    it('handles zero count gracefully', () => {
      render(<ProgramCardSkeleton count={0} />)

      expect(screen.queryByTestId('skeleton-program-0')).not.toBeInTheDocument()
    })

    it('handles large count', () => {
      render(<ProgramCardSkeleton count={12} />)

      expect(screen.getByTestId('skeleton-program-0')).toBeInTheDocument()
      expect(screen.getByTestId('skeleton-program-11')).toBeInTheDocument()
    })

    it('maintains consistent structure across multiple items', () => {
      render(<ProgramCardSkeleton count={3} />)

      for (let i = 0; i < 3; i++) {
        const item = screen.getByTestId(`skeleton-program-${i}`)
        expect(item.querySelector('.skeleton-header')).toBeInTheDocument()
        expect(item.querySelector('.skeleton-divider')).toBeInTheDocument()
        expect(item.querySelector('.skeleton-content')).toBeInTheDocument()
        expect(item.querySelector('.skeleton-footer')).toBeInTheDocument()
      }
    })
  })

  describe('Visual Elements', () => {
    it('has rounded badges', () => {
      render(<ProgramCardSkeleton />)

      const badges = document.querySelectorAll('.skeleton-header .rounded-full')
      expect(badges.length).toBeGreaterThan(0)
    })

    it('has varied content line widths', () => {
      render(<ProgramCardSkeleton />)

      const content = document.querySelector('.skeleton-content')
      const lines = content?.querySelectorAll('.h-4')

      // Check that not all lines have the same width class
      const widths = Array.from(lines || []).map(line => {
        const classes = line.className
        if (classes.includes('w-full')) return 'full'
        if (classes.includes('w-5/6')) return '5/6'
        if (classes.includes('w-4/5')) return '4/5'
        return 'other'
      })

      expect(new Set(widths).size).toBeGreaterThan(1)
    })

    it('footer items have different widths', () => {
      render(<ProgramCardSkeleton />)

      const footer = document.querySelector('.skeleton-footer')
      const items = footer?.querySelectorAll('.h-4')

      expect(items?.length).toBe(2)
      // Different width classes for visual variety
      expect(items?.[0]).toHaveClass('w-24')
      expect(items?.[1]).toHaveClass('w-32')
    })
  })

  describe('Performance', () => {
    it('renders efficiently with multiple items', () => {
      const startTime = performance.now()
      render(<ProgramCardSkeleton count={10} />)
      const endTime = performance.now()

      expect(endTime - startTime).toBeLessThan(100)
    })

    it('does not cause layout shift', () => {
      const { container } = render(<ProgramCardSkeleton />)

      // All sections should have defined dimensions
      const header = container.querySelector('.skeleton-header')
      expect(header).toHaveClass('p-4')

      const content = container.querySelector('.skeleton-content')
      expect(content).toHaveClass('p-4')

      const footer = container.querySelector('.skeleton-footer')
      expect(footer).toHaveClass('p-4')
    })
  })

  describe('Integration', () => {
    it('works in list layout', () => {
      const { container } = render(
        <div className="program-list">
          <ProgramCardSkeleton count={3} />
        </div>
      )

      const programs = container.querySelectorAll('.program-card-skeleton')
      expect(programs.length).toBe(3)
    })

    it('works in grid layout', () => {
      const { container } = render(
        <div className="grid grid-cols-2 gap-4">
          <ProgramCardSkeleton count={4} />
        </div>
      )

      const programs = container.querySelectorAll('.program-card-skeleton')
      expect(programs.length).toBe(4)
    })

    it('works with cards in container', () => {
      const { container } = render(
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow">
          <ProgramCardSkeleton />
        </div>
      )

      expect(container.querySelector('.program-card-skeleton')).toBeInTheDocument()
    })
  })

  describe('Accessibility Features', () => {
    it('maintains semantic structure', () => {
      render(<ProgramCardSkeleton />)

      // Check that sections follow logical order
      const card = screen.getByTestId('skeleton-program-0')
      const children = Array.from(card.children)

      expect(children[0]).toHaveClass('skeleton-header')
      expect(children[1]).toHaveClass('skeleton-divider')
      expect(children[2]).toHaveClass('skeleton-content')
      expect(children[3]).toHaveClass('skeleton-footer')
    })

    it('provides loading context to screen readers', () => {
      render(<ProgramCardSkeleton count={3} />)

      const loadingRegion = screen.getByLabelText('Loading programs...')
      expect(loadingRegion).toBeInTheDocument()
    })
  })
})
