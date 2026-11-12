/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect, useMemo, useId } from 'react'
import { useTranslation} from '../i18n/I18nContext'
import toast from 'react-hot-toast'
import { fetchApi } from '@/api/fetchApi'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import { getCurrentLocale } from '@/i18n'

// ============================================================================
// Type Definitions
// ============================================================================

interface School {
  id: number
  name: string
  address: string
  city: string
  state: string
  partnership_tier: string
}

interface ConsultationSlot {
  id: number
  title: string
  librarian_id: number
  description: string
  consultation_type: string
  scheduled_date: string
  start_time: string
  end_time: string
  duration_minutes: number
  current_participants: number
  max_participants: number
}

interface UserRegistration {
  attendee_id: number
  slot_id: number
  title: string
  librarian_id: number
  description: string
  consultation_type: string
  scheduled_date: string
  start_time: string
  end_time: string
  duration_minutes: number
  current_participants: number
  max_participants: number
  registered_at: string
}

// ============================================================================
// Sub-Component: ConsultationCalendar
// ============================================================================

interface ConsultationCalendarProps {
  selectedDate: Date
  onDateChange: (date: Date) => void
  highlightedDates: string[]
}

function ConsultationCalendar({ selectedDate, onDateChange, highlightedDates }: ConsultationCalendarProps) {
  const { t } = useTranslation()
  const [currentMonth, setCurrentMonth] = useState(selectedDate)

  const daysInMonth = (date: Date) => {
    return new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate()
  }

  const firstDayOfMonth = (date: Date) => {
    return new Date(date.getFullYear(), date.getMonth(), 1).getDay()
  }

  const monthDays = Array.from({ length: daysInMonth(currentMonth) }, (_, i) => i + 1)
  const emptyDays = Array.from({ length: firstDayOfMonth(currentMonth) }, () => 0)
  const allDays = [...emptyDays, ...monthDays]

  const isDateHighlighted = (day: number) => {
    if (day === 0) return false
    const dateStr = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), day)
      .toISOString()
      .split('T')[0] ?? ''
    return highlightedDates.includes(dateStr)
  }

  const isToday = (day: number) => {
    if (day === 0) return false
    const today = new Date()
    return (
      day === today.getDate() &&
      currentMonth.getMonth() === today.getMonth() &&
      currentMonth.getFullYear() === today.getFullYear()
    )
  }

  const handlePrevMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1))
  }

  const handleNextMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1))
  }

  const handleDayClick = (day: number) => {
    if (day > 0) {
      onDateChange(new Date(currentMonth.getFullYear(), currentMonth.getMonth(), day))
    }
  }

  const monthName = currentMonth.toLocaleString(getCurrentLocale(), { month: 'long', year: 'numeric' })
  const weekDays = [
    t('librarianConsultation.weekdaySun', 'Sun'),
    t('librarianConsultation.weekdayMon', 'Mon'),
    t('librarianConsultation.weekdayTue', 'Tue'),
    t('librarianConsultation.weekdayWed', 'Wed'),
    t('librarianConsultation.weekdayThu', 'Thu'),
    t('librarianConsultation.weekdayFri', 'Fri'),
    t('librarianConsultation.weekdaySat', 'Sat'),
  ]

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream">{monthName}</h2>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handlePrevMonth}
            aria-label={t('librarianConsultation.previousMonth', 'Previous month')}
            className="min-h-[44px] min-w-[44px] px-3 py-2 bg-earth-100 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg hover:bg-earth-200 dark:hover:bg-earth-600 transition focus:outline-none focus-visible:ring-2 focus-visible:ring-earth-600 focus-visible:ring-offset-2"
          >
            {t('librarianConsultation.prev', 'Prev')}
          </button>
          <button
            type="button"
            onClick={handleNextMonth}
            aria-label={t('librarianConsultation.nextMonth', 'Next month')}
            className="min-h-[44px] min-w-[44px] px-3 py-2 bg-earth-100 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg hover:bg-earth-200 dark:hover:bg-earth-600 transition focus:outline-none focus-visible:ring-2 focus-visible:ring-earth-600 focus-visible:ring-offset-2"
          >
            {t('librarianConsultation.next', 'Next')}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-7 gap-1 mb-4" aria-hidden="true">
        {weekDays.map((day) => (
          <div key={day} className="text-center text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 p-2">
            {day}
          </div>
        ))}
      </div>

      <div className="grid grid-cols-7 gap-1">
        {allDays.map((day, idx) => {
          if (day === 0) {
            return <div key={idx} aria-hidden="true" className="min-h-[44px]" />
          }
          const dayDate = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), day)
          const dayLabel = dayDate.toLocaleDateString(getCurrentLocale(), { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })
          const highlighted = isDateHighlighted(day)
          return (
            <button
              type="button"
              key={idx}
              onClick={() => handleDayClick(day)}
              aria-label={highlighted ? t('librarianConsultation.dayLabelConsultationsAvailable', { day: dayLabel }) : dayLabel}
              aria-pressed={selectedDate.toDateString() === dayDate.toDateString()}
              className={`min-h-[44px] min-w-[44px] p-2 rounded-lg text-sm font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-earth-600 focus-visible:ring-offset-2 ${
                highlighted
                  ? 'bg-status-success-500 text-white hover:bg-status-success-600'
                  : isToday(day)
                    ? 'border-2 border-earth-600 text-lsc-dark dark:text-lsc-cream dark:border-earth-400'
                    : 'bg-earth-100 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-earth-200 dark:hover:bg-earth-600'
              }`}
            >
              {day}
            </button>
          )
        })}
      </div>
    </div>
  )
}

