/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import {
  Heart,
  MapPin,
  Phone,
  Mail,
  BookOpen,
  Sparkles,
  Lightbulb,
  Target,
  Trophy,
  ArrowRight,
  Lock,
  Users,
  Scale,
  AlertTriangle,
  Globe,
  Code,
  Library,
  TrendingUp,
} from 'lucide-react';
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import StandardPageLayout from '@/components/StandardPageLayout'
import { getStaffBios, type StaffBio } from '@/api/community-api'
import { StaffAvatar } from '@/components/about/StaffAvatar'
import { listBranches, type Branch } from '@/api/branch-api'
import { getPublicStats } from '@/api/book-challenges-api'
import { fetchApi } from '@/lib/api-client'
import { useMemo, useState, useEffect } from 'react'
import { useTranslation } from '@/i18n'
import { usePageTitle } from '@/hooks/usePageTitle'
import { useOrganizationFeatures } from '@/contexts/OrganizationFeaturesContext'
import { useBranding } from '@/contexts/BrandingContext'
import LocationCard from '@/components/about/LocationCard'
import { useBranchHoursSummary } from '@/components/about/useBranchHoursSummary'
import LibraryHoursHero from '@/components/about/LibraryHoursHero'

interface BranchLocationCardProps {
  branch: Branch
  address: string | null
  slug: string
  isBookmobile: boolean
  accessibility: string
  fallbackHours: string
}

function BranchLocationCard({
  branch,
  address,
  slug,
  isBookmobile,
  accessibility,
  fallbackHours,
}: BranchLocationCardProps) {
  const { summary, isLoading, isError } = useBranchHoursSummary(branch.id, !isBookmobile)
  const hours = isBookmobile
    ? 'Routes vary — see schedule'
    : isError || !summary
      ? isLoading
        ? fallbackHours
        : fallbackHours
      : summary
  return (
    <LocationCard
      name={branch.name}
      address={address}
      phone={isBookmobile ? null : branch.phone}
      hours={hours}
      accessibility={accessibility}
      slug={slug}
      isBookmobile={isBookmobile}
      bookmobileHref="/locations"
      isPlaceholder
    />
  )
}

interface TimelineEvent {
  year: string;
  title: string;
  description: string;
}

interface LibraryNumbers {
  total_items: number;
  total_cardholders: number;
}

interface PublicOverview {
  total_items_in_collection: number;
  total_cardholders: number;
  checkouts_this_year: number;
}

// AA contrast against white text (text-white = #FFFFFF):
// All bgs verified at >= 4.5:1 for normal text per WCAG 2.1.
const STAFF_COLORS = [
  'bg-lsc-rose',
  'bg-earth-600',
  'bg-status-warning-700',
  'bg-pink-700',
  'bg-status-success-800',
  'bg-category-700',
  'bg-sky-700',
  'bg-rose-800',
];

function formatDisplayName(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length <= 1) return name;
  return parts[0] + " " + (parts[parts.length - 1]?.[0] || "").toUpperCase() + ".";
}

function formatNumber(n: number): string {
  return n.toLocaleString();
}

function formatAddress(branch: Branch): string {
  const parts = [branch.address_line1, branch.address_line2].filter(Boolean);
  const cityParts = [branch.city, branch.state].filter(Boolean).join(', ');
  if (branch.zip_code) {
    return [...parts, `${cityParts} ${branch.zip_code}`].join(', ');
  }
  return [...parts, cityParts].filter(Boolean).join(', ');
}

