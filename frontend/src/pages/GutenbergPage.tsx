/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useMemo } from 'react'
import { useTranslation} from '@/i18n'
import { Link } from 'react-router-dom'
import { useOrganizationFeatures } from '@/contexts/OrganizationFeaturesContext'

import {
  BookOpen,
  Search,
  Download,
  ExternalLink,
  Globe,
  Clock,
  Heart,
  Users,
  Filter,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Library,
  ScrollText,
  Feather,
  AlertTriangle,
  TrendingDown,
  DollarSign,
  Hammer,
  ArrowRight,
  PenLine,
  ShieldCheck,
} from 'lucide-react'
import PageContainer from '@/components/layout/PageContainer'

interface Genre {
  id: string
  name: string
  icon: React.ElementType
  description: string
  sampleTitles: string[]
}

interface FAQ {
  questionKey: string
  question: string
  answerKey: string
  answer: string
}

const faqs: FAQ[] = [
  {
    questionKey: 'gutenberg.faqWhatIsProjectGutenbergQ',
    question: 'What is Project Gutenberg?',
    answerKey: 'gutenberg.faqWhatIsProjectGutenbergA',
    answer: 'Project Gutenberg is the oldest digital library, founded in 1971. It offers over 75,000 free eBooks, primarily works that have entered the public domain in the United States. These are books whose copyright has expired, making them freely available to everyone.',
  },
  {
    questionKey: 'gutenberg.faqAreTheseBooksReallyQ',
    question: 'Are these books really free?',
    answerKey: 'gutenberg.faqAreTheseBooksReallyA',
    answer: 'Yes, completely free with no strings attached. These books are in the public domain, which means their copyright has expired. You can download them, read them on any device, share them, and even use them for creative projects.',
  },
  {
    questionKey: 'gutenberg.faqWhatFormatsAreAvailableQ',
    question: 'What formats are available?',
    answerKey: 'gutenberg.faqWhatFormatsAreAvailableA',
    answer: 'Project Gutenberg offers books in multiple formats including EPUB (works with most e-readers), Kindle-compatible formats, HTML (read in your browser), and plain text. This means you can read on virtually any device.',
  },
  {
    questionKey: 'gutenberg.faqDoINeedALibraryQ',
    question: 'Do I need a library card?',
    answerKey: 'gutenberg.faqDoINeedALibraryA',
    answer: 'No library card needed. Project Gutenberg is completely separate from our library system - it\'s a free public resource available to everyone worldwide. We\'re just helping you discover it.',
  },
  {
    questionKey: 'gutenberg.faqWhatHappenedToOurQ',
    question: 'What happened to our old digital vendors?',
    answerKey: 'gutenberg.faqWhatHappenedToOurA',
    answer: 'We canceled our commercial digital platform contracts. The costs were unsustainable and the value kept shrinking, driven by private equity ownership. We reinvested those dollars in Palace Project (free, open-source ebooks), our Indie Authors program, MakerSpace 3.0, and free resources like Project Gutenberg.',
  },
  {
    questionKey: 'gutenberg.faqCanIUseTheseQ',
    question: 'Can I use these for school projects?',
    answerKey: 'gutenberg.faqCanIUseTheseA',
    answer: 'Absolutely. Public domain texts are perfect for academic use - you can quote them freely, analyze them, and reference them in papers. Just remember to cite your sources properly.',
  },
]

const quickStats = [
  { labelKey: 'gutenberg.freeEbooksStat', label: 'Free eBooks', value: '75,000+', icon: BookOpen },
  { labelKey: 'gutenberg.languagesStat', label: 'Languages', value: '60+', icon: Globe },
  { labelKey: 'gutenberg.yearsRunningStat', label: 'Years Running', value: '54', icon: Clock },
  { labelKey: 'gutenberg.volunteersWorldwideStat', label: 'Volunteers Worldwide', value: 'Thousands', icon: Users },
]

