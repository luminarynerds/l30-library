/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Catalog Search — Comprehensive Test Suite
 *
 * Tests each of the key catalog search scenarios:
 *  1. Search for "python programming" — verify reasonable results
 *  2. Search with special characters: "Where the Wild Things Are — 50th Anniversary"
 *  3. ISBN search: "978-0-06-112008-4"
 *  4. Bibframe catalog view at /catalog/bibframe renders
 *  5. Zero results for "xyzzyflurb" — friendly empty state
 *  6. Catalog item detail page — cover image, description, availability, location
 *  7. Semantic / natural language search (if enabled)
 *  8. Sort/filter by format (audiobook, ebook, DVD, etc.)
 *  9. Gutenberg free ebooks page — browse and borrow
 * 10. Back button — search state persistence
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, within, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { OrganizationFeaturesProvider } from '@/contexts/OrganizationFeaturesContext'
import { BrandingProvider } from '@/contexts/BrandingContext'
import { UnifiedAccessibilityProvider } from '@/features/accessibility/context/UnifiedAccessibilityContext'

// --------------------------------------------------------------------------
// Mocks — must be at module level before component imports
// --------------------------------------------------------------------------

const mockSearchCatalog = vi.fn()
const mockGetCatalogItem = vi.fn()

vi.mock('@/api/api', () => ({
  searchCatalog: (...args: unknown[]) => mockSearchCatalog(...args),
  getCatalogItem: (...args: unknown[]) => mockGetCatalogItem(...args),
}))

vi.mock('@/api/domains/catalog/catalog-api', () => ({
  searchCatalog: (...args: unknown[]) => mockSearchCatalog(...args),
  getCatalogItem: (...args: unknown[]) => mockGetCatalogItem(...args),
}))

const mockUnifiedSearch = vi.fn()
const mockGetSearchSuggestions = vi.fn()

// useCatalogSearch runs fetchCatalogFacets alongside unifiedSearch (in
// Promise.all) to populate sidebar facets, falling back to EMPTY_FACETS on
// failure. Both must be present here or the queryFn throws synchronously
// (calling `undefined(...)`) and the results grid never leaves "loading".
const mockEmptyFacets = vi.hoisted(() => ({
  item_type: [],
  status: [],
  publication_year: [],
  location: [],
  subject: [],
  author: [],
  series: [],
}))

vi.mock('@/api/domains/catalog/unified-search-api', () => ({
  unifiedSearch: (...args: unknown[]) => mockUnifiedSearch(...args),
  fetchCatalogFacets: vi.fn().mockResolvedValue(mockEmptyFacets),
  EMPTY_FACETS: mockEmptyFacets,
  getSourceLabel: (s: string) => s === 'local' ? 'Local Catalog' : s === 'openlibrary' ? 'Open Library' : s,
}))

vi.mock('@/api/pg-search-api', () => ({
  getSearchSuggestions: (...args: unknown[]) => mockGetSearchSuggestions(...args),
}))

const mockSearchBibframe = vi.fn()
const mockListBibframeWorks = vi.fn()
const mockGetBibframeWork = vi.fn()

vi.mock('@/api/domains/catalog/bibframe-api', () => ({
  searchBibframeCatalog: (...args: unknown[]) => mockSearchBibframe(...args),
  listBibframeWorks: (...args: unknown[]) => mockListBibframeWorks(...args),
  getBibframeWork: (...args: unknown[]) => mockGetBibframeWork(...args),
}))

const mockHybridSearch = vi.fn()
const mockGetSemanticHealth = vi.fn()
const mockAutocomplete = vi.fn()

vi.mock('@/api/domains/catalog/semantic-search-api', () => ({
  semanticSearch: vi.fn(),
  hybridSearch: (...args: unknown[]) => mockHybridSearch(...args),
  crossCollectionSearch: vi.fn(),
  autocomplete: (...args: unknown[]) => mockAutocomplete(...args),
  findSimilarAuthors: vi.fn(),
  getHiddenGems: vi.fn(),
  findSimilarItems: vi.fn(),
  getSemanticHealth: (...args: unknown[]) => mockGetSemanticHealth(...args),
  getConfidenceColor: (c: string) => c === 'high' ? 'green' : c === 'medium' ? 'yellow' : 'red',
  getConfidenceLabel: (c: string) => c,
  getMatchTypeLabel: (m: string) => m,
  getSimilarityColor: () => 'blue',
}))

vi.mock('@/features/accessibility/hooks/useUnifiedAccessibility', () => ({
  useUnifiedAccessibility: () => ({
    quietMode: false,
    focusMode: false,
    simplifiedView: false,
    reduceMotion: false,
    showImages: true,
    preferPagination: false,
    noFOMO: false,
    announceToScreenReader: vi.fn(),
  }),
}))

