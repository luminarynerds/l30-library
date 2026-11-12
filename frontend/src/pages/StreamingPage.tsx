/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect, useCallback, useId } from 'react'
import { useTranslation} from '@/i18n'
import { useAuth } from '../contexts/AuthContext'
import {
  getPatronStreamingDashboard,
  searchStreaming,
  checkoutStreamingContent,
  returnStreamingContent,
  PatronStreamingDashboard,
  StreamingCatalogItem,
  StreamingCheckout,
  StreamingContentType,
  StreamingService,
  formatServiceName,
  formatContentType,
  formatDuration,
  isCheckoutExpiringSoon,
  getCheckoutTimeRemaining,
} from '../api/streaming-api'
import {
  Play,
  Search,
  Clock,
  ExternalLink,
  Smartphone,
  Globe,
  Film,
  Headphones,
  BookOpen,
  Music,
  Monitor,
  Loader2,
  AlertTriangle,
  CheckCircle,
  X,
} from 'lucide-react'
import StandardPageLayout from '@/components/StandardPageLayout'
import toast from 'react-hot-toast'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

type TabType = 'browse' | 'checkouts' | 'limits'

export default function StreamingPage() {
  const { t } = useTranslation()
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { token, user: _user, isAuthenticated } = useAuth()
  const [activeTab, setActiveTab] = useState<TabType>('browse')
  const [loading, setLoading] = useState(true)
  const [dashboard, setDashboard] = useState<PatronStreamingDashboard | null>(null)

  const fetchDashboard = useCallback(async () => {
    if (!token) return
    try {
      const data = await getPatronStreamingDashboard(token)
      setDashboard(data)
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('streaming.failedToLoadStreamingData'))
    } finally {
      setLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  useEffect(() => {
    if (isAuthenticated) {
      fetchDashboard()
    } else {
      setLoading(false)
    }
  }, [fetchDashboard, isAuthenticated])

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-lsc-cream dark:bg-earth-900 flex items-center justify-center">
        <div className="text-center">
          <Play className="w-16 h-16 mx-auto mb-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">{t('streaming.signInToAccessStreaming')}</h2>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            Log in to your library account to browse and check out streaming content.
          </p>
        </div>
      </div>
    )
  }

  return (
    <StandardPageLayout
      title="Streaming"
      subtitle={t('streaming.watchMoviesListenToAudiobooks')}
      icon={Monitor}
      isLoading={loading}
    >
      {/* Service Status */}
      {dashboard && (
        <div className="flex flex-wrap gap-4">
          {dashboard.services.map((service) => (
            <div
              key={service.service}
              className="bg-lsc-white dark:bg-earth-800 rounded-lg px-4 py-3 border border-lsc-border dark:border-earth-700"
            >
              <div className="flex items-center gap-2">
                <Play className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
                <span className="font-medium text-earth-700 dark:text-lsc-cream">{service.service_name}</span>
              </div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                {service.remaining_checkouts} of {service.monthly_limit} checkouts remaining
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="bg-lsc-white dark:bg-earth-800 border-b sticky top-0 z-10">
        {/* eslint-disable-next-line lsc-design-tokens/no-hardcoded-page-width -- sticky tab bar aligns tabs to content width, not a page root */}
        <div className="max-w-6xl mx-auto px-4">
          <div className="flex gap-6">
            {[
              { id: 'browse', label: 'Browse & Search', icon: Search },
              { id: 'checkouts', label: 'My Checkouts', icon: Play },
              { id: 'limits', label: 'Checkout Limits', icon: Clock },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as TabType)}
                className={`flex items-center gap-2 py-4 border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? 'border-status-info-600 text-status-info-600'
                    : 'border-transparent text-earth-600 hover:text-lsc-dark dark:text-lsc-cream dark:hover:text-earth-100'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
                {tab.id === 'checkouts' && dashboard && dashboard.total_active_checkouts > 0 && (
                  <span className="bg-status-info-100 dark:bg-status-info-900/30 text-status-info-800 dark:text-status-info-300 text-xs px-2 py-0.5 rounded-full">
                    {dashboard.total_active_checkouts}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <div>
        {activeTab === 'browse' && token && (
          <BrowseTab token={token} onCheckout={fetchDashboard} />
        )}
        {activeTab === 'checkouts' && dashboard && token && (
          <CheckoutsTab
            checkouts={dashboard.recent_checkouts.filter((c) => c.status === 'active')}
            recentCheckouts={dashboard.recent_checkouts}
            onReturn={fetchDashboard}
            token={token}
          />
        )}
        {activeTab === 'limits' && dashboard && <LimitsTab dashboard={dashboard} />}
      </div>
    </StandardPageLayout>
  )
}

// Browse Tab Component
function BrowseTab({ token, onCheckout }: { token: string; onCheckout: () => void }) {
  const { t } = useTranslation();
  const searchInputId = useId()
  const contentTypeFilterId = useId()
  const serviceFilterId = useId()
  const searchHelpTextId = useId()
  const searchResultsId = useId()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<StreamingCatalogItem[]>([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)
  const [selectedItem, setSelectedItem] = useState<StreamingCatalogItem | null>(null)
  const [checkingOut, setCheckingOut] = useState(false)
  const [contentTypeFilter, setContentTypeFilter] = useState<StreamingContentType | ''>('')
  const [serviceFilter, setServiceFilter] = useState<StreamingService | ''>('')

  const handleSearch = async () => {
    if (!query.trim()) return
    setLoading(true)
    setSearched(true)
    try {
      const response = await searchStreaming(token, {
        query: query.trim(),
        ...(contentTypeFilter ? { content_type: contentTypeFilter } : {}),
        ...(serviceFilter ? { service: serviceFilter } : {}),
        page_size: 50,
      })
      setResults(response.items)
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('streaming.weCouldNotRunYour'))
    } finally {
      setLoading(false)
    }
  }

  const handleCheckout = async (item: StreamingCatalogItem) => {
    setCheckingOut(true)
    try {
      await checkoutStreamingContent(token, item.id)
      toast.success(t('toast.streaming.successfullyCheckedOutTitle', { title: item.title }))
      setSelectedItem(null)
      onCheckout()
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : t('toast.checkoutFailed'))
    } finally {
      setCheckingOut(false)
    }
  }

  const hasActiveFilters = Boolean(contentTypeFilter || serviceFilter)

  return (
    <div className="space-y-6">
      {/* Search Form */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-6">
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault()
            handleSearch()
          }}
        >
          <div className="flex gap-4 flex-wrap items-end">
            <div className="flex-1 min-w-[200px]">
              <label htmlFor={searchInputId} className="block text-sm font-medium text-earth-800 dark:text-earth-100 mb-1">
                Search streaming catalog
              </label>
              <input
                id={searchInputId}
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={t('streaming.searchMoviesAudiobooksMusic')}
                aria-describedby={searchHelpTextId}
                className="w-full px-4 py-2 border border-lsc-border dark:border-earth-600 rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-status-info-500 focus-visible:border-status-info-500"
              />
            </div>
            <div>
              <label htmlFor={contentTypeFilterId} className="block text-sm font-medium text-earth-800 dark:text-earth-100 mb-1">
                Content type
              </label>
              <select
                id={contentTypeFilterId}
                value={contentTypeFilter}
                onChange={(e) => setContentTypeFilter(e.target.value as StreamingContentType | '')}
                className="px-4 py-2 border border-lsc-border dark:border-earth-600 rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-status-info-500 focus-visible:border-status-info-500"
              >
                <option value="">All Types</option>
                <option value="movie">Movies</option>
                <option value="tv_series">TV Series</option>
                <option value="audiobook">Audiobooks</option>
                <option value="ebook">eBooks</option>
                <option value="music_album">Music</option>
                <option value="documentary">Documentaries</option>
              </select>
            </div>
            <div>
              <label htmlFor={serviceFilterId} className="block text-sm font-medium text-earth-800 dark:text-earth-100 mb-1">
                Service
              </label>
              <select
                id={serviceFilterId}
                value={serviceFilter}
                onChange={(e) => setServiceFilter(e.target.value as StreamingService | '')}
                className="px-4 py-2 border border-lsc-border dark:border-earth-600 rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-status-info-500 focus-visible:border-status-info-500"
              >
                <option value="">All Services</option>
                <option value="palace">Palace Project</option>
              </select>
            </div>
            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="px-6 py-2 bg-status-info-600 text-white rounded-lg hover:bg-status-info-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-status-info-600"
            >
              {loading ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Search className="w-4 h-4" />}
              Search
            </button>
          </div>
          <p id={searchHelpTextId} className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            Enter a title, creator, or keyword. Use filters to narrow results before searching.
          </p>
          {hasActiveFilters && (
            <button
              type="button"
              onClick={() => {
                setContentTypeFilter('')
                setServiceFilter('')
              }}
              className="text-sm text-status-info-700 dark:text-status-info-300 hover:text-status-info-800 underline underline-offset-2"
            >
              Clear filters
            </button>
          )}
        </form>
      </div>

      {/* Results */}
      {searched && (
        <div id={searchResultsId} aria-live="polite" aria-atomic="true">
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4" role="status">
            {results.length} result{results.length !== 1 ? 's' : ''} found
          </p>
          {results.length === 0 ? (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-8 text-center">
              <Search className="w-12 h-12 mx-auto mb-4 text-earth-300" />
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('streaming.noResultsFoundTryA')}</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
              {results.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setSelectedItem(item)}
                  className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow overflow-hidden text-left hover:shadow-lg transition-shadow focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-status-info-600"
                  aria-label={`View details for ${item.title}`}
                >
                  <div className="aspect-[2/3] bg-earth-100 dark:bg-earth-700 relative">
                    {item.cover_url ? (
                      <img
                        src={item.cover_url}
                        alt={item.title}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <ContentTypeIcon type={item.content_type} size="large" />
                      </div>
                    )}
                    <div className="absolute top-2 right-2">
                      <span
                        className={`text-xs px-2 py-1 rounded-full font-medium ${
                          item.service_name === 'palace'
                            ? 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300'
                            : 'bg-status-info-100 dark:bg-status-info-900/30 text-status-info-700 dark:text-status-info-300'
                        }`}
                      >
                        {item.service_name ? formatServiceName(item.service_name as StreamingService) : ''}
                      </span>
                    </div>
                    {!item.is_available && (
                      <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
                        <span className="text-white font-medium">Unavailable</span>
                      </div>
                    )}
                  </div>
                  <div className="p-3">
                    <h3 className="font-medium text-lsc-dark dark:text-lsc-cream line-clamp-2 text-sm" title={item.title}>{item.title}</h3>
                    {item.author && (
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1 truncate" title={item.author}>{item.author}</p>
                    )}
                    <div className="flex items-center gap-2 mt-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      <span>{formatContentType(item.content_type)}</span>
                      {item.duration_minutes && (
                        <>
                          <span>•</span>
                          <span>{formatDuration(item.duration_minutes)}</span>
                        </>
                      )}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Item Detail Modal */}
      {selectedItem && (
        <ModalBackdrop onClose={() => setSelectedItem(null)} title={selectedItem.title}>
          <div
            className="bg-lsc-white dark:bg-earth-800 rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto"
          >
            <div className="p-6">
              <div className="flex justify-between items-start mb-4">
                <h2 id="streaming-item-title" className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">{selectedItem.title}</h2>
                <button
                  onClick={() => setSelectedItem(null)}
                  className="text-earth-600 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-earth-300"
                  aria-label={t('aria.streaming.closeItemDetails')}
                >
                  <X className="w-6 h-6" />
                </button>
              </div>

              <div className="flex gap-6">
                <div className="w-40 flex-shrink-0">
                  {selectedItem.cover_url ? (
                    <img
                      src={selectedItem.cover_url}
                      alt={selectedItem.title}
                      className="w-full rounded-lg"
                    />
                  ) : (
                    <div className="w-full aspect-[2/3] bg-earth-100 dark:bg-earth-700 rounded-lg flex items-center justify-center">
                      <ContentTypeIcon type={selectedItem.content_type} size="large" />
                    </div>
                  )}
                </div>
                <div className="flex-1">
                  {selectedItem.author && (
                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">By {selectedItem.author}</p>
                  )}
                  <div className="flex flex-wrap gap-2 mb-4">
                    <span className="text-sm px-3 py-1 bg-earth-100 dark:bg-earth-700 rounded-full">
                      {formatContentType(selectedItem.content_type)}
                    </span>
                    {selectedItem.release_year && (
                      <span className="text-sm px-3 py-1 bg-earth-100 dark:bg-earth-700 rounded-full">
                        {selectedItem.release_year}
                      </span>
                    )}
                    {selectedItem.duration_minutes && (
                      <span className="text-sm px-3 py-1 bg-earth-100 dark:bg-earth-700 rounded-full">
                        {formatDuration(selectedItem.duration_minutes)}
                      </span>
                    )}
                    {selectedItem.rating && (
                      <span className="text-sm px-3 py-1 bg-earth-100 dark:bg-earth-700 rounded-full">
                        {selectedItem.rating}
                      </span>
                    )}
                  </div>
                  {selectedItem.description && (
                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm mb-4 line-clamp-4" title={selectedItem.description}>
                      {selectedItem.description}
                    </p>
                  )}
                  <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                    Available on{' '}
                    <span className="font-medium">
                      {selectedItem.service_name
                        ? formatServiceName(selectedItem.service_name as StreamingService)
                        : 'streaming'}
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex gap-3 mt-6 pt-6 border-t">
                <button
                  onClick={() => handleCheckout(selectedItem)}
                  disabled={checkingOut || !selectedItem.is_available}
                  className="flex-1 px-6 py-3 bg-status-info-600 text-white rounded-lg hover:bg-status-info-700 disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {checkingOut ? (
                    <Loader2 className="w-5 h-5 motion-safe:animate-spin" />
                  ) : (
                    <Play className="w-5 h-5" />
                  )}
                  {selectedItem.is_available ? 'Check Out & Watch' : 'Currently Unavailable'}
                </button>
                {selectedItem.web_deep_link && (
                  <a
                    href={selectedItem.web_deep_link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-4 py-3 border rounded-lg hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800 flex items-center gap-2"
                  >
                    <ExternalLink className="w-5 h-5" />
                    View on {selectedItem.service_name ? formatServiceName(selectedItem.service_name as StreamingService) : 'site'}
                  </a>
                )}
              </div>
            </div>
          </div>
        </ModalBackdrop>
      )}
    </div>
  )
}

// Checkouts Tab Component
function CheckoutsTab({
  checkouts,
  recentCheckouts,
  onReturn,
  token,
}: {
  checkouts: StreamingCheckout[]
  recentCheckouts: StreamingCheckout[]
  onReturn: () => void
  token: string
}) {
  const { t } = useTranslation()
  const [returningId, setReturningId] = useState<number | null>(null)

  const handleReturn = async (checkout: StreamingCheckout) => {
    setReturningId(checkout.id)
    try {
      await returnStreamingContent(token, checkout.id)
      toast.success(t('toast.streaming.contentReturnedSuccessfully'))
      onReturn()
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : t('toast.streaming.returnFailed'))
    } finally {
      setReturningId(null)
    }
  }

  return (
    <div className="space-y-6">
      {/* Active Checkouts */}
      <div>
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Active Checkouts</h2>
        {checkouts.length === 0 ? (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-8 text-center">
            <Play className="w-12 h-12 mx-auto mb-4 text-earth-300" />
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('streaming.youHaveNoActiveCheckouts')}</p>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              Search for content to start watching or listening
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {checkouts.map((checkout) => (
              <div key={checkout.id} className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow p-4">
                <div className="flex gap-4">
                  <div className="w-20 h-28 bg-earth-100 dark:bg-earth-700 rounded flex-shrink-0 overflow-hidden">
                    {checkout.cover_url ? (
                      <img
                        src={checkout.cover_url}
                        alt={checkout.item_title || ''}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <ContentTypeIcon type={checkout.item_content_type || 'movie'} />
                      </div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{checkout.item_title}</h3>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      {checkout.service_name ? formatServiceName(checkout.service_name as StreamingService) : ''} •{' '}
                      {checkout.item_content_type
                        ? formatContentType(checkout.item_content_type)
                        : ''}
                    </p>
                    <div className="flex items-center gap-2 mt-2">
                      {isCheckoutExpiringSoon(checkout) ? (
                        <span className="text-sm text-status-warning-600 flex items-center gap-1">
                          <AlertTriangle className="w-4 h-4" />
                          {getCheckoutTimeRemaining(checkout)}
                        </span>
                      ) : (
                        <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 flex items-center gap-1">
                          <Clock className="w-4 h-4" />
                          {getCheckoutTimeRemaining(checkout)}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex flex-col gap-2">
                    {checkout.web_deep_link && (
                      <a
                        href={checkout.web_deep_link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="px-4 py-2 bg-status-info-600 text-white rounded-lg hover:bg-status-info-700 flex items-center gap-2 text-sm"
                      >
                        <Globe className="w-4 h-4" />
                        Watch
                      </a>
                    )}
                    {checkout.app_deep_link && (
                      <a
                        href={checkout.app_deep_link}
                        className="px-4 py-2 border rounded-lg hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800 flex items-center gap-2 text-sm"
                      >
                        <Smartphone className="w-4 h-4" />
                        Open App
                      </a>
                    )}
                    <button
                      onClick={() => handleReturn(checkout)}
                      disabled={returningId === checkout.id}
                      className="px-4 py-2 text-earth-600 hover:text-lsc-dark dark:text-lsc-cream dark:hover:text-earth-100 text-sm flex items-center gap-2"
                    >
                      {returningId === checkout.id ? (
                        <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                      ) : (
                        <X className="w-4 h-4" />
                      )}
                      Return Early
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Recent Activity */}
      {recentCheckouts.filter((c) => c.status !== 'active').length > 0 && (
        <div>
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Checkout History</h2>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow divide-y">
            {recentCheckouts
              .filter((c) => c.status !== 'active')
              .slice(0, 10)
              .map((checkout) => (
                <div key={checkout.id} className="p-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-earth-100 dark:bg-earth-700 rounded flex items-center justify-center">
                      <ContentTypeIcon type={checkout.item_content_type || 'movie'} />
                    </div>
                    <div>
                      <p className="font-medium text-lsc-dark dark:text-lsc-cream">{checkout.item_title}</p>
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        {new Date(checkout.checked_out_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <span
                    className={`text-sm px-3 py-1 rounded-full ${
                      checkout.status === 'returned'
                        ? 'bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70'
                        : 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-300'
                    }`}
                  >
                    {checkout.status === 'returned' ? 'Returned' : 'Expired'}
                  </span>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  )
}

// Limits Tab Component
function LimitsTab({ dashboard }: { dashboard: PatronStreamingDashboard }) {
  return (
    <div className="space-y-6">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow">
        <div className="p-6 border-b">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Monthly Checkout Limits</h2>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
            Your streaming checkout limits reset on the 1st of each month
          </p>
        </div>
        <div className="divide-y">
          {dashboard.services.map((service) => (
            <div key={service.service} className="p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div
                    className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                      service.service === 'palace' ? 'bg-status-success-100 dark:bg-status-success-900/30' : 'bg-status-info-100 dark:bg-status-info-900/30'
                    }`}
                  >
                    <Play
                      className={`w-6 h-6 ${
                        service.service === 'palace' ? 'text-status-success-600' : 'text-status-info-600'
                      }`}
                    />
                  </div>
                  <div>
                    <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{service.service_name}</h3>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      Resets {new Date(service.limit_reset_date).toLocaleDateString()}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                    {service.remaining_checkouts}
                    <span className="text-lg text-lsc-dark/70 dark:text-lsc-cream/70 font-normal">
                      {' '}
                      / {service.monthly_limit}
                    </span>
                  </p>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">checkouts remaining this month</p>
                </div>
              </div>

              <div className="h-3 bg-earth-200 dark:bg-earth-600 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${
                    service.remaining_checkouts === 0
                      ? 'bg-status-danger-500'
                      : service.remaining_checkouts <= 2
                      ? 'bg-status-warning-500'
                      : 'bg-status-success-500'
                  }`}
                  style={{
                    width: `${
                      ((service.monthly_limit - service.remaining_checkouts) /
                        service.monthly_limit) *
                      100
                    }%`,
                  }}
                />
              </div>

              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-3">
                You have used {service.current_month_checkouts} of your {service.monthly_limit}{' '}
                monthly checkouts
              </p>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-earth-50 dark:bg-earth-800/50 rounded-lg p-6">
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3">How Streaming Works</h3>
        <ul className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 space-y-3">
          <li className="flex items-start gap-2">
            <CheckCircle className="w-4 h-4 mt-0.5 flex-shrink-0 text-status-success-600 dark:text-status-success-400" />
            You get a set number of checkouts each month — enjoy each one at your own pace
          </li>
          <li className="flex items-start gap-2">
            <CheckCircle className="w-4 h-4 mt-0.5 flex-shrink-0 text-status-success-600 dark:text-status-success-400" />
            Your checkouts refresh on the 1st of every month
          </li>
          <li className="flex items-start gap-2">
            <CheckCircle className="w-4 h-4 mt-0.5 flex-shrink-0 text-status-success-600 dark:text-status-success-400" />
            Checked-out content stays available for 3–21 days depending on the type
          </li>
          <li className="flex items-start gap-2">
            <CheckCircle className="w-4 h-4 mt-0.5 flex-shrink-0 text-status-success-600 dark:text-status-success-400" />
            You can return items early to free up space, though the checkout still counts toward your monthly total
          </li>
        </ul>
      </div>
    </div>
  )
}

// Helper Components
function ContentTypeIcon({
  type,
  size = 'normal',
}: {
  type: string
  size?: 'normal' | 'large'
}) {
  const icons: Record<string, React.ElementType> = {
    movie: Film,
    tv_series: Film,
    tv_episode: Film,
    documentary: Film,
    audiobook: Headphones,
    ebook: BookOpen,
    music_album: Music,
    comic: BookOpen,
  }

  const Icon = icons[type] || Play
  const sizeClass = size === 'large' ? 'w-12 h-12' : 'w-6 h-6'

  return <Icon className={`${sizeClass} text-lsc-dark/70 dark:text-lsc-cream/70`} />
}
