/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useRef, useEffect, useCallback } from 'react'
import { List, ChevronDown, Check, Plus, X } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import {
  useAddToList,
  useCreateReadingList,
  useListsContainingItem,
  useMyReadingLists,
  useRemoveFromList,
} from '@/hooks/useMyReadingLists'
import { clsx } from '@/utils/helpers'

interface AddToListDropdownProps {
  catalogItemId: number
  className?: string
}

export function AddToListDropdown({ catalogItemId, className }: AddToListDropdownProps) {
  const { user } = useAuth()
  const [open, setOpen] = useState(false)

  const { data: myLists } = useMyReadingLists()
  // Defer the per-item membership lookup until the dropdown is opened. On a
  // catalog grid this component renders once per card (up to 100 per page), so
  // fetching eagerly fanned out one request per item and tripped rate limiting.
  const { data: containingListIds } = useListsContainingItem(catalogItemId, open)
  const addToList = useAddToList()
  const removeFromList = useRemoveFromList()
  const createList = useCreateReadingList()

  const [creating, setCreating] = useState(false)
  const [newListName, setNewListName] = useState('')
  const dropdownRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const containingSet = new Set(containingListIds ?? [])
  const isInAnyList = containingSet.size > 0

  useEffect(() => {
    if (!open) return
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        setOpen(false)
        setCreating(false)
      }
    }
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false)
        setCreating(false)
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [open])

  useEffect(() => {
    if (creating) inputRef.current?.focus()
  }, [creating])

  const handleToggle = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault()
      e.stopPropagation()
      setOpen((prev) => !prev)
      setCreating(false)
    },
    [],
  )

  const handleListClick = useCallback(
    (e: React.MouseEvent, listId: number) => {
      e.preventDefault()
      e.stopPropagation()
      if (containingSet.has(listId)) {
        removeFromList.mutate({ listId, catalogItemId })
      } else {
        addToList.mutate({ listId, catalogItemId })
      }
    },
    [containingSet, addToList, removeFromList, catalogItemId],
  )

  const handleNewListClick = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault()
      e.stopPropagation()
      setCreating(true)
    },
    [],
  )

  const handleCreateSubmit = useCallback(
    (e: React.MouseEvent | React.KeyboardEvent) => {
      e.preventDefault()
      e.stopPropagation()
      const name = newListName.trim()
      if (!name) return
      createList.mutate(
        { name },
        { onSuccess: (newList) => addToList.mutate({ listId: newList.id, catalogItemId }) },
      )
      setNewListName('')
      setCreating(false)
    },
    [newListName, createList, addToList, catalogItemId],
  )

  const handleCreateCancel = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault()
      e.stopPropagation()
      setCreating(false)
      setNewListName('')
    },
    [],
  )

  const handleInputKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      e.stopPropagation()
      if (e.key === 'Enter') handleCreateSubmit(e)
      if (e.key === 'Escape') {
        e.preventDefault()
        setCreating(false)
        setNewListName('')
      }
    },
    [handleCreateSubmit],
  )

  // Auth gate must run AFTER all hooks so the call count is stable across
  // renders (rule-of-hooks; sibling fix to ShelfBookmark for React #310).
  if (!user) return null

  return (
    <div ref={dropdownRef} className={clsx('relative', className)}>
      <button
        onClick={handleToggle}
        aria-label={isInAnyList ? 'Manage reading lists' : 'Add to reading list'}
        className={clsx(
          'flex items-center justify-center w-9 h-9 rounded-lg transition-all',
          'backdrop-blur-sm bg-black/30 hover:bg-black/50',
          'focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-1',
          isInAnyList && 'text-status-info-400',
          !isInAnyList && 'text-white/90 hover:text-white',
        )}
      >
        <List className="w-4 h-4" aria-hidden="true" />
        <ChevronDown className="w-3 h-3 ml-px" aria-hidden="true" />
      </button>

      {open && (
        <div
          className={clsx(
            'absolute right-0 top-full mt-1 z-30 min-w-[220px] max-h-[300px] overflow-y-auto',
            'rounded-xl shadow-lg py-1',
            'bg-lsc-white dark:bg-lsc-dark',
            'border border-lsc-dark/10 dark:border-lsc-cream/10',
          )}
        >
          {(myLists ?? []).length === 0 && !creating && (
            <p className="px-4 py-3 text-sm text-lsc-dark/60 dark:text-lsc-cream/60">
              No lists yet
            </p>
          )}

          {(myLists ?? []).map((list) => {
            const isInList = containingSet.has(list.id)
            return (
              <button
                key={list.id}
                onClick={(e) => handleListClick(e, list.id)}
                className={clsx(
                  'w-full flex items-center gap-2 px-4 py-2 text-sm text-left transition-colors',
                  'text-lsc-dark dark:text-lsc-cream',
                  'hover:bg-lsc-cream/50 dark:hover:bg-lsc-cream/5',
                )}
              >
                <span className="w-4 h-4 flex-shrink-0 flex items-center justify-center">
                  {isInList && <Check className="w-4 h-4 text-status-info-600 dark:text-status-info-400" aria-hidden="true" />}
                </span>
                <span className="flex-1 truncate">{list.name}</span>
                <span className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50 tabular-nums">
                  {list.item_count ?? 0}
                </span>
              </button>
            )
          })}

          <div className="border-t border-lsc-dark/10 dark:border-lsc-cream/10 mt-1 pt-1">
            {creating ? (
              <div className="flex items-center gap-1 px-3 py-2">
                <input
                  ref={inputRef}
                  type="text"
                  value={newListName}
                  onChange={(e) => setNewListName(e.target.value)}
                  onKeyDown={handleInputKeyDown}
                  onClick={(e) => { e.preventDefault(); e.stopPropagation() }}
                  placeholder="List name"
                  className={clsx(
                    'flex-1 min-w-0 text-sm px-2 py-1 rounded-lg',
                    'bg-lsc-cream/30 dark:bg-lsc-cream/5',
                    'text-lsc-dark dark:text-lsc-cream',
                    'border border-lsc-dark/10 dark:border-lsc-cream/10',
                    'focus:outline-none focus:ring-1 focus:ring-lsc-rose',
                  )}
                />
                <button
                  onClick={handleCreateSubmit}
                  disabled={!newListName.trim()}
                  className="p-1 text-status-info-600 dark:text-status-info-400 disabled:opacity-30"
                  aria-label="Create list"
                >
                  <Check className="w-4 h-4" aria-hidden="true" />
                </button>
                <button
                  onClick={handleCreateCancel}
                  className="p-1 text-lsc-dark/50 dark:text-lsc-cream/50"
                  aria-label="Cancel"
                >
                  <X className="w-4 h-4" aria-hidden="true" />
                </button>
              </div>
            ) : (
              <button
                onClick={handleNewListClick}
                className={clsx(
                  'w-full flex items-center gap-2 px-4 py-2 text-sm transition-colors',
                  'text-status-info-600 dark:text-status-info-400',
                  'hover:bg-lsc-cream/50 dark:hover:bg-lsc-cream/5',
                )}
              >
                <Plus className="w-4 h-4" aria-hidden="true" />
                New list
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
