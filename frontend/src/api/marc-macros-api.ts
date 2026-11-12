/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from "@/lib/api-client"

export type MarcMacroVisibility = "private" | "shared"
export type MarcMacroOp = "set" | "clear" | "find_replace" | "append"

export interface MarcMacroStep {
  op: MarcMacroOp
  tag: string
  subfield: string
  value?: string | null
  find?: string | null
  replace?: string | null
}

export interface MarcMacro {
  id: number
  name: string
  description: string | null
  visibility: MarcMacroVisibility
  owner_id: number | null
  steps: MarcMacroStep[]
  created_at: string
  updated_at: string
}

export interface MarcMacroListResponse {
  items: MarcMacro[]
  total: number
}

export interface MarcMacroCreate {
  name: string
  description?: string | null
  visibility: MarcMacroVisibility
  steps: MarcMacroStep[]
}

export interface MarcMacroUpdate {
  name?: string
  description?: string | null
  visibility?: MarcMacroVisibility
  steps?: MarcMacroStep[]
}

export interface MarcMacroRunItemResult {
  catalog_item_id: number
  changed_fields: string[]
  skipped_steps: string[]
  error: string | null
}

export interface MarcMacroRunResponse {
  macro_id: number
  total: number
  succeeded: number
  failed: number
  results: MarcMacroRunItemResult[]
}

export function listMarcMacros(): Promise<MarcMacroListResponse> {
  return fetchApi<MarcMacroListResponse>("/marc-macros")
}

export function getMarcMacro(id: number): Promise<MarcMacro> {
  return fetchApi<MarcMacro>(`/marc-macros/${id}`)
}

export function createMarcMacro(data: MarcMacroCreate): Promise<MarcMacro> {
  return fetchApi<MarcMacro>("/marc-macros", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export function updateMarcMacro(id: number, data: MarcMacroUpdate): Promise<MarcMacro> {
  return fetchApi<MarcMacro>(`/marc-macros/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
}

export function deleteMarcMacro(id: number): Promise<void> {
  return fetchApi<void>(`/marc-macros/${id}`, { method: "DELETE" })
}

export function runMarcMacro(
  id: number,
  catalogItemIds: number[],
): Promise<MarcMacroRunResponse> {
  return fetchApi<MarcMacroRunResponse>(`/marc-macros/${id}/run`, {
    method: "POST",
    body: JSON.stringify({ catalog_item_ids: catalogItemIds }),
  })
}

export function getMarcMacroTargets(): Promise<Record<string, string>> {
  return fetchApi<Record<string, string>>("/marc-macros/targets")
}
