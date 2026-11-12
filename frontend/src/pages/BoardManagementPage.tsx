/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import {
  Shield,
  Users,
  Calendar,
  Vote,
  FileText,
  Archive,
  Loader2,
  ClipboardList,
  ArrowRight,
} from 'lucide-react'
import BoardMembersSection from '../components/board/BoardMembersSection'
import MeetingsSection from '../components/board/MeetingsSection'
import VotingSection from '../components/board/VotingSection'
import MinutesSection from '../components/board/MinutesSection'
import DocumentsSection from '../components/board/DocumentsSection'
import { AdminShell } from '../components/shells/AdminShell'
import { API_BASE } from '@/api/types'
import api from '@/lib/api-client'
import PageContainer from '@/components/layout/PageContainer'

interface PrepMeeting {
  id: number
  title: string
  scheduled_date: string
  meeting_type: string
  is_cancelled: boolean
}

type TabType = 'members' | 'meetings' | 'voting' | 'minutes' | 'documents' | 'prep'

export default function BoardManagementPage(): React.ReactElement {
  const { user, token } = useAuth()
  const [activeTab, setActiveTab] = useState<TabType>('members')
  const [isLoading] = useState(false)
  const [prepMeetings, setPrepMeetings] = useState<PrepMeeting[]>([])
  const [prepLoading, setPrepLoading] = useState(false)
  const [prepError, setPrepError] = useState<string | null>(null)

  useEffect(() => {
    if (activeTab !== 'prep' || !token) return

    let cancelled = false
    async function fetchUpcoming() {
      setPrepLoading(true)
      setPrepError(null)
      try {
        const data = await api.get(`${API_BASE}/board/meetings`)
        const all: PrepMeeting[] = Array.isArray(data) ? data : (data as { meetings?: PrepMeeting[] }).meetings || []
        const today = new Date().toISOString().slice(0, 10)
        const upcoming = all
          .filter((m) => !m.is_cancelled && m.scheduled_date >= today)
          .sort((a, b) => a.scheduled_date.localeCompare(b.scheduled_date))
        if (!cancelled) setPrepMeetings(upcoming)
      } catch (err) {
        if (!cancelled) setPrepError(err instanceof Error ? err.message : 'Failed to load meetings')
      } finally {
        if (!cancelled) setPrepLoading(false)
      }
    }
    fetchUpcoming()
    return () => { cancelled = true }
  }, [activeTab, token])

  // Check admin access
  if (!user || !['admin', 'super_admin', 'board_member'].includes(user.role)) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-lsc-cream via-lsc-cream to-earth-50 dark:from-earth-900 dark:via-earth-900 dark:to-lsc-dark py-20">
        <PageContainer className="text-center">
          <Shield className="w-16 h-16 text-lsc-dark/70 dark:text-lsc-cream/70 mx-auto mb-4" />
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
            Staff-Only Area
          </h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">
            Board member or admin access required
          </p>
        </PageContainer>
      </div>
    )
  }

  const tabs: Array<{
    id: TabType
    label: string
    icon: React.ComponentType<React.SVGProps<SVGSVGElement>>
  }> = [
    { id: 'members', label: 'Board Members', icon: Users },
    { id: 'meetings', label: 'Meetings', icon: Calendar },
    { id: 'voting', label: 'Voting', icon: Vote },
    { id: 'minutes', label: 'Minutes', icon: FileText },
    { id: 'documents', label: 'Documents', icon: Archive },
    { id: 'prep', label: 'Meeting Prep', icon: ClipboardList },
  ]

  return (
    <AdminShell title="Board Management">
      {/* Tabs */}
      <div className="flex flex-wrap gap-2 bg-lsc-white dark:bg-earth-800 rounded-lg p-1 shadow-sm border border-lsc-border dark:border-earth-700 mb-6">
        {tabs.map((tab) => {
          const Icon = tab.icon
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
                isActive
                  ? 'bg-lsc-rose text-white'
                  : 'text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span className="hidden sm:inline">{tab.label}</span>
            </button>
          )
        })}
      </div>

      {/* Content */}
      <div>
        {isLoading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 text-lsc-rose motion-safe:animate-spin" />
          </div>
        )}

        {!isLoading && activeTab === 'members' && (
          <BoardMembersSection token={token} userRole={user.role} />
        )}
        {!isLoading && activeTab === 'meetings' && (
          <MeetingsSection token={token} userRole={user.role} />
        )}
        {!isLoading && activeTab === 'voting' && (
          <VotingSection token={token} userRole={user.role} />
        )}
        {!isLoading && activeTab === 'minutes' && (
          <MinutesSection token={token} userRole={user.role} />
        )}
        {!isLoading && activeTab === 'documents' && (
          <DocumentsSection token={token} userRole={user.role} />
        )}
        {!isLoading && activeTab === 'prep' && (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
            <div className="flex items-center gap-3 mb-4">
              <ClipboardList className="w-6 h-6 text-lsc-rose" />
              <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">Meeting Prep Packets</h2>
            </div>

            {prepLoading && (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 text-lsc-rose motion-safe:animate-spin" />
              </div>
            )}

            {prepError && (
              <p className="text-status-danger-600 dark:text-status-danger-400 text-sm">{prepError}</p>
            )}

            {!prepLoading && !prepError && prepMeetings.length === 0 && (
              <p className="text-lsc-dark/70 dark:text-lsc-cream/60 text-sm">
                No upcoming meetings.
              </p>
            )}

            {!prepLoading && !prepError && prepMeetings.length > 0 && (
              <ul className="divide-y divide-earth-200 dark:divide-earth-700">
                {prepMeetings.map((meeting) => (
                  <li key={meeting.id}>
                    <Link
                      to={`/board/meetings/${meeting.id}/prep`}
                      className="flex items-center justify-between py-3 group hover:bg-earth-50 dark:hover:bg-earth-700/50 -mx-2 px-2 rounded-lg transition-colors"
                    >
                      <div className="min-w-0">
                        <p className="font-medium text-lsc-dark dark:text-lsc-cream truncate">
                          {meeting.title}
                        </p>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
                          {new Date(meeting.scheduled_date + 'T00:00:00').toLocaleDateString(undefined, {
                            weekday: 'short',
                            month: 'short',
                            day: 'numeric',
                            year: 'numeric',
                          })}
                          {meeting.meeting_type && (
                            <span className="ml-2 text-xs bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 px-2 py-0.5 rounded-full">
                              {meeting.meeting_type}
                            </span>
                          )}
                        </p>
                      </div>
                      <ArrowRight className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/40 group-hover:text-lsc-rose shrink-0 ml-3 transition-colors" />
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </AdminShell>
  )
}
