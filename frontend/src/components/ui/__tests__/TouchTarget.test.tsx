/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * TouchTarget Component Tests
 *
 * Tests for TouchTarget wrapper component ensuring WCAG 2.2 Level AAA
 * minimum touch target size of 44x44px
 */

import { describe, it, expect, vi } from 'vitest'
import { render } from "@testing-library/react"
import { screen } from "@testing-library/react"
import userEvent from '@testing-library/user-event'
import { axe } from 'jest-axe'
import { TouchTarget, touchTargetClass } from '../TouchTarget'
import { X } from 'lucide-react'
import { t } from '@/i18n'

describe('TouchTarget Component', () => {
  describe('Rendering', () => {
    it('renders children correctly', () => {
      render(
        <TouchTarget>
          <span>Content</span>
        </TouchTarget>
      )
      expect(screen.getByText('Content')).toBeInTheDocument()
    })

    it('renders as div by default', () => {
      render(
        <TouchTarget data-testid="target">
          <span>Test</span>
        </TouchTarget>
      )
      const element = screen.getByTestId('target')
      expect(element.tagName).toBe('DIV')
    })

    it('renders as button when specified', () => {
      render(
        <TouchTarget as="button" data-testid="target">
          Click
        </TouchTarget>
      )
      const element = screen.getByTestId('target')
      expect(element.tagName).toBe('BUTTON')
    })

    it('renders as anchor when specified', () => {
      render(
        <TouchTarget as="a" data-testid="target" href="/">
          Link
        </TouchTarget>
      )
      const element = screen.getByTestId('target')
      expect(element.tagName).toBe('A')
    })

    it('accepts custom className', () => {
      render(
        <TouchTarget className="custom-class" data-testid="target">
          Test
        </TouchTarget>
      )
      expect(screen.getByTestId('target')).toHaveClass('custom-class')
    })
  })

  describe('Touch Target Size', () => {
    it('enforces minimum 44px width', () => {
      render(
        <TouchTarget data-testid="target">
          <X size={16} />
        </TouchTarget>
      )
      expect(screen.getByTestId('target')).toHaveClass('min-w-[44px]')
    })

    it('enforces minimum 44px height', () => {
      render(
        <TouchTarget data-testid="target">
          <X size={16} />
        </TouchTarget>
      )
      expect(screen.getByTestId('target')).toHaveClass('min-h-[44px]')
    })

    it('has touch-manipulation CSS property', () => {
      render(
        <TouchTarget data-testid="target">
          Test
        </TouchTarget>
      )
      expect(screen.getByTestId('target')).toHaveClass('touch-manipulation')
    })

    it('applies all required classes together', () => {
      render(
        <TouchTarget data-testid="target">
          Test
        </TouchTarget>
      )
      const element = screen.getByTestId('target')
      expect(element).toHaveClass('min-w-[44px]')
      expect(element).toHaveClass('min-h-[44px]')
      expect(element).toHaveClass('touch-manipulation')
    })
  })

  describe('Layout and Positioning', () => {
    it('uses inline-flex display', () => {
      render(
        <TouchTarget data-testid="target">
          Test
        </TouchTarget>
      )
      expect(screen.getByTestId('target')).toHaveClass('inline-flex')
    })

    it('centers items', () => {
      render(
        <TouchTarget data-testid="target">
          Test
        </TouchTarget>
      )
      const element = screen.getByTestId('target')
      expect(element).toHaveClass('items-center')
      expect(element).toHaveClass('justify-center')
    })

    it('works with inline elements', () => {
      render(
        <div>
          Text before
          <TouchTarget data-testid="target">
            <span>Inline</span>
          </TouchTarget>
          Text after
        </div>
      )
      expect(screen.getByTestId('target')).toHaveClass('inline-flex')
    })

    it('works with block-level elements', () => {
      render(
        <TouchTarget data-testid="target">
          <div>Block content</div>
        </TouchTarget>
      )
      expect(screen.getByText('Block content')).toBeInTheDocument()
    })
  })

  describe('Children Handling', () => {
    it('wraps single child element', () => {
      render(
        <TouchTarget data-testid="target">
          <button>Click</button>
        </TouchTarget>
      )
      expect(screen.getByRole('button')).toBeInTheDocument()
    })

    it('wraps multiple child elements', () => {
      render(
        <TouchTarget data-testid="target">
          <span>First</span>
          <span>Second</span>
        </TouchTarget>
      )
      expect(screen.getByText('First')).toBeInTheDocument()
      expect(screen.getByText('Second')).toBeInTheDocument()
    })

    it('wraps text content', () => {
      render(
        <TouchTarget data-testid="target">
          Plain text
        </TouchTarget>
      )
      expect(screen.getByText('Plain text')).toBeInTheDocument()
    })

    it('wraps icon components', () => {
      render(
        <TouchTarget data-testid="target">
          <X data-testid="icon" size={16} />
        </TouchTarget>
      )
      expect(screen.getByTestId('icon')).toBeInTheDocument()
    })

    it('preserves child element classes', () => {
      render(
        <TouchTarget data-testid="target">
          <button className="child-class">Button</button>
        </TouchTarget>
      )
      expect(screen.getByRole('button')).toHaveClass('child-class')
    })
  })

  describe('Props and Attributes', () => {
    it('forwards HTML attributes to wrapper', () => {
      render(
        <TouchTarget
          data-testid="target"
          id="unique-id"
          title="Tooltip"
        >
          Content
        </TouchTarget>
      )
      const element = screen.getByTestId('target')
      expect(element).toHaveAttribute('id', 'unique-id')
      expect(element).toHaveAttribute('title', 'Tooltip')
    })

    it('forwards event handlers', async () => {
      const handleClick = vi.fn()
      const user = userEvent.setup()

      render(
        <TouchTarget
          as="button"
          onClick={handleClick}
          data-testid="target"
        >
          Click me
        </TouchTarget>
      )

      await user.click(screen.getByTestId('target'))
      expect(handleClick).toHaveBeenCalledTimes(1)
    })

    it('forwards aria attributes', () => {
      render(
        <TouchTarget
          as="button"
          aria-label={t('aria.responseComposerDialog.closeDialog')}
          aria-pressed="false"
          data-testid="target"
        >
          <X size={16} />
        </TouchTarget>
      )
      const element = screen.getByTestId('target')
      expect(element).toHaveAttribute('aria-label', 'Close dialog')
      expect(element).toHaveAttribute('aria-pressed', 'false')
    })

    it('accepts ref prop when used as button', () => {
      const ref = { current: null }
      render(
        <TouchTarget
          as="button"
          ref={ref}
          data-testid="target"
        >
          Button
        </TouchTarget>
      )
      expect(screen.getByTestId('target')).toBeInTheDocument()
    })

    it('accepts href when used as anchor', () => {
      render(
        <TouchTarget
          as="a"
          href="/page"
          data-testid="target"
        >
          Link
        </TouchTarget>
      )
      expect(screen.getByTestId('target')).toHaveAttribute('href', '/page')
    })
  })

  describe('Button Variant', () => {
    it('renders as button with type attribute', () => {
      render(
        <TouchTarget as="button" type="submit" data-testid="target">
          Submit
        </TouchTarget>
      )
      const button = screen.getByTestId('target')
      expect(button.tagName).toBe('BUTTON')
      expect(button).toHaveAttribute('type', 'submit')
    })

    it('handles disabled state on button', () => {
      render(
        <TouchTarget as="button" disabled data-testid="target">
          Disabled
        </TouchTarget>
      )
      expect(screen.getByTestId('target')).toBeDisabled()
    })

    it('is keyboard accessible as button', () => {
      render(
        <TouchTarget as="button" data-testid="target">
          Focus me
        </TouchTarget>
      )
      const button = screen.getByTestId('target')
      button.focus()
      expect(document.activeElement).toBe(button)
    })

    it('handles button click events', async () => {
      const handleClick = vi.fn()
      const user = userEvent.setup()

      render(
        <TouchTarget as="button" onClick={handleClick} data-testid="target">
          Click
        </TouchTarget>
      )

      await user.click(screen.getByTestId('target'))
      expect(handleClick).toHaveBeenCalledTimes(1)
    })
  })

  describe('Anchor Variant', () => {
    it('renders as anchor with href', () => {
      render(
        <TouchTarget as="a" href="/test" data-testid="target">
          Link
        </TouchTarget>
      )
      const link = screen.getByTestId('target')
      expect(link.tagName).toBe('A')
      expect(link).toHaveAttribute('href', '/test')
    })

    it('accepts target and rel attributes for links', () => {
      render(
        <TouchTarget
          as="a"
          href="https://example.com"
          target="_blank"
          rel="noopener noreferrer"
          data-testid="target"
        >
          External
        </TouchTarget>
      )
      const link = screen.getByTestId('target')
      expect(link).toHaveAttribute('target', '_blank')
      expect(link).toHaveAttribute('rel', 'noopener noreferrer')
    })

    it('is keyboard accessible as anchor', () => {
      render(
        <TouchTarget as="a" href="/test" data-testid="target">
          Link
        </TouchTarget>
      )
      const link = screen.getByTestId('target')
      link.focus()
      expect(document.activeElement).toBe(link)
    })
  })

  describe('Use Cases', () => {
    it('wraps small close button', () => {
      render(
        <TouchTarget as="button" aria-label={t('aria.authModals.close')} data-testid="target">
          <X size={16} />
        </TouchTarget>
      )
      const button = screen.getByTestId('target')
      expect(button).toHaveClass('min-w-[44px]')
      expect(button).toHaveClass('min-h-[44px]')
    })

    it('wraps small badge or chip', () => {
      render(
        <TouchTarget as="button" data-testid="target">
          <span className="text-xs px-2 py-1">Badge</span>
        </TouchTarget>
      )
      expect(screen.getByTestId('target')).toHaveClass('min-w-[44px]')
      expect(screen.getByTestId('target')).toHaveClass('min-h-[44px]')
    })

    it('wraps small icon button', () => {
      render(
        <TouchTarget as="button" aria-label={t('aria.ui.delete')} data-testid="target">
          <X size={20} />
        </TouchTarget>
      )
      const button = screen.getByTestId('target')
      expect(button).toHaveAttribute('aria-label', 'Delete')
      expect(button).toHaveClass('min-w-[44px]')
    })

    it('wraps custom interactive element', () => {
      render(
        <TouchTarget
          as="div"
          role="button"
          tabIndex={0}
          aria-label={t('aria.ui.customControl')}
          data-testid="target"
        >
          <span>🎯</span>
        </TouchTarget>
      )
      const element = screen.getByTestId('target')
      expect(element).toHaveAttribute('role', 'button')
      expect(element).toHaveAttribute('tabIndex', '0')
    })
  })

  describe('Utility Class', () => {
    it('exports touchTargetClass constant', () => {
      expect(touchTargetClass).toBe('min-w-[44px] min-h-[44px] touch-manipulation')
    })

    it('touchTargetClass can be applied directly', () => {
      render(
        <button className={touchTargetClass} data-testid="target">
          Test
        </button>
      )
      const button = screen.getByTestId('target')
      expect(button).toHaveClass('min-w-[44px]')
      expect(button).toHaveClass('min-h-[44px]')
      expect(button).toHaveClass('touch-manipulation')
    })
  })

  describe('Accessibility Compliance', () => {
    it('has no accessibility violations as div', async () => {
      const { container } = render(
        <TouchTarget>
          <span>Content</span>
        </TouchTarget>
      )
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })

    it('has no accessibility violations as button', async () => {
      const { container } = render(
        <TouchTarget as="button">
          Click me
        </TouchTarget>
      )
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })

    it('has no accessibility violations as button with icon', async () => {
      const { container } = render(
        <TouchTarget as="button" aria-label={t('aria.authModals.close')}>
          <X size={16} />
        </TouchTarget>
      )
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })

    it('has no accessibility violations as anchor', async () => {
      const { container } = render(
        <TouchTarget as="a" href="/test">
          Link
        </TouchTarget>
      )
      const results = await axe(container)
      expect(results).toHaveNoViolations()
    })

    it('meets WCAG 2.2 SC 2.5.8 minimum target size', () => {
      render(
        <TouchTarget data-testid="target">
          <X size={16} />
        </TouchTarget>
      )
      // Verifies that component has the required classes
      // In actual implementation, these translate to 44x44px minimum
      const element = screen.getByTestId('target')
      expect(element).toHaveClass('min-w-[44px]')
      expect(element).toHaveClass('min-h-[44px]')
    })
  })

  describe('Integration with Other Components', () => {
    it('can wrap custom button components', () => {
      const CustomButton = ({ children }: { children: React.ReactNode }) => (
        <button className="custom-btn">{children}</button>
      )

      render(
        <TouchTarget data-testid="target">
          <CustomButton>Custom</CustomButton>
        </TouchTarget>
      )
      expect(screen.getByRole('button')).toBeInTheDocument()
      expect(screen.getByTestId('target')).toHaveClass('min-w-[44px]')
    })

    it('works within larger interactive components', () => {
      render(
        <div className="card">
          <div className="card-header">
            <h3>Card Title</h3>
            <TouchTarget as="button" aria-label={t('aria.ui.closeCard')} data-testid="close">
              <X size={16} />
            </TouchTarget>
          </div>
        </div>
      )
      expect(screen.getByTestId('close')).toHaveClass('min-w-[44px]')
    })
  })

  describe('Edge Cases', () => {
    it('handles empty children', () => {
      render(
        <TouchTarget data-testid="target">
          {''}
        </TouchTarget>
      )
      expect(screen.getByTestId('target')).toBeInTheDocument()
    })

    it('handles null children gracefully', () => {
      render(
        <TouchTarget data-testid="target">
          {null}
        </TouchTarget>
      )
      expect(screen.getByTestId('target')).toBeInTheDocument()
    })

    it('combines with custom classes properly', () => {
      render(
        <TouchTarget
          className="bg-earth-500 text-white rounded-full"
          data-testid="target"
        >
          Test
        </TouchTarget>
      )
      const element = screen.getByTestId('target')
      expect(element).toHaveClass('bg-earth-500')
      expect(element).toHaveClass('min-w-[44px]')
      expect(element).toHaveClass('min-h-[44px]')
    })

    it('preserves existing inline-flex from custom classes', () => {
      render(
        <TouchTarget
          className="inline-flex gap-2"
          data-testid="target"
        >
          Test
        </TouchTarget>
      )
      expect(screen.getByTestId('target')).toHaveClass('inline-flex')
    })
  })

  describe('Performance', () => {
    it('does not re-render unnecessarily', () => {
      const { rerender } = render(
        <TouchTarget data-testid="target">
          Content 1
        </TouchTarget>
      )
      const element1 = screen.getByTestId('target')

      rerender(
        <TouchTarget data-testid="target">
          Content 1
        </TouchTarget>
      )
      const element2 = screen.getByTestId('target')

      expect(element1).toBe(element2)
    })
  })
})