export default function AboutLibraryContent(): React.ReactElement {
  const branding = useBranding()
  const { t } = useTranslation()
  const { isFeatureEnabled } = useOrganizationFeatures()
  usePageTitle(t('about.aboutTheLibrary'))

  // Tenant-set story (Admin > Branding) wins; the stock i18n timeline is
  // only a fallback for installs that haven't written their own yet.
  const tenantTimeline = branding.about_story?.timeline
  const tenantIntro = branding.about_story?.intro
  const tenantNote = branding.about_story?.director_note
  const directorNote =
    tenantNote && tenantNote.paragraphs && tenantNote.paragraphs.length > 0 ? tenantNote : null
  const storyIntro: string[] =
    tenantIntro && tenantIntro.length > 0
      ? tenantIntro
      : [t('about.storyParagraph1'), t('about.storyParagraph2')]
  const timelineEvents: TimelineEvent[] = useMemo(() => {
    if (tenantTimeline && tenantTimeline.length > 0) {
      return tenantTimeline.map((e) => ({
        year: e.year,
        title: e.title,
        description: e.description,
      }))
    }
    return [
      {
        year: '1952',
        title: t('about.timeline.1952.title'),
        description: t('about.opensInADonatedStorefront'),
      },
      {
        year: '1985',
        title: t('about.timeline.1985.title'),
        description: t('about.movesIntoOurCurrentBuilding'),
      },
      {
        year: '1997',
        title: t('about.timeline.1997.title'),
        description: t('about.timeline.1997.description'),
      },
      {
        year: '2020',
        title: t('about.timeline.2020.title'),
        description: t('about.curbsidePickupVirtualStoryTimes'),
      },
      {
        year: '2026',
        title: t('about.timeline.2026.title'),
        description: t('about.toolLendingLegalClinicsWorkforce'),
      },
    ]
  }, [t, tenantTimeline]);

  const { data: staffBios, isLoading: staffLoading } = useQuery({
    queryKey: ['staffBios'],
    queryFn: getStaffBios,
    staleTime: 10 * 60 * 1000,
  });

  const { data: branches, isLoading: branchesLoading } = useQuery({
    queryKey: ['branches'],
    queryFn: () => listBranches({ active_only: true }),
    staleTime: 10 * 60 * 1000,
  });

  const { data: challengeStats } = useQuery({
    queryKey: ['publicChallengeStats'],
    queryFn: getPublicStats,
    staleTime: 5 * 60 * 1000,
  });

  const { data: libraryNumbers } = useQuery({
    queryKey: ['libraryNumbers'],
    queryFn: () => fetchApi<LibraryNumbers>('/stats/library-numbers'),
    staleTime: 5 * 60 * 1000,
  });

  const [overview, setOverview] = useState<PublicOverview | null>(null);
  useEffect(() => {
    fetchApi<PublicOverview>('/public/stats/overview')
      .then((data) => { if (data) setOverview(data); })
      .catch(() => {});
  }, []);

  const totalChallenges = challengeStats?.total_challenges ?? null;
  const booksRetained = challengeStats?.outcomes
    ? (challengeStats.outcomes['retained'] ?? 0) + (challengeStats.outcomes['retained_with_changes'] ?? 0)
    : null;
  const booksRemoved = challengeStats?.outcomes?.['removed'] ?? null;

  return (
    <StandardPageLayout
      title={t('about.theMostUsefulPlaceIn')}
      subtitle={t('about.notAMuseumForBooks')}
      icon={BookOpen}
    >

      <LibraryHoursHero />

      {/* Section navigation for scanning */}
      <nav aria-label="Page sections" className="py-4 mb-2">
        <ul className="flex flex-wrap gap-2 text-sm">
          {[
            { id: 'about-story', label: t('about.howWeGotHere') },
            { id: 'about-staff', label: t('about.meetTheStaff') },
            { id: 'about-locations', label: t('about.ourLocations') },
            { id: 'about-challenges', label: t('about.bookRemoval') },
            { id: 'about-roadmap', label: t('about.whatsNext') },
            { id: 'about-contact', label: t('about.contactUs') },
          ].map((link) => (
            <li key={link.id}>
              <a
                href={`#${link.id}`}
                className="inline-block px-3 py-1.5 rounded-full bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-rose/10 hover:text-lsc-rose dark:hover:text-lsc-rose-light transition-colors"
              >
                {link.label}
              </a>
            </li>
          ))}
        </ul>
      </nav>

      {/* Our Story */}
      <section aria-labelledby="about-story" className="py-12 bg-lsc-white dark:bg-earth-800">
        <div className="container mx-auto px-4 max-w-5xl">
          <div className="grid md:grid-cols-2 gap-10 items-start">
            <div>
              <div className="flex items-center gap-3 mb-4">
                <div className="flex-shrink-0 w-10 h-10 bg-sage-100 dark:bg-sage-800 rounded-full flex items-center justify-center">
                  <Sparkles className="w-5 h-5 text-sage-600 dark:text-sage-400" aria-hidden="true" />
                </div>
                <h2 id="about-story" className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                  {t('about.howWeGotHere')}
                </h2>
              </div>
              {storyIntro.map((paragraph, i) => (
                <p
                  key={i}
                  className={`text-lsc-dark/70 dark:text-lsc-cream/70 leading-relaxed ${i < storyIntro.length - 1 ? 'mb-4' : ''}`}
                >
                  {paragraph}
                </p>
              ))}
            </div>
            <div className="space-y-4">
              {timelineEvents.map((event) => (
                <div key={event.year} className="flex gap-4">
                  <div className="flex-shrink-0 w-14 text-right">
                    <span className="font-bold text-lsc-rose dark:text-lsc-rose-light text-sm">{event.year}</span>
                  </div>
                  <div className="flex-1 border-l-2 border-sage-200 dark:border-sage-700 pl-4 relative pb-1">
                    <div className="absolute -left-[5px] top-1.5 w-2 h-2 bg-sage-400 dark:bg-sage-500 rounded-full" />
                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm leading-relaxed">
                      <span className="font-semibold">{event.title}:</span> {event.description}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* A Note From the Director -- tenant note from branding, stock i18n
          fallback, or hidden entirely via about_story.hide_director_note. */}
      {!branding.about_story?.hide_director_note && (
        <section aria-labelledby="about-director" className="py-10 bg-earth-50 dark:bg-earth-900">
          <div className="container mx-auto px-4 max-w-3xl">
            <div className="flex items-start gap-6">
              <div className="flex-shrink-0 w-12 h-12 bg-lsc-rose/10 rounded-full flex items-center justify-center mt-1">
                <Heart className="w-6 h-6 text-lsc-rose" aria-hidden="true" />
              </div>
              <div>
                <h2 id="about-director" className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-3">
                  {t('about.directorNote')}
                </h2>
                {directorNote ? (
                  <>
                    {directorNote.paragraphs.map((paragraph, i) => (
                      <p
                        key={i}
                        className={`text-lsc-dark/70 dark:text-lsc-cream/70 leading-relaxed ${i < directorNote.paragraphs.length - 1 ? 'mb-3' : ''}`}
                      >
                        {paragraph}
                      </p>
                    ))}
                    {directorNote.signature && (
                      <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-4 font-medium italic">— {directorNote.signature}</p>
                    )}
                  </>
                ) : (
                  <>
                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70 leading-relaxed mb-3">
                      {t('about.directorNoteParagraph1')}
                    </p>
                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70 leading-relaxed">
                      {t('about.directorNoteParagraph2')}
                    </p>
                  </>
                )}
              </div>
            </div>
          </div>
        </section>
      )}

      {/* By the Numbers -- live stats */}
      <section aria-labelledby="about-stats" className="py-10 bg-sage-100 dark:bg-sage-900">
        <div className="container mx-auto px-4 max-w-4xl">
          <h2 id="about-stats" className="sr-only">Library Statistics</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6 text-center">
              <Library className="w-7 h-7 text-lsc-rose mx-auto mb-2" aria-hidden="true" />
              <div className="text-3xl md:text-4xl font-bold text-lsc-rose dark:text-lsc-rose-light mb-1">
                {libraryNumbers ? formatNumber(libraryNumbers.total_items) : overview ? formatNumber(overview.total_items_in_collection) : <span className="inline-block w-16 h-8 bg-earth-200 dark:bg-earth-600 rounded motion-safe:animate-pulse" />}
              </div>
              <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('about.stats.totalItems')}</div>
            </div>
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6 text-center">
              <Users className="w-7 h-7 text-lsc-rose mx-auto mb-2" aria-hidden="true" />
              <div className="text-3xl md:text-4xl font-bold text-lsc-rose dark:text-lsc-rose-light mb-1">
                {libraryNumbers ? formatNumber(libraryNumbers.total_cardholders) : overview ? formatNumber(overview.total_cardholders) : <span className="inline-block w-16 h-8 bg-earth-200 dark:bg-earth-600 rounded motion-safe:animate-pulse" />}
              </div>
              <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('about.stats.cardHolders')}</div>
            </div>
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6 text-center col-span-2 md:col-span-1">
              <TrendingUp className="w-7 h-7 text-lsc-rose mx-auto mb-2" aria-hidden="true" />
              <div className="text-3xl md:text-4xl font-bold text-lsc-rose dark:text-lsc-rose-light mb-1">
                {overview ? formatNumber(overview.checkouts_this_year) : <span className="inline-block w-16 h-8 bg-earth-200 dark:bg-earth-600 rounded motion-safe:animate-pulse" />}
              </div>
              <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('about.stats.checkoutsYear', 'Checkouts This Year')}</div>
            </div>
          </div>
          <p className="text-xs text-earth-700 dark:text-earth-200 text-center mt-3">Updated daily</p>
          <div className="text-center mt-2">
            <Link
              to="/about/stats"
              className="inline-flex items-center gap-1 text-sm font-medium text-lsc-dark hover:text-lsc-rose underline underline-offset-2 transition-colors dark:text-lsc-cream"
            >
              See all library stats <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </section>

      {/* Why We Own Our Digital Collection -- only shown when indie platform is enabled */}
      {isFeatureEnabled('indie_platform_enabled') && (
      <section aria-labelledby="about-digital" className="py-16 bg-lsc-white dark:bg-earth-800">
        <div className="container mx-auto px-4 max-w-5xl">
          <div className="flex items-center gap-3 mb-6">
            <div className="flex-shrink-0 w-10 h-10 bg-status-warning-100 dark:bg-status-warning-900/50 rounded-full flex items-center justify-center">
              <AlertTriangle className="w-5 h-5 text-status-warning-800 dark:text-status-warning-200" aria-hidden="true" />
            </div>
            <h2 id="about-digital" className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              {t('about.whyWeOwnDigital')}
            </h2>
          </div>

          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 leading-relaxed mb-6 max-w-3xl">
            {t('about.digitalIntro')}
          </p>

          <div className="bg-lsc-cream dark:bg-lsc-dark/50 rounded-xl p-6 border border-lsc-border dark:border-earth-700 mb-6">
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">{t('about.theProblemWithTheOld')}</h3>
            <div className="grid md:grid-cols-3 gap-6 text-sm">
              <div className="flex items-start gap-3">
                <span className="text-status-warning-800 dark:text-status-warning-200 font-bold whitespace-nowrap">$40-65</span>
                <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('about.ebookLicenseCost')}</span>
              </div>
              <div className="flex items-start gap-3">
                <span className="text-status-warning-800 dark:text-status-warning-200 font-bold whitespace-nowrap">26 loans</span>
                <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('about.licenseExpiry')}</span>
              </div>
              <div className="flex items-start gap-3">
                <span className="text-status-warning-800 dark:text-status-warning-200 font-bold whitespace-nowrap">1 copy</span>
                <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('about.artificialScarcity')}</span>
              </div>
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 leading-relaxed mb-4">
                {t('about.physicalVsEbook')}
              </p>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 leading-relaxed">
                {t('about.platformControl')}
              </p>
            </div>
            <div className="space-y-4">
              <div className="bg-lsc-cream dark:bg-earth-700 rounded-lg p-5 border border-lsc-border dark:border-earth-700">
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3">{t('about.whatWeReDoingInstead')}</h3>
                <ul className="space-y-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  <li className="flex gap-2">
                    <span className="text-lsc-rose font-bold">→</span>
                    <span>{t('about.doInstead1Prefix')} <a href="https://thepalaceproject.org" target="_blank" rel="noopener noreferrer" className="text-lsc-rose underline underline-offset-2 hover:no-underline font-bold">{t("about.doInstead1Bold")}</a>{t('about.doInstead1Suffix')}</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-lsc-rose font-bold">→</span>
                    <span>{t('about.doInstead2Prefix')} <strong>{t('about.doInstead2Bold')}</strong> {t('about.doInstead2Suffix')}</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-lsc-rose font-bold">→</span>
                    <span>{t('about.partneringDirectlyWithIndependentAuthors')}</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-lsc-rose font-bold">→</span>
                    <span>{t('about.doInstead4Prefix')} <Link to="/indie" className="text-lsc-rose underline underline-offset-2 hover:no-underline font-bold">{t("about.doInstead4Bold")}</Link> {t('about.doInstead4Suffix')}</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-lsc-rose font-bold">→</span>
                    <span>{t('about.keepingOurPhysicalCollectionAs')}</span>
                  </li>
                </ul>
              </div>
              <div className="bg-sage-50 dark:bg-sage-900/30 rounded-lg p-5 border border-sage-200 dark:border-sage-800">
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3">{t('about.whyPalaceProject')}</h3>
                <ul className="space-y-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  <li className="flex gap-2">
                    <span className="text-sage-600 dark:text-sage-400 font-bold">✓</span>
                    <span>{t('about.builtByLyrasisANonprofit')}</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-sage-600 dark:text-sage-400 font-bold">✓</span>
                    <span>{t('about.noPerCirculationFeesNo')}</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-sage-600 dark:text-sage-400 font-bold">✓</span>
                    <span>{t('about.patronDataStaysWithThe')}</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-sage-600 dark:text-sage-400 font-bold">✓</span>
                    <span>{t('about.openSourceSoWeCan')}</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>

          <div className="bg-status-warning-50 dark:bg-status-warning-900/20 rounded-lg p-5 border border-status-warning-200 dark:border-status-warning-800 mt-6">
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">{t('about.whyIndieAuthors')}</h3>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 leading-relaxed">
              {t('about.whyIndieAuthorsText')}
            </p>
          </div>

          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm leading-relaxed mt-6 max-w-3xl">
            {t('about.transitionNote')}
          </p>
        </div>
      </section>
      )}

      {/* Why We Built Our Own Tools */}
      <section aria-labelledby="about-tools" className="py-16 bg-lsc-cream dark:bg-lsc-dark">
        <div className="container mx-auto px-4 max-w-5xl">
          <div className="flex items-center gap-3 mb-3">
            <div className="flex-shrink-0 w-10 h-10 bg-sage-100 dark:bg-sage-800 rounded-full flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-sage-600 dark:text-sage-400" aria-hidden="true" />
            </div>
            <h2 id="about-tools" className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              {t('about.whyBuiltOwnTools')}
            </h2>
          </div>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-8 ml-[52px]">
            {t('about.whyBuiltOwnToolsSub')}
          </p>

          {/* The Problem */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-8 border border-lsc-border dark:border-earth-700 mb-6">
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
              <Target className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
              {t('about.theProblem')}
            </h3>
            <div className="grid md:grid-cols-2 gap-6">
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 leading-relaxed">
                {t('about.problemText')}
              </p>
              <div className="bg-lsc-cream dark:bg-lsc-dark/50 rounded-lg p-5">
                <div className="space-y-3 text-sm">
                  <div className="flex items-start gap-3">
                    <span className="text-lsc-rose font-bold">67%</span>
                    <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('about.stat67pct')}</span>
                  </div>
                  <div className="flex items-start gap-3">
                    <span className="text-lsc-rose font-bold">12 min</span>
                    <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('about.stat12min')}</span>
                  </div>
                  <div className="flex items-start gap-3">
                    <span className="text-lsc-rose font-bold">23%</span>
                    <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('about.stat23pct')}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Our Approach */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-8 border border-lsc-border dark:border-earth-700 mb-6">
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
              {t('about.whatWeDid')}
            </h3>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 leading-relaxed mb-6">
              {t('about.whatWeDidText')}
            </p>
            <div className="grid md:grid-cols-3 gap-4">
              <div className="bg-lsc-cream dark:bg-lsc-dark/30 rounded-lg p-4 border border-lsc-border dark:border-earth-700">
                <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2 flex items-center gap-2">
                  <Heart className="w-4 h-4 text-lsc-rose" aria-hidden="true" />
                  {t('about.communityShaped')}
                </h4>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('about.listeningSessionsInformedEveryDecision')}</p>
              </div>
              <div className="bg-lsc-cream dark:bg-lsc-dark/30 rounded-lg p-4 border border-lsc-border dark:border-earth-700">
                <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2 flex items-center gap-2">
                  <Lock className="w-4 h-4 text-lsc-rose" aria-hidden="true" />
                  {t('about.privacyFirst')}
                </h4>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('about.sessionsAreWipedWhenYou')}</p>
              </div>
              <div className="bg-lsc-cream dark:bg-lsc-dark/30 rounded-lg p-4 border border-lsc-border dark:border-earth-700">
                <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2 flex items-center gap-2">
                  <Lightbulb className="w-4 h-4 text-lsc-rose" aria-hidden="true" />
                  {t('about.transparent')}
                </h4>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t("about.everyFeatureIncludesPlainLanguage")} <Link to="/ai/how-it-works#rubric" className="text-lsc-rose underline underline-offset-2 hover:no-underline">View the scorecard</Link>.</p>
              </div>
            </div>
          </div>

          {/* Results + Honesty */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-8 border border-lsc-border dark:border-earth-700 mb-6">
            <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
              <Trophy className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
              {t('about.whatHappened')}
            </h3>
            <div className="grid md:grid-cols-3 gap-4 mb-6 text-center">
              <div>
                <div className="text-3xl font-bold text-lsc-rose mb-1">+34%</div>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('about.increaseCirculation')}</p>
              </div>
              <div>
                <div className="text-3xl font-bold text-lsc-rose mb-1">+89%</div>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('about.digitalResourceUsage')}</p>
              </div>
              <div>
                <div className="text-3xl font-bold text-lsc-rose mb-1">3 min</div>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('about.avgQuestionResolutionWas')}</p>
              </div>
            </div>

            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 leading-relaxed mb-4">
              <strong>{t('about.weHavenTCutA')}</strong> {t('about.noCutsText')}
            </p>

            <div className="bg-status-warning-50 dark:bg-status-warning-900/20 rounded-lg p-5 border border-status-warning-200 dark:border-status-warning-800 mb-6">
              <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">{t('about.whatWeWorryAbout2')}</h4>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 leading-relaxed">
                {t('about.whatWeWorryAboutText')}
              </p>
            </div>

            <div className="space-y-4">
              <blockquote className="bg-lsc-cream/50 dark:bg-lsc-dark/30 rounded-lg p-5 border-l-4 border-lsc-rose">
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm italic">{t('about.testimonial1Text')}</p>
                <cite className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream mt-1 block not-italic">{t('about.testimonial1Name')}</cite>
              </blockquote>
              <blockquote className="bg-lsc-cream/50 dark:bg-lsc-dark/30 rounded-lg p-5 border-l-4 border-lsc-rose">
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm italic">{t('about.testimonial2Text')}</p>
                <cite className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream mt-1 block not-italic">{t('about.testimonial2Name')}</cite>
              </blockquote>
            </div>
          </div>
        </div>
      </section>

      {/* Built for Everyone */}
      <section aria-labelledby="about-accessibility" className="py-16 bg-earth-50 dark:bg-earth-900">
        <div className="container mx-auto px-4 max-w-5xl">
          <div className="flex items-center gap-3 mb-3">
            <div className="flex-shrink-0 w-10 h-10 bg-sage-100 dark:bg-sage-800 rounded-full flex items-center justify-center">
              <Globe className="w-5 h-5 text-sage-600 dark:text-sage-400" aria-hidden="true" />
            </div>
            <h2 id="about-accessibility" className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              {t('about.builtForEveryone')}
            </h2>
          </div>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-8 ml-[52px]">
            {t('about.builtForEveryoneSub')}
          </p>

          <div className="grid md:grid-cols-2 gap-6 mb-6">
            <div className="bg-lsc-cream dark:bg-earth-700 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3">{t('about.accessibilityPresets')}</h3>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 leading-relaxed mb-4">
                {t('about.accessibilityPresetsText')}
              </p>
              <div className="flex flex-wrap gap-2">
                {[t('about.presetADHD'), t('about.presetDyslexia'), t('about.presetCalm'), t('about.presetSensory'), t('about.presetScreenReader'), t('about.presetMotor'), t('about.presetLowVision'), t('about.presetLightSensitive')].map((preset) => (
                  <span key={preset} className="inline-block text-sm px-3 py-1.5 bg-lsc-white dark:bg-earth-600 rounded-full text-lsc-dark/70 dark:text-lsc-cream/70 border border-lsc-border dark:border-earth-700">
                    {preset}
                  </span>
                ))}
              </div>
              <a href="/account?tab=accessibility" className="inline-block text-sm text-lsc-rose hover:underline mt-3">
                {t('about.enablePresets')}
              </a>
            </div>
            <div className="bg-lsc-cream dark:bg-earth-700 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3">{t('about.languageLiteracy')}</h3>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 leading-relaxed mb-4">
                {t('about.languageLiteracyText')}
              </p>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 leading-relaxed">
                {t('about.interfaceAdapts')}
              </p>
            </div>
          </div>

          <div className="bg-sage-50 dark:bg-sage-900/30 rounded-xl p-6 border border-sage-200 dark:border-sage-800">
            <div className="flex items-start gap-3">
              <Code className="w-5 h-5 text-sage-600 dark:text-sage-400 mt-0.5 flex-shrink-0" aria-hidden="true" />
              <div>
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">{t('about.poweredByOpenSource2')}</h3>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 leading-relaxed">
                  {t('about.poweredByOpenSourceText')} <a href="https://github.com/luminarynerds/l30" target="_blank" rel="noopener noreferrer" className="text-lsc-rose underline underline-offset-2 hover:no-underline">View source</a>.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* When Someone Wants a Book Removed */}
      <section aria-labelledby="about-challenges" className="py-16 bg-lsc-white dark:bg-earth-800">
        <div className="container mx-auto px-4 max-w-5xl">
          <div className="flex items-center gap-3 mb-6">
            <div className="flex-shrink-0 w-10 h-10 bg-sage-100 dark:bg-sage-800 rounded-full flex items-center justify-center">
              <Scale className="w-5 h-5 text-sage-600 dark:text-sage-400" aria-hidden="true" />
            </div>
            <h2 id="about-challenges" className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              {t('about.bookRemoval')}
            </h2>
          </div>

          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 leading-relaxed mb-6 max-w-3xl">
            {t('about.bookRemovalIntro')}
          </p>

          <div className="grid md:grid-cols-2 gap-6 mb-6">
            <div className="bg-lsc-cream dark:bg-earth-700 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">{t('about.ourPosition')}</h3>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 leading-relaxed text-sm">
                {t('about.ourPositionText')}
              </p>
            </div>
            <div className="bg-lsc-cream dark:bg-earth-700 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">{t('about.theProcess')}</h3>
              <ol className="space-y-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                <li className="flex gap-2">
                  <span className="text-lsc-rose font-bold flex-shrink-0">1.</span>
                  <span>{t('about.submitAFormalRequestFor')} <Link to="/contact" className="text-lsc-rose underline underline-offset-2 hover:no-underline">Submit one</Link>.</span>
                </li>
                <li className="flex gap-2">
                  <span className="text-lsc-rose font-bold flex-shrink-0">2.</span>
                  <span>{t('about.requesterMustHaveReadThe')}</span>
                </li>
                <li className="flex gap-2">
                  <span className="text-lsc-rose font-bold flex-shrink-0">3.</span>
                  <span>{t('about.aReviewCommitteeStaffCommunity')}</span>
                </li>
                <li className="flex gap-2">
                  <span className="text-lsc-rose font-bold flex-shrink-0">4.</span>
                  <span>{t('about.committeeEvaluatesAgainstOurCollection')}</span>
                </li>
                <li className="flex gap-2">
                  <span className="text-lsc-rose font-bold flex-shrink-0">5.</span>
                  <span>{t('about.writtenDecisionIssuedWithinDays')}</span>
                </li>
                <li className="flex gap-2">
                  <span className="text-lsc-rose font-bold flex-shrink-0">6.</span>
                  <span>{t('about.theBookStaysOnThe')}</span>
                </li>
              </ol>
            </div>
          </div>

          <div className="bg-sage-50 dark:bg-sage-900/30 rounded-xl p-6 border border-sage-200 dark:border-sage-800 mb-6">
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">{t('about.transparencyReport')}</h3>
            <div className="grid grid-cols-3 gap-4 text-center mb-4">
              <div>
                <div className="text-2xl font-bold text-sage-700 dark:text-sage-400">
                  {totalChallenges ?? '---'}
                </div>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('about.formalChallenges')}</p>
              </div>
              <div>
                <div className="text-2xl font-bold text-sage-700 dark:text-sage-400">
                  {booksRetained ?? '---'}
                </div>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('about.retainedOnShelfAfterReview')}</p>
              </div>
              <div>
                <div className="text-2xl font-bold text-sage-700 dark:text-sage-400">
                  {booksRemoved ?? '---'}
                </div>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('about.booksRemovedDueToA')}</p>
              </div>
            </div>
          </div>

          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm leading-relaxed max-w-3xl">
            {t('about.alaStatement')}{' '}
            <a href={`mailto:${branding.contact_email}`} className="text-lsc-rose hover:underline">{branding.contact_email || t("about.emailContactFallback", "Email us")}</a>.
          </p>
        </div>
      </section>

      {/* Meet the Staff */}
      <section aria-labelledby="about-staff" className="py-16 bg-lsc-cream dark:bg-lsc-dark">
        <div className="container mx-auto px-4 max-w-5xl">
          <div className="flex items-center gap-3 mb-3">
            <div className="flex-shrink-0 w-10 h-10 bg-sage-100 dark:bg-sage-800 rounded-full flex items-center justify-center">
              <Users className="w-5 h-5 text-sage-600 dark:text-sage-400" aria-hidden="true" />
            </div>
            <h2 id="about-staff" className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              {t('about.meetTheStaff')}
            </h2>
          </div>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-8 ml-[52px]">
            {t('about.meetTheStaffSub')}
          </p>

          {staffLoading ? (
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6" aria-busy="true">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="bg-lsc-white dark:bg-earth-700 rounded-xl p-5 border border-lsc-border dark:border-earth-700 motion-safe:animate-pulse">
                  <div className="w-14 h-14 bg-earth-200 dark:bg-earth-600 rounded-full mx-auto mb-3" />
                  <div className="h-4 bg-earth-200 dark:bg-earth-600 rounded w-2/3 mx-auto mb-2" />
                  <div className="h-3 bg-earth-200 dark:bg-earth-600 rounded w-1/2 mx-auto mb-2" />
                  <div className="h-3 bg-earth-200 dark:bg-earth-600 rounded w-3/4 mx-auto" />
                </div>
              ))}
            </div>
          ) : staffBios && staffBios.length > 0 ? (
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
              {/* TODO(sam): upload staff photos via /admin/about-us — currently falling back to initials */}
              {staffBios.map((member: StaffBio, index: number) => (
                <div
                  key={member.id}
                  className="bg-lsc-white dark:bg-earth-700 rounded-xl p-5 text-center border border-lsc-border dark:border-earth-700"
                >
                  <StaffAvatar
                    name={member.staff_name}
                    photoUrl={member.photo_url}
                    colorClass={STAFF_COLORS[index % STAFF_COLORS.length] ?? ''}
                  />
                  <h3 className="font-bold text-lsc-dark dark:text-lsc-cream text-sm">
                    {formatDisplayName(member.staff_name)}
                  </h3>
                  <p className="text-sm text-lsc-rose dark:text-lsc-rose-light font-medium mb-1">{member.role}</p>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{member.bio}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center text-lsc-dark/70 dark:text-lsc-cream/70">{t('about.staffInformationComingSoon')}</p>
          )}
        </div>
      </section>

      {/* Our Locations */}
      <section aria-labelledby="about-locations" className="py-12 bg-lsc-white dark:bg-earth-800">
        <div className="container mx-auto px-4 max-w-5xl">
          <div className="flex items-center gap-3 mb-8">
            <div className="flex-shrink-0 w-10 h-10 bg-sage-100 dark:bg-sage-800 rounded-full flex items-center justify-center">
              <MapPin className="w-5 h-5 text-sage-600 dark:text-sage-400" aria-hidden="true" />
            </div>
            <h2 id="about-locations" className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              {t('about.ourLocations')}
            </h2>
          </div>

          {/* Intro: voice of the page — multi-branch system, each location its own focus */}
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
            {t('about.locationsIntro', "We're a multi-branch system. Each location has its own focus.")}
          </p>

          {branchesLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6" aria-busy="true">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="bg-lsc-cream dark:bg-earth-700 rounded-xl border border-lsc-border dark:border-earth-700 motion-safe:animate-pulse overflow-hidden">
                  <div className="aspect-video bg-earth-200 dark:bg-earth-600" />
                  <div className="p-5">
                    <div className="h-5 bg-earth-200 dark:bg-earth-600 rounded w-1/3 mb-2" />
                    <div className="h-4 bg-earth-200 dark:bg-earth-600 rounded w-2/3" />
                  </div>
                </div>
              ))}
            </div>
          ) : branches && branches.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {branches.map((branch: Branch) => {
                const isBookmobile = branch.branch_type === 'bookmobile'
                const address = isBookmobile ? null : formatAddress(branch)
                // Slug for fallback static-map image at /images/maps/{slug}.webp
                // TODO(sam): drop real per-branch map images at /public/images/maps/{code}.webp — all 4 branches done
                const slug = (branch.code || branch.short_name || branch.name).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
                const accessibility = branch.is_ada_accessible
                  ? t('about.locationAccessibilityAccessible', 'Accessible entrance, parking on-site')
                  : t('about.locationAccessibilityCheck', 'Call ahead for accessibility details')
                return (
                  <BranchLocationCard
                    key={branch.id}
                    branch={branch}
                    address={address}
                    slug={slug}
                    isBookmobile={isBookmobile}
                    accessibility={accessibility}
                    fallbackHours={t('about.locationHoursDefault', 'See main branch hours')}
                  />
                )
              })}
            </div>
          ) : (
            <p className="text-center text-lsc-dark/70 dark:text-lsc-cream/70">{t('about.branchInformationComingSoon')}</p>
          )}
        </div>
      </section>

      {/* Coming Up */}
      <section aria-labelledby="about-roadmap" className="py-12 bg-earth-50 dark:bg-earth-900">
        <div className="container mx-auto px-4 max-w-3xl">
          <div className="flex items-center gap-3 mb-6">
            <div className="flex-shrink-0 w-10 h-10 bg-lsc-rose/10 rounded-full flex items-center justify-center">
              <Target className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
            </div>
            <h2 id="about-roadmap" className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              {t('about.whatsNext')}
            </h2>
          </div>
          <div className="space-y-4">
            {[
              { quarter: 'Summer 2026', milestone: t('about.roadmapQ2'), status: 'in-progress' },
              { quarter: 'Fall 2026', milestone: t('about.roadmapQ3'), status: 'upcoming' },
              { quarter: 'Winter 2026', milestone: t('about.roadmapQ4'), status: 'upcoming' },
              { quarter: '2027', milestone: t('about.roadmap2027'), status: 'upcoming' },
            ].map((item) => (
              <div key={item.quarter} className="flex items-center gap-4">
                <span className="flex-shrink-0 w-20 text-right text-sm font-bold text-lsc-rose">
                  {item.quarter}
                </span>
                <div className={`flex-shrink-0 w-3 h-3 rounded-full ${item.status === 'in-progress' ? 'bg-lsc-rose ring-2 ring-lsc-rose/30' : 'bg-earth-300 dark:bg-earth-600'}`} />
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">{item.milestone}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Contact CTA */}
      <section aria-labelledby="about-contact" className="py-12 bg-lsc-cream dark:bg-lsc-dark">
        <div className="container mx-auto px-4 max-w-2xl text-center">
          <h2 id="about-contact" className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">
            {t('about.thisIsYourLibrary')}
          </h2>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-8">
            {t('about.thisIsYourLibrarySub')}
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-8">
            <a
              href="/card-application"
              className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-lsc-rose hover:bg-lsc-rose/90 text-white font-medium rounded-xl transition-colors"
            >
              Get a library card
              <ArrowRight className="w-4 h-4" aria-hidden="true" />
            </a>
            <a
              href="/events"
              className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-lsc-white dark:bg-earth-700 hover:bg-sage-50 dark:hover:bg-earth-600 text-lsc-dark dark:text-lsc-cream font-medium rounded-xl border border-lsc-border dark:border-earth-700 transition-colors"
            >
              See what is on
            </a>
            <a
              href="/contact"
              className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-lsc-white dark:bg-earth-700 hover:bg-sage-50 dark:hover:bg-earth-600 text-lsc-dark dark:text-lsc-cream font-medium rounded-xl border border-lsc-border dark:border-earth-700 transition-colors"
            >
              Contact us
            </a>
          </div>

          <div className="flex items-center justify-center gap-6 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            <a href={`mailto:${branding.contact_email}`} className="flex items-center gap-2 hover:text-lsc-rose hover:underline transition-colors">
              <Mail className="w-4 h-4" aria-hidden="true" />
              {branding.contact_email || t("about.emailContactFallback", "Email us")}
            </a>
            {branding.phone && <a href={`tel:${branding.phone.replace(/\D/g, '')}`} className="flex items-center gap-2 hover:text-lsc-rose hover:underline transition-colors">
              <Phone className="w-4 h-4" aria-hidden="true" />
              {branding.phone}
            </a>}
          </div>
        </div>
      </section>

    </StandardPageLayout>
  );
}
