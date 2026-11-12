/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from "@/lib/api-client"

export type ArchivalLevel =
  | "collection"
  | "fonds"
  | "recordgrp"
  | "subgrp"
  | "series"
  | "subseries"
  | "file"
  | "item"

export interface ArchivalCollection {
  id: number
  name: string
  description: string | null
  parent_id: number | null
  position: number
  level: ArchivalLevel | null

  reference_code: string | null
  title: string | null
  date_creation: string | null
  date_accumulation: string | null
  extent: string | null
  creator: string | null

  biographical_history: string | null
  archival_history: string | null
  acquisition_source: string | null

  scope_content: string | null
  appraisal: string | null
  accruals: string | null
  arrangement: string | null

  access_conditions: string | null
  reproduction_conditions: string | null
  languages: string | null
  physical_access: string | null
  technical_access: string | null
  finding_aids: string | null

  originals_location: string | null
  copies_location: string | null
  related_materials: string | null
  publication_note: string | null

  notes: string | null

  description_rules: string | null
  description_status: string | null
  described_by: string | null
  described_at: string | null

  created_at: string | null
  updated_at: string | null
}

export interface ArchivalCollectionTreeNode extends ArchivalCollection {
  children: ArchivalCollectionTreeNode[]
  item_count: number
}

export interface ArchivalCollectionItem {
  id: number
  collection_id: number
  catalog_item_id: number
  position: number
  component_label: string | null
  note: string | null
  added_at: string | null
  catalog_item_title: string | null
  catalog_item_author: string | null
}

export type ArchivalCollectionCreate = Omit<
  ArchivalCollection,
  "id" | "created_at" | "updated_at" | "described_at"
>
export type ArchivalCollectionUpdate = Partial<ArchivalCollectionCreate>

export async function listRootCollections(): Promise<ArchivalCollection[]> {
  return fetchApi<ArchivalCollection[]>("/archival-collections")
}

export async function getCollection(id: number): Promise<ArchivalCollection> {
  return fetchApi<ArchivalCollection>(`/archival-collections/${id}`)
}

export async function getCollectionTree(
  id: number,
): Promise<ArchivalCollectionTreeNode> {
  return fetchApi<ArchivalCollectionTreeNode>(
    `/archival-collections/${id}/tree`,
  )
}

export async function createCollection(
  data: ArchivalCollectionCreate,
): Promise<ArchivalCollection> {
  return fetchApi<ArchivalCollection>("/archival-collections", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export async function updateCollection(
  id: number,
  data: ArchivalCollectionUpdate,
): Promise<ArchivalCollection> {
  return fetchApi<ArchivalCollection>(`/archival-collections/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
}

export async function deleteCollection(id: number): Promise<void> {
  await fetchApi<void>(`/archival-collections/${id}`, {
    method: "DELETE",
  })
}

export async function moveCollection(
  id: number,
  newParentId: number | null,
  position: number,
): Promise<ArchivalCollection> {
  return fetchApi<ArchivalCollection>(
    `/archival-collections/${id}/move`,
    {
      method: "POST",
      body: JSON.stringify({ new_parent_id: newParentId, position }),
    },
  )
}

export async function listCollectionItems(
  id: number,
): Promise<ArchivalCollectionItem[]> {
  return fetchApi<ArchivalCollectionItem[]>(
    `/archival-collections/${id}/items`,
  )
}

export async function addCollectionItem(
  collectionId: number,
  catalogItemId: number,
  position = 0,
  componentLabel?: string,
  note?: string,
): Promise<ArchivalCollectionItem> {
  return fetchApi<ArchivalCollectionItem>(
    `/archival-collections/${collectionId}/items`,
    {
      method: "POST",
      body: JSON.stringify({
        catalog_item_id: catalogItemId,
        position,
        component_label: componentLabel ?? null,
        note: note ?? null,
      }),
    },
  )
}

export async function removeCollectionItem(
  collectionId: number,
  linkId: number,
): Promise<void> {
  await fetchApi<void>(
    `/archival-collections/${collectionId}/items/${linkId}`,
    { method: "DELETE" },
  )
}

export function eadExportUrl(collectionId: number): string {
  return `/api/v1/archival-collections/${collectionId}/ead.xml`
}
