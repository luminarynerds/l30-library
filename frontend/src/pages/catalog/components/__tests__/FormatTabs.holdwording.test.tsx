/// <reference types="@testing-library/jest-dom" />
/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router-dom'

// FormatTabs imports standalone `t` from '@/i18n'; Button uses useTranslation hook.
// Factories must be self-contained (vi.mock is hoisted; no outer-scope refs allowed).
vi.mock('@/i18n', () => ({
  t: (key: string) => key,
  useTranslation: () => ({ t: (key: string) => key }),
}))
vi.mock('@/i18n/I18nContext', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}))

import { FormatTabs } from '../FormatTabs'
import type { CatalogItem } from '@/api/api'
import type { FormatVariant } from '../../hooks/useRelatedFormats'
import type { HoldPositionInfo } from '../../hooks/useHoldPosition'

const noHold: HoldPositionInfo = {
  hasHold: false, position: 0, totalAhead: 0, estimatedReadyDate: null, holdStatus: null,
}

function makeFormat(status: string): FormatVariant {
  return {
    id: 1,
    label: 'Hardcover',
    item_type: 'book',
    status,
    isCurrent: true,
    location: 'Main St',
    is_large_print: false,
    page_count: 300,
    runtime_minutes: null,
  } as unknown as FormatVariant
}

/** Surfaces the active route + login return target so tests can assert navigation. */
function LocationProbe() {
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from
  return (
    <>
      <div data-testid="location">{location.pathname}</div>
      <div data-testid="location-state-from">{from ?? ''}</div>
    </>
  )
}

function renderTabs(status: string, isLoggedIn = true, onPlaceHold: () => void = () => {}) {
  const item = { id: 1, title: 'Test Title', status } as unknown as CatalogItem
  render(
    <MemoryRouter>
      <FormatTabs
        currentItem={item}
        formats={[makeFormat(status)]}
        holdPosition={noHold}
        onPlaceHold={onPlaceHold}
        onOpenWayfinding={() => {}}
        reduceMotion
        isLoggedIn={isLoggedIn}
      />
      <LocationProbe />
    </MemoryRouter>,
  )
}

describe('FormatTabs hold wording', () => {
  it('shows an on-shelf badge and helper line for an available item', () => {
    renderTabs('available')
    expect(screen.getByText('On the shelf now')).toBeInTheDocument()
    expect(screen.getByText(/on the shelf .* set it aside for you/i)).toBeInTheDocument()
  })

  it('uses a "Join waitlist" button for a checked-out item', () => {
    // Physical hold wording was split from one generic "Place a hold" label
    // into status-specific copy (228814ec3): "Request for pickup" when on the
    // shelf, "Join waitlist" when checked out.
    renderTabs('checked_out')
    expect(screen.getByRole('button', { name: /join waitlist/i })).toBeInTheDocument()
    expect(screen.getByText(/email you when it's back/i)).toBeInTheDocument()
  })

  it('shows a reserved badge and helper line for an on-hold item', () => {
    renderTabs('on_hold')
    expect(screen.getByText('On shelf, reserved')).toBeInTheDocument()
    expect(screen.getByText(/next in line/i)).toBeInTheDocument()
  })
})

describe('FormatTabs logged-out sign-in-and-return', () => {
  it('labels the primary CTA as sign-in and routes to login with a hold return target', () => {
    const onPlaceHold = vi.fn()
    renderTabs('checked_out', false, onPlaceHold)
    const btn = screen.getByRole('button', { name: 'catalog.item.signInToPlaceHold' })
    fireEvent.click(btn)
    expect(onPlaceHold).not.toHaveBeenCalled()
    expect(screen.getByTestId('location').textContent).toBe('/login')
    expect(screen.getByTestId('location-state-from').textContent).toBe('/catalog/1?action=hold')
  })

  it('shows a "Browse eBooks to borrow" link for catalog ebooks instead of a sign-in-to-borrow CTA (in-app catalog ebook borrowing was removed as broken, #1721)', () => {
    // f5b056e99 removed onBorrowEbook/the sign-in-to-borrow flow entirely:
    // catalog ebooks are a separate, non-lendable dataset from indie ebooks,
    // so the old CTA always 500d. Catalog ebooks now point patrons at /indie,
    // regardless of login state, and there is no sign-in-and-return flow left
    // to test for this format.
    const item = { id: 1, title: 'Test Title', status: 'available' } as unknown as CatalogItem
    render(
      <MemoryRouter>
        <FormatTabs
          currentItem={item}
          formats={[{ ...makeFormat('available'), item_type: 'ebook' } as FormatVariant]}
          holdPosition={noHold}
          onPlaceHold={() => {}}
          onOpenWayfinding={() => {}}
          reduceMotion
          isLoggedIn={false}
        />
        <LocationProbe />
      </MemoryRouter>,
    )
    const link = screen.getByRole('link', { name: 'catalog.item.browseEbooksToBorrow' })
    expect(link).toHaveAttribute('href', '/indie')
    fireEvent.click(link)
    // A real <Link> navigation straight to /indie, not a sign-in-and-return
    // redirect through /login: no sign-in-to-borrow button exists any more
    // for this format.
    expect(screen.queryByRole('button', { name: /sign in/i })).not.toBeInTheDocument()
    expect(screen.getByTestId('location').textContent).toBe('/indie')
  })

  it('calls onPlaceHold directly when logged in', () => {
    const onPlaceHold = vi.fn()
    renderTabs('checked_out', true, onPlaceHold)
    fireEvent.click(screen.getByRole('button', { name: /join waitlist/i }))
    expect(onPlaceHold).toHaveBeenCalled()
    expect(screen.getByTestId('location').textContent).toBe('/')
  })
})
