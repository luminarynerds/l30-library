/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../contexts/AuthContext"
import { AdminShell } from '../components/shells/AdminShell'
import {
  Shield,
  ChevronLeft,
  Plus,
  X,
  Loader2,
  Clock,
  BarChart3,
  AlertTriangle,
  CheckCircle2,
  Eye,
  EyeOff,
} from "lucide-react"
import toast from "react-hot-toast"
import { emergencyOperationsAPI } from "../api/emergency-operations-api"
import { useTranslation} from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface ServicePriority {
  id: number
  service_name: string
  service_description?: string | null
  service_category: string
  priority: string
  rto_minutes: number
  rpo_minutes: number
  max_acceptable_downtime: number
  has_paper_process: boolean
  has_phone_process: boolean
  manual_workaround?: string | null
  estimated_manual_capacity?: string | null
  required_staff_roles?: string[] | null
  required_equipment?: string[] | null
  critical_forms?: string[] | null
}

export default function EmergencyOperationsServicePriorityPage(): React.ReactElement {
  const { t } = useTranslation()
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { user, token: _token, isLoading: authLoading, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  const [isLoading, setIsLoading] = useState(true)
  const [services, _setServices] = useState<ServicePriority[]>([])
  const [filterPriority, setFilterPriority] = useState<string | null>(null)
  const [filterCategory, setFilterCategory] = useState<string | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [expandedService, setExpandedService] = useState<number | null>(null)
  const [isSaving, setIsSaving] = useState(false)

  const [form, setForm] = useState({
    service_name: "",
    service_description: "",
    service_category: "",
    priority: "",
    rto_minutes: 60,
    rpo_minutes: 30,
    max_acceptable_downtime: 60,
    manual_workaround: "",
    required_staff_roles: [] as string[],
    critical_forms: [] as string[],
  })

  const categories = [
    "Circulation",
    "Catalog",
    "Patron Services",
    "Events",
    "Learning",
    "Communications",
    "Administration",
  ]

  const priorities = [
    { id: "critical", label: "Critical", color: "bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-800 dark:text-status-danger-300 border-status-danger-300 dark:border-status-danger-700" },
    { id: "high", label: "High", color: "bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-300 border-status-warning-300 dark:border-status-warning-700" },
    { id: "medium", label: "Medium", color: "bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-300 border-status-warning-300 dark:border-status-warning-700" },
    { id: "low", label: "Low", color: "bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-300 border-status-success-300 dark:border-status-success-700" },
  ]

  useEffect(() => {
    if (!isAuthenticated) {
      navigate("/login")
      return
    }

    if (!["admin", "director", "super_admin"].includes(user?.role?.toLowerCase() ?? '')) {
      navigate("/")
      return
    }

    setIsLoading(false)
  }, [isAuthenticated, user?.role, navigate])

  const handleCreateService = async () => {
    if (!form.service_name || !form.service_category || !form.priority) {
      toast.error(t('emergencyOperationsServicePriority.pleaseFillInAllRequired'))
      return
    }

    try {
      setIsSaving(true)
      await emergencyOperationsAPI.serviceContinuity.createServicePriority({
        service_name: form.service_name,
        service_description: form.service_description,
        service_category: form.service_category,
        priority: form.priority,
        rto_minutes: form.rto_minutes,
        rpo_minutes: form.rpo_minutes,
        max_acceptable_downtime: form.max_acceptable_downtime,
        manual_workaround: form.manual_workaround || undefined,
        required_staff_roles: form.required_staff_roles.length > 0 ? form.required_staff_roles : undefined,
        critical_forms: form.critical_forms.length > 0 ? form.critical_forms : undefined,
      })

      toast.success(t('emergencyOperationsServicePriority.servicePriorityCreatedSuccessfully'))
      setShowCreateModal(false)
      resetForm()
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('emergencyOperationsServicePriority.failedToCreateServicePriority'))
    } finally {
      setIsSaving(false)
    }
  }

  const resetForm = () => {
    setForm({
      service_name: "",
      service_description: "",
      service_category: "",
      priority: "",
      rto_minutes: 60,
      rpo_minutes: 30,
      max_acceptable_downtime: 60,
      manual_workaround: "",
      required_staff_roles: [],
      critical_forms: [],
    })
  }

  if (authLoading || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" />
      </div>
    )
  }

  const filteredServices = services.filter((service) => {
    if (filterPriority && service.priority !== filterPriority) return false
    if (filterCategory && service.service_category !== filterCategory) return false
    return true
  })

  const priorityCounts = {
    critical: services.filter((s) => s.priority === "critical").length,
    high: services.filter((s) => s.priority === "high").length,
    medium: services.filter((s) => s.priority === "medium").length,
    low: services.filter((s) => s.priority === "low").length,
  }

  return (
    <AdminShell title="Service Continuity Priorities" subtitle={t('emergencyOperationsServicePriority.recoveryTimeObjectivesRtoAnd')}>
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
            Add Service
          </button>
        </div>

        {/* Priority Summary */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border-2 border-status-danger-300 dark:border-status-danger-700 rounded-lg p-6">
            <div className="text-3xl font-bold text-status-danger-600">{priorityCounts.critical}</div>
            <div className="text-sm font-semibold text-status-danger-900 dark:text-status-danger-200">Critical Services</div>
            <p className="text-xs text-status-danger-700 dark:text-status-danger-300 mt-1">RTO: 0-1 hour</p>
          </div>

          <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border-2 border-status-warning-300 dark:border-status-warning-700 rounded-lg p-6">
            <div className="text-3xl font-bold text-status-warning-600">{priorityCounts.high}</div>
            <div className="text-sm font-semibold text-status-warning-900 dark:text-status-warning-200">High Priority</div>
            <p className="text-xs text-status-warning-700 dark:text-status-warning-300 mt-1">RTO: 1-4 hours</p>
          </div>

          <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border-2 border-status-warning-300 dark:border-status-warning-700 rounded-lg p-6">
            <div className="text-3xl font-bold text-status-warning-600">{priorityCounts.medium}</div>
            <div className="text-sm font-semibold text-status-warning-900 dark:text-status-warning-200">Medium Priority</div>
            <p className="text-xs text-status-warning-700 dark:text-status-warning-300 mt-1">RTO: 4-24 hours</p>
          </div>

          <div className="bg-status-success-50 dark:bg-status-success-900/20 border-2 border-status-success-300 dark:border-status-success-700 rounded-lg p-6">
            <div className="text-3xl font-bold text-status-success-600">{priorityCounts.low}</div>
            <div className="text-sm font-semibold text-status-success-900 dark:text-status-success-200">Low Priority</div>
            <p className="text-xs text-status-success-700 dark:text-status-success-300 mt-1">RTO: 24+ hours</p>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border-2 border-lsc-border dark:border-earth-700 p-4 mb-6 flex gap-4 flex-wrap items-end">
          <div>
            <label className="block font-semibold mb-2 text-sm">Filter by Priority</label>
            <select
              value={filterPriority || ""}
              onChange={(e) => setFilterPriority(e.target.value || null)}
              className="p-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-status-success-500 outline-none"
            >
              <option value="">All Priorities</option>
              {priorities.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block font-semibold mb-2 text-sm">Filter by Category</label>
            <select
              value={filterCategory || ""}
              onChange={(e) => setFilterCategory(e.target.value || null)}
              className="p-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-status-success-500 outline-none"
            >
              <option value="">All Categories</option>
              {categories.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={() => {
              setFilterPriority(null)
              setFilterCategory(null)
            }}
            className="px-3 py-2 bg-earth-200 dark:bg-earth-600 hover:bg-earth-300 dark:hover:bg-earth-500 rounded-lg transition-colors text-sm font-semibold"
          >
            Clear Filters
          </button>
        </div>

        {/* Services List */}
        {filteredServices.length > 0 ? (
          <div className="space-y-4">
            {filteredServices.map((service) => {
              const priorityConfig = priorities.find((p) => p.id === service.priority)
              return (
                <div
                  key={service.id}
                  className={`bg-lsc-white dark:bg-earth-800 rounded-lg border-2 p-6 hover:shadow-lg transition-shadow cursor-pointer ${priorityConfig?.color}`}
                  onClick={() => setExpandedService(expandedService === service.id ? null : service.id)} tabIndex={0} role="button" onKeyDown={(e: React.KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); (() => setExpandedService(expandedService === service.id ? null : service.id))(); } }}
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex-1">
                      <h3 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">{service.service_name}</h3>
                      {service.service_description && (
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{service.service_description}</p>
                      )}
                    </div>

                    {expandedService === service.id ? (
                      <EyeOff className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70 ml-3 flex-shrink-0" />
                    ) : (
                      <Eye className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70 ml-3 flex-shrink-0" />
                    )}
                  </div>

                  {/* Key Metrics */}
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
                    <div className="p-3 bg-lsc-white dark:bg-earth-800 rounded border-2 border-lsc-border dark:border-earth-700">
                      <div className="text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">RTO</div>
                      <div className="text-lg font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-1">
                        <Clock className="w-4 h-4" />
                        {service.rto_minutes}min
                      </div>
                    </div>

                    <div className="p-3 bg-lsc-white dark:bg-earth-800 rounded border-2 border-lsc-border dark:border-earth-700">
                      <div className="text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">RPO</div>
                      <div className="text-lg font-bold text-lsc-dark dark:text-lsc-cream flex items-center gap-1">
                        <BarChart3 className="w-4 h-4" />
                        {service.rpo_minutes}min
                      </div>
                    </div>

                    <div className="p-3 bg-lsc-white dark:bg-earth-800 rounded border-2 border-lsc-border dark:border-earth-700">
                      <div className="text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">Category</div>
                      <div className="text-lg font-bold text-lsc-dark dark:text-lsc-cream">{service.service_category}</div>
                    </div>

                    <div className="p-3 bg-lsc-white dark:bg-earth-800 rounded border-2 border-lsc-border dark:border-earth-700">
                      <div className="text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">Fallback</div>
                      <div className="text-sm font-bold text-lsc-dark dark:text-lsc-cream">
                        {service.has_paper_process || service.has_phone_process ? (
                          <CheckCircle2 className="w-5 h-5 text-status-success-600" />
                        ) : (
                          <AlertTriangle className="w-5 h-5 text-status-danger-600" />
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Expanded Details */}
                  {expandedService === service.id && (
                    <div className="mt-4 pt-4 border-t-2 border-lsc-border dark:border-earth-700 space-y-3">
                      {service.manual_workaround && (
                        <div>
                          <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">Manual Workaround:</h4>
                          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 bg-lsc-white dark:bg-earth-800 p-3 rounded border border-lsc-border dark:border-earth-700">
                            {service.manual_workaround}
                          </p>
                        </div>
                      )}

                      {(service.has_paper_process || service.has_phone_process) && (
                        <div>
                          <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">Fallback Procedures:</h4>
                          <div className="flex gap-2">
                            {service.has_paper_process && (
                              <span className="px-3 py-1 bg-lsc-white dark:bg-earth-800 rounded border-2 border-lsc-border dark:border-earth-700 text-sm font-semibold">
                                📋 Paper Forms
                              </span>
                            )}
                            {service.has_phone_process && (
                              <span className="px-3 py-1 bg-lsc-white dark:bg-earth-800 rounded border-2 border-lsc-border dark:border-earth-700 text-sm font-semibold">
                                ☎️ Phone Process
                              </span>
                            )}
                          </div>
                        </div>
                      )}

                      {service.required_staff_roles && service.required_staff_roles.length > 0 && (
                        <div>
                          <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">Required Staff:</h4>
                          <div className="flex flex-wrap gap-1">
                            {service.required_staff_roles.map((role) => (
                              <span
                                key={role}
                                className="px-2 py-1 bg-lsc-white dark:bg-earth-800 rounded border border-lsc-border dark:border-earth-700 text-xs font-semibold"
                              >
                                {role}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {service.critical_forms && service.critical_forms.length > 0 && (
                        <div>
                          <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">Critical Forms:</h4>
                          <div className="flex flex-wrap gap-1">
                            {service.critical_forms.map((form) => (
                              <span
                                key={form}
                                className="px-2 py-1 bg-lsc-white dark:bg-earth-800 rounded border border-lsc-border dark:border-earth-700 text-xs font-semibold"
                              >
                                {form}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        ) : (
          <div className="bg-status-success-50 dark:bg-status-success-900/20 border-2 border-status-success-200 dark:border-status-success-800 rounded-lg p-8 text-center">
            <Shield className="w-12 h-12 text-status-success-600 mx-auto mb-3" />
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 font-semibold">{t('emergencyOperationsServicePriority.noServicesConfiguredYet')}</p>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm mt-1">{t('emergencyOperationsServicePriority.addServicesToEstablishYour')}</p>
          </div>
        )}

      {/* Create Service Modal */}
      {showCreateModal && (
        <ModalBackdrop onClose={() => setShowCreateModal(false)} title="Dialog">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg max-w-2xl w-full mx-4 my-8 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-serif font-bold flex items-center gap-2">
                <Shield className="w-6 h-6 text-status-success-600" />
                Add Service Priority
              </h2>
              <button onClick={() => setShowCreateModal(false)}>
                <X className="w-6 h-6" />
              </button>
            </div>

            <div className="space-y-4 max-h-[70vh] overflow-y-auto">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block font-semibold mb-2">Service Name *</label>
                  <input
                    type="text"
                    value={form.service_name}
                    onChange={(e) => setForm({ ...form, service_name: e.target.value })}
                    placeholder={t('placeholder.emergencyOperationsServicePriority.egCirculationSystem')}
                    className="w-full p-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-status-success-500 outline-none"
                  />
                </div>

                <div>
                  <label className="block font-semibold mb-2">Category *</label>
                  <select
                    value={form.service_category}
                    onChange={(e) => setForm({ ...form, service_category: e.target.value })}
                    className="w-full p-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-status-success-500 outline-none"
                  >
                    <option value="">Select...</option>
                    {categories.map((cat) => (
                      <option key={cat} value={cat}>
                        {cat}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block font-semibold mb-2">Description</label>
                <textarea
                  value={form.service_description}
                  onChange={(e) => setForm({ ...form, service_description: e.target.value })}
                  placeholder={t('placeholder.emergencyOperationsServicePriority.describeTheService')}
                  className="w-full p-3 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-status-success-500 outline-none"
                  rows={2}
                />
              </div>

              <div>
                <label className="block font-semibold mb-2">Priority Level *</label>
                <select
                  value={form.priority}
                  onChange={(e) => setForm({ ...form, priority: e.target.value })}
                  className="w-full p-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-status-success-500 outline-none"
                >
                  <option value="">Select...</option>
                  {priorities.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block font-semibold mb-2">RTO (minutes)</label>
                  <input
                    type="number"
                    min="0"
                    value={form.rto_minutes}
                    onChange={(e) => setForm({ ...form, rto_minutes: parseInt(e.target.value) || 0 })}
                    className="w-full p-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-status-success-500 outline-none"
                  />
                </div>

                <div>
                  <label className="block font-semibold mb-2">RPO (minutes)</label>
                  <input
                    type="number"
                    min="0"
                    value={form.rpo_minutes}
                    onChange={(e) => setForm({ ...form, rpo_minutes: parseInt(e.target.value) || 0 })}
                    className="w-full p-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-status-success-500 outline-none"
                  />
                </div>

                <div>
                  <label className="block font-semibold mb-2">Max Downtime</label>
                  <input
                    type="number"
                    min="0"
                    value={form.max_acceptable_downtime}
                    onChange={(e) => setForm({ ...form, max_acceptable_downtime: parseInt(e.target.value) || 0 })}
                    className="w-full p-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-status-success-500 outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold mb-2">Manual Workaround</label>
                <textarea
                  value={form.manual_workaround}
                  onChange={(e) => setForm({ ...form, manual_workaround: e.target.value })}
                  placeholder={t('emergencyOperationsServicePriority.describeManualBackupProcedures')}
                  className="w-full p-3 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-status-success-500 outline-none"
                  rows={2}
                />
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
                  onClick={handleCreateService}
                  disabled={isSaving}
                  className="flex-1 px-4 py-2 bg-status-success-600 text-white rounded-lg hover:bg-status-success-700 font-semibold disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {isSaving ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Plus className="w-4 h-4" />}
                  Add Service
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