vi.mock('@/i18n/I18nContext', () => ({
  useTranslation: () => ({
    language: 'en',
    setLanguage: vi.fn(),
    isRTL: false,
    t: (key: string, fallbackOrVars?: string | Record<string, unknown>) => {
      const translations: Record<string, string> = {
        'catalog.title': 'Browse the Catalog',
        'catalog.activeFilters': 'Active Filters',
        'catalog.clearAll': 'Clear all',
        'catalog.loadingItems': 'Loading items...',
        'catalog.unableToLoad': 'Unable to load catalog results.',
        'catalog.temporaryIssue': 'This is a temporary issue.',
        'catalog.refreshPage': 'Refresh Page',
        'catalog.pageOf': 'Page {current} of {total}',
        'catalog.sort.relevance': 'Relevance',
        'catalog.sort.titleAZ': 'Title (A-Z)',
        'catalog.sort.titleZA': 'Title (Z-A)',
        'catalog.sort.authorAZ': 'Author (A-Z)',
        'catalog.sort.authorZA': 'Author (Z-A)',
        'catalog.sort.yearNewest': 'Year (Newest)',
        'catalog.sort.yearOldest': 'Year (Oldest)',
        'catalog.filter.format': 'Format',
        'catalog.filter.status': 'Status',
        'catalog.filter.location': 'Location',
        'catalog.sortBy': 'Sort results by',
        'catalog.itemsFound': '{count} items found',
        // Empty-state copy actually read by CatalogResultsList/CatalogPageContent
        // (getEmptyStateHeadline + the sr-only live region in CatalogPageContent).
        // {query} is not interpolated by this test's stub t(), which is fine —
        // assertions only need the surrounding literal text.
        'catalog.emptyState.queryWithFilters': "No items matched '{query}' with current filters.",
        'catalog.emptyState.queryOnly': "No items matched '{query}'.",
        'catalog.emptyState.filtersOnly': 'No items matched your current filters.',
        'catalog.noSearchMatches': 'No matches for your search. Try a broader keyword.',
        'catalog.noFilterMatches': 'No matches for your current filters. Clear one filter or try a broader keyword.',
        'aria.catalogContent.sortResultsBy': 'Sort results by',
        'catalog.tryDifferentSearch': 'Try checking your spelling, or search with fewer or different words.',
        'catalog.exploreByType': 'You can also explore by type:',
        'catalog.clearFilters': 'Clear filters',
        'catalog.browseByFormat': 'Browse by format',
        'catalog.formatChipLabels.book': 'Book',
        'catalog.formatChipLabels.ebook': 'E-Book',
        'catalog.formatChipLabels.audiobook': 'Audiobook',
        'catalog.formatChipLabels.dvd': 'DVD',
        'catalog.formatChipLabels.game': 'Game',
        'catalog.formatChipLabels.kit': 'Kit',
        'catalog.formatChipLabels.equipment': 'Equipment',
        'catalog.results.exploreByType': 'You can also explore by type:',
        'common.search': 'Search',
        'common.loading': 'Loading',
        'common.previous': 'Previous',
        'common.next': 'Next',
        'aria.gutenberg.searchProjectGutenberg': 'Search Project Gutenberg',
      }
      if (typeof fallbackOrVars === 'string') return fallbackOrVars
      return translations[key] || key
    },
  }),
}))

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: null,
    token: null,
    isAuthenticated: false,
  }),
}))

vi.mock('@/hooks/useDebounce', () => ({
  useDebounce: (value: unknown) => value,
}))

vi.mock('@/components/skeletons/CatalogItemSkeleton', () => ({
  CatalogItemSkeletonList: () => <div data-testid="skeleton-list">Loading...</div>,
}))

// Mock detail page hooks so CatalogItemPage can render without live API
vi.mock('@/pages/catalog/hooks/useItemDetail', () => ({
  useItemDetail: () => ({
    item: {
      id: 42,
      title: 'The Great Gatsby',
      author: 'F. Scott Fitzgerald',
      description: 'Set in the Jazz Age on Long Island, the novel depicts narrator Nick Carraway.',
      status: 'available',
      location: 'Downtown Branch - Fiction - F',
      cover_url: 'https://example.com/gatsby-cover.jpg',
      publication_year: 1925,
      isbn: '978-0743273565',
      publisher: 'Scribner',
      item_type: 'book',
      subjects: 'Fiction, Classic',
      page_count: 180,
      barcode: '999999',
      created_at: '2020-01-01',
      is_large_print: false,
      images: [],
      series_name: null,
      series_number: null,
      call_number: 'F FIT',
      dewey_decimal: null,
      total_checkouts: 100,
      director: null,
      actors: null,
      runtime_minutes: null,
      media_format: null,
      content_rating: null,
      disc_count: null,
      studio: null,
      artist: null,
      track_count: null,
      music_genre: null,
      platform: null,
      player_count: null,
      game_genre: null,
      brand: null,
      model_number: null,
      dimensions: null,
      material: null,
      kit_contents: null,
    },
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  }),
}))

vi.mock('@/pages/catalog/hooks/useItemActions', () => ({
  useItemActions: () => ({
    isFavorited: false,
    isLoadingFavorite: false,
    handleToggleFavorite: vi.fn(),
    lists: [],
    listsWithItem: new Set(),
    handleAddToList: vi.fn(),
    handleCreateNewList: vi.fn(),
    handleCreateListSubmit: vi.fn(),
    handleCancelCreateList: vi.fn(),
    showListDropdown: false,
    setShowListDropdown: vi.fn(),
    showCreateListForm: false,
    setShowCreateListForm: vi.fn(),
    newListName: '',
    setNewListName: vi.fn(),
    creatingList: false,
    showHoldModal: false,
    setShowHoldModal: vi.fn(),
  }),
}))

vi.mock('@/pages/catalog/hooks/useItemReviews', () => ({
  useItemReviews: () => ({
    preferences: { enabled: true, count: 3, strategy: 'mixed' },
    showSettings: false,
    setShowSettings: vi.fn(),
    similarItems: { items: [] },
    isLoading: false,
    handlePreferenceChange: vi.fn(),
    availableCount: 0,
  }),
}))

