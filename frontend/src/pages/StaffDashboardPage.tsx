/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { AdminShell } from '../components/shells/AdminShell'
import { Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { useTranslation } from '@/i18n'
import { useDashboardProfile } from '@/hooks/useDashboardProfile'
import DashboardOnboarding from '../components/staff/dashboard/DashboardOnboarding'
import DashboardShell from '../components/staff/dashboard/DashboardShell'
import PageContainer from '@/components/layout/PageContainer'

const SIDEBAR_FUNCTIONS = new Set(['front_desk', 'page_shelver', 'kids_services', 'marketing'])

export default function StaffDashboardPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user, isLoading: authLoading, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const { profile, isLoading: profileLoading, saveProfile, needsOnboarding } = useDashboardProfile()

  useEffect(() => { if (!authLoading && (!user || (user.role === 'patron' && !user.is_board_member))) { toast.error(t('toast.acquisitionManagement.staffAccessRequired')); navigate('/account') } }, [authLoading, isAuthenticated, user, navigate, t])

  if (authLoading || profileLoading) return <div className="flex items-center justify-center min-h-[400px]" role="status" aria-live="polite"><Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" aria-hidden="true" /><span className="sr-only">Loading dashboard...</span></div>
  if (!user || (user.role === 'patron' && !user.is_board_member)) return <></>

  if (needsOnboarding) {
    return (
      <DashboardOnboarding
        userName={user.first_name}
        onComplete={async (data) => { await saveProfile(data) }}
      />
    )
  }

  const defaultFunction = profile?.dashboard_functions?.[0]
  const useShell = defaultFunction && SIDEBAR_FUNCTIONS.has(defaultFunction)

  if (useShell) {
    return (
      <AdminShell title="Staff Dashboard" subtitle={`Welcome back, ${user.first_name}!`}>
        <DashboardShell />
      </AdminShell>
    )
  }

  return (
    <PageContainer width="wide" className="py-6 space-y-6">
      <div>
        <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">Staff Dashboard</h1>
        <p className="text-sm text-lsc-dark/60 dark:text-lsc-cream/70">Welcome back, {user.first_name}!</p>
      </div>
      <DashboardShell />
    </PageContainer>
  )
}
