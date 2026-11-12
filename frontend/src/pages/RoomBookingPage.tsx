/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Calendar, Clock, Users, AlertCircle, CheckCircle2, Loader2, X, LogIn, RotateCcw } from 'lucide-react'
import { useState, useEffect, useRef } from 'react'
import toast from 'react-hot-toast'
import api from '@/lib/api-client'
import { useRoomBookings } from '../features/rooms/useRoomBookings'
import type { Room, Booking } from '../features/rooms/useRoomBookings'
import { API_BASE } from '@/api/types'
import { useTranslation} from '@/i18n'
import { friendlyErrorMessage } from '@/utils/friendlyError'
import { usePageTitle } from '@/hooks/usePageTitle'
import { useBranding } from '@/contexts/BrandingContext'
import { useAuth } from '@/contexts/AuthContext'
import PageContainer from '@/components/layout/PageContainer'
import { RoomBookingForm } from '@/components/room-booking/RoomBookingForm'
import type { AvailabilitySlot, RoomAvailability } from '@/components/room-booking/RoomBookingForm'

const STATUS_STYLES: Record<string, string> = {
  pending: 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-300',
  confirmed: 'bg-status-info-100 dark:bg-status-info-900/30 text-status-info-700 dark:text-status-info-300',
  checked_in: 'bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300',
  completed: 'bg-earth-100 dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70',
  cancelled: 'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300',
  no_show: 'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-600 dark:text-status-danger-400',
  rejected: 'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300',
}

const STATUS_LABELS: Record<string, string> = {
  pending: 'Pending Approval',
  confirmed: 'Confirmed',
  checked_in: 'Checked In',
  completed: 'Completed',
  cancelled: 'Cancelled',
  no_show: 'No Show',
  rejected: 'Rejected',
}

function formatSlotTime(isoString: string) {
  return new Date(isoString).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
}

function formatDateTime(isoString: string) {
  const d = new Date(isoString)
  return d.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' }) +
    ' at ' + d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
}

function canCheckIn(booking: Booking): boolean {
  if (booking.status !== 'confirmed') return false
  const start = new Date(booking.start_time)
  const now = new Date()
  const fifteenMinBefore = new Date(start.getTime() - 15 * 60 * 1000)
  const fifteenMinAfter = new Date(start.getTime() + 15 * 60 * 1000)
  return now >= fifteenMinBefore && now <= fifteenMinAfter
}

function canCancel(booking: Booking): boolean {
  return ['pending', 'confirmed'].includes(booking.status)
}

