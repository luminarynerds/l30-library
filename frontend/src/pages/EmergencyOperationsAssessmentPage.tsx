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
  AlertTriangle,
  ChevronLeft,
  Plus,
  X,
  Loader2,
  Save,
  FileText,
  ClipboardList,
} from "lucide-react"
import toast from "react-hot-toast"
import { useTranslation} from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

export default function EmergencyOperationsAssessmentPage(): React.ReactElement {
  const { t } = useTranslation()
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { user, token: _token, isLoading: authLoading, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  const [isLoading, setIsLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [isSaving, setIsSaving] = useState(false)

  const [form, setForm] = useState({
    disaster_type: "",
    disaster_date: "",
    phase: "initial",
    areas_assessed: [] as string[],
    assessment_team: [] as number[],
    building_exterior_damage: 0,
    building_interior_damage: 0,
    roof_damage: "",
    structural_integrity: "",
    utilities_status: {
      electricity: "unknown",
      water: "unknown",
      hvac: "unknown",
    },
    hazards_identified: [] as string[],
    collection_damage_estimate_percent: undefined as number | undefined,
    mold_presence: false,
    estimated_property_damage: undefined as number | undefined,
    estimated_content_loss: undefined as number | undefined,
    estimated_recovery_cost: undefined as number | undefined,
  })

  useEffect(() => {
    if (!isAuthenticated) {
      navigate("/login")
      return
    }

    if (!["admin", "director", "super_admin", "manager"].includes(user?.role?.toLowerCase() ?? '')) {
      navigate("/")
      return
    }

    setIsLoading(false)
  }, [isAuthenticated, user?.role, navigate])

  const handleCreateAssessment = async () => {
    if (!form.disaster_type || !form.disaster_date) {
      toast.error(t('emergencyOperationsAssessment.pleaseProvideDisasterTypeAnd'))
      return
    }

    try {
      setIsSaving(true)
      // API call would go here
      toast.success(t('toast.emergencyOperationsAssessment.assessmentCreatedSuccessfully'))
      setShowCreateModal(false)
      // Reset form
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('emergencyOperationsAssessment.failedToCreateAssessment'))
    } finally {
      setIsSaving(false)
    }
  }

  if (authLoading || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" />
      </div>
    )
  }

  return (
    <AdminShell title="Post-Disaster Assessment" subtitle={t('emergencyOperationsAssessment.comprehensiveDamageDocumentationAndRecovery')}>
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
            className="px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 transition-colors font-semibold flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            New Assessment
          </button>
        </div>

        {/* Assessment Guidance */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border-2 border-lsc-border dark:border-earth-700 p-6">
            <h3 className="font-serif font-bold text-lg mb-3 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-status-warning-600" />
              Initial Assessment (First 24hrs)
            </h3>
            <ul className="space-y-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 list-disc list-inside">
              <li>Structural integrity evaluation</li>
              <li>Safety hazard identification</li>
              <li>Utilities status check</li>
              <li>Initial damage estimates</li>
              <li>Photo documentation</li>
            </ul>
          </div>

          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border-2 border-lsc-border dark:border-earth-700 p-6">
            <h3 className="font-serif font-bold text-lg mb-3 flex items-center gap-2">
              <ClipboardList className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
              Detailed Assessment (24-72hrs)
            </h3>
            <ul className="space-y-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 list-disc list-inside">
              <li>Comprehensive room-by-room audit</li>
              <li>Collection damage evaluation</li>
              <li>Equipment status assessment</li>
              <li>Detailed cost estimation</li>
              <li>Recovery priority matrix</li>
            </ul>
          </div>

          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border-2 border-lsc-border dark:border-earth-700 p-6">
            <h3 className="font-serif font-bold text-lg mb-3 flex items-center gap-2">
              <FileText className="w-5 h-5 text-status-success-600" />
              Recovery Planning (After Assessment)
            </h3>
            <ul className="space-y-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 list-disc list-inside">
              <li>Insurance claim documentation</li>
              <li>Restoration vendor quotes</li>
              <li>Resource allocation planning</li>
              <li>Timeline development</li>
              <li>Community communication plan</li>
            </ul>
          </div>
        </div>

        {/* No Assessments Yet */}
        <div className="bg-cyan-50 dark:bg-cyan-900/20 border-2 border-cyan-200 dark:border-cyan-800 rounded-lg p-8 text-center">
          <AlertTriangle className="w-12 h-12 text-cyan-600 mx-auto mb-3" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 font-semibold">{t('emergencyOperationsAssessment.noAssessmentsCreatedYet')}</p>
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm mt-1">
            Create a new assessment to begin documenting post-disaster damage and recovery efforts
          </p>
        </div>

      {/* Create Assessment Modal */}
      {showCreateModal && (
        <ModalBackdrop onClose={() => setShowCreateModal(false)} title="Dialog">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg max-w-2xl w-full mx-4 my-8 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-serif font-bold flex items-center gap-2">
                <AlertTriangle className="w-6 h-6 text-cyan-600" />
                Create Post-Disaster Assessment
              </h2>
              <button onClick={() => setShowCreateModal(false)}>
                <X className="w-6 h-6" />
              </button>
            </div>

            <div className="space-y-4 max-h-[70vh] overflow-y-auto">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block font-semibold mb-2">Disaster Type *</label>
                  <select
                    value={form.disaster_type}
                    onChange={(e) => setForm({ ...form, disaster_type: e.target.value })}
                    className="w-full p-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-cyan-500 outline-none"
                  >
                    <option value="">Select...</option>
                    <option value="fire">Fire</option>
                    <option value="water_damage">Water Damage</option>
                    <option value="flood">Flood</option>
                    <option value="wind">Wind Damage</option>
                    <option value="earthquake">Earthquake</option>
                    <option value="other">Other</option>
                  </select>
                </div>

                <div>
                  <label className="block font-semibold mb-2">Disaster Date *</label>
                  <input
                    type="date"
                    value={form.disaster_date}
                    onChange={(e) => setForm({ ...form, disaster_date: e.target.value })}
                    className="w-full p-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-cyan-500 outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold mb-2">Assessment Phase</label>
                <select
                  value={form.phase}
                  onChange={(e) => setForm({ ...form, phase: e.target.value })}
                  className="w-full p-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-cyan-500 outline-none"
                >
                  <option value="initial">Initial (First 24hrs)</option>
                  <option value="detailed">Detailed (24-72hrs)</option>
                  <option value="recovery_planning">Recovery Planning</option>
                  <option value="recovery_execution">Recovery Execution</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold mb-2">Areas Assessed</label>
                <div className="space-y-2 max-h-32 overflow-y-auto">
                  {["Main Floor", "Children's Area", "Teen Area", "Adult Area", "Reference", "Makerspace", "Staff Areas"].map(
                    (area) => (
                      <label key={area} className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={form.areas_assessed.includes(area)}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setForm({
                                ...form,
                                areas_assessed: [...form.areas_assessed, area],
                              })
                            } else {
                              setForm({
                                ...form,
                                areas_assessed: form.areas_assessed.filter((a) => a !== area),
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

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block font-semibold mb-2">Building Exterior Damage (%)</label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={form.building_exterior_damage}
                    onChange={(e) => setForm({ ...form, building_exterior_damage: parseInt(e.target.value) || 0 })}
                    className="w-full p-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-cyan-500 outline-none"
                  />
                </div>

                <div>
                  <label className="block font-semibold mb-2">Building Interior Damage (%)</label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={form.building_interior_damage}
                    onChange={(e) => setForm({ ...form, building_interior_damage: parseInt(e.target.value) || 0 })}
                    className="w-full p-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-cyan-500 outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold mb-2">Structural Integrity</label>
                <select
                  value={form.structural_integrity}
                  onChange={(e) => setForm({ ...form, structural_integrity: e.target.value })}
                  className="w-full p-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-cyan-500 outline-none"
                >
                  <option value="">Select...</option>
                  <option value="safe">Safe</option>
                  <option value="compromised">Compromised</option>
                  <option value="hazardous">Hazardous</option>
                  <option value="unknown">Unknown</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold mb-2">Identified Hazards</label>
                <div className="space-y-2 max-h-32 overflow-y-auto">
                  {[
                    "Broken glass",
                    "Mold",
                    "Chemical spill",
                    "Electrical hazard",
                    "Structural damage",
                    "Water pooling",
                    "Asbestos concern",
                    "Gas leak",
                  ].map((hazard) => (
                    <label key={hazard} className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={form.hazards_identified.includes(hazard)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setForm({
                              ...form,
                              hazards_identified: [...form.hazards_identified, hazard],
                            })
                          } else {
                            setForm({
                              ...form,
                              hazards_identified: form.hazards_identified.filter((h) => h !== hazard),
                            })
                          }
                        }}
                      />
                      <span>{hazard}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block font-semibold mb-2">Property Damage ($)</label>
                  <input
                    type="number"
                    min="0"
                    value={form.estimated_property_damage || ""}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        estimated_property_damage: e.target.value ? parseInt(e.target.value) : undefined,
                      })
                    }
                    className="w-full p-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-cyan-500 outline-none"
                  />
                </div>

                <div>
                  <label className="block font-semibold mb-2">Content Loss ($)</label>
                  <input
                    type="number"
                    min="0"
                    value={form.estimated_content_loss || ""}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        estimated_content_loss: e.target.value ? parseInt(e.target.value) : undefined,
                      })
                    }
                    className="w-full p-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-cyan-500 outline-none"
                  />
                </div>

                <div>
                  <label className="block font-semibold mb-2">Recovery Cost ($)</label>
                  <input
                    type="number"
                    min="0"
                    value={form.estimated_recovery_cost || ""}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        estimated_recovery_cost: e.target.value ? parseInt(e.target.value) : undefined,
                      })
                    }
                    className="w-full p-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-cyan-500 outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold mb-2">Collection Damage Estimate (%)</label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={form.collection_damage_estimate_percent || ""}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      collection_damage_estimate_percent: e.target.value ? parseInt(e.target.value) : undefined,
                    })
                  }
                  className="w-full p-2 border-2 border-lsc-border dark:border-earth-700 rounded-lg focus:border-cyan-500 outline-none"
                />
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="mold_presence"
                  checked={form.mold_presence}
                  onChange={(e) => setForm({ ...form, mold_presence: e.target.checked })}
                />
                <label htmlFor="mold_presence" className="font-semibold">
                  Mold presence detected
                </label>
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
                  onClick={handleCreateAssessment}
                  disabled={isSaving}
                  className="flex-1 px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 font-semibold disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {isSaving ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Save className="w-4 h-4" />}
                  Create Assessment
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
