/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import {
  getMyFavorites,
  addFavorite,
  removeFavorite,
  getMyLists,
  addToList,
  createList,
  type CatalogItem,
  type Favorite,
} from '@/api/api'
import { useUnifiedAccessibility } from '@/features/accessibility/hooks/useUnifiedAccessibility'

export function useItemActions(token: string | null, item: CatalogItem | undefined) {
  const { announceToScreenReader } = useUnifiedAccessibility()

  const [isFavorited, setIsFavorited] = useState(false)
  const [isLoadingFavorite, setIsLoadingFavorite] = useState(false)
  const [listsWithItem, setListsWithItem] = useState<Set<number>>(new Set())
  const [showHoldModal, setShowHoldModal] = useState(false)
  const [showListDropdown, setShowListDropdown] = useState(false)
  const [showCreateListForm, setShowCreateListForm] = useState(false)
  const [newListName, setNewListName] = useState('')
  const [creatingList, setCreatingList] = useState(false)

  // Fetch favorites and lists
  const { data: favorites = [], refetch: refetchFavorites } = useQuery({
    queryKey: ['my-favorites', token],
    queryFn: () => getMyFavorites(token!),
    enabled: !!token && !!item,
  })

  const { data: lists = [], refetch: refetchLists } = useQuery({
    queryKey: ['my-lists', token],
    queryFn: () => getMyLists(token!),
    enabled: !!token && !!item,
  })

  // Check if current item is favorited
  useEffect(() => {
    if (item && favorites) {
      const favorited = favorites.some((fav: Favorite) => fav.catalog_item_id === item.id)
      setIsFavorited(favorited)
    }
  }, [item, favorites])

  const handleToggleFavorite = async (): Promise<void> => {
    if (!token || !item) return

    setIsLoadingFavorite(true)
    try {
      if (isFavorited) {
        await removeFavorite(token, item.id)
        toast.success('Removed from favorites')
        announceToScreenReader('Removed from favorites')
        setIsFavorited(false)
      } else {
        await addFavorite(token, item.id)
        toast.success('Added to favorites')
        announceToScreenReader('Added to favorites')
        setIsFavorited(true)
      }
      refetchFavorites()
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Could not update your favorites right now. Please try again.'
      toast.error(message)
      announceToScreenReader(message)
    } finally {
      setIsLoadingFavorite(false)
    }
  }

  const handleAddToList = async (listId: number): Promise<void> => {
    if (!token || !item) return

    try {
      await addToList(token, listId, item.id)
      toast.success('Added to list')
      announceToScreenReader('Added to list')
      setListsWithItem(new Set(listsWithItem).add(listId))
      setShowListDropdown(false)
      refetchLists()
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Could not add this to your list right now. Please try again.'
      toast.error(message)
      announceToScreenReader(message)
    }
  }

  const handleCreateNewList = (): void => {
    setShowCreateListForm(true)
  }

  const handleCreateListSubmit = async (): Promise<void> => {
    if (!token || !item || !newListName.trim()) return

    setCreatingList(true)
    try {
      const newList = await createList(token, newListName.trim())
      await addToList(token, newList.id, item.id)
      toast.success(`Created "${newList.name}" and added item`)
      announceToScreenReader(`Created list ${newList.name} and added item`)
      setListsWithItem(new Set(listsWithItem).add(newList.id))
      refetchLists()
      setNewListName('')
      setShowCreateListForm(false)
      setShowListDropdown(false)
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Could not create that list right now. Please try again.'
      toast.error(message)
      announceToScreenReader(message)
    } finally {
      setCreatingList(false)
    }
  }

  const handleCancelCreateList = (): void => {
    setNewListName('')
    setShowCreateListForm(false)
  }

  return {
    // Favorites
    isFavorited,
    isLoadingFavorite,
    handleToggleFavorite,

    // Lists
    lists,
    listsWithItem,
    handleAddToList,
    handleCreateNewList,
    handleCreateListSubmit,
    handleCancelCreateList,
    showListDropdown,
    setShowListDropdown,
    showCreateListForm,
    setShowCreateListForm,
    newListName,
    setNewListName,
    creatingList,

    // Hold modal
    showHoldModal,
    setShowHoldModal,

    // Refetch
    refetchFavorites,
    refetchLists,
  }
}
