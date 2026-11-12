/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/// <reference types="vitest/globals" />
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import { loadLanguage } from '@/i18n/translations'

// Mock the typed API client so the component never hits the network.
// Per memory feedback_l30_openapi_handwritten_drift, the new section uses
// its own client (parent-onboarding-session-handouts-api.ts) -- mock that.
const listResourceHandoutsMock = vi.fn()
const listSessionHandoutsMock = vi.fn()
const createSessionHandoutMock = vi.fn()
const deleteSessionHandoutMock = vi.fn()
const requestPrintPacketMock = vi.fn()

vi.mock(
  '@/api/domains/services/parent-onboarding-session-handouts-api',
  () => ({
    listResourceHandouts: (...a: unknown[]) => listResourceHandoutsMock(...a),
    listSessionHandouts: (...a: unknown[]) => listSessionHandoutsMock(...a),
    createSessionHandout: (...a: unknown[]) => createSessionHandoutMock(...a),
    deleteSessionHandout: (...a: unknown[]) => deleteSessionHandoutMock(...a),
    requestPrintPacket: (...a: unknown[]) => requestPrintPacketMock(...a),
  }),
)

// Real i18n in English. Per memory feedback_l30_vitest_i18n_no_preload the
// vitest setup does NOT preload locales, so the test pre-loads en.
vi.mock('@/i18n', async () => {
  const actual = await vi.importActual<typeof import('@/i18n')>('@/i18n')
  return {
    ...actual,
    useTranslation: () => ({
      t: (key: string, params?: Record<string, unknown>) =>
        actual.getTranslation(key, 'en', params),
      language: 'en',
      isRTL: false,
    }),
  }
})

import { SessionResourceHandouts } from '@/components/staff/parent-onboarding/SessionResourceHandouts'

beforeAll(async () => {
  await loadLanguage('en')
})

beforeEach(() => {
  listResourceHandoutsMock.mockReset()
  listSessionHandoutsMock.mockReset()
  createSessionHandoutMock.mockReset()
  deleteSessionHandoutMock.mockReset()
  requestPrintPacketMock.mockReset()

  // Default: empty catalog + empty session.
  listResourceHandoutsMock.mockResolvedValue({ handouts: [], total: 0 })
  listSessionHandoutsMock.mockResolvedValue({ handouts: [], total: 0 })
})

function renderSection(
  sessionId = 42,
  patronLanguage: string | null | undefined = undefined,
) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <SessionResourceHandouts
        sessionId={sessionId}
        patronLanguage={patronLanguage}
      />
    </QueryClientProvider>,
  )
}


// ---------------------------------------------------------------------------
// Empty state
// ---------------------------------------------------------------------------

describe('SessionResourceHandouts -- empty state', () => {
  it('renders the heading and the empty "Given today" copy', async () => {
    renderSection()
    expect(
      await screen.findByRole('heading', {
        name: /resources given to this family/i,
      }),
    ).toBeInTheDocument()
    expect(
      await screen.findByText(/no resources given yet/i),
    ).toBeInTheDocument()
  })

  it('hides the Suggested group when patronLanguage is not set', async () => {
    renderSection(42, null)
    // "Suggested for this family" heading must NOT render.
    expect(
      screen.queryByRole('heading', { name: /suggested for this family/i }),
    ).not.toBeInTheDocument()
  })

  it('hides the Suggested group when patronLanguage is English', async () => {
    renderSection(42, 'en')
    expect(
      screen.queryByRole('heading', { name: /suggested for this family/i }),
    ).not.toBeInTheDocument()
  })
})


// ---------------------------------------------------------------------------
// Suggested-for-family
// ---------------------------------------------------------------------------

describe('SessionResourceHandouts -- suggested for family', () => {
  it('shows the Suggested group when patronLanguage is non-English', async () => {
    // First call: suggested (limit=5, language=es). Second call: full catalog.
    listResourceHandoutsMock.mockImplementation((q) => {
      if (q?.language === 'es' && q?.limit === 5) {
        return Promise.resolve({
          handouts: [
            {
              id: 12, slug: 'wic-eligibility', title: 'WIC Eligibility - Espanol',
              category: 'wic', language: 'es', file_url: '/static/handouts/wic-eligibility-es.pdf',
              tags: [], is_active: true, page_count: 2,
            },
          ],
          total: 1,
        })
      }
      return Promise.resolve({ handouts: [], total: 0 })
    })

    renderSection(42, 'es')
    expect(
      await screen.findByRole('heading', { name: /suggested for this family/i }),
    ).toBeInTheDocument()
    expect(
      await screen.findByRole('button', {
        name: /WIC Eligibility - Espanol/i,
      }),
    ).toBeInTheDocument()
  })
})


// ---------------------------------------------------------------------------
// Add / remove
// ---------------------------------------------------------------------------

