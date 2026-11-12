/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

// i18n mock: return the key (or interpolate {{x}} naively) so we can assert.
vi.mock('../../i18n/I18nContext', () => ({
  useTranslation: () => ({
    t: (key: string, vars?: Record<string, unknown>) => {
      if (!vars) return key
      return Object.entries(vars).reduce<string>(
        (acc, [k, v]) => acc.replace(`{{${k}}}`, String(v)),
        key,
      )
    },
  }),
}))

import TeacherHomePage from '../TeacherHomePage'

const EXPECTED_CARDS: ReadonlyArray<{ labelKey: string; href: string }> = [
  { labelKey: 'navigation.teacherReadingDashboard', href: '/teacher/reading-dashboard' },
  { labelKey: 'navigation.teacherReadingLists', href: '/teacher/reading-lists' },
  { labelKey: 'navigation.professionalDevelopment', href: '/teacher/professional-development' },
  { labelKey: 'navigation.librarianConsultations', href: '/teacher/library-consultations' },
  { labelKey: 'navigation.familyReadingChallenges', href: '/teacher/family-challenges' },
  { labelKey: 'navigation.libraryVisitScheduling', href: '/teacher/library-visits' },
]

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/teacher']}>
      <TeacherHomePage />
    </MemoryRouter>,
  )
}

describe('TeacherHomePage', () => {
  it('renders the page heading', () => {
    renderPage()
    expect(
      screen.getByRole('heading', { level: 1, name: 'teacherHome.title' }),
    ).toBeInTheDocument()
  })

  it('renders a card for each of the six teacher surfaces', () => {
    renderPage()
    for (const { labelKey } of EXPECTED_CARDS) {
      expect(
        screen.getByRole('heading', { level: 2, name: labelKey }),
      ).toBeInTheDocument()
    }
  })

  it('each card links to the correct teacher route', () => {
    renderPage()
    for (const { labelKey, href } of EXPECTED_CARDS) {
      // Each card heading sits inside a single <Link>. Walk up from the
      // heading to its enclosing anchor and assert the href.
      const heading = screen.getByRole('heading', { level: 2, name: labelKey })
      const anchor = heading.closest('a')
      expect(anchor).not.toBeNull()
      expect(anchor).toHaveAttribute('href', href)
    }
  })
})
