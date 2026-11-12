/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ClipboardList,
  Plus,
  Trash2,
  ShoppingCart,
  Search,
  Filter,
  ChevronDown,
  Loader2,
  X,
  BookOpen,
  CheckCircle,
  Sparkles,
} from 'lucide-react'
import toast from 'react-hot-toast'
import {
  getSelectionList,
  addToSelectionList,
  removeFromSelectionList,
  convertSelectionToPO,
  getVendors,
  getFunds,
  searchExternalCatalogs,
  type SelectionListItem,
  type SelectionListCreateData,
  type ExternalSearchResult,
  getCollectionIntelligenceReport,
  addInsightToPurchaseConsideration,
  type CollectionIntelligenceReport,
  type CollectionInsightItem,
} from '@/api/api'
import ConfirmDialog from '@/components/ConfirmDialog'
import { useTranslation} from '@/i18n'
import { AdminShell } from '../components/shells/AdminShell'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import PageContainer from '@/components/layout/PageContainer'

const PRIORITIES = [
  { value: 'low', label: 'Low' },
  { value: 'normal', label: 'Normal' },
  { value: 'high', label: 'High' },
  { value: 'urgent', label: 'Urgent' },
]

// eslint-disable-next-line complexity
export default function SelectionListPage(): React.ReactElement {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const [showFilters, setShowFilters] = useState(false)
  const [statusFilter, setStatusFilter] = useState('')
  const [priorityFilter, setPriorityFilter] = useState('')
  const [showAddModal, setShowAddModal] = useState(false)
  const [showConvertModal, setShowConvertModal] = useState(false)
  const [selectedItems, setSelectedItems] = useState<number[]>([])
  const [lastSelectedIndex, setLastSelectedIndex] = useState<number | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<SelectionListItem | null>(null)

  // External search state
  const [showExternalSearch, setShowExternalSearch] = useState(false)
  const [externalQuery, setExternalQuery] = useState('')
  const [searchResults, setSearchResults] = useState<ExternalSearchResult[]>([])
  const [isSearching, setIsSearching] = useState(false)

  // Form state - only include defined values to satisfy exactOptionalPropertyTypes
  const [formData, setFormData] = useState<SelectionListCreateData>({
    title: '',
    author: '',
    isbn: '',
    publisher: '',
    format: '',
    notes: '',
    priority: 'normal',
    source: 'manual',
  })

  // Convert PO state
  const [selectedVendor, setSelectedVendor] = useState<number | null>(null)
  const [selectedFund, setSelectedFund] = useState<number | null>(null)

  // Queries
  const { data: selectionData, isLoading } = useQuery({
    queryKey: ['acquisition', 'selection-list', statusFilter, priorityFilter],
    queryFn: () => getSelectionList({
      ...(statusFilter && { status: statusFilter }),
      ...(priorityFilter && { priority: priorityFilter }),
    }),
  })

  const { data: vendorsData } = useQuery({
    queryKey: ['acquisition', 'vendors', 'active'],
    queryFn: () => getVendors({ status: 'active' }),
    enabled: showConvertModal,
  })

  const { data: fundsData } = useQuery({
    queryKey: ['acquisition', 'funds', 'active'],
    queryFn: () => getFunds({ status: 'active' }),
    enabled: showConvertModal,
  })

  const { data: intelligenceData, isLoading: intelligenceLoading } = useQuery<CollectionIntelligenceReport>({
    queryKey: ['acquisition', 'collection-intelligence'],
    queryFn: getCollectionIntelligenceReport,
  })

  // Mutations
  const addMutation = useMutation({
    mutationFn: addToSelectionList,
    onSuccess: () => {
      toast.success(t('selectionList.itemAddedToSelectionList'))
      queryClient.invalidateQueries({ queryKey: ['acquisition', 'selection-list'] })
      setShowAddModal(false)
      setShowExternalSearch(false)
      resetForm()
    },
    onError: () => toast.error(t('selectionList.failedToAddItem')),
  })

  const removeMutation = useMutation({
    mutationFn: removeFromSelectionList,
    onSuccess: () => {
      toast.success(t('toast.selectionList.itemRemoved'))
      queryClient.invalidateQueries({ queryKey: ['acquisition', 'selection-list'] })
      setDeleteConfirm(null)
    },
    onError: () => toast.error(t('selectionList.failedToRemoveItem')),
  })

  const convertMutation = useMutation({
    mutationFn: convertSelectionToPO,
    onSuccess: (data) => {
      toast.success(t('toast.selectionList.purchaseOrderPurchaseorderidCreatedWith', { purchaseorderid: data.po_number, length: selectedItems.length }))
      queryClient.invalidateQueries({ queryKey: ['acquisition'] })
      setShowConvertModal(false)
      setSelectedItems([])
      setSelectedVendor(null)
      setSelectedFund(null)
    },
    onError: () => toast.error(t('selectionList.failedToCreatePurchaseOrder')),
  })

  const addInsightMutation = useMutation({
    mutationFn: addInsightToPurchaseConsideration,
    onSuccess: () => {
      toast.success(t('selectionList.addedToPurchaseConsideration'))
      queryClient.invalidateQueries({ queryKey: ['acquisition', 'selection-list'] })
    },
    onError: () => toast.error(t('selectionList.failedToAddToSelection')),
  })

  const resetForm = () => {
    setFormData({
      title: '',
      author: '',
      isbn: '',
      publisher: '',
      format: '',
      notes: '',
      priority: 'normal',
      source: 'manual',
    })
    setSearchResults([])
    setExternalQuery('')
  }

  const handleExternalSearch = async () => {
    if (!externalQuery.trim()) return
    setIsSearching(true)
    try {
      const results = await searchExternalCatalogs({ q: externalQuery })
      setSearchResults(results.results)
    } catch {
      toast.error(t('toast.selectionList.searchFailed'))
    } finally {
      setIsSearching(false)
    }
  }

  const selectFromSearch = (result: ExternalSearchResult) => {
    setFormData({
      title: result.title,
      author: result.author || '',
      isbn: result.isbn || '',
      publisher: result.publisher || '',
      ...(result.publication_year && { publication_year: result.publication_year }),
      ...(result.price && { price: result.price }),
      format: result.format || '',
      notes: '',
      priority: 'normal',
      source: result.source,
    })
    setShowExternalSearch(false)
  }

  const toggleSelectItem = (id: number, index?: number, allIds?: number[], shiftKey: boolean = false) => {
    if (shiftKey && lastSelectedIndex !== null && index !== undefined && allIds && lastSelectedIndex !== index) {
      // Range selection: select all items between lastSelectedIndex and current index
      const start = Math.min(lastSelectedIndex, index)
      const end = Math.max(lastSelectedIndex, index)
      const rangeIds = allIds.slice(start, end + 1)

      setSelectedItems((prev) => {
        const newSet = new Set([...prev, ...rangeIds])
        return Array.from(newSet)
      })
    } else {
      // Single toggle
      setSelectedItems((prev) =>
        prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
      )
    }
    if (index !== undefined) {
      setLastSelectedIndex(index)
    }
  }

  const selectAllPending = () => {
    const pendingIds = selectionData?.items.filter(i => i.status === 'pending').map(i => i.id) || []
    setSelectedItems(pendingIds)
  }

  const handleConvert = () => {
    if (!selectedVendor || !selectedFund) {
      toast.error(t('selectionList.pleaseSelectAVendorAnd'))
      return
    }
    convertMutation.mutate({
      selection_item_ids: selectedItems,
      vendor_id: selectedVendor,
      fund_id: selectedFund,
    })
  }

  const getPriorityBadge = (priority: string) => {
    const colors: Record<string, string> = {
      low: 'bg-earth-100 text-earth-800 dark:bg-earth-900/30 dark:text-earth-300',
      normal: 'bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light',
      high: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400',
      urgent: 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400',
    }
    return colors[priority] || colors.normal
  }

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      pending: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400',
      approved: 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400',
      ordered: 'bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light',
      rejected: 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400',
    }
    return colors[status] || colors.pending
  }

  const pendingCount = selectionData?.items.filter(i => i.status === 'pending').length ?? 0

  const addInsight = (item: CollectionInsightItem) => {
    addInsightMutation.mutate({
      title: item.title,
      ...(item.author ? { author: item.author } : {}),
      ...(item.isbn ? { isbn: item.isbn } : {}),
      notes: `${item.reason} (Source: ${item.source})`,
      source: 'manual',
      source_id: item.key,
    })
  }

  return (
    <AdminShell title="Selection List">
    <div className="min-h-screen bg-lsc-cream dark:bg-earth-900">
      <PageContainer width="wide" className="py-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-3">
              <ClipboardList className="w-8 h-8 text-lsc-rose" />
              Selection List
            </h1>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{t('selectionList.wishlistItemsForAcquisitionConsideration')}</p>
          </div>
          <div className="flex items-center gap-2">
            {selectedItems.length > 0 && (
              <button
                onClick={() => setShowConvertModal(true)}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-status-success-600 text-white hover:bg-status-success-700"
              >
                <ShoppingCart className="w-4 h-4" />
                Convert to PO ({selectedItems.length})
              </button>
            )}
            <button
              onClick={() => { resetForm(); setShowAddModal(true) }}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90"
            >
              <Plus className="w-4 h-4" />
              Add Item
            </button>
          </div>
        </div>


        <div className="mb-8 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 p-5">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-lsc-rose" />
            Intelligent Collection Development
          </h2>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{t('selectionList.stopGuessingWhatToBuy')}</p>

          {intelligenceLoading ? (
            <div className="py-6 text-lsc-dark/70 dark:text-lsc-cream/70 flex items-center gap-2"><Loader2 className="w-4 h-4 motion-safe:animate-spin" /> Loading intelligence report…</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
              {[
                ['Patrons searched but missing', intelligenceData?.patrons_searched_missing || []],
                ["Popular titles we don't own", intelligenceData?.popular_titles_not_owned || []],
                ['Series with missing volumes', intelligenceData?.series_missing_volumes || []],
                ['High hold-ratio items', intelligenceData?.high_hold_ratio_items || []],
                ['Outdated subjects (>10y avg age)', intelligenceData?.outdated_subjects || []],
                ['Peer library gaps', intelligenceData?.peer_library_gaps || []],
                ['Award winners missing', intelligenceData?.missing_award_winners || []],
                ['Trending topics without coverage', intelligenceData?.trending_topics_without_coverage || []],
              ].map(([label, items]) => (
                <div key={label as string} className="rounded-lg border border-lsc-border dark:border-earth-700 p-3">
                  <div className="font-medium text-lsc-dark dark:text-lsc-cream mb-2">{label as string} <span className="text-sm text-earth-600">({(items as CollectionInsightItem[]).length})</span></div>
                  <div className="space-y-2 max-h-56 overflow-y-auto">
                    {(items as CollectionInsightItem[]).slice(0, 5).map((item) => (
                      <div key={item.key} className="rounded-lg bg-earth-50 dark:bg-earth-900/40 p-2">
                        <div className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">{item.title}</div>
                        <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{item.reason}</div>
                        <button
                          onClick={() => addInsight(item)}
                          disabled={addInsightMutation.isPending}
                          className="mt-2 text-xs px-2 py-1 rounded bg-lsc-rose text-white hover:bg-lsc-rose/90 disabled:opacity-50"
                        >
                          One-click add to purchase consideration
                        </button>
                      </div>
                    ))}
                    {(items as CollectionInsightItem[]).length === 0 && <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{t('selectionList.noSignalsRightNow')}</div>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Filters */}
        <div className="mb-6">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-earth-900 dark:hover:text-earth-100"
          >
            <Filter className="w-4 h-4" />
            Filters
            <ChevronDown className={`w-4 h-4 transition-transform ${showFilters ? 'rotate-180' : ''}`} />
          </button>
          {showFilters && (
            <div className="mt-4 flex flex-wrap gap-4">
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
              >
                <option value="">All Statuses</option>
                <option value="pending">Pending</option>
                <option value="approved">Approved</option>
                <option value="ordered">Ordered</option>
                <option value="rejected">Rejected</option>
              </select>
              <select
                value={priorityFilter}
                onChange={(e) => setPriorityFilter(e.target.value)}
                className="px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
              >
                <option value="">All Priorities</option>
                {PRIORITIES.map((p) => (
                  <option key={p.value} value={p.value}>{p.label}</option>
                ))}
              </select>
              {pendingCount > 0 && (
                <button
                  onClick={selectAllPending}
                  className="px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-100 dark:bg-earth-700 dark:hover:bg-earth-700"
                >
                  Select All Pending ({pendingCount})
                </button>
              )}
            </div>
          )}
        </div>

        {/* Selection List Table */}
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
          </div>
        ) : (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-lsc-border dark:border-earth-700 bg-earth-50 dark:bg-earth-900/50">
                    <th className="text-left py-3 px-4 w-10">
                      <input
                        type="checkbox"
                        checked={selectedItems.length === pendingCount && pendingCount > 0}
                        onChange={() => selectedItems.length === pendingCount ? setSelectedItems([]) : selectAllPending()}
                        className="rounded border-lsc-border dark:border-earth-700"
                      />
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Title</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Author</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">ISBN</th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Price</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Priority</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Status</th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {selectionData?.items.map((item) => {
                    const pendingItems = selectionData?.items.filter(i => i.status === 'pending') || []
                    const pendingIds = pendingItems.map(i => i.id)
                    const pendingIndex = pendingItems.findIndex(i => i.id === item.id)
                    return (
                    <tr key={item.id} className="border-b border-earth-100 dark:border-earth-700/50 hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-700/30">
                      <td className="py-3 px-4">
                        {item.status === 'pending' && (
                          <input
                            type="checkbox"
                            checked={selectedItems.includes(item.id)}
                            onChange={(e) => toggleSelectItem(item.id, pendingIndex, pendingIds, e.nativeEvent instanceof MouseEvent && e.nativeEvent.shiftKey)}
                            className="rounded border-lsc-border dark:border-earth-700"
                            title={t('selectionList.holdShiftToSelectRange')}
                          />
                        )}
                      </td>
                      <td className="py-3 px-4">
                        <p className="font-medium text-lsc-dark dark:text-lsc-cream">{item.title}</p>
                        {item.publisher && (
                          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{item.publisher}</p>
                        )}
                      </td>
                      <td className="py-3 px-4 text-lsc-dark/70 dark:text-lsc-cream/70">{item.author || '-'}</td>
                      <td className="py-3 px-4 font-mono text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{item.isbn || '-'}</td>
                      <td className="py-3 px-4 text-right text-lsc-dark dark:text-lsc-cream">
                        {item.price ? `$${item.price.toFixed(2)}` : '-'}
                      </td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getPriorityBadge(item.priority)}`}>
                          {item.priority}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getStatusBadge(item.status)}`}>
                          {item.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={() => setDeleteConfirm(item)}
                          className="p-1 text-status-danger-500 hover:text-status-danger-700 dark:text-status-danger-300"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
  )})}

                </tbody>
              </table>
            </div>

            {selectionData?.items.length === 0 && (
              <div className="p-8 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
                <ClipboardList className="w-12 h-12 mx-auto mb-4 text-earth-300 dark:text-earth-300" />
                <p>{t('selectionList.noItemsInSelectionList')}</p>
              </div>
            )}
          </div>
        )}

        {/* Add Item Modal */}
        {showAddModal && (
          <ModalBackdrop onClose={() => { setShowAddModal(false); resetForm() }} title="Add to Selection List">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
              <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
                <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">{t('selectionList.addToSelectionList')}</h3>
                <button onClick={() => { setShowAddModal(false); resetForm() }} className="text-earth-600 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-earth-200">
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Search or Manual Entry Toggle */}
              <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex gap-2">
                <button
                  onClick={() => setShowExternalSearch(false)}
                  className={`px-4 py-2 rounded-lg font-medium ${!showExternalSearch ? 'bg-lsc-rose text-white' : 'bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70'}`}
                >
                  Manual Entry
                </button>
                <button
                  onClick={() => setShowExternalSearch(true)}
                  className={`px-4 py-2 rounded-lg font-medium ${showExternalSearch ? 'bg-lsc-rose text-white' : 'bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70'}`}
                >
                  Search External
                </button>
              </div>

              {showExternalSearch ? (
                /* External Search */
                <div className="p-4 space-y-4 max-h-[60vh] overflow-y-auto">
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={externalQuery}
                      onChange={(e) => setExternalQuery(e.target.value)}
                      placeholder={t('selectionList.searchByTitleAuthorOr')}
                      aria-label={t('selectionList.searchByTitleAuthorOr2')}
                      onKeyDown={(e) => e.key === 'Enter' && handleExternalSearch()}
                      className="flex-1 px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                    />
                    <button
                      onClick={handleExternalSearch}
                      disabled={isSearching}
                      className="px-4 py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 disabled:opacity-50"
                    >
                      {isSearching ? <Loader2 className="w-5 h-5 motion-safe:animate-spin" /> : <Search className="w-5 h-5" />}
                    </button>
                  </div>

                  {searchResults.length > 0 && (
                    <div className="space-y-2">
                      {searchResults.map((result, index) => (
                        <div
                          key={index}
                          onClick={() => selectFromSearch(result)} tabIndex={0} role="button" onKeyDown={(e: React.KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); (() => selectFromSearch(result))(); } }}
                          className="p-3 bg-earth-50 dark:bg-earth-700/50 rounded-lg cursor-pointer hover:bg-earth-100 dark:hover:bg-earth-700"
                        >
                          <div className="flex items-start gap-3">
                            <BookOpen className="w-10 h-10 text-lsc-dark/70 dark:text-lsc-cream/70 flex-shrink-0" />
                            <div className="flex-1 min-w-0">
                              <p className="font-medium text-lsc-dark dark:text-lsc-cream">{result.title}</p>
                              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{result.author}</p>
                              <div className="mt-1 flex items-center gap-3 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                                {result.isbn && <span>ISBN: {result.isbn}</span>}
                                {result.publisher && <span>{result.publisher}</span>}
                                {result.price && <span>${result.price.toFixed(2)}</span>}
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                /* Manual Entry Form */
                <div className="p-4 space-y-4 max-h-[60vh] overflow-y-auto">
                  <div>
                    <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Title *</label>
                    <input
                      type="text"
                      value={formData.title}
                      onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                      required
                      className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Author</label>
                      <input
                        type="text"
                        value={formData.author}
                        onChange={(e) => setFormData({ ...formData, author: e.target.value })}
                        className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">ISBN</label>
                      <input
                        type="text"
                        value={formData.isbn}
                        onChange={(e) => setFormData({ ...formData, isbn: e.target.value })}
                        className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Publisher</label>
                      <input
                        type="text"
                        value={formData.publisher}
                        onChange={(e) => setFormData({ ...formData, publisher: e.target.value })}
                        className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Publication Year</label>
                      <input
                        type="number"
                        value={formData.publication_year || ''}
                        onChange={(e) => {
                          // eslint-disable-next-line @typescript-eslint/no-unused-vars
                          const { publication_year: _, ...rest } = formData
                          if (e.target.value) {
                            setFormData({ ...rest, publication_year: parseInt(e.target.value) })
                          } else {
                            setFormData(rest as SelectionListCreateData)
                          }
                        }}
                        className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Price</label>
                      <input
                        type="number"
                        value={formData.price || ''}
                        onChange={(e) => {
                          // eslint-disable-next-line @typescript-eslint/no-unused-vars
                          const { price: _, ...rest } = formData
                          if (e.target.value) {
                            setFormData({ ...rest, price: parseFloat(e.target.value) })
                          } else {
                            setFormData(rest as SelectionListCreateData)
                          }
                        }}
                        step="0.01"
                        className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Format</label>
                      <input
                        type="text"
                        value={formData.format}
                        onChange={(e) => setFormData({ ...formData, format: e.target.value })}
                        placeholder={t('placeholder.selectionList.hardcoverPaperback')}
                        className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Priority</label>
                      <select
                        value={formData.priority}
                        onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
                        className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                      >
                        {PRIORITIES.map((p) => (
                          <option key={p.value} value={p.value}>{p.label}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Notes</label>
                    <textarea
                      value={formData.notes}
                      onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                      rows={2}
                      className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                    />
                  </div>
                </div>
              )}

              <div className="p-4 border-t border-lsc-border dark:border-earth-700 flex justify-end gap-2">
                <button
                  onClick={() => { setShowAddModal(false); resetForm() }}
                  className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70"
                >
                  Cancel
                </button>
                <button
                  onClick={() => addMutation.mutate(formData)}
                  disabled={addMutation.isPending || !formData.title}
                  className="px-4 py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 disabled:opacity-50"
                >
                  {addMutation.isPending ? <Loader2 className="w-5 h-5 motion-safe:animate-spin" /> : 'Add Item'}
                </button>
              </div>
            </div>
          </ModalBackdrop>
        )}

        {/* Convert to PO Modal */}
        {showConvertModal && (
          <ModalBackdrop onClose={() => setShowConvertModal(false)} title="Convert to Purchase Order">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg max-w-md w-full">
              <div className="p-4 border-b border-lsc-border dark:border-earth-700">
                <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">{t('selectionList.convertToPurchaseOrder')}</h3>
              </div>
              <div className="p-4 space-y-4">
                <div className="p-3 bg-earth-50 dark:bg-earth-800/20 rounded-lg">
                  <p className="text-sm text-lsc-rose dark:text-lsc-rose-light">
                    <CheckCircle className="w-4 h-4 inline mr-1" />
                    {selectedItems.length} item{selectedItems.length !== 1 ? 's' : ''} selected
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Vendor *</label>
                  <select
                    value={selectedVendor || ''}
                    onChange={(e) => setSelectedVendor(e.target.value ? parseInt(e.target.value) : null)}
                    className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  >
                    <option value="">Select vendor...</option>
                    {vendorsData?.items.map((vendor) => (
                      <option key={vendor.id} value={vendor.id}>{vendor.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Fund *</label>
                  <select
                    value={selectedFund || ''}
                    onChange={(e) => setSelectedFund(e.target.value ? parseInt(e.target.value) : null)}
                    className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  >
                    <option value="">Select fund...</option>
                    {fundsData?.items.map((fund) => (
                      <option key={fund.id} value={fund.id}>{fund.name} (${(fund.current_balance ?? 0).toLocaleString()} available)</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="p-4 border-t border-lsc-border dark:border-earth-700 flex justify-end gap-2">
                <button
                  onClick={() => setShowConvertModal(false)}
                  className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70"
                >
                  Cancel
                </button>
                <button
                  onClick={handleConvert}
                  disabled={convertMutation.isPending || !selectedVendor || !selectedFund}
                  className="px-4 py-2 rounded-lg bg-status-success-600 text-white hover:bg-status-success-700 disabled:opacity-50"
                >
                  {convertMutation.isPending ? <Loader2 className="w-5 h-5 motion-safe:animate-spin" /> : 'Create PO'}
                </button>
              </div>
            </div>
          </ModalBackdrop>
        )}

        {/* Delete Confirmation */}
        <ConfirmDialog
          isOpen={!!deleteConfirm}
          onCancel={() => setDeleteConfirm(null)}
          onConfirm={() => { if (deleteConfirm) removeMutation.mutate(deleteConfirm.id) }}
          title="Remove Item"
          message={`Are you sure you want to remove "${deleteConfirm?.title}" from the selection list?`}
          confirmText="Remove"
          confirmVariant="danger"
        />
      </PageContainer>
    </div>
    </AdminShell>
  )
}
