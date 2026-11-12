/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useMemo, useEffect, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { BookOpen, BookMarked, Info, Trophy, Filter, X, Flame } from 'lucide-react'
import StandardPageLayout from '@/components/StandardPageLayout'
import { getReadingPrograms, type ReadingProgramFilters } from '@/api/api'
import { useAuth } from '@/contexts/AuthContext'
import ProgramCard from '@/components/ProgramCard'
import ProgramFilters, { type SortOption } from '@/components/ProgramFilters'
import ProgramRegistrationModal from '@/components/ProgramRegistrationModal'
import ProgramDetailModal from '@/components/ProgramDetailModal'
import { getMyRegistrations, type ReadingProgram, type ReadingRegistration } from '@/api/api'
import { ProgramCardSkeletonGrid } from '@/components/skeletons/ProgramCardSkeleton'
import { useTranslation} from '@/i18n'
import LoginPromptModal from '@/components/LoginPromptModal'

export default function ReadingProgramsPage(): React.ReactElement {
  const { t } = useTranslation()
  const { token, isAuthenticated } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const [filters, setFilters] = useState<ReadingProgramFilters>({ active_only: true })
  const [searchQuery, setSearchQuery] = useState(() => searchParams.get('q') ?? '')
  const [debouncedQuery, setDebouncedQuery] = useState(() => searchParams.get('q') ?? '')
  const [sortBy, setSortBy] = useState<SortOption>('popular')
  const [selectedProgram, setSelectedProgram] = useState<ReadingProgram | null>(null)
  const [detailProgram, setDetailProgram] = useState<ReadingProgram | null>(null)
  const [showMobileFilters, setShowMobileFilters] = useState(false)
  const [showLoginPrompt, setShowLoginPrompt] = useState(false)
  const [infoBannerDismissed, setInfoBannerDismissed] = useState(
    () => localStorage.getItem('programs-info-dismissed') === '1'
  )
  const [selectedAgeGroup, setSelectedAgeGroup] = useState<string | null>(() => searchParams.get('age') ?? null)

  // Close mobile filter drawer on Escape
  useEffect(() => {
    if (!showMobileFilters) return
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setShowMobileFilters(false)
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [showMobileFilters])

  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(searchQuery), 200)
    return () => clearTimeout(timer)
  }, [searchQuery])

  // Sync debounced query + age group to URL
  useEffect(() => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      if (debouncedQuery) next.set('q', debouncedQuery); else next.delete('q')
      if (selectedAgeGroup) next.set('age', selectedAgeGroup); else next.delete('age')
      return next
    }, { replace: true })
  }, [debouncedQuery, selectedAgeGroup, setSearchParams])

  // Fetch programs
  const { data: programsData, isLoading: isLoadingPrograms, error: programsError } = useQuery({
    queryKey: ['reading-programs', filters],
    queryFn: () => getReadingPrograms(filters),
  })

  // Fetch user registrations if authenticated
  const { data: myRegistrations = [] } = useQuery({
    queryKey: ['my-registrations'],
    queryFn: () => (token ? getMyRegistrations(token) : Promise.resolve([])),
    enabled: isAuthenticated && !!token,
  })

  // Create a map for quick registration lookup
  const registrationMap = useMemo(() => {
    const map = new Map<number, ReadingRegistration>()
    myRegistrations.forEach((reg) => map.set(reg.program_id, reg))
    return map
  }, [myRegistrations])

  const registeredProgramIds = useMemo(
    () => new Set((myRegistrations || []).map((reg) => reg.program_id)),
    [myRegistrations]
  )

  // Filter and sort programs
  const programs = useMemo(() => {
    let filtered = Array.isArray(programsData) ? programsData.map((program) => ({
      ...program,
      isUserRegistered: registeredProgramIds.has(program.id),
    })) : []

    // Apply search filter
    if (debouncedQuery.trim()) {
      const query = debouncedQuery.toLowerCase()
      filtered = filtered.filter((p) => p.name.toLowerCase().includes(query) || p.description?.toLowerCase().includes(query))
    }

    // Apply age group quick-filter
    if (selectedAgeGroup) {
      filtered = filtered.filter((p) => {
        const ag = (p.age_group || '').toLowerCase()
        if (selectedAgeGroup === 'children') return ag.includes('child') || ag.includes('kid') || (p.target_age_max !== null && p.target_age_max <= 12)
        if (selectedAgeGroup === 'teen') return ag.includes('teen') || (p.target_age_min !== null && p.target_age_min >= 13 && p.target_age_max !== null && p.target_age_max <= 18)
        if (selectedAgeGroup === 'adult') return ag.includes('adult') || (p.target_age_min !== null && p.target_age_min >= 18)
        if (selectedAgeGroup === 'family') return ag.includes('family') || ag.includes('all')
        return true
      })
    }

    // Apply sorting
    const safeDate = (d: string | null | undefined) => d ? new Date(d).getTime() : Infinity
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'popular':
          return b.registration_count - a.registration_count
        case 'newest':
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        case 'ending_soon':
          return safeDate(a.end_date) - safeDate(b.end_date)
        case 'alphabetical':
          return a.name.localeCompare(b.name)
        default:
          return 0
      }
    })

    return filtered
  }, [programsData, registeredProgramIds, debouncedQuery, sortBy, selectedAgeGroup])

  const activePrograms = programs.filter((p) => !p.isUserRegistered)
  const joinedPrograms = programs.filter((p) => p.isUserRegistered)

  // Calculate user stats
  const userStats = useMemo(() => {
    const totalBooks = myRegistrations.reduce((sum, reg) => sum + reg.total_books, 0)
    const totalMinutes = myRegistrations.reduce((sum, reg) => sum + reg.total_minutes, 0)
    const totalPrograms = myRegistrations.length
    const avgProgress = totalPrograms > 0
      ? Math.round(myRegistrations.reduce((sum, reg) => sum + reg.progress_percentage, 0) / totalPrograms)
      : 0
    return { totalBooks, totalMinutes, totalPrograms, avgProgress }
  }, [myRegistrations])

  // Find featured program (most popular active one)
  const featuredProgram = useMemo(() => {
    const active = activePrograms.filter((p) => p.is_active && p.registration_count >= 5)
    return active.sort((a, b) => b.registration_count - a.registration_count)[0]
  }, [activePrograms])

  const openLoginPrompt = useCallback(() => setShowLoginPrompt(true), [])

  return (
    <StandardPageLayout
      title="Reading Programs"
      subtitle={t('readingPrograms.joinReadingChallengesTrackYour')}
      icon={BookMarked}
      isLoading={isLoadingPrograms}
    >
      {/* User stats (if logged in and has registrations) */}
      {isAuthenticated && userStats.totalPrograms > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-3 text-center border border-lsc-border dark:border-earth-700">
            <div className="text-2xl font-bold text-lsc-rose dark:text-lsc-rose-light">{userStats.totalPrograms}</div>
            <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Programs</div>
          </div>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-3 text-center border border-lsc-border dark:border-earth-700">
            <div className="text-2xl font-bold text-lsc-rose dark:text-lsc-rose-light">{userStats.totalBooks}</div>
            <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Books Read</div>
          </div>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-3 text-center border border-lsc-border dark:border-earth-700">
            <div className="text-2xl font-bold text-lsc-rose dark:text-lsc-rose-light">{userStats.totalMinutes}</div>
            <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Minutes</div>
          </div>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-3 text-center border border-lsc-border dark:border-earth-700">
            <div className="text-2xl font-bold text-lsc-rose dark:text-lsc-rose-light">{userStats.avgProgress}%</div>
            <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Avg Progress</div>
          </div>
        </div>
      )}

      {/* Info banner - Dismissable for repeat visitors */}
      {!infoBannerDismissed && (
        <div className="bg-lsc-cream dark:bg-lsc-brown/30 border border-lsc-border dark:border-lsc-brown rounded-xl p-4 flex gap-3">
          <Info className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" aria-hidden="true" />
          <div className="flex-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            <p className="font-medium text-lsc-dark dark:text-lsc-cream mb-1">How it works:</p>
            <ul className="space-y-1 text-xs list-disc list-inside">
              <li>{t('readingPrograms.findAProgramThatMatches')}</li>
              <li>{t('readingPrograms.joinToStartTrackingYour')}</li>
              <li>{t('readingPrograms.logYourReadingEntriesTo')}</li>
              <li>{t('readingPrograms.compareYourProgressWithOther')}</li>
            </ul>
          </div>
          <button
            onClick={() => {
              setInfoBannerDismissed(true)
              localStorage.setItem('programs-info-dismissed', '1')
            }}
            className="flex-shrink-0 p-1 hover:bg-lsc-border dark:hover:bg-lsc-brown rounded-full transition-colors self-start"
            aria-label={t('aria.readingPrograms.dismissInfoBanner')}
          >
            <X className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/50" />
          </button>
        </div>
      )}

      {/* Featured program */}
      {featuredProgram && !joinedPrograms.some((p) => p.id === featuredProgram.id) && (
        <section aria-labelledby="featured-programs-heading" className="space-y-3">
          <div className="flex items-center gap-2">
            <Flame className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
            <h2 id="featured-programs-heading" className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
              Featured Program
            </h2>
          </div>
          <ProgramCard
            program={featuredProgram}
            isRegistered={false}
            onRegister={
              isAuthenticated
                ? setSelectedProgram
                : openLoginPrompt
            }
            onClick={() => setDetailProgram(featuredProgram)}
            isFeatured={true}
          />
        </section>
      )}

      {/* Mobile filter toggle */}
      <div className="lg:hidden">
        <button
          onClick={() => setShowMobileFilters(true)}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl text-sm font-medium text-lsc-dark dark:text-lsc-cream"
        >
          <Filter className="w-4 h-4" aria-hidden="true" />
          Filters & Search
          {(filters.program_type || searchQuery || selectedAgeGroup) && (
            <span className="ml-1 px-1.5 py-0.5 bg-lsc-rose text-white text-xs rounded-full">
              {[filters.program_type, searchQuery, selectedAgeGroup].filter(Boolean).length}
            </span>
          )}
        </button>
      </div>

      {/* Main content */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sidebar filters - Desktop */}
        <aside className="hidden lg:block lg:col-span-1" aria-label={t('aria.readingPrograms.programFilters')}>
          <div className="sticky top-4 bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
            <ProgramFilters
              filters={filters}
              onChange={setFilters}
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
              sortBy={sortBy}
              onSortChange={setSortBy}
            />
          </div>
        </aside>

        {/* Programs grid */}
        <div className="lg:col-span-3">
          <div className="space-y-8">
            {/* Joined programs section */}
            {joinedPrograms.length > 0 && (
              <section aria-labelledby="your-programs-heading">
                <div className="flex items-center gap-2 mb-4">
                  <Trophy className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
                  <h2 id="your-programs-heading" className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                    Your Programs ({joinedPrograms.length})
                  </h2>
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  {joinedPrograms.map((program) => (
                    <div key={program.id} className="relative">
                      <ProgramCard
                        program={program}
                        isRegistered={true}
                        {...(registrationMap.get(program.id) ? { registration: registrationMap.get(program.id)! } : {})}
                        onRegister={() => {}}
                        onClick={() => setDetailProgram(program)}
                      />
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Available programs section */}
            <section aria-labelledby="available-programs-heading">
              <div className="flex items-center justify-between gap-2 mb-4">
                <div className="flex items-center gap-2">
                  <BookOpen className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
                  <h2 id="available-programs-heading" className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                    Available Programs {activePrograms.length > 0 && `(${activePrograms.length})`}
                  </h2>
                </div>
                {debouncedQuery && (
                  <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    Searching for "{debouncedQuery}"
                  </span>
                )}
              </div>

              {/* Age group quick-filter chips */}
              <div className="flex flex-wrap gap-2 mb-4" role="group" aria-label={t('readingPrograms.filterByAgeGroup')}>
                {[
                  { value: null, label: 'All Ages' },
                  { value: 'children', label: 'Children' },
                  { value: 'teen', label: 'Teens' },
                  { value: 'adult', label: 'Adults' },
                  { value: 'family', label: 'Families' },
                ].map((chip) => (
                  <button
                    key={chip.label}
                    onClick={() => setSelectedAgeGroup(chip.value)}
                    className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                      selectedAgeGroup === chip.value
                        ? 'bg-lsc-rose text-white'
                        : 'bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream/80 hover:bg-lsc-border dark:hover:bg-lsc-brown/80'
                    }`}
                  >
                    {chip.label}
                  </button>
                ))}
              </div>

              <div aria-live="polite" aria-busy={isLoadingPrograms}>
              {isLoadingPrograms ? (
                <div role="status" className="space-y-4">
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Loading programs...</p>
                  <ProgramCardSkeletonGrid count={4} />
                </div>
              ) : programsError ? (
                <div className="text-center text-status-danger-700 dark:text-status-danger-300 py-12">
                  <p className="mb-2">{t('readingPrograms.unableToLoadReadingPrograms')}</p>
                  <p className="text-sm">{t('readingPrograms.pleaseRefreshThePageOr')}</p>
                </div>
              ) : activePrograms.length > 0 ? (
                <div className="grid gap-4 md:grid-cols-2 motion-safe:animate-in motion-safe:fade-in motion-safe:duration-300">
                  {activePrograms
                    .filter((p) => p.id !== featuredProgram?.id) // Don't show featured twice
                    .map((program) => (
                      <ProgramCard
                        key={program.id}
                        program={program}
                        isRegistered={false}
                        onRegister={
                          isAuthenticated
                            ? setSelectedProgram
                            : openLoginPrompt
                        }
                        onClick={() => setDetailProgram(program)}
                      />
                    ))}
                </div>
              ) : (
                <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
                  <BookOpen className="w-16 h-16 mx-auto mb-4 opacity-50" aria-hidden="true" />
                  <p className="mb-2">
                    {debouncedQuery
                      ? `No programs found matching "${debouncedQuery}"`
                      : 'No programs available matching your filters.'}
                  </p>
                  <button
                    onClick={() => {
                      setFilters({ active_only: true })
                      setSearchQuery('')
                      setSelectedAgeGroup(null)
                    }}
                    className="mt-4 text-lsc-rose dark:text-lsc-rose-light hover:text-lsc-rose/80 dark:hover:text-lsc-rose/80 font-medium"
                  >
                    Reset filters
                  </button>
                </div>
              )}
              </div>
            </section>
          </div>
        </div>
      </div>

      {/* Mobile filter drawer */}
      {showMobileFilters && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 bg-black/50"
            onClick={() => setShowMobileFilters(false)}
            aria-hidden="true"
          />
          <section aria-labelledby="mobile-filters-heading" className="absolute right-0 top-0 bottom-0 w-full max-w-sm bg-lsc-white dark:bg-earth-800 shadow-lg overflow-y-auto">
            <div className="sticky top-0 bg-lsc-white dark:bg-earth-800 border-b border-lsc-border dark:border-earth-700 p-4 flex items-center justify-between">
              <h2 id="mobile-filters-heading" className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                Filters & Search
              </h2>
              <button
                onClick={() => setShowMobileFilters(false)}
                className="p-2 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-full transition-colors"
                aria-label={t('aria.readingPrograms.closeFilters')}
              >
                <X className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
              </button>
            </div>
            <div className="p-4">
              <ProgramFilters
                filters={filters}
                onChange={(f) => {
                  setFilters(f)
                }}
                searchQuery={searchQuery}
                onSearchChange={setSearchQuery}
                sortBy={sortBy}
                onSortChange={setSortBy}
              />
              <button
                onClick={() => setShowMobileFilters(false)}
                className="w-full mt-6 px-4 py-3 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-semibold transition-colors"
              >
                Apply Filters
              </button>
            </div>
          </section>
        </div>
      )}

      {/* Registration modal */}
      {selectedProgram && (
        <ProgramRegistrationModal
          program={selectedProgram}
          onClose={() => setSelectedProgram(null)}
        />
      )}

      {/* Detail modal */}
      {detailProgram && (
        <ProgramDetailModal
          program={detailProgram}
          {...(registrationMap.get(detailProgram.id) ? { registration: registrationMap.get(detailProgram.id)! } : {})}
          onClose={() => setDetailProgram(null)}
          onRegister={(program) => {
            setDetailProgram(null)
            if (isAuthenticated) {
              setSelectedProgram(program)
            } else {
              setShowLoginPrompt(true)
            }
          }}
          isRegistered={registeredProgramIds.has(detailProgram.id)}
        />
      )}
      {showLoginPrompt && <LoginPromptModal onClose={() => setShowLoginPrompt(false)} />}
    </StandardPageLayout>
  )
}
