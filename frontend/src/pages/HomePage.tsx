/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { lazy, Suspense, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getEvents } from '@/api/api'
import { getAnnouncements } from '@/api/announcements-api'
import { getIsOpen, getLibraryHours } from '@/api/domains/content/homepage-content-api'
import { useLibraryContact } from '@/hooks/useLibraryContact'
import { getHomePage } from '@/api/home'
import { useAuth } from '@/contexts/AuthContext'
import { ArrowRight, Heart } from 'lucide-react'

import HeroSection from '../components/HeroSection'
import LibraryPulse from '@/components/LibraryPulse'
import SectionDivider from '@/components/SectionDivider'
import Skeleton from '@/components/Skeleton'
import PageContainer from '@/components/layout/PageContainer'

import { useTranslation } from '@/i18n/I18nContext'
import { useHomePageQuote } from '@/hooks/useHomePageQuote'
import { useOnboarding } from '@/contexts/OnboardingContext'
import { useEssentialsMode } from '@/contexts/EssentialsModeContext'
import { useBrandingContext } from '@/contexts/BrandingContext'
import { usePageTitle } from '@/hooks/usePageTitle'

// Lazy load below-fold components to reduce initial bundle size
const EssentialsHomePage = lazy(() => import('@/components/EssentialsHomePage'))
const ActionGrid = lazy(() => import('@/components/ActionGrid'))
const ComputerLabStatus = lazy(() => import('@/components/ComputerLabStatus'))
const PlanYourVisit = lazy(() => import('@/components/home/PlanYourVisit'))
const HeroPick = lazy(() => import('@/components/home/HeroPick'))
const TopicalShelf = lazy(() => import('@/components/home/TopicalShelf'))
const UpcomingProgramsStrip = lazy(() => import('@/components/UpcomingProgramsStrip'))
const MostRequested = lazy(() => import('@/components/home/MostRequested'))
const ContinueExploring = lazy(() => import('@/components/home/ContinueExploring'))


