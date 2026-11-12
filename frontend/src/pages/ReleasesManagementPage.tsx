/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../contexts/AuthContext'
import {
  Plus,
  RefreshCw,
  ShoppingCart,
  Calendar,
  Users,
  AlertCircle,
} from 'lucide-react'
import toast from 'react-hot-toast'
import ConfirmDialog from '../components/ConfirmDialog'
import {
  getLibrarianReleases,
  getStaffAuthors,
  createAuthor,
  refreshAuthor,
  refreshAllAuthors,
  createPOFromReleases,
  type LibrarianReleaseItem,
  type Author,
  type AuthorCreate,
} from '../api/releases-api'
import { getVendors, getFunds, type Vendor, type Fund } from '../api/acquisition-api'
import { useTranslation} from '@/i18n'
import { clean } from '@/lib/utils'
import { AdminShell } from '../components/shells/AdminShell'
import { ReleasesTab } from '../components/releases/ReleasesTab'
import { AuthorsTab } from '../components/releases/AuthorsTab'
import { ReleasesSettingsTab } from '../components/releases/ReleasesSettingsTab'
import { CreateAuthorModal } from '../components/releases/CreateAuthorModal'
import { CreatePOModal } from '../components/releases/CreatePOModal'
import PageContainer from '@/components/layout/PageContainer'

type ActiveTab = 'releases' | 'authors' | 'settings'

