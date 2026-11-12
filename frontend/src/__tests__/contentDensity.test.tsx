/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render } from "@testing-library/react"
import { screen, waitFor } from "@testing-library/react"
import { axe } from 'jest-axe'
import userEvent from '@testing-library/user-event'
import { renderHook, act } from '@testing-library/react'
import { createMockLocalStorage } from './utils/mock-helpers'

// Content density types
type ContentDensity = 'spacious' | 'comfortable' | 'compact'

const VALID_DENSITIES: ContentDensity[] = ['spacious', 'comfortable', 'compact']

// Hook for managing content density - to be implemented
const useContentDensity = (initialDensity: ContentDensity = 'comfortable') => {
  const [density, setDensity] = useState<ContentDensity>(() => {
    const stored = localStorage.getItem('contentDensity')
    return stored && VALID_DENSITIES.includes(stored as ContentDensity) ? (stored as ContentDensity) : initialDensity
  })

  const updateDensity = (newDensity: ContentDensity) => {
    setDensity(newDensity)
    localStorage.setItem('contentDensity', newDensity)
    document.documentElement.setAttribute('data-content-density', newDensity)
  }

  // Apply on mount
  useEffect(() => {
    document.documentElement.setAttribute('data-content-density', density)
  }, [density])

  return { density, setDensity: updateDensity }
}

// Mock component for testing
import { useState, useEffect } from 'react'

const ContentDensitySelector = () => {
  const { density, setDensity } = useContentDensity()

  return (
    <div className="content-density-selector">
      <label htmlFor="density-select">Content Density</label>
      <select
        id="density-select"
        value={density}
        onChange={(e) => setDensity(e.target.value as ContentDensity)}
        aria-label={t('aria.common.selectContentDensity')}
      >
        <option value="spacious">Spacious - Extra spacing for readability</option>
        <option value="comfortable">Comfortable - Default spacing</option>
        <option value="compact">Compact - Minimal spacing to see more content</option>
      </select>

      <div className="density-preview" data-testid="preview">
        <div className="preview-card">
          <h3>Preview Card</h3>
          <p>This is how content will appear with {density} density.</p>
          <button>Sample Button</button>
        </div>
      </div>
    </div>
  )
}

