/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { api, isApiError } from '@/lib/api-client'
import type {
  AcquisitionRationale,
  AcquisitionRationaleCreate,
  BehaviorTag,
  SignalCandidate,
} from '@/types/acquisitionRationale'

// Backend mounts the rationale router under /api/v1/staff. The shared api-client
// already prefixes /api/v1, so paths here are relative to /staff.
const BASE = '/staff'

interface BehaviorTagsResponse {
  tags: BehaviorTag[]
}

interface SignalCandidatesResponse {
  candidates: SignalCandidate[]
}

interface MissingRationaleResponse {
  catalog_item_ids: number[]
  count: number
}

export async function getRationale(
  catalogItemId: number,
): Promise<AcquisitionRationale | null> {
  try {
    return await api.get<AcquisitionRationale>(
      `${BASE}/catalog-items/${catalogItemId}/acquisition-rationale`,
    )
  } catch (error: unknown) {
    if (isApiError(error) && error.status === 404) return null
    throw error
  }
}

export async function createRationale(
  catalogItemId: number,
  data: AcquisitionRationaleCreate,
): Promise<AcquisitionRationale> {
  return api.post<AcquisitionRationale>(
    `${BASE}/catalog-items/${catalogItemId}/acquisition-rationale`,
    data,
  )
}

export async function updateRationale(
  catalogItemId: number,
  data: AcquisitionRationaleCreate,
): Promise<AcquisitionRationale> {
  return api.put<AcquisitionRationale>(
    `${BASE}/catalog-items/${catalogItemId}/acquisition-rationale`,
    data,
  )
}

export async function listBehaviorTags(): Promise<BehaviorTag[]> {
  const body = await api.get<BehaviorTagsResponse>(`${BASE}/behavior-tags`)
  return body.tags
}

export async function listSignalCandidates(
  catalogItemId: number,
): Promise<SignalCandidate[]> {
  const body = await api.get<SignalCandidatesResponse>(
    `${BASE}/catalog-items/${catalogItemId}/signal-candidates`,
  )
  return body.candidates
}

export async function listMissingRationale(limit = 50): Promise<number[]> {
  const body = await api.get<MissingRationaleResponse>(
    `${BASE}/catalog-items/missing-rationale`,
    { params: { limit } },
  )
  return body.catalog_item_ids
}

export interface SimilarRationaleHit {
  aku_id?: string
  title?: string
  body?: string
  tags?: string[]
  score?: number
  // Server may include additional fields; treat as open shape.
  [key: string]: unknown
}

interface SimilarRationalesResponse {
  hits: SimilarRationaleHit[]
  query: string
}

export async function findSimilarRationales(
  query: string,
  limit = 5,
): Promise<SimilarRationalesResponse> {
  return api.get<SimilarRationalesResponse>(
    `${BASE}/acquisition-rationale/similar`,
    { params: { query, limit } },
  )
}
