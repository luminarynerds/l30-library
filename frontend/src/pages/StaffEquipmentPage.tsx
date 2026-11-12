/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useAuth } from "../contexts/AuthContext"
import { AdminShell } from '../components/shells/AdminShell'
import {
  Laptop, Loader2, Search, Plus, Calendar,
  AlertTriangle, Wrench, BarChart3,
  RefreshCw, Edit2, Trash2,
  ArrowLeftRight, ChevronRight, Bell,
  AlertCircle, CheckCircle2,
} from "lucide-react"
import toast from "react-hot-toast"
import {
  listEquipment,
  createEquipment,
  updateEquipment,
  retireEquipment,
  checkoutEquipment,
  scheduleMaintenance,
  getEquipmentDueForMaintenance,
  getActiveAlerts,
  acknowledgeAlert,
  resolveAlert,
  processOverdueAlerts,
  getEquipmentSummary,
  formatEquipmentType,
  formatCondition,
  formatStatus,
  getStatusColor,
  getConditionColor,
  type Equipment,
  type EquipmentType,
  type EquipmentStatus,
  type EquipmentCondition,
  type EquipmentCreate,
  type EquipmentUpdate,
  type MaintenanceType,
} from "../api/equipment-api"
import { useTranslation} from '@/i18n'
import ConfirmDialog from '@/components/ConfirmDialog'
import { EquipmentFormModal } from '../components/staff/EquipmentFormModal'
import { CheckoutModal } from '../components/staff/CheckoutModal'
import { MaintenanceFormModal } from '../components/staff/MaintenanceFormModal'
import { getEquipmentIcon } from '../components/staff/equipment-utils'

type TabId = "equipment" | "checkouts" | "reservations" | "maintenance" | "alerts" | "reports"

const EQUIPMENT_TYPES: EquipmentType[] = [
  'laptop', 'hotspot', 'projector', 'tablet', 'e_reader', 'camera',
  'audio_recorder', 'calculator', 'charger', 'headphones', 'keyboard', 'mouse',
  'webcam', 'microphone', 'tripod', 'light_kit', 'gaming_console', 'vr_headset', 'telescope', 'other'
]

const EQUIPMENT_STATUSES: EquipmentStatus[] = [
  'available', 'checked_out', 'reserved', 'in_maintenance', 'damaged', 'lost', 'retired'
]

const EQUIPMENT_CONDITIONS: EquipmentCondition[] = [
  'excellent', 'good', 'fair', 'poor', 'needs_repair', 'non_functional'
]