describe('SessionResourceHandouts -- catalog interactions', () => {
  it('adding a handout toggles aria-pressed on the catalog row', async () => {
    const user = userEvent.setup()

    let givenSnapshot: { handouts: unknown[]; total: number } = {
      handouts: [], total: 0,
    }
    listSessionHandoutsMock.mockImplementation(() =>
      Promise.resolve(givenSnapshot),
    )
    listResourceHandoutsMock.mockResolvedValue({
      handouts: [
        {
          id: 99, slug: 'snap-walkthrough', title: 'SNAP Walkthrough',
          category: 'snap', language: 'en',
          file_url: '/static/handouts/snap.pdf',
          tags: [], is_active: true, page_count: 3,
        },
      ],
      total: 1,
    })
    createSessionHandoutMock.mockImplementation(async () => {
      givenSnapshot = {
        handouts: [{
          id: 7, session_id: 42, resource_handout_id: 99,
          display_title: 'SNAP Walkthrough',
          given_at: '2026-05-25T12:00:00Z',
          given_in_language: 'en', delivery_method: 'printed',
        }],
        total: 1,
      }
      return givenSnapshot.handouts[0]
    })

    renderSection()
    // Catalog rows are <button aria-pressed=...> -- the role 'button'
    // filtered by aria-pressed avoids matching the Remove button
    // (which has aria-label "Remove: SNAP Walkthrough" but no aria-pressed).
    const row = await screen.findByRole('button', {
      name: /SNAP Walkthrough/i, pressed: false,
    })
    expect(row).toBeInTheDocument()

    await user.click(row)

    // The mutation invalidates session-handouts; the next paint should
    // see aria-pressed=true on the (same logical) row.
    await waitFor(() => {
      const updated = screen.getByRole('button', {
        name: /SNAP Walkthrough/i, pressed: true,
      })
      expect(updated).toBeInTheDocument()
    })
    expect(createSessionHandoutMock).toHaveBeenCalledTimes(1)
    expect(createSessionHandoutMock).toHaveBeenCalledWith(42, {
      resource_handout_id: 99,
      given_in_language: 'en',
      delivery_method: 'printed',
    })
  })

  it('remove from Given today calls delete and untoggles the row', async () => {
    const user = userEvent.setup()
    listResourceHandoutsMock.mockResolvedValue({
      handouts: [
        {
          id: 99, slug: 'snap-walkthrough', title: 'SNAP Walkthrough',
          category: 'snap', language: 'en',
          file_url: '/static/handouts/snap.pdf',
          tags: [], is_active: true, page_count: 3,
        },
      ],
      total: 1,
    })
    let givenSnapshot = {
      handouts: [{
        id: 7, session_id: 42, resource_handout_id: 99,
        display_title: 'SNAP Walkthrough',
        given_at: '2026-05-25T12:00:00Z',
        given_in_language: 'en', delivery_method: 'printed',
      }],
      total: 1,
    }
    listSessionHandoutsMock.mockImplementation(() =>
      Promise.resolve(givenSnapshot),
    )
    deleteSessionHandoutMock.mockImplementation(async () => {
      givenSnapshot = { handouts: [], total: 0 }
    })

    renderSection()
    // Catalog row is the <button aria-pressed=true> -- pressed-filter
    // disambiguates from the Remove button (no aria-pressed attribute).
    await screen.findByRole('button', {
      name: /SNAP Walkthrough/i, pressed: true,
    })
    // Click "Remove" inside the Given today list (accessible name
    // includes the resource title to avoid label collision).
    const removeBtn = await screen.findByRole('button', {
      name: /Remove: SNAP Walkthrough/i,
    })
    await user.click(removeBtn)

    await waitFor(() => {
      screen.getByRole('button', {
        name: /SNAP Walkthrough/i, pressed: false,
      })
    })
    expect(deleteSessionHandoutMock).toHaveBeenCalledWith(42, 7)
  })
})


// ---------------------------------------------------------------------------
// Print packet (501 -> graceful degrade)
// ---------------------------------------------------------------------------

describe('SessionResourceHandouts -- print packet', () => {
  it('disables the button when no printed items are in Given today', async () => {
    renderSection()
    // Spec UX: button is enabled when at least one "printed" item exists.
    // Empty given-today => disabled.
    const printBtn = await screen.findByRole('button', {
      name: /Print packet/i,
    })
    expect(printBtn).toBeDisabled()
  })

  it('renders sr-only context about the print-not-available state', async () => {
    renderSection()
    // The sr-only span is referenced via aria-describedby; getByText finds
    // it by visible text content even though it has the sr-only class.
    const help = await screen.findByText(
      /print packet generator is not available yet/i,
    )
    expect(help).toBeInTheDocument()
  })
})


// ---------------------------------------------------------------------------
// Delivery-method labelling (a11y -- per feedback_l30_form_label_collision)
// ---------------------------------------------------------------------------

describe('SessionResourceHandouts -- a11y', () => {
  it('gives each delivery-method dropdown a stable, unique label', async () => {
    listResourceHandoutsMock.mockResolvedValue({ handouts: [], total: 0 })
    listSessionHandoutsMock.mockResolvedValue({
      handouts: [
        {
          id: 1, session_id: 42, resource_handout_id: 11,
          display_title: 'WIC Eligibility',
          given_at: '2026-05-25T12:00:00Z',
          given_in_language: 'en', delivery_method: 'printed',
        },
        {
          id: 2, session_id: 42, resource_handout_id: 12,
          display_title: 'WIC Eligibility - Espanol',
          given_at: '2026-05-25T12:01:00Z',
          given_in_language: 'es', delivery_method: 'printed',
        },
      ],
      total: 2,
    })
    renderSection()

    // Each dropdown's accessible name includes the resource title so the
    // two rows do not collide.
    const select1 = await screen.findByRole('combobox', {
      name: /WIC Eligibility delivery method/i,
    })
    const select2 = await screen.findByRole('combobox', {
      name: /WIC Eligibility - Espanol delivery method/i,
    })
    expect(select1).not.toBe(select2)
  })
})
