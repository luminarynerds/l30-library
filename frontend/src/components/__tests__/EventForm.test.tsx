/// <reference types="@testing-library/jest-dom" />
/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Covers the EventForm expansion: tags, image_url+preview, is_featured (admin
 * gating), is_virtual + virtual_link, series_id/series_name pair validation,
 * branch select, and the collapsible accessibility section (auto-expand on
 * pre-set flags). These all regressed easily in the original "hidden-field"
 * version, so each gets a focused case.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useState } from 'react'
import { render, screen, waitFor, within, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import EventForm, { type EventFormData } from '../EventForm'

// ---- Hoisted mocks ------------------------------------------------------

const mocks = vi.hoisted(() => ({
  listBranches: vi.fn(),
  authUser: { value: { role: 'staff' } as { role: string } | null },
}))

// Mock t() to always return the key (ignoring fallback) so the tests can
// assert on i18n keys instead of English text. The real `t()` checks the
// loaded translation file first; we don't want to load it in tests.
vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    language: 'en-US',
    t: (key: string) => key,
    isRTL: false,
    setLanguage: vi.fn(),
  }),
}))

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ user: mocks.authUser.value, token: 'fake' }),
}))

vi.mock('@/api/branch-api', () => ({
  listBranches: mocks.listBranches,
}))

// ---- Helpers ------------------------------------------------------------

function renderForm(initial?: Partial<EventFormData>, opts?: { role?: string | null }) {
  mocks.authUser.value = opts && 'role' in opts
    ? (opts.role ? { role: opts.role } : null)
    : { role: 'staff' }
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const onSubmit = vi.fn().mockResolvedValue(undefined)
  const onCancel = vi.fn()
  const utils = render(
    <QueryClientProvider client={qc}>
      <EventForm
        onSubmit={onSubmit}
        onCancel={onCancel}
        initialData={initial}
        availableCategories={['Storytime']}
        availableAudiences={['Kids']}
      />
    </QueryClientProvider>
  )
  return { ...utils, onSubmit, onCancel }
}

beforeEach(() => {
  mocks.listBranches.mockReset()
  mocks.listBranches.mockResolvedValue([
    { id: 1, name: 'Main Branch' },
    { id: 2, name: 'Westside' },
  ])
})

// ---- Tests --------------------------------------------------------------

