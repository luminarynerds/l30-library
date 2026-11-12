/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { Monitor, Calendar, Clock, AlertCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import { useComputerSessions } from '../features/computers/useComputerSessions'
import { StationList } from '../features/computers/StationList'
import { BookingCalendar } from '../features/computers/BookingCalendar'
import { AvailabilityGrid } from '../features/computers/AvailabilityGrid'
import { ActiveSession } from '../features/computers/ActiveSession'
import { WaitlistStatus } from '../features/computers/WaitlistStatus'
import { ReservationCard } from '../features/computers/ReservationCard'
import { t } from '@/i18n'
import PageContainer from '@/components/layout/PageContainer'

type Tab = 'stations' | 'book' | 'session'

export default function ComputersPage() {
  const [tab, setTab] = useState<Tab>('stations')
  const [selectedComputerId, setSelectedComputerId] = useState<number>()
  const [bookDate, setBookDate] = useState(new Date().toISOString().split('T')[0]!)
  const {
    stations, reservations, currentSession,
    fetchStations, fetchReservations, fetchCurrentSession,
    createReservation, cancelReservation, checkIn, startSession,
  } = useComputerSessions()

  useEffect(() => {
    fetchReservations()
    fetchCurrentSession()
  }, [fetchReservations, fetchCurrentSession])

  // Load the station list the first time the "Book a Time" tab is opened so its
  // computer picker has options (the stations tab uses its own StationList instance).
  useEffect(() => {
    if (tab === 'book' && stations.length === 0) fetchStations()
  }, [tab, stations.length, fetchStations])

  // Auto-switch to session tab if active session
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- react to async-fetched session appearing; user can still navigate away after
    if (currentSession) setTab('session')
  }, [currentSession])

  const handleReserve = async (computerId: number, startTime: Date, durationMinutes: number) => {
    try {
      await createReservation(computerId, startTime.toISOString(), durationMinutes)
      toast.success(t('toast.computers.reservationCreated'))
      await fetchReservations()
      setTab('session')
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.computers.failedToCreateReservation'))
    }
  }

  // Book a specific computer for a slot. Duration is the slot length
  // (end - start), capped at the computer's max session (availability returns
  // hourly slots even for a 30-min-max station, which would otherwise overshoot).
  const bookSlot = (computerId: number, startTime: string, endTime: string) => {
    const station = stations.find(s => s.id === computerId)
    const slotMinutes = Math.round(
      (new Date(endTime).getTime() - new Date(startTime).getTime()) / 60000
    )
    const durationMinutes = station
      ? Math.min(slotMinutes, station.max_session_minutes)
      : slotMinutes
    void handleReserve(computerId, new Date(startTime), durationMinutes)
  }

  // The single-computer calendar requires a computer picked first.
  const handleSlotSelect = (startTime: string, endTime: string) => {
    if (!selectedComputerId) {
      toast(t('toast.computers.selectAComputerFirstFrom'))
      return
    }
    bookSlot(selectedComputerId, startTime, endTime)
  }

  const handleCancel = async (id: number) => {
    try {
      await cancelReservation(id)
      toast.success(t('toast.computers.reservationCancelled'))
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.computers.failedToCancelReservation'))
    }
  }

  const handleCheckIn = async (id: number) => {
    try {
      await checkIn(id)
      toast.success(t('toast.computers.checkedIn'))
      setTab('session')
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.computers.failedToCheckIn'))
    }
  }

  const handleStartSession = async (computerId: number, durationMinutes: number) => {
    try {
      await startSession(computerId, durationMinutes)
      toast.success(t('toast.computers.sessionStarted'))
      await fetchReservations()
      setTab('session')
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('toast.computers.failedToStart'))
    }
  }

  const tabs: { key: Tab; label: string; icon: typeof Monitor }[] = [
    { key: 'stations', label: 'Available Computers', icon: Monitor },
    { key: 'book', label: 'Book a Time', icon: Calendar },
    { key: 'session', label: 'My Session', icon: Clock },
  ]

  const activeReservations = reservations.filter(r =>
    ['confirmed', 'pending', 'in_session'].includes(r.status)
  )

  return (
    <>
    <PageContainer className="py-8">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <Monitor aria-hidden="true" className="w-8 h-8 text-lsc-rose" />
        <div>
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">Public Computers</h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">Browse, reserve, and manage computer sessions</p>
        </div>
      </div>

      {/* Tabs */}
      <div
        className="flex border-b border-lsc-border dark:border-earth-700 mb-6"
        role="tablist"
        aria-label="Public computer sections"
      >
        {tabs.map(({ key, label, icon: Icon }) => {
          const isSelected = tab === key
          return (
            <button
              key={key}
              id={`computers-tab-${key}`}
              type="button"
              role="tab"
              aria-selected={isSelected}
              aria-controls={`computers-panel-${key}`}
              tabIndex={isSelected ? 0 : -1}
              onClick={() => setTab(key)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:border-transparent ${
                isSelected
                  ? 'border-lsc-rose text-lsc-rose'
                  : 'border-transparent text-earth-600 dark:text-earth-400 hover:text-earth-700 dark:hover:text-earth-200'
              }`}
            >
              <Icon aria-hidden="true" className="w-4 h-4" />
              {label}
            </button>
          )
        })}
      </div>

      {/* Tab Content */}
      {tab === 'stations' && (
        <div
          id="computers-panel-stations"
          role="tabpanel"
          aria-labelledby="computers-tab-stations"
          className="space-y-4"
        >
          <StationList onReserve={handleReserve} onStartSession={handleStartSession} />
          <div
            className="p-4 bg-earth-50 dark:bg-earth-800 rounded-lg flex items-start gap-3"
            role="note"
            aria-label="How public computer sessions work"
          >
            <AlertCircle aria-hidden="true" className="w-5 h-5 text-earth-600 mt-0.5 flex-shrink-0" />
            <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              <p className="font-medium mb-1">How it works</p>
              <p>Click "Start Session" on an available computer for immediate use (60 min default). To book ahead, use the "Book a Time" tab.</p>
            </div>
          </div>
        </div>
      )}

      {tab === 'book' && (
        <div
          id="computers-panel-book"
          role="tabpanel"
          aria-labelledby="computers-tab-book"
          className="space-y-4"
        >
          <div>
            <label
              htmlFor="book-date"
              className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1"
            >
              Date
            </label>
            <input
              id="book-date"
              type="date"
              value={bookDate}
              min={new Date().toISOString().split('T')[0]}
              onChange={(e) => setBookDate(e.target.value)}
              className="w-full p-2 border border-lsc-border dark:border-earth-700 rounded bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
            />
          </div>

          <AvailabilityGrid date={bookDate} onPick={bookSlot} />

          <details className="border-t border-lsc-border dark:border-earth-700 pt-4">
            <summary className="cursor-pointer text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
              Or book a specific computer
            </summary>
            <div className="mt-3 space-y-3">
              <div>
                <label
                  htmlFor="book-computer-select"
                  className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1"
                >
                  Computer
                </label>
                <select
                  id="book-computer-select"
                  value={selectedComputerId ?? ''}
                  onChange={(e) => setSelectedComputerId(e.target.value ? Number(e.target.value) : undefined)}
                  className="w-full p-2 border border-lsc-border dark:border-earth-700 rounded bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
                >
                  <option value="">Select a computer…</option>
                  {stations
                    .filter(s => s.is_active && s.status !== 'maintenance' && s.status !== 'offline')
                    .map(s => (
                    <option key={s.id} value={s.id}>{s.name} — {s.computer_number}</option>
                  ))}
                </select>
              </div>
              {selectedComputerId ? (
                <BookingCalendar computerId={selectedComputerId} date={bookDate} onSlotSelect={handleSlotSelect} />
              ) : (
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70" role="status">
                  Choose a computer above to see available times.
                </p>
              )}
            </div>
          </details>
        </div>
      )}

      {tab === 'session' && (
        <div
          id="computers-panel-session"
          role="tabpanel"
          aria-labelledby="computers-tab-session"
          className="space-y-4"
        >
          <ActiveSession />
          <WaitlistStatus />
          {activeReservations.length > 0 && (
            <section className="space-y-3" aria-labelledby="my-reservations-heading">
              <h2
                id="my-reservations-heading"
                className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream"
              >
                My Reservations
              </h2>
              <ul className="space-y-3 list-none p-0 m-0" aria-label="Active reservations">
                {activeReservations.map(r => (
                  <li key={r.id}>
                    <ReservationCard reservation={r} onCancel={handleCancel} onCheckIn={handleCheckIn} />
                  </li>
                ))}
              </ul>
            </section>
          )}
          {!currentSession && activeReservations.length === 0 && (
            <div
              className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70"
              role="status"
              aria-live="polite"
            >
              <Monitor aria-hidden="true" className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No active session or reservations</p>
              <button
                type="button"
                onClick={() => setTab('stations')}
                className="mt-3 text-lsc-rose hover:underline focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2 rounded-lg"
              >
                Browse available computers
              </button>
            </div>
          )}
        </div>
      )}
    </PageContainer>

    </>
    )
}
