/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Typed client for the session-resource-handouts endpoints.
 *
 * Kept separate from `parent-onboarding-api.ts` for the same reason as
 * `parent-onboarding-followups-api.ts`: that file's hand-written contract
 * has drifted from the backend (fields like `resources_provided`,
 * `coordinator_id`, `session_type` exist only on the FE side -- per
 * feedback_l30_openapi_handwritten_drift). The long-term fix is openapi-
 * typescript codegen; until then, new surface lives in isolation so any
 * drift here is auditable in one file.
 *
 * Shapes mirror the Pydantic response models in
 * `app/schemas/parent_onboarding.py` (ResourceHandoutResponse,
 * SessionHandoutResponse) exactly.
 */
import api from '@/lib/api-client'

const BASE = '/api/v1/parent-onboarding'

// ============================================================================
// Types
// ============================================================================

export type HandoutDeliveryMethod =
  | 'printed'
  | 'emailed'
  | 'linked'
  | 'given_orally'

export interface ResourceHandout {
  id: number
  slug: string
  title: string
  category: string
  language: string
  description?: string | null
  file_url: string
  file_size_bytes?: number | null
  page_count?: number | null
  preview_thumbnail_url?: string | null
  tags: string[]
  is_active: boolean
}

export interface ResourceHandoutListResponse {
  handouts: ResourceHandout[]
  total: number
}

export interface SessionHandout {
  id: number
  session_id: number
  resource_handout_id?: number | null
  community_resource_link_id?: number | null
  display_title?: string | null
  given_at: string
  given_by_id?: number | null
  given_by_name?: string | null
  given_in_language: string
  delivery_method: HandoutDeliveryMethod
  notes?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface SessionHandoutListResponse {
  handouts: SessionHandout[]
  total: number
}

export interface SessionHandoutCreateInput {
  resource_handout_id?: number
  community_resource_link_id?: number
  given_at?: string
  given_in_language: string
  delivery_method?: HandoutDeliveryMethod
  notes?: string
}

export interface PrintPacketResponse {
  packet_url?: string
  expires_at?: string
  // Set when the print-packet generator is not available yet (501).
  unavailable?: boolean
  dependent_spec?: string
}

// ============================================================================
// Catalog
// ============================================================================

export interface CatalogQuery {
  language?: string
  category?: string
  search?: string
  is_active?: boolean
  limit?: number
  offset?: number
}

export async function listResourceHandouts(
  q: CatalogQuery = {},
): Promise<ResourceHandoutListResponse> {
  const params = new URLSearchParams()
  if (q.language) params.append('language', q.language)
  if (q.category) params.append('category', q.category)
  if (q.search) params.append('search', q.search)
  if (typeof q.is_active === 'boolean') {
    params.append('is_active', String(q.is_active))
  }
  if (typeof q.limit === 'number') params.append('limit', String(q.limit))
  if (typeof q.offset === 'number') params.append('offset', String(q.offset))
  const qs = params.toString()
  const { data } = await api.get(
    `${BASE}/handouts${qs ? `?${qs}` : ''}`,
  )
  return data
}

// ============================================================================
// Session assignments
// ============================================================================

export async function listSessionHandouts(
  sessionId: number,
): Promise<SessionHandoutListResponse> {
  const { data } = await api.get(
    `${BASE}/sessions/${sessionId}/handouts`,
  )
  return data
}

export async function createSessionHandout(
  sessionId: number,
  input: SessionHandoutCreateInput,
): Promise<SessionHandout> {
  const { data } = await api.post(
    `${BASE}/sessions/${sessionId}/handouts`,
    input,
  )
  return data
}

export async function deleteSessionHandout(
  sessionId: number,
  assignmentId: number,
): Promise<void> {
  await api.delete(
    `${BASE}/sessions/${sessionId}/handouts/${assignmentId}`,
  )
}

// ============================================================================
// Print packet (501 until the cross-spec generator ships)
// ============================================================================

export async function requestPrintPacket(
  sessionId: number,
): Promise<PrintPacketResponse> {
  try {
    const { data } = await api.post(
      `${BASE}/sessions/${sessionId}/handouts/print-packet`,
    )
    return data
  } catch (err: unknown) {
    // axios shape: err.response.status / err.response.data
    const errObj = err as {
      response?: { status?: number; data?: { dependent_spec?: string } }
    }
    if (errObj?.response?.status === 501) {
      return {
        unavailable: true,
        dependent_spec: errObj.response.data?.dependent_spec,
      }
    }
    throw err
  }
}
