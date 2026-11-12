/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState, useCallback } from 'react'
import {
  listBranches,
  getCurrentPosition,
  sortBranchesByDistance,
  formatBranchAddress,
  getBranchTypeLabel,
  getBranchHours,
  isBranchOpen,
  Branch,
  BranchHours,
  BranchWithDistance,
  BranchType,
} from '@/api/branch-api'
import { useTranslation} from '@/i18n'

interface BranchFinderProps {
  /** Filter to specific branch types */
  branchTypes?: BranchType[]
  /** Show only active/open branches */
  activeOnly?: boolean
  /** Callback when a branch is selected */
  onSelectBranch?: (branch: Branch) => void
  /** Show bookmobile-specific features */
  showBookmobileFeatures?: boolean
}

export function BranchFinder({
  branchTypes,
  activeOnly = true,
  onSelectBranch,
  showBookmobileFeatures = false,
}: BranchFinderProps) {
  const { t } = useTranslation()
  const [branches, setBranches] = useState<BranchWithDistance[]>([])
  const [filteredBranches, setFilteredBranches] = useState<BranchWithDistance[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [userLocation, setUserLocation] = useState<{ lat: number; lon: number } | null>(null)
  const [locationError, setLocationError] = useState<string | null>(null)
  const [locationLoading, setLocationLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedType, setSelectedType] = useState<BranchType | 'all'>('all')
  const [branchHours, setBranchHours] = useState<Record<number, BranchHours[]>>({})

  // Load branches
  useEffect(() => {
    async function loadBranches() {
      try {
        setLoading(true)
        const data = await listBranches({ active_only: activeOnly })

        // Filter by branch type if specified
        let filtered = data
        if (branchTypes && branchTypes.length > 0) {
          filtered = data.filter((b) => branchTypes.includes(b.branch_type))
        }

        // Add distance property (null for now)
        const withDistance = filtered.map((b) => ({ ...b, distance_miles: null }))
        setBranches(withDistance)
        setFilteredBranches(withDistance)
      } catch (_err) {
        setError(_err instanceof Error ? _err.message : t('branches.couldNotLoadLocations', 'Could not load library locations. Please try refreshing the page.'))
      } finally {
        setLoading(false)
      }
    }

    loadBranches()
  }, [branchTypes, activeOnly])

  // Fetch hours for each branch so cards can show today's hours and open/closed.
  // Branch list endpoint does not include hours, so we fetch per branch in parallel.
  useEffect(() => {
    let cancelled = false
    if (branches.length === 0) {
      setBranchHours({})
      return
    }

    async function loadAllHours() {
      const entries = await Promise.all(
        branches.map(async (b) => {
          try {
            const hours = await getBranchHours(b.id)
            return [b.id, hours] as const
          } catch {
            return [b.id, [] as BranchHours[]] as const
          }
        })
      )
      if (cancelled) return
      setBranchHours(Object.fromEntries(entries))
    }

    loadAllHours()
    return () => {
      cancelled = true
    }
  }, [branches])

  // Apply filters
  const applyFilters = useCallback(
    (branchList: BranchWithDistance[], query: string, type: BranchType | 'all') => {
      let result = branchList

      // Filter by search query
      if (query.trim()) {
        const lowerQuery = query.toLowerCase()
        result = result.filter(
          (b) =>
            b.name.toLowerCase().includes(lowerQuery) ||
            b.city?.toLowerCase().includes(lowerQuery) ||
            b.zip_code?.includes(query) ||
            b.address_line1?.toLowerCase().includes(lowerQuery)
        )
      }

      // Filter by type
      if (type !== 'all') {
        result = result.filter((b) => b.branch_type === type)
      }

      setFilteredBranches(result)
    },
    []
  )

  // Get user location
  const findNearby = useCallback(async () => {
    setLocationLoading(true)
    setLocationError(null)

    try {
      const position = await getCurrentPosition()
      const { latitude, longitude } = position.coords
      setUserLocation({ lat: latitude, lon: longitude })

      // Sort branches by distance
      const sorted = sortBranchesByDistance(branches, latitude, longitude)
      setBranches(sorted)
      applyFilters(sorted, searchQuery, selectedType)
    } catch (_err) {
      if (_err instanceof GeolocationPositionError) {
        switch (_err.code) {
          case _err.PERMISSION_DENIED:
            setLocationError(t('branches.locationPermissionDenied', 'Location permission denied. Please enable location access in your browser settings.'))
            break
          case _err.POSITION_UNAVAILABLE:
            setLocationError(t('branches.locationUnavailable', 'Location information unavailable.'))
            break
          case _err.TIMEOUT:
            setLocationError(t('branches.locationTimedOut', 'Location request timed out. Please try again.'))
            break
        }
      } else {
        setLocationError(_err instanceof Error ? _err.message : t('branches.failedToGetLocation', 'Failed to get location'))
      }
    } finally {
      setLocationLoading(false)
    }
  }, [branches, searchQuery, selectedType, applyFilters])

  // Handle search
  const handleSearch = useCallback(
    (query: string) => {
      setSearchQuery(query)
      applyFilters(branches, query, selectedType)
    },
    [branches, selectedType, applyFilters]
  )

  // Handle type filter
  const handleTypeFilter = useCallback(
    (type: BranchType | 'all') => {
      setSelectedType(type)
      applyFilters(branches, searchQuery, type)
    },
    [branches, searchQuery, applyFilters]
  )

  // Format distance
  const formatDistance = (miles: number | null) => {
    if (miles === null) return null
    if (miles < 0.1) return 'Less than 0.1 mi'
    if (miles < 10) return `${miles.toFixed(1)} mi`
    return `${Math.round(miles)} mi`
  }

  // Format a HH:MM time string as a friendly 12-hour label (e.g. 9 AM, 5:30 PM)
  const formatTime = (time: string) => {
    const [h, m] = time.split(':').map(Number)
    const hour = h ?? 0
    const min = m ?? 0
    const period = hour >= 12 ? 'PM' : 'AM'
    const h12 = hour % 12 || 12
    return min === 0 ? `${h12} ${period}` : `${h12}:${String(min).padStart(2, '0')} ${period}`
  }

  // Today's hours label for a branch, using the same capitalized day names as isBranchOpen
  const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
  const getTodayHoursLabel = (hours: BranchHours[] | undefined) => {
    if (!hours || hours.length === 0) return null
    const todayName = dayNames[new Date().getDay()]
    const today = hours.find((h) => h.day_of_week === todayName)
    if (!today || today.is_closed) return t('home.hours.closed')
    if (!today.open_time || !today.close_time) return null
    return `${formatTime(today.open_time)} - ${formatTime(today.close_time)}`
  }

  // Get directions URL
  const getDirectionsUrl = (branch: Branch) => {
    if (branch.latitude && branch.longitude) {
      return `https://www.google.com/maps/dir/?api=1&destination=${branch.latitude},${branch.longitude}`
    }
    const address = formatBranchAddress(branch)
    return `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(address)}`
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8" role="status" aria-live="polite" aria-label={t('aria.branchFinder.loadingLibraryLocations')}>
        <div className="motion-safe:animate-spin motion-reduce:animate-none rounded-full h-8 w-8 border-b-2 border-lsc-rose" aria-hidden="true" />
        <span className="ml-3 text-lsc-dark/70 dark:text-lsc-cream/70">{t('branches.loadingLocations', 'Loading locations...')}</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-4 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-lg">
        <p className="text-status-danger-700 dark:text-status-danger-300">{error}</p>
        <button
          onClick={() => window.location.reload()}
          className="mt-2 text-status-danger-600 underline hover:text-status-danger-800 dark:text-status-danger-300"
        >
          {t('states.tryAgain')}
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Search and filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex-1">
          <input
            type="text"
            placeholder={t('components.branchFinder.searchByNameCityOr')}
            aria-label={t('components.branchFinder.searchByNameCityOr2')}
            value={searchQuery}
            onChange={(e) => handleSearch(e.target.value)}
            className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg focus:ring-2 focus:ring-lsc-rose dark:focus:ring-lsc-rose-light focus:border-lsc-rose dark:focus:border-lsc-rose-light dark:bg-earth-800 dark:text-earth-50"
          />
        </div>

        <div className="flex gap-2">
          <select
            value={selectedType}
            onChange={(e) => handleTypeFilter(e.target.value as BranchType | 'all')}
            aria-label={t('aria.branchFinder.filterLocationsByBranchType')}
            className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg focus:ring-2 focus:ring-lsc-rose dark:focus:ring-lsc-rose-light dark:bg-earth-800 dark:text-earth-50"
          >
            <option value="all">{t('branches.filterType.allTypes', 'All Types')}</option>
            <option value="main">{t('branches.type.main', 'Main Library')}</option>
            <option value="branch">{t('branches.filterType.branches', 'Branches')}</option>
            <option value="bookmobile">{t('branches.filterType.bookmobiles', 'Bookmobiles')}</option>
            <option value="kiosk">{t('branches.filterType.kiosks', 'Kiosks')}</option>
          </select>

          <button
            onClick={findNearby}
            disabled={locationLoading}
            className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50 disabled:cursor-not-allowed min-w-[44px] min-h-[44px]"
          >
            {locationLoading ? (
              <div className="motion-safe:animate-spin motion-reduce:animate-none rounded-full h-4 w-4 border-b-2 border-white" />
            ) : (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"
                />
              </svg>
            )}
            <span className="hidden sm:inline">{t('branches.findNearby', 'Find Nearby')}</span>
          </button>
        </div>
      </div>

      {/* Location status/error */}
      {locationError && (
        <div className="p-3 bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-lg text-status-warning-800 dark:text-status-warning-300 text-sm">
          {locationError}
        </div>
      )}

      {userLocation && !locationError && (
        <div className="p-3 bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-800 rounded-lg text-status-success-800 dark:text-status-success-300 text-sm flex items-center gap-2">
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
              clipRule="evenodd"
            />
          </svg>
          {t('branches.sortedByDistance', 'Showing locations sorted by distance from your location')}
        </div>
      )}

      {/* Results count */}
      <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
        {t('branches.locationsFound', { count: filteredBranches.length })}
      </div>

      {/* Branch list */}
      <div className="space-y-3">
        {filteredBranches.length === 0 ? (
          <div className="p-6 text-center text-lsc-dark/70 dark:text-lsc-cream/70 bg-earth-50 dark:bg-earth-900 rounded-lg">
            {t('branches.noLocationsFound', 'No locations found matching your criteria.')}
          </div>
        ) : (
          filteredBranches.map((branch) => (
            <div
              key={branch.id}
              className="p-4 border border-lsc-border dark:border-earth-700 rounded-lg hover:border-lsc-border hover:shadow-sm transition-all bg-lsc-white dark:bg-earth-800"
            >
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="font-serif font-semibold text-lg text-lsc-dark dark:text-lsc-cream">{branch.name}</h3>
                    <span
                      className={`px-2 py-0.5 text-xs rounded-full ${
                        branch.branch_type === 'bookmobile'
                          ? 'bg-category-100 dark:bg-category-900/30 text-category-800 dark:text-category-300'
                          : branch.branch_type === 'main'
                          ? 'bg-earth-100 dark:bg-earth-800/30 text-earth-800 dark:text-lsc-rose-light'
                          : 'bg-earth-100 dark:bg-earth-700 text-earth-800 dark:text-earth-100'
                      }`}
                    >
                      {getBranchTypeLabel(branch.branch_type, t)}
                    </span>
                    {branch.distance_miles !== null && (
                      <span className="px-2 py-0.5 text-xs bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-300 rounded-full">
                        {formatDistance(branch.distance_miles)}
                      </span>
                    )}
                  </div>

                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{formatBranchAddress(branch)}</p>

                  {/* Today's hours + open/closed status */}
                  {(() => {
                    const hours = branchHours[branch.id]
                    if (!hours) return null
                    const open = isBranchOpen(hours)
                    const todayLabel = getTodayHoursLabel(hours)
                    return (
                      <div className="flex items-center gap-2 flex-wrap mt-2">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${
                            open
                              ? 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-300'
                              : 'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-800 dark:text-status-danger-300'
                          }`}
                        >
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${open ? 'bg-status-success-500' : 'bg-status-danger-500'}`}
                            aria-hidden="true"
                          />
                          {open ? t('home.hours.openNow') : t('home.hours.closed')}
                        </span>
                        {todayLabel && (
                          <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                            {t('dates.today')}: {todayLabel}
                          </span>
                        )}
                      </div>
                    )
                  })()}

                  {branch.phone && (
                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm mt-1">
                      <a href={`tel:${branch.phone}`} className="text-lsc-rose dark:text-lsc-rose-light hover:underline">
                        {branch.phone}
                      </a>
                    </p>
                  )}

                  {/* Features */}
                  <div className="flex flex-wrap gap-2 mt-2">
                    {branch.is_ada_accessible && (
                      <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{t('branches.features.accessible', 'Accessible')}</span>
                    )}
                    {branch.has_meeting_rooms && (
                      <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{t('branches.features.meetingRooms', 'Meeting Rooms')}</span>
                    )}
                    {branch.has_makerspace && (
                      <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{t('branches.features.makerspace', 'Makerspace')}</span>
                    )}
                    {branch.has_drive_through && (
                      <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{t('branches.features.driveThrough', 'Drive-Through')}</span>
                    )}
                    {branch.has_self_checkout && (
                      <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{t('branches.features.selfCheckout', 'Self-Checkout')}</span>
                    )}
                  </div>

                  {/* Bookmobile-specific info */}
                  {showBookmobileFeatures && branch.branch_type === 'bookmobile' && (
                    <div className="mt-2 p-2 bg-category-50 dark:bg-category-900/20 rounded text-sm text-category-800 dark:text-category-300">
                      {t('branches.viewScheduleForStops', 'View schedule for stops and times')}
                    </div>
                  )}
                </div>

                <div className="flex sm:flex-col gap-2">
                  <a
                    href={getDirectionsUrl(branch)}
                    aria-label={t('branches.directionsToAria', 'Directions to {{branch}}').replace('{{branch}}', branch.name)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-center gap-1 px-3 py-2 text-sm bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 rounded-lg hover:bg-earth-200 dark:hover:bg-earth-600 min-w-[44px] min-h-[44px]"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"
                      />
                    </svg>
                    <span>{t('contact.directions', 'Directions')}</span>
                  </a>

                  {onSelectBranch && (
                    <button
                      onClick={() => onSelectBranch(branch)}
                      aria-label={t('branches.seeHoursDetailsAria', 'See hours and details for {{branch}}').replace('{{branch}}', branch.name)}
                      className="flex items-center justify-center gap-1 px-3 py-2 text-sm bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 min-w-[44px] min-h-[44px]"
                    >
                      {t('branches.seeHoursDetails', 'See hours & details')}
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default BranchFinder
