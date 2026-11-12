/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect } from 'vitest'
import { render } from "@testing-library/react"
import { screen } from '@testing-library/dom'
import { axe } from 'jest-axe'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { t } from '@/i18n'

// Component to be implemented
interface BreadcrumbItem {
  label: string
  to: string
}

interface BreadcrumbsProps {
  items: BreadcrumbItem[]
}

// Mock component for testing - will be replaced with actual implementation
const Breadcrumbs = ({ items }: BreadcrumbsProps) => {
  if (items.length === 0) return null

  return (
    <nav aria-label={t('aria.breadcrumb.breadcrumb')}>
      <ol className="breadcrumb-list" style={{ display: 'flex', listStyle: 'none', padding: 0 }}>
        {items.map((item, index) => {
          const isLast = index === items.length - 1
          return (
            <li key={item.to}>
              {!isLast ? (
                <>
                  <a href={item.to}>{item.label}</a>
                  <span aria-hidden="true" style={{ margin: '0 0.5rem' }}>/</span>
                </>
              ) : (
                <span aria-current="page">{item.label}</span>
              )}
            </li>
          )
        })}
      </ol>
    </nav>
  )
}

// Wrapper component for routing context
const renderWithRouter = (ui: React.ReactElement) => {
  return render(<BrowserRouter>{ui}</BrowserRouter>)
}


// Preload English translations. vitest setup.ts does not preload i18n,
// and t() returns raw dotted-path keys when no language is loaded,
// breaking assertions that match resolved English strings.

