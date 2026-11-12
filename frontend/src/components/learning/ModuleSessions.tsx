/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * ModuleSessions - Shows scheduled sessions for a module with RSVP
 */
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Calendar, MapPin, Clock, Users, Package, Check, Plus } from 'lucide-react'
import { getModuleSessions, rsvpToSession, type ModuleSession } from '@/api/domains/learning/sessions-api'
import { useAuth } from '../../contexts/AuthContext'
import toast from 'react-hot-toast'
import { getCurrentLocale } from '@/i18n'

interface ModuleSessionsProps {
  moduleId: number
  moduleTitle: string
}

// Staff-ish roles that can schedule sessions. Everyone except patron/child
// sees the empty-state "Schedule one" CTA; patrons see nothing (status quo).
function viewerCanScheduleSessions(role: string | undefined): boolean {
  return !!role && role !== 'patron' && role !== 'child'
}

export function ModuleSessions({ moduleId, moduleTitle }: ModuleSessionsProps) {
  const { user } = useAuth()
  const [sessions, setSessions] = useState<ModuleSession[]>([])
  const [loading, setLoading] = useState(true)
  const [rsvpLoading, setRsvpLoading] = useState<number | null>(null)

  useEffect(() => {
    getModuleSessions(moduleId)
      .then(setSessions)
      .catch(() => {/* no sessions is fine */})
      .finally(() => setLoading(false))
  }, [moduleId])

  if (loading) return null

  // Empty state: patrons see nothing (preserves existing behavior); staff
  // see a quiet "Schedule one" link so this module surface is discoverable
  // from CourseDetailPage instead of being silently invisible.
  if (sessions.length === 0) {
    if (!viewerCanScheduleSessions(user?.role)) return null
    return (
      <div className="border-t border-lsc-border dark:border-earth-700 px-6 py-3">
        <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 flex items-center gap-2">
          <Calendar aria-hidden="true" className="w-3.5 h-3.5" />
          <span>No live sessions scheduled.</span>
          <Link
            to="/staff/admin/sessions"
            className="inline-flex items-center gap-1 text-lsc-rose hover:underline focus:outline-none focus:ring-2 focus:ring-lsc-rose rounded"
          >
            <Plus aria-hidden="true" className="w-3 h-3" />
            Schedule one
          </Link>
        </p>
      </div>
    )
  }

  const handleRsvp = async (sessionId: number, status: string) => {
    setRsvpLoading(sessionId)
    try {
      await rsvpToSession(sessionId, status)
      // Refresh sessions to get updated counts
      const updated = await getModuleSessions(moduleId)
      setSessions(updated)
      toast.success(status === 'attending' ? 'RSVP confirmed!' : 'RSVP updated')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'RSVP failed')
    } finally {
      setRsvpLoading(null)
    }
  }

  return (
    <div className="border-t border-lsc-border dark:border-earth-700 px-6 py-4">
      <h4 className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-3 flex items-center gap-2">
        <Calendar aria-hidden="true" className="w-4 h-4" />
        Scheduled Sessions
      </h4>
      <div className="space-y-3" role="region" aria-label="Scheduled sessions">
        {sessions.map(session => {
          const date = new Date(session.scheduled_at)
          const isPast = date < new Date()

          return (
            <div
              key={session.id}
              className={`p-3 rounded-xl border ${isPast ? 'border-earth-200 dark:border-earth-700 opacity-60' : 'border-lsc-rose/20 dark:border-lsc-rose/10 bg-lsc-rose/5 dark:bg-lsc-rose/5'}`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm text-lsc-dark dark:text-lsc-cream">
                    {session.title || moduleTitle}{isPast && <span className="sr-only"> (past session)</span>}
                  </p>
                  <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
                    <span className="flex items-center gap-1">
                      <Calendar aria-hidden="true" className="w-3 h-3" />
                      {date.toLocaleDateString(getCurrentLocale(), { weekday: 'short', month: 'short', day: 'numeric' })} at {date.toLocaleTimeString(getCurrentLocale(), { hour: 'numeric', minute: '2-digit' })}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock aria-hidden="true" className="w-3 h-3" />
                      {session.duration_minutes} min
                    </span>
                    {session.location && (
                      <span className="flex items-center gap-1">
                        <MapPin aria-hidden="true" className="w-3 h-3" />
                        {session.location}
                      </span>
                    )}
                    {session.max_participants && (
                      <span className="flex items-center gap-1">
                        <Users aria-hidden="true" className="w-3 h-3" />
                        {session.rsvp_count}/{session.max_participants} spots
                      </span>
                    )}
                  </div>
                  {session.materials && session.materials.length > 0 && (
                    <div className="flex items-center gap-1 mt-1.5 text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
                      <Package aria-hidden="true" className="w-3 h-3" />
                      Materials: {session.materials.join(', ')}
                    </div>
                  )}
                </div>
                {!isPast && (
                  <button
                    onClick={() => handleRsvp(session.id, 'attending')}
                    disabled={rsvpLoading === session.id}
                    className="flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg transition-colors disabled:opacity-50"
                  >
                    <Check aria-hidden="true" className="w-3 h-3" />
                    {rsvpLoading === session.id ? 'Saving...' : 'RSVP'}
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
