/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useLayoutEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import {
  Heart,
  Loader2,
  Check,
  List,
  Plus,
} from 'lucide-react'
import { clsx } from '@/utils/helpers'
import ShareButton from '@/components/ShareButton'
import type { CatalogItem, ReadingList } from '@/api/api'
import type { User } from '@/api/domains/auth/auth-api'
import { Button } from '@/components/ui/Button'
import { t } from '@/i18n'

// Menu width must match the Tailwind w-64 utility used on the menu element.
const MENU_WIDTH_PX = 256
const VIEWPORT_EDGE_GUTTER_PX = 8

interface ItemActionsProps {
  item: CatalogItem
  isFavorited: boolean
  isLoadingFavorite: boolean
  onToggleFavorite: () => Promise<void>
  lists: ReadingList[]
  listsWithItem: Set<number>
  onAddToList: (listId: number) => Promise<void>
  onCreateNewList: () => void
  onCreateListSubmit: () => Promise<void>
  onCancelCreateList: () => void
  showListDropdown: boolean
  setShowListDropdown: (show: boolean) => void
  showCreateListForm: boolean
  setShowCreateListForm: (show: boolean) => void
  newListName: string
  setNewListName: (name: string) => void
  creatingList: boolean
  user: User | null
  token: string | null
  reduceMotion: boolean
  onListMenuKeyDown: (event: React.KeyboardEvent<HTMLDivElement>) => void
  dropdownRef: React.RefObject<HTMLDivElement>
  addToListButtonRef: React.RefObject<HTMLButtonElement>
}

