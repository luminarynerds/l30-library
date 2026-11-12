/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../../contexts/AuthContext'
import { useLanguage } from '../../../i18n/I18nContext'
import { getLocale } from '../../../i18n/localization'
import { AdminShell } from '../../../components/shells/AdminShell'
import {
  DoorOpen, Loader2, Calendar, Monitor, CalendarDays, BarChart3, Settings, RefreshCw, Plus, Edit2, Save, CheckCircle, ShieldAlert,
} from 'lucide-react'
import toast from 'react-hot-toast'
import {
  getStaffEquipment,
  createStaffEquipment,
  updateStaffEquipment,
  type StaffEquipment,
  type StaffEquipmentCreate,
} from '../../../api/staff-rooms-api'

// Extracted components
import {
  RoomList,
  RoomDetail,
  ReservationList,
  ReservationCalendar,
  ReservationDetail,
  RoomStatsPanel,
  StaffOverrideBookingModal,
} from './components'

// Extracted hooks
import { useRooms, useReservations, useRoomStats } from './hooks'

import type { TabId } from './types'
import { useTranslation} from '@/i18n'
import { t } from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

// Equipment modal component (kept in page since it's equipment-specific)
function EquipmentFormModal({
  equipment,
  onClose,
  onSave,
  isLoading,
}: {
  equipment?: StaffEquipment | null
  onClose: () => void
  onSave: (data: StaffEquipmentCreate) => void
  isLoading: boolean
}) {
  const [formData, setFormData] = useState<StaffEquipmentCreate>(() => ({
    name: equipment?.name || '',
    equipment_code: equipment?.equipment_code || '',
    description: equipment?.description || '',
    category: equipment?.category || '',
    ...(equipment?.room_id ? { room_id: equipment.room_id } : {}),
    is_active: equipment?.is_active ?? true,
    requires_checkout: equipment?.requires_checkout ?? false,
  }))

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSave(formData)
  }

  return (
    <ModalBackdrop onClose={onClose} title="Requires Checkout">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-md w-full">
        <div className="p-6 border-b border-lsc-border dark:border-earth-700">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            {equipment ? 'Edit Equipment' : 'Add Equipment'}
          </h2>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label htmlFor="equipment-name" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Equipment Name *
            </label>
            <input
              id="equipment-name"
              type="text"
              value={formData.name}
              onChange={(e) => setFormData((prev) => ({ ...prev, name: e.target.value }))}
              required
              className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
              placeholder={t('placeholder.staffRooms.egProjectorWhiteboard')}
            />
          </div>

          <div>
            <label htmlFor="equipment-code" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Equipment Code *
            </label>
            <input
              id="equipment-code"
              type="text"
              value={formData.equipment_code}
              onChange={(e) => setFormData((prev) => ({ ...prev, equipment_code: e.target.value }))}
              required
              className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
              placeholder={t('placeholder.staffRooms.egProj001')}
            />
          </div>

          <div>
            <label htmlFor="equipment-category" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Category
            </label>
            <input
              id="equipment-category"
              type="text"
              value={formData.category}
              onChange={(e) => setFormData((prev) => ({ ...prev, category: e.target.value }))}
              className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
              placeholder={t('placeholder.staffRooms.egAvEquipment')}
            />
          </div>

          <div>
            <label htmlFor="equipment-description" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Description
            </label>
            <textarea
              id="equipment-description"
              value={formData.description}
              onChange={(e) => setFormData((prev) => ({ ...prev, description: e.target.value }))}
              rows={2}
              className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
            />
          </div>

          <div className="flex gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.requires_checkout}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, requires_checkout: e.target.checked }))
                }
                className="w-4 h-4 rounded border-lsc-border text-lsc-rose focus:ring-lsc-rose"
              />
              <span className="text-sm text-lsc-dark dark:text-lsc-cream">Requires Checkout</span>
            </label>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.is_active}
                onChange={(e) => setFormData((prev) => ({ ...prev, is_active: e.target.checked }))}
                className="w-4 h-4 rounded border-lsc-border text-lsc-rose focus:ring-lsc-rose"
              />
              <span className="text-sm text-lsc-dark dark:text-lsc-cream">Active</span>
            </label>
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg disabled:opacity-50"
            >
              {isLoading && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
              {equipment ? 'Update' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </ModalBackdrop>
  )
}