// ============================================================================
// Sub-Component: SlotCard
// ============================================================================

interface SlotCardProps {
  slot: ConsultationSlot
  onBook: (slot: ConsultationSlot) => void
  canBook: boolean
}

function SlotCard({ slot, onBook, canBook }: SlotCardProps) {
  const { t } = useTranslation()
  const spotsLeft = slot.max_participants - slot.current_participants
  const isFull = spotsLeft <= 0

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString(getCurrentLocale(), {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
    })
  }

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-6 hover:shadow-lg transition border-l-4 border-earth-600 dark:border-earth-400">
      <h3 className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream mb-3">{slot.title}</h3>

      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4 line-clamp-2" title={slot.description}>{slot.description}</p>

      <div className="space-y-2 mb-6">
        <div className="flex justify-between items-start">
          <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('librarianConsultation.typeLabel', 'Type')}</span>
          <span className="font-semibold text-lsc-dark dark:text-lsc-cream bg-earth-100 dark:bg-earth-700 px-2 py-1 rounded text-xs">
            {slot.consultation_type}
          </span>
        </div>

        <div className="flex justify-between items-start">
          <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('librarianConsultation.dateLabel', 'Date')}</span>
          <span className="font-semibold text-lsc-dark dark:text-lsc-cream">{formatDate(slot.scheduled_date)}</span>
        </div>

        <div className="flex justify-between items-start">
          <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('librarianConsultation.timeLabel', 'Time')}</span>
          <span className="font-semibold text-lsc-dark dark:text-lsc-cream">
            {slot.start_time} - {slot.end_time}
          </span>
        </div>

        <div className="flex justify-between items-start">
          <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('librarianConsultation.durationLabel', 'Duration')}</span>
          <span className="font-semibold text-lsc-dark dark:text-lsc-cream">{t('librarianConsultation.durationMinutes', { count: slot.duration_minutes })}</span>
        </div>

        <div className="flex justify-between items-start">
          <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('librarianConsultation.availabilityLabel', 'Availability')}</span>
          <div className="flex items-center gap-2">
            <div className="w-32 h-2 bg-earth-200 dark:bg-earth-700 rounded-full overflow-hidden">
              <div
                className={`h-full transition ${isFull ? 'bg-status-danger-500' : 'bg-status-success-500'}`}
                style={{ width: `${Math.min((slot.current_participants / slot.max_participants) * 100, 100)}%` }}
              ></div>
            </div>
            <span className={`text-xs font-semibold ${isFull ? 'text-status-danger-600 dark:text-status-danger-400' : 'text-status-success-600 dark:text-status-success-400'}`}>
              {spotsLeft > 0 ? t('librarianConsultation.spotsLeftCount', { count: spotsLeft }) : t('librarianConsultation.full', 'Full')}
            </span>
          </div>
        </div>
      </div>

      <button
        onClick={() => onBook(slot)}
        disabled={!canBook || isFull}
        className={`w-full px-4 py-2 rounded-lg font-medium transition ${
          canBook && !isFull
            ? 'bg-earth-600 text-white hover:bg-earth-700'
            : 'bg-earth-200 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 cursor-not-allowed'
        }`}
      >
        {isFull ? t('librarianConsultation.slotFull', 'Slot Full') : canBook ? t('librarianConsultation.bookConsultation', 'Book Consultation') : t('librarianConsultation.signInToBook', 'Sign In to Book')}
      </button>
    </div>
  )
}

