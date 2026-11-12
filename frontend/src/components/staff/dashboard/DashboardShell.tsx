/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, Suspense, useCallback } from 'react'
import { BookOpen, Clock } from 'lucide-react'
import { ToneProvider } from '@/contexts/ToneContext'
import { useDashboardProfile } from '@/hooks/useDashboardProfile'
import { updateDashboardProfile, DashboardFunction, DashboardTone } from '@/api/staff-api/dashboard-profile'
import { useAuth } from '@/contexts/AuthContext'
import RoleSwitcher from './RoleSwitcher'
import DashboardSettings from './DashboardSettings'
import StaffMessages from './panels/StaffMessages'
import MyCourses from './panels/MyCourses'
import TodayCard from './panels/TodayCard'
import MyShiftsTile from './MyShiftsTile'
import { lazyWithRetry } from '../../../utils/lazyWithRetry'
import { getCurrentLocale } from '@/i18n'

const FrontDeskDashboard = lazyWithRetry(() => import('./dashboards/FrontDeskDashboard'), 'staff-dashboard-front-desk-dashboard')
const BoardOpsDashboard = lazyWithRetry(() => import('./dashboards/BoardOpsDashboard'), 'staff-dashboard-board-ops-dashboard')
const BoardPresidentDashboard = lazyWithRetry(() => import('./dashboards/BoardPresidentDashboard'), 'staff-dashboard-board-president-dashboard')
const ShelverDashboard = lazyWithRetry(() => import('./dashboards/ShelverDashboard'), 'staff-dashboard-shelver-dashboard')
const MarketingDashboard = lazyWithRetry(() => import('./dashboards/MarketingDashboard'), 'staff-dashboard-marketing-dashboard')
const KidsDashboard = lazyWithRetry(() => import('./dashboards/KidsDashboard'), 'staff-dashboard-kids-dashboard')

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const DASHBOARD_COMPONENTS: Record<DashboardFunction, React.LazyExoticComponent<React.ComponentType<any>>> = {
  front_desk: FrontDeskDashboard,
  board_ops: BoardOpsDashboard,
  board_president: BoardPresidentDashboard,
  kids_services: KidsDashboard,
  marketing: MarketingDashboard,
  page_shelver: ShelverDashboard,
}

const TIME_SENSITIVE_ROLES: DashboardFunction[] = ['front_desk', 'page_shelver']
const SHIFT_BOUNDARIES_MIN = [13 * 60, 17 * 60, 20 * 60]
const SUNSET_LEAD_MIN = 30
const LIBRARY_TIMEZONE = 'America/New_York'

const VIBE_CLASS: Record<DashboardFunction, string> = {
  board_president: 'vibe-formal',
  board_ops: 'vibe-formal',
  kids_services: 'vibe-playful',
  page_shelver: 'vibe-utility',
  marketing: 'vibe-creative',
  front_desk: '',
}

function useShiftSunset(role: DashboardFunction): number {
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    if (!TIME_SENSITIVE_ROLES.includes(role)) {
      setProgress(0)
      return
    }

    const check = () => {
      const now = new Date(
        new Date().toLocaleString(getCurrentLocale(), { timeZone: LIBRARY_TIMEZONE }),
      )
      const timeInMin = now.getHours() * 60 + now.getMinutes()

      for (const boundary of SHIFT_BOUNDARIES_MIN) {
        const until = boundary - timeInMin
        if (until > 0 && until <= SUNSET_LEAD_MIN) {
          setProgress(1 - until / SUNSET_LEAD_MIN)
          return
        }
      }
      setProgress(0)
    }

    check()
    const id = setInterval(check, 60_000)
    return () => clearInterval(id)
  }, [role])

  return progress
}

function DashboardSpinner() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] gap-3" role="status" aria-live="polite">
      <BookOpen className="w-8 h-8 text-lsc-rose dark:text-lsc-rose-light motion-safe:animate-breathe" aria-hidden="true" />
      <span className="text-sm text-earth-600 dark:text-earth-400">Loading dashboard...</span>
    </div>
  )
}

