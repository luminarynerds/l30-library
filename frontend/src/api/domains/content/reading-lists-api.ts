/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from "@/lib/api-client"

export interface ReadingListSummary {
  id: number
  name: string
  description: string | null
  is_public: boolean
  created_at: string
  item_count: number
}

export interface ReadingListItem {
  id: number
  catalog_item_id: number
  catalog_item: {
    id: number
    title: string
    author: string | null
    cover_image_url: string | null
    item_type: string
  }
  added_at: string
}

export interface ReadingListWithItems extends ReadingListSummary {
  items: ReadingListItem[]
}

export async function getMyReadingLists(
  token: string,
): Promise<ReadingListSummary[]> {
  return fetchApi<ReadingListSummary[]>("/reading-lists/me", { token })
}

export async function createReadingList(
  token: string,
  name: string,
  description?: string,
): Promise<ReadingListSummary> {
  return fetchApi<ReadingListSummary>("/reading-lists/me", {
    token,
    method: "POST",
    body: { name, description },
  })
}

export async function getReadingList(
  token: string,
  listId: number,
): Promise<ReadingListWithItems> {
  return fetchApi<ReadingListWithItems>(`/reading-lists/me/${listId}`, {
    token,
  })
}

export async function updateReadingList(
  token: string,
  listId: number,
  updates: { name?: string; description?: string; is_public?: boolean },
): Promise<ReadingListSummary> {
  return fetchApi<ReadingListSummary>(`/reading-lists/me/${listId}`, {
    token,
    method: "PUT",
    body: updates,
  })
}

export async function deleteReadingList(
  token: string,
  listId: number,
): Promise<void> {
  await fetchApi(`/reading-lists/me/${listId}`, { token, method: "DELETE" })
}

export async function addItemToList(
  token: string,
  listId: number,
  catalogItemId: number,
): Promise<ReadingListItem> {
  return fetchApi<ReadingListItem>(`/reading-lists/me/${listId}/items`, {
    token,
    method: "POST",
    body: { catalog_item_id: catalogItemId },
  })
}

export async function removeItemFromList(
  token: string,
  listId: number,
  catalogItemId: number,
): Promise<void> {
  await fetchApi(`/reading-lists/me/${listId}/items/${catalogItemId}`, {
    token,
    method: "DELETE",
  })
}

export async function getListsContainingItem(
  token: string,
  catalogItemId: number,
): Promise<number[]> {
  return fetchApi<number[]>(`/reading-lists/me/containing/${catalogItemId}`, {
    token,
  })
}
