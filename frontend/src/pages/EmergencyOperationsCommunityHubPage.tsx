/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../contexts/AuthContext"
import { AdminShell } from '../components/shells/AdminShell'
import {
  Users,
  ChevronLeft,
  Plus,
  X,
  Loader2,
  Power,
  MapPin,
  CheckCircle2,
  AlertCircle,
  TrendingUp,
} from "lucide-react"
import toast from "react-hot-toast"
import { emergencyOperationsAPI } from "../api/emergency-operations-api"
import { listBranches, type Branch } from "../api/branch-api"
import { useTranslation} from '@/i18n'
import { clean } from '@/lib/utils'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface HubData {
  id: number
  hub_name: string
  branch_id: number
  location_description: string
  hub_purposes: string[]
  emergency_types: string[]
  max_capacity: number
  is_active: boolean
  activated_at?: string | null
  deactivated_at?: string | null
  activation_reason?: string | null
  activation_message?: string | null
  current_capacity_used: number
  visitors_served_count: number
  supplies_stocked: boolean
  equipment_tested: boolean
  staff_trained: boolean
  created_at: string
}

export default function EmergencyOperationsCommunityHubPage(): React.ReactElement {
  const { t } = useTranslation()
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { user, token: _token, isLoading: authLoading, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  const [isLoading, setIsLoading] = useState(true)
  const [hubs, setHubs] = useState<HubData[]>([])
  const [branches, setBranches] = useState<Branch[]>([])
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showActivateModal, setShowActivateModal] = useState(false)
  const [selectedHub, setSelectedHub] = useState<HubData | null>(null)
  const [isSaving, setIsSaving] = useState(false)

  const hubPurposes = [
    { id: "emergency_shelter", label: "Emergency Shelter" },
    { id: "charging_station", label: "Charging Station" },
    { id: "food_water", label: "Food & Water Distribution" },
    { id: "medical_services", label: "Medical Services" },
    { id: "communication_hub", label: "Communication Hub" },
    { id: "information_center", label: "Information Center" },
    { id: "wifi_access", label: "WiFi Access" },
    { id: "restroom_facilities", label: "Restroom Facilities" },
  ]

  const emergencyTypes = [
    { id: "natural_disaster", label: "Natural Disaster" },
    { id: "power_outage", label: "Power Outage" },
    { id: "pandemic", label: "Pandemic/Health Crisis" },
    { id: "infrastructure_failure", label: "Infrastructure Failure" },
    { id: "security_incident", label: "Security Incident" },
    { id: "weather_emergency", label: "Weather Emergency" },
    { id: "utility_failure", label: "Utility Failure" },
    { id: "community_crisis", label: "Community Crisis" },
  ]

  const [form, setForm] = useState({
    hub_name: "",
    branch_id: 0,
    location_description: "",
    hub_purposes: [] as string[],
    emergency_types: [] as string[],
    max_capacity: 50,
    volunteer_coordinator_id: undefined as number | undefined,
  })

  const [activateForm, setActivateForm] = useState({
    activation_reason: "",
    activation_message: "",
  })

  const loadHubs = useCallback(async () => {
    try {
      setIsLoading(true)
      const data = await emergencyOperationsAPI.communityResourceHub.getActiveHubs()
      setHubs(data)
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('emergencyOperationsCommunityHub.failedToLoadCommunityHubs'))
    } finally {
      setIsLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])


  useEffect(() => {
    if (!isAuthenticated) {
      navigate("/login")
      return
    }

    if (!["admin", "director", "super_admin"].includes(user?.role?.toLowerCase() ?? '')) {
      navigate("/")
      return
    }

    loadHubs()
    listBranches({ active_only: true })
      .then((data) => {
        setBranches(data)
        setForm((prev) => ({
          ...prev,
          branch_id: prev.branch_id || data[0]?.id || 0,
        }))
      })
      .catch((error: unknown) => {
        Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, user?.role, navigate])

  const handleCreateHub = async () => {
    if (!form.hub_name.trim() || !form.location_description.trim()) {
      toast.error(t('emergencyOperationsCommunityHub.pleaseFillInAllRequired'))
      return
    }

    if (!form.branch_id) {
      toast.error(t('emergencyOperationsCommunityHub.pleaseFillInAllRequired'))
      return
    }

    if (form.hub_purposes.length === 0) {
      toast.error(t('emergencyOperationsCommunityHub.pleaseSelectAtLeastOne'))
      return
    }

    if (form.emergency_types.length === 0) {
      toast.error(t('emergencyOperationsCommunityHub.pleaseSelectAtLeastOne2'))
      return
    }

    try {
      setIsSaving(true)
      await emergencyOperationsAPI.communityResourceHub.createHub(clean({
        hub_name: form.hub_name,
        branch_id: form.branch_id,
        location_description: form.location_description,
        hub_purposes: form.hub_purposes,
        emergency_types: form.emergency_types,
        max_capacity: form.max_capacity,
        volunteer_coordinator_id: form.volunteer_coordinator_id,
      }))

      toast.success(t('emergencyOperationsCommunityHub.communityHubCreatedSuccessfully'))
      setShowCreateModal(false)
      resetForm()
      loadHubs()
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('emergencyOperationsCommunityHub.failedToCreateCommunityHub'))
    } finally {
      setIsSaving(false)
    }
  }

  const handleActivateHub = async () => {
    if (!selectedHub || !activateForm.activation_reason.trim()) {
      toast.error(t('emergencyOperationsCommunityHub.pleaseProvideActivationReason'))
      return
    }

    try {
      setIsSaving(true)
      await emergencyOperationsAPI.communityResourceHub.activateHub(selectedHub.id, {
        activation_reason: activateForm.activation_reason,
        activation_message: activateForm.activation_message,
      })

      toast.success(t('emergencyOperationsCommunityHub.communityHubActivatedSuccessfully'))
      setShowActivateModal(false)
      setActivateForm({ activation_reason: "", activation_message: "" })
      loadHubs()
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('emergencyOperationsCommunityHub.failedToActivateCommunityHub'))
    } finally {
      setIsSaving(false)
    }
  }

  const handleDeactivateHub = async (hubId: number) => {
    try {
      setIsSaving(true)
      await emergencyOperationsAPI.communityResourceHub.deactivateHub(hubId)
      toast.success(t('toast.emergencyOperationsCommunityHub.communityHubDeactivated'))
      loadHubs()
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('emergencyOperationsCommunityHub.failedToDeactivateHub'))
    } finally {
      setIsSaving(false)
    }
  }

  const resetForm = () => {
    setForm({
      hub_name: "",
      branch_id: branches[0]?.id || 0,
      location_description: "",
      hub_purposes: [],
      emergency_types: [],
      max_capacity: 50,
      volunteer_coordinator_id: undefined,
    })
  }

  if (authLoading || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" />
      </div>
    )
  }

  return (
    <AdminShell title="Community Resource Hubs" subtitle={t('emergencyOperationsCommunityHub.emergencyCommunitySupportCenters')}>
      <div>
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={() => navigate("/emergency-operations")} className="hover:text-lsc-rose">
              <ChevronLeft className="w-6 h-6" />
            </button>
            <div></div>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-status-success-600 text-white rounded-lg hover:bg-status-success-700 transition-colors font-semibold flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Create Hub
          </button>
        </div>

        {/* Active Hubs */}
        {hubs.filter((h) => h.is_active).length > 0 ? (
          <div className="space-y-6 mb-8">
            <h2 className="text-2xl font-serif font-bold">Active Hubs</h2>
            {hubs
              .filter((h) => h.is_active)
              .map((hub) => (
                <div
                  key={hub.id}
                  className="bg-lsc-white dark:bg-earth-800 rounded-lg border-2 border-status-success-300 dark:border-status-success-700 p-6 hover:shadow-lg transition-shadow"
                >
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Hub Info */}
                    <div>
                      <div className="flex items-start gap-3 mb-4">
                        <div className="p-3 bg-status-success-100 dark:bg-status-success-900/30 rounded-lg">
                          <Users className="w-6 h-6 text-status-success-600" />
                        </div>
                        <div>
                          <h3 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">{hub.hub_name}</h3>
                          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1 flex items-center gap-1">
                            <MapPin className="w-4 h-4" />
                            {hub.location_description}
                          </p>
                        </div>
                      </div>

                      {hub.activation_reason && (
                        <div className="mt-3 p-3 bg-status-success-50 dark:bg-status-success-900/20 rounded border border-status-success-200 dark:border-status-success-800">
                          <p className="text-sm font-semibold text-status-success-900 dark:text-status-success-200">Activation Reason:</p>
                          <p className="text-sm text-status-success-800 dark:text-status-success-300">{hub.activation_reason}</p>
                        </div>
                      )}
                    </div>

                    {/* Capacity & Services */}
                    <div>
                      <h4 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">Capacity & Services</h4>

                      <div className="space-y-3">
                        <div>
                          <div className="flex justify-between mb-2">
                            <span className="font-semibold text-sm">Occupancy</span>
                            <span className="text-sm font-bold">
                              {hub.current_capacity_used} / {hub.max_capacity}
                            </span>
                          </div>
                          <div className="w-full bg-earth-200 dark:bg-earth-600 rounded-full h-2 overflow-hidden">
                            <div
                              className="bg-status-success-600 h-full transition-all"
                              style={{ width: `${(hub.current_capacity_used / hub.max_capacity) * 100}%` }}
                            />
                          </div>
                        </div>

                        <div className="flex items-center gap-2 pt-2">
                          <TrendingUp className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light" />
                          <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                            <strong>{hub.visitors_served_count}</strong> visitors served
                          </span>
                        </div>

                        <div className="pt-2">
                          <p className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream mb-2">Services Offered:</p>
                          <div className="flex flex-wrap gap-1">
                            {hub.hub_purposes.map((purpose) => (
                              <span
                                key={purpose}
                                className="px-2 py-1 bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-300 rounded text-xs font-semibold"
                              >
                                {purpose}
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Status Checklist */}
                    <div>
                      <h4 className="font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">Readiness Checklist</h4>

                      <div className="space-y-2">
                        <div className="flex items-center gap-2 p-2 bg-earth-50 dark:bg-earth-900 rounded">
                          {hub.supplies_stocked ? (
                            <CheckCircle2 className="w-5 h-5 text-status-success-600 flex-shrink-0" />
                          ) : (
                            <AlertCircle className="w-5 h-5 text-status-warning-600 flex-shrink-0" />
                          )}
                          <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                            {hub.supplies_stocked ? "✓" : "✗"} Supplies Stocked
                          </span>
                        </div>

                        <div className="flex items-center gap-2 p-2 bg-earth-50 dark:bg-earth-900 rounded">
                          {hub.equipment_tested ? (
                            <CheckCircle2 className="w-5 h-5 text-status-success-600 flex-shrink-0" />
                          ) : (
                            <AlertCircle className="w-5 h-5 text-status-warning-600 flex-shrink-0" />
                          )}
                          <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                            {hub.equipment_tested ? "✓" : "✗"} Equipment Tested
                          </span>
                        </div>

                        <div className="flex items-center gap-2 p-2 bg-earth-50 dark:bg-earth-900 rounded">
                          {hub.staff_trained ? (
                            <CheckCircle2 className="w-5 h-5 text-status-success-600 flex-shrink-0" />
                          ) : (
                            <AlertCircle className="w-5 h-5 text-status-warning-600 flex-shrink-0" />
                          )}
                          <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                            {hub.staff_trained ? "✓" : "✗"} Staff Trained
                          </span>
                        </div>
                      </div>

                      <button
                        onClick={() => handleDeactivateHub(hub.id)}
                        disabled={isSaving}
                        className="w-full mt-4 px-3 py-2 bg-status-danger-600 text-white rounded-lg hover:bg-status-danger-700 transition-colors font-semibold disabled:opacity-50 flex items-center justify-center gap-2 text-sm"
                      >
                        <Power className="w-4 h-4" />
                        Deactivate Hub
                      </button>
                    </div>
                  </div>
                </div>
              ))}
          </div>
        ) : (
          <div className="bg-status-success-50 dark:bg-status-success-900/20 border-2 border-status-success-200 dark:border-status-success-800 rounded-lg p-8 text-center mb-8">
            <Users className="w-12 h-12 text-status-success-600 mx-auto mb-3" />
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 font-semibold">{t('emergencyOperationsCommunityHub.noActiveCommunityHubs')}</p>
          </div>
        )}

        {/* Available Hubs for Activation */}
        {hubs.filter((h) => !h.is_active).length > 0 && (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border-2 border-lsc-border dark:border-earth-700 p-6">
            <h2 className="font-serif text-xl font-bold mb-4">Available Hubs (Inactive)</h2>
            <div className="space-y-3">
              {hubs
                .filter((h) => !h.is_active)
                .map((hub) => (
                  <div key={hub.id} className="p-4 bg-earth-50 dark:bg-earth-900 rounded border border-lsc-border dark:border-earth-700">
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{hub.hub_name}</h4>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{hub.location_description}</p>
                      </div>
                      <button
                        onClick={() => {
                          setSelectedHub(hub)
                          setShowActivateModal(true)
                        }}
                        className="px-4 py-2 bg-status-success-600 text-white rounded-lg hover:bg-status-success-700 transition-colors font-semibold flex items-center gap-2"
                      >
                        <Power className="w-4 h-4" />
                        Activate
                      </button>
                    </div>
                  </div>
                ))}
            </div>
          </div>
        )}

      {/* Create Hub Modal */}
      {showCreateModal && (
        <ModalBackdrop
          onClose={() => setShowCreateModal(false)}
          labelledBy="create-hub-modal-title"
        >
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg max-w-lg w-full mx-4 p-6 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 id="create-hub-modal-title" className="text-2xl font-serif font-bold flex items-center gap-2">
                <Users aria-hidden="true" className="w-6 h-6 text-status-success-600" />
                Create Community Hub
              </h2>
              <button
                onClick={() => setShowCreateModal(false)}
                aria-label="Close Create Community Hub dialog"
              >
                <X aria-hidden="true" className="w-6 h-6" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block font-semibold mb-2">Hub Name *</label>
                <input
                  type="text"
                  value={form.hub_name}
                  onChange={(e) => setForm({ ...form, hub_name: e.target.value })}
                  placeholder={t('placeholder.emergencyOperationsCommunityHub.egMainLibraryEmergency')}
                  className="w-full p-3 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-status-success-500 outline-none"
                />
              </div>

              <div>
                <label className="block font-semibold mb-2">Branch *</label>
                <select
                  value={form.branch_id}
                  onChange={(e) => setForm({ ...form, branch_id: parseInt(e.target.value, 10) || 0 })}
                  className="w-full p-3 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-status-success-500 outline-none bg-lsc-white dark:bg-earth-900"
                >
                  <option value={0}>Select a branch…</option>
                  {branches.map((branch) => (
                    <option key={branch.id} value={branch.id}>
                      {branch.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-semibold mb-2">Location Description *</label>
                <textarea
                  value={form.location_description}
                  onChange={(e) => setForm({ ...form, location_description: e.target.value })}
                  placeholder={t('emergencyOperationsCommunityHub.describeThePhysicalLocation')}
                  className="w-full p-3 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-status-success-500 outline-none"
                  rows={2}
                />
              </div>

              <div>
                <label className="block font-semibold mb-2">Maximum Capacity</label>
                <input
                  type="number"
                  min="10"
                  value={form.max_capacity}
                  onChange={(e) => setForm({ ...form, max_capacity: parseInt(e.target.value) })}
                  className="w-full p-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-status-success-500 outline-none"
                />
              </div>

              <div>
                <label className="block font-semibold mb-2">Hub Purposes *</label>
                <div className="space-y-2 max-h-40 overflow-y-auto">
                  {hubPurposes.map((purpose) => (
                    <label key={purpose.id} className="flex items-center gap-2 p-2 hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800">
                      <input
                        type="checkbox"
                        checked={form.hub_purposes.includes(purpose.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setForm({
                              ...form,
                              hub_purposes: [...form.hub_purposes, purpose.id],
                            })
                          } else {
                            setForm({
                              ...form,
                              hub_purposes: form.hub_purposes.filter((p) => p !== purpose.id),
                            })
                          }
                        }}
                      />
                      <span>{purpose.label}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <label className="block font-semibold mb-2">Emergency Types *</label>
                <div className="space-y-2 max-h-40 overflow-y-auto">
                  {emergencyTypes.map((type) => (
                    <label key={type.id} className="flex items-center gap-2 p-2 hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800">
                      <input
                        type="checkbox"
                        checked={form.emergency_types.includes(type.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setForm({
                              ...form,
                              emergency_types: [...form.emergency_types, type.id],
                            })
                          } else {
                            setForm({
                              ...form,
                              emergency_types: form.emergency_types.filter((t) => t !== type.id),
                            })
                          }
                        }}
                      />
                      <span>{type.label}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setShowCreateModal(false)}
                  disabled={isSaving}
                  className="flex-1 px-4 py-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800 font-semibold disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateHub}
                  disabled={isSaving}
                  className="flex-1 px-4 py-2 bg-status-success-600 text-white rounded-lg hover:bg-status-success-700 font-semibold disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {isSaving ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Plus className="w-4 h-4" />}
                  Create Hub
                </button>
              </div>
            </div>
          </div>
        </ModalBackdrop>
      )}

      {/* Activate Hub Modal */}
      {showActivateModal && selectedHub && (
        <ModalBackdrop
          onClose={() => setShowActivateModal(false)}
          labelledBy="activate-hub-modal-title"
          describedBy="activate-hub-modal-desc"
        >
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg max-w-lg w-full mx-4 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 id="activate-hub-modal-title" className="text-2xl font-serif font-bold flex items-center gap-2">
                <Power aria-hidden="true" className="w-6 h-6 text-status-success-600" />
                Activate Hub
              </h2>
              <button
                onClick={() => setShowActivateModal(false)}
                aria-label="Close Activate Hub dialog"
              >
                <X aria-hidden="true" className="w-6 h-6" />
              </button>
            </div>

            <p id="activate-hub-modal-desc" className="text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
              Activating <strong>{selectedHub.hub_name}</strong> as an emergency community resource hub.
            </p>

            <div className="space-y-4">
              <div>
                <label className="block font-semibold mb-2">Activation Reason *</label>
                <textarea
                  value={activateForm.activation_reason}
                  onChange={(e) => setActivateForm({ ...activateForm, activation_reason: e.target.value })}
                  placeholder={t('emergencyOperationsCommunityHub.whyIsThisHubBeing')}
                  className="w-full p-3 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-status-success-500 outline-none"
                  rows={3}
                />
              </div>

              <div>
                <label className="block font-semibold mb-2">Public Message</label>
                <textarea
                  value={activateForm.activation_message}
                  onChange={(e) => setActivateForm({ ...activateForm, activation_message: e.target.value })}
                  placeholder={t('emergencyOperationsCommunityHub.messageToDisplayToCommunity')}
                  className="w-full p-3 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-status-success-500 outline-none"
                  rows={2}
                />
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => setShowActivateModal(false)}
                  disabled={isSaving}
                  className="flex-1 px-4 py-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800 font-semibold disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleActivateHub}
                  disabled={isSaving}
                  className="flex-1 px-4 py-2 bg-status-success-600 text-white rounded-lg hover:bg-status-success-700 font-semibold disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {isSaving ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Power className="w-4 h-4" />}
                  Activate Now
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
