/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { API_BASE } from '@/api/types';
import {
  MapPin, Clock, Calendar, ArrowRight, ArrowLeft,
  Check, Building2,
} from 'lucide-react'
import api from '@/lib/api-client'
import { useOnboarding } from '@/contexts/OnboardingContext'
import { patronOnboardingApi } from '@/api/domains/patron/patron-onboarding-api'
import { useTranslation} from '@/i18n'
import PageContainer from '@/components/layout/PageContainer'

interface Branch {
  id: number
  name: string
  short_name?: string
  address_line1?: string
  city?: string
  state?: string
  zip_code?: string
  phone?: string
  latitude?: number
  longitude?: number
  is_ada_accessible?: boolean
  has_meeting_rooms?: boolean
  has_makerspace?: boolean
  has_self_checkout?: boolean
}

export default function BranchPage(): React.ReactElement {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { skipWelcomeWizard } = useOnboarding()
  const [selectedBranchId, setSelectedBranchId] = useState<number | null>(null)
  const [saving, setSaving] = useState(false)

  const { data: branchesData, isLoading } = useQuery({
    queryKey: ['branches'],
    queryFn: () => api.get(`${API_BASE}/branches`) as Promise<{ data: Branch[] }>,
  })

  const branches: Branch[] = branchesData?.data ?? (Array.isArray(branchesData) ? branchesData as Branch[] : [])

  const handleContinue = async () => {
    if (!selectedBranchId) return
    setSaving(true)
    try {
      await patronOnboardingApi.setHomeBranch(selectedBranchId)
    } catch {
      // Continue even if save fails
    }
    setSaving(false)
    navigate('/onboarding/tour')
  }

  const handleSkip = async () => {
    try {
      await patronOnboardingApi.skip(3)
    } catch {
      // ignore
    }
    skipWelcomeWizard()
    navigate('/catalog')
  }

  return (
    <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark">
      <PageContainer width="form" className="py-8 space-y-8">
        {/* Header */}
        <div className="text-center space-y-2">
          <h1 className="font-serif text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
            Which branch is closest to you?
          </h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            Set your home branch for pickup locations and local events.
          </p>
        </div>

        {/* Branch list */}
        <div className="space-y-3">
          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-28 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 motion-safe:animate-pulse" />
              ))}
            </div>
          ) : branches.length === 0 ? (
            <div className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70">
              <Building2 className="w-12 h-12 mx-auto mb-3 opacity-40" />
              <p>{t('branch.noBranchesFoundYouCan')}</p>
            </div>
          ) : (
            branches.map((branch) => {
              const selected = selectedBranchId === branch.id
              return (
                <button
                  key={branch.id}
                  onClick={() => setSelectedBranchId(branch.id)}
                  className={`w-full text-left p-4 rounded-xl border-2 transition-all ${
                    selected
                      ? 'border-lsc-rose bg-lsc-rose/5 dark:bg-lsc-rose/10'
                      : 'border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 hover:border-lsc-rose/50'
                  }`}
                  aria-pressed={selected}
                >
                  <div className="flex items-start gap-3">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5 ${
                      selected ? 'bg-lsc-rose text-white' : 'bg-lsc-cream dark:bg-lsc-brown'
                    }`}>
                      {selected
                        ? <Check className="w-5 h-5" aria-hidden="true" />
                        : <MapPin className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" />
                      }
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className={`font-serif font-semibold ${selected ? 'text-lsc-rose' : 'text-lsc-dark dark:text-lsc-cream'}`}>
                        {branch.name}
                      </h3>
                      {branch.address_line1 && (
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">
                          {branch.address_line1}{branch.city ? `, ${branch.city}` : ''}{branch.state ? `, ${branch.state}` : ''} {branch.zip_code || ''}
                        </p>
                      )}
                      <div className="flex flex-wrap items-center gap-3 mt-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                        {branch.phone && (
                          <span className="flex items-center gap-1">
                            <Clock className="w-3 h-3" aria-hidden="true" />
                            {branch.phone}
                          </span>
                        )}
                        {branch.is_ada_accessible && (
                          <span className="bg-sage-100 dark:bg-sage-900 text-sage-700 dark:text-sage-300 px-1.5 py-0.5 rounded">
                            ADA Accessible
                          </span>
                        )}
                        {branch.has_makerspace && (
                          <span className="bg-earth-100 dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 px-1.5 py-0.5 rounded">
                            Makerspace
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </button>
              )
            })
          )}
        </div>

        {/* Upcoming events placeholder */}
        {selectedBranchId && (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
            <div className="flex items-center gap-2 mb-2">
              <Calendar className="w-4 h-4 text-lsc-rose" aria-hidden="true" />
              <h3 className="font-serif font-semibold text-sm text-lsc-dark dark:text-lsc-cream">
                Upcoming at this branch
              </h3>
            </div>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              Check out events and programs at your branch after setup!
            </p>
          </div>
        )}

        {/* Navigation */}
        <div className="flex items-center justify-between pt-4">
          <button
            onClick={() => navigate('/onboarding/preferences')}
            className="flex items-center gap-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose transition-colors"
          >
            <ArrowLeft className="w-4 h-4" aria-hidden="true" />
            Back
          </button>
          <div className="flex items-center gap-3">
            <button
              onClick={handleSkip}
              className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose transition-colors underline"
            >
              Skip to homepage
            </button>
            <button
              onClick={handleContinue}
              disabled={!selectedBranchId || saving}
              className="flex items-center gap-2 bg-lsc-rose hover:bg-lsc-rose/90 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-2.5 px-5 rounded-xl transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2 dark:focus:ring-offset-lsc-dark"
            >
              {saving ? 'Saving...' : 'Continue'}
              <ArrowRight className="w-4 h-4" aria-hidden="true" />
            </button>
          </div>
        </div>

        {/* Progress dots */}
        <div className="flex items-center justify-center gap-2" aria-label={t('aria.branch.step3Of5')}>
          <div className="w-2 h-2 rounded-full bg-lsc-rose/40" />
          <div className="w-2 h-2 rounded-full bg-lsc-rose/40" />
          <div className="w-2.5 h-2.5 rounded-full bg-lsc-rose" />
          <div className="w-2 h-2 rounded-full bg-lsc-dark/20 dark:bg-lsc-cream/20" />
          <div className="w-2 h-2 rounded-full bg-lsc-dark/20 dark:bg-lsc-cream/20" />
        </div>
      </PageContainer>
    </div>
  )
}