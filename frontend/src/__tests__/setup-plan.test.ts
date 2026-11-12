import { describe, it, expect } from 'vitest'
import { buildPlan, parsePlan, PLAN_VERSION, type SetupPlan } from '@/lib/setup-plan'

const sample: SetupPlan = {
  plan_version: PLAN_VERSION, generated_at: '2026-06-03T00:00:00.000Z',
  branding: { library_name: 'SCPL', library_short_name: 'SCPL', contact_email: '', phone: '',
    address_line1: '', address_line2: '', primary_color: '#8B5E5E', accent_color: '#D49898',
    hero_title: '', hero_subtitle: 'You belong here.', tagline: '' },
  features: { preset: 'small_library', overrides: { events_enabled: true } },
  ai_prefs: { model: 'qwen2.5:0.5b', temperature: 0.7, system_prompt: '', guardrails: {} },
  ils: { source_system: 'koha', field_mapping: { cardnumber: 'barcode' },
         options: { migrate_patrons: true, migrate_catalog: true, migrate_checkouts: false, migrate_fines: false } },
}

describe('setup-plan', () => {
  it('round-trips a plan through serialize/parse', () => {
    const json = buildPlan(sample)
    const parsed = parsePlan(json)
    expect(parsed.ok).toBe(true)
    if (parsed.ok) expect(parsed.plan.features.preset).toBe('small_library')
  })
  it('rejects a wrong version with a friendly result', () => {
    const parsed = parsePlan(JSON.stringify({ ...sample, plan_version: 999 }))
    expect(parsed.ok).toBe(false)
  })
  it('rejects non-JSON', () => {
    expect(parsePlan('not json').ok).toBe(false)
  })
})
