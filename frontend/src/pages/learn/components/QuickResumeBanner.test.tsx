/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import type { LastLesson } from '@/types/learning'

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

import { QuickResumeBanner } from './QuickResumeBanner'

const lastLesson: LastLesson = {
  lessonId: 42,
  lessonTitle: 'Chapter 3: Cataloging Basics',
  courseId: 7,
  courseTitle: 'Intro to Library Science',
  viewedAt: '2026-06-01T00:00:00Z',
}

function renderWithRouter(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>)
}

describe('QuickResumeBanner', () => {
  it('renders the lesson title and course title', () => {
    renderWithRouter(<QuickResumeBanner lastLesson={lastLesson} />)
    expect(screen.getByText('Chapter 3: Cataloging Basics')).toBeInTheDocument()
    expect(screen.getByText(/Intro to Library Science/)).toBeInTheDocument()
  })

  it('links to /learn/course/<courseId>/lesson/<lessonId> built from the lastLesson fixture', () => {
    renderWithRouter(<QuickResumeBanner lastLesson={lastLesson} />)
    const link = screen.getByRole('link')
    expect(link.getAttribute('href')).toBe('/learn/course/7/lesson/42')
  })

  it('does not swap courseId/lessonId order when the values differ', () => {
    renderWithRouter(
      <QuickResumeBanner
        lastLesson={{ ...lastLesson, courseId: 100, lessonId: 5 }}
      />
    )
    const link = screen.getByRole('link')
    expect(link.getAttribute('href')).toBe('/learn/course/100/lesson/5')
  })
})
