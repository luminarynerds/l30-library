/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { CalendarCheck, Plus, ArrowRight, Loader2 } from 'lucide-react'
import { listAttendanceSessions } from '../../api/attendance-api'
import { useTranslation } from '@/i18n'
import { clean } from '@/lib/utils'
import { StatusBadge } from './StatusBadge'

interface SessionsTabProps {
  onCreateSession: () => void
  onSelectSession: (id: number) => void
}

export function SessionsTab({
  onCreateSession,
  onSelectSession,
}: SessionsTabProps) {
  const { t } = useTranslation()
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState<string>('')

  const { data, isLoading } = useQuery({
    queryKey: ['attendance-sessions', page, statusFilter],
    queryFn: () => listAttendanceSessions(clean({ page, per_page: 20, status: statusFilter || undefined })),
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}
            className="text-sm border border-lsc-border dark:border-earth-600 rounded-lg px-3 py-2 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
          >
            <option value="">All Statuses</option>
            <option value="open">Open</option>
            <option value="closed">Closed</option>
            <option value="finalized">Finalized</option>
          </select>
        </div>
        <button
          onClick={onCreateSession}
          className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 text-sm font-medium"
        >
          <Plus size={16} /> New Session
        </button>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-8">
          <Loader2 className="motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" size={24} />
        </div>
      ) : data?.data && data.data.length > 0 ? (
        <>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-lsc-dark/70 dark:text-lsc-cream/70 bg-lsc-cream dark:bg-earth-900 border-b dark:border-earth-700">
                  <th className="py-3 px-4">Session</th>
                  <th className="py-3 px-4">Date</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Mode</th>
                  <th className="py-3 px-4 text-right">Attendance</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.data.map((session) => (
                  <tr
                    key={session.id}
                    className="border-b dark:border-earth-700 last:border-0 hover:bg-lsc-cream dark:hover:bg-earth-750"
                  >
                    <td className="py-3 px-4 font-medium text-lsc-dark dark:text-lsc-cream">
                      {session.session_name}
                    </td>
                    <td className="py-3 px-4 text-lsc-dark/70 dark:text-lsc-cream/70">{session.session_date}</td>
                    <td className="py-3 px-4"><StatusBadge status={session.status} /></td>
                    <td className="py-3 px-4 text-lsc-dark/70 dark:text-lsc-cream/70">
                      {session.head_count_mode ? 'Head Count' : 'Individual'}
                    </td>
                    <td className="py-3 px-4 text-right font-medium text-lsc-dark dark:text-lsc-cream">
                      {session.effective_total}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => onSelectSession(session.id)}
                        className="text-lsc-rose dark:text-lsc-rose-light hover:text-lsc-rose dark:text-lsc-rose-light text-sm font-medium"
                      >
                        {session.status === 'open' ? 'Check In' : 'View'}
                        <ArrowRight size={14} className="inline ml-1" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {data.pagination.total_pages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={!data.pagination.has_previous}
                className="px-3 py-1 text-sm border rounded disabled:opacity-50"
              >
                Previous
              </button>
              <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                Page {data.pagination.page} of {data.pagination.total_pages}
              </span>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={!data.pagination.has_next}
                className="px-3 py-1 text-sm border rounded disabled:opacity-50"
              >
                Next
              </button>
            </div>
          )}
        </>
      ) : (
        <div className="text-center py-12 bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700">
          <CalendarCheck size={40} className="mx-auto text-earth-600 dark:text-earth-600 mb-3" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('attendanceTracking.noAttendanceSessionsYet')}</p>
          <button
            onClick={onCreateSession}
            className="mt-3 text-lsc-rose dark:text-lsc-rose-light hover:text-lsc-rose text-sm font-medium"
          >
            Create your first session
          </button>
        </div>
      )}
    </div>
  )
}