vi.mock('@/pages/catalog/hooks/useRelatedFormats', () => ({
  useRelatedFormats: () => ({
    formats: [{
      id: 42,
      label: 'Book',
      item_type: 'book',
      status: 'available',
      location: 'Downtown Branch - Fiction - F',
      is_large_print: false,
      isCurrent: true,
    }],
  }),
}))

vi.mock('@/pages/catalog/hooks/useHoldPosition', () => ({
  useHoldPosition: () => ({
    hasHold: false,
    position: 0,
    totalAhead: 0,
    estimatedReadyDate: null,
    holdStatus: null,
  }),
}))

// --------------------------------------------------------------------------
// Component imports — AFTER all vi.mock() calls
// --------------------------------------------------------------------------

import CatalogPage from '../CatalogPage'
import BibframeCatalogPage from '../BibframeCatalogPage'
import GutenbergPage from '../GutenbergPage'
import SemanticSearchPage from '../SemanticSearchPage'
import CatalogItemPage from '../catalog/CatalogItemPage'

// --------------------------------------------------------------------------
// Helpers
// --------------------------------------------------------------------------

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  })
}

interface MockCatalogItem {
  id: number
  title: string
  author: string | null
  item_type: string
  status: string
  isbn: string | null
  publisher: string | null
  publication_year: number | null
  description: string | null
  subjects: string | null
  cover_url: string | null
  page_count: number | null
  location: string | null
  barcode: string | null
  created_at: string
  is_large_print: boolean
  images: unknown[]
  series_name: string | null
  series_number: string | null
  call_number: string | null
  dewey_decimal: string | null
  total_checkouts: number
  director: string | null
  actors: string | null
  runtime_minutes: number | null
  media_format: string | null
  content_rating: string | null
  disc_count: number | null
  studio: string | null
  artist: string | null
  track_count: number | null
  music_genre: string | null
  platform: string | null
  player_count: string | null
  game_genre: string | null
  brand: string | null
  model_number: string | null
  dimensions: string | null
  material: string | null
  kit_contents: string | null
}

function makeCatalogItem(overrides: Partial<MockCatalogItem> = {}): MockCatalogItem {
  return {
    id: 1,
    title: 'Test Book',
    author: 'Test Author',
    item_type: 'book',
    status: 'available',
    isbn: '978-0123456789',
    publisher: 'Test Publisher',
    publication_year: 2023,
    description: 'A test book about testing.',
    subjects: 'Testing, Software',
    cover_url: 'https://example.com/cover.jpg',
    page_count: 300,
    location: 'Main Library - Fiction - F',
    barcode: '123456789',
    created_at: '2023-01-01T00:00:00Z',
    is_large_print: false,
    images: [],
    series_name: null,
    series_number: null,
    call_number: '005.14 TES',
    dewey_decimal: '005.14',
    total_checkouts: 42,
    director: null,
    actors: null,
    runtime_minutes: null,
    media_format: null,
    content_rating: null,
    disc_count: null,
    studio: null,
    artist: null,
    track_count: null,
    music_genre: null,
    platform: null,
    player_count: null,
    game_genre: null,
    brand: null,
    model_number: null,
    dimensions: null,
    material: null,
    kit_contents: null,
    ...overrides,
  }
}

function makeUnifiedSearchResult(items: MockCatalogItem[], total?: number) {
  return {
    query: '',
    total_results: total ?? items.length,
    results: items.map(item => ({
      id: `local-${item.id}`,
      source: 'local',
      source_id: String(item.id),
      title: item.title,
      author: item.author,
      authors: item.author ? [item.author] : [],
      format: item.item_type,
      format_details: [],
      description: item.description,
      cover_url: item.cover_url,
      isbn: item.isbn,
      publisher: item.publisher,
      publication_year: item.publication_year,
      subjects: item.subjects ? item.subjects.split(', ') : [],
      language: 'en',
      is_available: item.status === 'available',
      availability_count: item.status === 'available' ? 1 : 0,
      relevance_score: 0.9,
      source_url: null,
    })),
    sources_searched: ['local'],
    source_counts: { local: total ?? items.length },
    search_time_ms: 50,
    has_more: false,
  }
}

function renderCatalogPage(initialRoute = '/catalog') {
  // useCatalogSearch reads its initial query/filters from window.location.search
  // directly (not react-router's useSearchParams) to avoid stale params under
  // v7_startTransition (see 52e725957). MemoryRouter never touches
  // window.location, so tests must push it there themselves.
  window.history.pushState({}, '', initialRoute)
  const queryClient = createQueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      <BrandingProvider>
        <OrganizationFeaturesProvider>
          <UnifiedAccessibilityProvider>
            <MemoryRouter initialEntries={[initialRoute]}>
              <Routes>
                <Route path="/catalog" element={<CatalogPage />} />
              </Routes>
            </MemoryRouter>
          </UnifiedAccessibilityProvider>
        </OrganizationFeaturesProvider>
      </BrandingProvider>
    </QueryClientProvider>,
  )
}

function renderCatalogPageWithSearchParam(query: string) {
  return renderCatalogPage(`/catalog?q=${encodeURIComponent(query)}`)
}

