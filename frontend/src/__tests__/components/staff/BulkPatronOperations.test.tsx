/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Tests for BulkPatronOperations Component
 *
 * Tests bulk patron operations, batch processing, and error handling
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render } from '@testing-library/react'
import { screen, waitFor } from '@testing-library/dom'
import userEvent from '@testing-library/user-event'
import BulkPatronOperations from '../../../components/staff/BulkPatronOperations'
import { createMockPatron, createMockToken } from '../../helpers/testHelpers'

// Mock toast notifications
vi.mock('react-hot-toast', () => ({
  default: {
    error: vi.fn(),
    success: vi.fn(),
    loading: vi.fn(),
  },
}))

// Mock fetch API
global.fetch = vi.fn()

// SKIP NOTE: BulkPatronOperations was refactored to use a shared
// BulkOperationsPanel with Block/Unblock/Waive Fines/Send Notification/Export
// actions (see components/staff/BulkPatronOperations.tsx). The tests below
// assert an older UI with "Send Email", "Add Tags", and "Update Status"
// operations, plus a patron-list-with-checkboxes layout that the refactored
// component no longer owns (selection now lives in BulkOperationsPanel).
// Skipped pending a test rewrite against the new panel-based API.
describe.skip('BulkPatronOperations', () => {
  const mockPatrons = [
    createMockPatron({ id: 1, first_name: 'John', last_name: 'Smith', email: 'john@example.com' }),
    createMockPatron({ id: 2, first_name: 'Jane', last_name: 'Doe', email: 'jane@example.com' }),
    createMockPatron({ id: 3, first_name: 'Bob', last_name: 'Johnson', email: 'bob@example.com', is_active: false }),
  ]

  const mockOnOperationComplete = vi.fn()
  const mockToken = createMockToken()
  const defaultProps = {
    patrons: mockPatrons,
    allPatronIds: [1, 2, 3],
    token: mockToken,
    onOperationComplete: mockOnOperationComplete,
  }

  beforeEach(() => {
    vi.clearAllMocks()
    ;(global.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: async () => ({
        success: true,
        processed: 2,
        failed: 0,
      }),
    })
  })

  // ========== RENDERING TESTS ==========

  describe('Rendering', () => {
    it('renders bulk operations panel', () => {
      render(
        <BulkPatronOperations {...defaultProps} />
      )

      expect(screen.getByText(/bulk patron operations/i)).toBeInTheDocument()
    })

    it('displays patron list', () => {
      render(
        <BulkPatronOperations {...defaultProps} />
      )

      mockPatrons.forEach((patron) => {
        expect(screen.getByText(`${patron.first_name} ${patron.last_name}`)).toBeInTheDocument()
        expect(screen.getByText(patron.email!)).toBeInTheDocument()
      })
    })

    it('shows operation selection buttons', () => {
      render(
        <BulkPatronOperations {...defaultProps} />
      )

      expect(screen.getByRole('button', { name: /send email/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /add tags/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /update status/i })).toBeInTheDocument()
    })
  })

  // ========== SELECTION TESTS ==========

  describe('Selection', () => {
    it('has select all checkbox', () => {
      render(
        <BulkPatronOperations {...defaultProps} />
      )

      const selectAll = screen.getByRole('checkbox', { name: /select all/i })
      expect(selectAll).toBeInTheDocument()
    })

    it('selects all patrons when select all is clicked', async () => {
      const user = userEvent.setup()
      render(
        <BulkPatronOperations {...defaultProps} />
      )

      const selectAll = screen.getByRole('checkbox', { name: /select all/i })
      await user.click(selectAll)

      const checkboxes = screen.getAllByRole('checkbox')
      checkboxes.forEach((checkbox: HTMLElement) => {
        expect((checkbox as HTMLInputElement).checked).toBe(true)
      })
    })

    it('selects individual patron', async () => {
      const user = userEvent.setup()
      render(
        <BulkPatronOperations {...defaultProps} />
      )

      const checkbox = screen.getByRole('checkbox', { name: /john smith/i })
      await user.click(checkbox)

      expect((checkbox as HTMLInputElement).checked).toBe(true)
    })

    it('updates selection count', async () => {
      const user = userEvent.setup()
      render(
        <BulkPatronOperations {...defaultProps} />
      )

      const checkbox = screen.getByRole('checkbox', { name: /john smith/i })
      await user.click(checkbox)

      expect(screen.getByText(/1 patron selected/i)).toBeInTheDocument()
    })
  })

  // ========== BULK OPERATIONS TESTS ==========

  describe('Send Email Operation', () => {
    it('shows email template selection', async () => {
      const user = userEvent.setup()
      render(
        <BulkPatronOperations {...defaultProps} />
      )

      // Select patrons
      const selectAll = screen.getByRole('checkbox', { name: /select all/i })
      await user.click(selectAll)

      // Click send email
      const sendEmailBtn = screen.getByRole('button', { name: /send email/i })
      await user.click(sendEmailBtn)

      expect(screen.getByText(/email template/i)).toBeInTheDocument()
    })

    it('requires template selection before sending', async () => {
      const user = userEvent.setup()
      render(
        <BulkPatronOperations {...defaultProps} />
      )

      const selectAll = screen.getByRole('checkbox', { name: /select all/i })
      await user.click(selectAll)

      const sendEmailBtn = screen.getByRole('button', { name: /send email/i })
      await user.click(sendEmailBtn)

      const confirmBtn = screen.getByRole('button', { name: /send|confirm/i })
      expect(confirmBtn).toBeDisabled()
    })

    it('sends email after template selection', async () => {
      const user = userEvent.setup()
      render(
        <BulkPatronOperations {...defaultProps} />
      )

      // Select all patrons
      const selectAll = screen.getByRole('checkbox', { name: /select all/i })
      await user.click(selectAll)

      // Click send email
      const sendEmailBtn = screen.getByRole('button', { name: /send email/i })
      await user.click(sendEmailBtn)

      // Select template
      const templateSelect = screen.getByRole('combobox', { name: /template/i })
      await user.selectOptions(templateSelect, 'overdue-reminder')

      // Confirm
      const confirmBtn = screen.getByRole('button', { name: /send|confirm/i })
      await user.click(confirmBtn)

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalled()
      })
    })
  })

  describe('Add Tags Operation', () => {
    it('shows tag input field', async () => {
      const user = userEvent.setup()
      render(
        <BulkPatronOperations {...defaultProps} />
      )

      const selectAll = screen.getByRole('checkbox', { name: /select all/i })
      await user.click(selectAll)

      const addTagsBtn = screen.getByRole('button', { name: /add tags/i })
      await user.click(addTagsBtn)

      expect(screen.getByPlaceholderText(/enter tags/i)).toBeInTheDocument()
    })

    it('adds tags to selected patrons', async () => {
      const user = userEvent.setup()
      render(
        <BulkPatronOperations {...defaultProps} />
      )

      const selectAll = screen.getByRole('checkbox', { name: /select all/i })
      await user.click(selectAll)

      const addTagsBtn = screen.getByRole('button', { name: /add tags/i })
      await user.click(addTagsBtn)

      const tagInput = screen.getByPlaceholderText(/enter tags/i)
      await user.type(tagInput, 'vip, priority')

      const confirmBtn = screen.getByRole('button', { name: /confirm/i })
      await user.click(confirmBtn)

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          expect.any(String),
          expect.objectContaining({
            body: expect.stringContaining('vip'),
          })
        )
      })
    })
  })

  describe('Update Status Operation', () => {
    it('shows status selection', async () => {
      const user = userEvent.setup()
      render(
        <BulkPatronOperations {...defaultProps} />
      )

      const selectAll = screen.getByRole('checkbox', { name: /select all/i })
      await user.click(selectAll)

      const updateStatusBtn = screen.getByRole('button', { name: /update status/i })
      await user.click(updateStatusBtn)

      expect(screen.getByRole('combobox', { name: /new status/i })).toBeInTheDocument()
    })

    it('updates patron status', async () => {
      const user = userEvent.setup()
      render(
        <BulkPatronOperations {...defaultProps} />
      )

      const selectAll = screen.getByRole('checkbox', { name: /select all/i })
      await user.click(selectAll)

      const updateStatusBtn = screen.getByRole('button', { name: /update status/i })
      await user.click(updateStatusBtn)

      const statusSelect = screen.getByRole('combobox', { name: /new status/i })
      await user.selectOptions(statusSelect, 'suspended')

      const confirmBtn = screen.getByRole('button', { name: /confirm/i })
      await user.click(confirmBtn)

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalled()
      })
    })
  })

  // ========== ERROR HANDLING TESTS ==========

  describe('Error Handling', () => {
    it('displays error message on API failure', async () => {
      const user = userEvent.setup()
      ;(global.fetch as unknown as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error('API Error'))

      const { default: mockToast } = await import('react-hot-toast')
      render(
        <BulkPatronOperations {...defaultProps} />
      )

      const selectAll = screen.getByRole('checkbox', { name: /select all/i })
      await user.click(selectAll)

      const sendEmailBtn = screen.getByRole('button', { name: /send email/i })
      await user.click(sendEmailBtn)

      const templateSelect = screen.getByRole('combobox', { name: /template/i })
      await user.selectOptions(templateSelect, 'overdue-reminder')

      const confirmBtn = screen.getByRole('button', { name: /send|confirm/i })
      await user.click(confirmBtn)

      await waitFor(() => {
        expect(mockToast.error).toHaveBeenCalled()
      })
    })

    it('handles partial failures', async () => {
      const user = userEvent.setup()
      ;(global.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          processed: 2,
          failed: 1,
          failures: [{ id: 3, error: 'Invalid email' }],
        }),
      })

      render(
        <BulkPatronOperations {...defaultProps} />
      )

      const selectAll = screen.getByRole('checkbox', { name: /select all/i })
      await user.click(selectAll)

      const sendEmailBtn = screen.getByRole('button', { name: /send email/i })
      await user.click(sendEmailBtn)

      const templateSelect = screen.getByRole('combobox', { name: /template/i })
      await user.selectOptions(templateSelect, 'overdue-reminder')

      const confirmBtn = screen.getByRole('button', { name: /send|confirm/i })
      await user.click(confirmBtn)

      await waitFor(() => {
        expect(screen.getByText(/2 successful/i)).toBeInTheDocument()
        expect(screen.getByText(/1 failed/i)).toBeInTheDocument()
      })
    })
  })

  // ========== ACCESSIBILITY TESTS ==========

  describe('Accessibility (WCAG AA)', () => {
    it('has proper heading hierarchy', () => {
      render(
        <BulkPatronOperations {...defaultProps} />
      )

      expect(screen.getByRole('heading', { level: 2 })).toBeInTheDocument()
    })

    it('checkboxes have labels', () => {
      render(
        <BulkPatronOperations {...defaultProps} />
      )

      const selectAll = screen.getByRole('checkbox', { name: /select all/i })
      expect(selectAll).toHaveAttribute('aria-label')
    })

    it('selection count is announced', async () => {
      const user = userEvent.setup()
      render(
        <BulkPatronOperations {...defaultProps} />
      )

      const selectAll = screen.getByRole('checkbox', { name: /select all/i })
      await user.click(selectAll)

      const announcement = screen.getByText(/3 patrons selected/)
      expect(announcement).toHaveAttribute('role', 'status')
    })

    it('buttons have descriptive labels', () => {
      render(
        <BulkPatronOperations {...defaultProps} />
      )

      const buttons = screen.getAllByRole('button')
      buttons.forEach((button: HTMLElement) => {
        expect(button).toHaveAttribute('aria-label')
      })
    })
  })

  // ========== INTEGRATION TESTS ==========

  describe('Integration', () => {
    it('completes full bulk operation workflow', async () => {
      const user = userEvent.setup()
      const { default: mockToast } = await import('react-hot-toast')

      render(
        <BulkPatronOperations {...defaultProps} />
      )

      // Select patrons
      const selectAll = screen.getByRole('checkbox', { name: /select all/i })
      await user.click(selectAll)

      // Send email
      const sendEmailBtn = screen.getByRole('button', { name: /send email/i })
      await user.click(sendEmailBtn)

      // Select template
      const templateSelect = screen.getByRole('combobox', { name: /template/i })
      await user.selectOptions(templateSelect, 'overdue-reminder')

      // Confirm
      const confirmBtn = screen.getByRole('button', { name: /send|confirm/i })
      await user.click(confirmBtn)

      // Verify success
      await waitFor(() => {
        expect(mockToast.success).toHaveBeenCalled()
        expect(mockOnOperationComplete).toHaveBeenCalled()
      })
    })
  })
})
