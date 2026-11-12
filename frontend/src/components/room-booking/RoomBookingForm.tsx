/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState } from 'react'
import {
  Calendar,
  Clock,
  Users,
  AlertCircle,
  CheckCircle2,
  Loader2,
  Info,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'
import type { Room } from '@/features/rooms/useRoomBookings'
import { useTranslation } from '@/i18n'

export interface AvailabilitySlot {
  start_time: string
  end_time: string
  duration_minutes: number
  max_available_minutes?: number
}

export interface RoomAvailability {
  room_id: number
  room_name: string
  date: string
  available_slots: AvailabilitySlot[]
  reservations: { id: number; start_time: string; end_time: string; status: string }[]
}

const ROOM_TYPE_LABELS: Record<string, string> = {
  study_room: 'Study Room',
  meeting_room: 'Meeting Room',
  computer_lab: 'Computer Lab',
  event_space: 'Event Space',
  makerspace: 'Makerspace',
  workshop: 'Workshop',
  teen_space: 'Teen Space',
  quiet_room: 'Quiet Room',
}

const ROOM_TYPE_KEYS: Record<string, string> = {
  study_room: 'roomBooking.roomType.studyRoom',
  meeting_room: 'roomBooking.roomType.meetingRoom',
  computer_lab: 'roomBooking.roomType.computerLab',
  event_space: 'roomBooking.roomType.eventSpace',
  makerspace: 'roomBooking.roomType.makerspace',
  workshop: 'roomBooking.roomType.workshop',
  teen_space: 'roomBooking.roomType.teenSpace',
  quiet_room: 'roomBooking.roomType.quietRoom',
}

function roomTypeLabel(type: string, t: (key: string, fallback?: string) => string): string {
  const label = ROOM_TYPE_LABELS[type] || type
  const key = ROOM_TYPE_KEYS[type]
  return key ? t(key, label) : label
}

const AMENITY_LABELS: Record<string, string> = {
  children_furniture: "Children's furniture",
  computers: 'Computers',
  craft_supplies: 'Craft supplies',
  display_screen: 'Display screen',
  kitchenette: 'Kitchenette',
  podium: 'Podium',
  power_outlets: 'Power outlets',
  printer: 'Printer',
  projector: 'Projector',
  scanner: 'Scanner',
  screen: 'Screen',
  sound_system: 'Sound system',
  whiteboard: 'Whiteboard',
}

const AMENITY_KEYS: Record<string, string> = {
  children_furniture: 'roomBooking.amenity.childrensFurniture',
  computers: 'roomBooking.amenity.computers',
  craft_supplies: 'roomBooking.amenity.craftSupplies',
  display_screen: 'roomBooking.amenity.displayScreen',
  kitchenette: 'roomBooking.amenity.kitchenette',
  podium: 'roomBooking.amenity.podium',
  power_outlets: 'roomBooking.amenity.powerOutlets',
  printer: 'roomBooking.amenity.printer',
  projector: 'roomBooking.amenity.projector',
  scanner: 'roomBooking.amenity.scanner',
  screen: 'roomBooking.amenity.screen',
  sound_system: 'roomBooking.amenity.soundSystem',
  whiteboard: 'roomBooking.amenity.whiteboard',
}

function amenityLabel(value: string, t: (key: string, fallback?: string) => string): string {
  if (AMENITY_LABELS[value]) return t(AMENITY_KEYS[value]!, AMENITY_LABELS[value])
  const words = value.replace(/_/g, ' ').trim()
  return words.charAt(0).toUpperCase() + words.slice(1)
}

function durationToPlainLanguage(minutes: number, t: (key: string, paramsOrFallback?: Record<string, unknown> | string) => string): string {
  if (minutes < 60) return t('roomBooking.durationUpToMinutes', 'up to {{minutes}} minutes').replace('{{minutes}}', String(minutes))
  const hours = Math.floor(minutes / 60)
  const rem = minutes % 60
  if (rem === 0) return t('roomBooking.durationUpToHours', { hours })
  return t('roomBooking.durationUpToHoursMinutes', { hours, minutes: rem })
}

function extractRate(description: string | null): string | null {
  if (!description) return null
  const match = description.match(/Rates?:\s*([^\n]+)/i)
  if (!match || !match[1]) return null
  return match[1].trim().replace(/\.$/, '')
}

function costApprovalSummary(room: Room, t: (key: string, fallback?: string) => string): string {
  const rate = extractRate(room.description)
  const cost = rate ? rate : t('roomBooking.free', 'Free')
  if (room.requires_approval) {
    return `${cost}. ${t('roomBooking.staffApprovesWithinOneBusinessDay', 'Staff approves within 1 business day.')}`
  }
  return `${cost}. ${t('roomBooking.booksInstantlyNoApprovalNeeded', 'Books instantly, no approval needed.')}`
}

function formatSlotTime(isoString: string) {
  return new Date(isoString).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
}

function AmenitiesExpand({ amenities }: { amenities: string[] }) {
  const { t } = useTranslation()
  const [expanded, setExpanded] = useState(false)
  const visible = expanded ? amenities : amenities.slice(0, 4)
  const hiddenCount = amenities.length - 4

  return (
    <div className="flex flex-wrap gap-1 mt-2">
      {visible.map(amenity => (
        <span key={amenity} className="px-2 py-0.5 bg-earth-100 dark:bg-earth-700 rounded text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
          {amenityLabel(amenity, t)}
        </span>
      ))}
      {hiddenCount > 0 && (
        <button
          type="button"
          onClick={e => { e.preventDefault(); e.stopPropagation(); setExpanded(v => !v) }}
          aria-expanded={expanded}
          className="inline-flex items-center gap-0.5 px-2 py-0.5 text-xs text-lsc-rose hover:underline focus-visible:outline-2 focus-visible:outline-lsc-rose rounded"
        >
          {expanded ? (
            <><ChevronUp className="w-3 h-3" aria-hidden="true" />{t('roomBooking.showLess', 'Show less')}</>
          ) : (
            <><ChevronDown className="w-3 h-3" aria-hidden="true" />{t('roomBooking.moreCount', '+{{count}} more').replace('{{count}}', String(hiddenCount))}</>
          )}
        </button>
      )}
    </div>
  )
}

interface RoomBookingFormProps {
  rooms: Room[]
  filteredRooms: Room[]
  selectedRoom: number | null
  setSelectedRoom: (id: number) => void
  selectedDate: string
  setSelectedDate: (d: string) => void
  selectedSlot: AvailabilitySlot | null
  setSelectedSlot: (s: AvailabilitySlot | null) => void
  selectedStartTime: string | null
  setSelectedStartTime: (t: string | null) => void
  selectedDuration: number
  setSelectedDuration: (d: number) => void
  guestCount: string
  setGuestCount: (g: string) => void
  purpose: string
  setPurpose: (p: string) => void
  name: string
  setName: (n: string) => void
  email: string
  setEmail: (e: string) => void
  phone: string
  setPhone: (p: string) => void
  typeFilter: string
  setTypeFilter: (f: string) => void
  hideApprovalRequired: boolean
  setHideApprovalRequired: (h: boolean) => void
  availability: RoomAvailability | null
  loadingAvailability: boolean
  availabilityError: string | null
  setAvailabilityError: (e: string | null) => void
  setRetryAvailabilityKey: React.Dispatch<React.SetStateAction<number>>
  dayAvailabilityByRoom: Record<number, number>
  loadingDayAvailability: boolean
  selectedRoomData: Room | undefined
  handleSubmit: (e: React.FormEvent) => Promise<void>
  submitting: boolean
  formError: string
  formErrorRef: React.RefObject<HTMLDivElement>
  nameRef: React.RefObject<HTMLInputElement>
  emailRef: React.RefObject<HTMLInputElement>
  nameInvalid: boolean
  setNameInvalid: (v: boolean) => void
  emailInvalid: boolean
  setEmailInvalid: (v: boolean) => void
}

export function RoomBookingForm({
  rooms,
  filteredRooms,
  selectedRoom,
  setSelectedRoom,
  selectedDate,
  setSelectedDate,
  selectedSlot,
  setSelectedSlot,
  selectedStartTime,
  setSelectedStartTime,
  selectedDuration,
  setSelectedDuration,
  guestCount,
  setGuestCount,
  purpose,
  setPurpose,
  name,
  setName,
  email,
  setEmail,
  phone,
  setPhone,
  typeFilter,
  setTypeFilter,
  hideApprovalRequired,
  setHideApprovalRequired,
  availability,
  loadingAvailability,
  availabilityError,
  setAvailabilityError,
  setRetryAvailabilityKey,
  dayAvailabilityByRoom,
  loadingDayAvailability,
  selectedRoomData,
  handleSubmit,
  submitting,
  formError,
  formErrorRef,
  nameRef,
  emailRef,
  nameInvalid,
  setNameInvalid,
  emailInvalid,
  setEmailInvalid,
}: RoomBookingFormProps) {
  const { t } = useTranslation()

  return (
    <form onSubmit={handleSubmit} className="space-y-8">
      {/* Required fields legend */}
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
        {t('roomBooking.fieldsMarkedPrefix', 'Fields marked')} <span aria-hidden="true">*</span><span className="sr-only">{t('roomBooking.fieldsMarkedSrOnly', 'with an asterisk')}</span> {t('roomBooking.fieldsMarkedSuffix', 'are required.')}
      </p>

      {/* When do you need a space? (time-first) */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
          <Calendar className="w-5 h-5 inline mr-2 text-lsc-rose" aria-hidden="true" />
          {t('roomBooking.whenDoYouNeedSpace', 'When do you need a space?')}
        </h2>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
          {t('roomBooking.pickDateFirstHint', 'Pick a date first. Each room below shows whether it has open times that day.')}
        </p>
        <label htmlFor="room-date" className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
          {t('roomBooking.dateLabel', 'Date *')}
        </label>
        <input
          type="date"
          id="room-date"
          value={selectedDate}
          onChange={e => setSelectedDate(e.target.value)}
          min={new Date().toISOString().split('T')[0]}
          className="w-full sm:max-w-xs px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
          required
        />
        {selectedDate && loadingDayAvailability && (
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-2 flex items-center gap-2">
            <Loader2 className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" />
            {t('roomBooking.checkingRoomsOpenToday', 'Checking which rooms are open that day...')}
          </p>
        )}
      </div>

      {/* Room Selection */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">{t('roomBooking.chooseARoom', 'Choose a room *')}</h2>
        <div className="flex flex-wrap gap-3 mb-4">
          <label htmlFor="room-type-filter" className="sr-only">{t('roomBooking.filterByRoomType', 'Filter by room type')}</label>
          <select
            id="room-type-filter"
            value={typeFilter}
            onChange={e => setTypeFilter(e.target.value)}
            aria-label={t('roomBooking.filterByRoomType', 'Filter by room type')}
            className="px-3 py-1.5 text-sm rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
          >
            <option value="">{t('roomBooking.allRoomTypes', 'All room types')}</option>
            {[...new Set(rooms.map(r => r.room_type))].map(type => (
              <option key={type} value={type}>{roomTypeLabel(type, t)}</option>
            ))}
          </select>
          <label className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 cursor-pointer">
            <input
              type="checkbox"
              checked={hideApprovalRequired}
              onChange={e => setHideApprovalRequired(e.target.checked)}
              className="rounded"
            />
            {t('roomBooking.noApprovalNeeded', 'No approval needed')}
          </label>
        </div>
        {/* Single-column below sm, two-column above */}
        <div className="grid gap-4 grid-cols-1 sm:grid-cols-2" role="radiogroup" aria-label={t('aria.roomBooking.selectARoom')}>
          {filteredRooms.map(room => {
            const isSelected = selectedRoom === room.id
            const slotCount = dayAvailabilityByRoom[room.id]
            const descNoRate = room.description
              ? room.description.replace(/Rates?:[^\n]*/i, '').trim()
              : null
            return (
            <label
              key={room.id}
              className={`relative block p-4 rounded-lg border-2 cursor-pointer transition focus-within:ring-2 focus-within:ring-lsc-rose focus-within:ring-offset-2 dark:focus-within:ring-offset-earth-900 ${
                isSelected
                  ? 'border-lsc-rose bg-lsc-rose/5'
                  : 'border-lsc-border dark:border-earth-700 hover:border-lsc-rose/50'
              }`}
            >
              {/* Real radio, visually hidden but keyboard- and SR-accessible.
                  The wrapping label makes the whole card the click target. */}
              <input
                type="radio"
                name="room"
                required
                id={`room-${room.id}`}
                value={room.id}
                checked={isSelected}
                onChange={() => setSelectedRoom(room.id)}
                className="sr-only"
              />
              {/* Visible selected indicator */}
              {isSelected && (
                <span className="absolute top-3 right-3 inline-flex items-center gap-1 text-xs font-semibold text-lsc-rose">
                  <CheckCircle2 className="w-4 h-4" aria-hidden="true" />
                  {t('roomBooking.selectedBadge', 'Selected')}
                </span>
              )}
              {room.image_url && (
                <img src={room.image_url} alt="" className="w-full h-32 object-cover rounded-lg mb-3" />
              )}

              {/* Room name + type badge — primary content, full weight */}
              <div className="flex flex-wrap items-center gap-1.5 pr-20">
                <span className="font-semibold text-lsc-dark dark:text-lsc-cream">{room.name}</span>
                {!room.name.toLowerCase().includes((ROOM_TYPE_LABELS[room.room_type] || room.room_type).toLowerCase()) && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70">
                    {roomTypeLabel(room.room_type, t)}
                  </span>
                )}
              </div>

              {/* Use-case description — secondary, normal weight */}
              {descNoRate && (
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{descNoRate}</p>
              )}

              {/* Capacity */}
              <div className="flex items-center gap-2 mt-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                <Users className="w-4 h-4" aria-hidden="true" />
                {t('roomBooking.upToPeople', { count: room.capacity })}
              </div>

              {/* Availability for the chosen date (time-first hint) */}
              {selectedDate && slotCount !== undefined && (
                <p className={`text-sm mt-1 font-medium ${slotCount > 0 ? 'text-status-success-700 dark:text-status-success-300' : 'text-lsc-dark/60 dark:text-lsc-cream/60'}`}>
                  {slotCount > 0
                    ? t('roomBooking.timesOpenOnDate', { count: slotCount })
                    : t('roomBooking.fullyBookedOnDate', 'Fully booked on this date')}
                </p>
              )}

              {/* Cost + approval — secondary weight */}
              <p className="text-sm text-lsc-dark/60 dark:text-lsc-cream/60 mt-2">
                {costApprovalSummary(room, t)}
              </p>

              <p id={`room-${room.id}-hint`} className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                {t('roomBooking.bookDurationAtATime', 'Book {{duration}} at a time').replace('{{duration}}', durationToPlainLanguage(room.max_duration_minutes, t))}
              </p>

              {room.amenities && room.amenities.length > 0 && (
                <AmenitiesExpand amenities={room.amenities} />
              )}
            </label>
            )
          })}
        </div>
      </div>

      {/* Room Amenities */}
      {selectedRoomData?.amenities && selectedRoomData.amenities.length > 0 && (
        <div className="bg-lsc-cream/30 dark:bg-lsc-dark/30 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3">{t('roomBooking.roomAmenitiesHeading', 'Room Amenities')}</h3>
          <div className="flex flex-wrap gap-2">
            {selectedRoomData.amenities.map(amenity => (
              <span
                key={amenity}
                className="px-3 py-1 bg-lsc-rose/20 text-lsc-rose dark:text-lsc-rose-light rounded-full text-sm font-medium"
              >
                ✓ {amenityLabel(amenity, t)}
              </span>
            ))}
          </div>
        </div>
      )}

      {selectedRoom && (<>
      {selectedRoomData && selectedDate && (
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 -mt-4">
          {t('roomBooking.canBeBookedInAdvance', '{{room}} can be booked up to {{days}} days in advance.')
            .replace('{{room}}', selectedRoomData.name)
            .replace('{{days}}', String(selectedRoomData.advance_booking_days))}
        </p>
      )}

      {/* Available Time Slots */}
      {selectedRoom && selectedDate && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
          <p
            id="time-slots-label"
            className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-3"
          >
            <Clock className="w-4 h-4 inline mr-2" aria-hidden="true" />
            {t('roomBooking.availableTimeSlotsLabel', 'Available Time Slots *')}
          </p>

          {loadingAvailability && (
            <div className="text-center py-6">
              <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose mx-auto mb-2" />
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('roomBooking.checkingAvailability', 'Checking availability...')}</p>
            </div>
          )}

          {!loadingAvailability && availabilityError && (
            <div
              id="availability-error"
              role="alert"
              className="bg-status-danger-50 dark:bg-status-danger-900/20 rounded-lg p-4 border border-status-danger-200 dark:border-status-danger-900/30"
            >
              <div className="flex gap-3">
                <AlertCircle className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400 flex-shrink-0 mt-0.5" aria-hidden="true" />
                <div className="flex-1">
                  <p className="text-sm text-status-danger-700 dark:text-status-danger-300 font-medium">{t('roomBooking.unableToLoadTimeSlots', 'Unable to load time slots')}</p>
                  <p className="text-sm text-status-danger-600 dark:text-status-danger-400 mt-1">{availabilityError}</p>
                  <button
                    type="button"
                    onClick={() => { setAvailabilityError(null); setRetryAvailabilityKey(k => k + 1) }}
                    className="text-sm font-medium text-lsc-rose hover:underline mt-2"
                  >
                    {t('states.tryAgain')}
                  </button>
                </div>
              </div>
            </div>
          )}

          {!loadingAvailability && !availabilityError && availability && availability.available_slots.length > 0 && (
            <>
            {/* Start Time */}
            <p id="time-slots-hint" className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 mb-2">{t('roomBooking.pickAStartTime', 'Pick a start time')}</p>
            <div
              className="grid gap-2 grid-cols-3 sm:grid-cols-4 md:grid-cols-6"
              role="group"
              aria-labelledby="time-slots-label"
              aria-describedby="time-slots-hint"
            >
              {availability.available_slots.map((slot, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => {
                    setSelectedStartTime(slot.start_time)
                    const maxAvail = slot.max_available_minutes || selectedDuration
                    const dur = Math.min(selectedDuration, maxAvail)
                    setSelectedDuration(dur)
                    const start = new Date(slot.start_time)
                    const end = new Date(start.getTime() + dur * 60000)
                    setSelectedSlot({
                      start_time: slot.start_time,
                      end_time: end.toISOString(),
                      duration_minutes: dur,
                      max_available_minutes: slot.max_available_minutes,
                    })
                  }}
                  aria-pressed={selectedStartTime === slot.start_time}
                  className={`p-2 rounded-lg border-2 text-center transition text-sm ${
                    selectedStartTime === slot.start_time
                      ? 'border-lsc-rose bg-lsc-rose/10 text-lsc-rose font-semibold'
                      : 'border-lsc-border dark:border-earth-700 hover:border-lsc-rose/50 text-lsc-dark dark:text-lsc-cream'
                  }`}
                >
                  <div className="font-medium">{formatSlotTime(slot.start_time)}</div>
                </button>
              ))}
            </div>

            {/* Duration picker */}
            {selectedStartTime && selectedRoomData && (
              <div className="mt-4">
                <label htmlFor="room-duration" className="block text-xs text-lsc-dark/60 dark:text-lsc-cream/60 mb-2">
                  {t('roomBooking.howLongDoYouNeed', 'How long do you need?')}
                </label>
                <div className="flex flex-wrap gap-2">
                  {Array.from(
                    { length: Math.floor((selectedRoomData.max_duration_minutes - selectedRoomData.min_duration_minutes) / 30) + 1 },
                    (_, i) => selectedRoomData.min_duration_minutes + i * 30
                  ).filter(dur => {
                    const maxAvail = selectedSlot?.max_available_minutes
                    return !maxAvail || dur <= maxAvail
                  }).map(dur => {
                    const label = dur >= 60 ? `${Math.floor(dur / 60)}h${dur % 60 ? ` ${dur % 60}m` : ''}` : `${dur}m`
                    return (
                      <button
                        key={dur}
                        type="button"
                        onClick={() => {
                          setSelectedDuration(dur)
                          const start = new Date(selectedStartTime)
                          const end = new Date(start.getTime() + dur * 60000)
                          setSelectedSlot({
                            start_time: selectedStartTime,
                            end_time: end.toISOString(),
                            duration_minutes: dur,
                            max_available_minutes: selectedSlot?.max_available_minutes,
                          })
                        }}
                        aria-pressed={selectedDuration === dur}
                        className={`px-4 py-2 rounded-lg border-2 text-sm font-medium transition ${
                          selectedDuration === dur
                            ? 'border-lsc-rose bg-lsc-rose/10 text-lsc-rose'
                            : 'border-lsc-border dark:border-earth-700 hover:border-lsc-rose/50 text-lsc-dark dark:text-lsc-cream'
                        }`}
                      >
                        {label}
                      </button>
                    )
                  })}
                </div>
              </div>
            )}

            {selectedSlot && (
              <div className="mt-4 p-3 bg-lsc-rose/5 border border-lsc-rose/20 rounded-lg text-sm text-lsc-dark dark:text-lsc-cream">
                <strong>{t('roomBooking.selectedSlotLabel', 'Selected:')}</strong> {formatSlotTime(selectedSlot.start_time)} &mdash; {formatSlotTime(selectedSlot.end_time)} {t('roomBooking.durationMinutesParens', '({{minutes}} minutes)').replace('{{minutes}}', String(selectedSlot.duration_minutes))}
              </div>
            )}
            </>
          )}

          {!loadingAvailability && !availabilityError && availability && availability.available_slots.length === 0 && (
            <div className="text-center py-6 text-lsc-dark/70 dark:text-lsc-cream/70">
              <AlertCircle className="w-8 h-8 mx-auto mb-2 opacity-50" aria-hidden="true" />
              <p>{t('roomBooking.noAvailableTimeSlotsFor')}</p>
              <p className="text-sm mt-1">{t('roomBooking.trySelectingADifferentDate')}</p>
            </div>
          )}
        </div>
      )}

      {/* Guest Count */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
        <label htmlFor="room-guests" className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-3">
          <Users className="w-4 h-4 inline mr-2" aria-hidden="true" />
          {t('roomBooking.numberOfPeopleLabel', 'Number of People *')}
        </label>
        <input
          type="number"
          id="room-guests"
          min="1"
          required
          max={selectedRoomData?.capacity || 12}
          value={guestCount}
          onChange={e => setGuestCount(e.target.value)}
          aria-describedby={selectedRoomData && parseInt(guestCount) > selectedRoomData.capacity ? 'room-guests-error' : undefined}
          className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
        />
        {selectedRoomData && parseInt(guestCount) > selectedRoomData.capacity && (
          <p id="room-guests-error" role="alert" className="text-sm text-status-danger-600 mt-2">{t('roomBooking.exceedsRoomCapacity', 'Exceeds room capacity of {{capacity}}').replace('{{capacity}}', String(selectedRoomData.capacity))}</p>
        )}
      </div>

      {/* Purpose */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
        <label htmlFor="room-purpose" className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2">{t('roomBooking.purposeOptionalLabel', 'Purpose (optional)')}</label>
        <input
          type="text"
          id="room-purpose"
          value={purpose}
          onChange={e => setPurpose(e.target.value)}
          placeholder={t('placeholder.roomBooking.egStudyGroupTeam')}
          maxLength={500}
          className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
        />
      </div>

      {/* Contact Information */}
      <div className="space-y-4">
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">{t('roomBooking.yourInformationHeading', 'Your Information')}</h2>

        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
          <label htmlFor="room-name" className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2">{t('roomBooking.fullNameLabel', 'Full Name *')}</label>
          <input
            ref={nameRef}
            type="text"
            id="room-name"
            value={name}
            onChange={e => { setName(e.target.value); if (nameInvalid) setNameInvalid(false) }}
            placeholder={t('placeholder.roomBooking.johnDoe')}
            autoComplete="name"
            aria-required="true"
            aria-invalid={nameInvalid}
            aria-describedby={nameInvalid ? 'room-form-error' : undefined}
            className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
            required
          />
        </div>

        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
          <label htmlFor="room-email" className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2">{t('roomBooking.emailRequiredLabel', 'Email *')}</label>
          <input
            ref={emailRef}
            type="email"
            id="room-email"
            value={email}
            onChange={e => { setEmail(e.target.value); if (emailInvalid) setEmailInvalid(false) }}
            placeholder={t('placeholder.registrationModal.johnexamplecom')}
            autoComplete="email"
            aria-required="true"
            aria-invalid={emailInvalid}
            aria-describedby={emailInvalid ? 'room-form-error' : undefined}
            className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
            required
          />
        </div>

        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
          <label htmlFor="room-phone" className="block text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2">{t('roomBooking.phoneOptionalLabel', 'Phone (optional)')}</label>
          <input
            type="tel"
            id="room-phone"
            value={phone}
            onChange={e => setPhone(e.target.value)}
            placeholder={t('placeholder.guestPassForm.5551234567')}
            autoComplete="tel"
            className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
          />
        </div>
      </div>

      {/* Inline form error (shown when required fields are missing on submit) */}
      {formError && (
        <div
          ref={formErrorRef}
          id="room-form-error"
          tabIndex={-1}
          role="alert"
          className="p-4 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-500 dark:border-status-danger-700 rounded-xl text-sm text-status-danger-700 dark:text-status-danger-300"
        >
          {formError}
        </div>
      )}

      {/* Approval notice */}
      {selectedRoomData?.requires_approval && (
        <div className="bg-status-warning-50 dark:bg-status-warning-900/20 rounded-xl p-4 border border-status-warning-200 dark:border-status-warning-900/30 flex gap-3">
          <Info className="w-5 h-5 text-status-warning-600 flex-shrink-0 mt-0.5" aria-hidden="true" />
          <p className="text-sm text-status-warning-900 dark:text-status-warning-100">
            <strong>{t('roomBooking.approvalRequiredLabel', 'Approval Required:')}</strong> {t('roomBooking.approvalRequiredBody', 'This room type requires staff approval. You will be notified by email once your reservation is reviewed.')}
          </p>
        </div>
      )}

      {/* Reservation Policy */}
      <div className="bg-earth-50 dark:bg-earth-900/20 rounded-xl p-4 border border-lsc-border dark:border-earth-800/30 flex gap-3">
        <AlertCircle className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0 mt-0.5" aria-hidden="true" />
        <p className="text-sm text-earth-900 dark:text-earth-200">
          <strong>{t('roomBooking.reservationPolicyLabel', 'Reservation Policy:')}</strong> {t('roomBooking.reservationPolicyBody', 'Please arrive on time. Check in within 15 minutes of your start time or the reservation may be marked as a no-show.')}
        </p>
      </div>

      {/* Submit Button */}
      {(() => {
        const isFormReady = !!selectedRoom && !!selectedSlot && !submitting
        return (
          <button
            type="submit"
            disabled={!isFormReady}
            aria-disabled={!isFormReady}
            className={`w-full py-3 px-6 font-semibold rounded-lg transition flex items-center justify-center gap-2 ${
              isFormReady
                ? 'bg-lsc-rose text-white hover:bg-lsc-rose/90 cursor-pointer'
                : 'bg-earth-200 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 cursor-not-allowed'
            }`}
          >
            {submitting ? (
              <>
                <Loader2 className="w-5 h-5 motion-safe:animate-spin" />
                {t('roomBooking.submitting', 'Submitting...')}
              </>
            ) : (
              selectedRoomData?.requires_approval ? t('roomBooking.submitForApproval', 'Submit for Approval') : t('roomBooking.reserveRoom', 'Reserve Room')
            )}
          </button>
        )
      })()}
    </>)}
    </form>
  )
}
