/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from '@/lib/api-client'

// Types matching backend schemas

export interface CostFactor {
  name: string
  description: string
  low_estimate: string
  high_estimate: string
  unit: string
  notes: string | null
}

export interface MaterialFormatCosts {
  format_type: string
  format_name: string
  description: string
  acquisition_cost: CostFactor
  processing_cost: CostFactor
  storage_cost: CostFactor
  maintenance_cost: CostFactor
  licensing_model: string | null
  typical_lifespan_years: number | null
  simultaneous_users: string
  environmental_notes: string | null
  advantages: string[]
  limitations: string[]
}

export interface CostComparisonCategory {
  category_name: string
  category_description: string
  formats: MaterialFormatCosts[]
}

export interface MaterialCostComparisonResponse {
  last_updated: string
  data_sources: string[]
  methodology_note: string
  categories: CostComparisonCategory[]
}

export interface CostComparisonSummary {
  format_type: string
  format_name: string
  avg_total_cost_per_circulation: string
  typical_circulations_per_copy: number
  cost_per_simultaneous_user: string
}

export async function getMaterialCosts(): Promise<MaterialCostComparisonResponse> {
  return fetchApi<MaterialCostComparisonResponse>('/material-costs')
}

export async function getCostSummary(): Promise<CostComparisonSummary[]> {
  return fetchApi<CostComparisonSummary[]>('/material-costs/summary')
}
