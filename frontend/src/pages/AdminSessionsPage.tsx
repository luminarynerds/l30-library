/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Admin Sessions Page - Manage scheduled sessions for course modules
 */
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Calendar, MapPin, Clock, Users, Plus, Trash2, ArrowLeft } from 'lucide-react'
import { getModuleSessions, createModuleSession, cancelModuleSession, type ModuleSession } from '@/api/domains/learning/sessions-api'
import { getAllCoursesAdmin, getCourse } from '@/api/domains/learning/courses-api'
import toast from 'react-hot-toast'
import { AdminShell } from '../components/shells/AdminShell'
import { getCurrentLocale } from '@/i18n'

interface CourseInfo { id: number; title: string; modules: { id: number; title: string }[] }

export default function AdminSessionsPage() {
  const navigate = useNavigate()
  const [courses, setCourses] = useState<{ id: number; title: string }[]>([])
  const [selectedCourse, setSelectedCourse] = useState<CourseInfo | null>(null)
  const [sessions, setSessions] = useState<Record<number, ModuleSession[]>>({})
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState<number | null>(null) // module_id

  // Form state
  const [formDate, setFormDate] = useState('')
  const [formTime, setFormTime] = useState('10:00')
  const [formDuration, setFormDuration] = useState(120)
  const [formLocation, setFormLocation] = useState('')
  const [formMaxParticipants, setFormMaxParticipants] = useState(20)
  const [formMaterials, setFormMaterials] = useState('')
  const [formNotes, setFormNotes] = useState('')

  useEffect(() => {
    getAllCoursesAdmin()
      .then(setCourses)
      .catch(() => toast.error('Failed to load courses'))
      .finally(() => setLoading(false))
  }, [])

  const loadCourse = async (courseId: number) => {
    try {
      const course = await getCourse(courseId)
      setSelectedCourse(course as unknown as CourseInfo)
      // Load sessions for each module
      const sessionsMap: Record<number, ModuleSession[]> = {}
      for (const mod of course.modules) {
        try {
          sessionsMap[mod.id] = await getModuleSessions(mod.id)
        } catch {
          sessionsMap[mod.id] = []
        }
      }
      setSessions(sessionsMap)
    } catch {
      toast.error('Failed to load course')
    }
  }

  const handleCreate = async (moduleId: number) => {
    if (!formDate) { toast.error('Date is required'); return }
    try {
      const scheduledAt = new Date(`${formDate}T${formTime}`).toISOString()
      await createModuleSession(moduleId, {
        scheduled_at: scheduledAt,
        duration_minutes: formDuration,
        location: formLocation || undefined,
        max_participants: formMaxParticipants || undefined,
        materials: formMaterials ? formMaterials.split(',').map(s => s.trim()) : undefined,
        notes: formNotes || undefined,
      })
      toast.success('Session scheduled!')
      setShowForm(null)
      resetForm()
      // Reload sessions
      const updated = await getModuleSessions(moduleId)
      setSessions(prev => ({ ...prev, [moduleId]: updated }))
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create session')
    }
  }

  const handleCancel = async (sessionId: number, moduleId: number) => {
    try {
      await cancelModuleSession(sessionId)
      toast.success('Session cancelled')
      const updated = await getModuleSessions(moduleId)
      setSessions(prev => ({ ...prev, [moduleId]: updated }))
    } catch {
      toast.error('Failed to cancel session')
    }
  }

  const resetForm = () => {
    setFormDate('')
    setFormTime('10:00')
    setFormDuration(120)
    setFormLocation('')
    setFormMaxParticipants(20)
    setFormMaterials('')
    setFormNotes('')
  }

  if (loading) return <AdminShell title="Course Sessions" icon={<Calendar className="w-5 h-5" />} loading={true}><div /></AdminShell>

  const inputClass = "w-full border border-lsc-border dark:border-earth-500 rounded-lg px-3 py-2 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream text-sm focus:ring-2 focus:ring-lsc-rose focus:border-transparent"

  return (
    <AdminShell title="Course Sessions" icon={<Calendar className="w-5 h-5" />}>
      <div className="max-w-4xl mx-auto p-6">
        <div className="flex items-center gap-3 mb-6">
        <button onClick={() => selectedCourse ? setSelectedCourse(null) : navigate('/staff/admin/courses')} aria-label="Go back" className="text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-rose">
          <ArrowLeft className="w-5 h-5" />
        </button>
        <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
          {selectedCourse ? `Sessions: ${selectedCourse.title}` : 'Session Scheduling'}
        </h1>
      </div>

      {!selectedCourse ? (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700">
          <div className="p-4 border-b border-lsc-border dark:border-earth-700">
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Select a course to manage its session schedule.</p>
          </div>
          <div className="divide-y divide-lsc-border dark:divide-earth-700">
            {courses.map(course => (
              <button key={course.id} onClick={() => loadCourse(course.id)} className="w-full text-left px-4 py-3 hover:bg-lsc-cream dark:hover:bg-lsc-brown/50 transition-colors">
                <span className="text-lsc-dark dark:text-lsc-cream">{course.title}</span>
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          {selectedCourse.modules.map(mod => (
            <div key={mod.id} className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700">
              <div className="px-4 py-3 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
                <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">{mod.title}</h3>
                <button onClick={() => { setShowForm(showForm === mod.id ? null : mod.id); resetForm() }} aria-expanded={showForm === mod.id} className="flex items-center gap-1.5 text-xs font-medium text-lsc-rose hover:text-lsc-rose/80">
                  <Plus className="w-3.5 h-3.5" />
                  Schedule Session
                </button>
              </div>

              {showForm === mod.id && (
                <div className="px-4 py-4 border-b border-lsc-border dark:border-earth-700 bg-lsc-cream/50 dark:bg-earth-900/30">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1" htmlFor="session-date">Date</label>
                      <input type="date" id="session-date" value={formDate} onChange={e => setFormDate(e.target.value)} className={inputClass} />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1" htmlFor="session-time">Time</label>
                      <input type="time" id="session-time" value={formTime} onChange={e => setFormTime(e.target.value)} className={inputClass} />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1" htmlFor="session-duration">Duration (minutes)</label>
                      <input type="number" id="session-duration" value={formDuration} onChange={e => setFormDuration(parseInt(e.target.value) || 120)} className={inputClass} />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1" htmlFor="session-max">Max Participants</label>
                      <input type="number" id="session-max" value={formMaxParticipants} onChange={e => setFormMaxParticipants(parseInt(e.target.value) || 0)} className={inputClass} />
                    </div>
                    <div className="col-span-2">
                      <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1" htmlFor="session-location">Location</label>
                      <input type="text" id="session-location" value={formLocation} onChange={e => setFormLocation(e.target.value)} placeholder="e.g., Meeting Room A" className={inputClass} />
                    </div>
                    <div className="col-span-2">
                      <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1" htmlFor="session-materials">Materials (comma-separated)</label>
                      <input type="text" id="session-materials" value={formMaterials} onChange={e => setFormMaterials(e.target.value)} placeholder="sticky notes, projector, snacks" className={inputClass} />
                    </div>
                    <div className="col-span-2">
                      <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1" htmlFor="session-notes">Facilitator Notes</label>
                      <textarea id="session-notes" value={formNotes} onChange={e => setFormNotes(e.target.value)} rows={2} placeholder="Prep notes for the facilitator..." className={inputClass} />
                    </div>
                  </div>
                  <div className="flex gap-2 mt-3">
                    <button onClick={() => handleCreate(mod.id)} className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white text-sm rounded-lg font-medium">Create Session</button>
                    <button onClick={() => setShowForm(null)} className="px-4 py-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream">Cancel</button>
                  </div>
                </div>
              )}

              <div className="divide-y divide-lsc-border/50 dark:divide-earth-700/50">
                {(sessions[mod.id] || []).length === 0 ? (
                  <p className="px-4 py-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/50">No sessions scheduled</p>
                ) : (
                  (sessions[mod.id] || []).map(session => {
                    const date = new Date(session.scheduled_at)
                    return (
                      <div key={session.id} className="px-4 py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div className="flex-1">
                          <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-lsc-dark dark:text-lsc-cream">
                            <span className="flex items-center gap-1"><Calendar className="w-3.5 h-3.5 text-lsc-rose" />{date.toLocaleDateString(getCurrentLocale(), { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })} at {date.toLocaleTimeString(getCurrentLocale(), { hour: 'numeric', minute: '2-digit' })}</span>
                            <span className="flex items-center gap-1"><Clock className="w-3.5 h-3.5" />{session.duration_minutes} min</span>
                            {session.location && <span className="flex items-center gap-1"><MapPin className="w-3.5 h-3.5" />{session.location}</span>}
                            <span className="flex items-center gap-1"><Users className="w-3.5 h-3.5" />{session.rsvp_count} RSVPs{session.max_participants ? `/${session.max_participants}` : ''}</span>
                          </div>
                        </div>
                        <button onClick={() => handleCancel(session.id, mod.id)} className="text-status-danger-500 hover:text-status-danger-700 p-1" title="Cancel session" aria-label="Cancel session">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    )
                  })
                )}
              </div>
            </div>
          ))}
        </div>
      )}
      </div>
    </AdminShell>
  )
}