function GenreCard({ genre, expanded, onToggle }: {
  genre: Genre
  expanded: boolean
  onToggle: () => void
}): React.ReactElement {
  const { t } = useTranslation()
  const Icon = genre.icon
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm hover:shadow-md transition-shadow">
      <button
        onClick={onToggle}
        className="w-full p-5 flex items-start gap-4 text-left"
        aria-expanded={expanded}
        aria-controls={`genre-details-${genre.id}`}
      >
        <div className="w-12 h-12 rounded-xl bg-lsc-cream dark:bg-lsc-brown flex items-center justify-center flex-shrink-0">
          <Icon className="w-6 h-6 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
            {genre.name}
          </h3>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
            {genre.description}
          </p>
        </div>
        <div className="flex-shrink-0 text-lsc-dark/70 dark:text-lsc-cream/70">
          {expanded ? <ChevronUp aria-hidden="true" className="w-5 h-5" /> : <ChevronDown aria-hidden="true" className="w-5 h-5" />}
        </div>
      </button>

      {expanded && (
        <div id={`genre-details-${genre.id}`} className="px-5 pb-5 pt-0">
          <div className="border-t border-lsc-border dark:border-earth-700 pt-5">
            <p className="text-xs font-semibold text-lsc-dark dark:text-lsc-cream/90 uppercase tracking-wide mb-3">
              {t('gutenberg.popularTitles', 'Popular Titles')}
            </p>
            <ul className="space-y-2">
              {genre.sampleTitles.map((title, idx) => (
                <li key={idx} className="flex items-start gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  <BookOpen className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" aria-hidden="true" />
                  <span>{title}</span>
                </li>
              ))}
            </ul>
            <a
              href={`https://www.gutenberg.org/ebooks/bookshelf/${genre.id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 mt-4 text-sm font-medium text-lsc-rose dark:text-lsc-rose-light hover:underline"
            >
              {t('gutenberg.browseXOnGutenberg', { genre: genre.name })}
              <ExternalLink className="w-4 h-4" aria-hidden="true" />
            </a>
          </div>
        </div>
      )}
    </div>
  )
}

export default function GutenbergPage(): React.ReactElement {
  const { t } = useTranslation()
  const { isFeatureEnabled } = useOrganizationFeatures()
  const [expandedGenres, setExpandedGenres] = useState<Set<string>>(new Set())

  const genres: Genre[] = useMemo(() => [
    {
      id: 'fiction',
      name: t('gutenberg.genreFictionName', 'Fiction & Literature'),
      icon: BookOpen,
      description: t('gutenberg.genreFictionDesc', 'Classic novels, short stories, and literary masterpieces.'),
      sampleTitles: ['Pride and Prejudice', 'A Tale of Two Cities', 'The Adventures of Huckleberry Finn'],
    },
    {
      id: 'poetry',
      name: t('gutenberg.genrePoetryName', 'Poetry & Drama'),
      icon: Feather,
      description: t('gutenberg.genrePoetryDesc', 'Timeless poetry collections and plays.'),
      sampleTitles: ['The Complete Works of Shakespeare', 'Leaves of Grass', 'The Raven and Other Poems'],
    },
    {
      id: 'history',
      name: t('gutenberg.genreHistoryName', 'History & Biography'),
      icon: ScrollText,
      description: t('gutenberg.genreHistoryDesc', 'Historical accounts, memoirs, and biographies.'),
      sampleTitles: ['The Autobiography of Benjamin Franklin', 'The History of the Decline and Fall of the Roman Empire'],
    },
    {
      id: 'philosophy',
      name: t('gutenberg.genrePhilosophyName', 'Philosophy & Religion'),
      icon: Sparkles,
      description: t('gutenberg.genrePhilosophyDesc', 'Works of philosophy, religious texts, and ethical treatises.'),
      sampleTitles: ['Meditations by Marcus Aurelius', 'The Republic by Plato', 'Beyond Good and Evil'],
    },
    {
      id: 'science',
      name: t('gutenberg.genreScienceName', 'Science & Nature'),
      icon: Globe,
      description: t('gutenberg.genreScienceDesc', 'Scientific writings, natural history, and exploration.'),
      sampleTitles: ['On the Origin of Species', 'The Voyage of the Beagle', 'Principia Mathematica'],
    },
    {
      id: 'children',
      name: t('gutenberg.genreChildrenName', 'Children\'s Literature'),
      icon: Heart,
      description: t('gutenberg.genreChildrenDesc', 'Classic children\'s books, fairy tales, and adventures for young readers.'),
      sampleTitles: ['Alice\'s Adventures in Wonderland', 'Peter Pan', 'The Wonderful Wizard of Oz'],
    },
  ], [t])
  const [searchQuery, setSearchQuery] = useState('')

  const toggleGenre = (id: string): void => {
    setExpandedGenres(prev => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  const handleSearch = (e: React.FormEvent): void => {
    e.preventDefault()
    if (searchQuery.trim()) {
      window.open(
        `https://www.gutenberg.org/ebooks/search/?query=${encodeURIComponent(searchQuery)}`,
        '_blank',
        'noopener,noreferrer'
      )
    }
  }

  return (
    <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark">
      {/* Hero Section */}
      <div className="bg-lsc-white dark:bg-earth-800 border-b border-lsc-border dark:border-earth-700">
        <PageContainer className="py-12">
          <div className="flex items-start gap-4">
            <div className="p-3 bg-lsc-cream dark:bg-earth-800/30 rounded-xl">
              <Library className="w-8 h-8 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
            </div>
            <div className="flex-1">
              <h1 className="text-3xl md:text-4xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
                {t('gutenberg.projectGutenberg', 'Project Gutenberg')}
              </h1>
              <p className="text-lg text-lsc-dark/70 dark:text-lsc-cream/70">
                {t('gutenberg.freeEbooksNoWaitlistsNo', '70,000+ free eBooks. No waitlists. No library card needed. Yours to keep forever.')}
              </p>
            </div>
          </div>

          {/* Quick Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-8">
            {quickStats.map((stat) => {
              const Icon = stat.icon
              return (
                <div
                  key={stat.label}
                  className="bg-lsc-cream dark:bg-lsc-brown/30 rounded-xl p-4 text-center"
                >
                  <Icon className="w-6 h-6 mx-auto text-lsc-rose dark:text-lsc-rose-light mb-2" aria-hidden="true" />
                  <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{stat.value}</p>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t(stat.labelKey, stat.label)}</p>
                </div>
              )
            })}
          </div>
        </PageContainer>
      </div>

      {/* Why We're Winding Down Commercial Digital Platforms */}
      <div className="bg-status-warning-50 dark:bg-status-warning-900/30 border-b border-status-warning-200 dark:border-status-warning-800/50">
        <PageContainer className="py-10">
          <div className="flex items-start gap-3 mb-6">
            <div className="p-2 bg-status-warning-100 dark:bg-status-warning-900/50 rounded-lg flex-shrink-0">
              <AlertTriangle className="w-6 h-6 text-status-warning-600 dark:text-status-warning-400" aria-hidden="true" />
            </div>
            <div>
              <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                {t('gutenberg.whyWereCancelingCommercialDigital', "Why We're Canceling Commercial Digital Platforms")}
              </h2>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                {t('gutenberg.andWhyProjectGutenbergMatters', 'And why Project Gutenberg matters more than ever')}
              </p>
            </div>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 border border-status-warning-200 dark:border-status-warning-800/40">
              <div className="w-10 h-10 rounded-xl bg-status-danger-50 dark:bg-status-danger-900/30 flex items-center justify-center mb-3">
                <TrendingDown className="w-5 h-5 text-status-danger-500 dark:text-status-danger-400" aria-hidden="true" />
              </div>
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">{t('gutenberg.unsustainableCosts', 'Unsustainable Costs')}</h3>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                {t('gutenberg.eachYearWeSpentMore', 'Each year we spent more and received less value. The costs climbed at a pace we could not sustain. Stressful on staff, stressful on patrons, and the math stopped working.')}
              </p>
            </div>

            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 border border-status-warning-200 dark:border-status-warning-800/40">
              <div className="w-10 h-10 rounded-xl bg-status-warning-50 dark:bg-status-warning-900/30 flex items-center justify-center mb-3">
                <DollarSign className="w-5 h-5 text-status-warning-600 dark:text-status-warning-400" aria-hidden="true" />
              </div>
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">{t('gutenberg.privateEquityExtraction', 'Private Equity Extraction')}</h3>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                {t('gutenberg.ourVendorsWereAcquiredBy', 'Our vendors were acquired by private equity. The pattern is textbook: prices go up, licensing terms get worse, and the platform extracts more value from libraries while delivering less. We refused to keep feeding that cycle.')}
              </p>
            </div>

            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 border border-status-warning-200 dark:border-status-warning-800/40">
              <div className="w-10 h-10 rounded-xl bg-status-info-50 dark:bg-status-info-900/30 flex items-center justify-center mb-3">
                <ShieldCheck className="w-5 h-5 text-status-info-600 dark:text-status-info-400" aria-hidden="true" />
              </div>
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">{t('gutenberg.stewardsOfYourTaxDollars')}</h3>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                {t('gutenberg.weWantToBeGood', 'We want to be good stewards of your tax funds. Every dollar we sent to a private equity firm was a dollar that did not go back into our community.')}
              </p>
            </div>

            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 border border-status-warning-200 dark:border-status-warning-800/40">
              <div className="w-10 h-10 rounded-xl bg-status-success-50 dark:bg-status-success-900/30 flex items-center justify-center mb-3">
                <Hammer className="w-5 h-5 text-status-success-600 dark:text-status-success-400" aria-hidden="true" />
              </div>
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">{t('gutenberg.reinvestingInOurselves', 'Reinvesting in Ourselves')}</h3>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                {t('gutenberg.asASystemABoardAnd', 'As a system, a board, and a community, we decided to reinvest those dollars in ourselves:')} <strong>MakerSpace 3.0</strong>{t('gutenberg.ourXIndieAuthorLead', ', our')} <strong>Indie Author</strong>{t('gutenberg.programAndFreeResources', ' program, and free resources like Project Gutenberg.')}
              </p>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center">
            {isFeatureEnabled('makerspace_enabled') && (
              <Link
                to="/makerspace"
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-lsc-rose hover:bg-lsc-rose/90 text-white font-semibold rounded-xl transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lsc-rose"
              >
                <Hammer className="w-4 h-4" aria-hidden="true" />
                {t('gutenberg.exploreMakerspace30', 'Explore MakerSpace 3.0')}
                <ArrowRight className="w-4 h-4" aria-hidden="true" />
              </Link>
            )}
            <Link
              to="/digital"
              className="inline-flex items-center gap-2 text-sm font-medium text-lsc-rose dark:text-lsc-rose-light hover:underline"
            >
              {t('gutenberg.viewAllDigitalResources', 'View all digital resources')}
              <ArrowRight className="w-4 h-4" aria-hidden="true" />
            </Link>
          </div>
        </PageContainer>
      </div>


      <PageContainer className="py-8 space-y-12">
        {/* Search Section */}
        <section>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
            <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">
              {t('gutenberg.searchProjectGutenberg', 'Search Project Gutenberg')}
            </h2>
            <form onSubmit={handleSearch} className="flex gap-3">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" aria-hidden="true" />
                <input
                  type="text"
                  placeholder={t('gutenberg.searchByTitleAuthorOr')}
                  aria-label={t('aria.gutenberg.searchProjectGutenberg')}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                />
              </div>
              <button
                type="submit"
                className="px-6 py-3 bg-lsc-rose hover:bg-lsc-rose/90 text-white font-semibold rounded-xl transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lsc-rose dark:focus:ring-offset-earth-800"
              >
                {t('common.search')}
              </button>
            </form>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-3">
              {t('gutenberg.searchOpensInANew', 'Search opens in a new tab on gutenberg.org')}
            </p>
          </div>
        </section>

        {/* Quick Start */}
        <section>
          <div className="bg-lsc-cream dark:bg-lsc-brown/20 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
            <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">
              {t('gutenberg.quickStartGuide', 'Quick Start Guide')}
            </h2>
            <div className="grid md:grid-cols-3 gap-6">
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-lsc-rose text-white flex items-center justify-center flex-shrink-0 font-bold">
                  1
                </div>
                <div>
                  <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{t('gutenberg.browseOrSearch', 'Browse or Search')}</h3>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    {t('gutenberg.useTheSearchAbove', 'Use the search above or browse by genre below to find books.')}
                  </p>
                </div>
              </div>
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-lsc-rose text-white flex items-center justify-center flex-shrink-0 font-bold">
                  2
                </div>
                <div>
                  <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{t('gutenberg.chooseFormat', 'Choose Format')}</h3>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    {t('gutenberg.selectEpubForMost', 'Select EPUB for most e-readers, or HTML to read in your browser.')}
                  </p>
                </div>
              </div>
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-lsc-rose text-white flex items-center justify-center flex-shrink-0 font-bold">
                  3
                </div>
                <div>
                  <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{t('gutenberg.downloadAmpEnjoy', 'Download & Enjoy')}</h3>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    {t('gutenberg.itsYoursToKeep', "It's yours to keep forever. No due dates, no fees, no limits.")}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Browse by Genre */}
        <section>
          <div className="flex items-center gap-2 mb-4">
            <Filter className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
            <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              {t('gutenberg.browseByGenre', 'Browse by Genre')}
            </h2>
          </div>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
            {t('gutenberg.exploreTheClassicsClick', 'Explore the classics. Click any genre to see popular titles and browse the collection.')}
          </p>
          <div className="grid md:grid-cols-2 gap-4">
            {genres.map((genre) => (
              <GenreCard
                key={genre.id}
                genre={genre}
                expanded={expandedGenres.has(genre.id)}
                onToggle={() => toggleGenre(genre.id)}
              />
            ))}
          </div>
        </section>

        {/* Direct Links */}
        <section>
          <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">
            {t('gutenberg.quickLinks', 'Quick Links')}
          </h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <a
              href="https://www.gutenberg.org/browse/scores/top"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-3 p-4 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 hover:shadow-md transition-shadow"
            >
              <Sparkles className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
              <div>
                <p className="font-semibold text-lsc-dark dark:text-lsc-cream">{t('gutenberg.top100', 'Top 100')}</p>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('gutenberg.mostDownloadedBooks', 'Most downloaded books')}</p>
              </div>
            </a>
            <a
              href="https://www.gutenberg.org/browse/recent/last1"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-3 p-4 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 hover:shadow-md transition-shadow"
            >
              <Clock className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
              <div>
                <p className="font-semibold text-lsc-dark dark:text-lsc-cream">{t('gutenberg.newArrivals', 'New Arrivals')}</p>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('gutenberg.recentlyAddedBooks', 'Recently added books')}</p>
              </div>
            </a>
            <a
              href="https://www.gutenberg.org/browse/authors/a"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-3 p-4 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 hover:shadow-md transition-shadow"
            >
              <Users className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
              <div>
                <p className="font-semibold text-lsc-dark dark:text-lsc-cream">{t('gutenberg.byAuthor', 'By Author')}</p>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('gutenberg.browseAZByAuthor')}</p>
              </div>
            </a>
            <a
              href="https://www.gutenberg.org/browse/languages/"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-3 p-4 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 hover:shadow-md transition-shadow"
            >
              <Globe className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
              <div>
                <p className="font-semibold text-lsc-dark dark:text-lsc-cream">{t('gutenberg.byLanguage', 'By Language')}</p>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('gutenberg.booksIn60Languages', 'Books in 60+ languages')}</p>
              </div>
            </a>
          </div>
        </section>

        {/* Featured Recommendations */}
        <section>
          <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">
            {t('gutenberg.staffPicksWhereToStart', 'Staff Picks: Where to Start')}
          </h2>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
            {t('gutenberg.newToPublicDomainLiterature', 'New to public domain literature? Here are some timeless favorites to get you started.')}
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[
              { title: 'Pride and Prejudice', author: 'Jane Austen', url: 'https://www.gutenberg.org/ebooks/1342', why: t('gutenberg.theOriginalRomcom', 'The original rom-com') },
              { title: 'Frankenstein', author: 'Mary Shelley', url: 'https://www.gutenberg.org/ebooks/84', why: t('gutenberg.scifiBeforeScifiExisted', 'Sci-fi before sci-fi existed') },
              { title: 'The Great Gatsby', author: 'F. Scott Fitzgerald', url: 'https://www.gutenberg.org/ebooks/64317', why: t('gutenberg.jazzAgeClassic', 'Jazz age classic') },
              { title: 'Dracula', author: 'Bram Stoker', url: 'https://www.gutenberg.org/ebooks/345', why: t('gutenberg.theVampireNovel', 'The vampire novel') },
              { title: t('gutenberg.theAdventuresOfSherlockHolmes'), author: 'Arthur Conan Doyle', url: 'https://www.gutenberg.org/ebooks/1661', why: t('gutenberg.mysteryPerfected', 'Mystery perfected') },
              { title: 'Alice in Wonderland', author: 'Lewis Carroll', url: 'https://www.gutenberg.org/ebooks/11', why: t('gutenberg.wonderfullyWeird', 'Wonderfully weird') },
            ].map((book) => (
              <a
                key={book.title}
                href={book.url}
                target="_blank"
                rel="noopener noreferrer"
                className="group p-4 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 hover:shadow-md transition-shadow"
              >
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream group-hover:text-lsc-rose dark:group-hover:text-lsc-rose-light transition-colors">
                  {book.title}
                </h3>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{book.author}</p>
                <p className="text-xs text-lsc-rose dark:text-lsc-rose-light mt-2 italic">{book.why}</p>
              </a>
            ))}
          </div>
        </section>

        {/* Indie Author Selection */}
        <section>
          <div className="bg-gradient-to-br from-lsc-cream to-lsc-white dark:from-earth-800 dark:to-lsc-brown/20 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
            <div className="flex items-start gap-3 mb-2">
              <div className="p-2 bg-lsc-rose/10 dark:bg-lsc-rose/20 rounded-lg flex-shrink-0">
                <PenLine className="w-6 h-6 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
              </div>
              <div>
                <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                  {t('gutenberg.indieAuthorSelection', 'Indie Author Selection')}
                </h2>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                  {t('gutenberg.vettedIndependentAuthorsRightHere', 'Vetted independent authors, right here in our catalog. This is what reinvesting in ourselves looks like.')}
                </p>
              </div>
            </div>

            <div className="mt-6 grid md:grid-cols-2 gap-6">
              <div>
                <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/90 leading-relaxed">
                  {t('gutenberg.insteadOfSendingYourTax', "Instead of sending your tax dollars to a private equity firm for digital content we don't own, we're building something better. Our Indie Author program gives independent writers a platform - and gives you access to fresh, diverse voices that no algorithm at a corporate publisher would greenlight.")}
                </p>
                <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/90 leading-relaxed mt-3">
                  {t('gutenberg.everyTitleIsReviewedBy', "Every title is reviewed by library staff before it enters the collection. Between Gutenberg's 70,000 classics, our growing indie catalog, and more resources coming online shortly - we're building a digital collection that actually serves")} <em>{t('gutenberg.youEmphasis', 'you')}</em>{t('gutenberg.notShareholders', ', not shareholders.')}
                </p>
              </div>
              <div className="space-y-3">
                <div className="flex items-start gap-3 p-3 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700">
                  <PenLine className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" aria-hidden="true" />
                  <div>
                    <p className="font-semibold text-sm text-lsc-dark dark:text-lsc-cream">{t('gutenberg.staffVettedTitles', 'Staff-Vetted Titles')}</p>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{t('gutenberg.everyIndieBookIsReviewed')}</p>
                  </div>
                </div>
                <div className="flex items-start gap-3 p-3 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700">
                  <Heart className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" aria-hidden="true" />
                  <div>
                    <p className="font-semibold text-sm text-lsc-dark dark:text-lsc-cream">{t('gutenberg.supportRealAuthors', 'Support Real Authors')}</p>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{t('gutenberg.yourReadsDirectlySupportIndependent')}</p>
                  </div>
                </div>
                <div className="flex items-start gap-3 p-3 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700">
                  <Sparkles className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" aria-hidden="true" />
                  <div>
                    <p className="font-semibold text-sm text-lsc-dark dark:text-lsc-cream">{t('gutenberg.freshVoices', 'Fresh Voices')}</p>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{t('gutenberg.discoverGenresPerspectivesAndStories')}</p>
                  </div>
                </div>
              </div>
            </div>

            {isFeatureEnabled('indie_platform_enabled') && (
              <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center mt-6 pt-6 border-t border-lsc-border dark:border-earth-700">
                <Link
                  to="/indie/discover"
                  className="inline-flex items-center gap-2 px-5 py-2.5 bg-lsc-rose hover:bg-lsc-rose/90 text-white font-semibold rounded-xl transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lsc-rose"
                >
                  <PenLine className="w-4 h-4" aria-hidden="true" />
                  {t('gutenberg.browseIndieAuthors', 'Browse Indie Authors')}
                  <ArrowRight className="w-4 h-4" aria-hidden="true" />
                </Link>
                <Link
                  to="/indie"
                  className="inline-flex items-center gap-2 text-sm font-medium text-lsc-rose dark:text-lsc-rose-light hover:underline"
                >
                  {t('gutenberg.viewFullIndieCatalog', 'View full indie catalog')}
                  <ArrowRight className="w-4 h-4" aria-hidden="true" />
                </Link>
              </div>
            )}
          </div>
        </section>

        {/* Digital Reading Options */}
        <section>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
            <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
              {t('gutenberg.lifeAfterCommercialVendorsWhere', 'Life After Commercial Vendors: Where to Find What You Need')}
            </h2>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
              {t('gutenberg.weWalkedAwayFromThe', 'We walked away from the vendor treadmill. Here is how to keep reading digitally.')}
            </p>
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="p-4 bg-lsc-cream dark:bg-lsc-brown/30 rounded-xl">
                <div className="flex items-center gap-2 mb-3">
                  <Library className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
                  <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{t('gutenberg.projectGutenberg', 'Project Gutenberg')}</h3>
                </div>
                <p className="text-xs font-semibold text-status-success-600 dark:text-status-success-400 mb-2">{t('gutenberg.freeForever', 'FREE FOREVER')}</p>
                <ul className="space-y-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  <li className="flex items-start gap-2">
                    <Download className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" aria-hidden="true" />
                    <span>{t('gutenberg.classicEbooksYouOwnForever', '70,000+ classic eBooks you own forever')}</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <Download className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" aria-hidden="true" />
                    <span>{t('gutenberg.noWaitlistsNoDueDates')}</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <Download className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" aria-hidden="true" />
                    <span>{t('gutenberg.perfectForClassicsAndSchool')}</span>
                  </li>
                </ul>
              </div>
              <div className="p-4 bg-lsc-cream dark:bg-lsc-brown/30 rounded-xl">
                <div className="flex items-center gap-2 mb-3">
                  <PenLine className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
                  <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{t('gutenberg.indieAuthors', 'Indie Authors')}</h3>
                </div>
                <p className="text-xs font-semibold text-category-600 dark:text-category-400 mb-2">{t('gutenberg.staffVetted', 'STAFF-VETTED')}</p>
                <ul className="space-y-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  <li className="flex items-start gap-2">
                    <PenLine className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" aria-hidden="true" />
                    <span>{t('gutenberg.freshTitlesFromIndependentWriters')}</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <PenLine className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" aria-hidden="true" />
                    <span>{t('gutenberg.everyBookReviewedByLibrary')}</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <PenLine className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" aria-hidden="true" />
                    <span>{t('gutenberg.supportAuthorsDirectlyNotMiddlemen')}</span>
                  </li>
                </ul>
                {isFeatureEnabled('indie_platform_enabled') && (
                  <Link
                    to="/indie/discover"
                    className="inline-flex items-center gap-1 mt-3 text-sm font-medium text-lsc-rose dark:text-lsc-rose-light hover:underline"
                  >
                    {t('gutenberg.browseIndieCatalog', 'Browse indie catalog')}
                    <ArrowRight className="w-4 h-4" aria-hidden="true" />
                  </Link>
                )}
              </div>
              <div className="p-4 bg-lsc-cream dark:bg-lsc-brown/30 rounded-xl">
                <div className="flex items-center gap-2 mb-3">
                  <BookOpen className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
                  <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{t('gutenberg.palaceProject', 'Palace Project')}</h3>
                </div>
                <p className="text-xs font-semibold text-status-success-600 dark:text-status-success-400 mb-2">{t('gutenberg.freeAmpOpenSource')}</p>
                <ul className="space-y-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  <li className="flex items-start gap-2">
                    <BookOpen className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" aria-hidden="true" />
                    <span>{t('gutenberg.ebooksAndAudiobooksBuiltBy', 'eBooks and audiobooks, built by libraries')}</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <BookOpen className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" aria-hidden="true" />
                    <span>{t('gutenberg.noWaitlistsInstantBorrowing')}</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <BookOpen className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" aria-hidden="true" />
                    <span>{t('gutenberg.noCorporateMiddlemenOrTracking')}</span>
                  </li>
                </ul>
              </div>
              <div className="p-4 bg-lsc-cream dark:bg-lsc-brown/30 rounded-xl">
                <div className="flex items-center gap-2 mb-3">
                  <Hammer className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
                  <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">MakerSpace 3.0</h3>
                </div>
                <p className="text-xs font-semibold text-lsc-rose dark:text-lsc-rose-light mb-2">{t('gutenberg.whereTheMoneyGoes')}</p>
                <ul className="space-y-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  <li className="flex items-start gap-2">
                    <Hammer className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" aria-hidden="true" />
                    <span>{t('gutenberg.threeDPrintingLaserCutting', '3D printing, laser cutting, electronics')}</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <Hammer className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" aria-hidden="true" />
                    <span>{t('gutenberg.mediaStudioAndRecording')}</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <Hammer className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" aria-hidden="true" />
                    <span>{t('gutenberg.workshopsAndTraining', 'Workshops and training')}</span>
                  </li>
                </ul>
                {isFeatureEnabled('makerspace_enabled') && (
                  <Link
                    to="/makerspace"
                    className="inline-flex items-center gap-1 mt-3 text-sm font-medium text-lsc-rose dark:text-lsc-rose-light hover:underline"
                  >
                    {t('gutenberg.exploreMakerspace30', 'Explore MakerSpace 3.0')}
                    <ArrowRight className="w-4 h-4" aria-hidden="true" />
                  </Link>
                )}
              </div>
            </div>
          </div>
        </section>

        {/* FAQ Section */}
        <section>
          <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">
            {t('gutenberg.commonQuestions', 'Common Questions')}
          </h2>
          <div className="grid md:grid-cols-2 gap-4">
            {faqs.map((faq) => (
              <div
                key={faq.question}
                className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 border border-lsc-border dark:border-earth-700"
              >
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
                  {t(faq.questionKey, faq.question)}
                </h3>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  {t(faq.answerKey, faq.answer)}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* Footer CTA */}
        <section className="text-center py-8">
          <a
            href="https://www.gutenberg.org/"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-8 py-4 bg-lsc-rose hover:bg-lsc-rose/90 text-white font-semibold rounded-xl transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-lsc-rose dark:focus:ring-offset-lsc-dark"
          >
            <Library className="w-5 h-5" aria-hidden="true" />
            {t('gutenberg.visitProjectGutenberg', 'Visit Project Gutenberg')}
            <ExternalLink className="w-4 h-4" aria-hidden="true" />
          </a>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-4 italic">
            {t('gutenberg.aLibraryToModifyThe', '"A library, to modify the famous metaphor of Socrates, should be the delivery room for the birth of ideas."')}
            <br />
            - Norman Cousins
          </p>
        </section>
      </PageContainer>
    </div>
  )
}
