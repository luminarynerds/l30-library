/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchApi } from '@/lib/api-client'
import { parsePlan, type PlanAi, type SetupPlan } from '@/lib/setup-plan'
import SetupStepName from '@/components/setup/SetupStepName'
import SetupStepFeatures from '@/components/setup/SetupStepFeatures'
import SetupStepColors from '@/components/setup/SetupStepColors'
import SetupStepHero from '@/components/setup/SetupStepHero'
import SetupStepReview from '@/components/setup/SetupStepReview'
import PageContainer from '@/components/layout/PageContainer'

interface SetupConfig {
  library_name: string
  library_short_name: string
  contact_email: string
  phone: string
  address_line1: string
  address_line2: string
  admin_first_name: string
  admin_last_name: string
  admin_email: string
  admin_password: string
  feature_preset: 'barebones' | 'small_library' | 'full'
  feature_overrides: Record<string, boolean>
  primary_color: string
  accent_color: string
  hero_title: string
  hero_subtitle: string
  tagline: string
}

const INITIAL_CONFIG: SetupConfig = {
  library_name: '',
  library_short_name: '',
  contact_email: '',
  phone: '',
  address_line1: '',
  address_line2: '',
  admin_first_name: '',
  admin_last_name: '',
  admin_email: '',
  admin_password: '',
  feature_preset: 'small_library',
  feature_overrides: {},
  primary_color: '#8B5E5E',
  accent_color: '#D49898',
  hero_title: '',
  hero_subtitle: 'You belong here.',
  tagline: '',
}

const INITIAL_AI: PlanAi = { model: 'qwen2.5:0.5b', temperature: 0.7, system_prompt: '', guardrails: {} }

const STEPS = [
  { number: 1, label: 'Name' },
  { number: 2, label: 'Features' },
  { number: 3, label: 'Style' },
  { number: 4, label: 'Welcome' },
  { number: 5, label: 'Launch' },
]

export function applyPlanToConfig(config: SetupConfig, plan: SetupPlan): SetupConfig {
  return {
    ...config,
    library_name: plan.branding.library_name || config.library_name,
    library_short_name: plan.branding.library_short_name || config.library_short_name,
    contact_email: plan.branding.contact_email || config.contact_email,
    phone: plan.branding.phone || config.phone,
    address_line1: plan.branding.address_line1 || config.address_line1,
    address_line2: plan.branding.address_line2 || config.address_line2,
    primary_color: plan.branding.primary_color || config.primary_color,
    accent_color: plan.branding.accent_color || config.accent_color,
    hero_title: plan.branding.hero_title || config.hero_title,
    hero_subtitle: plan.branding.hero_subtitle || config.hero_subtitle,
    tagline: plan.branding.tagline || config.tagline,
    feature_preset: plan.features.preset,
    feature_overrides: { ...plan.features.overrides },
    // admin_* deliberately untouched — credentials are never imported from a file
  }
}

export async function buildSubmitSequence(
  config: SetupConfig,
  aiPrefs: PlanAi,
  api: typeof fetchApi,
): Promise<void> {
  // /setup/admin returns an access token for the founding admin: once an
  // admin exists, the remaining setup endpoints require admin auth.
  const created = await api<{ access_token?: string }>('/setup/admin', { method: 'POST', body: JSON.stringify({
    first_name: config.admin_first_name, last_name: config.admin_last_name,
    email: config.admin_email, password: config.admin_password }) })
  const token = created?.access_token
  await api('/setup/library-info', { method: 'POST', token, body: JSON.stringify({
    name: config.library_name, code: config.library_short_name || config.library_name.slice(0, 20),
    email: config.contact_email || null, phone: config.phone || null, address: config.address_line1 || null }) })
  await api('/setup/branding', { method: 'POST', token, body: JSON.stringify({
    primary_color: config.primary_color, accent_color: config.accent_color,
    hero_title: config.hero_title || `Welcome to ${config.library_name}`, tagline: config.tagline || null }) })
  await api('/setup/features', { method: 'POST', token, body: JSON.stringify({
    preset: config.feature_preset, overrides: config.feature_overrides }) })
  await api('/setup/ai', { method: 'POST', token, body: JSON.stringify({
    model: aiPrefs.model, temperature: aiPrefs.temperature,
    system_prompt: aiPrefs.system_prompt, guardrails: aiPrefs.guardrails }) })
  await api('/setup/complete', { method: 'POST', token })
}

