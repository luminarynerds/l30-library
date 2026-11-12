/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from 'react'
import { Laptop, Package, CalendarClock, AlertCircle, X, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { useAuth } from '@/contexts/AuthContext'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import {
  listEquipment,
  getMyEquipmentCheckouts,
  getMyReservations,
  cancelReservation,
  createReservation,
  formatEquipmentType,
  getStatusColor,
  isCheckoutOverdue,
  type Equipment,
  type EquipmentCheckout,
  type EquipmentReservation,
  type ReservationStatus,
} from '../api/equipment-api'
import PageContainer from '@/components/layout/PageContainer'

type Tab = 'browse' | 'checkouts' | 'reservations'

export default function MyEquipmentPage() {
  const { token } = useAuth()
  const [tab, setTab] = useState<Tab>('browse')

  // Browse state
  const [equipment, setEquipment] = useState<Equipment[]>([])
  const [browseLoading, setBrowseLoading] = useState(true)

  // Checkouts state
  const [activeCheckouts, setActiveCheckouts] = useState<EquipmentCheckout[]>([])
  const [pastCheckouts, setPastCheckouts] = useState<EquipmentCheckout[]>([])
  const [checkoutsLoading, setCheckoutsLoading] = useState(true)
  const [showHistory, setShowHistory] = useState(false)

  // Reservations state
  const [reservations, setReservations] = useState<EquipmentReservation[]>([])
  const [reservationsLoading, setReservationsLoading] = useState(true)
  const [cancellingId, setCancellingId] = useState<number | null>(null)

  // Reserve modal state
  const [reserveTarget, setReserveTarget] = useState<Equipment | null>(null)
  const [reserveStart, setReserveStart] = useState('')
  const [reserveEnd, setReserveEnd] = useState('')
  const [reservePurpose, setReservePurpose] = useState('')
  const [reserveSubmitting, setReserveSubmitting] = useState(false)

  const fetchBrowse = useCallback(async () => {
    if (!token) return
    setBrowseLoading(true)
    try {
      const res = await listEquipment(token, { available_only: true, per_page: 50 })
      setEquipment(res.items)
    } catch {
      toast.error('Failed to load available equipment')
    } finally {
      setBrowseLoading(false)
    }
  }, [token])

  const fetchCheckouts = useCallback(async () => {
    if (!token) return
    setCheckoutsLoading(true)
    try {
      const [active, history] = await Promise.all([
        getMyEquipmentCheckouts(token, false),
        getMyEquipmentCheckouts(token, true),
      ])
      setActiveCheckouts(active.items)
      setPastCheckouts(history.items.filter(c => c.status === 'returned'))
    } catch {
      toast.error('Failed to load checkouts')
    } finally {
      setCheckoutsLoading(false)
    }
  }, [token])

  const fetchReservations = useCallback(async () => {
    if (!token) return
    setReservationsLoading(true)
    try {
      const res = await getMyReservations(token)
      setReservations(res.items)
    } catch {
      toast.error('Failed to load reservations')
    } finally {
      setReservationsLoading(false)
    }
  }, [token])

  useEffect(() => {
    if (tab === 'browse') fetchBrowse()
    else if (tab === 'checkouts') fetchCheckouts()
    else if (tab === 'reservations') fetchReservations()
  }, [tab, fetchBrowse, fetchCheckouts, fetchReservations])

  const handleCancel = async (id: number) => {
    if (!token) return
    setCancellingId(id)
    try {
      await cancelReservation(token, id)
      toast.success('Reservation cancelled')
      await fetchReservations()
    } catch {
      toast.error('Failed to cancel reservation')
    } finally {
      setCancellingId(null)
    }
  }

  const handleReserveSubmit = async () => {
    if (!token || !reserveTarget) return
    if (!reserveStart || !reserveEnd) {
      toast.error('Please select start and end dates')
      return
    }
    setReserveSubmitting(true)
    try {
      const payload: Parameters<typeof createReservation>[1] = {
        equipment_id: reserveTarget.id,
        start_date: reserveStart,
        end_date: reserveEnd,
      }
      if (reservePurpose) payload.purpose = reservePurpose
      await createReservation(token, payload)
      toast.success('Reservation created')
      setReserveTarget(null)
      setReserveStart('')
      setReserveEnd('')
      setReservePurpose('')
      setTab('reservations')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create reservation')
    } finally {
      setReserveSubmitting(false)
    }
  }

  const canCancelReservation = (status: ReservationStatus) =>
    status === 'pending' || status === 'confirmed'

  const formatDate = (d: string) =>
    new Date(d).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })

  const tabs: { key: Tab; label: string; icon: typeof Laptop }[] = [
    { key: 'browse', label: 'Browse', icon: Package },
    { key: 'checkouts', label: 'My Checkouts', icon: Laptop },
    { key: 'reservations', label: 'My Reservations', icon: CalendarClock },
  ]

  return (
    <PageContainer className="py-8">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <Laptop className="w-8 h-8 text-lsc-rose" />
        <div>
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">Equipment Lending</h1>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">Browse, reserve, and track equipment loans</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-lsc-border dark:border-earth-700 mb-6">
        {tabs.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
              tab === key
                ? 'border-lsc-rose text-lsc-rose'
                : 'border-transparent text-earth-600 dark:text-earth-400 hover:text-earth-700 dark:hover:text-earth-200'
            }`}
          >
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>

      {/* Browse Tab */}
      {tab === 'browse' && (
        <div className="space-y-4">
          {browseLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-lsc-rose" />
            </div>
          ) : equipment.length === 0 ? (
            <div className="text-center py-12 text-earth-600 dark:text-earth-400">
              <Package className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No equipment currently available</p>
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              {equipment.map(item => (
                <div
                  key={item.id}
                  className="rounded-lg border border-earth-200 dark:border-earth-700 bg-lsc-white dark:bg-earth-800 p-4"
                >
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">{item.name}</h3>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-status-success-100 text-status-success-700">
                      Available
                    </span>
                  </div>
                  <div className="text-sm text-earth-600 dark:text-earth-400 space-y-1 mb-3">
                    <p>Type: {formatEquipmentType(item.equipment_type)}</p>
                    {item.location && <p>Location: {item.location}</p>}
                    <p>Loan period: {item.loan_period_days} day{item.loan_period_days !== 1 ? 's' : ''}</p>
                  </div>
                  <button
                    onClick={() => {
                      setReserveTarget(item)
                      const tomorrow = new Date()
                      tomorrow.setDate(tomorrow.getDate() + 1)
                      setReserveStart(tomorrow.toISOString().slice(0, 10))
                      const end = new Date(tomorrow)
                      end.setDate(end.getDate() + item.loan_period_days)
                      setReserveEnd(end.toISOString().slice(0, 10))
                    }}
                    className="w-full text-sm font-medium px-3 py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 transition-colors"
                  >
                    Reserve
                  </button>
                </div>
              ))}
            </div>
          )}

          <div className="p-4 bg-earth-50 dark:bg-earth-800 rounded-lg flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-earth-600 mt-0.5 flex-shrink-0" />
            <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              <p className="font-medium mb-1">How it works</p>
              <p>Reserve equipment online, then pick it up at the library. Loan periods vary by item. You can manage your reservations from the "My Reservations" tab.</p>
            </div>
          </div>
        </div>
      )}

      {/* Checkouts Tab */}
      {tab === 'checkouts' && (
        <div className="space-y-4">
          {checkoutsLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-lsc-rose" />
            </div>
          ) : (
            <>
              {activeCheckouts.length === 0 && !showHistory && (
                <div className="text-center py-12 text-earth-600 dark:text-earth-400">
                  <Laptop className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>No active checkouts</p>
                  <button onClick={() => setTab('browse')} className="mt-3 text-lsc-rose hover:underline">
                    Browse available equipment
                  </button>
                </div>
              )}

              {activeCheckouts.length > 0 && (
                <div className="space-y-3">
                  <h3 className="text-lg font-medium text-lsc-dark dark:text-lsc-cream">Active</h3>
                  {activeCheckouts.map(co => {
                    const overdue = isCheckoutOverdue(co)
                    return (
                      <div
                        key={co.id}
                        className={`rounded-lg border p-4 ${
                          overdue
                            ? 'border-status-danger-300 dark:border-status-danger-700 bg-status-danger-50 dark:bg-status-danger-900/20'
                            : 'border-earth-200 dark:border-earth-700 bg-lsc-white dark:bg-earth-800'
                        }`}
                      >
                        <div className="flex items-start justify-between mb-2">
                          <h4 className="font-medium text-lsc-dark dark:text-lsc-cream">
                            {co.equipment_name || `Equipment #${co.equipment_id}`}
                          </h4>
                          <span className={`text-xs px-2 py-0.5 rounded-full ${getStatusColor(co.status)}`}>
                            {overdue ? 'Overdue' : co.status.replace('_', ' ')}
                          </span>
                        </div>
                        <div className="text-sm text-earth-600 dark:text-earth-400 space-y-1">
                          {co.equipment_type && <p>Type: {formatEquipmentType(co.equipment_type)}</p>}
                          <p>Checked out: {formatDate(co.checked_out_at)}</p>
                          <p className={overdue ? 'text-status-danger-600 dark:text-status-danger-400 font-medium' : ''}>
                            Due: {formatDate(co.due_date)}
                          </p>
                          {co.renewal_count > 0 && <p>Renewed {co.renewal_count} time{co.renewal_count !== 1 ? 's' : ''}</p>}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}

              <button
                onClick={() => setShowHistory(h => !h)}
                className="text-sm text-lsc-rose hover:underline"
              >
                {showHistory ? 'Hide history' : 'Show checkout history'}
              </button>

              {showHistory && pastCheckouts.length > 0 && (
                <div className="space-y-3">
                  <h3 className="text-lg font-medium text-lsc-dark dark:text-lsc-cream">History</h3>
                  {pastCheckouts.map(co => (
                    <div
                      key={co.id}
                      className="rounded-lg border border-earth-200 dark:border-earth-700 bg-lsc-white dark:bg-earth-800 p-4"
                    >
                      <div className="flex items-start justify-between mb-2">
                        <h4 className="font-medium text-lsc-dark dark:text-lsc-cream">
                          {co.equipment_name || `Equipment #${co.equipment_id}`}
                        </h4>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${getStatusColor('returned')}`}>
                          Returned
                        </span>
                      </div>
                      <div className="text-sm text-earth-600 dark:text-earth-400 space-y-1">
                        {co.equipment_type && <p>Type: {formatEquipmentType(co.equipment_type)}</p>}
                        <p>Checked out: {formatDate(co.checked_out_at)}</p>
                        {co.returned_at && <p>Returned: {formatDate(co.returned_at)}</p>}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {showHistory && pastCheckouts.length === 0 && (
                <p className="text-sm text-earth-600 dark:text-earth-400">No checkout history</p>
              )}
            </>
          )}
        </div>
      )}

      {/* Reservations Tab */}
      {tab === 'reservations' && (
        <div className="space-y-4">
          {reservationsLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-lsc-rose" />
            </div>
          ) : reservations.length === 0 ? (
            <div className="text-center py-12 text-earth-600 dark:text-earth-400">
              <CalendarClock className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No reservations</p>
              <button onClick={() => setTab('browse')} className="mt-3 text-lsc-rose hover:underline">
                Browse available equipment
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {reservations.map(r => (
                <div
                  key={r.id}
                  className="rounded-lg border border-earth-200 dark:border-earth-700 bg-lsc-white dark:bg-earth-800 p-4"
                >
                  <div className="flex items-start justify-between mb-2">
                    <h4 className="font-medium text-lsc-dark dark:text-lsc-cream">
                      {r.equipment_name || `Equipment #${r.equipment_id}`}
                    </h4>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${getStatusColor(r.status as unknown as Parameters<typeof getStatusColor>[0])}`}>
                      {r.status.replace('_', ' ')}
                    </span>
                  </div>
                  <div className="text-sm text-earth-600 dark:text-earth-400 space-y-1">
                    {r.equipment_type && <p>Type: {formatEquipmentType(r.equipment_type)}</p>}
                    <p>{formatDate(r.start_date)} - {formatDate(r.end_date)}</p>
                    {r.purpose && <p>Purpose: {r.purpose}</p>}
                  </div>
                  {canCancelReservation(r.status) && (
                    <button
                      onClick={() => handleCancel(r.id)}
                      disabled={cancellingId === r.id}
                      className="mt-3 text-sm text-status-danger-600 dark:text-status-danger-400 hover:underline disabled:opacity-50"
                    >
                      {cancellingId === r.id ? 'Cancelling...' : 'Cancel reservation'}
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Reserve Modal */}
      {reserveTarget && (
        <ModalBackdrop onClose={() => setReserveTarget(null)} title={`Reserve ${reserveTarget.name}`}>
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-lg w-full max-w-md mx-4 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                Reserve {reserveTarget.name}
              </h2>
              <button
                onClick={() => setReserveTarget(null)}
                className="text-earth-600 hover:text-earth-700 dark:hover:text-earth-300"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  Start date
                </label>
                <input
                  type="date"
                  value={reserveStart}
                  onChange={e => setReserveStart(e.target.value)}
                  className="w-full rounded-lg border border-earth-300 dark:border-earth-600 bg-white dark:bg-earth-700 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  End date
                </label>
                <input
                  type="date"
                  value={reserveEnd}
                  onChange={e => setReserveEnd(e.target.value)}
                  className="w-full rounded-lg border border-earth-300 dark:border-earth-600 bg-white dark:bg-earth-700 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  Purpose (optional)
                </label>
                <input
                  type="text"
                  value={reservePurpose}
                  onChange={e => setReservePurpose(e.target.value)}
                  placeholder="e.g., Class project, job search"
                  className="w-full rounded-lg border border-earth-300 dark:border-earth-600 bg-white dark:bg-earth-700 px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream placeholder:text-earth-400"
                />
              </div>
              <button
                onClick={handleReserveSubmit}
                disabled={reserveSubmitting}
                className="w-full text-sm font-medium px-3 py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 transition-colors disabled:opacity-50"
              >
                {reserveSubmitting ? 'Reserving...' : 'Confirm Reservation'}
              </button>
            </div>
          </div>
        </ModalBackdrop>
      )}
    </PageContainer>
  )
}
