/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Shelf Dashboard Smoke Tests
 *
 * Verifies the core rendering and interaction behavior of the new
 * My Reading Shelf page and its sub-components:
 *   - ReadingShelfPage (empty state)
 *   - CurrentlyReadingHero (0 books / with books)
 *   - ProgressBar (label display, click-to-edit)
 *   - TagInput (chip rendering)
 *   - MilestoneCard (render + dismiss)
 *   - ConfettiCelebration (reduced-motion fallback)
 *   - ActivityFeed (empty state)
 *   - TagFilterBar (tag buttons + toggle)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from './utils/test-utils'
import userEvent from '@testing-library/user-event'

// ---------------------------------------------------------------------------
// Type-aligned mock data factories
// ---------------------------------------------------------------------------

function makeCatalogItem(overrides: Record<string, unknown> = {}) {
  return {
    id: 1,
    title: 'The Library at Mount Char',
    author: 'Scott Hawkins',
    item_type: 'book',
    status: 'available',
    isbn: '978-0553418620',
    publisher: 'Broadway Books',
    publication_year: 2015,
    description: null,
    subjects: null,
    cover_url: null,
    page_count: 400,
    location: null,
    barcode: null,
    created_at: '2025-01-01T00:00:00Z',
    is_large_print: false,
    images: [],
    series_name: null,
    series_number: null,
    call_number: null,
    dewey_decimal: null,
    total_checkouts: 0,
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
    ...overrides,
  }
}

function makeStatusRecord(overrides: Record<string, unknown> = {}) {
  return {
    id: 1,
    catalog_item_id: 1,
    catalog_item: makeCatalogItem(),
    status: 'currently_reading' as const,
    started_at: '2026-03-01T00:00:00Z',
    finished_at: null,
    private_notes: null,
    personal_tags: [] as string[],
    created_at: '2026-03-01T00:00:00Z',
    updated_at: '2026-03-01T00:00:00Z',
    ...overrides,
  }
}

function makeMilestone(overrides: Record<string, unknown> = {}) {
  return {
    id: 1,
    milestone_type: 'books_finished',
    milestone_key: 'first_finish',
    title: 'First Book Finished!',
    description: 'You completed your first book on the shelf.',
    earned_at: '2026-03-15T00:00:00Z',
    dismissed: false,
    ...overrides,
  }
}

// ---------------------------------------------------------------------------
// Hook mocks (module-level so vi.mock hoisting works)
// ---------------------------------------------------------------------------

const mockUseReadingStatus = vi.fn()
const mockUseReadingProgress = vi.fn()
const mockUsePatronTags = vi.fn()
const mockUseReadingMilestones = vi.fn()
const mockUseReadingActivity = vi.fn()
const mockUseShelfPreferences = vi.fn()
const mockToastSuccess = vi.fn()
const mockToastError = vi.fn()

// Auth context: always return an authenticated patron by default
vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({
    isAuthenticated: true,
    user: {
      id: 42,
      email: 'patron@l30.org',
      first_name: 'Roland',
      last_name: 'Somewhere Up North',
      full_name: 'Roland Somewhere Up North',
      role: 'PATRON',
      is_active: true,
      library_card: null,
      phone: '',
      address: null,
      email_verified: true,
      track_reading_history: true,
      created_at: '2025-01-01T00:00:00Z',
      onboarding_completed_at: null,
      onboarding_skipped: false,
      home_branch_id: null,
      profile_image: null,
      preferred_language: 'en',
    },
    token: 'mock-token',
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
    register: vi.fn(),
    updateProfile: vi.fn(),
    refreshUser: vi.fn(),
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
}))

vi.mock('../hooks/useReadingStatus', () => ({
  useReadingStatus: (...args: unknown[]) => mockUseReadingStatus(...args),
}))

vi.mock('../hooks/useReadingProgress', () => ({
  useReadingProgress: (...args: unknown[]) => mockUseReadingProgress(...args),
}))

vi.mock('../hooks/usePatronTags', () => ({
  usePatronTags: () => mockUsePatronTags(),
}))

vi.mock('../hooks/useReadingMilestones', () => ({
  useReadingMilestones: () => mockUseReadingMilestones(),
}))

vi.mock('../hooks/useReadingActivity', () => ({
  useReadingActivity: (...args: unknown[]) => mockUseReadingActivity(...args),
}))

vi.mock('../hooks/useShelfPreferences', () => ({
  useShelfPreferences: () => mockUseShelfPreferences(),
}))

vi.mock('react-hot-toast', () => ({
  default: {
    success: (...args: unknown[]) => mockToastSuccess(...args),
    error: (...args: unknown[]) => mockToastError(...args),
  },
}))

