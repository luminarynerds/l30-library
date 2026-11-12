/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Search, IdCard, Printer, DoorOpen, ArrowRight, BookOpen } from 'lucide-react'
import { useTranslation } from '@/i18n/I18nContext'
import { useBranding } from '@/contexts/BrandingContext'
import { useOrganizationFeatures } from '../contexts/OrganizationFeaturesContext'
import { useRecentSearches } from '@/hooks/useRecentSearches'

interface HeroSectionProps {
  title?: string
  subtitle?: string
  onSearch?: (query: string) => void
  showSearchChips?: boolean
}

const HeroSection: React.FC<HeroSectionProps> = ({
  title,
  subtitle,
  onSearch,
  showSearchChips = true,
}) => {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [searchQuery, setSearchQuery] = useState('')
  const [searchFocused, setSearchFocused] = useState(false)
  const branding = useBranding()
  const { isFeatureEnabled } = useOrganizationFeatures()
  const { addRecentSearch, getFilteredSearches } = useRecentSearches()

  const displayTitle = branding.hero_title || title || t('home.hero.title')
  const hasHero = Boolean(branding.hero_image_url)

  const subtitleClosing = branding.hero_subtitle || subtitle || t('home.hero.subtitle.closing') as string

  const handleSearch = () => {
    const query = searchQuery.trim()
    if (query) addRecentSearch(query)
    if (onSearch) {
      onSearch(query)
    } else if (query) {
      navigate(`/catalog?q=${encodeURIComponent(query)}`)
    }
  }
  const searchSuggestions = getFilteredSearches(searchQuery).slice(0, 4)

  const highlights = [
    ...(isFeatureEnabled('front_desk_enabled') ? [{ icon: IdCard, label: t('home.hero.highlights.getCard'), link: '/get-started' }] : []),
    ...(isFeatureEnabled('meeting_rooms_enabled') ? [{ icon: DoorOpen, label: t('home.hero.highlights.bookSpace'), link: '/rooms' }] : []),
    ...(isFeatureEnabled('front_desk_enabled') ? [{ icon: Printer, label: t('home.hero.highlights.printScan'), link: '/tech' }] : []),
  ]

  const searchChips = [
    { key: 'new', label: t('libraryExperience.browseNew', 'New arrivals'), href: '/catalog?is_new=true' },
    { key: 'largeprint', label: t('libraryExperience.browseLargePrint', 'Large print'), href: '/catalog?is_large_print=true' },
    { key: 'audio', label: t('libraryExperience.browseAudio', 'Audiobooks'), href: '/catalog?type=audiobook' },
  ]

  return (
    <section
      className={
        hasHero
          ? '-mt-8 relative pt-12 pb-4'
          : 'relative overflow-hidden max-w-5xl mx-auto pt-2 pb-4 px-4 sm:px-6 rounded-xl bg-gradient-to-b from-lsc-cream/30 via-lsc-cream/10 to-brand-50/40 dark:from-lsc-dark dark:via-lsc-dark dark:to-lsc-brown/60'
      }
    >
      {/* Tenant hero image (e.g. a photo of the library building). When set it
          breaks out to the full page width behind the editorial copy, drifts
          with a slow Ken Burns zoom (disabled under reduced-motion), and keeps
          a cream scrim anchored on the text side so the copy stays readable
          while the building shows through on the right. Decorative. */}
      {hasHero ? (
        <div
          className="absolute inset-y-0 left-1/2 -translate-x-1/2 w-screen overflow-hidden z-0"
          aria-hidden="true"
        >
          <div
            className="l30-ken-burns absolute inset-0 bg-cover bg-center"
            style={{ backgroundImage: `url(${branding.hero_image_url})` }}
          />
          <div className="l30-grain absolute inset-0" />
          <div className="absolute inset-0 bg-gradient-to-r from-lsc-cream via-lsc-cream/90 to-lsc-cream/40 dark:from-lsc-dark dark:via-lsc-dark/90 dark:to-lsc-dark/40" />
          <div className="absolute inset-0 bg-gradient-to-t from-lsc-cream/70 to-transparent dark:from-lsc-dark/70" />
        </div>
      ) : (
        <div className="l30-grain" aria-hidden="true" />
      )}

      <div className={hasHero ? 'relative z-10 max-w-6xl mx-auto px-4 sm:px-6' : 'relative z-10'}>
      {/* Editorial hero */}
      <div className="mb-6 md:mb-8">
        <p className="font-mono text-xs normal-case text-lsc-rose dark:text-lsc-rose mb-3">
          {branding.tagline || t('home.hero.tagline')}
        </p>

        <h1 className="font-serif text-3xl sm:text-4xl md:text-5xl text-lsc-dark dark:text-lsc-cream leading-[1.15] mb-4 min-w-0 [overflow-wrap:anywhere]">
          {displayTitle.split('<br/>').map((line, i) => (
            <React.Fragment key={i}>
              {line.split(/(<em>.*?<\/em>)/g).map((segment, j) => {
                const emMatch = /^<em>(.*?<\/em>)$/.exec(segment)
                if (emMatch?.[1]) {
                  return (
                    <span key={j} className="text-sage-600 dark:text-lsc-rose not-italic">
                      {emMatch[1].replace(/<\/em>$/, '')}
                    </span>
                  )
                }
                return <React.Fragment key={j}>{segment}</React.Fragment>
              })}
              {i < displayTitle.split('<br/>').length - 1 && <br />}
            </React.Fragment>
          ))}
        </h1>

        <div className="max-w-2xl space-y-4">
          {subtitleClosing && (
            <p className="text-base md:text-lg text-earth-800 dark:text-earth-300 leading-relaxed">
              {subtitleClosing}
            </p>
          )}
        </div>
      </div>

      {/* Search */}
      <div className="max-w-2xl mb-4">
        <h2 className="font-serif text-xl md:text-2xl text-lsc-dark dark:text-lsc-cream mb-4">
          {t('libraryExperience.searchHeading', 'Search catalog')}
        </h2>
        <div className="relative">
          <label htmlFor="search" className="sr-only">
            {t('home.hero.searchLabel')}
          </label>
          <div className="relative">
            <div className="absolute inset-y-0 left-4 sm:left-5 flex items-center pointer-events-none">
              <Search className="h-5 w-5 text-earth-600 dark:text-earth-400" aria-hidden="true" />
            </div>
            <input
              type="search"
              id="search"
              className="block w-full pl-12 sm:pl-14 pr-24 sm:pr-32 py-4 sm:py-5 rounded-xl border border-lsc-border dark:border-earth-700/50 bg-lsc-white dark:bg-earth-800/30 text-lsc-dark dark:text-lsc-cream placeholder:text-earth-600 dark:placeholder:text-earth-400 focus:ring-2 focus:ring-sage-500 dark:focus:ring-lsc-rose focus:border-sage-400 dark:focus:border-lsc-rose/50 focus:outline-none motion-safe:transition-colors duration-300"
              placeholder={t('home.hero.searchPlaceholder')}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onFocus={() => setSearchFocused(true)}
              onBlur={() => window.setTimeout(() => setSearchFocused(false), 150)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            />
            <button
              onClick={handleSearch}
              type="button"
              className="absolute right-2 sm:right-3 top-2 sm:top-3 bottom-2 sm:bottom-3 px-4 sm:px-6 bg-lsc-dark dark:bg-lsc-cream hover:bg-lsc-dark/90 dark:hover:bg-lsc-cream/90 text-white dark:text-lsc-dark rounded-xl font-medium focus-visible:ring-2 focus-visible:ring-sage-500 focus-visible:ring-offset-2 focus-visible:outline-none motion-safe:transition-[background-color,transform] motion-safe:duration-150 motion-safe:ease-out motion-safe:active:scale-[0.97]"
            >
              {t('home.hero.searchButton')}
            </button>
          </div>
          {searchFocused && searchSuggestions.length > 0 && (
            <ul
              className="absolute z-20 mt-2 w-full overflow-hidden rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 shadow-soft-sm origin-top motion-safe:animate-scale-in"
              aria-label={t('home.hero.recentSearches', 'Recent searches')}
            >
              {searchSuggestions.map((search) => (
                <li key={search.query}>
                  <button
                    type="button"
                    className="w-full px-4 py-3 text-left text-sm text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-sage-500"
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => {
                      setSearchQuery(search.query)
                      addRecentSearch(search.query)
                      navigate(`/catalog?q=${encodeURIComponent(search.query)}`)
                    }}
                  >
                    <span className="font-medium">{search.query}</span>
                    <span className="ml-2 text-earth-600 dark:text-earth-400">{t('home.hero.recentSearch', 'recent search')}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {showSearchChips && (
          <details className="mt-2">
            <summary className="cursor-pointer min-h-[44px] py-3 text-sm text-earth-700 dark:text-earth-300 rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sage-500">
              {t('libraryExperience.browseFormats', 'Browse by format')}
            </summary>
            <div className="pb-2 flex flex-wrap items-center gap-2">
            {searchChips.map((chip) => (
              <button
                key={chip.key}
                type="button"
                onClick={() => {
                  navigate(chip.href)
                }}
                className="text-xs font-medium px-3 py-2.5 min-h-[44px] rounded-lg bg-lsc-white dark:bg-earth-800 hover:bg-rose-50 dark:hover:bg-earth-700 text-lsc-dark dark:text-earth-200 border border-rose-200 dark:border-earth-600 hover:border-rose-300 dark:hover:border-earth-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sage-500 focus-visible:ring-offset-2 motion-safe:transition-[background-color,border-color,transform] motion-safe:duration-150 motion-safe:ease-out motion-safe:active:scale-[0.97]"
              >
                {chip.label}
              </button>
            ))}
            </div>
          </details>
        )}
      </div>

      {/* Quick actions (secondary) */}
      <div className="flex flex-wrap gap-x-5 gap-y-1 mb-2">
        {highlights.map((item) => (
          <Link
            key={item.label}
            to={item.link}
            className="group inline-flex min-h-[44px] items-center gap-2 rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sage-500 text-sm text-earth-700 hover:text-sage-700 dark:text-earth-300 dark:hover:text-lsc-rose no-underline motion-safe:transition-colors duration-300"
          >
            <item.icon className="w-4 h-4 text-sage-600 dark:text-lsc-rose" aria-hidden="true" />
            <span>{item.label}</span>
            <ArrowRight className="w-3 h-3 motion-safe:transition-transform motion-safe:duration-200 motion-safe:ease-out group-hover:translate-x-0.5" aria-hidden="true" />
          </Link>
        ))}
      </div>

      {branding.seasonal_callout_active && (
      <div className="mt-8 p-4 rounded-xl bg-sage-50/50 dark:bg-sage-900/20 border border-sage-200/50 dark:border-sage-800/30">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-sage-100 dark:bg-sage-800/40 flex items-center justify-center flex-shrink-0">
            <BookOpen className="w-5 h-5 text-sage-600 dark:text-sage-400" aria-hidden="true" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
              {t('home.hero.readingProgram.title') || 'Summer Reading Challenge'}
            </p>
            <p className="text-xs text-earth-600 dark:text-earth-400 mt-0.5">
              {t('home.hero.readingProgram.subtitle') || 'Sign up for our summer reading program and earn prizes all season long.'}
            </p>
          </div>
          <Link
            to="/programs"
            className="flex-shrink-0 text-xs font-medium px-4 py-2.5 min-h-[44px] inline-flex items-center rounded-lg bg-sage-600 dark:bg-sage-700 text-white hover:bg-sage-700 dark:hover:bg-sage-600 transition-colors"
          >
            {t('home.hero.readingProgram.cta') || 'Sign Up'}
          </Link>
        </div>
      </div>
      )}
      </div>
    </section>
  )
}

export default HeroSection
