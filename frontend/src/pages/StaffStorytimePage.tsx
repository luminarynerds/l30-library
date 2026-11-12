/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import {
  BookOpen, Plus, Loader2, Users, Calendar, Baby, MapPin,
  AlertTriangle, Music, Scissors, Pencil
} from 'lucide-react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { fetchApi } from '@/lib/api-client'
import { getAccessToken } from '@/utils/tokenStore'
import { AdminShell } from '../components/shells/AdminShell'
import { CreateStorytimeSeriesModal } from '../components/staff/CreateStorytimeSeriesModal'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import PageContainer from '@/components/layout/PageContainer'

// Types
interface DashboardSummary {
  total_series: number
  active_series: number
  sessions_this_week: number
  total_attendees: number
  repeat_attendees: number
  books_in_library: number
  crafts_available: number
  low_stock_supplies: number
}

interface StorytimeSeries {
  id: number
  title: string
  description: string | null
  series_type: string
  primary_age_group: string
  location: string
  day_of_week: string | null
  start_time: string | null
  duration_minutes: number
  max_capacity: number | null
  is_active: boolean
}

interface StorytimeSession {
  id: number
  series_id: number
  session_date: string
  start_time: string
  status: string
  is_cancelled: boolean
  actual_attendance: number
  expected_attendance: number
}

function authOpts() {
  const token = getAccessToken()
  return token ? { token } : {}
}

const AGE_LABELS: Record<string, string> = {
  babies: 'Babies',
  toddlers: 'Toddlers',
  twos: 'Twos',
  threes: 'Threes',
  fours: 'Fours',
  fives_and_up: '5+',
  preschool: 'Preschool',
  school_age: 'School Age',
  families: 'Families',
}

const TYPE_LABELS: Record<string, string> = {
  weekly: 'Weekly',
  biweekly: 'Biweekly',
  monthly: 'Monthly',
  drop_in: 'Drop-in',
  special_event: 'Special Event',
  workshop: 'Workshop',
}

const STATUS_COLORS: Record<string, string> = {
  scheduled: 'bg-status-info-100 text-status-info-800 dark:bg-status-info-900/30 dark:text-status-info-300',
  completed: 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300',
  in_progress: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300',
  cancelled_weather: 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-300',
  cancelled_other: 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-300',
}

