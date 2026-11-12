/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import '@testing-library/jest-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ContentTranslationsResponse, ContentTranslationRecord } from '@/api/admin/content-translations-api'

const toastSuccess = vi.fn()
const toastError = vi.fn()
vi.mock('react-hot-toast', () => ({
  default: {
    success: (...args: unknown[]) => toastSuccess(...args),
    error: (...args: unknown[]) => toastError(...args),
  },
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
    <div>
      <h1>{title}</h1>
      {subtitle && <p>{subtitle}</p>}
      {loading ? <div>loading</div> : error ? <div role="alert">{error}</div> : children}
    </div>
  ),
}))

const getContentTranslations = vi.fn()
const updateContentTranslation = vi.fn()
vi.mock('@/api/admin/content-translations-api', () => ({
  getContentTranslations: (...args: unknown[]) => getContentTranslations(...args),
  updateContentTranslation: (...args: unknown[]) => updateContentTranslation(...args),
}))

import AdminContentTranslationsPage from './AdminContentTranslationsPage'

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
            { field: 'name', source: 'Community Room (source name)', value: null },
            { field: 'description', source: 'A room for meetings', value: 'Sala para reuniones' },
          ],
        },
      ],
    },
    {
      content_type: 'tech_help_option',
      label: 'Tech help options',
      records: [],
    },
  ],
}

const UPDATED_RECORD: ContentTranslationRecord = {
  id: 1,
  display_name: 'Community Room',
  fields: [
    { field: 'name', source: 'Community Room (source name)', value: 'Sala comunitaria' },
    { field: 'description', source: 'A room for meetings', value: 'Sala para reuniones' },
  ],
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <AdminContentTranslationsPage />
    </QueryClientProvider>,
  )
}

describe('AdminContentTranslationsPage', () => {
  beforeEach(() => {
    getContentTranslations.mockReset()
    updateContentTranslation.mockReset()
    toastSuccess.mockReset()
    toastError.mockReset()
    getContentTranslations.mockResolvedValue(MOCK_RESPONSE)
  })

  it('renders groups, records, and English/Spanish field pairs', async () => {
    renderPage()

    expect(await screen.findByText('Rooms')).toBeInTheDocument()
    expect(screen.getByText('Tech help options')).toBeInTheDocument()
    expect(screen.getByText('No records yet.')).toBeInTheDocument()

    const roomCard = screen.getByRole('group', { name: 'Community Room' })
    expect(within(roomCard).getByText('A room for meetings')).toBeInTheDocument()
    expect(within(roomCard).getByText('Community Room (source name)')).toBeInTheDocument()

    const spanishDescription = within(roomCard).getByLabelText('Description — Spanish') as HTMLTextAreaElement
    expect(spanishDescription.value).toBe('Sala para reuniones')

    const spanishName = within(roomCard).getByLabelText('Name — Spanish') as HTMLInputElement
    expect(spanishName.value).toBe('')

    expect(getContentTranslations).toHaveBeenCalledWith('es')
  })

  it('saves the edited values via PUT and shows a success toast', async () => {
    updateContentTranslation.mockResolvedValue(UPDATED_RECORD)
    renderPage()

    const roomCard = await screen.findByRole('group', { name: 'Community Room' })

    const spanishName = within(roomCard).getByLabelText('Name — Spanish') as HTMLInputElement
    fireEvent.change(spanishName, { target: { value: 'Sala comunitaria' } })

    fireEvent.click(within(roomCard).getByRole('button', { name: 'Save' }))

    await waitFor(() => {
      expect(updateContentTranslation).toHaveBeenCalledWith('room', 1, 'es', {
        name: 'Sala comunitaria',
        description: 'Sala para reuniones',
      })
    })
    await waitFor(() => expect(toastSuccess).toHaveBeenCalled())
  })

  it('shows an error toast when saving fails', async () => {
    updateContentTranslation.mockRejectedValue(new Error('boom'))
    renderPage()

    const roomCard = await screen.findByRole('group', { name: 'Community Room' })
    fireEvent.click(within(roomCard).getByRole('button', { name: 'Save' }))

    await waitFor(() => expect(toastError).toHaveBeenCalled())
  })
})