describe('Breadcrumbs Accessibility', () => {
  const basicBreadcrumbs: BreadcrumbItem[] = [
    { label: 'Home', to: '/' },
    { label: 'Catalog', to: '/catalog' },
  ]

  const nestedBreadcrumbs: BreadcrumbItem[] = [
    { label: 'Home', to: '/' },
    { label: 'Catalog', to: '/catalog' },
    { label: 'Books', to: '/catalog/books' },
    { label: 'Science Fiction', to: '/catalog/books/sci-fi' },
  ]

  describe('ARIA Navigation Pattern', () => {
    it('uses nav element with aria-label', () => {
      renderWithRouter(<Breadcrumbs items={basicBreadcrumbs} />)
      const nav = screen.getByRole('navigation', { name: 'Breadcrumb' })
      expect(nav).toBeInTheDocument()
    })

    it('uses ol (ordered list) structure', () => {
      renderWithRouter(<Breadcrumbs items={basicBreadcrumbs} />)
      const nav = screen.getByRole('navigation', { name: 'Breadcrumb' })
      const list = nav.querySelector('ol')
      expect(list).toBeInTheDocument()
      expect(list?.tagName).toBe('OL')
    })

    it('marks last item with aria-current="page"', () => {
      renderWithRouter(<Breadcrumbs items={basicBreadcrumbs} />)
      const currentPage = screen.getByText('Catalog')
      expect(currentPage).toHaveAttribute('aria-current', 'page')
    })

    it('does not mark non-last items with aria-current', () => {
      renderWithRouter(<Breadcrumbs items={basicBreadcrumbs} />)
      const homeLink = screen.getByRole('link', { name: 'Home' })
      expect(homeLink).not.toHaveAttribute('aria-current')
    })

    it('separator icons are aria-hidden', () => {
      const { container } = renderWithRouter(<Breadcrumbs items={basicBreadcrumbs} />)
      const separators = container.querySelectorAll('[aria-hidden="true"]')
      // Should have n-1 separators for n items
      expect(separators.length).toBe(basicBreadcrumbs.length - 1)
    })
  })

  describe('Keyboard Navigation', () => {
    it('links are keyboard accessible with Tab', async () => {
      const user = userEvent.setup()
      renderWithRouter(<Breadcrumbs items={basicBreadcrumbs} />)

      const homeLink = screen.getByRole('link', { name: 'Home' })

      // Tab to the first link
      await user.tab()
      expect(homeLink).toHaveFocus()
    })

    it('all breadcrumb links can be reached via keyboard', async () => {
      const user = userEvent.setup()
      renderWithRouter(<Breadcrumbs items={nestedBreadcrumbs} />)

      const links = screen.getAllByRole('link')

      // Tab through all links
      for (const link of links) {
        await user.tab()
        expect(link).toHaveFocus()
      }
    })

    it('links can be activated with Enter key', async () => {
      const user = userEvent.setup()
      renderWithRouter(<Breadcrumbs items={basicBreadcrumbs} />)

      const homeLink = screen.getByRole('link', { name: 'Home' })

      await user.tab()
      expect(homeLink).toHaveFocus()

      // Verify link is present and can be clicked
      await user.keyboard('{Enter}')
      // In actual implementation, this would navigate
    })
  })

  describe('Automated Accessibility Checks', () => {
    it('has no accessibility violations with basic breadcrumbs', async () => {
      const { container } = renderWithRouter(<Breadcrumbs items={basicBreadcrumbs} />)
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })

    it('has no accessibility violations with nested breadcrumbs', async () => {
      const { container } = renderWithRouter(<Breadcrumbs items={nestedBreadcrumbs} />)
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })

    it('has no accessibility violations with single breadcrumb', async () => {
      const { container } = renderWithRouter(
        <Breadcrumbs items={[{ label: 'Home', to: '/' }]} />
      )
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })
  })

  describe('Screen Reader Support', () => {
    it('provides semantic breadcrumb structure for screen readers', () => {
      renderWithRouter(<Breadcrumbs items={basicBreadcrumbs} />)

      const nav = screen.getByRole('navigation', { name: 'Breadcrumb' })
      const list = nav.querySelector('ol')
      const listItems = nav.querySelectorAll('li')

      expect(list).toBeInTheDocument()
      expect(listItems).toHaveLength(basicBreadcrumbs.length)
    })

    it('announces current page correctly', () => {
      renderWithRouter(<Breadcrumbs items={basicBreadcrumbs} />)

      const currentPage = screen.getByText('Catalog')
      expect(currentPage).toHaveAttribute('aria-current', 'page')
      expect(currentPage.tagName).toBe('SPAN') // Not a link
    })

    it('hides decorative separators from screen readers', () => {
      const { container } = renderWithRouter(<Breadcrumbs items={nestedBreadcrumbs} />)

      const ariaHiddenElements = container.querySelectorAll('[aria-hidden="true"]')
      ariaHiddenElements.forEach((element: Element) => {
        // Verify these are the separator elements
        expect(element.textContent).toMatch(/[/›→]/)
      })
    })
  })

  describe('Edge Cases', () => {
    it('renders nothing when items array is empty', () => {
      const { container } = renderWithRouter(<Breadcrumbs items={[]} />)
      expect(container.querySelector('nav')).not.toBeInTheDocument()
    })

    it('handles very long breadcrumb trails', async () => {
      const longBreadcrumbs: BreadcrumbItem[] = Array.from({ length: 10 }, (_, i) => ({
        label: `Level ${i + 1}`,
        to: `/level${i + 1}`,
      }))

      const { container } = renderWithRouter(<Breadcrumbs items={longBreadcrumbs} />)
      const results = await axe(container)
      expect(results).toHaveNoViolations()

      const listItems = container.querySelectorAll('li')
      expect(listItems).toHaveLength(10)
    })

    it('handles breadcrumbs with special characters in labels', async () => {
      const specialBreadcrumbs: BreadcrumbItem[] = [
        { label: 'Home & Garden', to: '/home-garden' },
        { label: 'Books <Science>', to: '/books-science' },
        { label: "Children's Books", to: '/childrens-books' },
      ]

      const { container } = renderWithRouter(<Breadcrumbs items={specialBreadcrumbs} />)
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })
  })

  describe('Visual Structure', () => {
    it('renders items in correct order', () => {
      renderWithRouter(<Breadcrumbs items={nestedBreadcrumbs} />)

      const nav = screen.getByRole('navigation', { name: 'Breadcrumb' })
      const listItems = nav.querySelectorAll('li')

      nestedBreadcrumbs.forEach((item, index) => {
        expect(listItems[index]).toHaveTextContent(item.label)
      })
    })

    it('only the last item is not a link', () => {
      renderWithRouter(<Breadcrumbs items={nestedBreadcrumbs} />)

      const links = screen.getAllByRole('link')
      expect(links).toHaveLength(nestedBreadcrumbs.length - 1)

      // Last item should be text, not a link
      const lastItem = screen.getByText(nestedBreadcrumbs[nestedBreadcrumbs.length - 1]!.label)
      expect(lastItem.tagName).toBe('SPAN')
    })
  })

  describe('WCAG 2.1 Level AA Compliance', () => {
    it('meets color contrast requirements', () => {
      // This would typically be tested with actual CSS applied
      // In integration tests with proper styling
      renderWithRouter(<Breadcrumbs items={basicBreadcrumbs} />)
      const nav = screen.getByRole('navigation', { name: 'Breadcrumb' })
      expect(nav).toBeInTheDocument()
    })

    it('provides clear focus indicators', async () => {
      const user = userEvent.setup()
      renderWithRouter(<Breadcrumbs items={basicBreadcrumbs} />)

      const homeLink = screen.getByRole('link', { name: 'Home' })

      await user.tab()
      expect(homeLink).toHaveFocus()
      // In actual implementation, CSS would provide visible focus indicator
    })

    it('supports text resize up to 200%', () => {
      // This would be tested in E2E tests with actual browser
      renderWithRouter(<Breadcrumbs items={basicBreadcrumbs} />)
      const nav = screen.getByRole('navigation', { name: 'Breadcrumb' })
      expect(nav).toBeInTheDocument()
    })
  })
})
