/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

export type SignalType =
  | 'desk_question'
  | 'purchase_request'
  | 'agent_conversation'
  | 'staff_observation'
  | 'review_publication'
  | 'awards_list'
  | 'banned_elsewhere'
  | 'community_request'
  | 'gap_in_collection'
  | 'replacement'
  | 'other'

export type WeedingCondition =
  | 'ephemeral_2yr'
  | 'current_5yr'
  | 'foundational_indefinite'
  | 'circ_threshold'
  | 'damaged_only'
  | 'signal_persistence'
  | 'never_weed'

export type ChallengeReason =
  | 'sexual_content'
  | 'lgbtq_content'
  | 'violence'
  | 'language'
  | 'religious_viewpoint'
  | 'political_viewpoint'
  | 'age_inappropriate'
  | 'racism'
  | 'drugs_alcohol'
  | 'anti_family'
  | 'occult_supernatural'
  | 'other'

export interface AcquisitionRationale {
  id: number
  catalog_item_id: number
  created_by_id: number | null
  created_at: string
  updated_at: string

  signal_type: SignalType
  signal_ref_table: string | null
  signal_ref_id: number | null
  signal_note: string | null
  policy_clause: string | null
  primary_use_case_slug: string
  secondary_use_case_slugs: string[]
  weeding_condition: WeedingCondition
  weeding_signal_note: string | null
  anticipated_challenge_reasons: ChallengeReason[]
  anticipated_challenge_acknowledged: boolean
  patron_visible: boolean
  public_summary: string | null
}

export interface AcquisitionRationaleCreate {
  signal_type: SignalType
  signal_ref_table?: string | null
  signal_ref_id?: number | null
  signal_note?: string | null
  policy_clause?: string | null
  primary_use_case_slug: string
  secondary_use_case_slugs?: string[]
  weeding_condition: WeedingCondition
  weeding_signal_note?: string | null
  anticipated_challenge_reasons?: ChallengeReason[]
  anticipated_challenge_acknowledged?: boolean
  patron_visible?: boolean
  public_summary?: string | null
}

export interface BehaviorTag {
  slug: string
  label: string
  category: string
  description: string | null
  sort_order: number
}

export interface SignalCandidate {
  table_name: string
  record_id: number
  summary: string
  matched_on: string
}
