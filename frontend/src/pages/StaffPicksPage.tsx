/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../contexts/AuthContext"
import { AdminShell } from '../components/shells/AdminShell'
import {
  getStaffPicksLists,
  createStaffPicksList,
  getStaffPicksListWithItems,
  updateStaffPicksList,
  deleteStaffPicksList,
  addItemToStaffPicksList,
  removeItemFromStaffPicksList,
  updateStaffPicksItem,
  reorderStaffPicksItems,
  StaffPicksList,
  StaffPicksListWithItems,
  StaffPicksItem,
} from "../api/domains/content/staff-picks-api"
import { searchCatalog, CatalogItem } from "../api/catalog-api"
import { Plus, Loader2, RefreshCw } from "lucide-react"
import toast from "react-hot-toast"
import { useTranslation, getCurrentLocale } from '@/i18n'
import { ListsView } from '../components/staff-picks/ListsView'
import { ListDetailView } from '../components/staff-picks/ListDetailView'
import { ListModal } from '../components/staff-picks/ListModal'
import { AddItemModal } from '../components/staff-picks/AddItemModal'
import { EditItemModal } from '../components/staff-picks/EditItemModal'
import { DeleteListModal } from '../components/staff-picks/DeleteListModal'

type ViewMode = "lists" | "detail"

