/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { CreateOnboardingForm } from '../components/staff/CreateOnboardingForm'
import { useAuth } from '../contexts/AuthContext'
import { useTranslation } from '../i18n/I18nContext'
import { onboardingApi } from '../api/staff-onboarding-api'
import { AdminShell } from '../components/shells'

const MANAGER_ROLES = ['admin', 'director', 'super_admin']

export default function StaffOnboardingPage(): React.ReactElement {
  const [searchParams, setSearchParams] = useSearchParams()
  const { user } = useAuth()
  const { t } = useTranslation()
  const isManager = user?.role ? MANAGER_ROLES.includes(user.role) : false
  const tab = searchParams.get('tab') || 'overview'
  const [onboardings, setOnboardings] = useState<Array<{
    id: number; user_id: number; user_name?: string;
    department: string; position: string; status?: string;
  }>>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const res = await onboardingApi.listOnboardings()
        setOnboardings(Array.isArray(res) ? res : res?.data ?? [])
      } catch {
        setOnboardings([])
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const activeClass = 'px-4 py-2 text-sm font-medium border-b-2 border-lsc-rose text-lsc-rose'
  const inactiveClass = 'px-4 py-2 text-sm font-medium border-b-2 border-transparent text-earth-600 hover:text-earth-700'

  return (
      <AdminShell title="Staff Onboarding">
    <div className="space-y-6">
      <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
        {t('staff.onboarding.title', 'Staff Onboarding')}
      </h1>
      <div className="flex gap-2 border-b border-lsc-border dark:border-earth-700">
        <button
          onClick={() => setSearchParams({ tab: 'overview' })}
          className={tab === 'overview' ? activeClass : inactiveClass}
        >
          {t('staff.onboarding.overview', 'Overview')}
        </button>
        {isManager && (
          <button
            onClick={() => setSearchParams({ tab: 'new' })}
            className={tab === 'new' ? activeClass : inactiveClass}
          >
            {t('staff.onboarding.new', 'New Onboarding')}
          </button>
        )}
      </div>
      {tab === 'overview' && (
        loading ? (
          <div className="text-earth-600">{t('common.loading', 'Loading...')}</div>
        ) : onboardings.length === 0 ? (
          <div className="text-earth-600">{t('staff.onboarding.noRecords', 'No onboarding records found.')}</div>
        ) : (
          <div className="space-y-3">
            {onboardings.map((ob) => (
              <div key={ob.id} className="p-4 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900">
                <div className="flex justify-between items-center">
                  <div>
                    <span className="font-medium text-lsc-dark dark:text-lsc-cream">{ob.user_name || `Staff #${ob.user_id}`}</span>
                    <span className="ml-2 text-sm text-earth-600">{ob.department} &middot; {ob.position}</span>
                  </div>
                  <span className="text-xs px-2 py-1 rounded-full bg-earth-100 dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70">
                    {ob.status || 'in_progress'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )
      )}
      {tab === 'new' && isManager && <CreateOnboardingForm onSuccess={() => { setSearchParams({ tab: 'overview' }); setLoading(true) }} />}
    </div>
  
      </AdminShell>
    )
}