export default function HomePage(): React.ReactElement {
  usePageTitle('')
  const navigate = useNavigate()
  const { t, language } = useTranslation()
  const todaysQuote = useHomePageQuote(language)
  const { shouldShowPatronOnboarding } = useOnboarding()
  const { isEssentialsMode } = useEssentialsMode()
  const { setupComplete } = useBrandingContext()
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin' || user?.role === 'super_admin' || user?.role === 'director'

  // Redirect to setup wizard if setup not complete
  useEffect(() => {
    if (!setupComplete) {
      navigate('/welcome', { replace: true })
    }
  }, [setupComplete, navigate])

  // Redirect to onboarding if first login / never completed
  useEffect(() => {
    if (!isEssentialsMode && shouldShowPatronOnboarding) {
      navigate('/onboarding/welcome', { replace: true })
    }
  }, [isEssentialsMode, shouldShowPatronOnboarding, navigate])

  // --- Data Fetching ---

  const { data: eventsData } = useQuery({
    queryKey: ['events', { upcoming: true, per_page: 6 }],
    queryFn: () => getEvents({ upcoming: true, per_page: 6 }),
    staleTime: 120_000,
    enabled: !isEssentialsMode,
  })

  const { data: openStatus } = useQuery({
    queryKey: ['library-is-open'],
    queryFn: getIsOpen,
    staleTime: 300_000,
    refetchInterval: 300_000,
    enabled: !isEssentialsMode,
  })

  const mainBranch = useLibraryContact()

  const { data: libraryHours } = useQuery({
    queryKey: ['library-hours-weekly'],
    queryFn: getLibraryHours,
    staleTime: 300_000,
    enabled: !isEssentialsMode,
  })

  const {
    data: homePageData,
    isLoading: homePageLoading,
    isError: homePageError,
    refetch: retryHomePage,
  } = useQuery({
    queryKey: ['home-page'],
    queryFn: getHomePage,
    staleTime: 120_000,
    enabled: !isEssentialsMode,
  })

  const { data: announcementsData } = useQuery({
    queryKey: ['announcements-homepage'],
    queryFn: () => getAnnouncements({ active_only: true, homepage_only: true, per_page: 5 }),
    staleTime: 300_000,
    enabled: !isEssentialsMode,
  })

  // --- Derived State ---

  const todayHoursLabel = (() => {
    if (!libraryHours?.weekly) return null
    const dayIndex = new Date().getDay()
    const today = libraryHours.weekly.find((d) => d.day_of_week === dayIndex)
    if (!today || today.is_closed) return t('home.visitUs.closedToday')
    return null
  })()

  if (isEssentialsMode) {
    return (
      <Suspense fallback={<Skeleton variant="card" className="h-screen w-full" />}>
        <EssentialsHomePage />
      </Suspense>
    )
  }

  return (
    <>
    <div className="space-y-12 md:space-y-16">
      <HeroSection onSearch={(q) => navigate(`/catalog?q=${encodeURIComponent(q)}`)} />

      <PageContainer>
        <LibraryPulse
          openStatus={openStatus ?? null}
          mainBranch={mainBranch ?? null}
          todayHoursLabel={todayHoursLabel}
          announcements={announcementsData?.items ?? null}
          upcomingEvent={eventsData?.data?.[0] ?? null}
          weekly={libraryHours?.weekly ?? null}
          overrides={libraryHours?.overrides ?? null}
        />
      </PageContainer>

      <section
        aria-label={t('home.aria.shelvesSection', 'Curated reading and recommendations')}
        className="max-w-6xl mx-auto px-6 space-y-8 md:space-y-10"
      >
        {homePageLoading && (
          <div className="space-y-12" aria-busy="true" aria-live="polite">
            <Skeleton variant="card" className="h-72 w-full" />
            <Skeleton variant="card" className="h-56 w-full" />
            <Skeleton variant="card" className="h-56 w-full" />
            <Skeleton variant="card" className="h-56 w-full" />
          </div>
        )}
        {homePageError && !homePageLoading && (
          <div role="alert" className="rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800/40 p-8 text-center space-y-4">
            <p className="text-base text-earth-700 dark:text-earth-300">
              {t('home.shelves.error', 'We could not load staff picks right now. Search and library services are still available.')}
            </p>
            <button
              type="button"
              onClick={() => void retryHomePage()}
              className="inline-flex min-h-[44px] items-center justify-center rounded-lg bg-sage-700 px-4 py-2 text-sm font-semibold text-lsc-white transition-colors hover:bg-sage-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sage-500 focus-visible:ring-offset-2 dark:bg-sage-600 dark:hover:bg-sage-500"
            >
              {t('home.shelves.retry', 'Try loading staff picks again')}
            </button>
          </div>
        )}
        {!homePageLoading && !homePageError && homePageData && (() => {
          const hero = homePageData.hero
          const shelves = homePageData.shelves ?? []
          const config = homePageData.config
          const hasContent = Boolean(hero) || shelves.length > 0
          if (!hasContent) {
            return (
              <div className="rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800/40 p-12 text-center space-y-4">
                <p className="text-base text-earth-700 dark:text-earth-300">
                  {config?.empty_state_message ?? t('home.shelves.empty', 'Our shelves are being prepared. Check back soon.')}
                </p>
                {isAdmin && (
                  <Link
                    to="/staff/home-page"
                    className="inline-flex items-center gap-2 text-sm font-bold text-sage-700 dark:text-lsc-rose hover:text-sage-800 transition-colors"
                  >
                    {t('home.shelves.adminSetupCta', 'Set up your home page')}
                    <ArrowRight className="w-4 h-4" aria-hidden="true" />
                  </Link>
                )}
              </div>
            )
          }
          return (
            <>
              <div className="max-w-2xl space-y-2">
                <h2 className="font-serif text-3xl leading-tight text-lsc-dark dark:text-lsc-cream md:text-4xl">
                  {t('home.shelves.title', 'A few staff-picked places to start')}
                </h2>
                <p className="max-w-xl text-base leading-relaxed text-earth-600 dark:text-earth-400 md:text-lg">
                  {t('home.shelves.description', 'Start with one, then browse at your own pace.')}
                </p>
              </div>
              {hero && (
                <Suspense fallback={<Skeleton variant="card" className="h-72 w-full" />}>
                  <HeroPick hero={hero} />
                </Suspense>
              )}
              {shelves.slice(0, 2).map((shelf) => (
                <Suspense key={shelf.id} fallback={<Skeleton variant="card" className="h-56 w-full" />}>
                  <TopicalShelf shelf={shelf} />
                </Suspense>
              ))}
              {shelves.length > 2 && (
                <details className="border-t border-lsc-border dark:border-earth-700 pt-4">
                  <summary className="cursor-pointer rounded py-3 text-sm font-semibold text-sage-700 dark:text-lsc-rose focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sage-500">
                    {t('libraryExperience.moreShelves', 'More reading collections')}
                  </summary>
                  <div className="space-y-8 pt-4">
                    {shelves.slice(2).map((shelf) => (
                      <Suspense key={shelf.id} fallback={<Skeleton variant="card" className="h-56 w-full" />}>
                        <TopicalShelf shelf={shelf} />
                      </Suspense>
                    ))}
                  </div>
                </details>
              )}
              {config?.picks_link_label && config?.picks_link_href && (
                <div className="text-center pt-2">
                  <Link
                    to={config.picks_link_href}
                    className="group inline-flex items-center gap-2 text-sm font-bold text-sage-700 dark:text-lsc-rose hover:text-sage-800 transition-colors"
                  >
                    {config.picks_link_label}
                    <ArrowRight className="w-4 h-4 motion-safe:[@media(hover:hover)_and_(pointer:fine)]:group-hover:translate-x-1 motion-safe:transition-transform motion-safe:duration-150 motion-safe:ease-[cubic-bezier(0.23,1,0.32,1)]" aria-hidden="true" />
                  </Link>
                </div>
              )}
            </>
          )
        })()}
      </section>

      <div className="max-w-4xl mx-auto px-6">
        <SectionDivider />
      </div>

      <Suspense fallback={null}>
        <UpcomingProgramsStrip events={eventsData?.data ?? null} />
      </Suspense>

      <PageContainer as="section" className="space-y-6">
        <Suspense fallback={<Skeleton variant="card" className="h-48 w-full" />}>
          <ActionGrid />
        </Suspense>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Suspense fallback={null}><ComputerLabStatus /></Suspense>
          <Suspense fallback={null}><PlanYourVisit openStatus={openStatus ?? null} /></Suspense>
        </div>
      </PageContainer>

      <Suspense fallback={null}><ContinueExploring /></Suspense>
      <PageContainer as="section">
        <Suspense fallback={null}><MostRequested /></Suspense>
      </PageContainer>

      <section className="py-12 sm:py-20 md:py-32 text-center max-w-3xl mx-auto px-6 space-y-10 sm:space-y-16 motion-safe:animate-hero-fade-up-3">
        {todaysQuote && (
          <blockquote className="space-y-8 sm:space-y-10" aria-live="off">
            <p className="font-serif text-3xl md:text-4xl lg:text-5xl font-bold text-lsc-rose dark:text-lsc-cream leading-snug italic tracking-tight pb-3">
              "{todaysQuote.quote_text}"
            </p>
            {todaysQuote.attribution && (
              <cite className="block text-base sm:text-sm text-earth-700 dark:text-earth-300 font-mono uppercase tracking-[0.16em] not-italic">
                - {todaysQuote.attribution}
              </cite>
            )}
          </blockquote>
        )}
        
        <div className="flex flex-col items-center gap-6">
          <p className="text-sm text-earth-700 dark:text-earth-300 max-w-md text-center">
            {t('footer.donateMessage')}
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              to="/donate"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-full border-2 border-lsc-rose/40 hover:border-lsc-rose hover:bg-lsc-rose/5 dark:hover:bg-lsc-rose/10 text-lsc-rose transition-colors font-semibold text-sm motion-safe:[@media(hover:hover)_and_(pointer:fine)]:hover:scale-105 motion-safe:transition-transform motion-safe:duration-150 motion-safe:ease-[cubic-bezier(0.23,1,0.32,1)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2"
            >
              <Heart className="w-4 h-4" aria-hidden="true" />
              {t('home.support.donateButton')}
            </Link>
            <Link to="/about" className="group inline-flex items-center gap-2 text-sm font-bold text-earth-600 dark:text-earth-300 hover:text-lsc-rose transition-colors">
              {t('home.about.learnMore')} 
              <ArrowRight className="w-4 h-4 motion-safe:[@media(hover:hover)_and_(pointer:fine)]:group-hover:translate-x-1 motion-safe:transition-transform motion-safe:duration-150 motion-safe:ease-[cubic-bezier(0.23,1,0.32,1)]" />
            </Link>
          </div>
        </div>
      </section>
    </div>
    </>
  )
}