describe('EventForm — expanded fields', () => {
  it('renders all new fields by default (always-visible group)', async () => {
    renderForm()
    // Tags
    expect(screen.getByLabelText('eventForm.field.tags')).toBeInTheDocument()
    // Image URL
    expect(screen.getByLabelText('eventForm.field.imageUrl')).toBeInTheDocument()
    // is_featured (staff can see it)
    expect(screen.getByLabelText('eventForm.field.isFeatured')).toBeInTheDocument()
    // is_virtual
    expect(screen.getByLabelText('eventForm.field.isVirtual')).toBeInTheDocument()
    // Branch select renders (waiting for query)
    await waitFor(() => {
      expect(screen.getByLabelText('eventForm.field.branch')).toBeInTheDocument()
    })
    // Series collapsible summary present (collapsed by default)
    expect(screen.getByText('eventForm.section.series')).toBeInTheDocument()
    // Accessibility collapsible summary present
    expect(screen.getByText('eventForm.section.accessibility')).toBeInTheDocument()
  })

  it('hides is_featured for non-staff users (e.g. patrons)', () => {
    renderForm(undefined, { role: 'patron' })
    expect(screen.queryByLabelText('eventForm.field.isFeatured')).not.toBeInTheDocument()
  })

  it('hides is_featured when there is no user at all', () => {
    renderForm(undefined, { role: null })
    expect(screen.queryByLabelText('eventForm.field.isFeatured')).not.toBeInTheDocument()
  })

  it('shows virtual_link only when is_virtual is checked', async () => {
    const user = userEvent.setup()
    renderForm()
    expect(screen.queryByLabelText('eventForm.field.virtualLink')).not.toBeInTheDocument()
    await user.click(screen.getByLabelText('eventForm.field.isVirtual'))
    expect(screen.getByLabelText('eventForm.field.virtualLink')).toBeInTheDocument()
  })

  it('series_id without series_name shows pair error on submit', async () => {
    const user = userEvent.setup()
    const { onSubmit } = renderForm()
    // Open series section
    await user.click(screen.getByText('eventForm.section.series'))
    const idInput = await screen.findByLabelText('eventForm.field.seriesId')
    await user.type(idInput, 'summer-2026')
    // Fill required fields so submission reaches series validation
    await user.type(screen.getByLabelText(/eventForm\.field\.title/), 'Some Event')
    // Pick a future start_time
    const future = new Date(Date.now() + 24 * 3600 * 1000).toISOString().slice(0, 16)
    const startInput = screen.getByLabelText(/eventForm\.field\.startTime/) as HTMLInputElement
    await user.click(startInput)
    // Use fireEvent.change-like approach via userEvent.type after clearing
    startInput.value = ''
    await user.type(startInput, future)

    // Submit
    const submit = screen.getByRole('button', { name: /eventForm\.action\.create/ })
    await user.click(submit)

    expect(await screen.findByText('eventForm.validation.seriesPair')).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('series_id + series_name together submits without pair error', async () => {
    const user = userEvent.setup()
    const { onSubmit } = renderForm()
    await user.click(screen.getByText('eventForm.section.series'))
    await user.type(await screen.findByLabelText('eventForm.field.seriesId'), 'summer-2026')
    await user.type(screen.getByLabelText('eventForm.field.seriesName'), 'Summer Reading 2026')
    await user.type(screen.getByLabelText(/eventForm\.field\.title/), 'Series Kickoff')
    const future = new Date(Date.now() + 24 * 3600 * 1000).toISOString().slice(0, 16)
    const startInput = screen.getByLabelText(/eventForm\.field\.startTime/) as HTMLInputElement
    startInput.value = ''
    await user.type(startInput, future)
    await user.click(screen.getByRole('button', { name: /eventForm\.action\.create/ }))
    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1))
    expect(screen.queryByText('eventForm.validation.seriesPair')).not.toBeInTheDocument()
  })

  it('editing an event whose start_time is in the past still submits (future-only check is create-mode only)', async () => {
    const user = userEvent.setup()
    // Existing event already underway / past — staff wants to polish its time.
    const past = new Date(Date.now() - 24 * 3600 * 1000).toISOString().slice(0, 16)
    const { onSubmit } = renderForm({ title: 'Existing Event', start_time: past })
    await user.click(screen.getByRole('button', { name: /eventForm\.action\.update/ }))
    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1))
    expect(screen.queryByText('eventForm.validation.startTimeFuture')).not.toBeInTheDocument()
  })

  it('keeps an in-progress time edit when the parent re-renders with a fresh initialData object', async () => {
    // EventManagementPage builds initialData as an inline object literal, so the
    // form receives a brand-new reference on every parent render. A parent
    // re-render mid-edit (a query resolving, sibling state, etc.) must NOT wipe
    // the staff member's in-progress edits back to the original event values.
    const user = userEvent.setup()
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const onSubmit = vi.fn().mockResolvedValue(undefined)
    mocks.authUser.value = { role: 'staff' }
    function Wrapper() {
      const [, setN] = useState(0)
      return (
        <QueryClientProvider client={qc}>
          <button type="button" onClick={() => setN((n) => n + 1)}>force-rerender</button>
          <EventForm
            onSubmit={onSubmit}
            onCancel={() => {}}
            initialData={{ title: 'Medicare Info', start_time: '2026-06-12T13:00' }}
            availableCategories={['Storytime']}
            availableAudiences={['Kids']}
          />
        </QueryClientProvider>
      )
    }
    render(<Wrapper />)
    const startInput = screen.getByLabelText(/eventForm\.field\.startTime/) as HTMLInputElement
    fireEvent.change(startInput, { target: { value: '2026-06-12T10:00' } })
    // Parent re-renders, handing EventForm a new (equal-valued) initialData ref.
    await user.click(screen.getByText('force-rerender'))
    await user.click(screen.getByRole('button', { name: /eventForm\.action\.update/ }))
    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1))
    expect(onSubmit.mock.calls[0]?.[0]?.start_time).toBe('2026-06-12T10:00')
  })

  it('accessibility section is closed by default and open when editing event with a flag set', () => {
    // Closed by default
    const { unmount } = renderForm()
    // <details> renders content; check open attribute
    const summary = screen.getByText('eventForm.section.accessibility')
    const detailsEl = summary.closest('details') as HTMLDetailsElement
    expect(detailsEl.open).toBe(false)
    unmount()

    // Open when editing with a flag set
    renderForm({ sensory_friendly: true })
    const summary2 = screen.getByText('eventForm.section.accessibility')
    const detailsEl2 = summary2.closest('details') as HTMLDetailsElement
    expect(detailsEl2.open).toBe(true)
  })

  it('accessibility section auto-opens when editing event with accessibility_notes set', () => {
    renderForm({ accessibility_notes: 'Quiet space available.' })
    const summary = screen.getByText('eventForm.section.accessibility')
    const detailsEl = summary.closest('details') as HTMLDetailsElement
    expect(detailsEl.open).toBe(true)
  })

  it('renders all 6 accessibility boolean checkboxes', () => {
    renderForm({ sensory_friendly: true }) // auto-open
    expect(screen.getByLabelText('eventForm.field.wheelchairAccessible')).toBeInTheDocument()
    expect(screen.getByLabelText('eventForm.field.aslProvided')).toBeInTheDocument()
    expect(screen.getByLabelText('eventForm.field.captioningProvided')).toBeInTheDocument()
    expect(screen.getByLabelText('eventForm.field.assistiveListening')).toBeInTheDocument()
    expect(screen.getByLabelText('eventForm.field.sensoryFriendly')).toBeInTheDocument()
    expect(screen.getByLabelText('eventForm.field.largePrintAvailable')).toBeInTheDocument()
  })

  it('image_url shows a preview when the URL is valid http(s)', async () => {
    const user = userEvent.setup()
    renderForm()
    const url = screen.getByLabelText('eventForm.field.imageUrl')
    await user.type(url, 'https://example.com/x.jpg')
    const img = await screen.findByAltText('eventForm.field.imagePreviewAlt')
    expect(img).toHaveAttribute('src', 'https://example.com/x.jpg')
  })

  it('image_url shows no preview when input is not a valid URL', async () => {
    const user = userEvent.setup()
    renderForm()
    const url = screen.getByLabelText('eventForm.field.imageUrl')
    await user.type(url, 'not-a-url')
    expect(screen.queryByAltText('eventForm.field.imagePreviewAlt')).not.toBeInTheDocument()
  })

  it('tags input parses comma-separated values into chips', async () => {
    const user = userEvent.setup()
    renderForm()
    const tags = screen.getByLabelText('eventForm.field.tags')
    await user.type(tags, 'storytime, kids')
    const list = await screen.findByLabelText('eventForm.field.tagsList')
    expect(within(list).getByText('storytime')).toBeInTheDocument()
    expect(within(list).getByText('kids')).toBeInTheDocument()
  })

  it('branch select renders branches from listBranches()', async () => {
    renderForm()
    await waitFor(() => expect(mocks.listBranches).toHaveBeenCalled())
    const select = await screen.findByLabelText('eventForm.field.branch')
    // Two branches plus the empty option
    expect(within(select as HTMLElement).getByText('Main Branch')).toBeInTheDocument()
    expect(within(select as HTMLElement).getByText('Westside')).toBeInTheDocument()
  })
})