vi.mock('../features/accessibility/hooks/useUnifiedAccessibility', () => ({
  useUnifiedAccessibility: () => ({
    announceToScreenReader: vi.fn(),
    quietMode: false,
    focusMode: false,
    simplifiedView: false,
    reduceMotion: false,
    showImages: true,
    preferPagination: false,
    noFOMO: false,
  }),
}))

// Stub heavy child components not under test to keep renders fast
vi.mock('../components/shelf/StatsBar', () => ({
  default: () => <div data-testid="stats-bar">StatsBar</div>,
}))
vi.mock('../components/shelf/ExportButton', () => ({
  default: () => <div data-testid="export-button">Export</div>,
}))
vi.mock('../components/shelf/ShelfTabs', () => ({
  default: () => <div data-testid="shelf-tabs">ShelfTabs</div>,
}))
vi.mock('../components/shelf/QuickLogFAB', () => ({
  default: ({ onClick }: { onClick: () => void }) => (
    <button data-testid="quick-log-fab" onClick={onClick}>QuickLog</button>
  ),
}))
vi.mock('../components/shelf/QuickLogSheet', () => ({
  default: () => null,
}))
vi.mock('../components/shelf/TagManager', () => ({
  default: () => null,
}))
vi.mock('../components/shelf/ShelfPreferences', () => ({
  default: () => <div data-testid="shelf-prefs">Preferences</div>,
}))

// Mock setReadingStatus API (used by CurrentlyReadingHero tag handler)
vi.mock('../api/domains/content/reading-status-api', () => ({
  setReadingStatus: vi.fn().mockResolvedValue({}),
}))

// ---------------------------------------------------------------------------
// Default hook return values (happy-path baseline)
// ---------------------------------------------------------------------------

function setDefaults() {
  mockUseReadingStatus.mockReturnValue({
    currentStatus: undefined,
    allStatuses: [],
    stats: {
      want_to_read: 0,
      currently_reading: 0,
      on_hold: 0,
      finished: 0,
      did_not_finish: 0,
      finished_this_year: 0,
    },
    isUpdating: false,
    handleSetStatus: vi.fn(),
    handleRemove: vi.fn(),
    quickAdd: vi.fn(),
    SHELF_LABELS: {
      want_to_read: 'Want to Read',
      currently_reading: 'Currently Reading',
      on_hold: 'On Hold',
      finished: 'Finished',
      did_not_finish: 'Did Not Finish',
    },
  })

  mockUseReadingProgress.mockReturnValue({
    allLatest: [],
    history: [],
    paceStats: null,
    progressMap: new Map(),
    isLogging: false,
    handleLogProgress: vi.fn(),
  })

  mockUsePatronTags.mockReturnValue({
    allTags: [],
    isLoading: false,
    activeFilters: [],
    toggleFilter: vi.fn(),
    clearFilters: vi.fn(),
    handleRename: vi.fn(),
    handleDelete: vi.fn(),
  })

  mockUseReadingMilestones.mockReturnValue({
    milestones: [],
    isLoading: false,
    justEarned: null,
    handleDismiss: vi.fn(),
    triggerCelebration: vi.fn(),
  })

  mockUseReadingActivity.mockReturnValue({
    activities: [],
    total: 0,
    isLoading: false,
  })

  mockUseShelfPreferences.mockReturnValue({
    preferences: { show_reading_activity: false, show_pace_stats: false },
    handleUpdate: vi.fn(),
  })
}

beforeEach(() => {
  vi.clearAllMocks()
  setDefaults()
})

// ===========================================================================
// Lazy imports — loaded after vi.mock calls are hoisted
// ===========================================================================

// We use dynamic imports inside each describe so the mocked modules are
// resolved correctly.  To keep the file readable, helper functions perform the
// imports at call-time.

async function importReadingShelfPage() {
  const mod = await import('../pages/ReadingShelfPage')
  return mod.default
}

async function importCurrentlyReadingHero() {
  const mod = await import('../components/shelf/CurrentlyReadingHero')
  return mod.default
}

async function importProgressBar() {
  const mod = await import('../components/shelf/ProgressBar')
  return mod.default
}

async function importTagInput() {
  const mod = await import('../components/shelf/TagInput')
  return mod.default
}

async function importMilestoneCard() {
  const mod = await import('../components/shelf/MilestoneCard')
  return mod.default
}

async function importConfettiCelebration() {
  const mod = await import('../components/shelf/ConfettiCelebration')
  return mod.default
}

async function importActivityFeed() {
  const mod = await import('../components/shelf/ActivityFeed')
  return mod.default
}

async function importTagFilterBar() {
  const mod = await import('../components/shelf/TagFilterBar')
  return mod.default
}

