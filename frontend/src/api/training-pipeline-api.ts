/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { apiClient } from '@/lib/api-client'

const PREFIX = '/knowledge-pipeline'

// ── Types ───────────────────────────────────────────────

export interface TrainingStats {
  total_examples: number
  pending_review: number
  average_quality_score: number
  by_persona: Record<string, { approved: number; review: number; rejected: number; total: number }>
  by_source: Record<string, number>
}

export interface PipelineStats {
  total_entries: number
  by_source: Record<string, number>
  by_status: Record<string, number>
  by_domain: Record<string, number>
}

export interface TrainingExample {
  id: number
  knowledge_entry_id: number
  persona_domain: string | null
  instruction: string
  response: string
  source_type: string
  quality_score: number
  quality_breakdown: Record<string, number> | null
  bucket: string
  is_multi_turn: boolean
  created_at: string
  reviewed_at: string | null
  reviewed_by_name: string | null
  staff_override: boolean
  override_reason: string | null
}

export interface ReadinessResult {
  persona_domain: string
  approved_count: number
  review_count: number
  threshold: number
  progress_pct: number
  ready: boolean
  source_diversity: {
    compliant: boolean
    total: number
    breakdown: Record<string, { count: number; percentage: number }>
    violations: string[]
  }
}

export interface RetentionStats {
  total_entries: number
  patron_interaction_entries: number
  oldest_patron_entry: string | null
  expired_entries: number
  retention_months: number
}

// ── API calls ───────────────────────────────────────────

export async function getTrainingStats(): Promise<TrainingStats> {
  return apiClient(`${PREFIX}/training/stats`)
}

export async function getPipelineStats(): Promise<PipelineStats> {
  return apiClient(`${PREFIX}/stats`)
}

export async function getReviewQueue(page = 1, pageSize = 20, personaDomain?: string): Promise<TrainingExample[]> {
  return apiClient(`${PREFIX}/training/review-queue`, {
    params: { page, page_size: pageSize, ...(personaDomain ? { persona_domain: personaDomain } : {}) },
  })
}

export async function approveExample(id: number): Promise<{ id: number; bucket: string }> {
  return apiClient(`${PREFIX}/training/${id}/approve`, { method: 'POST' })
}

export async function rejectExample(id: number): Promise<{ id: number; bucket: string }> {
  return apiClient(`${PREFIX}/training/${id}/reject`, { method: 'POST' })
}

export async function overrideExample(id: number, bucket: string, reason: string): Promise<{ id: number; bucket: string; overridden: boolean }> {
  return apiClient(`${PREFIX}/training/${id}/override`, { method: 'POST', body: { bucket, reason } })
}

export async function getReadiness(personaDomain: string): Promise<ReadinessResult> {
  return apiClient(`${PREFIX}/training/readiness/${personaDomain}`)
}

export async function getRetentionStats(): Promise<RetentionStats> {
  return apiClient(`${PREFIX}/admin/retention-stats`)
}

export async function triggerBatchProcessing(personaDomain?: string, limit = 100): Promise<{ status: string }> {
  return apiClient(`${PREFIX}/training/process-batch`, {
    method: 'POST',
    params: { ...(personaDomain ? { persona_domain: personaDomain } : {}), limit },
  })
}

export async function triggerRetentionCleanup(): Promise<{ status: string }> {
  return apiClient(`${PREFIX}/admin/run-retention`, { method: 'POST' })
}

export async function exportTrainingData(personaDomain: string, minScore = 80): Promise<{ persona_domain: string; example_count: number; jsonl: string }> {
  return apiClient(`${PREFIX}/training/export`, {
    params: { persona_domain: personaDomain, min_score: minScore },
  })
}

export async function adminPurge(purgeType: string, opts: { startDate?: string; endDate?: string; sourceType?: string; patronId?: number }): Promise<{ purged_count: number }> {
  return apiClient(`${PREFIX}/admin/purge`, {
    method: 'POST',
    body: {
      purge_type: purgeType,
      start_date: opts.startDate,
      end_date: opts.endDate,
      source_type: opts.sourceType,
      patron_id: opts.patronId,
    },
  })
}
