/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../../contexts/AuthContext"
import { CatalogItem, CatalogSearchResult, checkDuplicates, DuplicateCandidate, bulkUpdateCatalogItems, fetchCoverForItem, listCatalogImages, CatalogImage as CatalogImageType } from "../../api/catalog-api"
import { fetchApi } from "@/lib/api-client"
import { searchZ3950, Z3950SearchResult } from "../../api/cataloging-api"
import { CatalogItemCreate, createCatalogItem, updateCatalogItem, deleteCatalogItem } from "../../api/staff-api/catalog"
import { BulkAction, useBulkSelection } from "../../components/staff/BulkOperationsPanel"
import { Tag, MapPin } from "lucide-react"
import toast from "react-hot-toast"
import { CATALOGING_DRAFT_KEY, emptyForm, type FormData } from "./constants"
import { t } from '@/i18n'
import { useOptimisticLock } from '../../hooks/useOptimisticLock'
import { getCatalogItem } from '../../api/catalog-api'
import { getRationale } from '../../api/acquisitionRationale'

export function useStaffCataloging() {
  const { user, token, isLoading: authLoading, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  // Search state
  const [searchQuery, setSearchQuery] = useState("")
  const [catalogingStatusFilter, setCatalogingStatusFilter] = useState<string | null>(null)
  const [searchResults, setSearchResults] = useState<CatalogSearchResult | null>(null)
  const [isSearching, setIsSearching] = useState(false)
  const [currentPage, setCurrentPage] = useState(1)

  // Form state
  const [showAddForm, setShowAddForm] = useState(false)
  const [editingItem, setEditingItem] = useState<CatalogItem | null>(null)
  const [formData, setFormData] = useState<FormData>(emptyForm)
  const [isSaving, setIsSaving] = useState(false)
  const [hasRationale, setHasRationale] = useState<boolean>(false)
  const [statsRefreshKey, setStatsRefreshKey] = useState(0)

  // Optimistic locking for concurrent edit detection
  const optimisticLock = useOptimisticLock("catalog", editingItem?.id ?? null, editingItem?.updated_at ?? null)

  // Delete state
  const [deleteConfirm, setDeleteConfirm] = useState<CatalogItem | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)

  // Duplicate detection state
  const [duplicates, setDuplicates] = useState<DuplicateCandidate[]>([])
  const [isCheckingDuplicates, setIsCheckingDuplicates] = useState(false)
  const [showDuplicateWarning, setShowDuplicateWarning] = useState(false)
  const duplicateCheckTimeout = useRef<NodeJS.Timeout | null>(null)
  const z3950AutoTimeout = useRef<NodeJS.Timeout | null>(null)

  // Z39.50 state
  const [showZ3950Search, setShowZ3950Search] = useState(false)
  const [z3950Results, setZ3950Results] = useState<Z3950SearchResult[]>([])
  const [isSearchingZ3950, setIsSearchingZ3950] = useState(false)
  const [selectedZ3950Record, setSelectedZ3950Record] = useState<Z3950SearchResult | null>(null)

  // Cover fetch state
  const [isFetchingCover, setIsFetchingCover] = useState(false)

  // Catalog images state
  const [catalogImages, setCatalogImages] = useState<CatalogImageType[]>([])

  // Bulk action modal state
  const [bulkModal, setBulkModal] = useState<{
    type: 'status' | 'location'
    ids: number[]
  } | null>(null)
  const [bulkModalValue, setBulkModalValue] = useState("")
  const [isBulkUpdating, setIsBulkUpdating] = useState(false)

  // Draft autosave state
  const [draftRestored, setDraftRestored] = useState(false)
  const draftSaveTimeout = useRef<NodeJS.Timeout | null>(null)

  // Bulk selection
  const { selectedIds, setSelectedIds, toggleSelection, isSelected, selectedCount } = useBulkSelection()

  // Auth guard
  useEffect(() => {
    if (!authLoading && (!user || user.role === "patron")) {
      toast.error(t('toast.acquisitionManagement.staffAccessRequired'))
      navigate("/account")
    }
  }, [authLoading, isAuthenticated, user, navigate])

  // Autosave form draft to localStorage (debounced)
  useEffect(() => {
    if (!showAddForm || editingItem) return
    const hasData = formData.title || formData.author || formData.isbn
    if (!hasData) {
      localStorage.removeItem(CATALOGING_DRAFT_KEY)
      return
    }
    if (draftSaveTimeout.current) clearTimeout(draftSaveTimeout.current)
    draftSaveTimeout.current = setTimeout(() => {
      localStorage.setItem(CATALOGING_DRAFT_KEY, JSON.stringify(formData))
    }, 1000)
    return () => {
      if (draftSaveTimeout.current) clearTimeout(draftSaveTimeout.current)
    }
  }, [formData, showAddForm, editingItem])

  // Warn before navigating away with unsaved form data
  useEffect(() => {
    if (!showAddForm) return
    const hasData = formData.title || formData.author || formData.isbn
    if (!hasData) return
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault()
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [showAddForm, formData.title, formData.author, formData.isbn])

  const handleSearch = useCallback(async (page = 1) => {
    if (!token) return
    setIsSearching(true)
    try {
      const params = new URLSearchParams()
      if (searchQuery) params.set('q', searchQuery)
      if (catalogingStatusFilter) params.set('cataloging_status', catalogingStatusFilter)
      params.set('page', page.toString())
      params.set('per_page', '20')
      const result = await fetchApi<CatalogSearchResult>(`/staff/catalog/items?${params}`)
      setSearchResults(result)
      setCurrentPage(page)
      setSelectedIds([])
    } catch {
      toast.error(t('toast.selectionList.searchFailed'))
    } finally {
      setIsSearching(false)
    }
  }, [token, searchQuery, catalogingStatusFilter, setSelectedIds])

  // Initial search
  useEffect(() => {
    if (token && isAuthenticated && user?.role !== "patron") handleSearch(1)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, isAuthenticated, user])

  // Re-search when cataloging status filter changes
  useEffect(() => {
    if (token && isAuthenticated) handleSearch(1)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [catalogingStatusFilter])

  // Duplicate check with debounce
  const checkForDuplicates = useCallback(async () => {
    if (!token || (!formData.isbn && !formData.title)) {
      setDuplicates([])
      return
    }

    setIsCheckingDuplicates(true)
    try {
      const result = await checkDuplicates(token, {
        ...(formData.isbn ? { isbn: formData.isbn } : {}),
        ...(formData.title ? { title: formData.title } : {}),
        ...(formData.author ? { author: formData.author } : {}),
        ...(editingItem?.id != null ? { exclude_id: editingItem.id } : {}),
      })
      setDuplicates(result.duplicates)
      if (result.has_duplicates) {
        setShowDuplicateWarning(true)
      }
    } catch {
      // Silent fail - don't block user
    } finally {
      setIsCheckingDuplicates(false)
    }
  }, [token, formData.isbn, formData.title, formData.author, editingItem?.id])

  // Trigger duplicate check when ISBN or title changes
  useEffect(() => {
    if (duplicateCheckTimeout.current) {
      clearTimeout(duplicateCheckTimeout.current)
    }
    if (formData.isbn || formData.title) {
      duplicateCheckTimeout.current = setTimeout(checkForDuplicates, 500)
    } else {
      setDuplicates([])
    }
    return () => {
      if (duplicateCheckTimeout.current) clearTimeout(duplicateCheckTimeout.current)
    }
  }, [formData.isbn, formData.title, formData.author, checkForDuplicates])

  // Z39.50 search
  const handleZ3950Search = async () => {
    if (!formData.isbn && !formData.title) {
      toast.error(t('toast.useStaffCataloging.enterAnIsbnOrTitle'))
      return
    }
    setIsSearchingZ3950(true)
    try {
      const result = await searchZ3950({
        ...(formData.isbn ? { isbn: formData.isbn } : {}),
        ...(formData.title ? { title: formData.title } : {}),
        ...(formData.author ? { author: formData.author } : {}),
        source: 'loc',
        max_results: 5,
      })
      setZ3950Results(result.results)
      if (result.results.length === 0) {
        toast(result.hint || "No records found in Library of Congress")
      }
    } catch {
      toast.error(t('toast.useStaffCataloging.z3950SearchFailed'))
    } finally {
      setIsSearchingZ3950(false)
    }
  }



  // Auto-trigger Z39.50 on valid ISBN entry (debounced)
  useEffect(() => {
    if (z3950AutoTimeout.current) clearTimeout(z3950AutoTimeout.current)
    if (!showAddForm || editingItem) return
    const isbn = formData.isbn.trim()
    const isValidIsbn = /^\d{9}[\dX]$/.test(isbn) || /^\d{13}$/.test(isbn)
    if (isValidIsbn && !formData.title.trim()) {
      z3950AutoTimeout.current = setTimeout(() => {
        handleZ3950Search()
      }, 400)
    }
    return () => {
      if (z3950AutoTimeout.current) clearTimeout(z3950AutoTimeout.current)
    }
  }, [formData.isbn, formData.title, showAddForm, editingItem])

  // Import Z39.50 record into form (bulk import, kept for backward compat)
  const importZ3950Record = (record: Z3950SearchResult) => {
    setFormData(prev => ({
      ...prev,
      title: record.title || prev.title,
      author: record.author || prev.author,
      isbn: record.isbn || prev.isbn,
      publisher: record.publisher || prev.publisher,
      publication_year: record.publication_year?.toString() || prev.publication_year,
      description: record.description || prev.description,
      subjects: record.subjects?.join(", ") || prev.subjects,
    }))
    setShowZ3950Search(false)
    setZ3950Results([])
    setSelectedZ3950Record(null)
    toast.success(t('toast.useStaffCataloging.recordImportedFromLibraryOf'))
  }

  // Select a Z39.50 record for side-by-side preview
  const selectZ3950Record = (record: Z3950SearchResult) => {
    setSelectedZ3950Record(record)
  }

  // Import a single field from the selected Z39.50 record
  const useZ3950Field = (key: keyof FormData, value: string) => {
    setFormData(prev => ({ ...prev, [key]: value }))
  }

  // Import all fields from the selected Z39.50 record
  const useAllZ3950Data = () => {
    if (!selectedZ3950Record) return
    importZ3950Record(selectedZ3950Record)
  }

  // Clear the Z39.50 preview selection (back to results list)
  const clearZ3950Selection = () => {
    setSelectedZ3950Record(null)
  }

  // Fetch cover for current item
  const handleFetchCover = async () => {
    if (!token || !editingItem?.id) return
    setIsFetchingCover(true)
    try {
      const updated = await fetchCoverForItem(token, editingItem.id)
      if (updated.cover_url) {
        setFormData(prev => ({ ...prev, cover_url: updated.cover_url || "" }))
        toast.success(t('toast.useStaffCataloging.coverFetchedSuccessfully'))
      } else {
        toast("No cover found for this item")
      }
    } catch {
      toast.error(t('toast.useStaffCataloging.failedToFetchCover'))
    } finally {
      setIsFetchingCover(false)
    }
  }

  // Load images for the editing item
  const loadCatalogImages = useCallback(async (itemId: number) => {
    try {
      const result = await listCatalogImages(itemId)
      setCatalogImages(result.images)
    } catch {
      setCatalogImages([])
    }
  }, [])

  const handleImagesChanged = useCallback(() => {
    if (editingItem?.id) {
      loadCatalogImages(editingItem.id)
      handleSearch(currentPage)
    }
  }, [editingItem?.id, loadCatalogImages, handleSearch, currentPage])

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    handleSearch(1)
  }

  const openAddForm = () => {
    const savedDraft = localStorage.getItem(CATALOGING_DRAFT_KEY)
    if (savedDraft) {
      try {
        const parsed = JSON.parse(savedDraft) as FormData
        setFormData({ ...emptyForm, ...parsed })
        setDraftRestored(true)
        setShowZ3950Search(false)
      } catch {
        setFormData(emptyForm)
        setDraftRestored(false)
        setShowZ3950Search(true)
      }
    } else {
      setFormData(emptyForm)
      setDraftRestored(false)
      setShowZ3950Search(true)
    }
    setEditingItem(null)
    setDuplicates([])
    setShowDuplicateWarning(false)
    setSelectedZ3950Record(null)
    setShowAddForm(true)
  }

  const openEditForm = (item: CatalogItem) => {
    setFormData({
      title: item.title || "", author: item.author || "", isbn: item.isbn || "", item_type: item.item_type || "book",
      publication_year: item.publication_year?.toString() || "", publisher: item.publisher || "",
      description: item.description || "", subjects: item.subjects || "", location: item.location || "",
      barcode: item.barcode || "", status: item.status || "available", cover_url: item.cover_url || "",
      edition: (item as unknown as Record<string, unknown>).edition as string || "",
      page_count: (item as unknown as Record<string, unknown>).page_count ? String((item as unknown as Record<string, unknown>).page_count) : "",
      series_name: (item as unknown as Record<string, unknown>).series_name as string || "",
      series_number: (item as unknown as Record<string, unknown>).series_number as string || "",
      is_large_print: !!(item as unknown as Record<string, unknown>).is_large_print,
      director: item.director || "", actors: item.actors || "", runtime_minutes: item.runtime_minutes?.toString() || "",
      media_format: item.media_format || "", content_rating: item.content_rating || "",
      disc_count: item.disc_count?.toString() || "", studio: item.studio || "",
      artist: item.artist || "", track_count: item.track_count?.toString() || "", music_genre: item.music_genre || "",
      platform: item.platform || "", player_count: item.player_count || "", game_genre: item.game_genre || "",
      brand: item.brand || "", model_number: item.model_number || "", dimensions: item.dimensions || "",
      material: item.material || "", kit_contents: item.kit_contents || "",
      safety_certification_required: !!(item as unknown as Record<string, unknown>).safety_certification_required,
      certification_name: (item as unknown as Record<string, unknown>).certification_name as string || "",
      power_source: (item as unknown as Record<string, unknown>).power_source as string || "",
      voltage: (item as unknown as Record<string, unknown>).voltage as string || "",
      weight_lbs: (item as unknown as Record<string, unknown>).weight_lbs ? String((item as unknown as Record<string, unknown>).weight_lbs) : "",
      safety_category: (item as unknown as Record<string, unknown>).safety_category as string || "",
      accessories_included: (item as unknown as Record<string, unknown>).accessories_included as string || "",
      consumables_needed: (item as unknown as Record<string, unknown>).consumables_needed as string || "",
      condition_notes: (item as unknown as Record<string, unknown>).condition_notes as string || "",
      replacement_cost: (item as unknown as Record<string, unknown>).replacement_cost ? String((item as unknown as Record<string, unknown>).replacement_cost) : "",
      lexile_measure: (item as unknown as Record<string, unknown>).lexile_measure as string || "",
      cataloging_status: (item as unknown as Record<string, unknown>).cataloging_status as string || "",
    })
    setEditingItem(item)
    setCatalogImages(item.images || [])
    loadCatalogImages(item.id)
    setDuplicates([])
    setShowDuplicateWarning(false)
    setShowAddForm(true)
    setHasRationale(false)
    getRationale(item.id).then(r => setHasRationale(r !== null)).catch(() => setHasRationale(false))
  }

  // Work next (E2): open the first item of the given cataloging status on the
  // current page; if none is loaded here, fall back to filtering the table.
  const handleWorkNext = (status: string) => {
    const next = searchResults?.items.find(
      (item) => (item as unknown as Record<string, unknown>).cataloging_status === status
    )
    if (next) {
      openEditForm(next)
    } else {
      setCatalogingStatusFilter(status)
    }
  }

  const reloadEditingItem = useCallback(async () => {
    if (!editingItem?.id) return
    try {
      const fresh = await getCatalogItem(editingItem.id)
      openEditForm(fresh)
      optimisticLock.clearConflict()
      toast.success("Item reloaded with latest changes")
    } catch {
      toast.error("Failed to reload item")
    }
  }, [editingItem?.id])

  const handleForceSave = useCallback(() => {
    optimisticLock.forceSave()
  }, [optimisticLock.forceSave])

  const closeForm = () => {
    setShowAddForm(false)
    setEditingItem(null)
    setFormData(emptyForm)
    setCatalogImages([])
    setDuplicates([])
    setShowDuplicateWarning(false)
    setShowZ3950Search(false)
    setZ3950Results([])
    setSelectedZ3950Record(null)
    setDraftRestored(false)
    localStorage.removeItem(CATALOGING_DRAFT_KEY)
  }

  const handleFormChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const target = e.target
    const { name } = target
    const value = target instanceof HTMLInputElement && target.type === 'checkbox' ? target.checked : target.value
    setFormData((prev) => ({ ...prev, [name]: value }))
  }

  const handleGenerateBarcode = () => {
    const charset = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    const randomChars = Array.from({ length: 8 }, () => {
      const randomIndex = Math.floor(Math.random() * charset.length)
      return charset[randomIndex]
    }).join("")

    setFormData((prev) => ({ ...prev, barcode: `LSC-${randomChars}` }))
  }

  // eslint-disable-next-line complexity
  const handleSubmit = async (e: React.SyntheticEvent, keepOpen = false): Promise<boolean> => {
    e.preventDefault()
    if (!token) return false
    if (!formData.title.trim()) {
      toast.error(t('toast.acquisition.titleIsRequired'))
      return false
    }
    if (editingItem && formData.cataloging_status === 'cataloged' && !hasRationale) {
      toast.error(t('acquisitionRationale.requiredBeforeCataloged'))
      return false
    }

    if (duplicates.length > 0 && !showDuplicateWarning) {
      setShowDuplicateWarning(true)
      return false
    }


    // Check for concurrent edits before saving
    if (editingItem) {
      const hasConflict = await optimisticLock.checkForConflict()
      if (hasConflict) return false
    }

    setIsSaving(true)
    try {
      const payload: CatalogItemCreate = { title: formData.title.trim(), item_type: formData.item_type }
      if (formData.author.trim()) payload.author = formData.author.trim()
      if (formData.isbn.trim()) payload.isbn = formData.isbn.trim()
      if (formData.publication_year) payload.publication_year = parseInt(formData.publication_year)
      if (formData.publisher.trim()) payload.publisher = formData.publisher.trim()
      if (formData.description.trim()) payload.description = formData.description.trim()
      if (formData.subjects.trim()) payload.subjects = formData.subjects.trim()
      if (formData.location.trim()) payload.location = formData.location.trim()
      if (formData.barcode.trim()) payload.barcode = formData.barcode.trim()
      if (formData.status) payload.status = formData.status
      if (formData.cover_url.trim()) payload.cover_url = formData.cover_url.trim()
      if (formData.edition.trim()) payload.edition = formData.edition.trim()
      if (formData.page_count) payload.page_count = parseInt(formData.page_count)
      if (formData.series_name.trim()) payload.series_name = formData.series_name.trim()
      if (formData.series_number.trim()) payload.series_number = formData.series_number.trim()
      if (formData.is_large_print) payload.is_large_print = true
      if (formData.director.trim()) payload.director = formData.director.trim()
      if (formData.actors.trim()) payload.actors = formData.actors.trim()
      if (formData.runtime_minutes) payload.runtime_minutes = parseInt(formData.runtime_minutes)
      if (formData.media_format) payload.media_format = formData.media_format
      if (formData.content_rating) payload.content_rating = formData.content_rating
      if (formData.disc_count) payload.disc_count = parseInt(formData.disc_count)
      if (formData.studio.trim()) payload.studio = formData.studio.trim()
      if (formData.artist.trim()) payload.artist = formData.artist.trim()
      if (formData.track_count) payload.track_count = parseInt(formData.track_count)
      if (formData.music_genre.trim()) payload.music_genre = formData.music_genre.trim()
      if (formData.platform.trim()) payload.platform = formData.platform.trim()
      if (formData.player_count.trim()) payload.player_count = formData.player_count.trim()
      if (formData.game_genre.trim()) payload.game_genre = formData.game_genre.trim()
      if (formData.brand.trim()) payload.brand = formData.brand.trim()
      if (formData.model_number.trim()) payload.model_number = formData.model_number.trim()
      if (formData.dimensions.trim()) payload.dimensions = formData.dimensions.trim()
      if (formData.material.trim()) payload.material = formData.material.trim()
      if (formData.kit_contents.trim()) payload.kit_contents = formData.kit_contents.trim()
      if (formData.lexile_measure?.trim()) payload.lexile_measure = formData.lexile_measure.trim()
      if (formData.cataloging_status?.trim()) payload.cataloging_status = formData.cataloging_status.trim()

      if (editingItem) {
        await updateCatalogItem(token, editingItem.id, payload)
        toast.success(t('toast.useStaffCataloging.itemUpdated'))
      } else {
        await createCatalogItem(token, payload)
        toast.success(t('toast.useStaffCataloging.itemCreated'))
      }
      // Save & add another: keep the modal open on a successful CREATE, clearing
      // only the per-item identity fields while preserving shelf/vendor context.
      if (keepOpen && !editingItem) {
        setFormData((prev) => ({
          ...prev,
          title: "", author: "", isbn: "", barcode: "", cover_url: "",
        }))
        setDuplicates([])
        setShowDuplicateWarning(false)
        setShowZ3950Search(false)
        setSelectedZ3950Record(null)
        setDraftRestored(false)
        localStorage.removeItem(CATALOGING_DRAFT_KEY)
      } else {
        closeForm()
      }
      handleSearch(currentPage)
      setStatsRefreshKey((k) => k + 1)
      return true
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.useStaffCataloging.unableToSavePleaseTry'))
      return false
    } finally {
      setIsSaving(false)
    }
  }

  const handleSubmitKeepOpen = (e: React.SyntheticEvent): Promise<boolean> => handleSubmit(e, true)

  const handleDelete = async () => {
    if (!token || !deleteConfirm) return
    setIsDeleting(true)
    try {
      await deleteCatalogItem(token, deleteConfirm.id)
      toast.success(t('toast.useStaffCataloging.itemDeleted'))
      setDeleteConfirm(null)
      handleSearch(currentPage)
      setStatsRefreshKey((k) => k + 1)
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : t('toast.useStaffCataloging.unableToDeletePleaseTry'))
    } finally {
      setIsDeleting(false)
    }
  }

  // Bulk modal submit handler
  const handleBulkModalSubmit = async () => {
    if (!bulkModal || !bulkModalValue.trim() || !token) return
    setIsBulkUpdating(true)
    try {
      const updatePayload: Record<string, string> = bulkModal.type === 'status'
        ? { status: bulkModalValue }
        : { location: bulkModalValue.trim() }
      const result = await bulkUpdateCatalogItems(token, bulkModal.ids, updatePayload)
      await handleSearch(currentPage)
      setStatsRefreshKey((k) => k + 1)
      if (result.failure_count === 0) {
        toast.success(t('toast.useStaffCataloging.updatedSuccesscountItems', { successcount: result.success_count }))
      } else {
        toast.error(t('toast.useStaffCataloging.failurecountItemsFailedToUpdate', { failurecount: result.failure_count }))
      }
    } catch {
      toast.error(t('toast.useStaffCataloging.bulkUpdateFailed'))
    } finally {
      setIsBulkUpdating(false)
      setBulkModal(null)
      setBulkModalValue("")
    }
  }

  // Bulk actions
  const bulkActions: BulkAction[] = [
    {
      id: 'change-status',
      label: 'Change Status',
      icon: <Tag className="w-4 h-4" />,
      description: 'Update status for selected items',
      onExecute: async (ids) => {
        setBulkModal({ type: 'status', ids })
        setBulkModalValue("")
        return { success: true, successCount: 0, failureCount: 0, message: "Select a status" }
      },
      confirmMessage: (count) => `Change status for ${count} selected items?`,
    },
    {
      id: 'change-location',
      label: 'Change Location',
      icon: <MapPin className="w-4 h-4" />,
      description: 'Update location for selected items',
      onExecute: async (ids) => {
        setBulkModal({ type: 'location', ids })
        setBulkModalValue("")
        return { success: true, successCount: 0, failureCount: 0, message: "Enter a location" }
      },
    },
  ]

  return {
    // Auth
    user,
    token,
    authLoading,

    // Workflow status refresh
    statsRefreshKey,

    // Search
    searchQuery,
    setSearchQuery,
    searchResults,
    isSearching,
    currentPage,
    handleSearch,
    handleSearchSubmit,
    catalogingStatusFilter,
    setCatalogingStatusFilter,

    // Form
    showAddForm,
    editingItem,
    formData,
    setFormData,
    isSaving,
    handleFormChange,
    handleGenerateBarcode,
    handleSubmit,
    handleSubmitKeepOpen,
    handleWorkNext,
    openAddForm,
    openEditForm,
    closeForm,
    hasRationale,
    setHasRationale,

    // Delete
    deleteConfirm,
    setDeleteConfirm,
    isDeleting,
    handleDelete,

    // Duplicates
    duplicates,
    isCheckingDuplicates,
    showDuplicateWarning,
    setShowDuplicateWarning,

    // Z39.50
    showZ3950Search,
    setShowZ3950Search,
    z3950Results,
    isSearchingZ3950,
    handleZ3950Search,
    importZ3950Record,
    selectedZ3950Record,
    selectZ3950Record,
    useZ3950Field,
    useAllZ3950Data,
    clearZ3950Selection,

    // Cover
    isFetchingCover,
    handleFetchCover,

    // Images
    catalogImages,
    handleImagesChanged,

    // Bulk
    bulkModal,
    setBulkModal,
    bulkModalValue,
    setBulkModalValue,
    isBulkUpdating,
    handleBulkModalSubmit,
    bulkActions,

    // Selection
    selectedIds,
    setSelectedIds,
    toggleSelection,
    isSelected,
    selectedCount,

    // Draft
    draftRestored,
    setDraftRestored,

    // Optimistic locking
    isStale: optimisticLock.isStale,
    conflictData: optimisticLock.conflictData,
    onForceSave: handleForceSave,
    onReloadItem: reloadEditingItem,
    onCancelConflict: optimisticLock.clearConflict,
  }
}
