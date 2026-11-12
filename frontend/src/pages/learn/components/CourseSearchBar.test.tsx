/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

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

import { CourseSearchBar } from './CourseSearchBar'

describe('CourseSearchBar', () => {
  it('sets an aria-label resolved from the translation key', () => {
    render(<CourseSearchBar searchTerm="" onSearchChange={vi.fn()} />)
    expect(
      screen.getByLabelText('learn.searchYourEnrolledCourses')
    ).toBeInTheDocument()
  })

  it('calls onSearchChange with the new value as the user types', async () => {
    const onSearchChange = vi.fn()
    const user = userEvent.setup()
    render(<CourseSearchBar searchTerm="" onSearchChange={onSearchChange} />)

    const input = screen.getByLabelText('learn.searchYourEnrolledCourses')
    await user.type(input, 'myst')

    expect(onSearchChange).toHaveBeenCalledTimes(4)
    expect(onSearchChange).toHaveBeenNthCalledWith(1, 'm')
    expect(onSearchChange).toHaveBeenNthCalledWith(4, 't')
  })

  it('is a controlled input — the displayed value follows the searchTerm prop', () => {
    const { rerender } = render(
      <CourseSearchBar searchTerm="mystery" onSearchChange={vi.fn()} />
    )
    const input = screen.getByLabelText<HTMLInputElement>(
      'learn.searchYourEnrolledCourses'
    )
    expect(input.value).toBe('mystery')

    rerender(<CourseSearchBar searchTerm="updated" onSearchChange={vi.fn()} />)
    expect(input.value).toBe('updated')
  })
})