export default function RoomBookingPage() {
  const branding = useBranding()
  const { user } = useAuth()
  usePageTitle('Book a Room', `Reserve meeting rooms and study spaces at ${branding.library_short_name}. Free for community groups and individuals.`)
  const { t } = useTranslation()
  const { rooms, bookings, loading: roomsLoading, error: roomsError, fetchRooms, fetchBookings, cancelBooking, checkInBooking } = useRoomBookings()

  const [activeTab, setActiveTab] = useState<'book' | 'reservations'>('book')
  const [selectedRoom, setSelectedRoom] = useState<number | null>(null)
  const [selectedDate, setSelectedDate] = useState('')
  const [selectedSlot, setSelectedSlot] = useState<AvailabilitySlot | null>(null)
  const [selectedStartTime, setSelectedStartTime] = useState<string | null>(null)
  const [selectedDuration, setSelectedDuration] = useState<number>(30)
  const [guestCount, setGuestCount] = useState('1')
  const [purpose, setPurpose] = useState('')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [submittedStatus, setSubmittedStatus] = useState('')
  const [typeFilter, setTypeFilter] = useState<string>('')
  const [hideApprovalRequired, setHideApprovalRequired] = useState(false)

  const [availability, setAvailability] = useState<RoomAvailability | null>(null)
  const [loadingAvailability, setLoadingAvailability] = useState(false)
  const [availabilityError, setAvailabilityError] = useState<string | null>(null)
  const [retryAvailabilityKey, setRetryAvailabilityKey] = useState(0)

  // Time-first flow: when a date is chosen, count free slots per room for that
  // day so each room card can show whether it has openings before you pick it.
  // Keyed by room id. undefined = not yet checked for the current date.
  const [dayAvailabilityByRoom, setDayAvailabilityByRoom] = useState<Record<number, number>>({})
  const [loadingDayAvailability, setLoadingDayAvailability] = useState(false)

  const [cancellingId, setCancellingId] = useState<number | null>(null)
  const [checkingInId, setCheckingInId] = useState<number | null>(null)
  const [loadingBookings, setLoadingBookings] = useState(false)

  // Inline form-level error shown when submit validation fails
  const [formError, setFormError] = useState('')
  const formErrorRef = useRef<HTMLDivElement>(null)
  const nameRef = useRef<HTMLInputElement>(null)
  const emailRef = useRef<HTMLInputElement>(null)
  // Track missing-required-field state for aria-invalid on contact fields
  const [nameInvalid, setNameInvalid] = useState(false)
  const [emailInvalid, setEmailInvalid] = useState(false)

  // Announcement text for the aria-live region (room selection / availability changes)
  const [liveAnnouncement, setLiveAnnouncement] = useState('')

  // Focus the inline error when it appears
  useEffect(() => {
    if (formError && formErrorRef.current) {
      formErrorRef.current.focus()
    }
  }, [formError])

  // Load rooms on mount
  useEffect(() => {
    fetchRooms()
  }, [fetchRooms])

  // Auto-fill contact info from logged-in user
  useEffect(() => {
    if (user) {
      if (!name) setName(user.full_name || `${user.first_name} ${user.last_name}`.trim())
      if (!email) setEmail(user.email || '')
      if (!phone && user.phone) setPhone(user.phone)
    }
  }, [user]) // eslint-disable-line react-hooks/exhaustive-deps

  // Fetch bookings when switching to reservations tab
  useEffect(() => {
    if (activeTab === 'reservations') {
      setLoadingBookings(true)
      fetchBookings().finally(() => setLoadingBookings(false))
    }
  }, [activeTab, fetchBookings])

  // Fetch availability when room and date change
  useEffect(() => {
    if (!selectedRoom || !selectedDate) {
      setAvailability(null)
      setSelectedSlot(null)
      setSelectedStartTime(null)
      setAvailabilityError(null)
      return
    }

    let cancelled = false

    const loadAvailability = async () => {
      setLoadingAvailability(true)
      setSelectedSlot(null)
      setSelectedStartTime(null)
      setAvailabilityError(null)
      try {
        const data: RoomAvailability = await api.get(
          `${API_BASE}/rooms/${selectedRoom}/availability?date=${selectedDate}`
        )
        if (!cancelled) {
          setAvailability(data)
          setAvailabilityError(null)
          const count = data.available_slots.length
          setLiveAnnouncement(
            count > 0
              ? `${count} time slot${count === 1 ? '' : 's'} available for the selected room and date.`
              : 'No available time slots for the selected room and date.'
          )
        }
      } catch (err: unknown) {
        if (!cancelled) {
          const errorMessage = friendlyErrorMessage(err)
          setAvailabilityError(errorMessage)
          toast.error(errorMessage)
          setAvailability(null)
          setLiveAnnouncement('Could not load availability. Please try again.')
        }
      } finally {
        if (!cancelled) setLoadingAvailability(false)
      }
    }

    loadAvailability()
    return () => { cancelled = true }
  }, [selectedRoom, selectedDate, retryAvailabilityKey])

  // Time-first: when a date is picked, ask the multi-room endpoint how many
  // slots each room has free that day. Lets cards show availability up front
  // so patrons pick a time first, then a room that is actually open.
  useEffect(() => {
    if (!selectedDate || rooms.length === 0) {
      setDayAvailabilityByRoom({})
      return
    }

    let cancelled = false
    const loadDayAvailability = async () => {
      setLoadingDayAvailability(true)
      try {
        const start = new Date(selectedDate + 'T00:00:00')
        const end = new Date(start.getTime() + 86400000)
        const endDate = end.toISOString().split('T')[0]
        const roomIds = rooms.map(r => r.id).join(',')
        const data: Record<string, RoomAvailability[]> = await api.get(
          `${API_BASE}/rooms/availability/multi?room_ids=${roomIds}&start_date=${selectedDate}&end_date=${endDate}`
        )
        if (cancelled) return
        const counts: Record<number, number> = {}
        for (const room of rooms) {
          const days = data[String(room.id)] || []
          const day = days.find(d => d.date === selectedDate) || days[0]
          counts[room.id] = day ? day.available_slots.length : 0
        }
        setDayAvailabilityByRoom(counts)
      } catch {
        // Non-fatal: cards just fall back to showing no availability hint.
        if (!cancelled) setDayAvailabilityByRoom({})
      } finally {
        if (!cancelled) setLoadingDayAvailability(false)
      }
    }

    loadDayAvailability()
    return () => { cancelled = true }
  }, [selectedDate, rooms])

  const selectedRoomData: Room | undefined = rooms.find(r => r.id === selectedRoom)

  // Reset duration to room's minimum when room changes
  useEffect(() => {
    if (selectedRoomData) {
      setSelectedDuration(selectedRoomData.min_duration_minutes)
      setLiveAnnouncement(`${selectedRoomData.name} selected.`)
    }
  }, [selectedRoomData?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  const filteredRooms = rooms.filter(room => {
    if (typeFilter && room.room_type !== typeFilter) return false
    if (hideApprovalRequired && room.requires_approval) return false
    return true
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError('')
    setNameInvalid(false)
    setEmailInvalid(false)

    if (!selectedRoom || !selectedSlot || !name || !email) {
      const missing: string[] = []
      if (!selectedRoom) missing.push('a room')
      if (!selectedSlot) missing.push('a time slot')
      if (!name) { setNameInvalid(true); missing.push('your name') }
      if (!email) { setEmailInvalid(true); missing.push('your email') }
      const msg = `Please provide ${missing.join(', ')} to continue.`
      setFormError(msg)
      toast.error(t('roomBooking.pleaseFillInAllRequired'))
      // Focus the first missing contact field if applicable
      if (!name) nameRef.current?.focus()
      else if (!email) emailRef.current?.focus()
      return
    }

    if (selectedRoomData && parseInt(guestCount) > selectedRoomData.capacity) {
      toast.error(t('toast.roomBooking.guestCountExceedsRoomCapacity', { capacity: selectedRoomData.capacity }))
      return
    }

    setSubmitting(true)
    try {
      const result = await api.post<{ status: string }>(`${API_BASE}/rooms/${selectedRoom}/reservations`, {
        room_id: selectedRoom,
        start_time: selectedSlot.start_time,
        end_time: selectedSlot.end_time,
        purpose: purpose || undefined,
        attendee_count: parseInt(guestCount) || 1,
        contact_name: name,
        contact_email: email,
        contact_phone: phone || undefined,
      })

      setSubmittedStatus(result.status)
      setSubmitted(true)

      if (result.status === 'confirmed') {
        toast.success(t('toast.roomBooking.roomReservationConfirmed'))
      } else {
        toast.success(t('roomBooking.roomReservationSubmittedForApproval'))
      }
    } catch (err: unknown) {
      const httpErr = err as { status?: number; message?: string }
      if (httpErr.status === 409) {
        toast.error(t('roomBooking.thisTimeSlotIsNo'))
        // Refresh availability
        try {
          const data: RoomAvailability = await api.get(
            `${API_BASE}/rooms/${selectedRoom}/availability?date=${selectedDate}`
          )
          setAvailability(data)
          setSelectedSlot(null)
          setSelectedStartTime(null)
        } catch { /* ignore */ }
      } else if (httpErr.status === 401) {
        toast.error(t('roomBooking.pleaseLogInToMake'))
      } else {
        toast.error(httpErr.message || t('toast.roomBooking.failedToSubmitReservation'))
      }
    } finally {
      setSubmitting(false)
    }
  }

  const handleCancel = async (bookingId: number) => {
    setCancellingId(bookingId)
    try {
      await cancelBooking(bookingId)
      toast.success(t('toast.computers.reservationCancelled'))
    } catch (err: unknown) {
      toast.error(friendlyErrorMessage(err))
    } finally {
      setCancellingId(null)
    }
  }

  const handleCheckIn = async (bookingId: number) => {
    setCheckingInId(bookingId)
    try {
      await checkInBooking(bookingId)
      toast.success(t('toast.roomBooking.checkedInSuccessfully'))
    } catch (err: unknown) {
      toast.error(friendlyErrorMessage(err))
    } finally {
      setCheckingInId(null)
    }
  }

  const resetForm = () => {
    setSelectedRoom(null)
    setSelectedDate('')
    setSelectedSlot(null)
    setSelectedStartTime(null)
    setSelectedDuration(30)
    setGuestCount('1')
    setPurpose('')
    setName('')
    setEmail('')
    setPhone('')
    setSubmitted(false)
    setSubmittedStatus('')
    setAvailability(null)
    setAvailabilityError(null)
    setFormError('')
    setNameInvalid(false)
    setEmailInvalid(false)
    setLiveAnnouncement('')
  }

  // ── Success screen ──────────────────────────────────────────────
  if (submitted) {
    const isPending = submittedStatus === 'pending'
    return (
      <PageContainer className="py-12 text-center">
        <div className={`p-8 rounded-xl border ${
          isPending
            ? 'bg-status-warning-50 dark:bg-status-warning-900/20 border-status-warning-200 dark:border-status-warning-900/30'
            : 'bg-status-success-50 dark:bg-status-success-900/20 border-status-success-200 dark:border-status-success-900/30'
        }`}>
          <CheckCircle2 className={`w-16 h-16 mx-auto mb-4 ${isPending ? 'text-status-warning-600' : 'text-status-success-600'}`} />
          <h2 className={`text-2xl font-serif font-bold mb-3 ${
            isPending ? 'text-status-warning-900 dark:text-status-warning-100' : 'text-status-success-900 dark:text-status-success-100'
          }`}>
            {isPending ? t('roomBooking.reservationSubmittedHeading', 'Reservation Submitted for Approval') : t('roomBooking.reservationConfirmedHeading', 'Reservation Confirmed!')}
          </h2>
          <p className={`mb-4 ${isPending ? 'text-status-warning-700 dark:text-status-warning-200' : 'text-status-success-700 dark:text-status-success-200'}`}>
            {isPending
              ? <>{t('roomBooking.pendingApprovalPrefix', 'Your reservation for')} <strong>{selectedRoomData?.name}</strong> {t('roomBooking.pendingApprovalMiddle', "requires staff approval. You'll receive an email at")} <strong>{email}</strong> {t('roomBooking.pendingApprovalSuffix', "once it's been reviewed.")}</>
              : <>{t('roomBooking.yourRoomReservationHasBeen')} <strong>{email}</strong> {t('roomBooking.confirmationShortly', 'shortly.')}</>
            }
          </p>
          {isPending && (
            <p className="text-sm text-status-warning-600 dark:text-status-warning-300 mb-4">
              {t('roomBooking.approvalTimeframeNotice', 'Meeting rooms and event spaces require approval. Most requests are reviewed within 24 hours.')}
            </p>
          )}
          <p className={`text-sm ${isPending ? 'text-status-warning-600 dark:text-status-warning-300' : 'text-status-success-600 dark:text-status-success-300'}`}>
            {t('roomBooking.manageFromTabHint', 'You can manage your reservations from the My Reservations tab.')}
          </p>
          <div className="flex gap-3 justify-center mt-6">
            <button
              onClick={() => { resetForm(); setActiveTab('reservations') }}
              className="px-6 py-2 border-2 border-lsc-rose text-lsc-rose font-semibold rounded-lg hover:bg-lsc-rose/10 transition"
            >
              {t('roomBooking.viewMyReservations', 'View My Reservations')}
            </button>
            <button
              onClick={resetForm}
              className="px-6 py-2 bg-lsc-rose text-white font-semibold rounded-lg hover:bg-lsc-rose/90 transition"
            >
              {t('roomBooking.bookAnotherRoom', 'Book Another Room')}
            </button>
          </div>
        </div>
      </PageContainer>
    )
  }

  // ── Main layout ───────────────────────────────────────────────────
  return (
    <PageContainer className="py-8">
      {/* Polite live region for dynamic announcements (room selection, availability) */}
      <div aria-live="polite" aria-atomic="true" className="sr-only" role="status">
        {liveAnnouncement}
      </div>

      {/* Header */}
      <div className="mb-8">
        <div className="inline-flex items-center gap-3 mb-4">
          <div className="p-3 bg-lsc-rose/10 rounded-full">
            <Calendar className="w-8 h-8 text-lsc-rose" />
          </div>
          <h1 className="font-serif text-4xl font-bold text-lsc-dark dark:text-lsc-cream">{t('roomBooking.bookARoom', 'Book a Room')}</h1>
        </div>
        <p className="text-lg text-lsc-dark/70 dark:text-lsc-cream/70">
          {t('roomBooking.subtitle', 'Reserve a quiet space for studying, meetings, or group work. Study rooms are free for library patrons. Meeting and event spaces may have rental fees.')}
        </p>
      </div>

      {/* Tab Navigation */}
      <div role="tablist" aria-label={t('aria.roomBooking.roomBookingSections')} className="flex gap-1 mb-8 border-b border-lsc-border dark:border-earth-700">
        <button
          role="tab"
          id="tab-book"
          aria-selected={activeTab === 'book'}
          aria-controls="tabpanel-book"
          onClick={() => setActiveTab('book')}
          className={`px-6 py-3 font-semibold text-sm transition border-b-2 -mb-px ${
            activeTab === 'book'
              ? 'border-lsc-rose text-lsc-rose'
              : 'border-transparent text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream'
          }`}
        >
          {t('roomBooking.bookARoom', 'Book a Room')}
        </button>
        <button
          role="tab"
          id="tab-reservations"
          aria-selected={activeTab === 'reservations'}
          aria-controls="tabpanel-reservations"
          onClick={() => setActiveTab('reservations')}
          className={`px-6 py-3 font-semibold text-sm transition border-b-2 -mb-px ${
            activeTab === 'reservations'
              ? 'border-lsc-rose text-lsc-rose'
              : 'border-transparent text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream'
          }`}
        >
          {t('roomBooking.myReservations', 'My Reservations')}
        </button>
      </div>

      {/* ── My Reservations Tab ─────────────────────────────────── */}
      {activeTab === 'reservations' && (
        <div role="tabpanel" id="tabpanel-reservations" aria-labelledby="tab-reservations">
          {loadingBookings && (
            <div className="text-center py-12">
              <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose mx-auto mb-2" />
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('roomBooking.loadingYourReservations', 'Loading your reservations...')}</p>
            </div>
          )}

          {!loadingBookings && bookings.length === 0 && (
            <div className="bg-earth-50 dark:bg-earth-800/20 rounded-xl p-8 text-center border border-lsc-border dark:border-earth-700">
              <Calendar className="w-12 h-12 text-earth-600 mx-auto mb-4 opacity-50" />
              <p className="text-lsc-dark dark:text-lsc-cream font-medium">{t('roomBooking.noReservationsYet', 'No reservations yet')}</p>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm mt-1">{t('roomBooking.bookRoomToSeeReservationsHere', 'Book a room to see your reservations here.')}</p>
              <button
                onClick={() => setActiveTab('book')}
                className="mt-4 px-6 py-2 bg-lsc-rose text-white font-semibold rounded-lg hover:bg-lsc-rose/90 transition"
              >
                {t('roomBooking.bookARoom', 'Book a Room')}
              </button>
            </div>
          )}

          {!loadingBookings && bookings.length > 0 && (
            <div className="space-y-4">
              {bookings.map(booking => (
                <div
                  key={booking.id}
                  className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 border border-lsc-border dark:border-earth-700"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2">
                        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream truncate" title={booking.room_name || `Room #${booking.room_id}`}>
                          {booking.room_name || `Room #${booking.room_id}`}
                        </h3>
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_STYLES[booking.status] || 'bg-earth-100 text-earth-600'}`}>
                          {STATUS_LABELS[booking.status] || booking.status}
                        </span>
                      </div>
                      <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 space-y-1">
                        <p>
                          <Clock className="w-3.5 h-3.5 inline mr-1" />
                          {formatDateTime(booking.start_time)} — {formatSlotTime(booking.end_time)}
                        </p>
                        {booking.purpose && (
                          <p className="truncate" title={t('roomBooking.purposeLabel', 'Purpose: {{purpose}}').replace('{{purpose}}', booking.purpose)}>{t('roomBooking.purposeLabel', 'Purpose: {{purpose}}').replace('{{purpose}}', booking.purpose)}</p>
                        )}
                        {booking.attendee_count > 1 && (
                          <p>
                            <Users className="w-3.5 h-3.5 inline mr-1" />
                            {t('roomBooking.peopleCount', '{{count}} people').replace('{{count}}', String(booking.attendee_count))}
                          </p>
                        )}
                        {booking.rejection_reason && (
                          <p className="text-status-danger-600 dark:text-status-danger-400">
                            {t('roomBooking.rejectionReasonLabel', 'Reason: {{reason}}').replace('{{reason}}', booking.rejection_reason)}
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="flex gap-2 flex-shrink-0">
                      {canCheckIn(booking) && (
                        <button
                          onClick={() => handleCheckIn(booking.id)}
                          disabled={checkingInId === booking.id}
                          className="px-3 py-1.5 bg-status-success-600 text-white text-sm font-medium rounded-lg hover:bg-status-success-700 disabled:opacity-50 transition flex items-center gap-1"
                        >
                          {checkingInId === booking.id ? (
                            <Loader2 className="w-3.5 h-3.5 motion-safe:animate-spin" />
                          ) : (
                            <LogIn className="w-3.5 h-3.5" />
                          )}
                          {t('roomBooking.checkIn', 'Check In')}
                        </button>
                      )}
                      {canCancel(booking) && (
                        <button
                          onClick={() => {
                            setSelectedRoom(booking.room_id)
                            setActiveTab('book')
                            toast(t('roomBooking.rescheduleToast', 'Select a new date and time. Your current reservation remains active until you cancel it.'), { duration: 5000 })
                          }}
                          className="px-3 py-1.5 border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream text-sm font-medium rounded-lg hover:bg-earth-50 dark:hover:bg-earth-700/50 transition flex items-center gap-1"
                        >
                          <RotateCcw className="w-3.5 h-3.5" />
                          {t('roomBooking.reschedule', 'Reschedule')}
                        </button>
                      )}
                      {canCancel(booking) && (
                        <button
                          onClick={() => handleCancel(booking.id)}
                          disabled={cancellingId === booking.id}
                          className="px-3 py-1.5 border border-status-danger-300 dark:border-status-danger-700 text-status-danger-600 dark:text-status-danger-400 text-sm font-medium rounded-lg hover:bg-status-danger-50 dark:hover:bg-status-danger-900/20 disabled:opacity-50 transition flex items-center gap-1"
                        >
                          {cancellingId === booking.id ? (
                            <Loader2 className="w-3.5 h-3.5 motion-safe:animate-spin" />
                          ) : (
                            <X className="w-3.5 h-3.5" />
                          )}
                          {t('common.cancel', 'Cancel')}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Book a Room Tab ──────────────────────────────────────── */}
      {activeTab === 'book' && (
        <div role="tabpanel" id="tabpanel-book" aria-labelledby="tab-book">
          {/* Loading / Error states */}
          {roomsLoading && (
            <div className="text-center py-12">
              <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose mx-auto mb-2" />
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('roomBooking.loadingAvailableRooms', 'Loading available rooms...')}</p>
            </div>
          )}

          {roomsError && !roomsLoading && (
            <div className="bg-status-danger-50 dark:bg-status-danger-900/20 rounded-xl p-4 border border-status-danger-200 dark:border-status-danger-900/30 mb-6 flex items-center justify-between">
              <span className="text-status-danger-700 dark:text-status-danger-300 text-sm">{roomsError}</span>
              <button
                onClick={() => fetchRooms()}
                className="text-sm font-medium text-lsc-rose hover:underline ml-4 shrink-0"
              >
                {t('states.tryAgain')}
              </button>
            </div>
          )}

          {!roomsLoading && !roomsError && rooms.length === 0 && (
            <div className="bg-earth-50 dark:bg-earth-800/20 rounded-xl p-8 text-center border border-lsc-border dark:border-earth-700">
              <Calendar className="w-12 h-12 text-earth-600 mx-auto mb-4 opacity-50" />
              <p className="text-lsc-dark dark:text-lsc-cream font-medium">{t('roomBooking.noRoomsAvailableAtThis')}</p>
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm mt-1">{t('roomBooking.pleaseCheckBackLaterOr')}</p>
            </div>
          )}

          {!roomsLoading && rooms.length > 0 && (
            <RoomBookingForm
              rooms={rooms}
              filteredRooms={filteredRooms}
              selectedRoom={selectedRoom}
              setSelectedRoom={setSelectedRoom}
              selectedDate={selectedDate}
              setSelectedDate={setSelectedDate}
              selectedSlot={selectedSlot}
              setSelectedSlot={setSelectedSlot}
              selectedStartTime={selectedStartTime}
              setSelectedStartTime={setSelectedStartTime}
              selectedDuration={selectedDuration}
              setSelectedDuration={setSelectedDuration}
              guestCount={guestCount}
              setGuestCount={setGuestCount}
              purpose={purpose}
              setPurpose={setPurpose}
              name={name}
              setName={setName}
              email={email}
              setEmail={setEmail}
              phone={phone}
              setPhone={setPhone}
              typeFilter={typeFilter}
              setTypeFilter={setTypeFilter}
              hideApprovalRequired={hideApprovalRequired}
              setHideApprovalRequired={setHideApprovalRequired}
              availability={availability}
              loadingAvailability={loadingAvailability}
              availabilityError={availabilityError}
              setAvailabilityError={setAvailabilityError}
              setRetryAvailabilityKey={setRetryAvailabilityKey}
              dayAvailabilityByRoom={dayAvailabilityByRoom}
              loadingDayAvailability={loadingDayAvailability}
              selectedRoomData={selectedRoomData}
              handleSubmit={handleSubmit}
              submitting={submitting}
              formError={formError}
              formErrorRef={formErrorRef}
              nameRef={nameRef}
              emailRef={emailRef}
              nameInvalid={nameInvalid}
              setNameInvalid={setNameInvalid}
              emailInvalid={emailInvalid}
              setEmailInvalid={setEmailInvalid}
            />
          )}


          {/* Questions */}
          <div className="mt-12 p-6 bg-lsc-cream/30 dark:bg-lsc-dark/30 rounded-xl border border-lsc-border dark:border-earth-700">
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3 flex items-center gap-2">
              <AlertCircle className="w-5 h-5" aria-hidden="true" />
              {t('roomBooking.questionsHeading', 'Questions about room reservations?')}
            </h3>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
              {t('roomBooking.contactPrefix', 'Contact us at')} <a href={`mailto:${branding.contact_email}`} className="text-lsc-rose hover:underline font-semibold">{branding.contact_email}</a> {t('roomBooking.contactSuffix', 'for help with room reservations.')}
            </p>
            <a href="/contact" className="text-lsc-rose hover:text-lsc-rose/80 font-semibold">
              {t('roomBooking.contactUsLink', 'Contact us')} &rarr;
            </a>
          </div>
        </div>
      )}
    </PageContainer>
  )
}
