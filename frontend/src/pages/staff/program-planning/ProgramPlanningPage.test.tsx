/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ user: { id: 1, role: 'admin' } }),
}))

vi.mock('@/i18n', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}))

// Mirror AdminShell's real behavior: it renders `title` as an <h1>.
vi.mock('@/components/shells/AdminShell', () => ({
  AdminShell: ({ title, children }: { title: string; children: React.ReactNode }) => (
    <div>
      <h1>{title}</h1>
      {children}
    </div>
  ),
}))

vi.mock('./components/QuickStats', () => ({ default: () => <div /> }))
vi.mock('./components/TemplateLibraryTab', () => ({ default: () => <div /> }))
vi.mock('./components/ProgramPlansTab', () => ({ default: () => <div /> }))
vi.mock('./components/MarketingRemindersTab', () => ({ default: () => <div /> }))
vi.mock('./components/SuccessMetricsTab', () => ({ default: () => <div /> }))

import ProgramPlanningPage from './ProgramPlanningPage'

describe('ProgramPlanningPage heading hierarchy', () => {
  it('renders a single h1 (the shell title); the in-page heading is an h2', () => {
    render(<ProgramPlanningPage />)
    const h1s = screen.getAllByRole('heading', { level: 1 })
    expect(h1s).toHaveLength(1)
    expect(h1s[0]).toHaveTextContent('Program Planning')
    expect(
      screen.getByRole('heading', { level: 2, name: 'Program Planning Tools' }),
    ).toBeInTheDocument()
  })
})