export function ItemActions({
  item,
  isFavorited,
  isLoadingFavorite,
  onToggleFavorite,
  lists,
  listsWithItem,
  onAddToList,
  onCreateNewList,
  onCreateListSubmit,
  onCancelCreateList,
  showListDropdown,
  setShowListDropdown,
  showCreateListForm,
  newListName,
  setNewListName,
  creatingList,
  user,
  token,
  onListMenuKeyDown,
  dropdownRef,
}: ItemActionsProps): React.ReactElement {
  // Portal the dropdown menu so it escapes the ancestor card's
  // `overflow-hidden`, which previously clipped the menu's bottom items.
  // Position is computed from the trigger wrapper's bounding rect and
  // refreshed on scroll/resize while the menu is open.
  const [menuPos, setMenuPos] = useState<{ top: number; left: number } | null>(null)

  // Use layout-effect so position settles synchronously before paint - the
  // parent's "focus first item" useEffect queries the portaled menu by id
  // and would miss it if the portal had not yet mounted.
  useLayoutEffect(() => {
    if (!showListDropdown) {
      setMenuPos(null)
      return
    }
    function updatePos(): void {
      if (!dropdownRef.current) return
      const rect = dropdownRef.current.getBoundingClientRect()
      const maxLeft = window.innerWidth - MENU_WIDTH_PX - VIEWPORT_EDGE_GUTTER_PX
      const left = Math.min(Math.max(rect.left, VIEWPORT_EDGE_GUTTER_PX), Math.max(maxLeft, VIEWPORT_EDGE_GUTTER_PX))
      setMenuPos({ top: rect.bottom + 8, left })
    }
    updatePos()
    window.addEventListener('resize', updatePos)
    window.addEventListener('scroll', updatePos, true)
    return () => {
      window.removeEventListener('resize', updatePos)
      window.removeEventListener('scroll', updatePos, true)
    }
  }, [showListDropdown, dropdownRef])

  return (
    <div className="flex flex-wrap gap-3">
      {/* Share Button */}
      <ShareButton
        resourceType="book"
        resourceId={item.id}
        title={item.title}
        {...(item.description ? { description: item.description } : {})}
        {...(item.author ? { author: item.author } : {})}
        {...(item.cover_url ? { imageUrl: item.cover_url } : {})}
        variant="default"
        showCount={true}
        platforms={['copy_link', 'bluesky', 'mastodon', 'email']}
      />

      {/* Favorite Button */}
      {user && token && (
        <Button variant="secondary"
          onClick={onToggleFavorite}
          disabled={isLoadingFavorite}
          aria-pressed={isFavorited}
          aria-label={isFavorited ? 'Remove from favorites' : 'Add to favorites'}
        >
          {isLoadingFavorite ? (
            <Loader2 className="w-5 h-5 motion-safe:animate-spin" aria-hidden="true" />
          ) : (
            <Heart
              aria-hidden="true"
              className={clsx('w-5 h-5', isFavorited && 'fill-current')}
            />
          )}
          {isFavorited ? 'Favorited' : 'Favorite'}
        </Button>
      )}

      {/* Add to List Dropdown */}
      {user && token && (
        <div className="relative" ref={dropdownRef}>
          <Button variant="secondary"
            onClick={() => setShowListDropdown(!showListDropdown)}
            aria-expanded={showListDropdown}
            aria-haspopup="menu"
            aria-controls="add-to-list-menu"
          >
            <List aria-hidden="true" className="w-5 h-5" />
            Add to List
          </Button>

          {/* Dropdown Menu (portaled to body to escape the ancestor card's
              overflow-hidden). */}
          {showListDropdown && menuPos && createPortal(
            <div
              style={{ position: 'fixed', top: menuPos.top, left: menuPos.left, width: MENU_WIDTH_PX, zIndex: 9999 }}
              className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl shadow-lg max-h-80 overflow-y-auto"
              id="add-to-list-menu"
              role="menu"
              aria-label={t('aria.itemActions.selectAList')}
              onKeyDown={onListMenuKeyDown}
            >
              {lists.length === 0 ? (
                <div className="p-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 text-center">
                  No lists yet.{' '}
                  <a href="/account?tab=lists" className="text-lsc-rose hover:underline">Create one</a>
                </div>
              ) : (
                <div className="py-2">
                  {lists.map((list: ReadingList) => {
                    const isInList = listsWithItem.has(list.id)
                    return (
                      <button
                        key={list.id}
                        onClick={() => onAddToList(list.id)}
                        disabled={isInList}
                        data-list-item
                        role="menuitem"
                        className="w-full flex items-center justify-between gap-2 px-4 py-2.5 text-left text-sm hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <span className="text-lsc-dark dark:text-lsc-cream/80 truncate" title={list.name}>{list.name}</span>
                        {isInList && (
                          <Check aria-hidden="true" className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0" />
                        )}
                      </button>
                    )
                  })}
                </div>
              )}

              {/* Create New List Option */}
              <div className="border-t border-lsc-border dark:border-earth-700">
                {showCreateListForm ? (
                  <div className="p-3 space-y-2">
                    <input
                      type="text"
                      value={newListName}
                      onChange={(e) => setNewListName(e.target.value)}
                      placeholder={t('placeholder.itemActions.listName')}
                      maxLength={200}
                      disabled={creatingList}
                      autoFocus
                      className="w-full px-3 py-2 text-sm border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:ring-2 focus:ring-lsc-rose focus:border-transparent disabled:opacity-50"
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && newListName.trim()) {
                          onCreateListSubmit()
                        } else if (e.key === 'Escape') {
                          onCancelCreateList()
                        }
                      }}
                    />
                    <div className="flex items-center gap-2">
                      <Button variant="primary" size="sm"
                        onClick={onCreateListSubmit}
                        disabled={creatingList || !newListName.trim()}
                      >
                        {creatingList ? (
                          <Loader2 aria-hidden="true" className="w-4 h-4 motion-safe:animate-spin" />
                        ) : (
                          <>
                            <Plus aria-hidden="true" className="w-4 h-4" />
                            Create & Add
                          </>
                        )}
                      </Button>
                      <Button variant="secondary" size="sm"
                        onClick={onCancelCreateList}
                        disabled={creatingList}
                      >
                        Cancel
                      </Button>
                    </div>
                  </div>
                ) : (
                  <button
                    onClick={onCreateNewList}
                    data-list-item
                    role="menuitem"
                    className="w-full flex items-center gap-2 px-4 py-2.5 text-left text-sm text-lsc-rose hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors font-medium"
                  >
                    <Plus aria-hidden="true" className="w-4 h-4" />
                    Create New List
                  </button>
                )}
              </div>
            </div>,
            document.body
          )}
        </div>
      )}
    </div>
  )
}
