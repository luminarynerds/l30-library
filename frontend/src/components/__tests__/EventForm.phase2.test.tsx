/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Phase 2 EventForm sections: recurrence, presenters, audience age range,
 * photo release. Existing form behavior is covered by integration tests
 * elsewhere; these tests pin the new section rendering, presenter add/remove,
 * and the client-side min<=max age guard.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import userEvent from '@testing-library/user-event'
import EventForm from '../EventForm'

vi.mock('@/api/branch-api', () => ({
  listBranches: vi.fn().mockResolvedValue([]),
}))

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ user: null, token: null }),
}))

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    language: 'en-US',
    t: (key: string, paramsOrFallback?: Record<string, unknown> | string) => {
      if (typeof paramsOrFallback === 'string') return paramsOrFallback
      if (paramsOrFallback) return `${key}:${JSON.stringify(paramsOrFallback)}`
      return key
    },
  }),
}))

function renderForm(props: Partial<React.ComponentProps<typeof EventForm>> = {}) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <EventForm
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
        availableProgramPartners={[
          { id: 1, name: 'Friends of the Library' },
          { id: 2, name: 'Local Bookstore Co-op' },
        ]}
        {...props}
      />
    </QueryClientProvider>,
  )
}

describe('EventForm Phase 2 sections', () => {
  it('renders the recurrence section with the RFC 5545 helper text', () => {
    renderForm()
    expect(screen.getByText('Recurrence')).toBeInTheDocument()
    expect(
      screen.getByLabelText(/Recurrence rule \(RFC 5545\)/i),
    ).toBeInTheDocument()
    // Helper text is below the textarea and surfaces the example.
    expect(
      screen.getByText(/FREQ=WEEKLY;BYDAY=TU;UNTIL=20260815T120000Z/),
    ).toBeInTheDocument()
  })

  it('renders the presenters section and supports add/remove', async () => {
    const user = userEvent.setup()
    renderForm()
    expect(screen.getByText('Presenters')).toBeInTheDocument()
    // No rows initially.
    expect(screen.queryByLabelText(/^Name$/i)).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Add presenter/i }))
    expect(screen.getByLabelText(/^Name/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/^Bio$/i)).toBeInTheDocument()
    expect(
      screen.getByLabelText(/Partner organization/i),
    ).toBeInTheDocument()

    // Type into the name field.
    await user.type(screen.getByLabelText(/^Name/i), 'Jane Author')

    // Add another row, then remove the first.
    await user.click(screen.getByRole('button', { name: /Add presenter/i }))
    const nameInputs = screen.getAllByLabelText(/^Name/i)
    expect(nameInputs).toHaveLength(2)

    const removeButtons = screen.getAllByRole('button', {
      name: /Remove presenter/i,
    })
    expect(removeButtons).toHaveLength(2)
    await user.click(removeButtons[0]!)
    expect(screen.getAllByLabelText(/^Name/i)).toHaveLength(1)
  })

  it('renders the audience section and surfaces an age-range error when min>max', async () => {
    const user = userEvent.setup()
    renderForm()
    // Two elements contain 'Audience' (the existing audience-category label
    // and our new section summary). Scope to the section summary.
    const audienceSummaries = screen.getAllByText('Audience')
    expect(audienceSummaries.length).toBeGreaterThanOrEqual(1)
    const minInput = screen.getByLabelText(/Min age/i)
    const maxInput = screen.getByLabelText(/Max age/i)

    await user.type(minInput, '10')
    await user.type(maxInput, '5')

    // The mirror of the DB CHECK + Pydantic validator surfaces inline.
    expect(
      screen.getByText(/Min age must be less than or equal to max age/i),
    ).toBeInTheDocument()
  })

  it('renders the photo-release section with consent helper text', () => {
    renderForm()
    expect(screen.getByText('Photo Release')).toBeInTheDocument()
    expect(
      screen.getByLabelText(/Photos may be taken at this event/i),
    ).toBeInTheDocument()
    expect(
      screen.getByText(
        /patrons will be asked to consent to being photographed/i,
      ),
    ).toBeInTheDocument()
  })

  it('does not submit when age range is invalid', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined)
    const user = userEvent.setup()
    // Future-dated start_time so the form-level validator passes.
    const future = new Date(Date.now() + 1000 * 60 * 60 * 48)
      .toISOString()
      .slice(0, 16)
    renderForm({
      onSubmit,
      initialData: {
        title: 'Valid title here',
        start_time: future,
      },
    })

    await user.type(screen.getByLabelText(/Min age/i), '12')
    await user.type(screen.getByLabelText(/Max age/i), '5')

    await user.click(screen.getByRole('button', { name: /Update Event/i }))

    expect(onSubmit).not.toHaveBeenCalled()
  })
})
