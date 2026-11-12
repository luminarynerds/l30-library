/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'
import type { CatalogItem } from '@/api/domains/catalog/catalog-api'

// ==================== Collections Types ====================

export interface Favorite {
  id: number
  catalog_item_id: number
  catalog_item: CatalogItem
  created_at: string
}

export interface ReadingList {
  id: number
  name: string
  description: string | null
  created_at: string
  item_count: number
  is_public?: boolean
  privacy_status?: string
}

export interface ListItem {
  id: number
  catalog_item_id: number
  catalog_item: CatalogItem
  added_at: string
}

export interface ReadingListWithItems extends ReadingList {
  items: ListItem[]
}

// ==================== Collections Functions ====================

// Favorites
export async function getMyFavorites(token: string): Promise<Favorite[]> {
  try {
    return await fetchApi<Favorite[]>('/favorites', { token })
  } catch {
    return []
  }
}

export async function addFavorite(token: string, catalogItemId: number): Promise<Favorite> {
  try {
    return await fetchApi<Favorite>('/favorites', {
      method: 'POST',
      token,
      body: { catalog_item_id: catalogItemId },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      // Provide specific error messages based on status code
       
      let message = error.detail || 'Failed to add favorite'

      if (error.status === 400 && message.includes('Already')) {
        message = 'This item is already in your favorites'
      } else if (error.status === 404) {
        message = 'Item not found in catalog'
      } else if (error.status >= 500) {
        message = 'Server error while adding favorite. Please try again.'
      } else if (!message || message === 'Unknown error') {
        message = 'Failed to add favorite. Please try again.'
      }

      throw new Error(message)
    }
    throw error
  }
}

export async function removeFavorite(token: string, catalogItemId: number): Promise<void> {
  try {
    await fetchApi<void>(`/favorites/${catalogItemId}`, {
      method: 'DELETE',
      token,
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
       
      let message = error.detail || 'Failed to remove favorite'

      if (error.status === 404) {
        message = 'This item is not in your favorites'
      } else if (error.status >= 500) {
        message = 'Server error while removing favorite. Please try again.'
      } else if (!message || message === 'Unknown error') {
        message = 'Failed to remove favorite. Please try again.'
      }

      throw new Error(message)
    }
    throw error
  }
}

// Reading Lists
export async function getMyLists(token: string): Promise<ReadingList[]> {
  try {
    return await fetchApi<ReadingList[]>('/lists', { token })
  } catch {
    return []
  }
}

export async function createList(token: string, name: string, description?: string): Promise<ReadingList> {
  try {
    return await fetchApi<ReadingList>('/lists', {
      method: 'POST',
      token,
      body: { name, description: description || null },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create list')
    }
    throw error
  }
}

export async function getList(token: string, listId: number): Promise<ReadingListWithItems> {
  try {
    return await fetchApi<ReadingListWithItems>(`/lists/${listId}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'List not found')
    }
    throw error
  }
}

export async function deleteList(token: string, listId: number): Promise<void> {
  try {
    await fetchApi<void>(`/lists/${listId}`, {
      method: 'DELETE',
      token,
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete list')
    }
    throw error
  }
}

export async function addToList(token: string, listId: number, catalogItemId: number): Promise<ListItem> {
  try {
    return await fetchApi<ListItem>(`/lists/${listId}/items`, {
      method: 'POST',
      token,
      body: { catalog_item_id: catalogItemId },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to add to list')
    }
    throw error
  }
}

export async function removeFromList(token: string, listId: number, catalogItemId: number): Promise<void> {
  try {
    await fetchApi<void>(`/lists/${listId}/items/${catalogItemId}`, {
      method: 'DELETE',
      token,
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to remove from list')
    }
    throw error
  }
}

// Reading List Privacy Management
export async function updateListPrivacy(
  token: string,
  listId: number,
  isPublic: boolean
): Promise<ReadingList> {
  try {
    return await fetchApi<ReadingList>(`/lists/${listId}`, {
      method: 'PATCH',
      token,
      body: { is_public: isPublic },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update list privacy')
    }
    throw error
  }
}
