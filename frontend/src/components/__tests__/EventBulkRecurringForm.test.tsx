/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * EventBulkRecurringForm: renders, requires preview before submit, calls the
 * dry-run endpoint, and on confirmed submit calls the real endpoint and
 * navigates back.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import EventBulkRecurringForm from '../EventBulkRecurringForm'

const mocks = vi.hoisted(() => ({
  bulkCreateRecurringEvents: vi.fn(),
  listBranches: vi.fn(),
  toast: { success: vi.fn(), error: vi.fn() },
}))

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    language: 'en-US',
    t: (key: string) => key,
    isRTL: false,
    setLanguage: vi.fn(),
  }),
}))

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ user: { role: 'staff' }, token: 'fake-token' }),
}))

vi.mock('@/api/branch-api', () => ({
  listBranches: mocks.listBranches,
}))

vi.mock('@/api/domains/services/events-api', () => ({
  bulkCreateRecurringEvents: mocks.bulkCreateRecurringEvents,
}))

vi.mock('react-hot-toast', () => ({
  default: mocks.toast,
}))

function renderForm(navigateOnSuccess?: (id: number, count: number) => void) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const onCancel = vi.fn()
  const utils = render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <EventBulkRecurringForm onCancel={onCancel} navigateOnSuccess={navigateOnSuccess} />
      </MemoryRouter>
    </QueryClientProvider>,
  )
  return { ...utils, onCancel }
}

async function fillMinimal(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText('bulkRecurring.title'), 'Storytime')
  // datetime-local inputs reject userEvent.type. Use fireEvent.change so the
  // controlled-input setState path runs.
  const start = screen.getByLabelText('bulkRecurring.firstOccurrenceStart') as HTMLInputElement
  fireEvent.change(start, { target: { value: '2026-06-01T10:00' } })
  await user.type(screen.getByLabelText('bulkRecurring.recurrenceRule'), 'FREQ=WEEKLY;COUNT=4')
}

beforeEach(() => {
  mocks.bulkCreateRecurringEvents.mockReset()
  mocks.listBranches.mockReset()
  mocks.listBranches.mockResolvedValue([])
  mocks.toast.success.mockReset()
  mocks.toast.error.mockReset()
})

describe('EventBulkRecurringForm', () => {
  it('renders the form fields', () => {
    renderForm()
    expect(screen.getByLabelText('bulkRecurring.title')).toBeInTheDocument()
    expect(screen.getByLabelText('bulkRecurring.recurrenceRule')).toBeInTheDocument()
    expect(screen.getByLabelText('bulkRecurring.firstOccurrenceStart')).toBeInTheDocument()
    expect(screen.getByLabelText('bulkRecurring.wheelchair_accessible')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /bulkRecurring\.previewButton/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /bulkRecurring\.submitButton/ })).toBeInTheDocument()
  })

  it('clicking preview calls the dry-run endpoint and displays count + dates', async () => {
    mocks.bulkCreateRecurringEvents.mockResolvedValueOnce({
      count: 4,
      first_start: '2026-06-01T10:00:00Z',
      last_start: '2026-06-22T10:00:00Z',
      instances: [
        { start_time: '2026-06-01T10:00:00Z', end_time: null },
        { start_time: '2026-06-08T10:00:00Z', end_time: null },
        { start_time: '2026-06-15T10:00:00Z', end_time: null },
        { start_time: '2026-06-22T10:00:00Z', end_time: null },
      ],
    })

    const user = userEvent.setup()
    renderForm()
    await fillMinimal(user)

    await user.click(screen.getByRole('button', { name: /bulkRecurring\.previewButton/ }))

    await waitFor(() => {
      expect(mocks.bulkCreateRecurringEvents).toHaveBeenCalledTimes(1)
    })
    const firstCall = mocks.bulkCreateRecurringEvents.mock.calls[0]!
    const payload = firstCall[1] as { dry_run: boolean; recurrence_rule: string }
    expect(payload.dry_run).toBe(true)
    expect(payload.recurrence_rule).toBe('FREQ=WEEKLY;COUNT=4')

    // Preview region with count is rendered.
    expect(await screen.findByRole('region', { name: 'bulkRecurring.previewRegion' })).toBeInTheDocument()
  })

  it('submit button is disabled until preview is run and count is confirmed', async () => {
    const user = userEvent.setup()
    renderForm()
    await fillMinimal(user)

    const submitBtn = screen.getByRole('button', { name: /bulkRecurring\.submitButton/ })
    expect(submitBtn).toBeDisabled()

    mocks.bulkCreateRecurringEvents.mockResolvedValueOnce({
      count: 2,
      first_start: '2026-06-01T10:00:00Z',
      last_start: '2026-06-08T10:00:00Z',
      instances: [
        { start_time: '2026-06-01T10:00:00Z', end_time: null },
        { start_time: '2026-06-08T10:00:00Z', end_time: null },
      ],
    })
    await user.click(screen.getByRole('button', { name: /bulkRecurring\.previewButton/ }))
    await screen.findByRole('region', { name: 'bulkRecurring.previewRegion' })

    // Still disabled until confirm box is ticked.
    expect(submitBtn).toBeDisabled()

    await user.click(screen.getByLabelText('bulkRecurring.confirmCountLabel'))
    expect(submitBtn).not.toBeDisabled()
  })

  it('submit calls the real endpoint and navigates on success', async () => {
    const user = userEvent.setup()
    const navigateSpy = vi.fn()
    renderForm(navigateSpy)
    await fillMinimal(user)

    // Preview first.
    mocks.bulkCreateRecurringEvents.mockResolvedValueOnce({
      count: 3,
      first_start: '2026-06-01T10:00:00Z',
      last_start: '2026-06-15T10:00:00Z',
      instances: [
        { start_time: '2026-06-01T10:00:00Z', end_time: null },
        { start_time: '2026-06-08T10:00:00Z', end_time: null },
        { start_time: '2026-06-15T10:00:00Z', end_time: null },
      ],
    })
    await user.click(screen.getByRole('button', { name: /bulkRecurring\.previewButton/ }))
    await screen.findByRole('region', { name: 'bulkRecurring.previewRegion' })
    await user.click(screen.getByLabelText('bulkRecurring.confirmCountLabel'))

    // Real submit.
    mocks.bulkCreateRecurringEvents.mockResolvedValueOnce({
      parent_id: 42,
      child_ids: [101, 102, 103],
      count: 3,
    })
    await user.click(screen.getByRole('button', { name: /bulkRecurring\.submitButton/ }))

    await waitFor(() => {
      expect(navigateSpy).toHaveBeenCalledWith(42, 3)
    })
    // Real call was made with dry_run=false.
    const realCall = mocks.bulkCreateRecurringEvents.mock.calls[1]!
    const realPayload = realCall[1] as { dry_run: boolean }
    expect(realPayload.dry_run).toBe(false)
    expect(mocks.toast.success).toHaveBeenCalled()
  })

  it('renders an error message when the endpoint fails', async () => {
    const user = userEvent.setup()
    renderForm()
    await fillMinimal(user)

    mocks.bulkCreateRecurringEvents.mockRejectedValueOnce(
      new Error('Recurrence expands to 60 occurrences within the 366-day horizon; the bulk-create cap is 52.'),
    )
    await user.click(screen.getByRole('button', { name: /bulkRecurring\.previewButton/ }))

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(/cap is 52/i)

    // Submit must remain disabled — no preview succeeded.
    expect(screen.getByRole('button', { name: /bulkRecurring\.submitButton/ })).toBeDisabled()
  })
})
