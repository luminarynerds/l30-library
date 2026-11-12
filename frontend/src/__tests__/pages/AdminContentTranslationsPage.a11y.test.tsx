/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * A11y gate for the content-translations editor.
 */
/// <reference types="@testing-library/jest-dom/vitest" />
import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { configureAxe } from 'jest-axe'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ContentTranslationsResponse } from '@/api/admin/content-translations-api'

const axeWithConfig = configureAxe({
  rules: {
    'color-contrast': { enabled: false },
  },
})

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}))

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (_key: string, fallback?: string) => (typeof fallback === 'string' ? fallback : _key),
  }),
}))

vi.mock('@/components/shells/AdminShell', () => ({
  AdminShell: ({
    title,
    subtitle,
    loading,
    error,
    children,
  }: {
    title: string
    subtitle?: string
    loading?: boolean
    error?: string | null
    children: React.ReactNode
  }) => (
    <main>
      <h1>{title}</h1>
      {subtitle && <p>{subtitle}</p>}
      {loading ? <div>loading</div> : error ? <div role="alert">{error}</div> : children}
    </main>
  ),
}))

const MOCK_RESPONSE: ContentTranslationsResponse = {
  language: 'es',
  groups: [
    {
      content_type: 'room',
      label: 'Rooms',
      records: [
        {
          id: 1,
          display_name: 'Community Room',
          fields: [
            { field: 'name', source: 'Community Room', value: 'Sala comunitaria' },
            { field: 'description', source: 'Large meeting room', value: null },
          ],
        },
      ],
    },
    {
      content_type: 'discover_shelf',
      label: 'Discover Shelves',
      records: [
        {
          id: 3,
          display_name: 'Cozy mysteries',
          fields: [{ field: 'title', source: 'Cozy mysteries', value: 'Misterios acogedores' }],
        },
      ],
    },
  ],
}

vi.mock('@/api/admin/content-translations-api', () => ({
  getContentTranslations: vi.fn(async () => MOCK_RESPONSE),
  updateContentTranslation: vi.fn(),
}))

import AdminContentTranslationsPage from '@/pages/staff/AdminContentTranslationsPage'

describe('AdminContentTranslationsPage a11y', () => {
  it('renders with no axe violations', async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const { container } = render(
      <QueryClientProvider client={qc}>
        <AdminContentTranslationsPage />
      </QueryClientProvider>,
    )
    await screen.findAllByText('Community Room')
    expect(await axeWithConfig(container)).toHaveNoViolations()
  })
})