function DashboardSkeleton({ role }: { role?: string }) {
  const pulse = 'motion-safe:animate-pulse bg-earth-200 dark:bg-earth-700 rounded-xl'

  if (role === 'front_desk') {
    return (
      <div className="min-h-[400px] space-y-4" role="status" aria-live="polite">
        <div className={`${pulse} h-12 w-full`} />
        <div className="grid grid-cols-2 gap-4">
          <div className={`${pulse} h-32 col-span-2`} />
          <div className={`${pulse} h-24`} />
          <div className={`${pulse} h-24`} />
        </div>
        <span className="sr-only">Loading dashboard...</span>
      </div>
    )
  }

  if (role === 'page_shelver') {
    return (
      <div className="min-h-[400px] space-y-4" role="status" aria-live="polite">
        <div className={`${pulse} h-16 w-full`} />
        <div className="space-y-2">
          {[...Array(6)].map((_, i) => (
            <div key={i} className={`${pulse} h-10 w-full`} />
          ))}
        </div>
        <span className="sr-only">Loading dashboard...</span>
      </div>
    )
  }

  if (role === 'board_president' || role === 'board_ops') {
    return (
      <div className="min-h-[400px] space-y-4" role="status" aria-live="polite">
        <div className={`${pulse} h-20 w-full`} />
        <div className="grid grid-cols-3 gap-4">
          <div className={`${pulse} h-32`} />
          <div className={`${pulse} h-32`} />
          <div className={`${pulse} h-32`} />
        </div>
        <span className="sr-only">Loading dashboard...</span>
      </div>
    )
  }

  if (role === 'kids_services') {
    return (
      <div className="min-h-[400px] space-y-6" role="status" aria-live="polite">
        <div className={`${pulse} h-24 w-full rounded-xl`} />
        <div className="grid grid-cols-2 gap-6">
          <div className={`${pulse} h-40 rounded-xl`} />
          <div className={`${pulse} h-40 rounded-xl`} />
        </div>
        <span className="sr-only">Loading dashboard...</span>
      </div>
    )
  }

  return (
    <div className="min-h-[400px] space-y-4" role="status" aria-live="polite">
      <div className={`${pulse} h-16 w-full`} />
      <div className="grid grid-cols-2 gap-4">
        <div className={`${pulse} h-28`} />
        <div className={`${pulse} h-28`} />
      </div>
      <span className="sr-only">Loading dashboard...</span>
    </div>
  )
}

export default function DashboardShell() {
  const { token } = useAuth()
  const { profile, isLoading, saveProfile } = useDashboardProfile()
  const [activeFunction, setActiveFunction] = useState<DashboardFunction | null>(null)

  const functions = profile?.dashboard_functions ?? []
  const currentFunction = activeFunction ?? functions[0] ?? 'front_desk'
  const ActiveDashboard = DASHBOARD_COMPONENTS[currentFunction]
  const sunsetProgress = useShiftSunset(currentFunction)
  const currentVibe = VIBE_CLASS[currentFunction] ?? ''

  const handleToneChange = useCallback(async (tone: DashboardTone) => {
    if (!token || !functions.length) return
    await updateDashboardProfile(token, {
      dashboard_functions: functions,
      dashboard_tone: tone,
    })
  }, [token, functions])

  const handleSettingsSave = useCallback(async (newFunctions: DashboardFunction[], newTone: DashboardTone) => {
    await saveProfile({ dashboard_functions: newFunctions, dashboard_tone: newTone })
    if (!newFunctions.includes(currentFunction)) {
      setActiveFunction(newFunctions[0] ?? null)
    }
  }, [saveProfile, currentFunction])

  if (isLoading) return <DashboardSpinner />

  return (
    <ToneProvider initialTone={profile?.dashboard_tone ?? 'standard'} onToneChange={handleToneChange}>
      <div className="relative flex gap-4">
        {sunsetProgress > 0 && (
          <div
            className="fixed inset-0 pointer-events-none z-10 transition-opacity duration-[60000ms]"
            style={{
              background: `linear-gradient(180deg, transparent 0%, rgba(42, 37, 48, ${sunsetProgress * 0.08}) 100%)`,
            }}
            aria-hidden="true"
          />
        )}
        <RoleSwitcher
          functions={functions}
          active={currentFunction}
          onSwitch={setActiveFunction}
        />
        <div className={`flex-1 min-w-0 space-y-4 ${currentVibe}`}>
          <div className="flex items-center justify-end">
            <DashboardSettings
              currentFunctions={functions}
              currentTone={profile?.dashboard_tone ?? 'standard'}
              onSave={handleSettingsSave}
            />
          </div>
          <div className="flex gap-6">
            <div className="flex-1 min-w-0">
              <Suspense fallback={<DashboardSkeleton role={currentFunction} />}>
                <ActiveDashboard />
              </Suspense>
            </div>
            <aside className="hidden lg:block w-80 shrink-0 space-y-4">
              <TodayCard />
              {currentFunction !== 'front_desk' && (
                <>
                  <h3 className="text-sm font-semibold text-earth-600 dark:text-earth-400 uppercase tracking-wider px-1">Personal</h3>
                  <div>
                    <p className="text-xs font-medium text-lsc-dark/60 dark:text-lsc-cream/60 flex items-center gap-1.5 mb-2">
                      <Clock className="w-3.5 h-3.5" aria-hidden="true" />
                      My shifts
                    </p>
                    <MyShiftsTile />
                  </div>
                  <StaffMessages />
                  <MyCourses />
                </>
              )}
            </aside>
          </div>
        </div>
      </div>
    </ToneProvider>
  )
}
