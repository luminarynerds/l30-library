/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Reading Lists Tab
 * Displays user's reading lists with creation, viewing, and deletion functionality
 */
import React, { useState } from 'react'
import {
  RefreshCw,
  Loader2,
  List,
  Calendar,
  Book,
  Trash2,
  Plus,
  X,
  ArrowLeft,
  ExternalLink,
  Lock,
  Globe,
  Link2,
  Check,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { ReadingList, ReadingListWithItems } from '../../api/api'
import ConfirmDialog from '../ConfirmDialog'
import { t, getCurrentLocale } from '@/i18n'

interface ListsSectionProps {
  lists: ReadingList[]
  loading: boolean
  creating: boolean
  deletingId: number | null
  onRefresh: () => void
  onCreate: (name: string, description?: string) => Promise<ReadingList | null>
  onDelete: (listId: number) => void
  onGetList: (listId: number) => Promise<ReadingListWithItems | null>
  onRemoveItem: (listId: number, catalogItemId: number) => Promise<boolean>
  onUpdatePrivacy?: (listId: number, isPublic: boolean) => Promise<ReadingList | null>
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString(getCurrentLocale(), {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

export const ListsSection: React.FC<ListsSectionProps> = ({
  lists,
  loading,
  creating,
  deletingId,
  onRefresh,
  onCreate,
  onDelete,
  onGetList,
  onRemoveItem,
  onUpdatePrivacy,
}) => {
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [newListName, setNewListName] = useState('')
  const [newListDescription, setNewListDescription] = useState('')

  // View list state
  const [viewingList, setViewingList] = useState<ReadingListWithItems | null>(null)
  const [loadingList, setLoadingList] = useState(false)
  const [removingItemId, setRemovingItemId] = useState<number | null>(null)
  const [togglingPrivacy, setTogglingPrivacy] = useState<number | null>(null)
  const [copiedListId, setCopiedListId] = useState<number | null>(null)

  // Confirmation dialog state
  const [confirmDeleteListId, setConfirmDeleteListId] = useState<number | null>(null)
  const [confirmRemoveItemId, setConfirmRemoveItemId] = useState<number | null>(null)
  const listToDelete = lists.find((l) => l.id === confirmDeleteListId)
  const itemToRemove = viewingList?.items.find((i) => i.catalog_item_id === confirmRemoveItemId)

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newListName.trim()) return

    const result = await onCreate(newListName.trim(), newListDescription.trim() || undefined)
    if (result) {
      setNewListName('')
      setNewListDescription('')
      setShowCreateForm(false)
    }
  }

  const handleCancelCreate = () => {
    setNewListName('')
    setNewListDescription('')
    setShowCreateForm(false)
  }

  const handleViewList = async (listId: number) => {
    setLoadingList(true)
    const listDetails = await onGetList(listId)
    if (listDetails) {
      setViewingList(listDetails)
    }
    setLoadingList(false)
  }

  const handleBackToLists = () => {
    setViewingList(null)
  }

  const handleRemoveItem = async (catalogItemId: number) => {
    if (!viewingList) return
    setRemovingItemId(catalogItemId)
    const success = await onRemoveItem(viewingList.id, catalogItemId)
    if (success) {
      // Update local state to remove the item
      setViewingList({
        ...viewingList,
        items: viewingList.items.filter(item => item.catalog_item_id !== catalogItemId),
        item_count: viewingList.item_count - 1,
      })
    }
    setRemovingItemId(null)
  }

  const handleTogglePrivacy = async (listId: number, currentIsPublic: boolean) => {
    if (!onUpdatePrivacy) return
    setTogglingPrivacy(listId)
    try {
      await onUpdatePrivacy(listId, !currentIsPublic)
    } finally {
      setTogglingPrivacy(null)
    }
  }

  const handleCopyLink = async (listId: number) => {
    const url = `${window.location.origin}/public-reading-lists/${listId}`
    try {
      await navigator.clipboard.writeText(url)
      setCopiedListId(listId)
      toast.success('Link copied to clipboard')
      setTimeout(() => setCopiedListId(null), 2000)
    } catch {
      toast.error('Failed to copy link')
    }
  }

  // View single list mode
  if (viewingList) {
    return (
      <div>
        <div className="flex items-center gap-4 mb-6">
          <button
            onClick={handleBackToLists}
            className="flex items-center gap-2 text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
            Back to Lists
          </button>
        </div>

        <div className="mb-6">
          <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
            {viewingList.name}
          </h2>
          {viewingList.description && (
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{viewingList.description}</p>
          )}
          <div className="flex items-center gap-4 mt-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            <span>{viewingList.item_count} {viewingList.item_count === 1 ? 'item' : 'items'}</span>
            <span>Created: {formatDate(viewingList.created_at)}</span>
          </div>
        </div>

        {viewingList.items.length === 0 ? (
          <div className="text-center py-12">
            <Book className="w-12 h-12 text-sage/30 mx-auto mb-3" />
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{'This list is empty'}</p>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              Browse the catalog to add items to this list
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {viewingList.items.map((item) => (
              <div
                key={item.id}
                className="p-4 rounded-xl border-2 border-sage/20 bg-cream dark:bg-earth-800"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                      {item.catalog_item.title}
                    </h3>
                    {item.catalog_item.author && (
                      <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm mt-1">
                        by {item.catalog_item.author}
                      </p>
                    )}
                    <div className="flex items-center gap-4 mt-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      {item.catalog_item.item_type && (
                        <span className="capitalize">{item.catalog_item.item_type}</span>
                      )}
                      <span>Added: {formatDate(item.added_at)}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 ml-4">
                    <a
                      href={`/catalog/${item.catalog_item_id}`}
                      className="px-3 py-2 text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream transition-colors flex items-center gap-1"
                    >
                      <ExternalLink className="w-4 h-4" />
                      View
                    </a>
                    <button
                      onClick={() => setConfirmRemoveItemId(item.catalog_item_id)}
                      disabled={removingItemId === item.catalog_item_id}
                      className="px-3 py-2 bg-status-danger-600 text-white rounded-xl hover:bg-status-danger-700 transition-colors disabled:opacity-50 flex items-center gap-1"
                    >
                      {removingItemId === item.catalog_item_id ? (
                        <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                      ) : (
                        <>
                          <Trash2 className="w-4 h-4" />
                          Remove
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        <ConfirmDialog
          isOpen={confirmRemoveItemId !== null}
          title="Remove from list?"
          message={
            itemToRemove
              ? `Remove "${itemToRemove.catalog_item.title}" from "${viewingList.name}"?`
              : 'Remove this item from the list?'
          }
          confirmText="Yes, remove"
          cancelText="Keep"
          confirmVariant="danger"
          onConfirm={() => {
            if (confirmRemoveItemId !== null) {
              handleRemoveItem(confirmRemoveItemId)
            }
            setConfirmRemoveItemId(null)
          }}
          onCancel={() => setConfirmRemoveItemId(null)}
        />
      </div>
    )
  }

  // Main lists view
  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          My Reading Lists
        </h2>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowCreateForm(true)}
            disabled={showCreateForm || creating}
            className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 transition-colors disabled:opacity-50"
          >
            <Plus className="w-5 h-5" />
            Create List
          </button>
          <button
            onClick={onRefresh}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-5 h-5 ${loading ? 'motion-safe:animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Create List Form */}
      {showCreateForm && (
        <div className="mb-6 p-6 rounded-xl border-2 border-lsc-rose/30 bg-lsc-rose/5 dark:bg-lsc-rose/10">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream text-lg">
              Create New List
            </h3>
            <button
              onClick={handleCancelCreate}
              disabled={creating}
              className="text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream transition-colors disabled:opacity-50"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
          <form onSubmit={handleCreateSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="list-name"
                className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1"
              >
                List Name <span className="text-status-danger-500">*</span>
              </label>
              <input
                id="list-name"
                type="text"
                value={newListName}
                onChange={(e) => setNewListName(e.target.value)}
                placeholder={t('placeholder.account.egSummerReadingFavorites')}
                maxLength={200}
                required
                disabled={creating}
                className="w-full px-4 py-2 border border-sage/30 dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:ring-2 focus:ring-lsc-rose focus:border-transparent disabled:opacity-50"
              />
            </div>
            <div>
              <label
                htmlFor="list-description"
                className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1"
              >
                Description <span className="text-lsc-dark/70 dark:text-lsc-cream/70">(optional)</span>
              </label>
              <textarea
                id="list-description"
                value={newListDescription}
                onChange={(e) => setNewListDescription(e.target.value)}
                placeholder={'What is this list about?'}
                rows={2}
                disabled={creating}
                className="w-full px-4 py-2 border border-sage/30 dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:ring-2 focus:ring-lsc-rose focus:border-transparent disabled:opacity-50 resize-none"
              />
            </div>
            <div className="flex items-center gap-3">
              <button
                type="submit"
                disabled={creating || !newListName.trim()}
                className="flex items-center gap-2 px-6 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 transition-colors disabled:opacity-50"
              >
                {creating ? (
                  <>
                    <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Plus className="w-4 h-4" />
                    Create List
                  </>
                )}
              </button>
              <button
                type="button"
                onClick={handleCancelCreate}
                disabled={creating}
                className="px-4 py-2 text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Loading list details overlay */}
      {loadingList && (
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-dark/70 dark:text-lsc-cream/70" />
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-dark/70 dark:text-lsc-cream/70" />
        </div>
      ) : lists.length === 0 ? (
        <div className="text-center py-12">
          <List className="w-12 h-12 text-sage/30 mx-auto mb-3" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{'No reading lists yet'}</p>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
            Create your first list to start organizing your reading!
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {lists.map((list) => (
            // eslint-disable-next-line jsx-a11y/click-events-have-key-events
            <div
              key={list.id}
              className="p-4 rounded-xl border-2 border-sage/20 bg-cream dark:bg-earth-800 hover:border-sage/40 transition-colors cursor-pointer"
              onClick={() => handleViewList(list.id)}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream text-lg">
                      {list.name}
                    </h3>
                    {list.is_public ? (
                      <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300 text-xs font-medium">
                        <Globe className="w-3 h-3" />
                        Public
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-earth-200 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-xs font-medium">
                        <Lock className="w-3 h-3" />
                        Private
                      </span>
                    )}
                  </div>
                  {list.description && (
                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm mt-1">{list.description}</p>
                  )}
                  <div className="flex items-center gap-4 mt-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    <div className="flex items-center gap-1">
                      <Book className="w-4 h-4" />
                      <span>
                        {list.item_count} {list.item_count === 1 ? 'item' : 'items'}
                      </span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Calendar className="w-4 h-4" />
                      <span>Created: {formatDate(list.created_at)}</span>
                    </div>
                  </div>
                </div>
                <div className="ml-4 flex items-center gap-2">
                  {onUpdatePrivacy && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleTogglePrivacy(list.id, list.is_public || false)
                      }}
                      disabled={togglingPrivacy === list.id}
                      title={list.is_public ? 'Make private' : 'Make public'}
                      className="px-3 py-2 bg-lsc-rose/20 text-lsc-rose hover:bg-lsc-rose/30 dark:bg-lsc-rose/10 dark:hover:bg-lsc-rose/20 rounded-xl transition-colors disabled:opacity-50 flex items-center gap-1"
                    >
                      {togglingPrivacy === list.id ? (
                        <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                      ) : list.is_public ? (
                        <>
                          <Globe className="w-4 h-4" />
                          <span className="text-sm">Public</span>
                        </>
                      ) : (
                        <>
                          <Lock className="w-4 h-4" />
                          <span className="text-sm">Private</span>
                        </>
                      )}
                    </button>
                  )}
                  {list.is_public && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleCopyLink(list.id)
                      }}
                      title="Copy share link"
                      className="px-3 py-2 bg-earth-100 dark:bg-earth-700 text-earth-600 dark:text-earth-300 hover:bg-earth-200 dark:hover:bg-earth-600 rounded-xl transition-colors flex items-center gap-1"
                    >
                      {copiedListId === list.id ? (
                        <>
                          <Check className="w-4 h-4 text-status-success-600" />
                          <span className="text-sm">Copied</span>
                        </>
                      ) : (
                        <>
                          <Link2 className="w-4 h-4" />
                          <span className="text-sm">Share</span>
                        </>
                      )}
                    </button>
                  )}
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      setConfirmDeleteListId(list.id)
                    }}
                    disabled={deletingId === list.id}
                    className="px-4 py-2 bg-status-danger-600 text-white rounded-xl hover:bg-status-danger-700 transition-colors disabled:opacity-50 flex items-center gap-2"
                  >
                    {deletingId === list.id ? (
                      <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                    ) : (
                      <>
                        <Trash2 className="w-4 h-4" />
                        Delete
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <ConfirmDialog
        isOpen={confirmDeleteListId !== null}
        title={'Delete this reading list?'}
        message={
          listToDelete
            ? `Permanently delete "${listToDelete.name}" and all ${listToDelete.item_count} ${listToDelete.item_count === 1 ? 'item' : 'items'} in it? This cannot be undone.`
            : 'Permanently delete this list? This cannot be undone.'
        }
        confirmText="Yes, delete list"
        cancelText="Keep list"
        confirmVariant="danger"
        onConfirm={() => {
          if (confirmDeleteListId !== null) {
            onDelete(confirmDeleteListId)
          }
          setConfirmDeleteListId(null)
        }}
        onCancel={() => setConfirmDeleteListId(null)}
      />
    </div>
  )
}