export default function StaffRoomsPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user, token, isLoading: authLoading } = useAuth()
  const { language } = useLanguage()
  const locale = getLocale(language)
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<TabId>('rooms')

  // Modals state
  const [showRoomModal, setShowRoomModal] = useState(false)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [editingRoom, setEditingRoom] = useState<any>(null)
  const [showEquipmentModal, setShowEquipmentModal] = useState(false)
  const [editingEquipment, setEditingEquipment] = useState<StaffEquipment | null>(null)
  const [showOverrideModal, setShowOverrideModal] = useState(false)
  const [selectedReservationId, setSelectedReservationId] = useState<number | null>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [selectedReservation, setSelectedReservation] = useState<any>(null)

  // Room filters
  const [roomTypeFilter, setRoomTypeFilter] = useState('')
  const [includeInactive, setIncludeInactive] = useState(false)

  // Reservation filters
  const [reservationStatus, setReservationStatus] = useState('')
  const [reservationDateFrom, setReservationDateFrom] = useState('')
  const [reservationDateTo, setReservationDateTo] = useState('')

  // Report dates
  const [reportStartDate, setReportStartDate] = useState<string>(() => {
    const d = new Date()
    d.setMonth(d.getMonth() - 1)
    return d.toISOString().split('T')[0]!
  })
  const [reportEndDate, setReportEndDate] = useState<string>(() => {
    return new Date().toISOString().split('T')[0]!
  })

  // Settings state
  const SETTINGS_KEY = 'lsc_room_booking_settings'
  const defaultSettings = {
    maxBookingDuration: 2,
    advanceBookingDays: 14,
    minimumNotice: 1,
    noShowWindow: 15,
    requireApproval: true,
    sendConfirmationEmails: true,
    sendReminders: true,
    allowRecurring: false,
    operatingHours: {
      Monday: { open: '09:00', close: '21:00', isOpen: true },
      Tuesday: { open: '09:00', close: '21:00', isOpen: true },
      Wednesday: { open: '09:00', close: '21:00', isOpen: true },
      Thursday: { open: '09:00', close: '21:00', isOpen: true },
      Friday: { open: '09:00', close: '21:00', isOpen: true },
      Saturday: { open: '09:00', close: '17:00', isOpen: true },
      Sunday: { open: '13:00', close: '17:00', isOpen: true },
    } as Record<string, { open: string; close: string; isOpen: boolean }>,
  }

  const [settings, setSettings] = useState(() => {
    try {
      const saved = localStorage.getItem(SETTINGS_KEY)
      return saved ? { ...defaultSettings, ...JSON.parse(saved) } : defaultSettings
    } catch {
      return defaultSettings
    }
  })
  const [settingsSaved, setSettingsSaved] = useState(false)
  const [isSavingSettings, setIsSavingSettings] = useState(false)

  const handleSaveSettings = useCallback(() => {
    setIsSavingSettings(true)
    try {
      localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings))
      toast.success(t('toast.adminRecommendations.settingsSavedSuccessfully'))
      setSettingsSaved(true)
      setTimeout(() => setSettingsSaved(false), 2000)
    } catch {
      toast.error(t('staffRooms.failedToSaveSettings'))
    } finally {
      setIsSavingSettings(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settings])

  const updateOperatingHours = useCallback((day: string, field: string, value: string | boolean) => {
    setSettings((prev: typeof defaultSettings) => ({
      ...prev,
      operatingHours: {
        ...prev.operatingHours,
        [day]: { ...prev.operatingHours[day], [field]: value },
      },
    }))
  }, [])

  // Check auth
  useEffect(() => {
    if (!authLoading && (!user || user.role === 'patron')) {
      toast.error(t('toast.acquisitionManagement.staffAccessRequired'))
      navigate('/account')
    }
  }, [authLoading, user, navigate, t])

  // Use extracted hooks
  const roomsHook = useRooms({
    token,
    enabled: activeTab === 'rooms' || showOverrideModal,
    filters: { roomTypeFilter, includeInactive },
  })

  const reservationsHook = useReservations({
    token,
    enabled: activeTab === 'reservations' || activeTab === 'schedule',
    filters: { status: reservationStatus, dateFrom: reservationDateFrom, dateTo: reservationDateTo },
  })

  const statsHook = useRoomStats({
    token,
    enabled: activeTab === 'reports' || activeTab === 'rooms',
    rooms: roomsHook.rooms,
    allReservations: reservationsHook.allReservations,
    pendingReservations: reservationsHook.pendingReservations,
    reportStartDate,
    reportEndDate,
  })

  // Equipment management (kept separate for now)
  const [equipmentData, setEquipmentData] = useState<StaffEquipment[]>([])
  const [equipmentLoading, setEquipmentLoading] = useState(false)

  const refetchEquipment = useCallback(async () => {
    if (!token || activeTab !== 'equipment') return
    setEquipmentLoading(true)
    try {
      const data = await getStaffEquipment(token, includeInactive)
      setEquipmentData(data)
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : t('toast.staffRooms.failedToLoadEquipment'))
    } finally {
      setEquipmentLoading(false)
    }
  }, [token, includeInactive, activeTab, t])

  // Load equipment when tab changes
  useEffect(() => {
    if (activeTab === 'equipment') {
      refetchEquipment()
    }
  }, [activeTab, refetchEquipment])

  // Equipment mutations
  const handleSaveEquipment = useCallback(
    async (data: StaffEquipmentCreate) => {
      if (!token) return
      try {
        if (editingEquipment) {
          await updateStaffEquipment(token, editingEquipment.id, data)
          toast.success(t('toast.staffEquipment.equipmentUpdatedSuccessfully'))
        } else {
          await createStaffEquipment(token, data)
          toast.success(t('toast.staffEquipment.equipmentCreatedSuccessfully'))
        }
        setShowEquipmentModal(false)
        setEditingEquipment(null)
        refetchEquipment()
      } catch (error: unknown) {
        toast.error(error instanceof Error ? error.message : t('toast.staffRooms.failedToSaveEquipment'))
      }
    },
    [token, editingEquipment, refetchEquipment, t]
  )

  // Load reservation details when modal opens
  useEffect(() => {
    if (selectedReservationId) {
      reservationsHook.fetchDetails(selectedReservationId).then((details) => {
        setSelectedReservation(details)
      })
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedReservationId, t])

  // Tab configuration
  const tabs: { id: TabId; label: string; icon: React.ReactNode }[] = [
    { id: 'rooms', label: 'Rooms', icon: <DoorOpen className="w-4 h-4" /> },
    { id: 'reservations', label: 'Reservations', icon: <Calendar className="w-4 h-4" /> },
    { id: 'equipment', label: 'Equipment', icon: <Monitor className="w-4 h-4" /> },
    { id: 'schedule', label: 'Schedule', icon: <CalendarDays className="w-4 h-4" /> },
    { id: 'reports', label: 'Reports', icon: <BarChart3 className="w-4 h-4" /> },
    { id: 'settings', label: 'Settings', icon: <Settings className="w-4 h-4" /> },
  ]

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" />
      </div>
    )
  }

  if (!user || user.role === 'patron') return <></>

  return (
    <AdminShell title="Room Management">
        <section className="space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-lsc-cream dark:bg-earth-800/30 rounded-xl">
                <DoorOpen className="w-6 h-6 text-lsc-rose dark:text-lsc-rose-light" />
              </div>
              <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                Room Management
              </h1>
            </div>
            <div className="flex items-center gap-2">
              {(activeTab === 'reservations' || activeTab === 'schedule') && (
                <button
                  onClick={() => setShowOverrideModal(true)}
                  className="flex items-center gap-2 px-4 py-2 text-sm bg-status-warning-600 hover:bg-status-warning-700 text-white rounded-lg transition-colors"
                  title="Force-book a room, cancelling any conflicts"
                >
                  <ShieldAlert className="w-4 h-4" /> Override Booking
                </button>
              )}
              <button
                onClick={() => {
                  if (activeTab === 'rooms') roomsHook.refetch()
                  else if (activeTab === 'reservations') reservationsHook.refetchAll()
                  else if (activeTab === 'equipment') refetchEquipment()
                }}
                className="flex items-center gap-2 px-4 py-2 text-sm bg-lsc-cream dark:bg-earth-800 hover:bg-lsc-border dark:hover:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg transition-colors"
              >
                <RefreshCw className="w-4 h-4" /> Refresh
              </button>
            </div>
          </div>

          {/* Quick Stats */}
          <RoomStatsPanel
            stats={statsHook.quickStats}
            reportStartDate={reportStartDate}
            reportEndDate={reportEndDate}
            onReportStartDateChange={setReportStartDate}
            onReportEndDateChange={setReportEndDate}
          />

          {/* Tabs */}
          <div className="border-b border-lsc-border dark:border-earth-700">
            <nav className="flex gap-4 overflow-x-auto">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 pb-3 px-1 border-b-2 transition-colors whitespace-nowrap ${
                    activeTab === tab.id
                      ? 'border-lsc-rose text-lsc-rose dark:text-lsc-rose-light'
                      : 'border-transparent text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream'
                  }`}
                >
                  {tab.icon}
                  <span className="font-medium">{tab.label}</span>
                </button>
              ))}
            </nav>
          </div>

          {/* Tab Content */}

          {/* ROOMS TAB */}
          {activeTab === 'rooms' && (
            <RoomList
              rooms={roomsHook.rooms}
              isLoading={roomsHook.isLoading}
              roomTypeFilter={roomTypeFilter}
              includeInactive={includeInactive}
              onRoomTypeFilterChange={setRoomTypeFilter}
              onIncludeInactiveChange={setIncludeInactive}
              onAddRoom={() => {
                setEditingRoom(null)
                setShowRoomModal(true)
              }}
              onEditRoom={(room) => {
                setEditingRoom(room)
                setShowRoomModal(true)
              }}
              onToggleActivation={(room) => {
                if (room.is_active) {
                  roomsHook.deactivateRoomMutation.mutate(room.id)
                } else {
                  roomsHook.activateRoomMutation.mutate(room.id)
                }
              }}
              isDeactivating={roomsHook.deactivateRoomMutation.isPending}
              isActivating={roomsHook.activateRoomMutation.isPending}
            />
          )}

          {/* RESERVATIONS TAB */}
          {activeTab === 'reservations' && (
            <ReservationList
              reservations={reservationsHook.allReservations}
              pendingReservations={reservationsHook.pendingReservations}
              isLoading={reservationsHook.isLoadingAll || reservationsHook.isLoadingPending}
              reservationStatus={reservationStatus}
              reservationDateFrom={reservationDateFrom}
              reservationDateTo={reservationDateTo}
              locale={locale}
              onStatusFilterChange={setReservationStatus}
              onDateFromChange={setReservationDateFrom}
              onDateToChange={setReservationDateTo}
              onViewReservation={(id) => {
                setSelectedReservationId(id)
              }}
            />
          )}

          {/* EQUIPMENT TAB */}
          {activeTab === 'equipment' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <label className="flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream">
                  <input
                    type="checkbox"
                    checked={includeInactive}
                    onChange={(e) => setIncludeInactive(e.target.checked)}
                    className="w-4 h-4 rounded border-lsc-border text-lsc-rose focus:ring-lsc-rose"
                  />
                  Show Inactive
                </label>

                <button
                  onClick={() => {
                    setEditingEquipment(null)
                    setShowEquipmentModal(true)
                  }}
                  className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg text-sm"
                >
                  <Plus className="w-4 h-4" /> Add Equipment
                </button>
              </div>

              {equipmentLoading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
                </div>
              ) : equipmentData && equipmentData.length > 0 ? (
                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {equipmentData.map((item) => (
                    <div
                      key={item.id}
                      className={`bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border ${
                        item.is_active
                          ? 'border-lsc-border dark:border-earth-700'
                          : 'border-status-danger-200 dark:border-status-danger-900/50 opacity-60'
                      }`}
                    >
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{item.name}</h3>
                          <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 font-mono">
                            {item.equipment_code}
                          </p>
                        </div>
                        <span
                          className={`px-2 py-0.5 rounded text-xs font-medium ${
                            item.is_active
                              ? 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400'
                              : 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400'
                          }`}
                        >
                          {item.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </div>

                      {item.category && (
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                          {item.category}
                        </p>
                      )}

                      {item.description && (
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{item.description}</p>
                      )}

                      {item.requires_checkout && (
                        <div className="mt-2">
                          <span className="text-xs px-2 py-0.5 bg-earth-100 dark:bg-earth-800/30 text-earth-800 dark:text-lsc-rose-light rounded">
                            Requires Checkout
                          </span>
                        </div>
                      )}

                      <div className="flex gap-2 mt-4 pt-3 border-t border-lsc-border dark:border-earth-700">
                        <button
                          onClick={() => {
                            setEditingEquipment(item)
                            setShowEquipmentModal(true)
                          }}
                          className="flex items-center gap-1 px-2 py-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded"
                        >
                          <Edit2 className="w-3 h-3" /> Edit
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
                  <Monitor className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>No equipment found</p>
                  <button
                    onClick={() => setShowEquipmentModal(true)}
                    className="mt-3 text-lsc-rose hover:underline"
                  >
                    Add your first equipment
                  </button>
                </div>
              )}
            </div>
          )}

          {/* SCHEDULE TAB */}
          {activeTab === 'schedule' && (
            <ReservationCalendar
              reservations={reservationsHook.allReservations ?? []}
            />
          )}

          {/* REPORTS TAB */}
          {activeTab === 'reports' && (
            <RoomStatsPanel
              stats={statsHook.quickStats}
              utilizationReport={statsHook.utilizationReport ?? []}
              popularTimesReport={statsHook.popularTimesReport ?? null}
              noShowReport={statsHook.noShowReport ?? null}
              isLoadingUtilization={statsHook.isLoadingUtilization}
              isLoadingPopularTimes={statsHook.isLoadingPopularTimes}
              isLoadingNoShow={statsHook.isLoadingNoShow}
              reportStartDate={reportStartDate}
              reportEndDate={reportEndDate}
              onReportStartDateChange={setReportStartDate}
              onReportEndDateChange={setReportEndDate}
            />
          )}

          {/* SETTINGS TAB */}
          {activeTab === 'settings' && (
            <div className="space-y-6">
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
                  <Settings className="w-5 h-5 text-lsc-rose" />
                  Room Booking Defaults
                </h3>
                <div className="grid md:grid-cols-2 gap-6">
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                        Default Max Booking Duration (hours)
                      </label>
                      <input
                        type="number"
                        value={settings.maxBookingDuration}
                        onChange={(e) => setSettings((prev: typeof settings) => ({ ...prev, maxBookingDuration: parseInt(e.target.value) || 0 }))}
                        min={1}
                        max={24}
                        className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                        Default Advance Booking (days)
                      </label>
                      <input
                        type="number"
                        value={settings.advanceBookingDays}
                        onChange={(e) => setSettings((prev: typeof settings) => ({ ...prev, advanceBookingDays: parseInt(e.target.value) || 0 }))}
                        min={1}
                        max={365}
                        className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                        Minimum Notice (hours)
                      </label>
                      <input
                        type="number"
                        value={settings.minimumNotice}
                        onChange={(e) => setSettings((prev: typeof settings) => ({ ...prev, minimumNotice: parseInt(e.target.value) || 0 }))}
                        min={0}
                        max={168}
                        className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                      />
                    </div>
                  </div>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                        No-Show Window (minutes)
                      </label>
                      <input
                        type="number"
                        value={settings.noShowWindow}
                        onChange={(e) => setSettings((prev: typeof settings) => ({ ...prev, noShowWindow: parseInt(e.target.value) || 0 }))}
                        min={5}
                        max={60}
                        className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                      />
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                        Minutes after start time before marking as no-show
                      </p>
                    </div>
                    <div className="space-y-3 pt-2">
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={settings.requireApproval}
                          onChange={(e) => setSettings((prev: typeof settings) => ({ ...prev, requireApproval: e.target.checked }))}
                          className="w-4 h-4 rounded border-lsc-border text-lsc-rose focus:ring-lsc-rose"
                        />
                        <span className="text-sm text-lsc-dark dark:text-lsc-cream">
                          Require approval for meeting rooms
                        </span>
                      </label>
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={settings.sendConfirmationEmails}
                          onChange={(e) => setSettings((prev: typeof settings) => ({ ...prev, sendConfirmationEmails: e.target.checked }))}
                          className="w-4 h-4 rounded border-lsc-border text-lsc-rose focus:ring-lsc-rose"
                        />
                        <span className="text-sm text-lsc-dark dark:text-lsc-cream">
                          Send confirmation emails
                        </span>
                      </label>
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={settings.sendReminders}
                          onChange={(e) => setSettings((prev: typeof settings) => ({ ...prev, sendReminders: e.target.checked }))}
                          className="w-4 h-4 rounded border-lsc-border text-lsc-rose focus:ring-lsc-rose"
                        />
                        <span className="text-sm text-lsc-dark dark:text-lsc-cream">
                          Send reminder notifications (1 hour before)
                        </span>
                      </label>
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={settings.allowRecurring}
                          onChange={(e) => setSettings((prev: typeof settings) => ({ ...prev, allowRecurring: e.target.checked }))}
                          className="w-4 h-4 rounded border-lsc-border text-lsc-rose focus:ring-lsc-rose"
                        />
                        <span className="text-sm text-lsc-dark dark:text-lsc-cream">
                          Allow recurring reservations
                        </span>
                      </label>
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
                  Operating Hours
                </h3>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60 mb-4">
                  Set the default operating hours for room availability. Individual rooms can override these settings.
                </p>
                <div className="space-y-2">
                  {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'].map((day) => (
                    <div key={day} className="flex items-center gap-3">
                      <span className="w-24 text-sm text-lsc-dark dark:text-lsc-cream">{day}</span>
                      <input
                        type="time"
                        value={settings.operatingHours[day]?.open ?? '09:00'}
                        onChange={(e) => updateOperatingHours(day, 'open', e.target.value)}
                        className="px-2 py-1 rounded border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-sm text-lsc-dark dark:text-lsc-cream"
                      />
                      <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">to</span>
                      <input
                        type="time"
                        value={settings.operatingHours[day]?.close ?? '21:00'}
                        onChange={(e) => updateOperatingHours(day, 'close', e.target.value)}
                        className="px-2 py-1 rounded border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-sm text-lsc-dark dark:text-lsc-cream"
                      />
                      <label className="flex items-center gap-1 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={settings.operatingHours[day]?.isOpen ?? true}
                          onChange={(e) => updateOperatingHours(day, 'isOpen', e.target.checked)}
                          className="w-4 h-4 rounded border-lsc-border text-lsc-rose focus:ring-lsc-rose"
                        />
                        <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">Open</span>
                      </label>
                    </div>
                  ))}
                </div>
              </div>

              {/* Save Button */}
              <div className="flex justify-end">
                <button
                  onClick={handleSaveSettings}
                  disabled={isSavingSettings}
                  className="flex items-center gap-2 px-6 py-2.5 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
                >
                  {isSavingSettings ? (
                    <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                  ) : settingsSaved ? (
                    <CheckCircle className="w-4 h-4" />
                  ) : (
                    <Save className="w-4 h-4" />
                  )}
                  {settingsSaved ? 'Saved' : 'Save Settings'}
                </button>
              </div>
            </div>
          )}
        </section>

      {/* Modals */}
      {showRoomModal && (
        <RoomDetail
          room={editingRoom}
          onClose={() => {
            setShowRoomModal(false)
            setEditingRoom(null)
          }}
          onSave={(data) => roomsHook.handleSaveRoom(editingRoom, data)}
          isLoading={roomsHook.createRoomMutation.isPending || roomsHook.updateRoomMutation.isPending}
        />
      )}

      {showEquipmentModal && (
        <EquipmentFormModal
          equipment={editingEquipment}
          onClose={() => {
            setShowEquipmentModal(false)
            setEditingEquipment(null)
          }}
          onSave={handleSaveEquipment}
          isLoading={false}
        />
      )}

      {showOverrideModal && (
        <StaffOverrideBookingModal
          rooms={roomsHook.rooms}
          onClose={() => setShowOverrideModal(false)}
          onSubmit={(data) =>
            reservationsHook.createOverrideMutation.mutate(data, {
              onSuccess: () => setShowOverrideModal(false),
            })
          }
          isLoading={reservationsHook.createOverrideMutation.isPending}
        />
      )}

      {selectedReservationId && token && (
        <ReservationDetail
          reservation={selectedReservation}
          isLoading={false}
          locale={locale}
          onClose={() => {
            setSelectedReservationId(null)
            setSelectedReservation(null)
          }}
          onApprove={() =>
            reservationsHook.approveMutation.mutate({
              reservationId: selectedReservationId,
              approved: true,
            })
          }
          onReject={(reasonCode, reasonText) =>
            reservationsHook.approveMutation.mutate({
              reservationId: selectedReservationId,
              approved: false,
              rejectionReasonCode: reasonCode,
              rejectionReason: reasonText,
            })
          }
          onCheckIn={() =>
            reservationsHook.checkInMutation.mutate(selectedReservationId)
          }
          onCancel={() =>
            reservationsHook.cancelMutation.mutate({
              reservationId: selectedReservationId,
              reason: 'Cancelled by staff',
            })
          }
          isApproving={reservationsHook.approveMutation.isPending}
          isCancelling={reservationsHook.cancelMutation.isPending}
          isCheckingIn={reservationsHook.checkInMutation.isPending}
        />
      )}
    </AdminShell>
  )
}
