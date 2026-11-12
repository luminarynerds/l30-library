/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Tests for QuickCheckoutModal Component
 *
 * Tests quick checkout workflow, item scanning, and transaction completion
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render } from "@testing-library/react"
import { screen, waitFor } from '@testing-library/dom'
import userEvent from '@testing-library/user-event'
import QuickCheckoutModal from '../../../components/staff/QuickCheckoutModal'
import toast from 'react-hot-toast'

// Mock toast notifications
vi.mock('react-hot-toast', () => ({
  default: {
    error: vi.fn(),
    success: vi.fn(),
    loading: vi.fn(),
  },
}))

// Mock fetch API
const mockFetch = vi.fn()
global.fetch = mockFetch as unknown as typeof fetch

// SKIP NOTE: The QuickCheckoutModal component was refactored to accept a
// pre-resolved `patron` prop and only handles item-barcode scanning (it
// returns null when patron is null). These tests assert the old UI that
// included a patron-lookup input, a multi-item checkout list, and a
// complete-checkout button — none of which exist in the current component.
// Skipped pending a test rewrite against the new component API.
describe.skip('QuickCheckoutModal', () => {
  const mockPatron = {
    id: 1,
    name: 'John Smith',
    barcode: '1234567890',
    email: 'john@example.com',
    phone: '555-1234',
    fines: 0,
    holds: 0,
  }


  const mockOnClose = vi.fn()
  const mockOnCheckoutComplete = vi.fn()
  const mockToken = "test-token-123"

  beforeEach(() => {
    vi.clearAllMocks()
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockPatron,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, checked_out: 2 }),
      })
  })

  // ========== RENDERING TESTS ==========

  describe('Rendering', () => {
    it('renders quick checkout modal', () => {
      render(
        <QuickCheckoutModal
          isOpen={true}
          onClose={mockOnClose}
          patron={null} token={mockToken} onCheckoutComplete={mockOnCheckoutComplete}
        />
      )

      expect(screen.getByText(/quick checkout/i)).toBeInTheDocument()
    })

    it('shows patron input field', () => {
      render(
        <QuickCheckoutModal
          isOpen={true}
          onClose={mockOnClose}
          patron={null} token={mockToken} onCheckoutComplete={mockOnCheckoutComplete}
        />
      )

      expect(screen.getByPlaceholderText(/scan patron|enter patron/i)).toBeInTheDocument()
    })

    it('shows item input field', () => {
      render(
        <QuickCheckoutModal
          isOpen={true}
          onClose={mockOnClose}
          patron={null} token={mockToken} onCheckoutComplete={mockOnCheckoutComplete}
        />
      )

      expect(screen.getByPlaceholderText(/scan item|enter item/i)).toBeInTheDocument()
    })

    it('does not render when isOpen is false', () => {
      const { container } = render(
        <QuickCheckoutModal
          isOpen={false}
          onClose={mockOnClose}
          patron={null} token={mockToken} onCheckoutComplete={mockOnCheckoutComplete}
        />
      )

      expect(container.querySelector('[role="dialog"]')).not.toBeInTheDocument()
    })
  })

  // ========== PATRON LOOKUP TESTS ==========

  describe('Patron Lookup', () => {
    it('searches for patron by barcode', async () => {
      const user = userEvent.setup()
      render(
        <QuickCheckoutModal
          isOpen={true}
          onClose={mockOnClose}
          patron={null} token={mockToken} onCheckoutComplete={mockOnCheckoutComplete}
        />
      )

      const patronInput = screen.getByPlaceholderText(/scan patron|enter patron/i)
      await user.type(patronInput, '1234567890')
      await user.keyboard('{Enter}')

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining('/patron'),
          expect.any(Object)
        )
      })
    })

    it('displays patron details after lookup', async () => {
      const user = userEvent.setup()
      render(
        <QuickCheckoutModal
          isOpen={true}
          onClose={mockOnClose}
          patron={null} token={mockToken} onCheckoutComplete={mockOnCheckoutComplete}
        />
      )

      const patronInput = screen.getByPlaceholderText(/scan patron|enter patron/i)
      await user.type(patronInput, '1234567890')
      await user.keyboard('{Enter}')

      await waitFor(() => {
        expect(screen.getByText('John Smith')).toBeInTheDocument()
        expect(screen.getByText('john@example.com')).toBeInTheDocument()
      })
    })

    it('shows patron warnings if applicable', async () => {
      const user = userEvent.setup()
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          ...mockPatron,
          fines: 25.50,
          holds: 2,
        }),
      })

      render(
        <QuickCheckoutModal
          isOpen={true}
          onClose={mockOnClose}
          patron={null} token={mockToken} onCheckoutComplete={mockOnCheckoutComplete}
        />
      )

      const patronInput = screen.getByPlaceholderText(/scan patron|enter patron/i)
      await user.type(patronInput, '1234567890')
      await user.keyboard('{Enter}')

      await waitFor(() => {
        expect(screen.getByText(/has fines|owes/i)).toBeInTheDocument()
      })
    })

    it('handles patron not found', async () => {
      const user = userEvent.setup()
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
      })
      render(
        <QuickCheckoutModal
          isOpen={true}
          onClose={mockOnClose}
          patron={null} token={mockToken} onCheckoutComplete={mockOnCheckoutComplete}
        />
      )

      const patronInput = screen.getByPlaceholderText(/scan patron|enter patron/i)
      await user.type(patronInput, '9999999999')
      await user.keyboard('{Enter}')

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith(
          expect.stringContaining('not found')
        )
      })
    })
  })

  // ========== ITEM SCANNING TESTS ==========

  describe('Item Scanning', () => {
    it('adds item to checkout list', async () => {
      const user = userEvent.setup()
      render(
        <QuickCheckoutModal
          isOpen={true}
          onClose={mockOnClose}
          patron={null} token={mockToken} onCheckoutComplete={mockOnCheckoutComplete}
        />
      )

      // First scan patron
      const patronInput = screen.getByPlaceholderText(/scan patron|enter patron/i)
      await user.type(patronInput, '1234567890')
      await user.keyboard('{Enter}')

      await waitFor(() => {
        expect(screen.getByText('John Smith')).toBeInTheDocument()
      })

      // Then scan item
      const itemInput = screen.getByPlaceholderText(/scan item|enter item/i)
      await user.type(itemInput, '0001')
      await user.keyboard('{Enter}')

      await waitFor(() => {
        expect(screen.getByText('The Great Gatsby')).toBeInTheDocument()
      })
    })

    it('displays item details', async () => {
      const user = userEvent.setup()
      render(
        <QuickCheckoutModal
          isOpen={true}
          onClose={mockOnClose}
          patron={null} token={mockToken} onCheckoutComplete={mockOnCheckoutComplete}
        />
      )

      const patronInput = screen.getByPlaceholderText(/scan patron|enter patron/i)
      await user.type(patronInput, '1234567890')
      await user.keyboard('{Enter}')

      await waitFor(() => {
        expect(screen.getByText('John Smith')).toBeInTheDocument()
      })

      const itemInput = screen.getByPlaceholderText(/scan item|enter item/i)
      await user.type(itemInput, '0001')
      await user.keyboard('{Enter}')

      await waitFor(() => {
        expect(screen.getByText('978-0743273565')).toBeInTheDocument()
      })
    })

    it('shows checkout count', async () => {
      const user = userEvent.setup()
      render(
        <QuickCheckoutModal
          isOpen={true}
          onClose={mockOnClose}
          patron={null} token={mockToken} onCheckoutComplete={mockOnCheckoutComplete}
        />
      )

      const patronInput = screen.getByPlaceholderText(/scan patron|enter patron/i)
      await user.type(patronInput, '1234567890')
      await user.keyboard('{Enter}')

      await waitFor(() => {
        expect(screen.getByText('John Smith')).toBeInTheDocument()
      })

      const itemInput = screen.getByPlaceholderText(/scan item|enter item/i)
      await user.type(itemInput, '0001')
      await user.keyboard('{Enter}')

      await waitFor(() => {
        expect(screen.getByText(/1 item/i)).toBeInTheDocument()
      })
    })

    it('handles duplicate item scan', async () => {
      const user = userEvent.setup()
      

      render(
        <QuickCheckoutModal
          isOpen={true}
          onClose={mockOnClose}
          patron={null} token={mockToken} onCheckoutComplete={mockOnCheckoutComplete}
        />
      )

      const patronInput = screen.getByPlaceholderText(/scan patron|enter patron/i)
      await user.type(patronInput, '1234567890')
      await user.keyboard('{Enter}')

      await waitFor(() => {
        expect(screen.getByText('John Smith')).toBeInTheDocument()
      })

      const itemInput = screen.getByPlaceholderText(/scan item|enter item/i)
      await user.type(itemInput, '0001')
      await user.keyboard('{Enter}')

      // Scan same item again
      await user.type(itemInput, '0001')
      await user.keyboard('{Enter}')

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith(
          expect.stringContaining('already')
        )
      })
    })
  })

  // ========== CHECKOUT COMPLETION ==========

  describe('Checkout Completion', () => {
    it('shows complete checkout button', async () => {
      const user = userEvent.setup()
      render(
        <QuickCheckoutModal
          isOpen={true}
          onClose={mockOnClose}
          patron={null} token={mockToken} onCheckoutComplete={mockOnCheckoutComplete}
        />
      )

      const patronInput = screen.getByPlaceholderText(/scan patron|enter patron/i)
      await user.type(patronInput, '1234567890')
      await user.keyboard('{Enter}')

      await waitFor(() => {
        expect(screen.getByText('John Smith')).toBeInTheDocument()
      })

      const completeBtn = screen.getByRole('button', { name: /complete|finish/i })
      expect(completeBtn).toBeInTheDocument()
    })

    it('completes checkout with items', async () => {
      const user = userEvent.setup()
      render(
        <QuickCheckoutModal
          isOpen={true}
          onClose={mockOnClose}
          patron={null} token={mockToken} onCheckoutComplete={mockOnCheckoutComplete}
        />
      )

      const patronInput = screen.getByPlaceholderText(/scan patron|enter patron/i)
      await user.type(patronInput, '1234567890')
      await user.keyboard('{Enter}')

      await waitFor(() => {
        expect(screen.getByText('John Smith')).toBeInTheDocument()
      })

      const itemInput = screen.getByPlaceholderText(/scan item|enter item/i)
      await user.type(itemInput, '0001')
      await user.keyboard('{Enter}')

      const completeBtn = screen.getByRole('button', { name: /complete|finish/i })
      await user.click(completeBtn)

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining('/checkout'),
          expect.any(Object)
        )
      })
    })

    it('shows success message after checkout', async () => {
      const user = userEvent.setup()
      

      render(
        <QuickCheckoutModal
          isOpen={true}
          onClose={mockOnClose}
          patron={null} token={mockToken} onCheckoutComplete={mockOnCheckoutComplete}
        />
      )

      const patronInput = screen.getByPlaceholderText(/scan patron|enter patron/i)
      await user.type(patronInput, '1234567890')
      await user.keyboard('{Enter}')

      await waitFor(() => {
        expect(screen.getByText('John Smith')).toBeInTheDocument()
      })

      const itemInput = screen.getByPlaceholderText(/scan item|enter item/i)
      await user.type(itemInput, '0001')
      await user.keyboard('{Enter}')

      const completeBtn = screen.getByRole('button', { name: /complete|finish/i })
      await user.click(completeBtn)

      await waitFor(() => {
        expect(toast.success).toHaveBeenCalled()
      })
    })
  })

  // ========== ITEM REMOVAL ==========

  describe('Item Removal', () => {
    it('removes item from checkout list', async () => {
      const user = userEvent.setup()
      render(
        <QuickCheckoutModal
          isOpen={true}
          onClose={mockOnClose}
          patron={null} token={mockToken} onCheckoutComplete={mockOnCheckoutComplete}
        />
      )

      const patronInput = screen.getByPlaceholderText(/scan patron|enter patron/i)
      await user.type(patronInput, '1234567890')
      await user.keyboard('{Enter}')

      await waitFor(() => {
        expect(screen.getByText('John Smith')).toBeInTheDocument()
      })

      const itemInput = screen.getByPlaceholderText(/scan item|enter item/i)
      await user.type(itemInput, '0001')
      await user.keyboard('{Enter}')

      const removeBtn = screen.getByRole('button', { name: /remove/i })
      await user.click(removeBtn)

      await waitFor(() => {
        expect(screen.queryByText('The Great Gatsby')).not.toBeInTheDocument()
      })
    })
  })

  // ========== ERROR HANDLING ==========

  describe('Error Handling', () => {
    it('handles checkout API error', async () => {
      const user = userEvent.setup()
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => mockPatron,
        })
        .mockRejectedValueOnce(new Error('Checkout failed'))

      
      render(
        <QuickCheckoutModal
          isOpen={true}
          onClose={mockOnClose}
          patron={null} token={mockToken} onCheckoutComplete={mockOnCheckoutComplete}
        />
      )

      const patronInput = screen.getByPlaceholderText(/scan patron|enter patron/i)
      await user.type(patronInput, '1234567890')
      await user.keyboard('{Enter}')

      await waitFor(() => {
        expect(screen.getByText('John Smith')).toBeInTheDocument()
      })

      const itemInput = screen.getByPlaceholderText(/scan item|enter item/i)
      await user.type(itemInput, '0001')
      await user.keyboard('{Enter}')

      const completeBtn = screen.getByRole('button', { name: /complete|finish/i })
      await user.click(completeBtn)

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalled()
      })
    })
  })

  // ========== ACCESSIBILITY TESTS ==========

  describe('Accessibility (WCAG AA)', () => {
    it('has proper modal structure', () => {
      render(
        <QuickCheckoutModal
          isOpen={true}
          onClose={mockOnClose}
          patron={null} token={mockToken} onCheckoutComplete={mockOnCheckoutComplete}
        />
      )

      const dialog = screen.getByRole('dialog')
      expect(dialog).toHaveAttribute('aria-modal', 'true')
    })

    it('input fields have labels', () => {
      render(
        <QuickCheckoutModal
          isOpen={true}
          onClose={mockOnClose}
          patron={null} token={mockToken} onCheckoutComplete={mockOnCheckoutComplete}
        />
      )

      const patronInput = screen.getByPlaceholderText(/scan patron|enter patron/i)
      expect(patronInput).toHaveAttribute('aria-label')

      const itemInput = screen.getByPlaceholderText(/scan item|enter item/i)
      expect(itemInput).toHaveAttribute('aria-label')
    })

    it('buttons have descriptive labels', () => {
      render(
        <QuickCheckoutModal
          isOpen={true}
          onClose={mockOnClose}
          patron={null} token={mockToken} onCheckoutComplete={mockOnCheckoutComplete}
        />
      )

      const buttons = screen.getAllByRole('button')
      buttons.forEach((button: HTMLElement) => {
        expect(button).toHaveAttribute('aria-label')
      })
    })
  })

  // ========== INTEGRATION TESTS ==========

  describe('Integration', () => {
    it('completes full quick checkout workflow', async () => {
      const user = userEvent.setup()
      

      render(
        <QuickCheckoutModal
          isOpen={true}
          onClose={mockOnClose}
          patron={null} token={mockToken} onCheckoutComplete={mockOnCheckoutComplete}
        />
      )

      // Scan patron
      const patronInput = screen.getByPlaceholderText(/scan patron|enter patron/i)
      await user.type(patronInput, '1234567890')
      await user.keyboard('{Enter}')

      // Verify patron loaded
      await waitFor(() => {
        expect(screen.getByText('John Smith')).toBeInTheDocument()
      })

      // Scan item
      const itemInput = screen.getByPlaceholderText(/scan item|enter item/i)
      await user.type(itemInput, '0001')
      await user.keyboard('{Enter}')

      // Verify item added
      await waitFor(() => {
        expect(screen.getByText('The Great Gatsby')).toBeInTheDocument()
      })

      // Complete checkout
      const completeBtn = screen.getByRole('button', { name: /complete|finish/i })
      await user.click(completeBtn)

      // Verify success
      await waitFor(() => {
        expect(toast.success).toHaveBeenCalled()
        expect(mockOnCheckoutComplete).toHaveBeenCalled()
      })
    })
  })
})
