/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getEvents, createEvent, updateEvent, deleteEvent, getEventCategories, getEventAudiences, type Event, type EventCreate } from '@/api/events-api'
import EventForm, { type EventFormData } from '../components/EventForm'
import EventBulkRecurringForm from '../components/EventBulkRecurringForm'
import { Shield, Plus, Edit2, Trash2, Calendar, MapPin, Users, X, Loader2, Search, ClipboardList, Repeat } from 'lucide-react'
import toast from 'react-hot-toast'
import { toApiDateTime, toDateTimeLocalValue } from '@/pages/events/utils/eventDateTime'
import { useTranslation, getCurrentLocale } from '@/i18n'
import { AdminShell } from '../components/shells/AdminShell'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import PageContainer from '@/components/layout/PageContainer'

function applySensoryFields(eventData: EventCreate, formData: EventFormData): void {
  if (formData.lighting) eventData.lighting = formData.lighting
  if (formData.noise_level) eventData.noise_level = formData.noise_level
  if (formData.crowd_size) eventData.crowd_size = formData.crowd_size
  if (formData.quiet_space_available) eventData.quiet_space_available = true
}

function sensoryInitialData(
  event: Event,
): Pick<EventFormData, 'lighting' | 'noise_level' | 'crowd_size' | 'quiet_space_available'> {
  return {
    lighting: event.lighting || '',
    noise_level: event.noise_level || '',
    crowd_size: event.crowd_size || '',
    quiet_space_available: event.quiet_space_available || false,
  }
}

