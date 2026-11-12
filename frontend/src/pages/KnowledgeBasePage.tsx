/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useMemo, useEffect } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  BookOpen,
  Search,
  HelpCircle,
  FileText,
  Lightbulb,
  ThumbsUp,
  Tag,
  ChevronRight,
  Loader2,
  X,
  GitFork,
  MessageCircle,
  AlertCircle,
} from 'lucide-react'
import toast from 'react-hot-toast'
import {
  getKnowledgeBaseEntries,
  getKnowledgeBaseEntry,
  markEntryHelpful,
  getReadAlikes,
  getFAQs,
  getKnowledgeBaseCategoryCounts,
  type KnowledgeBaseEntry,
} from '@/api/knowledge-base-api'
import { useTranslation} from '@/i18n'
import DecisionTreeBrowser from '@/components/knowledge-base/DecisionTreeBrowser'
import { useOrganizationFeatures, type OrganizationFeatures } from '@/contexts/OrganizationFeaturesContext'
import { usePageTitle } from '@/hooks/usePageTitle'
import { useRequireRole } from '@/hooks/useRequireRole'
import { Link } from 'react-router-dom'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import PageContainer from '@/components/layout/PageContainer'

const ENTRY_TYPE_KEYS = [
  { value: 'faq', labelKey: 'knowledgeBase.entryType.faq', icon: HelpCircle },
  { value: 'guide', labelKey: 'knowledgeBase.entryType.guide', icon: BookOpen },
  { value: 'policy', labelKey: 'knowledgeBase.entryType.policy', icon: FileText },
  { value: 'how-to', labelKey: 'knowledgeBase.entryType.howTo', icon: Lightbulb },
  { value: 'read-alike', labelKey: 'knowledgeBase.entryType.readAlike', icon: BookOpen },
] as const

// Maps backend entry_type values to translation keys for rendering localized labels
const ENTRY_TYPE_LABEL_KEYS: Record<string, string> = {
  'faq': 'knowledgeBase.entryType.faq',
  'guide': 'knowledgeBase.entryType.guide',
  'policy': 'knowledgeBase.entryType.policy',
  'how-to': 'knowledgeBase.entryType.howTo',
  'read-alike': 'knowledgeBase.entryType.readAlike',
}

const CATEGORY_DEFINITIONS: { value: string; featureFlag?: keyof OrganizationFeatures }[] = [
  { value: 'Account & Membership' },
  { value: 'Borrowing & Returns' },
  { value: 'Digital Resources' },
  { value: 'Events & Programs', featureFlag: 'events_enabled' },
  { value: 'Services' },
  { value: 'Policies' },
  { value: 'Technology Help' },
  { value: 'Reading Programs', featureFlag: 'reading_programs_enabled' },
  { value: 'AI Tools', featureFlag: 'ai_tools_enabled' },
  { value: 'Learning & Courses', featureFlag: 'learning_platform_enabled' },
  { value: 'Indie Catalog', featureFlag: 'indie_platform_enabled' },
]

// Maps backend category values to translation keys for rendering localized labels
const CATEGORY_LABEL_KEYS: Record<string, string> = {
  'Account & Membership': 'knowledgeBase.category.accountMembership',
  'Borrowing & Returns': 'knowledgeBase.category.borrowingReturns',
  'Digital Resources': 'knowledgeBase.category.digitalResources',
  'Events & Programs': 'knowledgeBase.category.eventsPrograms',
  'Services': 'knowledgeBase.category.services',
  'Policies': 'knowledgeBase.category.policies',
  'Technology Help': 'knowledgeBase.category.technologyHelp',
  'Reading Programs': 'knowledgeBase.category.readingPrograms',
  'AI Tools': 'knowledgeBase.category.aiTools',
  'Learning & Courses': 'knowledgeBase.category.learningCourses',
  'Indie Catalog': 'knowledgeBase.category.indieCatalog',
}

