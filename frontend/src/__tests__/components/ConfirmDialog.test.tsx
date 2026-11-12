/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, userEvent } from '../utils/test-utils'
import ConfirmDialog from '../../components/ConfirmDialog'
import { a11yPatterns } from '../utils/accessibility'

// Mock focus-trap-react for test environment - FocusTrap doesn't work well in jsdom
vi.mock('focus-trap-react', () => ({
  default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

beforeEach(() => {
  vi.clearAllMocks()
})

describe('ConfirmDialog', () => {
  const defaultProps = {
    isOpen: true,
    title: 'Confirm Action',
    message: 'Are you sure you want to proceed?',
    onConfirm: vi.fn(),
    onCancel: vi.fn(),
  }

  describe('Accessibility', () => {
    it('should have proper dialog ARIA attributes', () => {
      render(<ConfirmDialog {...defaultProps} />)

      const dialog = screen.getByRole('dialog')
      expect(dialog).toHaveAttribute('aria-modal', 'true')
      expect(dialog).toHaveAttribute('aria-labelledby', 'confirm-dialog-title')
      expect(dialog).toHaveAttribute('aria-describedby', 'confirm-dialog-description')
    })

    it('should have accessible title and description', () => {
      render(<ConfirmDialog {...defaultProps} />)

      const title = screen.getByRole('heading', { name: /confirm action/i })
      expect(title).toHaveAttribute('id', 'confirm-dialog-title')

      const description = screen.getByText(/are you sure you want to proceed/i)
      expect(description).toHaveAttribute('id', 'confirm-dialog-description')
    })

    it('should render confirm button that can receive focus', () => {
      render(<ConfirmDialog {...defaultProps} />)

      const confirmButton = screen.getByRole('button', { name: /yes, proceed/i })
      // Confirm button should exist and be focusable
      expect(confirmButton).toBeInTheDocument()
      expect(confirmButton).not.toBeDisabled()
    })

    it('should close on Escape key', async () => {
      const onCancel = vi.fn()
      const user = userEvent.setup()

      render(<ConfirmDialog {...defaultProps} onCancel={onCancel} />)

      await user.keyboard('{Escape}')
      expect(onCancel).toHaveBeenCalled()
    })

    it('should have focusable buttons in dialog', () => {
      render(<ConfirmDialog {...defaultProps} />)

      const cancelButton = screen.getByRole('button', { name: /go back/i })
      const confirmButton = screen.getByRole('button', { name: /yes, proceed/i })

      // Both buttons should be focusable
      expect(cancelButton).not.toBeDisabled()
      expect(confirmButton).not.toBeDisabled()
    })

    it('should have buttons with accessible names', () => {
      render(
        <ConfirmDialog
          {...defaultProps}
          confirmText="Delete"
          cancelText="Keep"
        />
      )

      expect(screen.getByRole('button', { name: 'Delete' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Keep' })).toBeInTheDocument()
    })

    it('dialog should match accessibility patterns', () => {
      render(<ConfirmDialog {...defaultProps} />)

      const dialog = screen.getByRole('dialog')
      expect(a11yPatterns.isAccessibleDialog(dialog)).toBe(true)
    })
  })

  describe('Behavior', () => {
    it('should not render when closed', () => {
      render(<ConfirmDialog {...defaultProps} isOpen={false} />)
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })

    it('should call onConfirm when confirm button is clicked', async () => {
      const onConfirm = vi.fn()
      const user = userEvent.setup()

      render(<ConfirmDialog {...defaultProps} onConfirm={onConfirm} />)

      await user.click(screen.getByRole('button', { name: /yes, proceed/i }))
      expect(onConfirm).toHaveBeenCalled()
    })

    it('should call onCancel when cancel button is clicked', async () => {
      const onCancel = vi.fn()
      const user = userEvent.setup()

      render(<ConfirmDialog {...defaultProps} onCancel={onCancel} />)

      await user.click(screen.getByRole('button', { name: /go back/i }))
      expect(onCancel).toHaveBeenCalled()
    })

    it('should call onCancel when backdrop is clicked', async () => {
      const onCancel = vi.fn()
      const user = userEvent.setup()

      render(<ConfirmDialog {...defaultProps} onCancel={onCancel} />)

      // Click on backdrop (the aria-hidden div)
      const backdrop = document.querySelector('[aria-hidden="true"]')
      expect(backdrop).toBeInTheDocument()
      await user.click(backdrop!)
      expect(onCancel).toHaveBeenCalled()
    })

    it('should disable buttons during loading', () => {
      render(<ConfirmDialog {...defaultProps} loading={true} />)

      expect(screen.getByRole('button', { name: /go back/i })).toBeDisabled()
      expect(screen.getByRole('button', { name: /yes, proceed/i })).toBeDisabled()
    })
  })

  describe('Variants', () => {
    it('should render danger variant', () => {
      render(<ConfirmDialog {...defaultProps} confirmVariant="danger" />)
      const confirmButton = screen.getByRole('button', { name: /yes, proceed/i })
      expect(confirmButton).toHaveClass('bg-status-danger-600')
    })

    it('should render success variant', () => {
      render(<ConfirmDialog {...defaultProps} confirmVariant="success" />)
      const confirmButton = screen.getByRole('button', { name: /yes, proceed/i })
      expect(confirmButton).toHaveClass('bg-status-success-600')
    })
  })
})