// ===========================================================================
// 1. ReadingShelfPage — empty state for new patron
// ===========================================================================

describe('ReadingShelfPage', () => {
  it('renders "Start your reading journey" when allStatuses is empty', async () => {
    const ReadingShelfPage = await importReadingShelfPage()
    render(<ReadingShelfPage />)

    expect(screen.getByText('Start your reading journey')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /browse the catalog/i })).toHaveAttribute(
      'href',
      '/catalog',
    )
  })
})

// ===========================================================================
// 2 & 3. CurrentlyReadingHero — empty and populated
// ===========================================================================

describe('CurrentlyReadingHero', () => {
  it('shows "Nothing on the go" when there are 0 currently-reading books', async () => {
    // allStatuses already empty from defaults
    const CurrentlyReadingHero = await importCurrentlyReadingHero()
    render(<CurrentlyReadingHero />)

    expect(screen.getByText(/nothing on the go/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /browse catalog/i })).toHaveAttribute(
      'href',
      '/catalog',
    )
  })

  it('renders book cards with titles when books are present', async () => {
    const entry1 = makeStatusRecord({
      id: 1,
      catalog_item_id: 1,
      catalog_item: makeCatalogItem({ id: 1, title: 'The Library at Mount Char' }),
      personal_tags: ['fiction'],
    })
    const entry2 = makeStatusRecord({
      id: 2,
      catalog_item_id: 2,
      catalog_item: makeCatalogItem({ id: 2, title: 'Piranesi', author: 'Susanna Clarke' }),
      personal_tags: [],
    })

    mockUseReadingStatus.mockReturnValue({
      ...mockUseReadingStatus(),
      allStatuses: [entry1, entry2],
    })

    mockUseReadingProgress.mockReturnValue({
      ...mockUseReadingProgress(),
      progressMap: new Map([
        [1, { catalog_item_id: 1, percent: 45, current_page: 180, total_pages: 400 }],
      ]),
    })

    const CurrentlyReadingHero = await importCurrentlyReadingHero()
    render(<CurrentlyReadingHero allTags={['fiction']} />)

    expect(screen.getByText('The Library at Mount Char')).toBeInTheDocument()
    expect(screen.getByText('Piranesi')).toBeInTheDocument()
    expect(screen.getByText('Susanna Clarke')).toBeInTheDocument()
  })
})

// ===========================================================================
// 4. ProgressBar — displays correct label
// ===========================================================================

describe('ProgressBar', () => {
  it('shows page/percent label when currentPage and totalPages are provided', async () => {
    const ProgressBar = await importProgressBar()
    render(
      <ProgressBar percent={45} currentPage={180} totalPages={400} onPageSubmit={vi.fn()} />,
    )

    expect(
      screen.getByLabelText(/reading progress.*pg 180 \/ 400 \(45%\)/i),
    ).toBeInTheDocument()
  })

  it('shows approximate percent when only percent is provided', async () => {
    const ProgressBar = await importProgressBar()
    render(<ProgressBar percent={72} onPageSubmit={vi.fn()} />)

    expect(screen.getByLabelText(/~72%/)).toBeInTheDocument()
  })

  it('shows first-page prompt when percent is 0', async () => {
    const ProgressBar = await importProgressBar()
    render(<ProgressBar percent={0} onPageSubmit={vi.fn()} />)

    expect(screen.getByLabelText(/tap to log your first page/i)).toBeInTheDocument()
  })

  // =========================================================================
  // 5. ProgressBar click opens page input
  // =========================================================================

  it('opens inline page editor when clicked', async () => {
    const user = userEvent.setup()
    const ProgressBar = await importProgressBar()
    const onPageSubmit = vi.fn()

    render(
      <ProgressBar percent={45} currentPage={180} totalPages={400} onPageSubmit={onPageSubmit} />,
    )

    // Click the progress bar button
    await user.click(screen.getByRole('button'))

    // The editor form should now be visible
    expect(screen.getByLabelText(/current page number/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /save/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
  })
})

// ===========================================================================
// 6. TagInput — chips render with remove buttons
// ===========================================================================

describe('TagInput', () => {
  it('shows existing tags as colored chips', async () => {
    const TagInput = await importTagInput()
    const onChange = vi.fn()

    render(
      <TagInput tags={['fiction', 'sci-fi', 'favorite']} allTags={['fiction', 'sci-fi', 'favorite', 'classics']} onChange={onChange} />,
    )

    expect(screen.getByText('fiction')).toBeInTheDocument()
    expect(screen.getByText('sci-fi')).toBeInTheDocument()
    expect(screen.getByText('favorite')).toBeInTheDocument()

    // Each chip has a remove button
    expect(screen.getByRole('button', { name: /remove tag fiction/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /remove tag sci-fi/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /remove tag favorite/i })).toBeInTheDocument()
  })
})

// ===========================================================================
// 7. MilestoneCard — renders title, description, dismiss button
// ===========================================================================

describe('MilestoneCard', () => {
  it('renders title, description, and dismiss button', async () => {
    const MilestoneCard = await importMilestoneCard()
    const onDismiss = vi.fn()
    const milestone = makeMilestone()

    render(<MilestoneCard milestone={milestone} onDismiss={onDismiss} />)

    expect(screen.getByText('First Book Finished!')).toBeInTheDocument()
    expect(
      screen.getByText('You completed your first book on the shelf.'),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /dismiss milestone.*first book finished/i }),
    ).toBeInTheDocument()
  })

  it('hides dismiss button when onDismiss is not provided', async () => {
    const MilestoneCard = await importMilestoneCard()
    const milestone = makeMilestone()

    render(<MilestoneCard milestone={milestone} />)

    expect(screen.getByText('First Book Finished!')).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: /dismiss/i }),
    ).not.toBeInTheDocument()
  })
})