// ============================================================================
// Sub-Component: RegistrationRow
// ============================================================================

interface RegistrationRowProps {
  registration: UserRegistration
  onCancel: (registrationId: number, slotId: number) => void
}

function RegistrationRow({ registration, onCancel }: RegistrationRowProps) {
  const { t } = useTranslation()
  const [showConfirmation, setShowConfirmation] = useState(false)

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString(getCurrentLocale(), {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
    })
  }

  const formatTime = (timeStr: string) => {
    if (!timeStr) return ''
    const [hours = '0', minutes] = timeStr.split(':')
    const hour = parseInt(hours)
    const ampm = hour >= 12 ? 'PM' : 'AM'
    const displayHour = hour % 12 || 12
    return `${displayHour}:${minutes} ${ampm}`
  }

  const handleConfirmCancel = () => {
    onCancel(registration.attendee_id, registration.slot_id)
    setShowConfirmation(false)
  }

  return (
    <>
      <div className="p-4 border border-lsc-border dark:border-earth-700 rounded-lg hover:bg-earth-50 dark:hover:bg-earth-700 transition">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 items-center mb-3">
          <div>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wide">{t('librarianConsultation.titleLabel', 'Title')}</p>
            <p className="font-semibold text-lsc-dark dark:text-lsc-cream">{registration.title}</p>
          </div>

          <div>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wide">{t('librarianConsultation.dateAndTimeLabel', 'Date & Time')}</p>
            <p className="font-semibold text-lsc-dark dark:text-lsc-cream">
              {formatDate(registration.scheduled_date)} @ {formatTime(registration.start_time)}
            </p>
          </div>

          <div>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wide">{t('librarianConsultation.typeLabel', 'Type')}</p>
            <p className="font-semibold text-lsc-dark dark:text-lsc-cream">{registration.consultation_type}</p>
          </div>

          <div>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wide">{t('librarianConsultation.durationLabel', 'Duration')}</p>
            <p className="font-semibold text-lsc-dark dark:text-lsc-cream">{t('librarianConsultation.durationMinutes', { count: registration.duration_minutes })}</p>
          </div>

          <div className="text-right">
            <button
              onClick={() => setShowConfirmation(true)}
              className="px-4 py-2 text-status-danger-600 dark:text-status-danger-400 hover:bg-status-danger-50 dark:hover:bg-status-danger-900/20 rounded-lg transition text-sm font-medium"
            >
              {t('librarianConsultation.cancelBooking', 'Cancel Booking')}
            </button>
          </div>
        </div>

        {registration.description && (
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 italic">{registration.description}</p>
        )}
      </div>

      {showConfirmation && (
        <ModalBackdrop onClose={() => setShowConfirmation(false)} title={t('librarianConsultation.cancelBookingQuestion', 'Cancel Booking?')}>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full p-8">
            <h3 className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream mb-4">{t('librarianConsultation.cancelBookingQuestion', 'Cancel Booking?')}</h3>

            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-6">
              {t('librarianConsultation.areYouSureYouWant', 'Are you sure you want to cancel this consultation with')} <strong>{registration.title}</strong> {t('librarianConsultation.onDatePrefix', 'on')}{' '}
              <strong>{formatDate(registration.scheduled_date)}</strong>?
            </p>

            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-6 italic">
              {t('librarianConsultation.youCanAlwaysBookAnother', 'You can always book another consultation slot if you change your mind.')}
            </p>

            <div className="flex gap-4">
              <button
                onClick={() => setShowConfirmation(false)}
                className="flex-1 px-4 py-2 bg-earth-200 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg hover:bg-earth-300 dark:hover:bg-earth-600 transition font-medium"
              >
                {t('librarianConsultation.keepBooking', 'Keep Booking')}
              </button>
              <button
                onClick={handleConfirmCancel}
                className="flex-1 px-4 py-2 bg-status-danger-600 text-white rounded-lg hover:bg-status-danger-700 transition font-medium"
              >
                {t('librarianConsultation.yesCancel', 'Yes, Cancel')}
              </button>
            </div>
          </div>
        </ModalBackdrop>
      )}
    </>
  )
}

