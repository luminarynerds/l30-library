/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useTranslation} from '@/i18n'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../contexts/AuthContext'
import { useOrganizationFeatures } from '../contexts/OrganizationFeaturesContext'
import { useEssentialsMode } from '../contexts/EssentialsModeContext'
import { getIsOpen, getLibraryHours } from '@/api/domains/content/homepage-content-api'
import { getEvents } from '@/api/api'
import { useBranding } from '@/contexts/BrandingContext'
import api from '@/lib/api-client'
import { API_BASE } from '@/api/types'
import TodayStrip from '@/components/home/TodayStrip'

import { Search, Clock, Calendar, CheckCircle2, ArrowRight, MapPin, CircleHelp } from 'lucide-react'

const DAY_NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

function formatTo12Hour(time: string): string {
  const parts = time.split(':').map(Number)
  const h = parts[0] ?? 0
  const m = parts[1] ?? 0
  const suffix = h >= 12 ? 'PM' : 'AM'
  const hour12 = h % 12 || 12
  return m === 0 ? `${hour12}:00 ${suffix}` : `${hour12}:${String(m).padStart(2, '0')} ${suffix}`
}

export default function EssentialsHomePage() {
  const branding = useBranding()
  const { t, language } = useTranslation()
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()
  const { isFeatureEnabled } = useOrganizationFeatures()
  const { toggleMode, isLoading: isEssentialsLoading } = useEssentialsMode()
  const [searchQuery, setSearchQuery] = useState('')

  const [now] = useState(() => new Date())
  const today = now.getDay()

  const { data: openStatus } = useQuery({
    queryKey: ['library-is-open'],
    queryFn: getIsOpen,
    staleTime: 60_000,
    refetchInterval: 60_000,
  })

  const { data: pulseData } = useQuery({
    queryKey: ['community-pulse'],
    queryFn: () => api.get(`${API_BASE}/stats/community-pulse`).catch(() => null),
    staleTime: 60_000,
  })

  const { data: hoursData } = useQuery({
    queryKey: ['library-hours-weekly'],
    queryFn: getLibraryHours,
    staleTime: 300_000,
  })

  const { data: eventsData } = useQuery({
    queryKey: ['events', { upcoming: true, per_page: 6 }],
    queryFn: () => getEvents({ upcoming: true, per_page: 6 }),
    staleTime: 120_000,
  })

  const todayHoursLabel = (() => {
    const todaysHours = hoursData?.weekly?.find((dayHours) => dayHours.day_of_week === today)
    return !todaysHours || todaysHours.is_closed ? t('home.visitUs.closedToday') : null
  })()

  const { isOpen, statusText } = (() => {
    if (!openStatus) return { isOpen: false, statusText: '' }
    if (openStatus.is_open) {
      const time = openStatus.closes_at ? formatTo12Hour(openStatus.closes_at) : ''
      return { isOpen: true, statusText: `Open until ${time}` }
    }
    const time = openStatus.opens_at ? formatTo12Hour(openStatus.opens_at) : ''
    return { isOpen: false, statusText: time ? `Opens at ${time}` : 'Closed' }
  })()

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (searchQuery.trim()) {
      navigate(`/catalog?q=${encodeURIComponent(searchQuery.trim())}`)
    }
  }

  return (
    <main className="min-h-screen bg-lsc-cream dark:bg-earth-950 transition-colors duration-500">
      {/* Search-first header area */}
      <div className="border-b border-earth-200 dark:border-earth-800 bg-lsc-white dark:bg-earth-900 shadow-soft-sm transition-colors duration-500">
        <div className="max-w-3xl mx-auto px-6 py-12 sm:py-16">
          <div className="mb-10 flex flex-wrap items-start justify-between gap-4">
            <div className="max-w-xl space-y-2">
              <h1 className="font-serif text-3xl text-lsc-dark dark:text-lsc-cream sm:text-4xl">{branding.library_name}</h1>
              <p className="text-base leading-relaxed text-earth-600 dark:text-earth-300">
                A simpler view with fewer choices. Start with one thing, then return whenever you are ready.
              </p>
            </div>
            <button
              type="button"
              onClick={() => void toggleMode()}
              disabled={isEssentialsLoading}
              className="min-h-[44px] rounded-lg border border-earth-300 px-4 py-2 text-sm font-semibold text-earth-700 transition-colors hover:bg-earth-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 disabled:opacity-50 dark:border-earth-600 dark:text-earth-200 dark:hover:bg-earth-800"
            >
              Use full view
            </button>
          </div>
          
          {/* Status line - The "Comforting Hum" */}
          <div className="flex flex-wrap items-center gap-4 mb-10 font-mono text-xs tracking-widest uppercase">
            <span
              className={`inline-flex items-center gap-2 px-3 py-1 rounded-full font-bold ${
                isOpen
                  ? 'bg-forest-50 text-forest-700 dark:bg-forest-900/30 dark:text-forest-400'
                  : 'bg-status-warning-50 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-400'
              }`}
              role="status"
              aria-live="polite"
            >
              <Clock className="w-3.5 h-3.5" />
              {statusText}
            </span>
            
            {pulseData?.checkouts_today > 0 && (
              <span className="flex items-center gap-2 text-earth-600 dark:text-earth-400">
                <CheckCircle2 className="w-3.5 h-3.5" />
                {pulseData.checkouts_today.toLocaleString()} borrowed today
              </span>
            )}

            <time className="text-earth-600 dark:text-earth-500" dateTime={now.toISOString()}>
              {now.toLocaleDateString(language, { weekday: 'short', month: 'short', day: 'numeric' })}
            </time>
          </div>

          {/* Search */}
          <form onSubmit={handleSearch} role="search" aria-label={t('components.essentialsHome.searchTheLibraryCatalog')} className="space-y-4">
            <label htmlFor="home-search" className="block text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              Search books, media, and resources
            </label>
            <div className="flex gap-2">
              <input
                id="home-search"
                type="search"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={t('components.essentialsHome.titleAuthorSubjectIsbn')}
                className="flex-1 px-5 py-4 text-lg bg-earth-50 dark:bg-earth-800 border border-earth-200 dark:border-earth-700 rounded-xl text-lsc-dark dark:text-lsc-cream placeholder:text-earth-400 focus:outline-none focus:ring-2 focus:ring-lsc-rose dark:focus:ring-lsc-rose transition-all duration-300"
                autoComplete="off"
              />
              <button
                type="submit"
                className="px-6 py-4 bg-lsc-dark dark:bg-lsc-cream text-white dark:text-lsc-dark font-bold rounded-xl transition-all duration-300 hover:scale-105 active:scale-95 focus:ring-2 focus:ring-lsc-rose"
                aria-label={t('aria.essentialsHomePage.search')}
              >
                <Search className="w-6 h-6" aria-hidden="true" />
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* Main content: dense, useful links */}
      <div className="max-w-3xl mx-auto px-6 py-12 sm:py-16">
        <TodayStrip
          openStatus={openStatus ?? null}
          events={eventsData?.data ?? null}
          todayHoursLabel={todayHoursLabel}
        />

        <section aria-labelledby="start-here-heading" className="mt-12">
          <div className="mb-5 space-y-2">
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-earth-600 dark:text-earth-400">Start here</p>
            <h2 id="start-here-heading" className="font-serif text-2xl text-lsc-dark dark:text-lsc-cream">Choose one next step</h2>
          </div>
        <nav aria-label={t('aria.essentialsHomePage.quickActions')}>
          <div className="bg-lsc-white dark:bg-earth-900 border border-earth-200 dark:border-earth-800 divide-y divide-earth-100 dark:divide-earth-800 rounded-xl overflow-hidden shadow-soft-sm">
            <Link
              to="/catalog"
              className="flex items-center justify-between px-6 py-5 hover:bg-earth-50 dark:hover:bg-earth-800 transition-colors group"
            >
              <div>
                <span className="text-base font-bold text-lsc-dark dark:text-lsc-cream">Find a title</span>
                <span className="block text-sm text-earth-600 dark:text-earth-400 mt-0.5">Search books, media, and resources</span>
              </div>
              <ArrowRight className="w-5 h-5 text-earth-300 dark:text-earth-700 group-hover:text-lsc-rose group-hover:translate-x-1 transition-all" aria-hidden="true" />
            </Link>

            <Link
              to="/branches"
              className="flex items-center justify-between px-6 py-5 hover:bg-earth-50 dark:hover:bg-earth-800 transition-colors group"
            >
              <div>
                <span className="inline-flex items-center gap-2 text-base font-bold text-lsc-dark dark:text-lsc-cream"><MapPin className="h-4 w-4" aria-hidden="true" />Plan a visit</span>
                <span className="block text-sm text-earth-600 dark:text-earth-400 mt-0.5">Hours, locations, and getting here</span>
              </div>
              <ArrowRight className="w-5 h-5 text-earth-300 dark:text-earth-700 group-hover:text-lsc-rose group-hover:translate-x-1 transition-all" aria-hidden="true" />
            </Link>

            <Link
              to="/account"
              className="flex items-center justify-between px-6 py-5 hover:bg-earth-50 dark:hover:bg-earth-800 transition-colors group"
            >
              <div>
                <span className="text-base font-bold text-lsc-dark dark:text-lsc-cream">My Account</span>
                <span className="block text-sm text-earth-600 dark:text-earth-400 mt-0.5">
                  {isAuthenticated ? 'Checkouts, holds, fines, reading history' : 'Sign in to view your account'}
                </span>
              </div>
              <ArrowRight className="w-5 h-5 text-earth-300 dark:text-earth-700 group-hover:text-lsc-rose group-hover:translate-x-1 transition-all" aria-hidden="true" />
            </Link>

            {isFeatureEnabled('events_enabled') && (
              <Link
                to="/events"
                className="flex items-center justify-between px-6 py-5 hover:bg-earth-50 dark:hover:bg-earth-800 transition-colors group"
              >
                <div>
                  <span className="text-base font-bold text-lsc-dark dark:text-lsc-cream">Events &amp; Programs</span>
                  <span className="block text-sm text-earth-600 dark:text-earth-400 mt-0.5">{t('components.essentialsHome.classesReadingsKidsProgramsCommunity')}</span>
                </div>
                <ArrowRight className="w-5 h-5 text-earth-300 dark:text-earth-700 group-hover:text-lsc-rose group-hover:translate-x-1 transition-all" aria-hidden="true" />
              </Link>
            )}

            {isFeatureEnabled('meeting_rooms_enabled') && (
              <Link
                to="/rooms"
                className="flex items-center justify-between px-6 py-5 hover:bg-earth-50 dark:hover:bg-earth-800 transition-colors group"
              >
                <div>
                  <span className="text-base font-bold text-lsc-dark dark:text-lsc-cream">Book a Room</span>
                  <span className="block text-sm text-earth-600 dark:text-earth-400 mt-0.5">{t('components.essentialsHome.studyRoomsMeetingSpacesRecording')}</span>
                </div>
                <ArrowRight className="w-5 h-5 text-earth-300 dark:text-earth-700 group-hover:text-lsc-rose group-hover:translate-x-1 transition-all" aria-hidden="true" />
              </Link>
            )}

            <Link
              to="/ask-librarian"
              className="flex items-center justify-between px-6 py-5 hover:bg-earth-50 dark:hover:bg-earth-800 transition-colors group"
            >
              <div>
                <span className="inline-flex items-center gap-2 text-base font-bold text-lsc-dark dark:text-lsc-cream"><CircleHelp className="h-4 w-4" aria-hidden="true" />Get help</span>
                <span className="block text-sm text-earth-600 dark:text-earth-400 mt-0.5">{t('components.essentialsHome.chatEmailOrCallFor')}</span>
              </div>
              <ArrowRight className="w-5 h-5 text-earth-300 dark:text-earth-700 group-hover:text-lsc-rose group-hover:translate-x-1 transition-all" aria-hidden="true" />
            </Link>
          </div>
        </nav>
        </section>

        {/* Hours table */}
        <div className="mt-16">
          <h2 className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.2em] text-earth-600 dark:text-earth-500 mb-6">
            <Calendar className="w-4 h-4" />
            Weekly Schedule
          </h2>
          <div className="bg-lsc-white dark:bg-earth-900 border border-earth-200 dark:border-earth-800 rounded-xl overflow-hidden shadow-soft-sm transition-colors duration-500">
            <table className="w-full text-sm" role="table">
              <tbody className="divide-y divide-earth-50 dark:divide-earth-800">
                {hoursData?.weekly
                  ? hoursData.weekly.map((dayHours) => {
                      const isToday = dayHours.day_of_week === today
                      const hoursText = dayHours.is_closed || !dayHours.open_time || !dayHours.close_time
                        ? 'Closed'
                        : `${formatTo12Hour(dayHours.open_time)} \u2013 ${formatTo12Hour(dayHours.close_time)}`
                      return (
                        <tr
                          key={dayHours.day_of_week}
                          className={`transition-colors ${
                            isToday ? 'bg-sage-50/50 dark:bg-lsc-rose/5' : ''
                          }`}
                        >
                          <td className={`px-6 py-4 font-mono text-xs ${isToday ? 'font-bold text-lsc-dark dark:text-lsc-cream' : 'text-earth-600 dark:text-earth-500'}`}>
                            {dayHours.label || DAY_NAMES[dayHours.day_of_week]}
                          </td>
                          <td className={`px-6 py-4 text-right font-mono text-xs ${isToday ? 'font-bold text-lsc-dark dark:text-lsc-cream underline decoration-lsc-rose/30' : 'text-earth-600 dark:text-earth-400'}`}>
                            {hoursText}
                          </td>
                        </tr>
                      )
                    })
                  : [0, 1, 2, 3, 4, 5, 6].map((day) => (
                      <tr key={day}>
                        <td className="px-6 py-4 font-mono text-xs text-earth-600">{DAY_NAMES[day]}</td>
                        <td className="px-6 py-4 text-right font-mono text-xs text-earth-200">&mdash;</td>
                      </tr>
                    ))
                }
              </tbody>
            </table>
          </div>
        </div>

        {/* Card signup CTA */}
        {!isAuthenticated && (
          <div className="mt-16 bg-gradient-to-br from-earth-50 to-sage-50 dark:from-earth-900 dark:to-earth-950 border border-earth-200 dark:border-earth-800 px-8 py-8 flex items-center justify-between gap-6 flex-wrap rounded-xl shadow-soft-sm">
            <div className="max-w-md">
              <p className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream">{t('components.essentialsHome.getALibraryCard')}</p>
              <p className="text-sm text-earth-600 dark:text-earth-400 mt-1">{t('components.essentialsHome.freeForAllResidentsApply')}</p>
            </div>
            <button
              onClick={() => navigate('/card-application')}
              className="px-8 py-3 bg-lsc-rose text-white font-bold rounded-xl transition-all duration-300 hover:scale-105 hover:bg-lsc-dark focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2"
            >
              Apply now
            </button>
          </div>
        )}
      </div>
    </main>
  )
}