// ===========================================================================
// 8. ConfettiCelebration — reduced motion shows toast instead of animation
// ===========================================================================

describe('ConfettiCelebration', () => {
  it('shows toast instead of animation when prefers-reduced-motion is set', async () => {
    // Override matchMedia to report reduced motion
    const matchMediaSpy = vi.spyOn(window, 'matchMedia')
    matchMediaSpy.mockImplementation((query: string) => ({
      matches: query === '(prefers-reduced-motion: reduce)',
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }))

    const ConfettiCelebration = await importConfettiCelebration()
    const milestone = makeMilestone({ title: 'Bookworm Badge' })

    render(<ConfettiCelebration milestone={milestone} />)

    // Should fire a toast, not render confetti
    // The component triggers toast.success inside a useEffect, so we need to wait
    await vi.waitFor(() => {
      expect(mockToastSuccess).toHaveBeenCalledWith(
        expect.stringContaining('Bookworm Badge'),
      )
    })

    // The confetti container should NOT be in the document
    expect(screen.queryByLabelText(/celebration/i)).not.toBeInTheDocument()

    matchMediaSpy.mockRestore()
  })
})

// ===========================================================================
// 9. ActivityFeed — empty state
// ===========================================================================

describe('ActivityFeed', () => {
  it('shows "Your reading activity will appear here" when empty', async () => {
    const ActivityFeed = await importActivityFeed()
    render(<ActivityFeed />)

    expect(
      screen.getByText(/your reading activity will appear here/i),
    ).toBeInTheDocument()
  })
})

// ===========================================================================
// 10. TagFilterBar — renders tag buttons with toggle behavior
// ===========================================================================

describe('TagFilterBar', () => {
  it('renders tag buttons and supports toggle', async () => {
    const user = userEvent.setup()
    const onToggleFilter = vi.fn()
    const onClearFilters = vi.fn()

    const TagFilterBar = await importTagFilterBar()

    render(
      <TagFilterBar
        allTags={['fiction', 'non-fiction', 'mystery']}
        activeFilters={['fiction']}
        onToggleFilter={onToggleFilter}
        onClearFilters={onClearFilters}
      />,
    )

    // All tag buttons present
    const fictionBtn = screen.getByRole('button', { name: 'fiction' })
    const nonFictionBtn = screen.getByRole('button', { name: 'non-fiction' })
    const mysteryBtn = screen.getByRole('button', { name: 'mystery' })

    expect(fictionBtn).toBeInTheDocument()
    expect(nonFictionBtn).toBeInTheDocument()
    expect(mysteryBtn).toBeInTheDocument()

    // Active filter has aria-pressed=true
    expect(fictionBtn).toHaveAttribute('aria-pressed', 'true')
    expect(nonFictionBtn).toHaveAttribute('aria-pressed', 'false')
    expect(mysteryBtn).toHaveAttribute('aria-pressed', 'false')

    // Clicking a tag fires onToggleFilter
    await user.click(mysteryBtn)
    expect(onToggleFilter).toHaveBeenCalledWith('mystery')

    // Clear button is present because there is an active filter
    const clearBtn = screen.getByRole('button', { name: /clear/i })
    await user.click(clearBtn)
    expect(onClearFilters).toHaveBeenCalled()
  })

  it('returns null when allTags is empty', async () => {
    const TagFilterBar = await importTagFilterBar()

    const { container } = render(
      <TagFilterBar
        allTags={[]}
        activeFilters={[]}
        onToggleFilter={vi.fn()}
        onClearFilters={vi.fn()}
      />,
    )

    expect(container.innerHTML).toBe('')
  })
})
