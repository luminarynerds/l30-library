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
  Package,
  ChevronLeft,
  Plus,
  X,
  Loader2,
  CheckCircle2,
  AlertCircle,
  TrendingUp,
  BarChart3,
  Eye,
  EyeOff,
} from "lucide-react"
import toast from "react-hot-toast"
import { emergencyOperationsAPI } from "../api/emergency-operations-api"
import { useTranslation} from '@/i18n'
import { clean } from '@/lib/utils'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface RecoveryProject {
  id: number
  project_name: string
  project_description?: string | null
  disaster_type: string
  disaster_date: string
  affected_areas: string[]
  estimated_items_affected?: number | null
  total_items_assessed: number
  items_salvaged: number
  items_lost: number
  is_active: boolean
  created_at: string
}

export default function EmergencyOperationsRecoveryPage(): React.ReactElement {
  const { t } = useTranslation()
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { user, token: _token, isLoading: authLoading, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  const [isLoading, setIsLoading] = useState(true)
  const [projects, setProjects] = useState<RecoveryProject[]>([])
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [_statistics, _setStatistics] = useState<any>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [expandedProject, setExpandedProject] = useState<number | null>(null)
  const [isSaving, setIsSaving] = useState(false)

  const disasterTypes = [
    { id: "fire", label: "Fire" },
    { id: "water_damage", label: "Water Damage" },
    { id: "mold", label: "Mold" },
    { id: "theft", label: "Theft" },
    { id: "vandalism", label: "Vandalism" },
    { id: "pest_damage", label: "Pest Damage" },
    { id: "flood", label: "Flood" },
    { id: "other", label: "Other" },
  ]

  const [form, setForm] = useState({
    project_name: "",
    project_description: "",
    disaster_type: "",
    disaster_date: "",
    affected_areas: [] as string[],
    estimated_items_affected: undefined as number | undefined,
  })

  const loadProjects = useCallback(async () => {
    try {
      setIsLoading(true)
      // In real implementation, would fetch from API
      setProjects([])
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('emergencyOperationsRecovery.failedToLoadRecoveryProjects'))
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

    if (!["admin", "director", "super_admin", "manager"].includes(user?.role?.toLowerCase() ?? '')) {
      navigate("/")
      return
    }

    loadProjects()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, user?.role, navigate])

  const handleCreateProject = async () => {
    if (!form.project_name.trim() || !form.disaster_type || !form.disaster_date) {
      toast.error(t('emergencyOperationsRecovery.pleaseFillInAllRequired'))
      return
    }

    try {
      setIsSaving(true)
      await emergencyOperationsAPI.collectionRecovery.createProject(clean({
        project_name: form.project_name,
        disaster_type: form.disaster_type,
        disaster_date: form.disaster_date,
        affected_areas: form.affected_areas,
        estimated_items_affected: form.estimated_items_affected,
      }))

      toast.success(t('emergencyOperationsRecovery.recoveryProjectCreatedSuccessfully'))
      setShowCreateModal(false)
      resetForm()
      loadProjects()
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('emergencyOperationsRecovery.failedToCreateRecoveryProject'))
    } finally {
      setIsSaving(false)
    }
  }

  const resetForm = () => {
    setForm({
      project_name: "",
      project_description: "",
      disaster_type: "",
      disaster_date: "",
      affected_areas: [],
      estimated_items_affected: undefined,
    })
  }

  if (authLoading || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" />
      </div>
    )
  }

  const totalItems = projects.reduce((sum, p) => sum + p.total_items_assessed, 0)
  const totalSalvaged = projects.reduce((sum, p) => sum + p.items_salvaged, 0)
  const totalLost = projects.reduce((sum, p) => sum + p.items_lost, 0)
  const salvageRate = totalItems > 0 ? ((totalSalvaged / totalItems) * 100).toFixed(1) : 0

  return (
    <AdminShell title="Collection Recovery Projects" subtitle={t('emergencyOperationsRecovery.trackDamagedItemsAndRecovery')}>
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
            className="px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/80 transition-colors font-semibold flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Create Project
          </button>
        </div>

        {/* Overall Statistics */}
        {projects.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border-2 border-lsc-border dark:border-earth-700 p-6">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Total Items</h3>
                <BarChart3 className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
              </div>
              <div className="text-3xl font-bold text-lsc-rose dark:text-lsc-rose-light">{totalItems}</div>
            </div>

            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border-2 border-status-success-200 dark:border-status-success-800 p-6">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-serif font-semibold text-status-success-900 dark:text-status-success-200">Salvaged</h3>
                <CheckCircle2 className="w-5 h-5 text-status-success-600" />
              </div>
              <div className="text-3xl font-bold text-status-success-600">{totalSalvaged}</div>
            </div>

            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border-2 border-status-danger-200 dark:border-status-danger-800 p-6">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-serif font-semibold text-status-danger-900 dark:text-status-danger-200">Lost/Unsalvageable</h3>
                <AlertCircle className="w-5 h-5 text-status-danger-600" />
              </div>
              <div className="text-3xl font-bold text-status-danger-600">{totalLost}</div>
            </div>

            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border-2 border-category-200 dark:border-category-800 p-6">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-serif font-semibold text-category-900 dark:text-category-200">Salvage Rate</h3>
                <TrendingUp className="w-5 h-5 text-category-600" />
              </div>
              <div className="text-3xl font-bold text-category-600">{salvageRate}%</div>
            </div>
          </div>
        )}

        {/* Recovery Projects */}
        {projects.length > 0 ? (
          <div className="space-y-6">
            <h2 className="text-2xl font-serif font-bold">Active Projects</h2>
            {projects.map((project) => (
              <div
                key={project.id}
                className="bg-lsc-white dark:bg-earth-800 rounded-lg border-2 border-lsc-rose/30 dark:border-lsc-rose/30 p-6 hover:shadow-lg transition-shadow"
              >
                <div
                  className="cursor-pointer"
                  onClick={() => setExpandedProject(expandedProject === project.id ? null : project.id)} tabIndex={0} role="button" onKeyDown={(e: React.KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); (() => setExpandedProject(expandedProject === project.id ? null : project.id))(); } }}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h3 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">{project.project_name}</h3>
                      {project.project_description && (
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{project.project_description}</p>
                      )}
                    </div>
                    {expandedProject === project.id ? (
                      <EyeOff className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
                    ) : (
                      <Eye className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
                    )}
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
                    <div className="p-3 bg-earth-50 dark:bg-earth-900 rounded border border-lsc-border dark:border-earth-700">
                      <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 font-semibold">Disaster Type</div>
                      <div className="text-lg font-bold text-lsc-dark dark:text-lsc-cream capitalize">{project.disaster_type}</div>
                    </div>

                    <div className="p-3 bg-earth-50 dark:bg-earth-900 rounded border border-lsc-border dark:border-earth-700">
                      <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 font-semibold">Date</div>
                      <div className="text-lg font-bold text-lsc-dark dark:text-lsc-cream">
                        {new Date(project.disaster_date).toLocaleDateString()}
                      </div>
                    </div>

                    <div className="p-3 bg-earth-50 dark:bg-earth-900 rounded border border-lsc-border dark:border-earth-700">
                      <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 font-semibold">Items Assessed</div>
                      <div className="text-lg font-bold text-lsc-dark dark:text-lsc-cream">{project.total_items_assessed}</div>
                    </div>

                    <div className="p-3 bg-earth-50 dark:bg-earth-900 rounded border border-lsc-border dark:border-earth-700">
                      <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 font-semibold">Status</div>
                      <div
                        className={`text-lg font-bold ${
                          project.is_active ? "text-lsc-rose dark:text-lsc-rose-light" : "text-lsc-dark/70 dark:text-lsc-cream/70"
                        }`}
                      >
                        {project.is_active ? "Active" : "Completed"}
                      </div>
                    </div>
                  </div>

                  {/* Progress Bar */}
                  <div className="mb-4">
                    <div className="flex justify-between mb-2">
                      <span className="font-semibold text-sm">Assessment Progress</span>
                      <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                        {project.estimated_items_affected
                          ? (
                              ((project.total_items_assessed /
                                project.estimated_items_affected) *
                              100).toFixed(1)
                            ).toString()
                          : "0"}
                        %
                      </span>
                    </div>
                    <div className="w-full bg-earth-200 dark:bg-earth-600 rounded-full h-3 overflow-hidden">
                      <div
                        className="bg-lsc-rose h-full transition-all"
                        style={{
                          width: `${
                            project.estimated_items_affected
                              ? (
                                  (project.total_items_assessed /
                                    project.estimated_items_affected) *
                                  100
                                ).toFixed(1)
                              : 0
                          }%`,
                        }}
                      />
                    </div>
                  </div>

                  {/* Item Status Summary */}
                  <div className="grid grid-cols-3 gap-3">
                    <div className="p-3 bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-800 rounded text-center">
                      <div className="text-2xl font-bold text-status-success-600">{project.items_salvaged}</div>
                      <div className="text-xs text-status-success-800 dark:text-status-success-300 font-semibold">Salvaged</div>
                    </div>
                    <div className="p-3 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded text-center">
                      <div className="text-2xl font-bold text-status-danger-600">{project.items_lost}</div>
                      <div className="text-xs text-status-danger-800 dark:text-status-danger-300 font-semibold">Lost</div>
                    </div>
                    <div className="p-3 bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded text-center">
                      <div className="text-2xl font-bold text-status-warning-600">
                        {project.total_items_assessed - project.items_salvaged - project.items_lost}
                      </div>
                      <div className="text-xs text-status-warning-800 dark:text-status-warning-300 font-semibold">Assessing</div>
                    </div>
                  </div>
                </div>

                {/* Expanded Details */}
                {expandedProject === project.id && (
                  <div className="mt-4 pt-4 border-t-2 border-lsc-border dark:border-earth-700 space-y-4">
                    {project.affected_areas.length > 0 && (
                      <div>
                        <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2">Affected Areas:</h4>
                        <div className="flex flex-wrap gap-2">
                          {project.affected_areas.map((area) => (
                            <span
                              key={area}
                              className="px-3 py-1 bg-lsc-rose/10 dark:bg-lsc-rose/20 text-lsc-rose dark:text-lsc-rose-light rounded-full text-sm font-semibold"
                            >
                              {area}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    <button
                      onClick={() => navigate(`/emergency-operations/recovery/${project.id}/items`)}
                      className="w-full px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/80 transition-colors font-semibold flex items-center justify-center gap-2"
                    >
                      <Package className="w-4 h-4" />
                      View Damaged Items
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="bg-lsc-rose/5 dark:bg-lsc-rose/10 border-2 border-lsc-rose/20 dark:border-lsc-rose/30 rounded-lg p-8 text-center">
            <Package className="w-12 h-12 text-lsc-rose dark:text-lsc-rose-light mx-auto mb-3" />
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 font-semibold">{t('emergencyOperationsRecovery.noRecoveryProjectsCreatedYet')}</p>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">{t('emergencyOperationsRecovery.createAProjectToBegin')}</p>
          </div>
        )}

      {/* Create Project Modal */}
      {showCreateModal && (
        <ModalBackdrop onClose={() => setShowCreateModal(false)} title="Dialog">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg max-w-lg w-full mx-4 p-6 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-serif font-bold flex items-center gap-2">
                <Package className="w-6 h-6 text-lsc-rose dark:text-lsc-rose-light" />
                Create Recovery Project
              </h2>
              <button onClick={() => setShowCreateModal(false)}>
                <X className="w-6 h-6" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block font-semibold mb-2">Project Name *</label>
                <input
                  type="text"
                  value={form.project_name}
                  onChange={(e) => setForm({ ...form, project_name: e.target.value })}
                  placeholder={t('placeholder.emergencyOperationsRecovery.egWaterDamageEast')}
                  className="w-full p-3 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-lsc-rose outline-none"
                />
              </div>

              <div>
                <label className="block font-semibold mb-2">Description</label>
                <textarea
                  value={form.project_description}
                  onChange={(e) => setForm({ ...form, project_description: e.target.value })}
                  placeholder={t('emergencyOperationsRecovery.describeTheRecoveryProject')}
                  className="w-full p-3 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-lsc-rose outline-none"
                  rows={2}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block font-semibold mb-2">Disaster Type *</label>
                  <select
                    value={form.disaster_type}
                    onChange={(e) => setForm({ ...form, disaster_type: e.target.value })}
                    className="w-full p-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-lsc-rose outline-none"
                  >
                    <option value="">Select...</option>
                    {disasterTypes.map((type) => (
                      <option key={type.id} value={type.id}>
                        {type.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block font-semibold mb-2">Disaster Date *</label>
                  <input
                    type="date"
                    value={form.disaster_date}
                    onChange={(e) => setForm({ ...form, disaster_date: e.target.value })}
                    className="w-full p-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-lsc-rose outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold mb-2">Estimated Items Affected</label>
                <input
                  type="number"
                  min="0"
                  value={form.estimated_items_affected || ""}
                  onChange={(e) =>
                    setForm({ ...form, estimated_items_affected: e.target.value ? parseInt(e.target.value) : undefined })
                  }
                  placeholder={t('emergencyOperationsRecovery.estimatedCountOfDamagedItems')}
                  className="w-full p-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-lsc-rose outline-none"
                />
              </div>

              <div>
                <label className="block font-semibold mb-2">Affected Areas</label>
                <div className="space-y-2 max-h-40 overflow-y-auto">
                  {["Main Floor", "Children's Area", "Teen Area", "Adult Area", "Reference", "Makerspace"].map(
                    (area) => (
                      <label key={area} className="flex items-center gap-2 p-2 hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800">
                        <input
                          type="checkbox"
                          checked={form.affected_areas.includes(area)}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setForm({
                                ...form,
                                affected_areas: [...form.affected_areas, area],
                              })
                            } else {
                              setForm({
                                ...form,
                                affected_areas: form.affected_areas.filter((a) => a !== area),
                              })
                            }
                          }}
                        />
                        <span>{area}</span>
                      </label>
                    )
                  )}
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
                  onClick={handleCreateProject}
                  disabled={isSaving}
                  className="flex-1 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/80 font-semibold disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {isSaving ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Plus className="w-4 h-4" />}
                  Create Project
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
