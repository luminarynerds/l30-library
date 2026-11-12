/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Tests for SendNotificationModal Component
 *
 * Tests notification sending, template selection, and delivery tracking
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import SendNotificationModal from '../../../components/staff/SendNotificationModal'
import toast from 'react-hot-toast'
import { createMockPatron } from '../../helpers/testHelpers'

// Mock toast notifications
vi.mock('react-hot-toast', () => ({
  default: {
    error: vi.fn(),
    success: vi.fn(),
    loading: vi.fn(),
  },
}))

describe('SendNotificationModal', () => {
  const mockOnClose = vi.fn()
  const mockOnSend = vi.fn()
  const mockPatron = createMockPatron({ first_name: 'Jane', last_name: 'Rivera', phone: '555-0100' })

  beforeEach(() => {
    vi.clearAllMocks()
    mockOnSend.mockResolvedValue(undefined)
  })

  // ========== RENDERING TESTS ==========

  describe('Rendering', () => {
    it('renders notification modal with patron name in the title', () => {
      render(
        <SendNotificationModal isOpen={true}
          onClose={mockOnClose}
          patron={mockPatron} onSend={mockOnSend}
        />
      )

      expect(screen.getByRole('heading', { name: /send notification - jane rivera/i })).toBeInTheDocument()
    })

    it('displays template selection', () => {
      render(
        <SendNotificationModal isOpen={true}
          onClose={mockOnClose}
          patron={mockPatron} onSend={mockOnSend}
        />
      )

      expect(screen.getByLabelText(/template/i)).toBeInTheDocument()
    })

    it('shows available templates filtered to the selected notification type', () => {
      render(
        <SendNotificationModal isOpen={true}
          onClose={mockOnClose}
          patron={mockPatron} onSend={mockOnSend}
        />
      )

      // Defaults to the "email" type, which all three seed templates support
      expect(screen.getByRole('option', { name: 'Overdue Notice' })).toBeInTheDocument()
      expect(screen.getByRole('option', { name: 'Hold Ready' })).toBeInTheDocument()
      expect(screen.getByRole('option', { name: 'Account Update' })).toBeInTheDocument()
    })

    it('displays recipient info for the patron', () => {
      render(
        <SendNotificationModal isOpen={true}
          onClose={mockOnClose}
          patron={mockPatron} onSend={mockOnSend}
        />
      )

      expect(screen.getByText('Jane Rivera')).toBeInTheDocument()
      expect(screen.getByText('patron@example.com')).toBeInTheDocument()
    })

    it('does not render when isOpen is false', () => {
      render(
        <SendNotificationModal isOpen={false}
          onClose={mockOnClose}
          patron={mockPatron} onSend={mockOnSend}
        />
      )

      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })

    it('does not render when there is no patron', () => {
      render(
        <SendNotificationModal isOpen={true}
          onClose={mockOnClose}
          patron={null} onSend={mockOnSend}
        />
      )

      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })
  })

  // ========== TEMPLATE SELECTION TESTS ==========

  describe('Template Selection', () => {
    it('requires a non-empty message before sending is enabled', () => {
      render(
        <SendNotificationModal isOpen={true}
          onClose={mockOnClose}
          patron={mockPatron} onSend={mockOnSend}
        />
      )

      const sendButton = screen.getByRole('button', { name: /send notification/i })
      expect(sendButton).toBeDisabled()
    })

    it('enables send button once a template populates the message', async () => {
      const user = userEvent.setup()
      render(
        <SendNotificationModal isOpen={true}
          onClose={mockOnClose}
          patron={mockPatron} onSend={mockOnSend}
        />
      )

      const templateSelect = screen.getByLabelText(/template/i)
      await user.selectOptions(templateSelect, 'overdue')

      const sendButton = screen.getByRole('button', { name: /send notification/i })
      expect(sendButton).not.toBeDisabled()
    })

    it('populates subject and message from the selected template', async () => {
      const user = userEvent.setup()
      render(
        <SendNotificationModal isOpen={true}
          onClose={mockOnClose}
          patron={mockPatron} onSend={mockOnSend}
        />
      )

      const templateSelect = screen.getByLabelText(/template/i)
      await user.selectOptions(templateSelect, 'overdue')

      expect(screen.getByDisplayValue('Overdue Items')).toBeInTheDocument()
      expect(screen.getByRole('textbox', { name: /message/i })).toHaveValue(
        'You have overdue items. Please return them as soon as possible.'
      )
    })

    it('narrows the template list when switching to SMS (account_update is email-only)', async () => {
      const user = userEvent.setup()
      render(
        <SendNotificationModal isOpen={true}
          onClose={mockOnClose}
          patron={mockPatron} onSend={mockOnSend}
        />
      )

      await user.click(screen.getByRole('button', { name: /^sms$/i }))

      expect(screen.getByRole('option', { name: 'Overdue Notice' })).toBeInTheDocument()
      expect(screen.queryByRole('option', { name: 'Account Update' })).not.toBeInTheDocument()
    })
  })

  // ========== CUSTOMIZATION TESTS ==========

  describe('Notification Customization', () => {
    it('allows customizing the subject line', async () => {
      const user = userEvent.setup()
      render(
        <SendNotificationModal isOpen={true}
          onClose={mockOnClose}
          patron={mockPatron} onSend={mockOnSend}
        />
      )

      const templateSelect = screen.getByLabelText(/template/i)
      await user.selectOptions(templateSelect, 'overdue')

      const subjectInput = screen.getByLabelText(/subject/i)
      await user.clear(subjectInput)
      await user.type(subjectInput, 'Custom subject')

      expect(subjectInput).toHaveValue('Custom subject')
    })

    it('allows customizing the message body', async () => {
      const user = userEvent.setup()
      render(
        <SendNotificationModal isOpen={true}
          onClose={mockOnClose}
          patron={mockPatron} onSend={mockOnSend}
        />
      )

      const bodyTextarea = screen.getByRole('textbox', { name: /message/i })
      await user.type(bodyTextarea, 'A hand-written note')

      expect(bodyTextarea).toHaveValue('A hand-written note')
    })

    it('shows a live character count for the message body', async () => {
      const user = userEvent.setup()
      render(
        <SendNotificationModal isOpen={true}
          onClose={mockOnClose}
          patron={mockPatron} onSend={mockOnSend}
        />
      )

      const bodyTextarea = screen.getByRole('textbox', { name: /message/i })
      await user.type(bodyTextarea, 'Hi')

      expect(screen.getByText('2 / 500 characters')).toBeInTheDocument()
    })

    it('disables the SMS notification type when the patron has no phone on file', () => {
      const patronWithoutPhone = createMockPatron({ phone: null })
      render(
        <SendNotificationModal isOpen={true}
          onClose={mockOnClose}
          patron={patronWithoutPhone} onSend={mockOnSend}
        />
      )

      expect(screen.getByRole('button', { name: /^sms$/i })).toBeDisabled()
    })
  })

  // ========== SENDING TESTS ==========

  describe('Sending Notifications', () => {
    it('sends the notification with the selected template and trimmed message', async () => {
      const user = userEvent.setup()
      render(
        <SendNotificationModal isOpen={true}
          onClose={mockOnClose}
          patron={mockPatron} onSend={mockOnSend}
        />
      )

      const templateSelect = screen.getByLabelText(/template/i)
      await user.selectOptions(templateSelect, 'overdue')

      const sendButton = screen.getByRole('button', { name: /send notification/i })
      await user.click(sendButton)

      await waitFor(() => {
        expect(mockOnSend).toHaveBeenCalledWith(
          mockPatron,
          expect.objectContaining({
            type: 'email',
            template: 'overdue',
            subject: 'Overdue Items',
            message: 'You have overdue items. Please return them as soon as possible.',
          })
        )
      })
    })

    it('shows sending progress on the submit button', async () => {
      const user = userEvent.setup()
      mockOnSend.mockImplementation(() => new Promise(() => {})) // never resolves

      render(
        <SendNotificationModal isOpen={true}
          onClose={mockOnClose}
          patron={mockPatron} onSend={mockOnSend}
        />
      )

      const templateSelect = screen.getByLabelText(/template/i)
      await user.selectOptions(templateSelect, 'overdue')

      const sendButton = screen.getByRole('button', { name: /send notification/i })
      await user.click(sendButton)

      expect(await screen.findByText(/sending\.\.\./i)).toBeInTheDocument()
    })

    it('shows a success toast naming the patron', async () => {
      const user = userEvent.setup()
      render(
        <SendNotificationModal isOpen={true}
          onClose={mockOnClose}
          patron={mockPatron} onSend={mockOnSend}
        />
      )

      const templateSelect = screen.getByLabelText(/template/i)
      await user.selectOptions(templateSelect, 'overdue')

      const sendButton = screen.getByRole('button', { name: /send notification/i })
      await user.click(sendButton)

      await waitFor(() => {
        expect(toast.success).toHaveBeenCalledWith('Notification sent to Jane Rivera')
      })
    })

    it('closes the modal after a successful send', async () => {
      const user = userEvent.setup()
      render(
        <SendNotificationModal isOpen={true}
          onClose={mockOnClose}
          patron={mockPatron} onSend={mockOnSend}
        />
      )

      const templateSelect = screen.getByLabelText(/template/i)
      await user.selectOptions(templateSelect, 'overdue')

      const sendButton = screen.getByRole('button', { name: /send notification/i })
      await user.click(sendButton)

      await waitFor(() => {
        expect(mockOnClose).toHaveBeenCalled()
      })
    })
  })

  // ========== ERROR HANDLING TESTS ==========

  describe('Error Handling', () => {
    it('shows an error toast with the failure message when onSend rejects', async () => {
      const user = userEvent.setup()
      mockOnSend.mockRejectedValueOnce(new Error('Delivery service unavailable'))

      render(
        <SendNotificationModal isOpen={true}
          onClose={mockOnClose}
          patron={mockPatron} onSend={mockOnSend}
        />
      )

      const templateSelect = screen.getByLabelText(/template/i)
      await user.selectOptions(templateSelect, 'overdue')

      const sendButton = screen.getByRole('button', { name: /send notification/i })
      await user.click(sendButton)

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith('Delivery service unavailable')
      })
      // Failure keeps the modal open for the staff member to retry
      expect(mockOnClose).not.toHaveBeenCalled()
    })

    it('falls back to a generic error toast for non-Error rejections', async () => {
      const user = userEvent.setup()
      mockOnSend.mockRejectedValueOnce('network blip')

      render(
        <SendNotificationModal isOpen={true}
          onClose={mockOnClose}
          patron={mockPatron} onSend={mockOnSend}
        />
      )

      const templateSelect = screen.getByLabelText(/template/i)
      await user.selectOptions(templateSelect, 'overdue')

      await user.click(screen.getByRole('button', { name: /send notification/i }))

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith('Failed to send notification')
      })
    })
  })

  // ========== USER INTERACTION TESTS ==========

  describe('User Interactions', () => {
    it('closes the modal when the header close button is clicked', async () => {
      const user = userEvent.setup()
      render(
        <SendNotificationModal isOpen={true}
          onClose={mockOnClose}
          patron={mockPatron} onSend={mockOnSend}
        />
      )

      const closeButton = screen.getByRole('button', { name: /close modal/i })
      await user.click(closeButton)

      expect(mockOnClose).toHaveBeenCalled()
    })

    it('resets subject and message once closed and reopened', async () => {
      const user = userEvent.setup()
      const { rerender } = render(
        <SendNotificationModal isOpen={true}
          onClose={mockOnClose}
          patron={mockPatron} onSend={mockOnSend}
        />
      )

      await user.selectOptions(screen.getByLabelText(/template/i), 'overdue')
      expect(screen.getByLabelText(/subject/i)).toHaveValue('Overdue Items')

      rerender(
        <SendNotificationModal isOpen={false}
          onClose={mockOnClose}
          patron={mockPatron} onSend={mockOnSend}
        />
      )
      rerender(
        <SendNotificationModal isOpen={true}
          onClose={mockOnClose}
          patron={mockPatron} onSend={mockOnSend}
        />
      )

      expect(screen.getByLabelText(/subject/i)).toHaveValue('')
      expect(screen.getByRole('textbox', { name: /message/i })).toHaveValue('')
    })
  })

  // ========== ACCESSIBILITY TESTS ==========

  describe('Accessibility (WCAG AA)', () => {
    it('has proper modal structure', () => {
      render(
        <SendNotificationModal isOpen={true}
          onClose={mockOnClose}
          patron={mockPatron} onSend={mockOnSend}
        />
      )

      const dialog = screen.getByRole('dialog')
      expect(dialog).toHaveAttribute('aria-modal', 'true')
      expect(dialog).toHaveAttribute('aria-labelledby')
    })

    it('template select has an associated label', () => {
      render(
        <SendNotificationModal isOpen={true}
          onClose={mockOnClose}
          patron={mockPatron} onSend={mockOnSend}
        />
      )

      expect(screen.getByLabelText(/template/i).tagName).toBe('SELECT')
    })

    it('message textarea has an associated label', () => {
      render(
        <SendNotificationModal isOpen={true}
          onClose={mockOnClose}
          patron={mockPatron} onSend={mockOnSend}
        />
      )

      expect(screen.getByLabelText(/^message$/i).tagName).toBe('TEXTAREA')
    })

    it('the close button has a descriptive accessible name', () => {
      render(
        <SendNotificationModal isOpen={true}
          onClose={mockOnClose}
          patron={mockPatron} onSend={mockOnSend}
        />
      )

      expect(screen.getByRole('button', { name: /close modal/i })).toBeInTheDocument()
    })
  })

  // ========== INTEGRATION TESTS ==========

  describe('Integration', () => {
    it('completes the full notification sending workflow', async () => {
      const user = userEvent.setup()

      render(
        <SendNotificationModal isOpen={true}
          onClose={mockOnClose}
          patron={mockPatron} onSend={mockOnSend}
        />
      )

      // Select template (populates subject + message)
      const templateSelect = screen.getByLabelText(/template/i)
      await user.selectOptions(templateSelect, 'hold_ready')

      // Send
      const sendButton = screen.getByRole('button', { name: /send notification/i })
      await user.click(sendButton)

      // Verify success
      await waitFor(() => {
        expect(mockOnSend).toHaveBeenCalled()
        expect(toast.success).toHaveBeenCalled()
        expect(mockOnClose).toHaveBeenCalled()
      })
    })
  })
})