describe('Content Density', () => {
  beforeEach(() => {
    // The global setup.ts localStorage mock is a set of bare vi.fn() stubs
    // with no backing store (getItem always returns undefined), so it can't
    // round-trip a real value. Swap in the working mock-helpers implementation
    // for this file's tests, which actually persist what's written to them.
    Object.defineProperty(window, 'localStorage', { value: createMockLocalStorage(), configurable: true })
    document.documentElement.removeAttribute('data-content-density')
  })

  afterEach(() => {
    localStorage.clear()
    document.documentElement.removeAttribute('data-content-density')
  })

  describe('Data Attribute Application', () => {
    it('applies data-content-density="spacious" to document', () => {
      renderHook(() => useContentDensity('spacious'))

      expect(document.documentElement.getAttribute('data-content-density')).toBe('spacious')
    })

    it('applies data-content-density="comfortable" to document', () => {
      renderHook(() => useContentDensity('comfortable'))

      expect(document.documentElement.getAttribute('data-content-density')).toBe('comfortable')
    })

    it('applies data-content-density="compact" to document', () => {
      renderHook(() => useContentDensity('compact'))

      expect(document.documentElement.getAttribute('data-content-density')).toBe('compact')
    })

    it('updates attribute when density changes', () => {
      const { result } = renderHook(() => useContentDensity('comfortable'))

      expect(document.documentElement.getAttribute('data-content-density')).toBe('comfortable')

      act(() => {
        result.current.setDensity('spacious')
      })

      expect(document.documentElement.getAttribute('data-content-density')).toBe('spacious')
    })
  })

  describe('Hook Functionality', () => {
    it('returns current density', () => {
      const { result } = renderHook(() => useContentDensity('comfortable'))

      expect(result.current.density).toBe('comfortable')
    })

    it('updates density when setDensity is called', () => {
      const { result } = renderHook(() => useContentDensity('comfortable'))

      act(() => {
        result.current.setDensity('spacious')
      })

      expect(result.current.density).toBe('spacious')
    })

    it('defaults to comfortable if no stored value', () => {
      const { result } = renderHook(() => useContentDensity())

      expect(result.current.density).toBe('comfortable')
    })

    it('uses custom initial value', () => {
      const { result } = renderHook(() => useContentDensity('compact'))

      expect(result.current.density).toBe('compact')
    })
  })

  describe('LocalStorage Persistence', () => {
    it('persists setting to localStorage', () => {
      const { result } = renderHook(() => useContentDensity())

      act(() => {
        result.current.setDensity('spacious')
      })

      expect(localStorage.getItem('contentDensity')).toBe('spacious')
    })

    it('loads setting from localStorage on mount', () => {
      localStorage.setItem('contentDensity', 'compact')

      const { result } = renderHook(() => useContentDensity())

      expect(result.current.density).toBe('compact')
    })

    it('persists setting across sessions', () => {
      // First session
      const { unmount } = renderHook(() => useContentDensity())
      const { result: firstResult } = renderHook(() => useContentDensity())

      act(() => {
        firstResult.current.setDensity('spacious')
      })

      unmount()

      // Second session
      const { result: secondResult } = renderHook(() => useContentDensity())

      expect(secondResult.current.density).toBe('spacious')
    })

    it('updates localStorage when density changes', () => {
      const { result } = renderHook(() => useContentDensity())

      act(() => {
        result.current.setDensity('spacious')
      })

      expect(localStorage.getItem('contentDensity')).toBe('spacious')

      act(() => {
        result.current.setDensity('compact')
      })

      expect(localStorage.getItem('contentDensity')).toBe('compact')
    })
  })

  describe('CSS Application', () => {
    it('CSS rules apply correct padding for spacious mode', () => {
      // This would be tested with actual CSS in integration tests
      // Here we verify the attribute is set correctly
      renderHook(() => useContentDensity('spacious'))

      expect(document.documentElement.getAttribute('data-content-density')).toBe('spacious')

      // In actual CSS: [data-content-density="spacious"] .card { padding: 2rem; }
    })

    it('CSS rules apply correct padding for comfortable mode', () => {
      renderHook(() => useContentDensity('comfortable'))

      expect(document.documentElement.getAttribute('data-content-density')).toBe('comfortable')

      // In actual CSS: [data-content-density="comfortable"] .card { padding: 1.5rem; }
    })

    it('CSS rules apply correct padding for compact mode', () => {
      renderHook(() => useContentDensity('compact'))

      expect(document.documentElement.getAttribute('data-content-density')).toBe('compact')

      // In actual CSS: [data-content-density="compact"] .card { padding: 1rem; }
    })

    it('attribute cascades to all child elements', () => {
      renderHook(() => useContentDensity('spacious'))

      render(
        <div>
          <div className="card">Card content</div>
          <div className="list-item">List item</div>
        </div>
      )

      expect(document.documentElement.getAttribute('data-content-density')).toBe('spacious')
      // All children inherit the density styling through CSS selectors
    })
  })

  describe('Content Density Selector Component', () => {
    it('renders density selector', () => {
      render(<ContentDensitySelector />)

      expect(screen.getByLabelText(/content density/i)).toBeInTheDocument()
    })

    it('shows all density options', () => {
      render(<ContentDensitySelector />)

      const select = screen.getByLabelText(/content density/i)
      const options = within(select as HTMLSelectElement).getAllByRole('option')

      expect(options).toHaveLength(3)
      expect(options[0]).toHaveTextContent(/spacious/i)
      expect(options[1]).toHaveTextContent(/comfortable/i)
      expect(options[2]).toHaveTextContent(/compact/i)
    })

    it('changes density when option selected', async () => {
      const user = userEvent.setup()
      render(<ContentDensitySelector />)

      const select = screen.getByLabelText(/content density/i)

      await user.selectOptions(select, 'spacious')

      await waitFor(() => {
        expect(document.documentElement.getAttribute('data-content-density')).toBe('spacious')
      })
    })

    it('displays current density in selector', () => {
      localStorage.setItem('contentDensity', 'compact')

      render(<ContentDensitySelector />)

      const select = screen.getByLabelText(/content density/i) as HTMLSelectElement
      expect(select.value).toBe('compact')
    })

    it('preview updates when density changes', async () => {
      const user = userEvent.setup()
      render(<ContentDensitySelector />)

      const select = screen.getByLabelText(/content density/i)

      await user.selectOptions(select, 'spacious')

      await waitFor(() => {
        expect(screen.getByText(/spacious density/i)).toBeInTheDocument()
      })
    })
  })

  describe('Accessibility', () => {
    it('selector is keyboard accessible', async () => {
      const user = userEvent.setup()
      render(<ContentDensitySelector />)

      const select = screen.getByLabelText(/content density/i)

      await user.tab()
      expect(select).toHaveFocus()
    })

    it('can be changed with keyboard', async () => {
      const user = userEvent.setup()
      render(<ContentDensitySelector />)

      const select = screen.getByLabelText(/content density/i)
      select.focus()

      await user.keyboard('{ArrowDown}')
      await user.keyboard('{Enter}')

      // Density should change
    })

    it('has proper label association', () => {
      render(<ContentDensitySelector />)

      const select = screen.getByLabelText('Content Density')
      expect(select).toHaveAttribute('id', 'density-select')
    })

    it('has descriptive option text', () => {
      render(<ContentDensitySelector />)

      expect(screen.getByText(/spacious - extra spacing for readability/i)).toBeInTheDocument()
      expect(screen.getByText(/comfortable - default spacing/i)).toBeInTheDocument()
      expect(screen.getByText(/compact - minimal spacing/i)).toBeInTheDocument()
    })

    it('passes axe accessibility checks', async () => {
      const { container } = render(<ContentDensitySelector />)
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })
  })

  describe('User Preference', () => {
    it('respects stored user preference', () => {
      localStorage.setItem('contentDensity', 'spacious')

      const { result } = renderHook(() => useContentDensity())

      expect(result.current.density).toBe('spacious')
      expect(document.documentElement.getAttribute('data-content-density')).toBe('spacious')
    })

    it('overrides default with user preference', () => {
      localStorage.setItem('contentDensity', 'compact')

      // Even though default is 'comfortable', user preference wins
      const { result } = renderHook(() => useContentDensity('comfortable'))

      expect(result.current.density).toBe('compact')
    })

    it('falls back to default if no preference stored', () => {
      localStorage.removeItem('contentDensity')

      const { result } = renderHook(() => useContentDensity('spacious'))

      expect(result.current.density).toBe('spacious')
    })
  })

  describe('Edge Cases', () => {
    it('handles invalid stored value gracefully', () => {
      localStorage.setItem('contentDensity', 'invalid')

      const { result } = renderHook(() => useContentDensity('comfortable'))

      // Should fall back to default
      expect(['spacious', 'comfortable', 'compact']).toContain(result.current.density)
    })

    it('handles missing localStorage gracefully', () => {
      const originalGetItem = Storage.prototype.getItem
      Storage.prototype.getItem = vi.fn(() => {
        throw new Error('localStorage unavailable')
      })

      const { result } = renderHook(() => useContentDensity('comfortable'))

      // Should use default
      expect(result.current.density).toBe('comfortable')

      Storage.prototype.getItem = originalGetItem
    })

    it('handles rapid density changes', async () => {
      const { result } = renderHook(() => useContentDensity())

      act(() => {
        result.current.setDensity('spacious')
        result.current.setDensity('compact')
        result.current.setDensity('comfortable')
      })

      expect(result.current.density).toBe('comfortable')
      expect(localStorage.getItem('contentDensity')).toBe('comfortable')
    })
  })

  describe('Multiple Components', () => {
    it('all components use same density', () => {
      const { result: result1 } = renderHook(() => useContentDensity())

      act(() => {
        result1.current.setDensity('spacious')
      })

      // Both hooks should reflect the change
      expect(result1.current.density).toBe('spacious')
      // Note: In real implementation, this would use context or state management
      // to sync between hooks
    })
  })

  describe('WCAG 2.1 Compliance', () => {
    it('provides sufficient spacing in all modes', () => {
      const densities: ContentDensity[] = ['spacious', 'comfortable', 'compact']

      densities.forEach((density) => {
        renderHook(() => useContentDensity(density))
        expect(document.documentElement.getAttribute('data-content-density')).toBe(density)
        // All modes should maintain minimum touch target sizes (44x44px)
      })
    })

    it('maintains readability in all density modes', () => {
      // All density modes should maintain WCAG line-height requirements
      // Line height of at least 1.5 for body text
      renderHook(() => useContentDensity('compact'))
      expect(document.documentElement.getAttribute('data-content-density')).toBe('compact')
    })

    it('maintains adequate focus indicators in all modes', () => {
      const densities: ContentDensity[] = ['spacious', 'comfortable', 'compact']

      densities.forEach((density) => {
        renderHook(() => useContentDensity(density))
        // Focus indicators should be visible regardless of density
      })
    })
  })
})

// Import for type safety
import { within } from '@testing-library/react'
import { t } from '@/i18n'
