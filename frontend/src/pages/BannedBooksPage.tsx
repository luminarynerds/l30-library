/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useRef, useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { Link } from 'react-router-dom'
import {
  BookOpen, Shield, Scale, ExternalLink, FileText,
  AlertTriangle, TrendingUp,
  Send, Loader2, ChevronDown, ChevronUp, ShieldAlert, Megaphone, ChevronRight
} from 'lucide-react'
import {
  getPublicStats,
  getIntellectualFreedomResources,
  submitReconsiderationRequest,
  getReadingPrograms,
  CHALLENGE_REASON_LABELS,
  type ChallengeReason,
  type ReconsiderationRequest,
} from '../api/api'
import TransparencyLog from '@/components/banned-books/TransparencyLog'
import { useTranslation} from '@/i18n'
import { nextBannedBooksWeek } from '@/utils/bannedBooksWeek'
import { friendlyErrorMessage } from '@/utils/friendlyError'
import { TurnstileWidget } from '@/components/TurnstileWidget'
import PageContainer from '@/components/layout/PageContainer'

const INITIAL_FORM: ReconsiderationRequest = {
  title: '',
  author: null,
  isbn: null,
  primary_reason: '',
  challenger_complaint: '',
  challenger_name: '',
  challenger_contact: null,
  has_read_material: false,
  turnstile_token: null,
}

