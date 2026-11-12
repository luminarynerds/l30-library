import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

vi.mock('@/hooks/usePageTitle', () => ({ usePageTitle: () => {} }))
vi.mock('@/i18n/I18nContext', () => ({ useTranslation: () => ({ t: (k: string, f?: string) => f ?? k, language: 'en' }) }))
vi.mock('@/api/releases-api', () => ({
  getFeaturedUpcoming: vi.fn(async () => ({
    items: [{ tracker_book_id: 'a', title: 'Villa Coco', author_name: 'Greer', source: 'libraryreads',
              source_url: 'https://libraryreads.org', blurb_credit: 'Mara, Champaign PL', release_date: '2099-06-15',
              is_date_exact: true, library_status: 'new' },
            { tracker_book_id: 'b', title: 'Owned Title', author_name: 'Author', source: 'manual',
              release_date: '2099-07-01', is_date_exact: true, library_status: 'owned', catalog_item_id: 42 }],
    total: 2, page: 1, per_page: 24 })),
}))
import ComingSoonPage from '../ComingSoonPage'

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}><ComingSoonPage /></QueryClientProvider>)
}

describe('ComingSoonPage', () => {
  it('renders titles with LibraryReads link-back + nominator credit', async () => {
    renderPage()
    expect(await screen.findByText('Villa Coco')).toBeInTheDocument()
    const link = await screen.findByRole('link', { name: /libraryreads/i })
    expect(link).toHaveAttribute('href', 'https://libraryreads.org')
    expect(screen.getByText(/Mara, Champaign PL/)).toBeInTheDocument()
  })

  it('renders the card title as a heading', async () => {
    renderPage()
    expect(await screen.findByRole('heading', { name: 'Villa Coco' })).toBeInTheDocument()
  })

  it('shows owned-status with a catalog link', async () => {
    renderPage()
    const inCatalog = await screen.findByText('In our catalog')
    expect(inCatalog).toBeInTheDocument()
    expect(inCatalog.closest('a')).toHaveAttribute('href', '/catalog/42')
  })
})
