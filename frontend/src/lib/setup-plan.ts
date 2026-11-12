export const PLAN_VERSION = 1

export interface PlanBranding {
  library_name: string; library_short_name: string; contact_email: string; phone: string
  address_line1: string; address_line2: string; primary_color: string; accent_color: string
  hero_title: string; hero_subtitle: string; tagline: string
}
export interface PlanFeatures { preset: 'barebones' | 'small_library' | 'full'; overrides: Record<string, boolean> }
export interface PlanAi { model: string; temperature: number; system_prompt: string; guardrails: Record<string, unknown> }
export interface PlanIls {
  source_system: 'sirsi' | 'koha' | 'csv'
  field_mapping: Record<string, string>
  options: { migrate_patrons: boolean; migrate_catalog: boolean; migrate_checkouts: boolean; migrate_fines: boolean }
}
export interface SetupPlan {
  plan_version: number; generated_at: string
  branding: PlanBranding; features: PlanFeatures; ai_prefs: PlanAi; ils: PlanIls
}

export function buildPlan(plan: SetupPlan): string {
  return JSON.stringify(plan, null, 2)
}

export type ParseResult =
  | { ok: true; plan: SetupPlan }
  | { ok: false; reason: string }

export function parsePlan(text: string): ParseResult {
  let raw: any
  try { raw = JSON.parse(text) } catch { return { ok: false, reason: 'This file is not valid JSON.' } }
  if (typeof raw !== 'object' || raw === null) return { ok: false, reason: 'This file is not a plan.' }
  if (raw.plan_version !== PLAN_VERSION) {
    return { ok: false, reason: `This plan was made with a different version (v${raw.plan_version}). Expected v${PLAN_VERSION}.` }
  }
  return { ok: true, plan: raw as SetupPlan }
}