// ============================================================================
// Sub-Component: BookingConfirmationModal
// ============================================================================

interface BookingConfirmationModalProps {
  slot: ConsultationSlot | null
  isOpen: boolean
  onConfirm: (slot: ConsultationSlot) => Promise<void>
  onClose: () => void
  isLoading: boolean
}

function BookingConfirmationModal({ slot, isOpen, onConfirm, onClose, isLoading }: BookingConfirmationModalProps) {
  const { t } = useTranslation()
  const [notes, setNotes] = useState('')
  const notesId = useId()

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString(getCurrentLocale(), {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
    })
  }

  const formatTime = (timeStr: string) => {
    if (!timeStr) return ''
    const [hours = '0', minutes] = timeStr.split(':')
    const hour = parseInt(hours)
    const ampm = hour >= 12 ? 'PM' : 'AM'
    const displayHour = hour % 12 || 12
    return `${displayHour}:${minutes} ${ampm}`
  }

  const handleConfirm = async () => {
    if (slot) {
      await onConfirm(slot)
      setNotes('')
    }
  }

  const handleClose = () => {
    setNotes('')
    onClose()
  }

  if (!isOpen || !slot) return null

  return (
    <ModalBackdrop onClose={handleClose} title={t('librarianConsultation.confirmBooking', 'Confirm Booking')}>
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full p-8">
        <h2 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-6">{t('librarianConsultation.confirmBooking', 'Confirm Booking')}</h2>

        <div className="space-y-4 mb-6 bg-earth-50 dark:bg-earth-700/50 p-4 rounded-lg">
          <div>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wide">{t('librarianConsultation.consultationLabel', 'Consultation')}</p>
            <p className="font-semibold text-lsc-dark dark:text-lsc-cream">{slot.title}</p>
          </div>

          <div>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wide">{t('librarianConsultation.dateAndTimeLabel', 'Date & Time')}</p>
            <p className="font-semibold text-lsc-dark dark:text-lsc-cream">
              {t('librarianConsultation.dateAtTime', { date: formatDate(slot.scheduled_date), time: formatTime(slot.start_time) })}
            </p>
          </div>

          <div>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wide">{t('librarianConsultation.typeLabel', 'Type')}</p>
            <p className="font-semibold text-lsc-dark dark:text-lsc-cream">{slot.consultation_type}</p>
          </div>

          <div>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wide">{t('librarianConsultation.durationLabel', 'Duration')}</p>
            <p className="font-semibold text-lsc-dark dark:text-lsc-cream">{t('librarianConsultation.durationMinutesFull', { count: slot.duration_minutes })}</p>
          </div>
        </div>

        <div className="mb-6">
          <label htmlFor={notesId} className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
            {t('librarianConsultation.notesOptional', 'Notes (optional)')}
          </label>
          <textarea
            id={notesId}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder={t('librarianConsultation.anySpecificTopicsYouD')}
            rows={4}
            className="w-full px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg dark:bg-earth-700 dark:text-earth-100 placeholder-earth-500 dark:placeholder-earth-400 focus:outline-none focus:ring-2 focus:ring-earth-600"
          />
        </div>

        <div className="flex gap-4">
          <button
            onClick={handleClose}
            disabled={isLoading}
            className="flex-1 px-4 py-2 bg-earth-200 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg hover:bg-earth-300 dark:hover:bg-earth-600 transition disabled:opacity-50"
          >
            {t('librarianConsultation.cancel', 'Cancel')}
          </button>
          <button
            onClick={handleConfirm}
            disabled={isLoading}
            className="flex-1 px-4 py-2 bg-earth-600 text-white rounded-lg hover:bg-earth-700 transition disabled:opacity-50 font-medium"
          >
            {isLoading ? t('librarianConsultation.bookingEllipsis', 'Booking...') : t('librarianConsultation.confirmBooking', 'Confirm Booking')}
          </button>
        </div>
      </div>
    </ModalBackdrop>
  )
}

