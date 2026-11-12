/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Parent Onboarding — Resource Guide API client.
 *
 * Pure move from parent-onboarding-api.ts; no behaviour change.
 */
import api from '@/lib/api-client';
import { API_BASE } from '@/api/types';

// ============================================================================
// Types
// ============================================================================

export interface ResourceGuideItemTranslation {
  title?: string;
  description?: string;
}

export interface ResourceGuideItem {
  id: number;
  section_id: number;
  title: string;
  description?: string;
  url?: string;
  phone?: string;
  address?: string;
  eligibility?: string;
  notes?: string;
  sort_order: number;
  /** Languages this resource is available in for real-world use. ISO
   * 639-1 lowercase codes. Surfaced here for the first time as of
   * 2026-05-25 (latent bug: backend column existed but the TS type
   * never exposed it). */
  languages?: string[];
  /** Library-curated per-language copy. Map keyed by ISO 639-1 code. */
  translations?: Record<string, ResourceGuideItemTranslation>;
  // Verification trail fields. NOTE: handwritten TS clients drift silently
  // from OpenAPI schema (feedback_l30_openapi_handwritten_drift); when
  // codegen is enabled for this surface, regenerate to refresh these.
  last_verified_at?: string | null;
  verified_by_id?: number | null;
  verified_by_name?: string | null;
  stale?: boolean;
  open_flag_count?: number;
}

export type ResourceGuideFlagReason =
  | 'disconnected_phone'
  | 'wrong_address'
  | 'eligibility_changed'
  | 'closed_permanently'
  | 'other';

export type ResourceGuideFlagStatus = 'open' | 'resolved' | 'dismissed';

export type ResourceGuideFlagResolution =
  | 'verified_current'
  | 'retired'
  | 'edited'
  | 'duplicate'
  | 'invalid';

export interface ResourceGuideFlagItemSnapshot {
  id: number;
  section_id: number;
  title: string;
  contact_info?: string | null;
  url?: string | null;
}

export interface ResourceGuideFlag {
  id: number;
  item_id: number;
  flagged_by_id?: number | null;
  flagged_by_name?: string | null;
  reason_code: ResourceGuideFlagReason;
  comment?: string | null;
  status: ResourceGuideFlagStatus;
  resolution?: ResourceGuideFlagResolution | null;
  resolution_notes?: string | null;
  resolved_by_id?: number | null;
  resolved_by_name?: string | null;
  resolved_at?: string | null;
  created_at: string;
  updated_at: string;
  item?: ResourceGuideFlagItemSnapshot | null;
}

export interface ResourceGuideSection {
  id: number;
  title: string;
  description?: string;
  icon?: string;
  sort_order: number;
  items: ResourceGuideItem[];
}

// ============================================================================
// API functions
// ============================================================================

export async function getResourceGuide(
  opts: { lang?: string } = {},
): Promise<ResourceGuideSection[]> {
  const qs = opts.lang ? `?lang=${encodeURIComponent(opts.lang)}` : '';
  return api.get(`${API_BASE}/parent-onboarding/resource-guide/sections${qs}`);
}

export async function verifyResourceGuideItem(
  itemId: number,
): Promise<ResourceGuideItem> {
  return api.post(
    `${API_BASE}/parent-onboarding/resource-guide/items/${itemId}/verify`,
    {},
  );
}

export async function flagResourceGuideItem(
  itemId: number,
  payload: { reason_code: ResourceGuideFlagReason; comment?: string },
): Promise<ResourceGuideFlag> {
  return api.post(
    `${API_BASE}/parent-onboarding/resource-guide/items/${itemId}/flags`,
    payload,
  );
}

export async function listResourceGuideFlags(
  status?: ResourceGuideFlagStatus,
): Promise<ResourceGuideFlag[]> {
  const query = status ? `?status=${status}` : '';
  return api.get(
    `${API_BASE}/parent-onboarding/resource-guide/flags${query}`,
  );
}

export async function patchResourceGuideFlag(
  flagId: number,
  payload: {
    status: ResourceGuideFlagStatus;
    resolution?: ResourceGuideFlagResolution;
    resolution_notes?: string;
  },
): Promise<ResourceGuideFlag> {
  return api.patch(
    `${API_BASE}/parent-onboarding/resource-guide/flags/${flagId}`,
    payload,
  );
}
