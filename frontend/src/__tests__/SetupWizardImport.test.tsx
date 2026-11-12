import { describe, it, expect } from 'vitest'
import { applyPlanToConfig } from '@/pages/SetupWizardPage'
import { PLAN_VERSION } from '@/lib/setup-plan'

const base = {
  library_name: '', library_short_name: '', contact_email: '', phone: '',
  address_line1: '', address_line2: '', admin_first_name: '', admin_last_name: '',
  admin_email: '', admin_password: '',
  feature_preset: 'small_library' as const, feature_overrides: {},
  primary_color: '#8B5E5E', accent_color: '#D49898',
  hero_title: '', hero_subtitle: 'You belong here.', tagline: '',
}

describe('applyPlanToConfig', () => {
  it('merges a plan into setup config without touching admin credentials', () => {
    const plan = {
      plan_version: PLAN_VERSION, generated_at: 'x',
      branding: { ...base, library_name: 'SCPL' },
      features: { preset: 'full' as const, overrides: { events_enabled: true } },
      ai_prefs: { model: 'x', temperature: 0.5, system_prompt: '', guardrails: {} },
      ils: { source_system: 'koha' as const, field_mapping: {}, options: { migrate_patrons: true, migrate_catalog: true, migrate_checkouts: false, migrate_fines: false } },
    }
    const next = applyPlanToConfig(base, plan as any)
    expect(next.library_name).toBe('SCPL')
    expect(next.feature_preset).toBe('full')
    expect(next.admin_email).toBe('')
    expect(next.admin_password).toBe('')
  })
})