export default function KnowledgeBasePage(): React.ReactElement {
  const { t } = useTranslation()
  const { isFeatureEnabled } = useOrganizationFeatures()
  // Decision trees are staff-only; hide the Troubleshooting tab from
  // patrons and anonymous visitors so it is not a dead, empty tab.
  const { isAuthorized: canSeeStaffTrees } = useRequireRole('staffKnowledge')
  const [activeTab, setActiveTab] = useState<'all' | 'faqs' | 'read-alikes' | 'troubleshooting'>('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState(searchQuery)
  const [categoryFilter, setCategoryFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [page, setPage] = useState(1)
  const [selectedEntry, setSelectedEntry] = useState<KnowledgeBaseEntry | null>(null)
  const [readAlikeSearch, setReadAlikeSearch] = useState({ title: '', author: '' })

  usePageTitle(t('knowledgeBase.title'))

  const { data: countsData } = useQuery({
    queryKey: ['knowledge-base', 'category-counts'],
    queryFn: getKnowledgeBaseCategoryCounts,
    staleTime: 5 * 60 * 1000,
  })

  const filteredCategories = useMemo(() => {
    const counts = countsData?.categories ?? {}
    const flagAllowed = CATEGORY_DEFINITIONS.filter(c => !c.featureFlag || isFeatureEnabled(c.featureFlag))
    if (!countsData) return flagAllowed.map(c => c.value)
    return flagAllowed.filter(c => (counts[c.value] ?? 0) > 0).map(c => c.value)
  }, [isFeatureEnabled, countsData])

  const filteredEntryTypes = useMemo(() => {
    const counts = countsData?.types ?? {}
    if (!countsData) return ENTRY_TYPE_KEYS.map(et => et.value)
    return ENTRY_TYPE_KEYS.filter(et => (counts[et.value] ?? 0) > 0).map(et => et.value)
  }, [countsData])

  // Only show the advanced category/type dropdown filters once the corpus is
  // large enough to need them. With a handful of articles the four content
  // pills are plenty, and empty dropdowns just clutter the page.
  const totalEntryCount = useMemo(() => {
    const counts = countsData?.categories ?? {}
    return Object.values(counts).reduce((sum, n) => sum + n, 0)
  }, [countsData])
  const showAdvancedFilters = totalEntryCount > 25

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchQuery), 300)
    return () => clearTimeout(timer)
  }, [searchQuery])

  // Queries
  const { data: entriesData, isLoading: loadingEntries, isError: errorEntries } = useQuery({
    queryKey: ['knowledge-base', 'entries', page, debouncedSearch, categoryFilter, typeFilter],
    queryFn: () => getKnowledgeBaseEntries({
      ...(debouncedSearch ? { q: debouncedSearch } : {}),
      ...(categoryFilter ? { category: categoryFilter } : {}),
      ...(typeFilter ? { entry_type: typeFilter } : {}),
      page,
      per_page: 12,
    }),
    enabled: activeTab === 'all',
  })

  const { data: faqsData, isLoading: loadingFaqs, isError: errorFaqs } = useQuery({
    queryKey: ['knowledge-base', 'faqs', categoryFilter],
    queryFn: () => getFAQs({ ...(categoryFilter ? { category: categoryFilter } : {}),}),
    enabled: activeTab === 'faqs',
  })

  const { data: readAlikesData, isLoading: loadingReadAlikes, isError: errorReadAlikes } = useQuery({
    queryKey: ['knowledge-base', 'read-alikes', readAlikeSearch],
    queryFn: () => getReadAlikes(readAlikeSearch),
    enabled: activeTab === 'read-alikes' && (!!readAlikeSearch.title || !!readAlikeSearch.author),
  })

  const { data: entryDetail } = useQuery({
    queryKey: ['knowledge-base', 'entry', selectedEntry?.id],
    queryFn: () => getKnowledgeBaseEntry(selectedEntry!.id),
    enabled: !!selectedEntry,
  })

  const { data: relatedData } = useQuery({
    queryKey: ['knowledge-base', 'related', selectedEntry?.category],
    queryFn: () => getKnowledgeBaseEntries({ category: selectedEntry!.category, per_page: 4 }),
    enabled: !!selectedEntry,
  })
  const relatedArticles = (relatedData?.items ?? []).filter(e => e.id !== selectedEntry?.id).slice(0, 3)

  // Mutations
  const helpfulMutation = useMutation({
    mutationFn: (id: number) => markEntryHelpful(id),
    onSuccess: () => toast.success(t('knowledgeBase.thanksForYourFeedback')),
    onError: () => toast.error(t('knowledgeBase.couldNotRecordFeedback')),
  })

  const getTypeBadge = (type: string) => {
    const colors: Record<string, string> = {
      faq: 'bg-category-100 text-category-800 dark:bg-category-900/30 dark:text-category-400',
      guide: 'bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light',
      policy: 'bg-earth-100 text-earth-800 dark:bg-earth-900/30 dark:text-earth-300',
      'how-to': 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400',
      'read-alike': 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400',
    }
    return colors[type] || colors.guide
  }

  return (
    <div className="min-h-screen bg-lsc-cream dark:bg-earth-900">
      <PageContainer className="py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center justify-center gap-3">
            <BookOpen aria-hidden="true" className="w-8 h-8 text-lsc-rose" />
            {t('knowledgeBase.title')}
          </h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">{t('knowledgeBase.findAnswersGuidesAndRecommendations')}</p>
        </div>

        {/* Search */}
        {activeTab === 'all' && (
          <div className="max-w-2xl mx-auto mb-8">
            <div className="relative">
              <Search aria-hidden="true" className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => { setSearchQuery(e.target.value); setPage(1) }}
                placeholder={t('placeholder.adminLibraryAgents.searchKnowledgeBase')}
                aria-label={t('aria.adminLibraryAgents.searchKnowledgeBase')}
                className="w-full pl-12 pr-4 py-3 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
              />
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex flex-wrap justify-center gap-2 mb-6" role="tablist">
          {[
            { id: 'all' as const, label: t('knowledgeBase.tabs.allArticles'), icon: FileText },
            { id: 'faqs' as const, label: t('knowledgeBase.tabs.faqs'), icon: HelpCircle },
            { id: 'read-alikes' as const, label: t('knowledgeBase.tabs.readAlikes'), icon: BookOpen },
            { id: 'troubleshooting' as const, label: t('knowledgeBase.tabs.troubleshooting'), icon: GitFork },
          ].filter((tab) => tab.id !== 'troubleshooting' || canSeeStaffTrees).map((tab) => (
            <button
              key={tab.id}
              role="tab"
              aria-selected={activeTab === tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
                activeTab === tab.id
                  ? 'bg-lsc-rose text-white'
                  : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-100 dark:hover:bg-earth-700'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* All Articles Tab */}
        {activeTab === 'all' && (
          <div role="tabpanel">
            {/* Filters */}
            {showAdvancedFilters && (
              <div className="flex flex-wrap gap-4 mb-6">
                <select
                  value={categoryFilter}
                  onChange={(e) => { setCategoryFilter(e.target.value); setPage(1) }}
                  className="px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
                >
                  <option value="">{t('knowledgeBase.allCategories')}</option>
                  {filteredCategories.map((cat) => (
                    <option key={cat} value={cat}>{t(CATEGORY_LABEL_KEYS[cat] ?? cat)}</option>
                  ))}
                </select>
                <select
                  value={typeFilter}
                  onChange={(e) => { setTypeFilter(e.target.value); setPage(1) }}
                  className="px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
                >
                  <option value="">{t('knowledgeBase.allTypes')}</option>
                  {ENTRY_TYPE_KEYS.filter(type => filteredEntryTypes.includes(type.value)).map((type) => (
                    <option key={type.value} value={type.value}>{t(type.labelKey)}</option>
                  ))}
                </select>
              </div>
            )}

            {!loadingEntries && entriesData && entriesData.items.length > 0 && (
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                {t('knowledgeBase.resultCount', { count: entriesData.total })}
              </p>
            )}

            {/* Articles Grid */}
            {loadingEntries ? (
              <div className="flex items-center justify-center h-64" role="status" aria-label={t('aria.knowledgeBase.loadingArticles')}>
                <Loader2 aria-hidden="true" className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
              </div>
            ) : errorEntries ? (
              <div className="text-center py-12">
                <AlertCircle aria-hidden="true" className="w-12 h-12 mx-auto text-status-danger-400 mb-4" />
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('knowledgeBase.errorLoading', 'Unable to load articles. Please try again later.')}</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {entriesData?.items.map((entry) => (
                  <div
                    key={entry.id}
                    onClick={() => setSelectedEntry(entry)} tabIndex={0} role="button" onKeyDown={(e: React.KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); (() => setSelectedEntry(entry))(); } }}
                    className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 p-5 cursor-pointer hover:shadow-md transition-shadow"
                  >
                    <div className="flex items-center gap-2 mb-3">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getTypeBadge(entry.entry_type ?? 'guide')}`}>
                        {ENTRY_TYPE_LABEL_KEYS[entry.entry_type ?? 'guide'] ? t(ENTRY_TYPE_LABEL_KEYS[entry.entry_type ?? 'guide']!) : entry.entry_type}
                      </span>
                      <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{CATEGORY_LABEL_KEYS[entry.category] ? t(CATEGORY_LABEL_KEYS[entry.category]!) : entry.category}</span>
                    </div>
                    <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2 line-clamp-2" title={entry.title}>{entry.title}</h3>
                    {entry.summary && (
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 line-clamp-2" title={entry.summary}>{entry.summary}</p>
                    )}
                    <div className="mt-3 flex items-center justify-between text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      <button
                        type="button"
                        onClick={(e) => { e.stopPropagation(); helpfulMutation.mutate(entry.id) }}
                        disabled={helpfulMutation.isPending}
                        aria-label={t('knowledgeBase.helpfulCount', { count: entry.helpful_count })}
                        className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-earth-100 dark:bg-earth-700 text-lsc-dark/80 dark:text-lsc-cream/80 hover:bg-lsc-rose hover:text-white transition-colors disabled:opacity-50"
                      >
                        <ThumbsUp aria-hidden="true" className="w-3.5 h-3.5" />
                        {t('knowledgeBase.foundHelpful', { count: entry.helpful_count })}
                      </button>
                      <ChevronRight aria-hidden="true" className="w-4 h-4" />
                    </div>
                  </div>
                ))}
              </div>
            )}

            {entriesData?.items.length === 0 && (
              <div className="text-center py-12 bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700">
                {(searchQuery || categoryFilter || typeFilter) ? (
                  <>
                    <Search aria-hidden="true" className="w-12 h-12 text-earth-300 dark:text-earth-600 mx-auto mb-4" />
                    <p className="font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                      {t('knowledgeBase.noResultsFor', { query: searchQuery || categoryFilter || typeFilter })}
                    </p>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">{t('knowledgeBase.tryBroaderSearch')}</p>
                    <button
                      onClick={() => { setSearchQuery(''); setCategoryFilter(''); setTypeFilter(''); setPage(1) }}
                      className="text-sm text-lsc-rose hover:underline"
                    >
                      {t('knowledgeBase.clearFilters')}
                    </button>
                  </>
                ) : (
                  <>
                    <BookOpen aria-hidden="true" className="w-12 h-12 text-earth-300 dark:text-earth-600 mx-auto mb-4" />
                    <p className="font-medium text-lsc-dark dark:text-lsc-cream mb-1">{t('knowledgeBase.kbComingSoon')}</p>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">{t('knowledgeBase.kbComingSoonDesc')}</p>
                    <div className="flex items-center justify-center gap-4">
                      <Link to="/ask-librarian" className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-lsc-rose text-white text-sm font-medium hover:bg-lsc-rose/90 transition-colors">
                        <MessageCircle aria-hidden="true" className="w-4 h-4" />
                        {t('knowledgeBase.askALibrarian')}
                      </Link>
                      <Link to="/contact" className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-600 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm font-medium hover:bg-earth-100 dark:hover:bg-earth-700 transition-colors">
                        {t('knowledgeBase.contactUs')}
                      </Link>
                    </div>
                  </>
                )}
              </div>
            )}

            {/* Pagination */}
            {entriesData && entriesData.total > 12 && (
              <div className="mt-6 flex items-center justify-center gap-2">
                <button
                  onClick={() => setPage(page - 1)}
                  disabled={page === 1}
                  className="px-3 py-1 rounded bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 disabled:opacity-50"
                >
                  {t('knowledgeBase.previous')}
                </button>
                <span className="px-3 py-1 text-lsc-dark/70 dark:text-lsc-cream/70">
                  {t('knowledgeBase.pageOf', { page, total: Math.ceil(entriesData.total / 12) })}
                </span>
                <button
                  onClick={() => setPage(page + 1)}
                  disabled={page * 12 >= entriesData.total}
                  className="px-3 py-1 rounded bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 disabled:opacity-50"
                >
                  {t('knowledgeBase.next')}
                </button>
              </div>
            )}
          </div>
        )}

        {/* FAQs Tab */}
        {activeTab === 'faqs' && (
          <div role="tabpanel">
            {showAdvancedFilters && (
              <div className="mb-6">
                <select
                  value={categoryFilter}
                  onChange={(e) => setCategoryFilter(e.target.value)}
                  className="px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
                >
                  <option value="">{t('knowledgeBase.allCategories')}</option>
                  {filteredCategories.map((cat) => (
                    <option key={cat} value={cat}>{t(CATEGORY_LABEL_KEYS[cat] ?? cat)}</option>
                  ))}
                </select>
              </div>
            )}

            {!loadingFaqs && faqsData && faqsData.length > 0 && (
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                {t('knowledgeBase.resultCountFaqs', { count: faqsData.length })}
              </p>
            )}

            {loadingFaqs ? (
              <div className="flex items-center justify-center h-64">
                <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
              </div>
            ) : errorFaqs ? (
              <div className="text-center py-12">
                <AlertCircle aria-hidden="true" className="w-12 h-12 mx-auto text-status-danger-400 mb-4" />
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('knowledgeBase.errorLoading', 'Unable to load articles. Please try again later.')}</p>
              </div>
            ) : (
              <div className="space-y-3">
                {faqsData?.map((faq: KnowledgeBaseEntry) => (
                  <details
                    key={faq.id}
                    className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 group"
                  >
                    <summary className="p-4 cursor-pointer flex items-center justify-between list-none">
                      <div className="flex items-center gap-3">
                        <HelpCircle className="w-5 h-5 text-lsc-rose flex-shrink-0" />
                        <span className="font-medium text-lsc-dark dark:text-lsc-cream">{faq.title}</span>
                      </div>
                      <ChevronRight className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70 transition-transform group-open:rotate-90" />
                    </summary>
                    <div className="px-4 pb-4 pl-12">
                      <p className="text-lsc-dark/70 dark:text-lsc-cream/70 whitespace-pre-wrap">{faq.content}</p>
                      <button
                        onClick={() => helpfulMutation.mutate(faq.id)}
                        disabled={helpfulMutation.isPending}
                        className="mt-3 flex items-center gap-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose"
                      >
                        <ThumbsUp className="w-4 h-4" />
                        {t('knowledgeBase.helpfulCount', { count: faq.helpful_count })}
                      </button>
                    </div>
                  </details>
                ))}
              </div>
            )}

            {faqsData?.length === 0 && (
              <div className="text-center py-12 bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700">
                {categoryFilter ? (
                  <>
                    <Search aria-hidden="true" className="w-12 h-12 text-earth-300 dark:text-earth-600 mx-auto mb-4" />
                    <p className="font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                      {t('knowledgeBase.noResultsFor', { query: categoryFilter })}
                    </p>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">{t('knowledgeBase.tryBroaderSearch')}</p>
                    <button
                      onClick={() => setCategoryFilter('')}
                      className="text-sm text-lsc-rose hover:underline"
                    >
                      {t('knowledgeBase.clearFilters')}
                    </button>
                  </>
                ) : (
                  <>
                    <HelpCircle aria-hidden="true" className="w-12 h-12 text-earth-300 dark:text-earth-600 mx-auto mb-4" />
                    <p className="font-medium text-lsc-dark dark:text-lsc-cream mb-1">{t('knowledgeBase.kbComingSoon')}</p>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">{t('knowledgeBase.kbComingSoonDesc')}</p>
                    <div className="flex items-center justify-center gap-4">
                      <Link to="/ask-librarian" className="inline-flex items-center gap-2 text-sm text-lsc-rose hover:underline">
                        <MessageCircle aria-hidden="true" className="w-4 h-4" />
                        {t('knowledgeBase.askALibrarian')}
                      </Link>
                      <Link to="/contact" className="inline-flex items-center gap-2 text-sm text-lsc-rose hover:underline">
                        <HelpCircle aria-hidden="true" className="w-4 h-4" />
                        {t('knowledgeBase.contactUs')}
                      </Link>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        )}

        {/* Read-Alikes Tab */}
        {activeTab === 'read-alikes' && (
          <div role="tabpanel">
            <div className="max-w-xl mx-auto mb-8 bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 p-6">
              <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">{t('knowledgeBase.findSimilarBooks')}</h3>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                {t('knowledgeBase.lovedABook')}
              </p>
              <div className="space-y-3">
                <input
                  type="text"
                  value={readAlikeSearch.title}
                  onChange={(e) => setReadAlikeSearch({ ...readAlikeSearch, title: e.target.value })}
                  placeholder={t('placeholder.knowledgeBase.bookTitle')}
                  className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                />
                <input
                  type="text"
                  value={readAlikeSearch.author}
                  onChange={(e) => setReadAlikeSearch({ ...readAlikeSearch, author: e.target.value })}
                  placeholder={t('placeholder.knowledgeBase.authorName')}
                  className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                />
              </div>
            </div>

            {loadingReadAlikes ? (
              <div className="flex items-center justify-center h-32">
                <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
              </div>
            ) : errorReadAlikes ? (
              <div className="text-center py-12">
                <AlertCircle aria-hidden="true" className="w-12 h-12 mx-auto text-status-danger-400 mb-4" />
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('knowledgeBase.errorLoading', 'Unable to load articles. Please try again later.')}</p>
              </div>
            ) : readAlikesData?.items && readAlikesData.items.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {readAlikesData.items.map((rec, index: number) => (
                  <div
                    key={index}
                    className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 p-5"
                  >
                    <div className="flex items-start gap-4">
                      {rec.then_try_cover_url ? (
                        <img
                          src={rec.then_try_cover_url}
                          alt={t('knowledgeBase.coverOf', { title: rec.then_try })}
                          className="w-12 h-16 object-cover rounded flex-shrink-0"
                          loading="lazy"
                        />
                      ) : (
                        <div className="w-12 h-16 bg-lsc-rose/20 rounded flex items-center justify-center flex-shrink-0">
                          <BookOpen className="w-6 h-6 text-lsc-rose" />
                        </div>
                      )}
                      <div className="flex-1">
                        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                          {t('knowledgeBase.ifYouLiked', { title: rec.if_you_liked, author: rec.if_you_liked_author })}
                        </p>
                        {rec.then_try_catalog_id ? (
                          <Link
                            to={`/catalog/${rec.then_try_catalog_id}`}
                            className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream hover:text-lsc-rose underline-offset-2 hover:underline"
                          >
                            {rec.then_try}
                          </Link>
                        ) : (
                          <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{rec.then_try}</h4>
                        )}
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('knowledgeBase.byAuthor', { author: rec.then_try_author })}</p>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">{rec.reason}</p>
                        {rec.then_try_catalog_id && (
                          <div className="mt-3">
                            <Link
                              to={`/catalog/${rec.then_try_catalog_id}?action=hold`}
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-lsc-rose text-white text-xs font-medium hover:bg-lsc-rose/90"
                            >
                              {t('knowledgeBase.placeHold', 'Place hold')}
                            </Link>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (readAlikeSearch.title || readAlikeSearch.author) && !loadingReadAlikes ? (
              <div className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70">
                {t('knowledgeBase.noRecommendationsFound')}
              </div>
            ) : null}
          </div>
        )}

        {/* Troubleshooting Tab */}
        {activeTab === 'troubleshooting' && canSeeStaffTrees && (
          <div role="tabpanel"><DecisionTreeBrowser /></div>
        )}


        {/* Ask a Librarian CTA */}
        <div className="mt-10 rounded-lg bg-earth-100/60 dark:bg-earth-800/60 border border-lsc-border dark:border-earth-700 px-6 py-5 flex flex-col sm:flex-row items-center gap-4">
          <div className="flex-shrink-0 w-10 h-10 rounded-full bg-lsc-rose/10 flex items-center justify-center">
            <HelpCircle aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
          </div>
          <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80 text-center sm:text-left flex-1">
            {t('knowledgeBase.needMoreHelp')}
          </p>
          <div className="flex items-center gap-3">
            <Link to="/ask-librarian" className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-lsc-rose text-white text-sm font-medium hover:bg-lsc-rose/90 transition-colors">
              <MessageCircle aria-hidden="true" className="w-4 h-4" />
              {t('knowledgeBase.askLibrarian')}
            </Link>
            <Link to="/contact" className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-600 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm font-medium hover:bg-earth-100 dark:hover:bg-earth-700 transition-colors">
              {t('knowledgeBase.contactUs')}
            </Link>
          </div>
        </div>
        {/* Entry Detail Modal */}
        {selectedEntry && (
          <ModalBackdrop onClose={() => setSelectedEntry(null)} title={selectedEntry.title}>
            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg max-w-2xl w-full max-h-[90vh] overflow-hidden">
              <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getTypeBadge(selectedEntry.entry_type ?? 'guide')}`}>
                    {ENTRY_TYPE_LABEL_KEYS[selectedEntry.entry_type ?? 'guide'] ? t(ENTRY_TYPE_LABEL_KEYS[selectedEntry.entry_type ?? 'guide']!) : selectedEntry.entry_type}
                  </span>
                  <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{CATEGORY_LABEL_KEYS[selectedEntry.category] ? t(CATEGORY_LABEL_KEYS[selectedEntry.category]!) : selectedEntry.category}</span>
                </div>
                <button onClick={() => setSelectedEntry(null)} className="text-earth-600 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-earth-200" aria-label={t('aria.responseComposerDialog.closeDialog')}>
                  <X aria-hidden="true" className="w-5 h-5" />
                </button>
              </div>
              <div className="p-6 overflow-y-auto max-h-[70vh]">
                <h2 id="modal-title" className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">{selectedEntry.title}</h2>
                <div className="prose prose-sm dark:prose-invert max-w-none prose-headings:text-lsc-dark dark:prose-headings:text-lsc-cream prose-p:text-lsc-dark/80 dark:prose-p:text-lsc-cream/80 prose-li:text-lsc-dark/80 dark:prose-li:text-lsc-cream/80 prose-strong:text-lsc-dark dark:prose-strong:text-lsc-cream prose-a:text-lsc-rose hover:prose-a:underline">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {entryDetail?.content || selectedEntry.content || ''}
                  </ReactMarkdown>
                </div>
                {(() => {
                  const rawTags = selectedEntry.tags
                  const tagList = Array.isArray(rawTags)
                    ? rawTags
                    : typeof rawTags === 'string'
                      ? rawTags.split(',').map(t => t.trim()).filter(Boolean)
                      : []
                  if (tagList.length === 0) return null
                  return (
                    <div className="mt-6 flex items-center gap-2 flex-wrap">
                      <Tag aria-hidden="true" className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
                      {tagList.map((tag: string) => (
                        <span key={tag} className="px-2 py-0.5 bg-earth-100 dark:bg-earth-700 rounded text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                          {tag}
                        </span>
                      ))}
                    </div>
                  )
                })()}
                <div className="mt-6 pt-4 border-t border-lsc-border dark:border-earth-700 flex items-center justify-between">
                  <button
                    onClick={() => helpfulMutation.mutate(selectedEntry.id)}
                    disabled={helpfulMutation.isPending}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-200 dark:hover:bg-earth-600"
                  >
                    <ThumbsUp aria-hidden="true" className="w-4 h-4" />
                    {t('knowledgeBase.helpfulCount', { count: entryDetail?.helpful_count ?? selectedEntry.helpful_count })}
                  </button>
                  <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    {t('knowledgeBase.viewsCount', { count: selectedEntry.view_count })}
                  </span>
                </div>
              </div>
              {relatedArticles.length > 0 && (
                <div className="border-t border-earth-200 dark:border-earth-700 bg-earth-50/50 dark:bg-earth-900/30 px-6 pt-5 pb-6">
                  <h3 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-3">{t("knowledgeBase.relatedArticles")}</h3>
                  <ul className="space-y-2">
                    {relatedArticles.map((article) => (
                      <li key={article.id}>
                        <button
                          onClick={() => setSelectedEntry(article)}
                          className="text-sm text-earth-600 dark:text-earth-400 hover:text-lsc-dark dark:hover:text-lsc-cream hover:underline text-left"
                        >
                          {article.title}
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <div className="border-t border-earth-200 dark:border-earth-700 px-6 py-3 flex items-center justify-between gap-3 flex-wrap">
                <span className="text-sm text-lsc-dark/60 dark:text-lsc-cream/60">
                  {t('knowledgeBase.stillStuck')}
                </span>
                <div className="flex items-center gap-2">
                  <Link
                    to={`/ask-librarian?article=${selectedEntry.id}`}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-lsc-rose text-white text-sm font-medium hover:bg-lsc-rose/90 transition-colors"
                  >
                    <MessageCircle aria-hidden="true" className="w-4 h-4" />
                    {t('knowledgeBase.askLibrarian')}
                  </Link>
                  <Link
                    to={`/contact?article=${selectedEntry.id}`}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-lsc-border dark:border-earth-600 text-lsc-dark/70 dark:text-lsc-cream/70 text-sm font-medium hover:bg-earth-100 dark:hover:bg-earth-700 transition-colors"
                  >
                    {t('knowledgeBase.contactUs')}
                  </Link>
                </div>
              </div>
            </div>
          </ModalBackdrop>
        )}
      </PageContainer>
    </div>
  )
}