export default function BannedBooksPage() {
  const { t } = useTranslation()
  const bannedBooksWeek = nextBannedBooksWeek()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<ReconsiderationRequest>({ ...INITIAL_FORM })
  const [formError, setFormError] = useState<string | null>(null)

  const titleRef = useRef<HTMLInputElement>(null)
  const reasonRef = useRef<HTMLSelectElement>(null)
  const complaintRef = useRef<HTMLTextAreaElement>(null)
  const nameRef = useRef<HTMLInputElement>(null)
  const readRef = useRef<HTMLInputElement>(null)

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['publicChallengeStats'],
    queryFn: getPublicStats,
  })

  const { data: resources, isLoading: resourcesLoading } = useQuery({
    queryKey: ['intellectualFreedomResources'],
    queryFn: () => getIntellectualFreedomResources(),
  })

  // The signup CTA below lands on the seeded Banned Books Week program. A fork that
  // hasn't run the Task 5 seeder has no such program, so probe for it and
  // fall back to the plain programs list rather than a search with zero
  // results. active_only: true matches ReadingProgramsPage's own default
  // filter (ReadingProgramsPage.tsx:26) -- a librarian can deactivate the
  // program once the week ends, and the destination page would filter it
  // out even though this probe found it. Filtering the probe the same way
  // keeps "found" meaning "findable at the destination."
  const { data: bbwProgram } = useQuery({
    queryKey: ['bannedBooksWeekProgram'],
    queryFn: async () => {
      const programs = await getReadingPrograms({ active_only: true })
      return programs.find(p => /banned books week/i.test(p.name)) ?? null
    },
    staleTime: 5 * 60 * 1000,
  })
  const bbwProgramHref = bbwProgram ? '/programs?q=Banned+Books+Week' : '/programs'
  const bannedBooksCatalogHref = `/catalog?q=${encodeURIComponent([
    'Adventures of Huckleberry Finn',
    'The Wonderful Wizard of Oz',
    'Ulysses',
    'Leaves of Grass',
    "Uncle Tom's Cabin",
  ].map(title => `"${title}"`).join(' OR '))}`

  const submitMutation = useMutation({
    mutationFn: (data: ReconsiderationRequest) => submitReconsiderationRequest(data),
    onSuccess: (response) => {
      toast.success(response.message)
      setForm({ ...INITIAL_FORM })
      setFormError(null)
      setShowForm(false)
    },
    onError: (error: Error) => {
      const msg = friendlyErrorMessage(error)
      toast.error(msg)
      setFormError(msg)
    },
  })

  const failValidation = (
    msg: string,
    ref: React.RefObject<HTMLElement>
  ) => {
    setFormError(msg)
    toast.error(msg)
    setTimeout(() => ref.current?.focus(), 0)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)
    if (!form.title.trim()) {
      failValidation(t('bannedBooks.pleaseEnterTheTitleOf', 'Please enter the title of the material.'), titleRef)
      return
    }
    if (!form.primary_reason) {
      failValidation(t('bannedBooks.pleaseSelectAReason', 'Please select a primary reason.'), reasonRef)
      return
    }
    if (!form.challenger_complaint.trim()) {
      failValidation(t('bannedBooks.pleaseDescribeYourConcern', 'Please describe your concern.'), complaintRef)
      return
    }
    if (!form.challenger_name.trim()) {
      failValidation(t('bannedBooks.pleaseEnterYourName', 'Please enter your name.'), nameRef)
      return
    }
    if (!form.has_read_material) {
      failValidation(t('bannedBooks.youMustConfirmThatYou', 'Please confirm you have read or viewed the material in its entirety.'), readRef)
      return
    }
    submitMutation.mutate(form)
  }

  return (
    <PageContainer className="py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-4">
          <Shield className="w-10 h-10 text-lsc-rose dark:text-lsc-rose-light" />
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
            {t('bannedBooks.intellectualFreedomAmpBannedBooks', 'Intellectual Freedom & Banned Books')}
          </h1>
        </div>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-lg max-w-3xl">
          {t('bannedBooks.librariesAreBastionsOfIntellectual', 'Libraries are bastions of intellectual freedom. We believe in the right to read, the freedom of thought, and access to diverse perspectives. Here you can learn about our commitment to these values and how we handle challenges to library materials.')}
        </p>
      </div>

      {/* Mission Statement */}
      <section className="mb-12 bg-lsc-rose/10 dark:bg-lsc-rose/20 rounded-xl p-6 border border-lsc-rose/20">
        <div className="flex items-start gap-4">
          <Scale className="w-8 h-8 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-1" />
          <div>
            <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
              {t('bannedBooks.ourCommitment', 'Our Commitment')}
            </h2>
            <p className="text-lsc-dark/80 dark:text-lsc-cream/90">
              {t('bannedBooks.l30CommunityLibraryIsCommitted', "Our library is committed to providing materials that represent diverse viewpoints on a wide range of topics. We support the freedom to read and oppose censorship. When materials are challenged, we follow a fair and transparent review process guided by the American Library Association's Library Bill of Rights.")}
            </p>
          </div>
        </div>
      </section>

      {/* Hero CTA: Read a Banned Book */}
      <section className="mb-12">
        <div className="bg-gradient-to-r from-lsc-rose/20 to-lsc-brown/20 dark:from-lsc-rose/30 dark:to-lsc-brown/30 rounded-xl p-6 border border-lsc-rose/20">
          <div className="flex items-center gap-3 mb-3">
            <BookOpen className="w-8 h-8 text-lsc-rose dark:text-lsc-rose-light" />
            <h2 className="font-serif text-2xl font-semibold text-lsc-dark dark:text-lsc-cream">
              {t('bannedBooks.readABannedBook', 'Read a Banned Book')}
            </h2>
          </div>
          <p className="text-lsc-dark/80 dark:text-lsc-cream/90 mb-4 max-w-3xl">
            {t('bannedBooks.exploreTheBooksOurCommunity', 'Explore the books our community and others have challenged. Every banned book is a story someone tried to silence — and every checkout is a quiet act of support for the freedom to read.')}
          </p>
          <div className="flex flex-wrap gap-3">
            <Link
              to={bannedBooksCatalogHref}
              className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors font-medium"
            >
              <BookOpen className="w-4 h-4" />
              {t('bannedBooks.browseBannedBooksInOur', 'Browse Banned Books in Our Catalog')}
            </Link>
            <a
              href="https://www.ala.org/bbooks/frequentlychallengedbooks/top10"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream border border-lsc-border dark:border-earth-700 rounded-lg hover:shadow-md transition-shadow font-medium"
            >
              {t('bannedBooks.viewFrequentlyChallengedBooksAla', 'View Frequently Challenged Books (ALA)')}
              <ExternalLink className="w-4 h-4" />
            </a>
            <a
              href="#banned-books-week"
              className="inline-flex items-center gap-2 px-4 py-2 text-lsc-rose dark:text-lsc-rose-light hover:underline font-medium"
            >
              {t('bannedBooks.signUpForBannedBooksWeek', 'Sign Up for Banned Books Week')}
              <ChevronRight className="w-4 h-4" />
            </a>
          </div>
        </div>
      </section>

      {/* Current national context */}
      <section className="mb-12" aria-labelledby="national-context-heading">
        <div className="flex items-center gap-2 mb-4">
          <ShieldAlert className="w-6 h-6 text-lsc-rose dark:text-lsc-rose-light" />
          <h2 id="national-context-heading" className="font-serif text-2xl font-semibold text-lsc-dark dark:text-lsc-cream">
            {t('bannedBooks.nationalContext', 'National Context: 2025 Data')}
          </h2>
        </div>
        <div className="rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 p-6 space-y-4">
          <p className="text-lsc-dark/80 dark:text-lsc-cream/90">
            {t('bannedBooks.nationalContextAla', "The American Library Association documented 4,235 unique titles challenged in 2025. It reports that 92% of challenges were initiated by pressure groups, government officials, or other decision makers, while fewer than 3% originated with individual parents.")}
          </p>
          <p className="text-lsc-dark/80 dark:text-lsc-cream/90">
            {t('bannedBooks.nationalContextPen', 'PEN America separately recorded 6,870 instances of school book bans affecting nearly 4,000 unique titles during the 2024-25 school year. These totals use different definitions, sources, and reporting periods, so they should not be added together.')}
          </p>
          <p className="text-lsc-dark/80 dark:text-lsc-cream/90">
            {t('bannedBooks.nationalContextEvidence', 'The pattern is organized as well as local. In a recorded 2024 coalition webinar, a rating-site founder described using BookLooks ratings and compiling district data to help trigger statewide removals. The linked evidence record includes the recording, transcript excerpts, and source grading.')}
          </p>
          <div className="flex flex-wrap gap-x-5 gap-y-2 text-sm">
            <a href="https://www.ala.org/bbooks/book-ban-data" target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-lsc-rose hover:underline">
              {t('bannedBooks.ala2025Data', 'ALA 2025 data and methodology')} <ExternalLink className="w-3 h-3" aria-hidden="true" />
            </a>
            <a href="https://pen.org/book-bans/pen-america-index-of-school-book-bans-2024-2025/" target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-lsc-rose hover:underline">
              {t('bannedBooks.pen2025Index', 'PEN America 2024-25 index')} <ExternalLink className="w-3 h-3" aria-hidden="true" />
            </a>
            <a href="https://moms4all.org/rating-machine/#BBA-1075" target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-lsc-rose hover:underline">
              {t('bannedBooks.organizedCampaignEvidence', 'Documented campaign example (BBA-1075)')} <ExternalLink className="w-3 h-3" aria-hidden="true" />
            </a>
          </div>
          <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60">
            {t('bannedBooks.nationalDataCaveat', 'National figures are snapshots of reported incidents; many challenges are never reported. Local statistics below describe this library only.')}
          </p>
        </div>
      </section>

      {/* Statistics */}
      <section className="mb-12">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp className="w-6 h-6 text-lsc-rose dark:text-lsc-rose-light" />
          <h2 className="font-serif text-2xl font-semibold text-lsc-dark dark:text-lsc-cream">
            {t('bannedBooks.challengeStatistics', 'Challenge Statistics')}
          </h2>
          <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60 ml-1">{t('bannedBooks.allTime', 'All Time')}</span>
        </div>
        {statsLoading ? (
          <div className="motion-safe:animate-pulse grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="h-24 bg-lsc-cream dark:bg-earth-800 rounded-lg" />
            ))}
          </div>
        ) : stats ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg p-4 border border-lsc-border dark:border-earth-700 text-center">
              <div className="text-3xl font-bold text-lsc-rose dark:text-lsc-rose-light">
                {stats.total_challenges}
              </div>
              <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                {t('bannedBooks.totalChallenges', 'Total Challenges')}
              </div>
            </div>
            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg p-4 border border-lsc-border dark:border-earth-700 text-center">
              <div className="text-3xl font-bold text-lsc-rose dark:text-lsc-rose-light">
                {stats.pending_challenges}
              </div>
              <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                {t('bannedBooks.open', 'Open')}
              </div>
            </div>
            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg p-4 border border-lsc-border dark:border-earth-700 text-center">
              <div className="text-3xl font-bold text-status-success-600 dark:text-status-success-400">
                {stats.resolved_this_year}
              </div>
              <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                {t('bannedBooks.resolvedThisYear', 'Resolved This Year')}
              </div>
            </div>
            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg p-4 border border-lsc-border dark:border-earth-700 text-center">
              <div className="text-3xl font-bold text-status-success-600 dark:text-status-success-400">
                {stats.outcomes?.retained || 0}
              </div>
              <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                {t('bannedBooks.booksRetained', 'Books Retained')}
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-lsc-cream dark:bg-earth-800 rounded-lg p-6 border border-lsc-border dark:border-earth-700 text-center">
            <TrendingUp className="w-12 h-12 text-lsc-rose/50 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-lsc-dark dark:text-lsc-cream mb-2">
              {t('bannedBooks.statisticsNotAvailable', 'Statistics Not Available')}
            </h3>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
              {t('bannedBooks.challengeStatisticsWillBeDisplayed', 'Challenge statistics will be displayed here as data becomes available.')}
            </p>
          </div>
        )}
      </section>

      {/* Educational Resources */}
      <section className="mb-12">
        <div className="flex items-center gap-2 mb-4">
          <BookOpen className="w-6 h-6 text-lsc-rose dark:text-lsc-rose-light" />
          <h2 className="font-serif text-2xl font-semibold text-lsc-dark dark:text-lsc-cream">
            {t('bannedBooks.learnAboutIntellectualFreedom', 'Learn About Intellectual Freedom')}
          </h2>
        </div>

        {resourcesLoading ? (
          <div className="motion-safe:animate-pulse space-y-4">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-24 bg-lsc-cream dark:bg-earth-800 rounded-lg" />
            ))}
          </div>
        ) : resources && resources.length > 0 ? (
          <div className="grid md:grid-cols-2 gap-4">
            {resources.map(resource => (
              <div
                key={resource.id}
                className="bg-lsc-white dark:bg-earth-800 rounded-lg p-5 border border-lsc-border dark:border-earth-700 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start gap-3">
                  <div className="p-2 bg-lsc-cream dark:bg-earth-700 rounded-lg">
                    {resource.resource_type === 'policy' ? (
                      <FileText className="w-5 h-5 text-lsc-rose" />
                    ) : resource.resource_type === 'external_link' ? (
                      <ExternalLink className="w-5 h-5 text-lsc-rose" />
                    ) : (
                      <BookOpen className="w-5 h-5 text-lsc-rose" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-1">
                      {resource.title}
                    </h3>
                    {resource.description && (
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                        {resource.description}
                      </p>
                    )}
                    {resource.url && (
                      <a
                        href={resource.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-lsc-rose hover:underline inline-flex items-center gap-1"
                        aria-label={t('aria.bannedBooks.learnMoreAboutX', { title: resource.title })}
                      >
                        {t('bannedBooks.learnMore', 'Learn more')} <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="bg-lsc-cream dark:bg-earth-800 rounded-lg p-6 border border-lsc-border dark:border-earth-700">
            <div className="grid md:grid-cols-2 gap-4">
              <a
                href="https://www.ala.org/bbooks"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-3 p-4 bg-lsc-white dark:bg-earth-700 rounded-lg hover:shadow-md transition-shadow"
              >
                <ExternalLink className="w-5 h-5 text-lsc-rose" />
                <div>
                  <div className="font-medium text-lsc-dark dark:text-lsc-cream">{t('bannedBooks.alaBannedBooks', 'ALA Banned Books')}</div>
                  <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    {t('bannedBooks.americanLibraryAssociationResources', 'American Library Association resources')}
                  </div>
                </div>
              </a>
              <a
                href="https://www.ala.org/advocacy/intfreedom/librarybill"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-3 p-4 bg-lsc-white dark:bg-earth-700 rounded-lg hover:shadow-md transition-shadow"
              >
                <ExternalLink className="w-5 h-5 text-lsc-rose" />
                <div>
                  <div className="font-medium text-lsc-dark dark:text-lsc-cream">{t('bannedBooks.libraryBillOfRights', 'Library Bill of Rights')}</div>
                  <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    {t('bannedBooks.corePrinciplesOfIntellectual', 'Core principles of intellectual freedom')}
                  </div>
                </div>
              </a>
            </div>
          </div>
        )}
      </section>

      {/* Our Challenge Stories */}
      <section className="mb-12">
        <div className="flex items-center gap-2 mb-4">
          <AlertTriangle className="w-6 h-6 text-lsc-rose dark:text-lsc-rose-light" />
          <h2 className="font-serif text-2xl font-semibold text-lsc-dark dark:text-lsc-cream">
            {t('bannedBooks.ourChallengeStories', 'Our Challenge Stories')}
          </h2>
        </div>
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
          {t('bannedBooks.transparencyIsImportantToUs', 'Transparency is important to us. Here are some of the challenges our library has faced and how we responded. We share these stories to help our community understand our commitment to intellectual freedom.')}
        </p>

        <TransparencyLog />
      </section>

      {/* Request for Reconsideration */}
      <section className="mb-12">
        <div className="flex items-center gap-2 mb-4">
          <FileText className="w-6 h-6 text-lsc-rose dark:text-lsc-rose-light" />
          <h2 className="font-serif text-2xl font-semibold text-lsc-dark dark:text-lsc-cream">
            {t('bannedBooks.requestForReconsideration', 'Request for Reconsideration')}
          </h2>
        </div>
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg p-6 border border-lsc-border dark:border-earth-700">
          <p className="text-lsc-dark/80 dark:text-lsc-cream/90 mb-4">
            {t('bannedBooks.ifYouHaveConcernsAbout', 'If you have concerns about a library material, we encourage you to speak with a librarian first. If you would like to submit a formal request for reconsideration, you may use the form below or pick up a paper form at the circulation desk.')}
          </p>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
            {t('bannedBooks.duringTheReviewProcessThe', 'During the review process, the challenged material will remain available to all patrons. You will receive a written response within 30 days.')}
          </p>

          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
            {t('bannedBooks.youllNeedTheTitle', "You'll need the title of the material and a description of your concern. Takes about 5 minutes.")}
          </p>
          <button
            type="button"
            onClick={() => setShowForm(!showForm)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors font-medium"
          >
            <FileText className="w-4 h-4" />
            {t('bannedBooks.submitRequestOnline', 'Submit a Request Online')}
            {showForm ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>

          {showForm && (
            <form onSubmit={handleSubmit} noValidate className="mt-6 space-y-5 border-t border-lsc-border dark:border-earth-700 pt-6">
              {formError && (
                <div
                  role="alert"
                  aria-live="assertive"
                  data-testid="reconsideration-form-error"
                  className="rounded-lg border border-status-danger-300 bg-status-danger-50 dark:bg-status-danger-900/20 px-4 py-3 text-sm text-status-danger-800 dark:text-status-danger-200"
                >
                  {formError}
                </div>
              )}
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="rc-title" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                    {t('bannedBooks.titleOfMaterial', 'Title of Material')} <span className="text-status-danger-500" aria-hidden="true">*</span>
                  </label>
                  <input
                    ref={titleRef}
                    id="rc-title"
                    type="text"
                    required
                    aria-required="true"
                    maxLength={250}
                    value={form.title}
                    onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-lsc-rose"
                    placeholder={t('placeholder.bannedBooks.egTheCatcherIn')}
                  />
                </div>
                <div>
                  <label htmlFor="rc-author" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                    {t('bannedBooks.author', 'Author')}
                  </label>
                  <input
                    id="rc-author"
                    type="text"
                    maxLength={200}
                    value={form.author || ''}
                    onChange={e => setForm(f => ({ ...f, author: e.target.value || null }))}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-lsc-rose"
                    placeholder={t('placeholder.bannedBooks.egJdSalinger')}
                  />
                </div>
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="rc-isbn" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                    {t('bannedBooks.isbnIfKnown', 'ISBN (if known)')}
                  </label>
                  <input
                    id="rc-isbn"
                    type="text"
                    maxLength={20}
                    value={form.isbn || ''}
                    onChange={e => setForm(f => ({ ...f, isbn: e.target.value || null }))}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-lsc-rose"
                    placeholder={t('placeholder.bannedBooks.eg9780316769480')}
                  />
                </div>
                <div>
                  <label htmlFor="rc-reason" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                    {t('bannedBooks.primaryReasonForConcern', 'Primary Reason for Concern')} <span className="text-status-danger-500" aria-hidden="true">*</span>
                  </label>
                  <select
                    ref={reasonRef}
                    id="rc-reason"
                    required
                    aria-required="true"
                    value={form.primary_reason}
                    onChange={e => setForm(f => ({ ...f, primary_reason: e.target.value as ChallengeReason | '' }))}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-lsc-rose"
                  >
                    <option value="" disabled>{t('bannedBooks.selectAReason', 'Select a reason...')}</option>
                    {(Object.entries(CHALLENGE_REASON_LABELS) as [ChallengeReason, string][]).map(
                      ([value, label]) => (
                        <option key={value} value={value}>{label}</option>
                      )
                    )}
                  </select>
                </div>
              </div>

              <div>
                <label htmlFor="rc-complaint" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  {t('bannedBooks.describeYourConcern', 'Describe Your Concern')} <span className="text-status-danger-500" aria-hidden="true">*</span>
                </label>
                <textarea
                  ref={complaintRef}
                  id="rc-complaint"
                  required
                  aria-required="true"
                  maxLength={5000}
                  rows={4}
                  value={form.challenger_complaint}
                  onChange={e => setForm(f => ({ ...f, challenger_complaint: e.target.value }))}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-lsc-rose"
                  placeholder={t('bannedBooks.pleaseDescribeYourSpecificConcerns', 'Please describe your specific concerns about this material...')}
                />
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="rc-name" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                    {t('bannedBooks.yourName', 'Your Name')} <span className="text-status-danger-500" aria-hidden="true">*</span>
                  </label>
                  <input
                    ref={nameRef}
                    id="rc-name"
                    type="text"
                    required
                    aria-required="true"
                    maxLength={200}
                    value={form.challenger_name}
                    onChange={e => setForm(f => ({ ...f, challenger_name: e.target.value }))}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-lsc-rose"
                    placeholder={t('placeholder.bannedBooks.yourFullName')}
                  />
                </div>
                <div>
                  <label htmlFor="rc-contact" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                    {t('bannedBooks.emailForFollowup', 'Email for Follow-up')}
                  </label>
                  <input
                    id="rc-contact"
                    type="email"
                    inputMode="email"
                    autoComplete="email"
                    maxLength={200}
                    value={form.challenger_contact || ''}
                    onChange={e => setForm(f => ({ ...f, challenger_contact: e.target.value || null }))}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-lsc-rose"
                    placeholder={t('bannedBooks.howCanWeReachYou', 'How can we reach you with our response?')}
                  />
                </div>
              </div>

              <div className="flex items-start gap-3">
                <input
                  ref={readRef}
                  id="rc-read"
                  type="checkbox"
                  required
                  aria-required="true"
                  checked={form.has_read_material}
                  onChange={e => setForm(f => ({ ...f, has_read_material: e.target.checked }))}
                  className="mt-1 h-4 w-4 text-lsc-rose border-lsc-border rounded focus:ring-lsc-rose"
                />
                <label htmlFor="rc-read" className="text-sm text-lsc-dark/80 dark:text-lsc-cream/90">
                  {t('bannedBooks.iConfirmThatIHave', 'I confirm that I have read or viewed the material in its entirety.')} <span className="text-status-danger-500" aria-hidden="true">*</span>
                </label>
              </div>

              <TurnstileWidget
                onVerify={token => setForm(f => ({ ...f, turnstile_token: token || null }))}
                className="my-2"
              />

              <div className="flex items-center gap-3 pt-2">
                <button
                  type="submit"
                  disabled={submitMutation.isPending}
                  aria-busy={submitMutation.isPending}
                  className="inline-flex items-center gap-2 px-5 py-2.5 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {submitMutation.isPending ? (
                    <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                  ) : (
                    <Send className="w-4 h-4" />
                  )}
                  {submitMutation.isPending ? t('bannedBooks.submitting', 'Submitting...') : t('bannedBooks.submitRequest', 'Submit Request')}
                </button>
                <button
                  type="button"
                  onClick={() => { setShowForm(false); setForm({ ...INITIAL_FORM }); setFormError(null) }}
                  className="px-4 py-2.5 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream transition-colors"
                >
                  {t('common.cancel', 'Cancel')}
                </button>
              </div>
            </form>
          )}
        </div>
      </section>

      {/* Banned Books Week */}
      <section id="banned-books-week" className="mb-12 scroll-mt-24">
        <div className="rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 p-6">
          <h2 className="text-xs font-medium uppercase tracking-[0.18em] text-lsc-dark/60 dark:text-lsc-cream/60">
            {t('bannedBooks.bannedBooksWeek', 'Banned Books Week')}
          </h2>

          {bannedBooksWeek && (
            <>
              <p className="mt-3 font-serif text-4xl sm:text-5xl font-bold leading-none text-lsc-dark dark:text-lsc-cream">
                {bannedBooksWeek.formatted}
              </p>
              <hr className="my-5 border-0 border-t border-lsc-border dark:border-earth-700" />
              {bannedBooksWeek.theme && <blockquote className="font-serif text-lg italic text-lsc-dark/90 dark:text-lsc-cream/90">
                &ldquo;{bannedBooksWeek.theme}&rdquo;
                {/* <cite>, not <footer>: index.css:438 styles every `footer`
                    as the site footer under .high-contrast (black background,
                    !important), which rendered this attribution dark-on-black
                    at 1.15:1. <cite> is the element for a quotation's source
                    anyway, and it does not collide with that global rule. */}
                <cite className="mt-1 block text-sm not-italic text-lsc-dark/60 dark:text-lsc-cream/60">
                  {t('bannedBooks.themeAttribution', '2026 campaign theme, Banned Books Week Coalition')}
                </cite>
              </blockquote>}
              {bannedBooksWeek.freedomReadDay && <p className="mt-4 text-sm font-medium text-lsc-dark/80 dark:text-lsc-cream/80">
                {t('bannedBooks.freedomReadDayX', {
                  date: bannedBooksWeek.freedomReadDay.toLocaleDateString(undefined, {
                    weekday: 'long', month: 'long', day: 'numeric',
                  }),
                })}
              </p>}
            </>
          )}
          <p className="text-lsc-dark/80 dark:text-lsc-cream/90 mb-4">
            {t('bannedBooks.everyYearDuringTheLast', 'Libraries across the country mark Banned Books Week together. We join in with displays, discussions, and events built around the books people have tried to pull off the shelf.')}
          </p>
          <div className="flex flex-wrap gap-3 items-center">
            <Link
              to={bbwProgramHref}
              className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors font-medium"
            >
              <BookOpen className="w-4 h-4" />
              {t('bannedBooks.joinBannedBooksWeek', 'Join Banned Books Week')}
            </Link>
            <a
              href="https://bannedbooksweek.org"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-lsc-rose hover:text-lsc-rose/80 font-medium"
            >
              {t('bannedBooks.learnMoreAboutBannedBooksWeek', 'Learn more about Banned Books Week')} <ExternalLink className="w-4 h-4" />
            </a>
          </div>
        </div>
      </section>

      {/* Related Pages */}
      <section>
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
          {t('bannedBooks.exploreMore', 'Explore More')}
        </h2>
        <div className="grid md:grid-cols-2 gap-4">
          <Link
            to="/ban-tracker"
            className="group flex items-center gap-4 p-5 bg-lsc-white/60 dark:bg-lsc-dark/40 rounded-xl border border-lsc-brown/10 dark:border-lsc-cream/10 hover:border-lsc-rose/30 dark:hover:border-lsc-rose/30 transition-all hover:shadow-md"
          >
            <div className="flex-shrink-0 w-12 h-12 rounded-lg bg-status-danger-100 dark:bg-status-danger-900/30 flex items-center justify-center">
              <ShieldAlert className="w-6 h-6 text-status-danger-600 dark:text-status-danger-400" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream group-hover:text-lsc-rose transition-colors">
                {t('bannedBooks.nationalBanTracker', 'National Ban Tracker')}
              </h3>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
                {t('bannedBooks.nationalBanTrackerDesc', 'Explore reported book bans and challenges from across the country, with source and coverage details.')}
              </p>
            </div>
            <ChevronRight className="w-5 h-5 text-lsc-dark/30 dark:text-lsc-cream/60 group-hover:text-lsc-rose transition-colors" />
          </Link>
          <Link
            to="/advocacy"
            className="group flex items-center gap-4 p-5 bg-lsc-white/60 dark:bg-lsc-dark/40 rounded-xl border border-lsc-brown/10 dark:border-lsc-cream/10 hover:border-lsc-rose/30 dark:hover:border-lsc-rose/30 transition-all hover:shadow-md"
          >
            <div className="flex-shrink-0 w-12 h-12 rounded-lg bg-status-warning-100 dark:bg-status-warning-900/30 flex items-center justify-center">
              <Megaphone className="w-6 h-6 text-status-warning-600 dark:text-status-warning-400" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream group-hover:text-lsc-rose transition-colors">
                {t('bannedBooks.takeAction', 'Take Action')}
              </h3>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
                {t('bannedBooks.takeActionDesc', 'Find your representatives and use letter templates to advocate against book bans.')}
              </p>
            </div>
            <ChevronRight className="w-5 h-5 text-lsc-dark/30 dark:text-lsc-cream/60 group-hover:text-lsc-rose transition-colors" />
          </Link>
        </div>
      </section>
    </PageContainer>
  )
}