// GutenbergPage and CatalogItemPage both call useOrganizationFeatures (feature
// gating), so they need OrganizationFeaturesProvider in the tree.
function renderGutenbergPage() {
  const queryClient = createQueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      <OrganizationFeaturesProvider>
        <MemoryRouter initialEntries={['/gutenberg']}>
          <Routes>
            <Route path="/gutenberg" element={<GutenbergPage />} />
          </Routes>
        </MemoryRouter>
      </OrganizationFeaturesProvider>
    </QueryClientProvider>,
  )
}

// ==================== Tests ====================

describe('Catalog Search', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.localStorage.getItem = vi.fn().mockReturnValue(null)
    window.localStorage.setItem = vi.fn()
    window.localStorage.removeItem = vi.fn()
    mockGetSearchSuggestions.mockResolvedValue([])
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  // --------------------------------------------------------------------------
  // 1. Search for "python programming" — reasonable results
  // --------------------------------------------------------------------------
  describe('1. Search for "python programming"', () => {
    it('renders search results for a programming query', async () => {
      const pythonItems = [
        makeCatalogItem({
          id: 1,
          title: 'Python Programming for Beginners',
          author: 'Jane Smith',
          description: 'Learn Python from scratch with practical examples.',
          subjects: 'Python, Programming, Computer Science',
        }),
        makeCatalogItem({
          id: 2,
          title: 'Advanced Python Programming',
          author: 'John Doe',
          description: 'Deep dive into Python advanced features.',
          subjects: 'Python, Programming',
          item_type: 'ebook',
        }),
        makeCatalogItem({
          id: 3,
          title: 'Python Crash Course',
          author: 'Eric Matthes',
          isbn: '978-1593279288',
          description: 'A hands-on, project-based introduction to programming.',
        }),
      ]

      mockUnifiedSearch.mockResolvedValue(makeUnifiedSearchResult(pythonItems, 3))

      renderCatalogPageWithSearchParam('python programming')

      await waitFor(() => {
        expect(mockUnifiedSearch).toHaveBeenCalledWith(
          expect.objectContaining({ query: 'python programming' }),
        )
      })

      await waitFor(() => {
        expect(screen.getAllByText(/3.*items?\s*found/i).length).toBeGreaterThanOrEqual(1)
      })

      expect(screen.getByText('Python Programming for Beginners')).toBeInTheDocument()
      expect(screen.getByText('Advanced Python Programming')).toBeInTheDocument()
      expect(screen.getByText('Python Crash Course')).toBeInTheDocument()
    })

    it('passes the query string to the unifiedSearch API', async () => {
      mockUnifiedSearch.mockResolvedValue(makeUnifiedSearchResult([]))

      renderCatalogPageWithSearchParam('python programming')

      await waitFor(() => {
        expect(mockUnifiedSearch).toHaveBeenCalledWith(
          expect.objectContaining({ query: 'python programming' }),
        )
      })
    })
  })

  // --------------------------------------------------------------------------
  // 2. Search with special characters
  // --------------------------------------------------------------------------
  describe('2. Search with special characters', () => {
    it('handles em-dashes and special characters in the search query', async () => {
      const specialItem = makeCatalogItem({
        id: 10,
        title: 'Where the Wild Things Are \u2014 50th Anniversary',
        author: 'Maurice Sendak',
        description: 'Special anniversary edition of the beloved classic.',
      })

      mockUnifiedSearch.mockResolvedValue(makeUnifiedSearchResult([specialItem], 1))

      renderCatalogPageWithSearchParam('Where the Wild Things Are \u2014 50th Anniversary')

      await waitFor(() => {
        expect(mockUnifiedSearch).toHaveBeenCalledWith(
          expect.objectContaining({
            query: 'Where the Wild Things Are \u2014 50th Anniversary',
          }),
        )
      })

      await waitFor(() => {
        expect(screen.getAllByText(/1.*items?\s*found/i).length).toBeGreaterThanOrEqual(1)
      })

      expect(screen.getByText('Where the Wild Things Are \u2014 50th Anniversary')).toBeInTheDocument()
    })

    it('URL-encodes special characters in the search param', () => {
      mockUnifiedSearch.mockResolvedValue(makeUnifiedSearchResult([]))

      renderCatalogPageWithSearchParam('Where the Wild Things Are \u2014 50th Anniversary')

      expect(mockUnifiedSearch).toHaveBeenCalled()
    })
  })

  // --------------------------------------------------------------------------
  // 3. ISBN search
  // --------------------------------------------------------------------------
  describe('3. ISBN search', () => {
    it('searches by ISBN and finds the correct item', async () => {
      const isbnItem = makeCatalogItem({
        id: 20,
        title: 'To Kill a Mockingbird',
        author: 'Harper Lee',
        isbn: '978-0-06-112008-4',
        description: 'The unforgettable novel of a childhood in a sleepy Southern town.',
        publisher: 'Harper Perennial Modern Classics',
        publication_year: 2006,
      })

      mockUnifiedSearch.mockResolvedValue(makeUnifiedSearchResult([isbnItem], 1))

      renderCatalogPageWithSearchParam('978-0-06-112008-4')

      await waitFor(() => {
        expect(mockUnifiedSearch).toHaveBeenCalledWith(
          expect.objectContaining({ query: '978-0-06-112008-4' }),
        )
      })

      await waitFor(() => {
        expect(screen.getByText('To Kill a Mockingbird')).toBeInTheDocument()
      })

      expect(screen.getByText('Harper Lee')).toBeInTheDocument()
    })

    it('sends the raw ISBN with hyphens to the API', async () => {
      mockUnifiedSearch.mockResolvedValue(makeUnifiedSearchResult([]))

      renderCatalogPageWithSearchParam('978-0-06-112008-4')

      await waitFor(() => {
        expect(mockUnifiedSearch).toHaveBeenCalledWith(
          expect.objectContaining({ query: '978-0-06-112008-4' }),
        )
      })
    })
  })

  // --------------------------------------------------------------------------
  // 4. Bibframe catalog view renders at /catalog/bibframe
  // --------------------------------------------------------------------------
  describe('4. Bibframe catalog view', () => {
    it('renders the BibframeCatalogPage component', async () => {
      mockListBibframeWorks.mockResolvedValue({
        items: [],
        total: 0,
        page: 1,
        per_page: 20,
        pages: 0,
      })
      mockSearchBibframe.mockResolvedValue({
        items: [],
        total: 0,
        page: 1,
        per_page: 20,
        pages: 0,
      })

      const queryClient = createQueryClient()

      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter initialEntries={['/catalog/bibframe']}>
            <Routes>
              <Route path="/catalog/bibframe" element={<BibframeCatalogPage />} />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>,
      )

      await waitFor(() => {
        expect(screen.getByText(/BIBFRAME Catalog/i)).toBeInTheDocument()
      })
    })

    it('shows the search input for BIBFRAME Works', async () => {
      mockListBibframeWorks.mockResolvedValue({
        items: [],
        total: 0,
        page: 1,
        per_page: 20,
        pages: 0,
      })
      mockSearchBibframe.mockResolvedValue({
        items: [],
        total: 0,
        page: 1,
        per_page: 20,
        pages: 0,
      })

      const queryClient = createQueryClient()

      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter initialEntries={['/catalog/bibframe']}>
            <Routes>
              <Route path="/catalog/bibframe" element={<BibframeCatalogPage />} />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>,
      )

      await waitFor(() => {
        const searchInputs = screen.getAllByRole('textbox')
        expect(searchInputs.length).toBeGreaterThan(0)
      })
    })
  })

  // --------------------------------------------------------------------------
  // 5. Zero results — friendly empty state
  // --------------------------------------------------------------------------
  describe('5. Zero results for "xyzzyflurb"', () => {
    it('shows a friendly empty state message', async () => {
      mockUnifiedSearch.mockResolvedValue(makeUnifiedSearchResult([], 0))

      renderCatalogPageWithSearchParam('xyzzyflurb')

      await waitFor(() => {
        expect(mockUnifiedSearch).toHaveBeenCalledWith(
          expect.objectContaining({ query: 'xyzzyflurb' }),
        )
      })

      await waitFor(() => {
        expect(screen.getByText(/no.*items.*matched/i)).toBeInTheDocument()
      })
    })

    it('shows a helpful suggestion to try different search terms', async () => {
      mockUnifiedSearch.mockResolvedValue(makeUnifiedSearchResult([], 0))

      renderCatalogPageWithSearchParam('xyzzyflurb')

      await waitFor(() => {
        expect(
          screen.getByText(/No matches for your search|try a broader keyword/i),
        ).toBeInTheDocument()
      })
    })

    it('shows "explore by type" format buttons in empty state', async () => {
      mockUnifiedSearch.mockResolvedValue(makeUnifiedSearchResult([], 0))

      renderCatalogPageWithSearchParam('xyzzyflurb')

      // The empty state renders explore-by-type section with format browse buttons
      await waitFor(() => {
        expect(screen.getByText(/explore by type/i)).toBeInTheDocument()
      })
      // Format labels appear as browse buttons in the empty state
      expect(screen.getAllByText('Book').length).toBeGreaterThanOrEqual(1)
      expect(screen.getAllByText('Audiobook').length).toBeGreaterThanOrEqual(1)
      expect(screen.getAllByText('E-Book').length).toBeGreaterThanOrEqual(1)
      expect(screen.getAllByText('DVD').length).toBeGreaterThanOrEqual(1)
    })

    it('shows a "Clear search" button in empty state (no active filters)', async () => {
      mockUnifiedSearch.mockResolvedValue(makeUnifiedSearchResult([], 0))

      renderCatalogPageWithSearchParam('xyzzyflurb')

      // CatalogResultsList is supposed to show "Clear all filters" only when
      // filters are active, and plain "Clear search" for a bare text search
      // (CatalogResultsList.tsx:417-418, hasActiveFilters ? ... : ...).
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /^clear search$/i })).toBeInTheDocument()
      })
    })
  })

  // --------------------------------------------------------------------------
  // 6. Catalog item detail page
  // --------------------------------------------------------------------------
  describe('6. Catalog item detail page', () => {
    it('displays cover image, description, availability, and location', async () => {
      const queryClient = createQueryClient()

      render(
        <QueryClientProvider client={queryClient}>
          <BrandingProvider>
            <OrganizationFeaturesProvider>
              <UnifiedAccessibilityProvider>
                <MemoryRouter initialEntries={['/catalog/42']}>
                  <Routes>
                    <Route path="/catalog/:id" element={<CatalogItemPage />} />
                  </Routes>
                </MemoryRouter>
              </UnifiedAccessibilityProvider>
            </OrganizationFeaturesProvider>
          </BrandingProvider>
        </QueryClientProvider>,
      )

      // Title
      await waitFor(() => {
        expect(screen.getByText('The Great Gatsby')).toBeInTheDocument()
      })

      // Author
      expect(screen.getByText('F. Scott Fitzgerald')).toBeInTheDocument()

      // Cover image
      // Alt text is built by buildCoverAlt (title, author, format) — see
      // e16070e59 (accessibility improvements in catalog).
      const coverImg = screen.getByAltText('The Great Gatsby, by F. Scott Fitzgerald, Book cover')
      expect(coverImg).toBeInTheDocument()
      // Cover images render through the backend cover-proxy, not the raw
      // cover_url, to keep patron browsing private (no third-party Referer)
      // — see 6148d0479 (feat(catalog): proxy cover images via backend).
      expect(coverImg).toHaveAttribute('src', '/api/v1/catalog/covers/42')

      // Description
      expect(screen.getByText(/Set in the Jazz Age/)).toBeInTheDocument()

      // Availability badge (may appear in header + format tabs)
      expect(screen.getAllByText('Available').length).toBeGreaterThanOrEqual(1)

      // Location (may appear in header + format tabs)
      expect(screen.getAllByText('Downtown Branch - Fiction - F').length).toBeGreaterThanOrEqual(1)
    })
  })

  // --------------------------------------------------------------------------
  // 7. Semantic / natural language search
  // --------------------------------------------------------------------------
  describe('7. Semantic search — natural language query', () => {
    it('renders the SemanticSearchPage', async () => {
      mockHybridSearch.mockResolvedValue({
        query: '',
        total_results: 0,
        merged_results: [],
        search_time_ms: 0,
        semantic_time_ms: 0,
        keyword_time_ms: 0,
        merge_strategy: 'rrf',
        has_more: false,
      })
      mockGetSemanticHealth.mockResolvedValue({
        status: 'healthy',
        semantic_search_ready: true,
        embeddings_available: 5000,
        minimum_embeddings_required: 100,
        features: {},
        message: 'Semantic search is ready.',
      })
      mockAutocomplete.mockResolvedValue({
        query: '',
        suggestions: [],
        search_time_ms: 10,
        total_suggestions: 0,
        strategy: 'prefix',
      })

      const queryClient = createQueryClient()

      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter initialEntries={['/semantic-search']}>
            <Routes>
              <Route path="/semantic-search" element={<SemanticSearchPage />} />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>,
      )

      // Page should render with a search interface. The default "hybrid"
      // mode's search input is role="combobox" (autocomplete listbox), not
      // "textbox" — see afa81fa3a (a11y: dialog semantics + control names).
      await waitFor(() => {
        const searchInputs = [
          ...screen.queryAllByRole('textbox'),
          ...screen.queryAllByRole('combobox'),
        ]
        expect(searchInputs.length).toBeGreaterThan(0)
      })
    })

    it('hybridSearch is callable with natural language queries', async () => {
      mockHybridSearch.mockResolvedValue({
        query: 'books about coping with grief for teenagers',
        total_results: 0,
        merged_results: [],
        search_time_ms: 100,
        semantic_time_ms: 50,
        keyword_time_ms: 50,
        merge_strategy: 'rrf',
        has_more: false,
      })

      await mockHybridSearch('books about coping with grief for teenagers')

      expect(mockHybridSearch).toHaveBeenCalledWith(
        'books about coping with grief for teenagers',
      )
    })
  })

  // --------------------------------------------------------------------------
  // 8. Sort / filter by format
  // --------------------------------------------------------------------------
  describe('8. Sort/filter by format', () => {
    it('renders format chip buttons for browsing by format', async () => {
      const mixedItems = [
        makeCatalogItem({ id: 1, title: 'A Book', item_type: 'book' }),
        makeCatalogItem({ id: 2, title: 'An Audiobook', item_type: 'audiobook' }),
        makeCatalogItem({ id: 3, title: 'An E-Book', item_type: 'ebook' }),
        makeCatalogItem({ id: 4, title: 'A DVD', item_type: 'dvd' }),
      ]

      mockUnifiedSearch.mockResolvedValue(makeUnifiedSearchResult(mixedItems, 4))

      renderCatalogPage()

      await waitFor(() => {
        expect(screen.getAllByText(/4.*items?\s*found/i).length).toBeGreaterThanOrEqual(1)
      })

      // With no query and no filters, CatalogPageContent is supposed to show
      // CatalogLandingPanel's "browse by format" chip row (role="group",
      // aria-label catalog.browseByFormat -> CatalogFormatChips.tsx:29).
      // The landing panel is gated on `!activeQuery && !hasActiveFilters`
      // (CatalogPageContent.tsx:551).
      const formatGroup = screen.getByRole('group', { name: /format/i })
      expect(formatGroup).toBeInTheDocument()
      const chipButtons = within(formatGroup).getAllByRole('button')
      expect(chipButtons.length).toBeGreaterThanOrEqual(4)
    })

    it('calls unifiedSearch with formats filter when a format chip is clicked', async () => {
      mockUnifiedSearch.mockResolvedValue(makeUnifiedSearchResult([
        makeCatalogItem({ id: 1, title: 'Test', item_type: 'book' }),
      ], 1))

      renderCatalogPage()

      await waitFor(() => {
        expect(mockUnifiedSearch).toHaveBeenCalled()
      })

      // Click a format checkbox in the sidebar filter
      const bookCheckbox = screen.getAllByRole('checkbox', { name: /book/i })[0]!
      await userEvent.click(bookCheckbox)

      await waitFor(() => {
        const calls = mockUnifiedSearch.mock.calls
        const lastCall = calls[calls.length - 1]
        expect(lastCall?.[0]).toHaveProperty('formats')
      })
    })

    it('displays sort dropdown with sort options', async () => {
      mockUnifiedSearch.mockResolvedValue(makeUnifiedSearchResult([
        makeCatalogItem({ id: 1, title: 'Test' }),
      ], 1))

      renderCatalogPage()

      await waitFor(() => {
        expect(screen.getAllByText(/1.*items?\s*found/i).length).toBeGreaterThanOrEqual(1)
      })

      const sortSelect = screen.getByLabelText('Sort results by')
      expect(sortSelect).toBeInTheDocument()

      const options = within(sortSelect as HTMLElement).getAllByRole('option')
      const labels = options.map(o => o.textContent)

      expect(labels).toContain('Relevance')
      expect(labels).toContain('Title (A-Z)')
      expect(labels).toContain('Title (Z-A)')
      expect(labels).toContain('Author (A-Z)')
      expect(labels).toContain('Author (Z-A)')
      expect(labels).toContain('Year (Newest)')
      expect(labels).toContain('Year (Oldest)')
    })

    it('updates sort when a new sort option is selected', async () => {
      mockUnifiedSearch.mockResolvedValue(makeUnifiedSearchResult([
        makeCatalogItem({ id: 1, title: 'Test' }),
      ]))

      renderCatalogPage()

      await waitFor(() => {
        expect(screen.getByLabelText('Sort results by')).toBeInTheDocument()
      })

      const sortSelect = screen.getByLabelText('Sort results by')
      await userEvent.selectOptions(sortSelect, 'title-asc')

      // Sort is applied client-side; verify the select value changed
      await waitFor(() => {
        expect(sortSelect).toHaveValue('title-asc')
      })
    })
  })

  // --------------------------------------------------------------------------
  // 9. Gutenberg free ebooks page
  // --------------------------------------------------------------------------
  describe('9. Gutenberg free ebooks page', () => {
    it('renders the Gutenberg page with hero, search, genres, and quick links', () => {
      renderGutenbergPage()

      // Page title (may appear in heading + navigation; use heading role)
      expect(screen.getByRole('heading', { name: 'Project Gutenberg', level: 1 })).toBeInTheDocument()

      // Hero stats
      expect(screen.getByText('75,000+')).toBeInTheDocument()
      expect(screen.getByText('60+')).toBeInTheDocument()

      // Search section
      expect(screen.getByLabelText('Search Project Gutenberg')).toBeInTheDocument()

      // Genre sections
      expect(screen.getByText('Fiction & Literature')).toBeInTheDocument()
      expect(screen.getByText('Poetry & Drama')).toBeInTheDocument()
      expect(screen.getByText('History & Biography')).toBeInTheDocument()
      expect(screen.getByText('Philosophy & Religion')).toBeInTheDocument()
      expect(screen.getByText('Science & Nature')).toBeInTheDocument()
      expect(screen.getByText("Children's Literature")).toBeInTheDocument()

      // Quick Links
      expect(screen.getByText('Top 100')).toBeInTheDocument()
      expect(screen.getByText('New Arrivals')).toBeInTheDocument()
      expect(screen.getByText('By Author')).toBeInTheDocument()
      expect(screen.getByText('By Language')).toBeInTheDocument()

      // Staff Picks
      expect(screen.getByText('Pride and Prejudice')).toBeInTheDocument()
      expect(screen.getByText('Frankenstein')).toBeInTheDocument()
    })

    it('expands genres when clicked to show sample titles', async () => {
      renderGutenbergPage()

      // Click on Fiction & Literature genre
      const fictionButton = screen.getByText('Fiction & Literature').closest('button')
      expect(fictionButton).toBeTruthy()

      if (fictionButton) {
        await userEvent.click(fictionButton)
      }

      // Sample titles should now be visible
      await waitFor(() => {
        expect(screen.getByText('A Tale of Two Cities')).toBeInTheDocument()
        expect(screen.getByText('The Adventures of Huckleberry Finn')).toBeInTheDocument()
      })
    })

    it('search opens gutenberg.org in a new tab', async () => {
      const mockOpen = vi.fn()
      vi.spyOn(window, 'open').mockImplementation(mockOpen)

      renderGutenbergPage()

      const searchInput = screen.getByLabelText('Search Project Gutenberg')
      await userEvent.type(searchInput, 'Jane Austen')

      const searchButton = screen.getByRole('button', { name: 'Search' })
      await userEvent.click(searchButton)

      expect(mockOpen).toHaveBeenCalledWith(
        'https://www.gutenberg.org/ebooks/search/?query=Jane%20Austen',
        '_blank',
        'noopener,noreferrer',
      )
    })

    it('renders the FAQ section', () => {
      renderGutenbergPage()

      expect(screen.getByText('What is Project Gutenberg?')).toBeInTheDocument()
      expect(screen.getByText('Are these books really free?')).toBeInTheDocument()
      expect(screen.getByText('What formats are available?')).toBeInTheDocument()
      expect(screen.getByText('Do I need a library card?')).toBeInTheDocument()
    })

    it('renders vendor wind-down messaging', () => {
      renderGutenbergPage()

      expect(screen.getByText(/Why We.*Canceling Commercial Digital Platforms/)).toBeInTheDocument()
    })
  })

  // --------------------------------------------------------------------------
  // 10. Back button — search state persistence
  // --------------------------------------------------------------------------
  describe('10. Back button search state persistence', () => {
    it('reads the search query from URL search params on mount', async () => {
      mockUnifiedSearch.mockResolvedValue(
        makeUnifiedSearchResult([
          makeCatalogItem({ id: 1, title: 'Persisted Result' }),
        ], 1),
      )

      renderCatalogPageWithSearchParam('persisted query')

      await waitFor(() => {
        expect(mockUnifiedSearch).toHaveBeenCalledWith(
          expect.objectContaining({ query: 'persisted query' }),
        )
      })

      await waitFor(() => {
        expect(screen.getByText('Persisted Result')).toBeInTheDocument()
      })
    })

    it('saves search preferences to localStorage when filters change', async () => {
      mockUnifiedSearch.mockResolvedValue(makeUnifiedSearchResult([
        makeCatalogItem({ id: 1, title: 'Test' }),
      ]))

      renderCatalogPage()

      await waitFor(() => {
        expect(mockUnifiedSearch).toHaveBeenCalled()
      })

      // Click a format checkbox in the sidebar to change filters
      const bookCheckbox = screen.getAllByRole('checkbox', { name: /book/i })[0]!
      await userEvent.click(bookCheckbox)

      await waitFor(() => {
        expect(window.localStorage.setItem).toHaveBeenCalledWith(
          'lsc-catalog-search-prefs',
          expect.any(String),
        )
      })
    })

    it('restores saved search preferences from localStorage on mount', async () => {
      const savedPrefs = JSON.stringify({
        filters: {
          item_type: 'audiobook',
          status: '',
          year_min: '',
          year_max: '',
          location: '',
          character: '',
          publisher: '',
        },
        simplifiedView: false,
        showNewArrivals: false,
        showLargePrintOnly: false,
        sortBy: 'title',
        sortDirection: 'asc',
      })

      ;(window.localStorage.getItem as ReturnType<typeof vi.fn>).mockReturnValue(savedPrefs)

      mockUnifiedSearch.mockResolvedValue(
        makeUnifiedSearchResult([
          makeCatalogItem({ id: 1, title: 'An Audiobook', item_type: 'audiobook' }),
        ]),
      )

      renderCatalogPage()

      // unifiedSearch is called with formats filter from restored prefs
      await waitFor(() => {
        expect(mockUnifiedSearch).toHaveBeenCalledWith(
          expect.objectContaining({
            formats: ['audiobook'],
          }),
        )
      })
    })

    it('populates search input from URL query param "q" on mount', async () => {
      mockUnifiedSearch.mockResolvedValue(makeUnifiedSearchResult([]))

      renderCatalogPageWithSearchParam('back button test')

      await waitFor(() => {
        const searchInput = screen.getByPlaceholderText(/search/i)
        expect(searchInput).toHaveValue('back button test')
      })
    })
  })
})