export default function ReleasesManagementPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user, isAuthenticated } = useAuth()
  const [activeTab, setActiveTab] = useState<ActiveTab>('releases')
  const [isLoading, setIsLoading] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Releases state
  const [releases, setReleases] = useState<LibrarianReleaseItem[]>([])
  const [releasesTotal, setReleasesTotal] = useState(0)
  const [releasesPage, setReleasesPage] = useState(1)
  const [releaseStatusFilter, setReleaseStatusFilter] = useState<'upcoming' | 'released' | ''>('')
  const [libraryStatusFilter, setLibraryStatusFilter] = useState<'new' | 'owned' | 'on_order' | ''>('')
  const [ageRatingFilter, setAgeRatingFilter] = useState<'child' | 'teen' | 'adult' | ''>('')
  const [minDemandFilter, setMinDemandFilter] = useState<number>(0)
  const [selectedReleases, setSelectedReleases] = useState<Set<string>>(new Set())

  // Authors state
  const [authors, setAuthors] = useState<Author[]>([])
  const [authorsTotal, setAuthorsTotal] = useState(0)
  const [authorsPage, setAuthorsPage] = useState(1)
  const [authorSearch, setAuthorSearch] = useState('')
  const [activeOnly, setActiveOnly] = useState(true)
  const [refreshingAuthorId, setRefreshingAuthorId] = useState<string | null>(null)

  // Author form state
  const [authorForm, setAuthorForm] = useState<AuthorCreate>({
    name: '',
    google_id: '',
    image_url: '',
    bio: '',
    website: '',
  })

  // PO creation state
  const [showPODialog, setShowPODialog] = useState(false)
  const [vendors, setVendors] = useState<Vendor[]>([])
  const [funds, setFunds] = useState<Fund[]>([])
  const [selectedVendor, setSelectedVendor] = useState<number>(0)
  const [selectedFund, setSelectedFund] = useState<number>(0)
  const [useExistingDraft, setUseExistingDraft] = useState(true)

  // Refresh all state
  const [isRefreshingAll, setIsRefreshingAll] = useState(false)
  const [confirmRefreshAll, setConfirmRefreshAll] = useState(false)

  const isStaffOrAdmin =
    isAuthenticated && user && ['admin', 'super_admin', 'staff'].includes(user.role)
  const isAdmin = isAuthenticated && user && ['admin', 'super_admin'].includes(user.role)

  // Load releases
  const loadReleases = useCallback(async () => {
    setIsLoading(true)
    try {
      const params: Record<string, unknown> = {
        page: releasesPage,
        per_page: 25,
      }
      if (releaseStatusFilter) params.status = releaseStatusFilter
      if (libraryStatusFilter) params.library_status = libraryStatusFilter
      if (ageRatingFilter) params.age_rating = ageRatingFilter
      if (minDemandFilter > 0) params.min_demand = minDemandFilter

      const data = await getLibrarianReleases(params)
      setReleases(data.items)
      setReleasesTotal(data.total)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.acquisition.failedToLoadReleases'))
    } finally {
      setIsLoading(false)
    }
  }, [releasesPage, releaseStatusFilter, libraryStatusFilter, ageRatingFilter, minDemandFilter, t])

  // Load authors
  const loadAuthors = useCallback(async () => {
    setIsLoading(true)
    try {
      const data = await getStaffAuthors({
        ...(authorSearch ? { q: authorSearch } : {}),
        active_only: activeOnly,
        page: authorsPage,
        per_page: 25,
      })
      setAuthors(data.items)
      setAuthorsTotal(data.total)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.releaseRadar.failedToLoadAuthors'))
    } finally {
      setIsLoading(false)
    }
  }, [authorsPage, authorSearch, activeOnly, t])

  // Load vendors and funds for PO creation
  const loadVendorsAndFunds = useCallback(async () => {
    try {
      const [vendorsData, fundsData] = await Promise.all([
        getVendors({ status: 'active' }),
        getFunds({ status: 'active' }),
      ])
      setVendors(vendorsData.items)
      setFunds(fundsData.items)
    } catch (err: unknown) {
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)))
    }
  }, [])

  useEffect(() => {
    if (!isStaffOrAdmin) return
    if (activeTab === 'releases') {
      loadReleases()
      loadVendorsAndFunds()
    } else if (activeTab === 'authors') {
      loadAuthors()
    }
  }, [isStaffOrAdmin, activeTab, loadReleases, loadAuthors, loadVendorsAndFunds])

  // Handle author creation
  const handleCreateAuthor = async () => {
    if (!authorForm.name.trim()) {
      toast.error(t('releasesManagement.authorNameIsRequired'))
      return
    }
    setIsSubmitting(true)
    try {
      await createAuthor(clean({
        name: authorForm.name.trim(),
        google_id: authorForm.google_id?.trim() || undefined,
        image_url: authorForm.image_url?.trim() || undefined,
        bio: authorForm.bio?.trim() || undefined,
        website: authorForm.website?.trim() || undefined,
      }))
      toast.success(t('toast.releasesManagement.authorCreatedSuccessfully'))
      setShowForm(false)
      setAuthorForm({ name: '', google_id: '', image_url: '', bio: '', website: '' })
      loadAuthors()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.releasesManagement.failedToCreateAuthor'))
    } finally {
      setIsSubmitting(false)
    }
  }

  // Handle author refresh
  const handleRefreshAuthor = async (authorId: string) => {
    setRefreshingAuthorId(authorId)
    try {
      const stats = await refreshAuthor(authorId)
      toast.success(t('toast.releasesManagement.refreshedBooksaddedAddedBooksupdatedUpdated', { booksadded: stats.books_added, booksupdated: stats.books_updated }))
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.releasesManagement.failedToRefreshAuthor'))
    } finally {
      setRefreshingAuthorId(null)
    }
  }

  // Handle refresh all authors
  const handleRefreshAllAuthors = async () => {
    setIsRefreshingAll(true)
    setConfirmRefreshAll(false)
    try {
      const result = await refreshAllAuthors(true)
      toast.success(result.message)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.releasesManagement.failedToStartRefresh'))
    } finally {
      setIsRefreshingAll(false)
    }
  }

  // Handle release selection
  const toggleReleaseSelection = (bookId: string) => {
    setSelectedReleases((prev) => {
      const newSet = new Set(prev)
      if (newSet.has(bookId)) {
        newSet.delete(bookId)
      } else {
        newSet.add(bookId)
      }
      return newSet
    })
  }

  const selectAllReleases = () => {
    const newReleases = releases.filter((r) => r.library_status === 'new')
    if (selectedReleases.size === newReleases.length) {
      setSelectedReleases(new Set())
    } else {
      setSelectedReleases(new Set(newReleases.map((r) => r.book.id)))
    }
  }

  // Handle PO creation
  const handleCreatePO = async () => {
    if (selectedReleases.size === 0) {
      toast.error(t('releasesManagement.selectAtLeastOneRelease'))
      return
    }
    if (!selectedVendor) {
      toast.error(t('toast.releasesManagement.selectAVendor'))
      return
    }
    if (!selectedFund) {
      toast.error(t('toast.releasesManagement.selectAFund'))
      return
    }

    setIsSubmitting(true)
    try {
      const result = await createPOFromReleases({
        tracker_book_ids: Array.from(selectedReleases),
        vendor_id: selectedVendor,
        fund_id: selectedFund,
        use_existing_draft: useExistingDraft,
      })
      toast.success(t('toast.releasesManagement.poPonumberCreatedWithItemsadded', { ponumber: result.po_number, itemsadded: result.items_added, catalogitemscreated: result.catalog_items_created }))
      setShowPODialog(false)
      setSelectedReleases(new Set())
      loadReleases()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.releasesManagement.failedToCreatePo'))
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!isStaffOrAdmin) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-lsc-cream via-lsc-cream to-earth-50 dark:from-lsc-dark dark:via-earth-800 dark:to-lsc-dark py-20">
        <PageContainer className="text-center">
          <AlertCircle className="w-16 h-16 text-lsc-dark/70 dark:text-lsc-cream/70 mx-auto mb-4" />
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">Staff-Only Area</h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
            Staff or admin access required
          </p>
        </PageContainer>
      </div>
    )
  }

  return (

    <AdminShell title="Releases Management">    <div className="min-h-screen bg-gradient-to-b from-lsc-cream via-lsc-cream to-earth-50 dark:from-lsc-dark dark:via-earth-800 dark:to-lsc-dark py-8">
      <PageContainer>
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
              Release Alerts Management
            </h1>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
              Track upcoming releases, manage authors, and create purchase orders
            </p>
          </div>
          {activeTab === 'authors' && (
            <button
              onClick={() => {
                setAuthorForm({ name: '', google_id: '', image_url: '', bio: '', website: '' })
                setShowForm(true)
              }}
              className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl flex items-center gap-2 transition-colors"
            >
              <Plus className="w-5 h-5" />
              Add Author
            </button>
          )}
          {activeTab === 'releases' && selectedReleases.size > 0 && (
            <button
              onClick={() => setShowPODialog(true)}
              className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl flex items-center gap-2 transition-colors"
            >
              <ShoppingCart className="w-5 h-5" />
              Create PO ({selectedReleases.size})
            </button>
          )}
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 border-b border-lsc-border dark:border-earth-700">
          {[
            { id: 'releases' as const, label: 'Upcoming Releases', icon: Calendar },
            { id: 'authors' as const, label: 'Authors', icon: Users },
            { id: 'settings' as const, label: 'Settings', icon: RefreshCw },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 font-medium border-b-2 transition-colors flex items-center gap-2 ${
                activeTab === tab.id
                  ? 'border-lsc-rose text-lsc-rose'
                  : 'border-transparent text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        {activeTab === 'releases' && (
          <ReleasesTab
            releases={releases}
            releasesTotal={releasesTotal}
            releasesPage={releasesPage}
            releaseStatusFilter={releaseStatusFilter}
            libraryStatusFilter={libraryStatusFilter}
            ageRatingFilter={ageRatingFilter}
            minDemandFilter={minDemandFilter}
            selectedReleases={selectedReleases}
            isLoading={isLoading}
            onReleaseStatusFilter={setReleaseStatusFilter}
            onLibraryStatusFilter={setLibraryStatusFilter}
            onAgeRatingFilter={setAgeRatingFilter}
            onMinDemandFilter={setMinDemandFilter}
            onToggleRelease={toggleReleaseSelection}
            onSelectAll={selectAllReleases}
            onPageChange={setReleasesPage}
          />
        )}

        {activeTab === 'authors' && (
          <AuthorsTab
            authors={authors}
            authorsTotal={authorsTotal}
            authorsPage={authorsPage}
            authorSearch={authorSearch}
            activeOnly={activeOnly}
            refreshingAuthorId={refreshingAuthorId}
            isLoading={isLoading}
            onAuthorSearch={setAuthorSearch}
            onActiveOnly={setActiveOnly}
            onRefreshAuthor={handleRefreshAuthor}
            onPageChange={setAuthorsPage}
          />
        )}

        {activeTab === 'settings' && (
          <ReleasesSettingsTab
            isAdmin={!!isAdmin}
            isRefreshingAll={isRefreshingAll}
            onRefreshAll={() => setConfirmRefreshAll(true)}
          />
        )}
      </PageContainer>

      {/* Create Author Modal */}
      {showForm && (
        <CreateAuthorModal
          authorForm={authorForm}
          isSubmitting={isSubmitting}
          onClose={() => setShowForm(false)}
          onSubmit={handleCreateAuthor}
          onFormChange={setAuthorForm}
        />
      )}

      {/* Create PO Dialog */}
      {showPODialog && (
        <CreatePOModal
          selectedCount={selectedReleases.size}
          vendors={vendors}
          funds={funds}
          selectedVendor={selectedVendor}
          selectedFund={selectedFund}
          useExistingDraft={useExistingDraft}
          isSubmitting={isSubmitting}
          onClose={() => setShowPODialog(false)}
          onSubmit={handleCreatePO}
          onVendorChange={setSelectedVendor}
          onFundChange={setSelectedFund}
          onUseExistingDraftChange={setUseExistingDraft}
        />
      )}

      {/* Confirm Refresh All Dialog */}
      <ConfirmDialog
        isOpen={confirmRefreshAll}
        title="Refresh All Authors?"
        message="This will fetch the latest book information from external sources for all tracked authors. The operation runs in the background and may take several minutes to complete."
        confirmText="Start Refresh"
        cancelText="Cancel"
        confirmVariant="primary"
        onConfirm={handleRefreshAllAuthors}
        onCancel={() => setConfirmRefreshAll(false)}
      />
    </div>
  </AdminShell>
  )
}
