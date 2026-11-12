import { describe, it, expect, vi, beforeEach } from 'vitest'

const calls: any[] = []
vi.mock('@/lib/api-client', () => ({
  fetchApi: vi.fn(async (path: string, opts?: any) => {
    calls.push({ path, opts })
    // /setup/admin returns the founding admin's access token
    return path === '/setup/admin' ? { access_token: 'founding-admin-token' } : {}
  }),
}))

import { buildSubmitSequence } from '@/pages/SetupWizardPage'

const config = {
  library_name: 'Schitt Creek PL', library_short_name: 'SCPL',
  contact_email: 'hi@scpl.test', phone: '555-0100',
  address_line1: '1 Rose St', address_line2: '',
  admin_first_name: 'Moira', admin_last_name: 'Rose',
  admin_email: 'moira@scpl.test', admin_password: 'roseapothecary',
  feature_preset: 'small_library' as const, feature_overrides: { events_enabled: true },
  primary_color: '#8B5E5E', accent_color: '#D49898',
  hero_title: '', hero_subtitle: 'You belong here.', tagline: 'A little town',
}
const aiPrefs = { model: 'qwen2.5:0.5b', temperature: 0.7, system_prompt: '', guardrails: {} }

describe('setup wizard submit sequence', () => {
  beforeEach(() => { calls.length = 0 })
  it('posts the /setup/* bootstrap sequence in order', async () => {
    const { fetchApi } = await import('@/lib/api-client')
    await buildSubmitSequence(config, aiPrefs, fetchApi as any)
    expect(calls.map(c => `${c.opts?.method ?? 'GET'} ${c.path}`)).toEqual([
      'POST /setup/admin',
      'POST /setup/library-info',
      'POST /setup/branding',
      'POST /setup/features',
      'POST /setup/ai',
      'POST /setup/complete',
    ])
    const admin = JSON.parse(calls[0].opts.body)
    expect(admin).toEqual(expect.objectContaining({ first_name: 'Moira', last_name: 'Rose', email: 'moira@scpl.test' }))
    // Every post-admin step carries the founding admin's token (the
    // endpoints are admin-gated once an admin account exists)
    for (const c of calls.slice(1)) {
      expect(c.opts.token, `${c.path} must send the founding admin token`).toBe('founding-admin-token')
    }
    const feats = JSON.parse(calls[3].opts.body)
    expect(feats).toEqual({ preset: 'small_library', overrides: { events_enabled: true } })
    const ai = JSON.parse(calls[4].opts.body)
    expect(ai).toEqual(expect.objectContaining({ model: 'qwen2.5:0.5b' }))
  })
})