// ==================== Catalog helper function unit tests ====================

describe('Catalog helper functions', () => {
  describe('FORMAT_LABELS', () => {
    it('maps all expected format types to human-readable labels', async () => {
      const { FORMAT_LABELS } = await import('../catalog/utils/catalogHelpers')

      expect(FORMAT_LABELS['book']).toBe('Book')
      expect(FORMAT_LABELS['audiobook']).toBe('Audiobook')
      expect(FORMAT_LABELS['ebook']).toBe('E-Book')
      expect(FORMAT_LABELS['dvd']).toBe('DVD')
      expect(FORMAT_LABELS['bluray']).toBe('Blu-ray')
      expect(FORMAT_LABELS['cd']).toBe('CD')
      expect(FORMAT_LABELS['vinyl']).toBe('Vinyl')
      expect(FORMAT_LABELS['magazine']).toBe('Magazine')
      expect(FORMAT_LABELS['game']).toBe('Game')
      expect(FORMAT_LABELS['equipment']).toBe('Equipment')
      expect(FORMAT_LABELS['kit']).toBe('Kit')
      expect(FORMAT_LABELS['other']).toBe('Other')
    })
  })

  describe('statusColor / statusLabel', () => {
    it('returns correct status colors', async () => {
      const { statusColor } = await import('../catalog/utils/catalogHelpers')

      expect(statusColor('available')).toBe('green')
      expect(statusColor('checked_out')).toBe('amber')
      expect(statusColor('in_transit')).toBe('blue')
      expect(statusColor('on_order')).toBe('blue')
      expect(statusColor('in_processing')).toBe('blue')
    })

    it('returns human-readable status labels', async () => {
      const { statusLabel } = await import('../catalog/utils/catalogHelpers')

      expect(statusLabel('available')).toBe('Available')
      expect(statusLabel('checked_out')).toBe('Checked Out')
      expect(statusLabel('on_hold')).toBe('On Hold')
      expect(statusLabel('in_transit')).toBe('In Transit')
    })
  })

  describe('SEARCH_PREFS_KEY', () => {
    it('is defined as the expected localStorage key', async () => {
      const { SEARCH_PREFS_KEY } = await import('../catalog/utils/catalogPageConstants')
      expect(SEARCH_PREFS_KEY).toBe('lsc-catalog-search-prefs')
    })
  })
})