export default function SetupWizardPage(): React.ReactElement {
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [config, setConfig] = useState<SetupConfig>(INITIAL_CONFIG)
  const [aiPrefs, setAiPrefs] = useState<PlanAi>(INITIAL_AI)
  const [importError, setImportError] = useState<string | null>(null)

  const handleSubmit = useCallback(async () => {
    await buildSubmitSequence(config, aiPrefs, fetchApi)
    navigate('/')
  }, [config, aiPrefs, navigate])

  return (
    <div className="min-h-screen bg-lsc-cream dark:bg-earth-900">
      {/* Progress bar */}
      <div className="bg-lsc-white dark:bg-earth-800 border-b border-lsc-border dark:border-earth-700 px-4 py-4">
        <div className="max-w-2xl mx-auto">
          <div className="flex items-center justify-between">
            {STEPS.map((s, i) => (
              <div key={s.number} className="flex items-center">
                <div className="flex flex-col items-center">
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors ${
                      step >= s.number
                        ? 'bg-lsc-rose text-white'
                        : 'bg-earth-200 dark:bg-earth-700 text-earth-600 dark:text-earth-300'
                    }`}
                  >
                    {s.number}
                  </div>
                  <span
                    className={`text-xs mt-1 hidden sm:block ${
                      step >= s.number
                        ? 'text-lsc-rose font-medium'
                        : 'text-earth-600 dark:text-earth-400'
                    }`}
                  >
                    {s.label}
                  </span>
                </div>
                {i < STEPS.length - 1 && (
                  <div
                    className={`w-8 sm:w-16 h-0.5 mx-1 sm:mx-2 ${
                      step > s.number
                        ? 'bg-lsc-rose'
                        : 'bg-earth-200 dark:bg-earth-700'
                    }`}
                  />
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Step content */}
      {step === 1 && (
        <PageContainer width="form" className="pt-6">
          <label className="block text-sm mb-4">
            Have a plan file?{' '}
            <input type="file" accept="application/json,.json" data-testid="plan-import"
              onChange={async (e) => {
                const f = e.target.files?.[0]; if (!f) return
                const res = parsePlan(await f.text())
                if (res.ok) { setConfig(applyPlanToConfig(config, res.plan)); setAiPrefs(res.plan.ai_prefs); setImportError(null) }
                else setImportError(res.reason)
              }} />
          </label>
          {importError && <p className="text-sm text-status-danger-600">{importError}</p>}
        </PageContainer>
      )}
      {step === 1 && (
        <SetupStepName
          config={config}
          onChange={setConfig}
          onNext={() => setStep(2)}
        />
      )}
      {step === 2 && (
        <SetupStepFeatures
          config={config}
          onChange={setConfig}
          onBack={() => setStep(1)}
          onNext={() => setStep(3)}
        />
      )}
      {step === 3 && (
        <SetupStepColors
          config={config}
          onChange={setConfig}
          onBack={() => setStep(2)}
          onNext={() => setStep(4)}
        />
      )}
      {step === 4 && (
        <SetupStepHero
          config={config}
          onChange={setConfig}
          onBack={() => setStep(3)}
          onNext={() => setStep(5)}
        />
      )}
      {step === 5 && (
        <SetupStepReview
          config={config}
          onBack={() => setStep(4)}
          onSubmit={handleSubmit}
        />
      )}
    </div>
  )
}