export default function StaffPicksPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user, token, isLoading: authLoading, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  const [viewMode, setViewMode] = useState<ViewMode>("lists")
  const [isLoading, setIsLoading] = useState(true)
  const [lists, setLists] = useState<StaffPicksList[]>([])
  const [includeInactive, setIncludeInactive] = useState(false)
  const [selectedList, setSelectedList] = useState<StaffPicksListWithItems | null>(null)
  const [isLoadingList, setIsLoadingList] = useState(false)

  const [showListModal, setShowListModal] = useState(false)
  const [isEditingList, setIsEditingList] = useState(false)
  const [listForm, setListForm] = useState({ title: "", description: "", display_order: 0, is_active: true })
  const [isSavingList, setIsSavingList] = useState(false)

  const [showAddItemModal, setShowAddItemModal] = useState(false)
  const [catalogSearchQuery, setCatalogSearchQuery] = useState("")
  const [catalogSearchResults, setCatalogSearchResults] = useState<CatalogItem[]>([])
  const [isSearchingCatalog, setIsSearchingCatalog] = useState(false)
  const [selectedCatalogItem, setSelectedCatalogItem] = useState<CatalogItem | null>(null)
  const [itemNotes, setItemNotes] = useState("")
  const [isAddingItem, setIsAddingItem] = useState(false)

  const [showEditItemModal, setShowEditItemModal] = useState(false)
  const [editingItem, setEditingItem] = useState<StaffPicksItem | null>(null)
  const [editItemNotes, setEditItemNotes] = useState("")
  const [isSavingItem, setIsSavingItem] = useState(false)

  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [deletingList, setDeletingList] = useState<StaffPicksList | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)

  useEffect(() => {
    if (!authLoading && (!user || user.role === "patron")) {
      toast.error(t('toast.acquisitionManagement.staffAccessRequired'))
      navigate("/account")
    }
  }, [authLoading, isAuthenticated, user, navigate, t])

  const fetchLists = useCallback(async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const data = await getStaffPicksLists(token, includeInactive)
      setLists(data)
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : t('toast.staffPicks.failedToLoadLists'))
    } finally {
      setIsLoading(false)
    }
  }, [token, includeInactive, t])

  useEffect(() => {
    if (token && isAuthenticated) {
      fetchLists()
    }
  }, [token, isAuthenticated, fetchLists])

  const loadListDetail = async (listId: number) => {
    if (!token) return
    setIsLoadingList(true)
    try {
      const data = await getStaffPicksListWithItems(token, listId)
      setSelectedList(data)
      setViewMode("detail")
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : t('toast.staffPicks.failedToLoadListDetails'))
    } finally {
      setIsLoadingList(false)
    }
  }

  const handleSaveList = async () => {
    if (!token || !listForm.title.trim()) {
      toast.error(t('toast.acquisition.titleIsRequired'))
      return
    }
    setIsSavingList(true)
    try {
      if (isEditingList && selectedList) {
        const descriptionValue = listForm.description.trim()
        const updated = await updateStaffPicksList(token, selectedList.id, {
          title: listForm.title.trim(),
          ...(descriptionValue ? { description: descriptionValue } : {}),
          display_order: listForm.display_order,
          is_active: listForm.is_active,
        })
        toast.success(t('toast.staffPicks.listUpdatedSuccessfully'))
        await loadListDetail(updated.id)
      } else {
        const created = await createStaffPicksList(token, listForm.title.trim(), listForm.description.trim() || undefined)
        toast.success(t('toast.staffPicks.listCreatedSuccessfully'))
        await fetchLists()
        await loadListDetail(created.id)
      }
      setShowListModal(false)
      resetListForm()
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : t('toast.staffPicks.failedToSaveList'))
    } finally {
      setIsSavingList(false)
    }
  }

  const handleDeleteList = async () => {
    if (!token || !deletingList) return
    setIsDeleting(true)
    try {
      await deleteStaffPicksList(token, deletingList.id)
      toast.success(t('toast.staffPicks.listDeletedSuccessfully'))
      setShowDeleteConfirm(false)
      setDeletingList(null)
      if (selectedList?.id === deletingList.id) {
        setSelectedList(null)
        setViewMode("lists")
      }
      await fetchLists()
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : t('toast.staffPicks.failedToDeleteList'))
    } finally {
      setIsDeleting(false)
    }
  }

  const handleToggleActive = async (list: StaffPicksList) => {
    if (!token) return
    try {
      await updateStaffPicksList(token, list.id, { is_active: !list.is_active })
      toast.success(list.is_active ? t('toast.staffPicks.listUnpublished') : t('toast.staffPicks.listPublished'))
      await fetchLists()
      if (selectedList?.id === list.id) {
        await loadListDetail(list.id)
      }
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : t('toast.staffPicks.failedToUpdateList'))
    }
  }

  const handleSetFeatured = async (list: StaffPicksList) => {
    if (!token) return
    try {
      await updateStaffPicksList(token, list.id, { display_order: 0 })
      toast.success(t('staffPicks.listSetAsFeatured'))
      await fetchLists()
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : t('toast.staffPicks.failedToSetFeatured'))
    }
  }

  const handleCatalogSearch = async () => {
    if (!catalogSearchQuery.trim()) return
    setIsSearchingCatalog(true)
    try {
      const result = await searchCatalog({ query: catalogSearchQuery, per_page: 20 })
      setCatalogSearchResults(result.items)
    } catch {
      toast.error(t('staffPicks.failedToSearchCatalog'))
    } finally {
      setIsSearchingCatalog(false)
    }
  }

  const handleAddItem = async () => {
    if (!token || !selectedList || !selectedCatalogItem) return
    setIsAddingItem(true)
    try {
      await addItemToStaffPicksList(token, selectedList.id, selectedCatalogItem.id, itemNotes.trim() || undefined)
      toast.success(t('staffPicks.itemAddedToList'))
      setShowAddItemModal(false)
      setSelectedCatalogItem(null)
      setItemNotes("")
      setCatalogSearchQuery("")
      setCatalogSearchResults([])
      await loadListDetail(selectedList.id)
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : t('toast.staffPicks.failedToAddItem'))
    } finally {
      setIsAddingItem(false)
    }
  }

  const handleRemoveItem = async (item: StaffPicksItem) => {
    if (!token || !selectedList) return
    try {
      await removeItemFromStaffPicksList(token, selectedList.id, item.id)
      toast.success(t('staffPicks.itemRemovedFromList'))
      await loadListDetail(selectedList.id)
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : t('toast.staffPicks.failedToRemoveItem'))
    }
  }

  const handleUpdateItem = async () => {
    if (!token || !selectedList || !editingItem) return
    setIsSavingItem(true)
    try {
      const notesValue = editItemNotes.trim()
      await updateStaffPicksItem(token, selectedList.id, editingItem.id, {
        ...(notesValue ? { staff_notes: notesValue } : {}),
      })
      toast.success(t('toast.useStaffCataloging.itemUpdated'))
      setShowEditItemModal(false)
      setEditingItem(null)
      setEditItemNotes("")
      await loadListDetail(selectedList.id)
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : t('toast.staffPicks.failedToUpdateItem'))
    } finally {
      setIsSavingItem(false)
    }
  }

  const handleMoveItem = async (item: StaffPicksItem, direction: "up" | "down") => {
    if (!token || !selectedList) return
    const items = [...selectedList.items]
    const currentIndex = items.findIndex((i) => i.id === item.id)
    if (currentIndex === -1) return
    const newIndex = direction === "up" ? currentIndex - 1 : currentIndex + 1
    if (newIndex < 0 || newIndex >= items.length) return
    const currentItem = items[currentIndex]
    const swapItem = items[newIndex]
    if (currentItem && swapItem) {
      items[currentIndex] = swapItem
      items[newIndex] = currentItem
    }
    try {
      await reorderStaffPicksItems(token, selectedList.id, items.map((i) => i.id))
      await loadListDetail(selectedList.id)
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : t('toast.staffPicks.failedToReorderItems'))
    }
  }

  const resetListForm = () => {
    setListForm({ title: "", description: "", display_order: 0, is_active: true })
    setIsEditingList(false)
  }

  const openEditListModal = (list: StaffPicksListWithItems) => {
    setListForm({ title: list.title, description: list.description || "", display_order: list.display_order, is_active: list.is_active })
    setIsEditingList(true)
    setShowListModal(true)
  }

  const openEditItemModal = (item: StaffPicksItem) => {
    setEditingItem(item)
    setEditItemNotes(item.staff_notes || "")
    setShowEditItemModal(true)
  }

  const formatDate = (dateStr: string | null | undefined) => {
    if (!dateStr) return "—"
    const d = new Date(dateStr)
    if (isNaN(d.getTime()) || d.getFullYear() < 2000) return "—"
    return d.toLocaleDateString(getCurrentLocale(), { month: "short", day: "numeric", year: "numeric" })
  }

  if (authLoading || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" />
      </div>
    )
  }

  if (!user || user.role === "patron") {
    return <></>
  }

  return (
    <AdminShell title="Staff Picks" subtitle="Create and manage curated reading lists for patrons">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div></div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchLists}
            className="flex items-center gap-2 px-4 py-2 text-lsc-rose dark:text-lsc-rose-light hover:bg-lsc-cream dark:hover:bg-lsc-brown/20 rounded-xl transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
          <button
            onClick={() => { resetListForm(); setShowListModal(true) }}
            className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 transition-colors"
          >
            <Plus className="w-4 h-4" />
            New List
          </button>
        </div>
      </div>

      {viewMode === "lists" && (
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            <input
              type="checkbox"
              checked={includeInactive}
              onChange={(e) => setIncludeInactive(e.target.checked)}
              className="rounded border-lsc-border dark:border-earth-700 text-lsc-rose focus:ring-lsc-rose"
            />
            Show inactive lists
          </label>
        </div>
      )}

      {viewMode === "lists" ? (
        <ListsView
          lists={lists}
          onCreateList={() => { resetListForm(); setShowListModal(true) }}
          onLoadDetail={loadListDetail}
          onToggleActive={handleToggleActive}
          onSetFeatured={handleSetFeatured}
          onDeleteList={(list) => { setDeletingList(list); setShowDeleteConfirm(true) }}
          formatDate={formatDate}
        />
      ) : (
        <ListDetailView
          selectedList={selectedList}
          isLoadingList={isLoadingList}
          onBack={() => { setViewMode("lists"); setSelectedList(null) }}
          onEditList={openEditListModal}
          onToggleActive={handleToggleActive}
          onAddItem={() => setShowAddItemModal(true)}
          onEditItem={openEditItemModal}
          onRemoveItem={handleRemoveItem}
          onMoveItem={handleMoveItem}
          formatDate={formatDate}
        />
      )}

      {showListModal && (
        <ListModal
          isEditing={isEditingList}
          form={listForm}
          onFormChange={setListForm}
          onSave={handleSaveList}
          onClose={() => { setShowListModal(false); resetListForm() }}
          isSaving={isSavingList}
        />
      )}

      {showAddItemModal && selectedList && (
        <AddItemModal
          searchQuery={catalogSearchQuery}
          onSearchQueryChange={setCatalogSearchQuery}
          onSearch={handleCatalogSearch}
          isSearching={isSearchingCatalog}
          searchResults={catalogSearchResults}
          selectedItem={selectedCatalogItem}
          onSelectItem={setSelectedCatalogItem}
          onClearItem={() => setSelectedCatalogItem(null)}
          itemNotes={itemNotes}
          onNotesChange={setItemNotes}
          onAdd={handleAddItem}
          isAdding={isAddingItem}
          onClose={() => {
            setShowAddItemModal(false)
            setCatalogSearchQuery("")
            setCatalogSearchResults([])
            setSelectedCatalogItem(null)
            setItemNotes("")
          }}
        />
      )}

      {showEditItemModal && editingItem && (
        <EditItemModal
          item={editingItem}
          notes={editItemNotes}
          onNotesChange={setEditItemNotes}
          onSave={handleUpdateItem}
          onClose={() => { setShowEditItemModal(false); setEditingItem(null); setEditItemNotes("") }}
          isSaving={isSavingItem}
        />
      )}

      {showDeleteConfirm && deletingList && (
        <DeleteListModal
          list={deletingList}
          onConfirm={handleDeleteList}
          onCancel={() => { setShowDeleteConfirm(false); setDeletingList(null) }}
          isDeleting={isDeleting}
        />
      )}
    </AdminShell>
  )
}