export default function EventManagementPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user, token } = useAuth()
  const queryClient = useQueryClient()
  const [showModal, setShowModal] = useState(false)
  const [showBulkModal, setShowBulkModal] = useState(false)
  const [editingEvent, setEditingEvent] = useState<Event | null>(null)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<Event | null>(null)
  const [filterMode, setFilterMode] = useState<'all' | 'upcoming' | 'past'>('all')
  const [searchQuery, setSearchQuery] = useState('')
  const { data: eventsData, isLoading } = useQuery({
    queryKey: ['admin-events', filterMode, searchQuery],
    queryFn: () => {
      // Request the API max page size (100); full pagination TBD. Was 500, which
      // the events endpoint silently ignored (it reads page_size, capped at 100).
      const filters: Record<string, unknown> = { per_page: 100 }
      if (filterMode === 'upcoming') filters.upcoming = true
      else if (filterMode === 'past') filters.upcoming = false
      if (searchQuery) filters.search = searchQuery
      return getEvents(filters as import('@/api/events-api').EventFilters)
    },
  })

  const { data: availableCategories = [] } = useQuery({
    queryKey: ['event-categories'],
    queryFn: getEventCategories,
    staleTime: 5 * 60 * 1000,
  })

  const { data: availableAudiences = [] } = useQuery({
    queryKey: ['event-audiences'],
    queryFn: getEventAudiences,
    staleTime: 5 * 60 * 1000,
  })

  const createMutation = useMutation({
    mutationFn: (data: EventCreate) => createEvent(token!, data),
    onSuccess: () => {
      toast.success(t('toast.eventManagement.eventCreatedSuccessfully'))
      queryClient.invalidateQueries({ queryKey: ['admin-events'] })
      queryClient.invalidateQueries({ queryKey: ['events'] })
      setShowModal(false)
    },
    onError: (error: Error) => {
      toast.error(error.message || t('toast.eventManagement.failedToCreateEvent'))
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: EventCreate }) => updateEvent(token!, id, data),
    onSuccess: () => {
      toast.success(t('toast.eventManagement.eventUpdatedSuccessfully'))
      queryClient.invalidateQueries({ queryKey: ['admin-events'] })
      queryClient.invalidateQueries({ queryKey: ['events'] })
      setShowModal(false)
      setEditingEvent(null)
    },
    onError: (error: Error) => {
      toast.error(error.message || t('toast.eventManagement.failedToUpdateEvent'))
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (eventId: number) => deleteEvent(token!, eventId),
    onSuccess: () => {
      toast.success(t('toast.eventManagement.eventDeletedSuccessfully'))
      queryClient.invalidateQueries({ queryKey: ['admin-events'] })
      queryClient.invalidateQueries({ queryKey: ['events'] })
      setShowDeleteConfirm(null)
    },
    onError: (error: Error) => {
      toast.error(error.message || t('toast.eventManagement.failedToDeleteEvent'))
    },
  })


  if (!user || !['admin', 'super_admin', 'staff'].includes(user.role)) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-lsc-cream via-lsc-cream to-earth-50 dark:from-lsc-dark dark:via-earth-800 dark:to-lsc-dark py-20">
        <PageContainer className="text-center">
          <Shield className="w-16 h-16 text-lsc-dark/70 dark:text-lsc-cream/70 mx-auto mb-4" />
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">Staff-Only Area</h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">{t('eventManagement.staffOrAdminAccessRequired')}</p>
        </PageContainer>
      </div>
    )
  }
  const handleCreateEvent = async (formData: EventFormData) => {
    const eventData: EventCreate = {
      title: formData.title,
      start_time: toApiDateTime(formData.start_time),
      registration_required: formData.registration_required,
      max_attendees: formData.max_attendees ? parseInt(formData.max_attendees, 10) : null,
    }

    if (formData.description) eventData.description = formData.description
    if (formData.category) eventData.category = formData.category
    if (formData.audience) eventData.audience = formData.audience
    if (formData.event_language) eventData.event_language = formData.event_language
    if (formData.location) eventData.location = formData.location
    if (formData.end_time) eventData.end_time = toApiDateTime(formData.end_time)

    // Expanded fields
    if (formData.tags.length > 0) eventData.tags = formData.tags
    if (formData.image_url) eventData.image_url = formData.image_url
    if (formData.is_featured) eventData.is_featured = true
    if (formData.is_virtual) {
      eventData.is_virtual = true
      if (formData.virtual_link) eventData.virtual_link = formData.virtual_link
    }
    if (formData.series_id) eventData.series_id = formData.series_id
    if (formData.series_name) eventData.series_name = formData.series_name
    if (formData.branch_id) eventData.branch_id = parseInt(formData.branch_id, 10)
    if (formData.accessibility_notes) eventData.accessibility_notes = formData.accessibility_notes
    if (formData.wheelchair_accessible) eventData.wheelchair_accessible = true
    if (formData.asl_provided) eventData.asl_provided = true
    if (formData.captioning_provided) eventData.captioning_provided = true
    if (formData.assistive_listening) eventData.assistive_listening = true
    if (formData.sensory_friendly) eventData.sensory_friendly = true
    if (formData.large_print_available) eventData.large_print_available = true
    applySensoryFields(eventData, formData)

    if (editingEvent) {
      await updateMutation.mutateAsync({ id: editingEvent.id, data: eventData })
    } else {
      await createMutation.mutateAsync(eventData)
    }
  }

  const handleEdit = (event: Event) => {
    setEditingEvent(event)
    setShowModal(true)
  }

  const handleDelete = (event: Event) => {
    setShowDeleteConfirm(event)
  }

  const confirmDelete = () => {
    if (showDeleteConfirm) {
      deleteMutation.mutate(showDeleteConfirm.id)
    }
  }

  const handleCloseModal = () => {
    setShowModal(false)
    setEditingEvent(null)
  }

  const formatDateTime = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString(getCurrentLocale(), {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    })
  }

  const getEventStatus = (event: Event) => {
    const now = new Date()
    const start = new Date(event.start_time)
    const end = event.end_time ? new Date(event.end_time) : null

    if (end && now > end) {
      return { label: 'Past', color: 'text-lsc-dark/70 dark:text-lsc-cream/70 bg-lsc-cream dark:bg-earth-800' }
    }
    if (now > start && (!end || now <= end)) {
      return { label: 'Active', color: 'text-lsc-rose dark:text-lsc-rose-light bg-lsc-cream dark:bg-lsc-dark/30' }
    }
    return { label: 'Upcoming', color: 'text-lsc-rose dark:text-lsc-cream/70 bg-lsc-cream dark:bg-lsc-brown/30' }
  }

  const events = eventsData?.data || []

  return (
    <AdminShell title="Event Management">
    <div className="min-h-screen bg-gradient-to-b from-lsc-cream via-lsc-cream to-earth-50 dark:from-lsc-dark dark:via-earth-800 dark:to-lsc-dark py-8">
      <PageContainer>
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">
              Manage Events
            </h1>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
              Create, edit, and manage library events
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowBulkModal(true)}
              className="px-4 py-2 bg-lsc-brown hover:bg-lsc-brown/90 text-white rounded-xl flex items-center gap-2 transition-colors focus:ring-2 focus:ring-lsc-brown"
            >
              <Repeat className="w-5 h-5" />
              Create recurring series
            </button>
            <button
              onClick={() => {
                setEditingEvent(null)
                setShowModal(true)
              }}
              className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl flex items-center gap-2 transition-colors focus:ring-2 focus:ring-lsc-rose"
            >
              <Plus className="w-5 h-5" />
              Create New Event
            </button>
          </div>
        </div>

        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 mb-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex gap-2">
              <button
                onClick={() => setFilterMode('all')}
                aria-pressed={filterMode === 'all'}
                className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
                  filterMode === 'all'
                    ? 'bg-lsc-rose text-white'
                    : 'bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream/80 hover:bg-lsc-cream dark:hover:bg-lsc-brown/90'
                }`}
              >
                All Events
              </button>
              <button
                onClick={() => setFilterMode('upcoming')}
                aria-pressed={filterMode === 'upcoming'}
                className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
                  filterMode === 'upcoming'
                    ? 'bg-lsc-rose text-white'
                    : 'bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream/80 hover:bg-lsc-cream dark:hover:bg-lsc-brown/90'
                }`}
              >
                Upcoming
              </button>
              <button
                onClick={() => setFilterMode('past')}
                aria-pressed={filterMode === 'past'}
                className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
                  filterMode === 'past'
                    ? 'bg-lsc-rose text-white'
                    : 'bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream/80 hover:bg-lsc-cream dark:hover:bg-lsc-brown/90'
                }`}
              >
                Past
              </button>
            </div>

            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
                <input
                  type="text"
                  placeholder={t('placeholder.eventManagement.searchByTitle')}
                  aria-label={t('aria.eventManagement.searchByTitle')}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                />
              </div>
            </div>
          </div>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 text-lsc-rose motion-safe:animate-spin" />
          </div>
        ) : events.length === 0 ? (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-8 text-center">
            <Calendar className="w-12 h-12 text-lsc-dark/70 dark:text-lsc-cream/70 mx-auto mb-3" />
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
              {searchQuery ? 'No events found matching your search' : 'No events found'}
            </p>
          </div>
        ) : (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full" aria-label={t('aria.eventManagement.eventsManagement')}>
                <thead className="bg-lsc-cream dark:bg-lsc-brown">
                  <tr>
                    <th scope="col" className="px-4 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                      Title
                    </th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                      Date & Time
                    </th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                      Location
                    </th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                      Category
                    </th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                      Status
                    </th>
                    <th className="px-4 py-3 text-right text-sm font-semibold text-lsc-dark dark:text-lsc-cream">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                  {events.map((event) => {
                    const status = getEventStatus(event)
                    return (
                      <tr
                        key={event.id}
                        className="hover:bg-lsc-cream dark:hover:bg-lsc-brown/50 transition-colors"
                      >
                        <td className="px-4 py-3">
                          <div>
                            <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                              {event.title}
                            </p>
                            {event.registration_required && (
                              <div className="flex items-center gap-2 mt-1">
                                <Users className="w-3 h-3 text-lsc-dark/70 dark:text-lsc-cream/70" />
                                <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                                  {event.registration_count}{event.max_attendees ? `/${event.max_attendees}` : ''} registered
                                </span>
                              </div>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                          <div className="flex items-center gap-2">
                            <Calendar className="w-4 h-4" />
                            {formatDateTime(event.start_time)}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                          <div className="flex items-center gap-2">
                            <MapPin className="w-4 h-4" />
                            {event.location || 'TBD'}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                          {event.category || '-'}
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${status.color}`}
                          >
                            {status.label}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Link
                              to={`/staff/events/${event.id}/roster`}
                              className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown/90 rounded-xl transition-colors"
                              aria-label={t('events.roster.openRosterAria', 'Open roster for {{title}}').replace('{{title}}', event.title)}
                              title={t('events.roster.openRoster', 'Roster')}
                            >
                              <ClipboardList className="w-4 h-4" />
                            </Link>
                            <button
                              onClick={() => handleEdit(event)}
                              className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown/90 rounded-xl transition-colors"
                              aria-label={`Edit ${event.title}`}
                            >
                              <Edit2 className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleDelete(event)}
                              className="p-2 text-status-danger-600 dark:text-status-danger-400 hover:bg-status-danger-100 dark:bg-status-danger-900/30 dark:hover:bg-status-danger-900/30 rounded-xl transition-colors"
                              aria-label={`Delete ${event.title}`}
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
  )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </PageContainer>

      {showModal && (
        <ModalBackdrop onClose={handleCloseModal} title="Dialog">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-2xl w-full" style={{ maxHeight: '90vh', overflowY: 'auto' }}>
            <div className="flex items-center justify-between p-4 border-b border-lsc-border dark:border-earth-700 sticky top-0 bg-lsc-white dark:bg-earth-800 z-10">
              <h2 className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                {editingEvent ? 'Edit Event' : 'Create New Event'}
              </h2>
              <button
                onClick={handleCloseModal}
                className="p-1 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-full transition-colors"
                aria-label={t('aria.addRoleModal.closeModal')}
              >
                <X className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
              </button>
            </div>
            <div className="p-4">
              <EventForm
                // Remount the form when the edit target changes so it
                // re-initializes from the new event. EventForm intentionally
                // does not re-sync from initialData on prop change (that would
                // revert in-progress edits on every parent re-render).
                key={editingEvent ? `edit-${editingEvent.id}` : 'create'}
                onSubmit={handleCreateEvent}
                onCancel={handleCloseModal}
                initialData={
                  editingEvent ? {
                    title: editingEvent.title,
                    description: editingEvent.description || '',
                    category: editingEvent.category || '',
                    audience: editingEvent.audience || '',
                    event_language: editingEvent.event_language || '',
                    location: editingEvent.location || '',
                    start_time: toDateTimeLocalValue(editingEvent.start_time),
                    end_time: editingEvent.end_time ? toDateTimeLocalValue(editingEvent.end_time) : '',
                    registration_required: editingEvent.registration_required,
                    max_attendees: editingEvent.max_attendees?.toString() || '',
                    tags: editingEvent.tags || [],
                    image_url: editingEvent.image_url || '',
                    is_featured: editingEvent.is_featured,
                    is_virtual: editingEvent.is_virtual,
                    virtual_link: editingEvent.virtual_link || '',
                    series_id: editingEvent.series_id || '',
                    series_name: editingEvent.series_name || '',
                    branch_id: editingEvent.branch_id != null ? String(editingEvent.branch_id) : '',
                    accessibility_notes: editingEvent.accessibility_notes || '',
                    wheelchair_accessible: editingEvent.wheelchair_accessible || false,
                    asl_provided: editingEvent.asl_provided || false,
                    captioning_provided: editingEvent.captioning_provided || false,
                    assistive_listening: editingEvent.assistive_listening || false,
                    sensory_friendly: editingEvent.sensory_friendly || false,
                    large_print_available: editingEvent.large_print_available || false,
                    ...sensoryInitialData(editingEvent),
                  } : undefined
                }
                isSubmitting={createMutation.isPending || updateMutation.isPending}
                availableCategories={availableCategories}
                availableAudiences={availableAudiences}
              />
            </div>
          </div>
        </ModalBackdrop>
      )}

      {showBulkModal && (
        <ModalBackdrop onClose={() => setShowBulkModal(false)} title="Create recurring series">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-2xl w-full" style={{ maxHeight: '90vh', overflowY: 'auto' }}>
            <div className="flex items-center justify-between p-4 border-b border-lsc-border dark:border-earth-700 sticky top-0 bg-lsc-white dark:bg-earth-800 z-10">
              <h2 className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                Create recurring series
              </h2>
              <button
                onClick={() => setShowBulkModal(false)}
                className="p-1 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-full transition-colors"
                aria-label={t('aria.addRoleModal.closeModal')}
              >
                <X className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
              </button>
            </div>
            <div className="p-4">
              <EventBulkRecurringForm onCancel={() => setShowBulkModal(false)} />
            </div>
          </div>
        </ModalBackdrop>
      )}

      {showDeleteConfirm && (
        <ModalBackdrop onClose={() => setShowDeleteConfirm(null)} title="Delete Event" role="alertdialog">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full">
            <div className="p-6">
              <h2 className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
                Delete Event
              </h2>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                Are you sure you want to delete "{showDeleteConfirm.title}"? This action cannot be undone.
              </p>
              <div className="flex gap-3">
                <button
                  onClick={() => setShowDeleteConfirm(null)}
                  disabled={deleteMutation.isPending}
                  className="flex-1 px-4 py-2 border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream/80 rounded-xl hover:bg-lsc-cream dark:hover:bg-lsc-brown transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={confirmDelete}
                  disabled={deleteMutation.isPending}
                  className="flex-1 px-4 py-2 bg-status-danger-600 hover:bg-status-danger-700 disabled:bg-status-danger-400 text-white rounded-xl transition-colors flex items-center justify-center gap-2"
                >
                  {deleteMutation.isPending ? (
                    <>
                      <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                      Deleting...
                    </>
                  ) : (
                    'Delete Event'
                  )}
                </button>
              </div>
            </div>
          </div>
        </ModalBackdrop>
      )}
    </div>
    </AdminShell>
  )
}