function StatCard({ icon: Icon, label, value, alert }: {
  icon: typeof BookOpen
  label: string
  value: number
  alert?: boolean
}) {
  return (
    <div className={`bg-lsc-white dark:bg-earth-800 rounded-xl border p-4 ${
      alert ? 'border-status-warning-300 dark:border-status-warning-700' : 'border-lsc-border dark:border-earth-700'
    }`}>
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-lg ${alert ? 'bg-status-warning-50 dark:bg-status-warning-900/20' : 'bg-earth-50 dark:bg-earth-900'}`}>
          <Icon className={`w-5 h-5 ${alert ? 'text-status-warning-600' : 'text-lsc-gold'}`} aria-hidden="true" />
        </div>
        <div>
          <div className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{value}</div>
          <div className="text-xs text-earth-600 dark:text-earth-400">{label}</div>
        </div>
      </div>
    </div>
  )
}

interface ContentItem { id: number; title: string; author?: string; composer?: string; age_groups?: string[]; times_used?: number; times_read?: number }
type ContentTab = 'program' | 'books' | 'songs' | 'rhymes'

export default function StaffStorytimePage(): React.ReactElement {
  const queryClient = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [editingSeries, setEditingSeries] = useState<StorytimeSeries | null>(null)
  const [contentTab, setContentTab] = useState<ContentTab>('program')
  const [showAddContent, setShowAddContent] = useState(false)
  const [addingContent, setAddingContent] = useState(false)
  const [contentForm, setContentForm] = useState<Record<string, string>>({ title: '', author: '', text: '', lyrics: '' })

  const { data: dashboard, isLoading: dashLoading } = useQuery({
    queryKey: ['storytime-dashboard'],
    queryFn: () => fetchApi<DashboardSummary>('/storytime/dashboard/summary', authOpts()),
  })

  const { data: seriesList, isLoading: seriesLoading } = useQuery({
    queryKey: ['storytime-series'],
    queryFn: () => fetchApi<StorytimeSeries[]>('/storytime/series', authOpts()),
  })

  const { data: sessions } = useQuery({
    queryKey: ['storytime-sessions'],
    queryFn: () => fetchApi<StorytimeSession[]>('/storytime/sessions?limit=10', authOpts()),
  })

  const { data: books } = useQuery({
    queryKey: ['storytime-books'],
    queryFn: () => fetchApi<ContentItem[]>('/storytime/books', authOpts()),
    enabled: contentTab === 'books',
  })
  const { data: songs } = useQuery({
    queryKey: ['storytime-songs'],
    queryFn: () => fetchApi<ContentItem[]>('/storytime/songs', authOpts()),
    enabled: contentTab === 'songs',
  })
  const { data: rhymes } = useQuery({
    queryKey: ['storytime-rhymes'],
    queryFn: () => fetchApi<ContentItem[]>('/storytime/rhymes', authOpts()),
    enabled: contentTab === 'rhymes',
  })

  const handleAddContent = async (e: React.FormEvent) => {
    e.preventDefault()
    setAddingContent(true)
    try {
      const endpoint = `/storytime/${contentTab}`
      const body: Record<string, unknown> = { title: contentForm.title }
      if (contentTab === 'books') { body.author = contentForm.author; body.illustrator = contentForm.illustrator }
      if (contentTab === 'songs') { body.composer = contentForm.author; body.lyrics = contentForm.lyrics }
      if (contentTab === 'rhymes') { body.author = contentForm.author; body.text = contentForm.text }
      await fetchApi(endpoint, { method: 'POST', body, ...authOpts() })
      setShowAddContent(false)
      setContentForm({ title: '', author: '', text: '', lyrics: '', illustrator: '' })
      queryClient.invalidateQueries({ queryKey: [`storytime-${contentTab}`] })
    } catch { /* */ }
    finally { setAddingContent(false) }
  }

  const contentItems = contentTab === 'books' ? books : contentTab === 'songs' ? songs : contentTab === 'rhymes' ? rhymes : null

  const isLoading = dashLoading || seriesLoading

  return (
    <AdminShell title="Storytime">
      <PageContainer className="py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
              <Baby className="w-6 h-6" aria-hidden="true" />
              Storytime Program
            </h1>
            <p className="text-sm text-earth-600 dark:text-earth-400 mt-1">
              Manage storytime series, sessions, and attendance.
            </p>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg text-sm font-medium hover:bg-lsc-rose/90 focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2"
            aria-label="Create new storytime series"
          >
            <Plus className="w-4 h-4" />
            New Series
          </button>
        </div>

        {/* Dashboard Stats */}
        {dashboard && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
            <StatCard icon={BookOpen} label="Active Series" value={dashboard.active_series} />
            <StatCard icon={Calendar} label="Upcoming Sessions" value={dashboard.sessions_this_week} />
            <StatCard icon={Users} label="Total Attendees" value={dashboard.total_attendees} />
            <StatCard icon={AlertTriangle} label="Low Stock Supplies" value={dashboard.low_stock_supplies} alert={dashboard.low_stock_supplies > 0} />
          </div>
        )}

        {/* Secondary Stats */}
        {dashboard && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
            <StatCard icon={Users} label="Repeat Attendees" value={dashboard.repeat_attendees} />
            <StatCard icon={BookOpen} label="Books in Library" value={dashboard.books_in_library} />
            <StatCard icon={Scissors} label="Crafts Available" value={dashboard.crafts_available} />
            <StatCard icon={Music} label="Total Series" value={dashboard.total_series} />
          </div>
        )}

        {isLoading ? (
          <div className="flex justify-center py-16" role="status" aria-label="Loading storytime data">
            <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-gold" />
          </div>
        ) : (
          <div className="space-y-8">
            {/* Series Table */}
            <div>
              <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3">Series</h2>
              {(seriesList?.length ?? 0) === 0 ? (
                <div className="text-center py-12 text-earth-600 dark:text-earth-400 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700">
                  <Baby className="w-12 h-12 mx-auto mb-3 opacity-40" aria-hidden="true" />
                  <p>No storytime series yet. Create one to get started.</p>
                </div>
              ) : (
                <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
                  <table className="w-full text-left">
                    <thead className="bg-earth-50 dark:bg-earth-900">
                      <tr>
                        <th className="px-4 py-3 text-xs font-medium text-earth-600 dark:text-earth-400 uppercase">Series</th>
                        <th className="px-4 py-3 text-xs font-medium text-earth-600 dark:text-earth-400 uppercase">Type</th>
                        <th className="px-4 py-3 text-xs font-medium text-earth-600 dark:text-earth-400 uppercase">Age Group</th>
                        <th className="px-4 py-3 text-xs font-medium text-earth-600 dark:text-earth-400 uppercase">Schedule</th>
                        <th className="px-4 py-3 text-xs font-medium text-earth-600 dark:text-earth-400 uppercase">Location</th>
                        <th className="px-4 py-3 text-xs font-medium text-earth-600 dark:text-earth-400 uppercase">Status</th>
                        <th className="px-4 py-3 text-xs font-medium text-earth-600 dark:text-earth-400 uppercase">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {seriesList?.map((series) => (
                        <tr key={series.id} className="border-b border-earth-100 dark:border-earth-700">
                          <td className="px-4 py-3">
                            <div className="font-medium text-lsc-dark dark:text-lsc-cream">{series.title}</div>
                            {series.description && (
                              <div className="text-sm text-earth-600 dark:text-earth-400 line-clamp-1">{series.description}</div>
                            )}
                          </td>
                          <td className="px-4 py-3 text-sm text-earth-600 dark:text-earth-400">
                            {TYPE_LABELS[series.series_type] ?? series.series_type}
                          </td>
                          <td className="px-4 py-3">
                            <span className="text-xs font-medium px-2 py-1 rounded-full bg-category-100 text-category-800 dark:bg-category-900/30 dark:text-category-300">
                              {AGE_LABELS[series.primary_age_group] ?? series.primary_age_group}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-sm text-earth-600 dark:text-earth-400">
                            <div className="flex items-center gap-1">
                              {series.day_of_week && <span>{series.day_of_week}</span>}
                              {series.start_time && <span>{series.start_time}</span>}
                              {!series.day_of_week && !series.start_time && '--'}
                            </div>
                            <div className="text-xs text-earth-600">{series.duration_minutes} min</div>
                          </td>
                          <td className="px-4 py-3 text-sm text-earth-600 dark:text-earth-400">
                            <div className="flex items-center gap-1">
                              <MapPin className="w-3.5 h-3.5" aria-hidden="true" />
                              {series.location}
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <span className={`text-xs font-medium px-2 py-1 rounded-full ${
                              series.is_active
                                ? 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300'
                                : 'bg-earth-100 text-earth-600 dark:bg-earth-800 dark:text-earth-400'
                            }`}>
                              {series.is_active ? 'Active' : 'Inactive'}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <button
                              onClick={() => setEditingSeries(series)}
                              className="p-1.5 text-earth-600 hover:bg-earth-50 dark:text-earth-400 dark:hover:bg-earth-800 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                              title="Edit"
                              aria-label="Edit series"
                            >
                              <Pencil className="w-4 h-4" />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Upcoming Sessions */}
            {sessions && sessions.length > 0 && (
              <div>
                <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-3">Upcoming Sessions</h2>
                <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
                  <table className="w-full text-left">
                    <thead className="bg-earth-50 dark:bg-earth-900">
                      <tr>
                        <th className="px-4 py-3 text-xs font-medium text-earth-600 dark:text-earth-400 uppercase">Date</th>
                        <th className="px-4 py-3 text-xs font-medium text-earth-600 dark:text-earth-400 uppercase">Time</th>
                        <th className="px-4 py-3 text-xs font-medium text-earth-600 dark:text-earth-400 uppercase">Status</th>
                        <th className="px-4 py-3 text-xs font-medium text-earth-600 dark:text-earth-400 uppercase">Attendance</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sessions.map((session) => (
                        <tr key={session.id} className="border-b border-earth-100 dark:border-earth-700">
                          <td className="px-4 py-3 text-sm text-lsc-dark dark:text-lsc-cream">
                            {new Date(session.session_date).toLocaleDateString()}
                          </td>
                          <td className="px-4 py-3 text-sm text-earth-600 dark:text-earth-400">
                            {new Date(session.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </td>
                          <td className="px-4 py-3">
                            <span className={`text-xs font-medium px-2 py-1 rounded-full ${STATUS_COLORS[session.status] ?? 'bg-earth-100 text-earth-600'}`}>
                              {session.is_cancelled ? 'Cancelled' : session.status}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-sm text-earth-600 dark:text-earth-400">
                            {session.actual_attendance > 0
                              ? `${session.actual_attendance} attended`
                              : session.expected_attendance > 0
                                ? `${session.expected_attendance} expected`
                                : '--'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Content Library Tabs */}
        <div className="border-b border-lsc-border dark:border-earth-700 mb-6 mt-8">
          <nav className="flex gap-4">
            {(['program', 'books', 'songs', 'rhymes'] as ContentTab[]).map(tab => (
              <button key={tab} onClick={() => setContentTab(tab)} className={`pb-3 px-1 border-b-2 font-medium capitalize text-sm ${contentTab === tab ? 'border-lsc-gold text-lsc-gold' : 'border-transparent text-earth-600 dark:text-earth-400'}`}>{tab}</button>
            ))}
          </nav>
        </div>

        {contentTab !== 'program' && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream capitalize">{contentTab} Library</h2>
              <button onClick={() => { setContentForm({ title: '', author: '', text: '', lyrics: '', illustrator: '' }); setShowAddContent(true) }} className="inline-flex items-center gap-2 px-3 py-1.5 bg-lsc-rose text-white rounded-lg text-sm hover:bg-lsc-rose/90">
                <Plus className="w-4 h-4" /> Add {contentTab.slice(0, -1)}
              </button>
            </div>
            {contentItems && contentItems.length > 0 ? (
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 divide-y divide-earth-100 dark:divide-earth-700">
                {contentItems.map(item => (
                  <div key={item.id} className="px-4 py-3 flex items-center justify-between">
                    <div>
                      <span className="font-medium text-lsc-dark dark:text-lsc-cream">{item.title}</span>
                      {(item.author || item.composer) && <span className="ml-2 text-sm text-earth-600 dark:text-earth-400">by {item.author || item.composer}</span>}
                    </div>
                    <span className="text-xs text-earth-600 dark:text-earth-400">{item.times_used ?? item.times_read ?? 0} uses</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-earth-600 dark:text-earth-400 bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700">
                No {contentTab} yet. Add some to build your library.
              </div>
            )}

            {showAddContent && (
              <ModalBackdrop onClose={() => setShowAddContent(false)} title="Add Content">
                <div className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-md w-full">
                  <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
                    <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream capitalize">Add {contentTab.slice(0, -1)}</h3>
                    <button onClick={() => setShowAddContent(false)} className="text-earth-600 hover:text-earth-700"><span className="sr-only">Close</span>&times;</button>
                  </div>
                  <form onSubmit={handleAddContent} className="p-4 space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Title *</label>
                      <input type="text" required value={contentForm.title} onChange={e => setContentForm({...contentForm, title: e.target.value})} className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">{contentTab === 'songs' ? 'Composer' : 'Author'}</label>
                      <input type="text" value={contentForm.author} onChange={e => setContentForm({...contentForm, author: e.target.value})} className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream" />
                    </div>
                    {contentTab === 'books' && (
                      <div>
                        <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Illustrator</label>
                        <input type="text" value={contentForm.illustrator || ''} onChange={e => setContentForm({...contentForm, illustrator: e.target.value})} className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream" />
                      </div>
                    )}
                    {contentTab === 'songs' && (
                      <div>
                        <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Lyrics</label>
                        <textarea value={contentForm.lyrics} onChange={e => setContentForm({...contentForm, lyrics: e.target.value})} rows={4} className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream" />
                      </div>
                    )}
                    {contentTab === 'rhymes' && (
                      <div>
                        <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Text *</label>
                        <textarea required value={contentForm.text} onChange={e => setContentForm({...contentForm, text: e.target.value})} rows={4} className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream" />
                      </div>
                    )}
                    <div className="flex justify-end gap-2 pt-2">
                      <button type="button" onClick={() => setShowAddContent(false)} className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-600 text-lsc-dark/70 dark:text-lsc-cream/70">Cancel</button>
                      <button type="submit" disabled={addingContent} className="px-4 py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 disabled:opacity-50">
                        {addingContent ? <Loader2 className="w-5 h-5 motion-safe:animate-spin" /> : 'Add'}
                      </button>
                    </div>
                  </form>
                </div>
              </ModalBackdrop>
            )}
          </div>
        )}

        {(showCreate || editingSeries) && (
          <CreateStorytimeSeriesModal
            onClose={() => { setShowCreate(false); setEditingSeries(null) }}
            onCreated={() => {
              queryClient.invalidateQueries({ queryKey: ['storytime-series'] })
              queryClient.invalidateQueries({ queryKey: ['storytime-dashboard'] })
            }}
            editing={editingSeries}
          />
        )}
      </PageContainer>
    </AdminShell>
  )
}
