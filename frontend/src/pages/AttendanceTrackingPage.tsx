/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../contexts/AuthContext'
import { ClipboardCheck, BarChart3, CalendarCheck, UserCheck, TrendingUp } from 'lucide-react'
import { useTranslation} from '@/i18n'
import { DashboardTab } from '../components/attendance/DashboardTab'
import { SessionsTab } from '../components/attendance/SessionsTab'
import { CheckInTab } from '../components/attendance/CheckInTab'
import { TrendsTab } from '../components/attendance/TrendsTab'
import { CreateSessionModal } from '../components/attendance/CreateSessionModal'
import { AdminShell } from '../components/shells/AdminShell'
import PageContainer from '@/components/layout/PageContainer'

type Tab = 'dashboard' | 'sessions' | 'check-in' | 'trends'

export default function AttendanceTrackingPage() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<Tab>('dashboard')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null)

  if (!user || !['admin', 'super_admin', 'staff'].includes(user.role)) {
    return (
      <AdminShell title="Attendance Tracking">
      <PageContainer className="py-12 text-center">
        <h1 className="text-2xl font-serif font-bold text-lsc-dark/70 dark:text-lsc-cream/70">Staff-Only Area</h1>
        <p className="mt-2 text-lsc-dark/70 dark:text-lsc-cream/70">{t('attendanceTracking.staffOrAdminAccessRequired')}</p>
      </PageContainer>
      </AdminShell>
    )
  }

  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: 'dashboard', label: 'Dashboard', icon: <BarChart3 size={18} /> },
    { id: 'sessions', label: 'Sessions', icon: <CalendarCheck size={18} /> },
    { id: 'check-in', label: 'Check-In', icon: <UserCheck size={18} /> },
    { id: 'trends', label: 'Trends & ROI', icon: <TrendingUp size={18} /> },
  ]

  return (
    <AdminShell
      title="Attendance Tracking"
      subtitle="Digital sign-in for events and programs — no more paper sheets."
      icon={<ClipboardCheck size={28} />}
    >
      <div className="flex gap-1 mb-6 border-b border-lsc-border dark:border-earth-700">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.id
                ? 'border-lsc-rose text-lsc-rose dark:text-lsc-rose-light dark:border-earth-400 dark:text-lsc-rose-light'
                : 'border-transparent text-lsc-dark/70 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-lsc-dark/70'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'dashboard' && <DashboardTab />}
      {activeTab === 'sessions' && (
        <SessionsTab
          onCreateSession={() => setShowCreateModal(true)}
          onSelectSession={(id) => {
            setSelectedSessionId(id)
            setActiveTab('check-in')
          }}
        />
      )}
      {activeTab === 'check-in' && (
        <CheckInTab
          selectedSessionId={selectedSessionId}
          onSelectSession={setSelectedSessionId}
        />
      )}
      {activeTab === 'trends' && <TrendsTab />}

      {showCreateModal && (
        <CreateSessionModal
          onClose={() => setShowCreateModal(false)}
          onCreated={(session) => {
            setShowCreateModal(false)
            setSelectedSessionId(session.id)
            setActiveTab('check-in')
            queryClient.invalidateQueries({ queryKey: ['attendance-sessions'] })
            queryClient.invalidateQueries({ queryKey: ['attendance-dashboard'] })
          }}
        />
      )}
    </AdminShell>
  )
}