// ============================================================================
// Main Component: LibrarianConsultationPage
// ============================================================================

export default function LibrarianConsultationPage() {
  const { t } = useTranslation()

  // State Management
  const [loading, setLoading] = useState(true)
  const [schools, setSchools] = useState<School[]>([])
  const [selectedSchool, setSelectedSchool] = useState<School | null>(null)
  const [allSlots, setAllSlots] = useState<ConsultationSlot[]>([])
  const [userRegistrations, setUserRegistrations] = useState<UserRegistration[]>([])
  const [selectedDate, setSelectedDate] = useState(new Date())
  const [view, setView] = useState<'available' | 'booked'>('available')
  const [filterType, setFilterType] = useState('')
  const [selectedSlotForBooking, setSelectedSlotForBooking] = useState<ConsultationSlot | null>(null)
  const [showBookingModal, setShowBookingModal] = useState(false)
  const [isBookingLoading, setIsBookingLoading] = useState(false)
  const [isLoggedIn, setIsLoggedIn] = useState(true)

  // API Functions
  const checkAuth = async () => {
    try {
      await fetchApi('/auth/me')
      setIsLoggedIn(true)
    } catch {
      setIsLoggedIn(false)
    }
  }


  const fetchSchools = async () => {
    try {
      const data = await fetchApi('/school-partnerships/schools')
      const list = Array.isArray(data) ? data : (data?.schools ?? [])
      setSchools(list)
      if (list.length > 0) {
        setSelectedSchool(list[0])
      }
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('librarianConsultation.failedToLoadSchools'))
    }
  }


  // Initial load: fetch schools
  useEffect(() => {
    fetchSchools()
    checkAuth()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const fetchUserRegistrations = async () => {
    if (!selectedSchool || !isLoggedIn) return
    try {
      const data = await fetchApi(`/school-partnerships/consultation-slots/${selectedSchool.id}/my-registrations`)
      setUserRegistrations(data.registrations || [])
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    }
  }


  const fetchSlots = async () => {
    if (!selectedSchool) return
    setLoading(true)
    try {
      const data: ConsultationSlot[] = await fetchApi(`/school-partnerships/consultation-slots/${selectedSchool.id}`)
      setAllSlots(data)
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('librarianConsultation.failedToLoadConsultationSlots'))
    } finally {
      setLoading(false)
    }
  }


  // When school changes, fetch slots and registrations
  useEffect(() => {
    if (selectedSchool) {
      fetchSlots()
      fetchUserRegistrations()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedSchool])

  const handleBookSlot = async (slot: ConsultationSlot) => {
    if (!isLoggedIn) {
      toast.error(t('librarianConsultation.pleaseSignInToBook'))
      return
    }

    setSelectedSlotForBooking(slot)
    setShowBookingModal(true)
  }

  const handleConfirmBooking = async (slot: ConsultationSlot) => {
    setIsBookingLoading(true)
    try {
      await fetchApi(`/school-partnerships/consultation-slots/${slot.id}/register`, {
        method: 'POST',
      })
      toast.success(t('toast.librarianConsultation.consultationBookedSuccessfully'))
      setShowBookingModal(false)
      setSelectedSlotForBooking(null)
      await fetchSlots()
      await fetchUserRegistrations()
    } catch (error) {
      // fetchApi throws { status, message } for non-ok responses; surface 400
      // detail to the user, fall back to generic error otherwise.
      const err = error as { status?: number; message?: string }
      if (err?.status === 400) {
        toast.error(err.message || t('toast.librarianConsultation.couldNotBookConsultation'))
      } else {
        Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
        toast.error(t('librarianConsultation.failedToBookConsultation'))
      }
    } finally {
      setIsBookingLoading(false)
    }
  }

  const handleCancelRegistration = async (_attendeeId: number, slotId: number) => {
    try {
      await fetchApi(`/school-partnerships/consultation-slots/${slotId}/unregister`, {
        method: 'DELETE',
      })
      toast.success(t('toast.librarianConsultation.bookingCancelledSuccessfully'))
      await fetchSlots()
      await fetchUserRegistrations()
    } catch (error) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('librarianConsultation.failedToCancelBooking'))
    }
  }

  // Computed Values
  const consultationTypes = useMemo(() => {
    return [...new Set(allSlots.map((s) => s.consultation_type))]
  }, [allSlots])

  const highlightedDates = useMemo(() => {
    return allSlots
      .map((slot) => slot.scheduled_date.split('T')[0] ?? '')
      .filter((date, idx, arr) => date !== '' && arr.indexOf(date) === idx)
  }, [allSlots])

  const filteredSlots = useMemo(() => {
    const dateStr = selectedDate.toISOString().split('T')[0] ?? ''
    return allSlots.filter((slot) => {
      const slotDate = slot.scheduled_date.split('T')[0] ?? ''
      const matchesDate = slotDate === dateStr
      const matchesType = filterType === '' || slot.consultation_type === filterType
      return matchesDate && matchesType
    })
  }, [allSlots, selectedDate, filterType])

  const registeredSlotIds = useMemo(() => {
    return new Set(userRegistrations.map((r) => r.slot_id))
  }, [userRegistrations])

  return (
    <div className="min-h-screen bg-lsc-cream dark:bg-earth-900 p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="font-serif text-4xl font-bold text-lsc-dark dark:text-lsc-cream mb-2">{t('librarianConsultation.librarianConsultations', 'Librarian Consultations')}</h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            {t('librarianConsultation.scheduleOneononeConsultationsWithOur', 'Schedule one-on-one consultations with our expert librarians to discuss reading programs, curriculum integration, and more.')}
          </p>
        </div>

        {/* School Selector */}
        {schools.length > 0 && (
          <fieldset className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-6 mb-8">
            <legend className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-3 px-1">
              {t('librarianConsultation.selectYourSchool', 'Select Your School')}
            </legend>
            <div role="radiogroup" aria-label={t('librarianConsultation.selectYourSchoolAria', 'Select your school')} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
              {schools.map((school) => (
                <button
                  type="button"
                  role="radio"
                  aria-checked={selectedSchool?.id === school.id}
                  key={school.id}
                  onClick={() => setSelectedSchool(school)}
                  className={`min-h-[44px] p-4 rounded-lg text-left transition border-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-earth-600 focus-visible:ring-offset-2 ${
                    selectedSchool?.id === school.id
                      ? 'bg-earth-600 text-white border-earth-700'
                      : 'bg-earth-50 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream border-lsc-border dark:border-earth-700 hover:border-earth-400 dark:hover:border-earth-500'
                  }`}
                >
                  <p className="font-semibold">{school.name}</p>
                  <p className="text-xs opacity-75">
                    {school.city}, {school.state}
                  </p>
                </button>
              ))}
            </div>
          </fieldset>
        )}

        {selectedSchool && (
          <>
            {/* View Toggle */}
            <div role="group" aria-label={t('librarianConsultation.consultationView', 'Consultation view')} className="flex gap-4 mb-8">
              <button
                type="button"
                onClick={() => setView('available')}
                aria-pressed={view === 'available'}
                className={`min-h-[44px] px-6 py-3 rounded-lg font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-earth-600 focus-visible:ring-offset-2 ${
                  view === 'available'
                    ? 'bg-earth-600 text-white shadow-lg'
                    : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream border border-lsc-border dark:border-earth-700 hover:border-earth-400 dark:hover:border-earth-500'
                }`}
              >
                {t('librarianConsultation.availableSlotsCount', { count: filteredSlots.length })}
              </button>
              <button
                type="button"
                onClick={() => setView('booked')}
                aria-pressed={view === 'booked'}
                className={`min-h-[44px] px-6 py-3 rounded-lg font-medium transition relative focus:outline-none focus-visible:ring-2 focus-visible:ring-earth-600 focus-visible:ring-offset-2 ${
                  view === 'booked'
                    ? 'bg-earth-600 text-white shadow-lg'
                    : 'bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream border border-lsc-border dark:border-earth-700 hover:border-earth-400 dark:hover:border-earth-500'
                }`}
              >
                {t('librarianConsultation.myBookings', 'My Bookings')}
                {userRegistrations.length > 0 && (
                  <span aria-label={t('librarianConsultation.bookingsCount', { count: userRegistrations.length })} className="absolute -top-2 -right-2 bg-status-danger-500 text-white text-xs font-bold rounded-full h-6 w-6 flex items-center justify-center">
                    {userRegistrations.length}
                  </span>
                )}
              </button>
            </div>

            {/* Available Slots View */}
            {view === 'available' && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Calendar and Filter */}
                <div className="lg:col-span-1 space-y-6">
                  <ConsultationCalendar
                    selectedDate={selectedDate}
                    onDateChange={setSelectedDate}
                    highlightedDates={highlightedDates}
                  />

                  {consultationTypes.length > 0 && (
                    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-6">
                      <h2 className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream mb-4">{t('librarianConsultation.filterByType', 'Filter by Type')}</h2>
                      <div role="group" aria-label={t('librarianConsultation.filterConsultationsByType', 'Filter consultations by type')} className="space-y-2">
                        <button
                          type="button"
                          onClick={() => setFilterType('')}
                          aria-pressed={filterType === ''}
                          className={`min-h-[44px] w-full text-left px-4 py-2 rounded-lg transition focus:outline-none focus-visible:ring-2 focus-visible:ring-earth-600 focus-visible:ring-offset-2 ${
                            filterType === ''
                              ? 'bg-earth-600 text-white'
                              : 'bg-earth-100 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-earth-200 dark:hover:bg-earth-600'
                          }`}
                        >
                          {t('librarianConsultation.allTypes', 'All Types')}
                        </button>
                        {consultationTypes.map((type) => (
                          <button
                            type="button"
                            key={type}
                            onClick={() => setFilterType(type)}
                            aria-pressed={filterType === type}
                            className={`min-h-[44px] w-full text-left px-4 py-2 rounded-lg transition focus:outline-none focus-visible:ring-2 focus-visible:ring-earth-600 focus-visible:ring-offset-2 ${
                              filterType === type
                                ? 'bg-earth-600 text-white'
                                : 'bg-earth-100 dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-earth-200 dark:hover:bg-earth-600'
                            }`}
                          >
                            {type}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Slots Grid */}
                <div className="lg:col-span-2">
                  {loading ? (
                    <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
                      <div className="inline-block motion-safe:animate-spin mb-4">{t('librarianConsultation.loadingEllipsis', 'Loading...')}</div>
                      <p>{t('librarianConsultation.fetchingConsultationSlots', 'Fetching consultation slots...')}</p>
                    </div>
                  ) : filteredSlots.length === 0 ? (
                    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-12 text-center">
                      <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                        {t('librarianConsultation.noAvailableConsultationsOnDate', { date: selectedDate.toLocaleDateString(getCurrentLocale()) })}
                      </p>
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        {t('librarianConsultation.trySelectingADifferentDate', 'Try selecting a different date or consultation type.')}
                      </p>
                    </div>
                  ) : (
                    <div className="grid gap-6">
                      {filteredSlots.map((slot) => (
                        <SlotCard
                          key={slot.id}
                          slot={slot}
                          onBook={handleBookSlot}
                          canBook={isLoggedIn && !registeredSlotIds.has(slot.id)}
                        />
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* My Bookings View */}
            {view === 'booked' && (
              <div>
                {!isLoggedIn ? (
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-12 text-center">
                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">{t('librarianConsultation.pleaseSignInToView')}</p>
                  </div>
                ) : userRegistrations.length === 0 ? (
                  <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-12 text-center">
                    <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">{t('librarianConsultation.youHavenTBookedAny')}</p>
                    <button
                      onClick={() => setView('available')}
                      className="px-6 py-2 bg-earth-600 text-white rounded-lg hover:bg-earth-700 transition"
                    >
                      {t('librarianConsultation.browseAvailableSlots', 'Browse Available Slots')}
                    </button>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {userRegistrations.map((registration) => (
                      <RegistrationRow
                        key={registration.attendee_id}
                        registration={registration}
                        onCancel={handleCancelRegistration}
                      />
                    ))}
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>

      {/* Booking Confirmation Modal */}
      <BookingConfirmationModal
        slot={selectedSlotForBooking}
        isOpen={showBookingModal}
        onConfirm={handleConfirmBooking}
        onClose={() => {
          setShowBookingModal(false)
          setSelectedSlotForBooking(null)
        }}
        isLoading={isBookingLoading}
      />
    </div>
  )
}
