/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Button Component Tests
 *
 * Comprehensive test suite for Button component using TDD approach
 * Tests variants, sizes, states, accessibility, and keyboard navigation
 */

import { describe, it, expect, vi } from 'vitest'
import { render as rtlRender, type RenderOptions } from "@testing-library/react"
import { screen } from "@testing-library/react"
import userEvent from '@testing-library/user-event'
import { axe } from 'jest-axe'
import type { ReactElement, ReactNode } from 'react'
import { Button } from '../Button'
import { Home, ChevronRight } from 'lucide-react'
import { t } from '@/i18n'
import { I18nProvider } from '@/i18n/I18nContext'
import { BrandingProvider } from '@/contexts/BrandingContext'

// Button now calls useTranslation() for its loading-state copy, so it needs
// I18nProvider (which itself needs BrandingProvider) in the tree. Wrapping
// here instead of touching every call site below.
function render(ui: ReactElement, options?: RenderOptions) {
  return rtlRender(ui, {
    wrapper: ({ children }: { children: ReactNode }) => (
      <BrandingProvider>
        <I18nProvider>{children}</I18nProvider>
      </BrandingProvider>
    ),
    ...options,
  })
}

describe('Button Component', () => {
  describe('Rendering', () => {
    it('renders children correctly', () => {
      render(<Button>Click me</Button>)
      expect(screen.getByRole('button', { name: 'Click me' })).toBeInTheDocument()
    })

    it('renders as a button element', () => {
      render(<Button>Test</Button>)
      const button = screen.getByRole('button')
      expect(button.tagName).toBe('BUTTON')
    })

    it('renders with custom className', () => {
      render(<Button className="custom-class">Test</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('custom-class')
    })

    it('renders with left icon', () => {
      render(
        <Button leftIcon={<Home data-testid="left-icon" />}>
          Home
        </Button>
      )
      expect(screen.getByTestId('left-icon')).toBeInTheDocument()
      expect(screen.getByText('Home')).toBeInTheDocument()
    })

    it('renders with right icon', () => {
      render(
        <Button rightIcon={<ChevronRight data-testid="right-icon" />}>
          Next
        </Button>
      )
      expect(screen.getByTestId('right-icon')).toBeInTheDocument()
      expect(screen.getByText('Next')).toBeInTheDocument()
    })

    it('renders with both left and right icons', () => {
      render(
        <Button
          leftIcon={<Home data-testid="left-icon" />}
          rightIcon={<ChevronRight data-testid="right-icon" />}
        >
          Content
        </Button>
      )
      expect(screen.getByTestId('left-icon')).toBeInTheDocument()
      expect(screen.getByTestId('right-icon')).toBeInTheDocument()
    })

    it('renders full width when fullWidth prop is true', () => {
      render(<Button fullWidth>Full Width</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('w-full')
    })
  })

  describe('Variants', () => {
    it('renders primary variant correctly', () => {
      render(<Button variant="primary">Primary</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('bg-lsc-rose')
      expect(button).toHaveClass('text-white')
    })

    it('renders secondary variant correctly', () => {
      render(<Button variant="secondary">Secondary</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('bg-lsc-cream')
      expect(button).toHaveClass('border-2')
    })

    it('renders tertiary variant correctly', () => {
      render(<Button variant="tertiary">Tertiary</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('bg-transparent')
    })

    it('renders danger variant correctly', () => {
      render(<Button variant="danger">Delete</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('bg-status-danger-600')
      expect(button).toHaveClass('text-white')
    })

    it('defaults to primary variant when not specified', () => {
      render(<Button>Default</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('bg-lsc-rose')
    })
  })

  describe('Sizes', () => {
    it('renders small size correctly', () => {
      render(<Button size="sm">Small</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('text-sm')
      expect(button).toHaveClass('min-h-[44px]')
    })

    it('renders medium size correctly', () => {
      render(<Button size="md">Medium</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('text-base')
      expect(button).toHaveClass('min-h-[48px]')
    })

    it('renders large size correctly', () => {
      render(<Button size="lg">Large</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('text-lg')
      expect(button).toHaveClass('min-h-[56px]')
    })

    it('defaults to medium size when not specified', () => {
      render(<Button>Default</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('text-base')
      expect(button).toHaveClass('min-h-[48px]')
    })

    it('all sizes meet minimum 44px touch target', () => {
      const { rerender } = render(<Button size="sm">Small</Button>)
      expect(screen.getByRole('button')).toHaveClass('min-h-[44px]')

      rerender(<Button size="md">Medium</Button>)
      expect(screen.getByRole('button')).toHaveClass('min-h-[48px]')

      rerender(<Button size="lg">Large</Button>)
      expect(screen.getByRole('button')).toHaveClass('min-h-[56px]')
    })
  })

  describe('States', () => {
    it('handles disabled state correctly', () => {
      render(<Button disabled>Disabled</Button>)
      const button = screen.getByRole('button')
      expect(button).toBeDisabled()
      expect(button).toHaveAttribute('disabled')
    })

    it('shows loading state with spinner', () => {
      render(<Button isLoading>Loading</Button>)
      const button = screen.getByRole('button')

      // Should show loading spinner (aria-hidden)
      const spinner = button.querySelector('[aria-hidden="true"]')
      expect(spinner).toBeInTheDocument()

      // Should be disabled when loading
      expect(button).toBeDisabled()

      // Should not show original children when loading
      expect(screen.queryByText('Loading')).not.toBeInTheDocument()
    })

    it('hides children and icons when loading', () => {
      render(
        <Button
          isLoading
          leftIcon={<Home data-testid="icon" />}
        >
          Submit
        </Button>
      )

      expect(screen.queryByText('Submit')).not.toBeInTheDocument()
      expect(screen.queryByTestId('icon')).not.toBeInTheDocument()
    })

    it('loading state takes precedence over disabled', () => {
      render(<Button isLoading disabled>Test</Button>)
      const button = screen.getByRole('button')
      expect(button).toBeDisabled()
      // Loading spinner should be present
      expect(button.querySelector('[aria-hidden="true"]')).toBeInTheDocument()
      // Original text should not be visible
      expect(screen.queryByText('Test')).not.toBeInTheDocument()
    })
  })

  describe('Interactions', () => {
    it('calls onClick when clicked with mouse', async () => {
      const handleClick = vi.fn()
      const user = userEvent.setup()

      render(<Button onClick={handleClick}>Click me</Button>)
      await user.click(screen.getByRole('button'))

      expect(handleClick).toHaveBeenCalledTimes(1)
    })

    it('calls onClick when activated with Enter key', async () => {
      const handleClick = vi.fn()
      const user = userEvent.setup()

      render(<Button onClick={handleClick}>Press me</Button>)
      const button = screen.getByRole('button')
      button.focus()
      await user.keyboard('{Enter}')

      expect(handleClick).toHaveBeenCalledTimes(1)
    })

    it('calls onClick when activated with Space key', async () => {
      const handleClick = vi.fn()
      const user = userEvent.setup()

      render(<Button onClick={handleClick}>Press me</Button>)
      const button = screen.getByRole('button')
      button.focus()
      await user.keyboard(' ')

      expect(handleClick).toHaveBeenCalledTimes(1)
    })

    it('does not call onClick when disabled', async () => {
      const handleClick = vi.fn()
      const user = userEvent.setup()

      render(<Button onClick={handleClick} disabled>Disabled</Button>)
      await user.click(screen.getByRole('button'))

      expect(handleClick).not.toHaveBeenCalled()
    })

    it('does not call onClick when loading', async () => {
      const handleClick = vi.fn()
      const user = userEvent.setup()

      render(<Button onClick={handleClick} isLoading>Loading</Button>)
      await user.click(screen.getByRole('button'))

      expect(handleClick).not.toHaveBeenCalled()
    })
  })

  describe('Touch Targets', () => {
    it('has minimum 44px height on small size', () => {
      render(<Button size="sm">Small</Button>)
      expect(screen.getByRole('button')).toHaveClass('min-h-[44px]')
    })

    it('has minimum 48px height on medium size', () => {
      render(<Button size="md">Medium</Button>)
      expect(screen.getByRole('button')).toHaveClass('min-h-[48px]')
    })

    it('has minimum 56px height on large size', () => {
      render(<Button size="lg">Large</Button>)
      expect(screen.getByRole('button')).toHaveClass('min-h-[56px]')
    })

    it('has touch-manipulation CSS property', () => {
      render(<Button>Touch Target</Button>)
      expect(screen.getByRole('button')).toHaveClass('touch-manipulation')
    })
  })

  describe('Keyboard Accessibility', () => {
    it('is keyboard focusable', () => {
      render(<Button>Focusable</Button>)
      const button = screen.getByRole('button')
      button.focus()
      expect(document.activeElement).toBe(button)
    })

    it('is not focusable when disabled', () => {
      render(<Button disabled>Not Focusable</Button>)
      const button = screen.getByRole('button')
      button.focus()
      expect(document.activeElement).not.toBe(button)
    })

    it('has visible focus ring', () => {
      render(<Button>Focus Ring</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveClass('focus:ring-2')
      expect(button).toHaveClass('focus:ring-lsc-rose')
    })

    it('has focus outline removed in favor of ring', () => {
      render(<Button>Focus</Button>)
      expect(screen.getByRole('button')).toHaveClass('focus:outline-none')
    })
  })

  describe('ARIA Attributes', () => {
    it('has implicit button role', () => {
      render(<Button>Button</Button>)
      expect(screen.getByRole('button')).toBeInTheDocument()
    })

    it('accepts custom aria attributes', () => {
      render(
        <Button aria-label={t('aria.ui.customLabel')} aria-describedby="description">
          Text
        </Button>
      )
      const button = screen.getByRole('button', { name: 'Custom label' })
      expect(button).toHaveAttribute('aria-describedby', 'description')
    })

    it('loading spinner has aria-hidden', () => {
      render(<Button isLoading>Loading</Button>)
      const spinner = document.querySelector('[aria-hidden="true"]')
      expect(spinner).toBeInTheDocument()
    })

    it('provides screen reader text for loading state', () => {
      render(<Button isLoading loadingAction="load">Submit</Button>)
      const loadingText = screen.getByText('Loading...')
      expect(loadingText).toBeInTheDocument()
    })

    it('icons have aria-hidden', () => {
      render(
        <Button leftIcon={<Home />} rightIcon={<ChevronRight />}>
          Test
        </Button>
      )
      const spans = screen.getByRole('button').querySelectorAll('span[aria-hidden="true"]')
      expect(spans.length).toBe(2)
    })
  })

  describe('HTML Attributes', () => {
    it('accepts type attribute', () => {
      render(<Button type="submit">Submit</Button>)
      expect(screen.getByRole('button')).toHaveAttribute('type', 'submit')
    })

    it('accepts form attribute', () => {
      render(<Button form="my-form">Submit</Button>)
      expect(screen.getByRole('button')).toHaveAttribute('form', 'my-form')
    })

    it('accepts name and value attributes', () => {
      render(<Button name="action" value="save">Save</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveAttribute('name', 'action')
      expect(button).toHaveAttribute('value', 'save')
    })

    it('forwards other HTML button attributes', () => {
      render(<Button data-testid="test-button" id="my-button">Test</Button>)
      const button = screen.getByRole('button')
      expect(button).toHaveAttribute('data-testid', 'test-button')
      expect(button).toHaveAttribute('id', 'my-button')
    })
  })

  describe('Accessibility Compliance', () => {
    it('has no accessibility violations (primary)', async () => {
      const { container } = render(<Button variant="primary">Primary</Button>)
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })

    it('has no accessibility violations (secondary)', async () => {
      const { container } = render(<Button variant="secondary">Secondary</Button>)
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })

    it('has no accessibility violations (tertiary)', async () => {
      const { container } = render(<Button variant="tertiary">Tertiary</Button>)
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })

    it('has no accessibility violations (danger)', async () => {
      const { container } = render(<Button variant="danger">Delete</Button>)
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })

    it('has no accessibility violations (disabled)', async () => {
      const { container } = render(<Button disabled>Disabled</Button>)
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })

    it('has no accessibility violations (loading)', async () => {
      const { container } = render(<Button isLoading>Loading</Button>)
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })

    it('has no accessibility violations (with icons)', async () => {
      const { container } = render(
        <Button leftIcon={<Home />} rightIcon={<ChevronRight />}>
          With Icons
        </Button>
      )
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })
  })

  describe('Edge Cases', () => {
    it('handles empty children', () => {
      render(<Button>{''}</Button>)
      expect(screen.getByRole('button')).toBeInTheDocument()
    })

    it('handles multiple children nodes', () => {
      render(
        <Button>
          <span>Part 1</span>
          <span>Part 2</span>
        </Button>
      )
      expect(screen.getByText('Part 1')).toBeInTheDocument()
      expect(screen.getByText('Part 2')).toBeInTheDocument()
    })

    it('handles rapid clicks', async () => {
      const handleClick = vi.fn()
      const user = userEvent.setup()

      render(<Button onClick={handleClick}>Click</Button>)
      const button = screen.getByRole('button')

      await user.click(button)
      await user.click(button)
      await user.click(button)

      expect(handleClick).toHaveBeenCalledTimes(3)
    })

    it('handles click during loading state transition', async () => {
      const handleClick = vi.fn()
      const { rerender } = render(<Button onClick={handleClick}>Submit</Button>)

      // Click before loading
      const user = userEvent.setup()
      await user.click(screen.getByRole('button'))
      expect(handleClick).toHaveBeenCalledTimes(1)

      // Set to loading
      rerender(<Button onClick={handleClick} isLoading>Submit</Button>)

      // Try clicking during loading
      await user.click(screen.getByRole('button'))
      expect(handleClick).toHaveBeenCalledTimes(1) // Should not increment
    })

    it('preserves focus after state changes', async () => {
      const { rerender } = render(<Button>Test</Button>)
      const button = screen.getByRole('button')

      button.focus()
      expect(document.activeElement).toBe(button)

      rerender(<Button variant="secondary">Test</Button>)
      expect(document.activeElement).toBe(button)
    })
  })

  describe('Animation and Transitions', () => {
    it('has transition classes', () => {
      render(<Button>Animated</Button>)
      expect(screen.getByRole('button')).toHaveClass('transition-all')
      expect(screen.getByRole('button')).toHaveClass('duration-200')
    })

    it('loading spinner respects prefers-reduced-motion', () => {
      render(<Button isLoading>Loading</Button>)
      const spinner = document.querySelector('.motion-safe\\:animate-spin')
      expect(spinner).toBeInTheDocument()
    })
  })
})