// eslint-disable-next-line complexity
export default function StaffEquipmentPage(): React.ReactElement {
  const { t } = useTranslation()
  const { user, token, isLoading: authLoading } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const [activeTab, setActiveTab] = useState<TabId>((searchParams.get("tab") as TabId) || "equipment")

  const [searchQuery, setSearchQuery] = useState("")
  const [typeFilter, setTypeFilter] = useState<EquipmentType | "">("")
  const [statusFilter, setStatusFilter] = useState<EquipmentStatus | "">("")
  const [conditionFilter, setConditionFilter] = useState<EquipmentCondition | "">("")

  const [showEquipmentForm, setShowEquipmentForm] = useState(false)
  const [editingEquipment, setEditingEquipment] = useState<Equipment | null>(null)
  const [selectedEquipment, setSelectedEquipment] = useState<Equipment | null>(null)
  const [showCheckoutModal, setShowCheckoutModal] = useState(false)
  const [showMaintenanceForm, setShowMaintenanceForm] = useState(false)

  const [equipmentForm, setEquipmentForm] = useState({
    name: "",
    equipment_type: "laptop" as EquipmentType,
    description: "",
    barcode: "",
    serial_number: "",
    manufacturer: "",
    model: "",
    condition: "good" as EquipmentCondition,
    location: "",
    loan_period_days: 14,
    max_renewals: 2,
    deposit_required: "",
    included_accessories: "",
    return_instructions: "",
    notes: "",
  })
  const [maintenanceForm, setMaintenanceForm] = useState({
    equipment_id: 0,
    maintenance_type: "routine_check" as MaintenanceType,
    scheduled_date: "",
    description: "",
  })
  const [checkoutPatronId, setCheckoutPatronId] = useState("")
  const [checkoutNotes, setCheckoutNotes] = useState("")
  const [depositCollected, setDepositCollected] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [pendingRetireId, setPendingRetireId] = useState<number | null>(null)
  const [retirementNotes, setRetirementNotes] = useState("")

  useEffect(() => {
    if (!authLoading && (!user || user.role === "patron")) {
      toast.error(t('toast.acquisitionManagement.staffAccessRequired'))
      navigate("/account")
    }
  }, [authLoading, user, navigate, t])

  useEffect(() => {
    const tab = searchParams.get("tab") as TabId
    if (tab && ["equipment", "checkouts", "reservations", "maintenance", "alerts", "reports"].includes(tab)) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- syncs activeTab to URL ?tab on external nav (back/forward); not derivable without losing stale-keep-on-invalid behavior
      setActiveTab(tab)
    }
  }, [searchParams])

  const handleTabChange = (tab: TabId) => {
    setActiveTab(tab)
    setSearchParams({ tab })
  }

  const { data: equipmentData, isLoading: equipmentLoading, refetch: refetchEquipment } = useQuery({
    queryKey: ["staff-equipment", typeFilter, statusFilter, conditionFilter, searchQuery],
    queryFn: async () => {
      if (!token) return { items: [], total: 0, page: 1, per_page: 50, pages: 0 }
      return await listEquipment(token, {
        per_page: 50,
        ...(typeFilter && { equipment_type: typeFilter }),
        ...(statusFilter && { status: statusFilter }),
        ...(conditionFilter && { condition: conditionFilter }),
        ...(searchQuery && { search: searchQuery }),
      })
    },
    enabled: !!token && activeTab === "equipment",
  })

  const { data: summaryData } = useQuery({
    queryKey: ["staff-equipment-summary"],
    queryFn: async () => {
      if (!token) return null
      return await getEquipmentSummary(token)
    },
    enabled: !!token && (activeTab === "equipment" || activeTab === "reports"),
  })

  const { data: maintenanceDueData } = useQuery({
    queryKey: ["equipment-maintenance-due"],
    queryFn: async () => {
      if (!token) return []
      return await getEquipmentDueForMaintenance(token)
    },
    enabled: !!token && (activeTab === "maintenance" || activeTab === "equipment"),
  })

  const { data: alertsData, isLoading: alertsLoading, refetch: refetchAlerts } = useQuery({
    queryKey: ["equipment-alerts"],
    queryFn: async () => {
      if (!token) return { items: [], total: 0, page: 1, per_page: 50, pages: 0 }
      return await getActiveAlerts(token, { per_page: 50 })
    },
    enabled: !!token && activeTab === "alerts",
  })

  const createEquipmentMutation = useMutation({
    mutationFn: async (data: EquipmentCreate) => {
      if (!token) throw new Error("Not authenticated")
      return await createEquipment(token, data)
    },
    onSuccess: () => {
      toast.success(t('toast.staffEquipment.equipmentCreatedSuccessfully'))
      setShowEquipmentForm(false)
      resetEquipmentForm()
      queryClient.invalidateQueries({ queryKey: ["staff-equipment"] })
      queryClient.invalidateQueries({ queryKey: ["staff-equipment-summary"] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const updateEquipmentMutation = useMutation({
    mutationFn: async ({ id, data }: { id: number; data: EquipmentUpdate }) => {
      if (!token) throw new Error("Not authenticated")
      return await updateEquipment(token, id, data)
    },
    onSuccess: () => {
      toast.success(t('toast.staffEquipment.equipmentUpdatedSuccessfully'))
      setShowEquipmentForm(false)
      setEditingEquipment(null)
      resetEquipmentForm()
      queryClient.invalidateQueries({ queryKey: ["staff-equipment"] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const retireEquipmentMutation = useMutation({
    mutationFn: async ({ id, notes }: { id: number; notes?: string }) => {
      if (!token) throw new Error("Not authenticated")
      return await retireEquipment(token, id, notes)
    },
    onSuccess: () => {
      toast.success(t('toast.staffEquipment.equipmentRetired'))
      queryClient.invalidateQueries({ queryKey: ["staff-equipment"] })
      queryClient.invalidateQueries({ queryKey: ["staff-equipment-summary"] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const checkoutMutation = useMutation({
    mutationFn: async ({ equipmentId, patronId, notes, deposit }: { equipmentId: number; patronId: number; notes?: string; deposit?: boolean }) => {
      if (!token) throw new Error("Not authenticated")
      return await checkoutEquipment(token, {
        equipment_id: equipmentId,
        patron_id: patronId,
        ...(notes && { checkout_notes: notes }),
        ...(deposit !== undefined && { deposit_collected: deposit }),
      })
    },
    onSuccess: () => {
      toast.success(t('toast.staffEquipment.equipmentCheckedOut'))
      setShowCheckoutModal(false)
      setSelectedEquipment(null)
      setCheckoutPatronId("")
      setCheckoutNotes("")
      setDepositCollected(false)
      queryClient.invalidateQueries({ queryKey: ["staff-equipment"] })
      queryClient.invalidateQueries({ queryKey: ["staff-equipment-summary"] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const scheduleMaintenanceMutation = useMutation({
    mutationFn: async (data: typeof maintenanceForm) => {
      if (!token) throw new Error("Not authenticated")
      return await scheduleMaintenance(token, data)
    },
    onSuccess: () => {
      toast.success(t('toast.staffEquipment.maintenanceScheduled'))
      setShowMaintenanceForm(false)
      setMaintenanceForm({
        equipment_id: 0,
        maintenance_type: "routine_check" as MaintenanceType,
        scheduled_date: "",
        description: "",
      })
      queryClient.invalidateQueries({ queryKey: ["equipment-maintenance-due"] })
      queryClient.invalidateQueries({ queryKey: ["staff-equipment"] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const acknowledgeAlertMutation = useMutation({
    mutationFn: async ({ alertId, notes }: { alertId: number; notes?: string }) => {
      if (!token) throw new Error("Not authenticated")
      return await acknowledgeAlert(token, alertId, notes || undefined)
    },
    onSuccess: () => {
      toast.success(t('toast.adminLinkHealth.alertAcknowledged'))
      queryClient.invalidateQueries({ queryKey: ["equipment-alerts"] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const resolveAlertMutation = useMutation({
    mutationFn: async ({ alertId, notes }: { alertId: number; notes?: string }) => {
      if (!token) throw new Error("Not authenticated")
      return await resolveAlert(token, alertId, notes || undefined)
    },
    onSuccess: () => {
      toast.success(t('toast.adminLinkHealth.alertResolved'))
      queryClient.invalidateQueries({ queryKey: ["equipment-alerts"] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const processOverdueMutation = useMutation({
    mutationFn: async () => {
      if (!token) throw new Error("Not authenticated")
      return await processOverdueAlerts(token)
    },
    onSuccess: (data) => {
      toast.success(`${data.alerts_created} overdue alert(s) created`)
      queryClient.invalidateQueries({ queryKey: ["equipment-alerts"] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const resetEquipmentForm = () => {
    setEquipmentForm({
      name: "",
      equipment_type: "laptop",
      description: "",
      barcode: "",
      serial_number: "",
      manufacturer: "",
      model: "",
      condition: "good",
      location: "",
      loan_period_days: 14,
      max_renewals: 2,
      deposit_required: "",
      included_accessories: "",
      return_instructions: "",
      notes: "",
    })
  }

  const handleEditEquipment = (equipment: Equipment) => {
    setEditingEquipment(equipment)
    setEquipmentForm({
      name: equipment.name,
      equipment_type: equipment.equipment_type,
      description: equipment.description || "",
      barcode: equipment.barcode,
      serial_number: equipment.serial_number || "",
      manufacturer: equipment.manufacturer || "",
      model: equipment.model || "",
      condition: equipment.condition,
      location: equipment.location || "",
      loan_period_days: equipment.loan_period_days,
      max_renewals: equipment.max_renewals,
      deposit_required: equipment.deposit_required || "",
      included_accessories: equipment.included_accessories || "",
      return_instructions: equipment.return_instructions || "",
      notes: equipment.notes || "",
    })
    setShowEquipmentForm(true)
  }

  const handleSubmitEquipmentForm = (e: React.FormEvent) => {
    e.preventDefault()
    if (editingEquipment) {
      updateEquipmentMutation.mutate({ id: editingEquipment.id, data: equipmentForm })
    } else {
      createEquipmentMutation.mutate(equipmentForm)
    }
  }

  const tabs: { id: TabId; label: string; icon: React.ReactNode }[] = [
    { id: "equipment", label: "Equipment", icon: <Laptop className="w-4 h-4" /> },
    { id: "checkouts", label: "Checkouts", icon: <ArrowLeftRight className="w-4 h-4" /> },
    { id: "reservations", label: "Reservations", icon: <Calendar className="w-4 h-4" /> },
    { id: "maintenance", label: "Maintenance", icon: <Wrench className="w-4 h-4" /> },
    { id: "alerts", label: "Alerts", icon: <Bell className="w-4 h-4" /> },
    { id: "reports", label: "Reports", icon: <BarChart3 className="w-4 h-4" /> },
  ]

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" />
      </div>
    )
  }

  if (!user || user.role === "patron") return <></>

  return (
    <AdminShell title="Equipment Management">
      <div>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-lsc-cream dark:bg-earth-800/30 rounded-xl">
              <Laptop className="w-6 h-6 text-lsc-rose dark:text-lsc-rose-light" />
            </div>
            <div>
              {/* StaffLayout (via AdminShell title) already emits the page <h1>; this is a styled visual title only, demoted to avoid a duplicate h1. */}
              <p className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
                Equipment Management
              </p>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                Manage equipment lending, maintenance, and reservations
              </p>
            </div>
          </div>
          <button
            onClick={() => refetchEquipment()}
            className="flex items-center gap-2 px-4 py-2 text-sm bg-lsc-cream dark:bg-earth-800 hover:bg-lsc-border dark:hover:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg transition-colors"
          >
            <RefreshCw className="w-4 h-4" /> Refresh
          </button>
        </div>

        {summaryData && activeTab === "equipment" && (
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
              <p className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">{summaryData.total_equipment}</p>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total Equipment</p>
            </div>
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
              <p className="text-2xl font-bold text-status-success-600 dark:text-status-success-400">{summaryData.available_count}</p>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Available</p>
            </div>
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
              <p className="text-2xl font-bold text-lsc-rose dark:text-lsc-rose-light">{summaryData.checked_out_count}</p>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Checked Out</p>
            </div>
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
              <p className="text-2xl font-bold text-status-warning-600 dark:text-status-warning-400">{summaryData.maintenance_count}</p>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">In Maintenance</p>
            </div>
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
              <p className="text-2xl font-bold text-status-danger-600 dark:text-status-danger-400">{summaryData.overdue_checkouts}</p>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Overdue</p>
            </div>
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
              <p className="text-2xl font-bold text-category-600 dark:text-category-400">{summaryData.active_reservations}</p>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Reservations</p>
            </div>
          </div>
        )}

        <div className="border-b border-lsc-border dark:border-earth-700">
          <nav className="flex gap-4 overflow-x-auto">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => handleTabChange(tab.id)}
                className={`flex items-center gap-2 pb-3 px-1 border-b-2 transition-colors whitespace-nowrap ${
                  activeTab === tab.id
                    ? "border-lsc-rose text-lsc-rose dark:text-lsc-rose-light"
                    : "border-transparent text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
                }`}
              >
                {tab.icon}
                <span className="font-medium">{tab.label}</span>
                {tab.id === "alerts" && alertsData && alertsData.total > 0 && (
                  <span className="bg-status-danger-500 text-white text-xs rounded-full px-2 py-0.5">{alertsData.total}</span>
                )}
              </button>
            ))}
          </nav>
        </div>

        {activeTab === "equipment" && (
          <div className="space-y-4">
            <div className="flex flex-wrap gap-4 items-center justify-between">
              <div className="flex flex-wrap gap-2 items-center">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder={t('placeholder.staffEquipment.searchEquipment')}
                    aria-label={t('aria.staffEquipment.searchEquipment')}
                    className="pl-10 pr-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream text-sm w-64"
                  />
                </div>
                <select
                  value={typeFilter}
                  onChange={(e) => setTypeFilter(e.target.value as EquipmentType | "")}
                  aria-label={t('aria.staffEquipment.filterByType', 'Filter by equipment type')}
                  className="px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream text-sm"
                >
                  <option value="">All Types</option>
                  {EQUIPMENT_TYPES.map((type) => (
                    <option key={type} value={type}>{formatEquipmentType(type)}</option>
                  ))}
                </select>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value as EquipmentStatus | "")}
                  aria-label={t('aria.staffEquipment.filterByStatus', 'Filter by status')}
                  className="px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream text-sm"
                >
                  <option value="">All Statuses</option>
                  {EQUIPMENT_STATUSES.map((status) => (
                    <option key={status} value={status}>{formatStatus(status)}</option>
                  ))}
                </select>
                <select
                  value={conditionFilter}
                  onChange={(e) => setConditionFilter(e.target.value as EquipmentCondition | "")}
                  aria-label={t('aria.staffEquipment.filterByCondition', 'Filter by condition')}
                  className="px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream text-sm"
                >
                  <option value="">All Conditions</option>
                  {EQUIPMENT_CONDITIONS.map((cond) => (
                    <option key={cond} value={cond}>{formatCondition(cond)}</option>
                  ))}
                </select>
              </div>
              <button
                onClick={() => {
                  setEditingEquipment(null)
                  resetEquipmentForm()
                  setShowEquipmentForm(true)
                }}
                className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg text-sm font-medium"
              >
                <Plus className="w-4 h-4" /> Add Equipment
              </button>
            </div>

            {maintenanceDueData && maintenanceDueData.length > 0 && (
              <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-xl p-4">
                <div className="flex items-center gap-2 text-status-warning-800 dark:text-status-warning-400 mb-2">
                  <AlertTriangle className="w-5 h-5" />
                  <span className="font-medium">Equipment Due for Maintenance ({maintenanceDueData.length})</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {maintenanceDueData.slice(0, 5).map((eq) => (
                    <span key={eq.id} className="px-2 py-1 bg-status-warning-100 dark:bg-status-warning-900/30 rounded text-sm text-status-warning-800 dark:text-status-warning-400">
                      {eq.name}
                    </span>
                  ))}
                  {maintenanceDueData.length > 5 && (
                    <span className="text-sm text-status-warning-700 dark:text-status-warning-500">+{maintenanceDueData.length - 5} more</span>
                  )}
                </div>
              </div>
            )}

            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
              {equipmentLoading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
                </div>
              ) : equipmentData?.items && equipmentData.items.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-lsc-cream/50 dark:bg-earth-900/50">
                      <tr className="text-left text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        <th className="px-4 py-3 font-medium">Equipment</th>
                        <th className="px-4 py-3 font-medium">Type</th>
                        <th className="px-4 py-3 font-medium">Barcode</th>
                        <th className="px-4 py-3 font-medium">Status</th>
                        <th className="px-4 py-3 font-medium">Condition</th>
                        <th className="px-4 py-3 font-medium">Location</th>
                        <th className="px-4 py-3 font-medium text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                      {equipmentData.items.map((equipment) => (
                        <tr key={equipment.id} className="hover:bg-lsc-cream/30 dark:hover:bg-earth-700/30 transition-colors">
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-3">
                              <div className="w-10 h-10 bg-lsc-cream dark:bg-earth-700 rounded-lg flex items-center justify-center text-lsc-rose dark:text-lsc-rose-light">
                                {getEquipmentIcon(equipment.equipment_type)}
                              </div>
                              <div>
                                <p className="font-medium text-lsc-dark dark:text-lsc-cream">{equipment.name}</p>
                                {equipment.manufacturer && (
                                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                                    {equipment.manufacturer} {equipment.model}
                                  </p>
                                )}
                              </div>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
                            {formatEquipmentType(equipment.equipment_type)}
                          </td>
                          <td className="px-4 py-3 font-mono text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
                            {equipment.barcode}
                          </td>
                          <td className="px-4 py-3">
                            <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${getStatusColor(equipment.status)}`}>
                              {formatStatus(equipment.status)}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${getConditionColor(equipment.condition)}`}>
                              {formatCondition(equipment.condition)}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">
                            {equipment.location || "-"}
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center justify-end gap-2">
                              {equipment.status === "available" && (
                                <button
                                  onClick={() => {
                                    setSelectedEquipment(equipment)
                                    setShowCheckoutModal(true)
                                  }}
                                  className="p-1.5 text-status-success-600 hover:bg-status-success-100 dark:bg-status-success-900/30 dark:hover:bg-status-success-900/30 rounded"
                                  title="Checkout"
                                >
                                  <ArrowLeftRight className="w-4 h-4" />
                                </button>
                              )}
                              <button
                                onClick={() => handleEditEquipment(equipment)}
                                className="p-1.5 text-lsc-dark/70 hover:bg-lsc-cream dark:text-lsc-cream/70 dark:hover:bg-earth-700 rounded"
                                title="Edit"
                              >
                                <Edit2 className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => {
                                  setSelectedEquipment(equipment)
                                  setMaintenanceForm({ ...maintenanceForm, equipment_id: equipment.id })
                                  setShowMaintenanceForm(true)
                                }}
                                className="p-1.5 text-status-warning-600 hover:bg-status-warning-100 dark:bg-status-warning-900/30 dark:hover:bg-status-warning-900/30 rounded"
                                title="Schedule Maintenance"
                              >
                                <Wrench className="w-4 h-4" />
                              </button>
                              {equipment.status !== "retired" && (
                                <button
                                  onClick={() => { setPendingRetireId(equipment.id); setRetirementNotes(""); setConfirmOpen(true) }}
                                  className="p-1.5 text-status-danger-600 hover:bg-status-danger-100 dark:bg-status-danger-900/30 dark:hover:bg-status-danger-900/30 rounded"
                                  title="Retire"
                                >
                                  <Trash2 className="w-4 h-4" />
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
                  <Laptop className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>No equipment found</p>
                  <button
                    onClick={() => setShowEquipmentForm(true)}
                    className="mt-4 text-lsc-rose hover:underline"
                  >
                    Add your first equipment item
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === "checkouts" && (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Active Checkouts</h3>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
              View and manage equipment checkouts. Use the Circulation page to process returns.
            </p>
            <div className="mt-4 text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70">
              <ArrowLeftRight className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>{t('staffEquipment.searchForAPatronTo')}</p>
            </div>
          </div>
        )}

        {activeTab === "reservations" && (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">Equipment Reservations</h3>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
              View and manage equipment reservations from patrons.
            </p>
            <div className="mt-4 text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/70">
              <Calendar className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>{t('staffEquipment.selectAnEquipmentItemTo')}</p>
            </div>
          </div>
        )}

        {activeTab === "maintenance" && (
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Maintenance Schedule</h3>
              <button
                onClick={() => {
                  setMaintenanceForm({
                    equipment_id: 0,
                    maintenance_type: "routine_check" as MaintenanceType,
                    scheduled_date: "",
                    description: "",
                  })
                  setShowMaintenanceForm(true)
                }}
                className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg text-sm font-medium"
              >
                <Plus className="w-4 h-4" /> Schedule Maintenance
              </button>
            </div>

            {maintenanceDueData && maintenanceDueData.length > 0 ? (
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
                <table className="w-full">
                  <thead className="bg-lsc-cream/50 dark:bg-earth-900/50">
                    <tr className="text-left text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      <th className="px-4 py-3 font-medium">Equipment</th>
                      <th className="px-4 py-3 font-medium">Type</th>
                      <th className="px-4 py-3 font-medium">Barcode</th>
                      <th className="px-4 py-3 font-medium">Condition</th>
                      <th className="px-4 py-3 font-medium text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                    {maintenanceDueData.map((eq) => (
                      <tr key={eq.id} className="hover:bg-lsc-cream/30 dark:hover:bg-earth-700/30">
                        <td className="px-4 py-3 font-medium text-lsc-dark dark:text-lsc-cream">{eq.name}</td>
                        <td className="px-4 py-3 text-sm text-lsc-dark/80 dark:text-lsc-cream/80">{formatEquipmentType(eq.equipment_type)}</td>
                        <td className="px-4 py-3 font-mono text-sm">{eq.barcode}</td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${getConditionColor(eq.condition)}`}>
                            {formatCondition(eq.condition)}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <button
                            onClick={() => {
                              setMaintenanceForm({ ...maintenanceForm, equipment_id: eq.id })
                              setShowMaintenanceForm(true)
                            }}
                            className="px-3 py-1.5 bg-lsc-rose hover:bg-lsc-rose/90 text-white text-sm rounded-lg"
                          >
                            Schedule
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700 text-center">
                <Wrench className="w-12 h-12 mx-auto mb-3 opacity-50 text-lsc-dark/70 dark:text-lsc-cream/70" />
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('staffEquipment.noEquipmentCurrentlyDueFor')}</p>
              </div>
            )}
          </div>
        )}

        {activeTab === "alerts" && (
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Equipment Alerts</h3>
              <div className="flex gap-2">
                <button
                  onClick={() => processOverdueMutation.mutate()}
                  disabled={processOverdueMutation.isPending}
                  className="flex items-center gap-2 px-4 py-2 bg-lsc-cream dark:bg-earth-700 hover:bg-lsc-border dark:hover:bg-earth-600 text-lsc-dark dark:text-lsc-cream rounded-lg text-sm"
                >
                  <RefreshCw className={`w-4 h-4 ${processOverdueMutation.isPending ? "motion-safe:animate-spin" : ""}`} />
                  Process Overdues
                </button>
                <button
                  onClick={() => refetchAlerts()}
                  className="flex items-center gap-2 px-4 py-2 bg-lsc-cream dark:bg-earth-700 hover:bg-lsc-border dark:hover:bg-earth-600 text-lsc-dark dark:text-lsc-cream rounded-lg text-sm"
                >
                  <RefreshCw className="w-4 h-4" /> Refresh
                </button>
              </div>
            </div>

            {alertsLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
              </div>
            ) : alertsData?.items && alertsData.items.length > 0 ? (
              <div className="space-y-3">
                {alertsData.items.map((alert) => (
                  <div
                    key={alert.id}
                    className={`p-4 rounded-xl border ${
                      alert.priority === "high"
                        ? "bg-status-danger-50 dark:bg-status-danger-900/20 border-status-danger-200 dark:border-status-danger-800"
                        : alert.priority === "medium"
                        ? "bg-status-warning-50 dark:bg-status-warning-900/20 border-status-warning-200 dark:border-status-warning-800"
                        : "bg-earth-50 dark:bg-earth-800/20 border-lsc-border dark:border-earth-700"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-start gap-3">
                        <div className={`p-2 rounded-lg ${
                          alert.priority === "high" ? "bg-status-danger-100 dark:bg-status-danger-900/40" :
                          alert.priority === "medium" ? "bg-status-warning-100 dark:bg-status-warning-900/40" :
                          "bg-earth-100 dark:bg-earth-800/40"
                        }`}>
                          <AlertCircle className={`w-5 h-5 ${
                            alert.priority === "high" ? "text-status-danger-600 dark:text-status-danger-400" :
                            alert.priority === "medium" ? "text-status-warning-600 dark:text-status-warning-400" :
                            "text-lsc-rose dark:text-lsc-rose-light"
                          }`} />
                        </div>
                        <div>
                          <p className="font-medium text-lsc-dark dark:text-lsc-cream">{alert.title}</p>
                          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{alert.message}</p>
                          <div className="flex flex-wrap gap-2 mt-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                            {alert.equipment_name && <span>Equipment: {alert.equipment_name}</span>}
                            {alert.patron_name && <span>Patron: {alert.patron_name}</span>}
                            {alert.days_overdue && <span>Days overdue: {alert.days_overdue}</span>}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {!alert.acknowledged_at && (
                          <button
                            onClick={() => acknowledgeAlertMutation.mutate({ alertId: alert.id })}
                            disabled={acknowledgeAlertMutation.isPending}
                            className="px-3 py-1.5 bg-lsc-rose hover:bg-lsc-rose/90 text-white text-sm rounded-lg"
                          >
                            Acknowledge
                          </button>
                        )}
                        {!alert.resolved_at && (
                          <button
                            onClick={() => {
                              const notes = prompt("Resolution notes (optional):")
                              resolveAlertMutation.mutate({
                                alertId: alert.id,
                                ...(notes && { notes })
                              })
                            }}
                            disabled={resolveAlertMutation.isPending}
                            className="px-3 py-1.5 bg-status-success-500 hover:bg-status-success-600 text-white text-sm rounded-lg"
                          >
                            Resolve
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700 text-center">
                <CheckCircle2 className="w-12 h-12 mx-auto mb-3 text-status-success-500 opacity-70" />
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70">No active alerts</p>
              </div>
            )}
          </div>
        )}

        {activeTab === "reports" && (
          <div className="space-y-4">
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Equipment Reports</h3>

            {summaryData && (
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
                  <h4 className="font-medium text-lsc-dark dark:text-lsc-cream mb-4">Equipment by Type</h4>
                  <div className="space-y-2">
                    {summaryData.types_breakdown && Object.entries(summaryData.types_breakdown).map(([type, count]) => (
                      <div key={type} className="flex items-center justify-between">
                        <span className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80">{formatEquipmentType(type as EquipmentType)}</span>
                        <span className="font-medium text-lsc-dark dark:text-lsc-cream">{count}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
                  <h4 className="font-medium text-lsc-dark dark:text-lsc-cream mb-4">Quick Stats</h4>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80">Total Value</span>
                      <span className="font-medium text-lsc-dark dark:text-lsc-cream">${Number(summaryData.total_value || 0).toLocaleString()}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80">Pending Maintenance</span>
                      <span className="font-medium text-status-warning-600 dark:text-status-warning-400">{summaryData.pending_maintenance}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80">Retired Items</span>
                      <span className="font-medium text-lsc-dark/70 dark:text-lsc-cream/70">{summaryData.retired_count}</span>
                    </div>
                  </div>
                </div>

                <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
                  <h4 className="font-medium text-lsc-dark dark:text-lsc-cream mb-4">Generate Reports</h4>
                  <div className="space-y-2">
                    <button className="w-full flex items-center justify-between p-3 bg-lsc-cream dark:bg-earth-700/50 rounded-lg hover:bg-lsc-border dark:hover:bg-earth-700 transition-colors text-left">
                      <span className="text-sm text-lsc-dark dark:text-lsc-cream">Utilization Report</span>
                      <ChevronRight className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/60" />
                    </button>
                    <button className="w-full flex items-center justify-between p-3 bg-lsc-cream dark:bg-earth-700/50 rounded-lg hover:bg-lsc-border dark:hover:bg-earth-700 transition-colors text-left">
                      <span className="text-sm text-lsc-dark dark:text-lsc-cream">Popular Equipment</span>
                      <ChevronRight className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/60" />
                    </button>
                    <button className="w-full flex items-center justify-between p-3 bg-lsc-cream dark:bg-earth-700/50 rounded-lg hover:bg-lsc-border dark:hover:bg-earth-700 transition-colors text-left">
                      <span className="text-sm text-lsc-dark dark:text-lsc-cream">Maintenance History</span>
                      <ChevronRight className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/60" />
                    </button>
                    <button className="w-full flex items-center justify-between p-3 bg-lsc-cream dark:bg-earth-700/50 rounded-lg hover:bg-lsc-border dark:hover:bg-earth-700 transition-colors text-left">
                      <span className="text-sm text-lsc-dark dark:text-lsc-cream">Overdue Report</span>
                      <ChevronRight className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/60" />
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {showEquipmentForm && (
          <EquipmentFormModal
            editingEquipment={editingEquipment}
            formData={equipmentForm}
            onChange={setEquipmentForm}
            onSubmit={handleSubmitEquipmentForm}
            onClose={() => { setShowEquipmentForm(false); setEditingEquipment(null) }}
            isPending={createEquipmentMutation.isPending || updateEquipmentMutation.isPending}
          />
        )}

        {showCheckoutModal && selectedEquipment && (
          <CheckoutModal
            equipment={selectedEquipment}
            patronId={checkoutPatronId}
            notes={checkoutNotes}
            depositCollected={depositCollected}
            isPending={checkoutMutation.isPending}
            onPatronIdChange={setCheckoutPatronId}
            onNotesChange={setCheckoutNotes}
            onDepositChange={setDepositCollected}
            onSubmit={(equipmentId, patronId, notes, deposit) =>
              checkoutMutation.mutate({
                equipmentId,
                patronId,
                ...(notes !== undefined && { notes }),
                ...(deposit !== undefined && { deposit }),
              })
            }
            onClose={() => { setShowCheckoutModal(false); setSelectedEquipment(null) }}
          />
        )}

        {showMaintenanceForm && (
          <MaintenanceFormModal
            formData={maintenanceForm}
            equipmentList={equipmentData?.items}
            isPending={scheduleMaintenanceMutation.isPending}
            onChange={setMaintenanceForm}
            onSubmit={(e) => { e.preventDefault(); scheduleMaintenanceMutation.mutate(maintenanceForm) }}
            onClose={() => setShowMaintenanceForm(false)}
          />
        )}
      </div>
      <ConfirmDialog isOpen={confirmOpen} title="Retire equipment?" message={<><p>Are you sure you want to retire this equipment?</p><label className="block text-sm font-medium mt-3 mb-1">Retirement notes (optional)</label><input type="text" value={retirementNotes} onChange={(e) => setRetirementNotes(e.target.value)} className="w-full px-3 py-2 border rounded text-sm" placeholder="Reason for retirement" /></>} confirmText="Retire" confirmVariant="warning" onConfirm={() => { if (pendingRetireId) retireEquipmentMutation.mutate({ id: pendingRetireId, ...(retirementNotes && { notes: retirementNotes }) }); setConfirmOpen(false); setPendingRetireId(null) }} onCancel={() => { setConfirmOpen(false); setPendingRetireId(null) }} />
    </AdminShell>
  )
}
