/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from "@/lib/api-client"

export interface EventProgramPartner {
  id: number
  name: string
  slug: string
  website: string | null
  contact_email: string | null
  contact_phone: string | null
  notes: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface EventProgramPartnerCreate {
  name: string
  website?: string | null
  contact_email?: string | null
  contact_phone?: string | null
  notes?: string | null
  is_active?: boolean
}

export interface EventProgramPartnerUpdate {
  name?: string
  website?: string | null
  contact_email?: string | null
  contact_phone?: string | null
  notes?: string | null
  is_active?: boolean
}

export interface EventProgramPartnerListResult {
  data: EventProgramPartner[]
  pagination: {
    page: number
    per_page: number
    total: number
    total_pages: number
    has_next: boolean
    has_previous: boolean
  }
}

export interface ListProgramPartnersFilters {
  search?: string | undefined
  include_inactive?: boolean | undefined
  page?: number | undefined
  per_page?: number | undefined
}

export async function listProgramPartners(
  filters: ListProgramPartnersFilters = {},
  token?: string,
): Promise<EventProgramPartnerListResult> {
  const params = new URLSearchParams()
  if (filters.search) params.set("search", filters.search)
  if (filters.include_inactive) params.set("include_inactive", "true")
  if (filters.page) params.set("page", String(filters.page))
  // Backend PaginationParams expects `page_size`, not `per_page`.
  if (filters.per_page) params.set("page_size", String(filters.per_page))

  const qs = params.toString()
  try {
    return await fetchApi<EventProgramPartnerListResult>(
      `/program-partners${qs ? `?${qs}` : ""}`,
      token ? { token } : undefined,
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || "Failed to list program partners")
    }
    throw error
  }
}

export async function getProgramPartner(
  id: number,
  token?: string,
): Promise<EventProgramPartner> {
  try {
    return await fetchApi<EventProgramPartner>(
      `/program-partners/${id}`,
      token ? { token } : undefined,
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || "Failed to load program partner")
    }
    throw error
  }
}

export async function createProgramPartner(
  token: string,
  payload: EventProgramPartnerCreate,
): Promise<EventProgramPartner> {
  try {
    return await fetchApi<EventProgramPartner>("/program-partners", {
      method: "POST",
      token,
      body: payload,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || "Failed to create program partner")
    }
    throw error
  }
}

export async function updateProgramPartner(
  token: string,
  id: number,
  payload: EventProgramPartnerUpdate,
): Promise<EventProgramPartner> {
  try {
    return await fetchApi<EventProgramPartner>(`/program-partners/${id}`, {
      method: "PATCH",
      token,
      body: payload,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || "Failed to update program partner")
    }
    throw error
  }
}

export async function deleteProgramPartner(
  token: string,
  id: number,
  force = false,
): Promise<void> {
  try {
    await fetchApi<void>(
      `/program-partners/${id}${force ? "?force=true" : ""}`,
      {
        method: "DELETE",
        token,
        skipJsonParse: true,
      },
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || "Failed to delete program partner")
    }
    throw error
  }
}
