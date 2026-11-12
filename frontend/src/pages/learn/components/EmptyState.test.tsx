/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'

vi.mock('@/i18n/I18nContext', () => ({
  useTranslation: () => ({
    t: (key: string, opt?: Record<string, unknown> | string) =>
      typeof opt === 'string' ? opt : key,
    language: 'en',
    isRTL: false,
  }),
}))
vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string, opt?: Record<string, unknown> | string) =>
      typeof opt === 'string' ? opt : key,
    language: 'en',
    isRTL: false,
  }),
}))

import { EmptyState } from './EmptyState'

function renderWithRouter(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>)
}

describe('EmptyState', () => {
  it('renders "no courses match" plus a clear-search button when a search filters out all enrolled courses', async () => {
    const onClearSearch = vi.fn()
    const user = userEvent.setup()
    renderWithRouter(
      <EmptyState
        hasEnrolledCourses
        searchTerm="foo"
        isAuthenticated
        onClearSearch={onClearSearch}
      />
    )

    const message = screen.getByText(/No courses match/)
    expect(message).toBeInTheDocument()
    expect(message.textContent).toContain('“foo”')

    const clearButton = screen.getByRole('button', { name: 'Clear search' })
    await user.click(clearButton)
    expect(onClearSearch).toHaveBeenCalledTimes(1)
  })

  it('renders the "ready to start learning" CTA linking to /learn/catalog when authenticated with no enrolled courses', () => {
    renderWithRouter(
      <EmptyState
        hasEnrolledCourses={false}
        searchTerm=""
        isAuthenticated
        onClearSearch={vi.fn()}
      />
    )

    expect(screen.getByText('learn.readyToStartLearning')).toBeInTheDocument()
    const cta = screen.getByRole('link', { name: /Explore Courses/ })
    expect(cta.getAttribute('href')).toBe('/learn/catalog')
  })

  it('renders the two-button create-account / browse-courses CTA when unauthenticated with no enrolled courses', () => {
    renderWithRouter(
      <EmptyState
        hasEnrolledCourses={false}
        searchTerm=""
        isAuthenticated={false}
        onClearSearch={vi.fn()}
      />
    )

    const createAccount = screen.getByRole('link', { name: /Create Free Account/ })
    expect(createAccount.getAttribute('href')).toBe('/account')

    const browseCourses = screen.getByRole('link', { name: 'Browse Courses' })
    expect(browseCourses.getAttribute('href')).toBe('/learn/catalog')
  })
})
