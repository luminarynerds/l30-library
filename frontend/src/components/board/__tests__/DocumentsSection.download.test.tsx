import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

vi.mock('../../../api/api', () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}))
vi.mock('react-hot-toast', () => ({ default: { error: vi.fn(), success: vi.fn() } }))
vi.mock('@/i18n', () => ({
  useTranslation: () => ({ t: (key: string, fallback?: unknown) => (typeof fallback === 'string' ? fallback : key) }),
}))

import api from '../../../api/api'
import toast from 'react-hot-toast'
import { UnifiedAccessibilityProvider } from '@/features/accessibility/context/UnifiedAccessibilityContext'
import DocumentsSection from '../DocumentsSection'

const renderSection = () =>
  render(
    <UnifiedAccessibilityProvider>
      <DocumentsSection token="t" userRole="patron" />
    </UnifiedAccessibilityProvider>,
  )

const doc = (file_path: string) => ({
  id: 1,
  title: 'Budget Packet',
  description: '',
  document_type: 'financial_report',
  filename: 'budget.pdf',
  file_path,
  file_size: 1000,
  mime_type: 'application/pdf',
  status: 'published',
  created_at: '2026-11-01T00:00:00Z',
  updated_at: '2026-11-01T00:00:00Z',
})

describe('DocumentsSection download', () => {
  afterEach(() => vi.clearAllMocks())

  it('tells the visitor when a document link cannot be opened', async () => {
    vi.mocked(api.get).mockResolvedValue([doc('javascript:alert(1)')])
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})

    renderSection()
    await userEvent.click(await screen.findByRole('button', { name: 'Download Budget Packet' }))

    expect(click).not.toHaveBeenCalled()
    expect(toast.error).toHaveBeenCalledWith(expect.stringMatching(/can't be opened/))
  })

  it('opens a normal document link', async () => {
    vi.mocked(api.get).mockResolvedValue([doc('/files/budget.pdf')])
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})

    renderSection()
    await userEvent.click(await screen.findByRole('button', { name: 'Download Budget Packet' }))

    expect(click).toHaveBeenCalledOnce()
    expect(toast.error).not.toHaveBeenCalled()
  })
})
