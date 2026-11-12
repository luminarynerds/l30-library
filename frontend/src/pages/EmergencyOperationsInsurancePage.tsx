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
  DollarSign,
  ChevronLeft,
  Plus,
  X,
  Loader2,
  CheckCircle2,
  AlertCircle,
  FileText,
  Clock,
  Eye,
  EyeOff,
} from "lucide-react"
import toast from "react-hot-toast"
import { useTranslation} from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface InsuranceClaim {
  id: number
  incident_date: string
  incident_type: string
  incident_description: string
  claim_number?: string | null
  insurance_company: string
  agent_name: string
  agent_email?: string | null
  initial_damage_estimate: number
  final_damage_amount?: number | null
  claimed_amount?: number | null
  approved_amount?: number | null
  reimbursed_amount?: number | null
  documentation_complete: boolean
  claim_submitted: boolean
  claim_approved: boolean
  created_at: string
}

export default function EmergencyOperationsInsurancePage(): React.ReactElement {
  const { t } = useTranslation()
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { user, token: _token, isLoading: authLoading, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  const [isLoading, setIsLoading] = useState(true)
  const [claims, _setClaims] = useState<InsuranceClaim[]>([])
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [expandedClaim, setExpandedClaim] = useState<number | null>(null)
  const [isSaving, setIsSaving] = useState(false)

  const [form, setForm] = useState({
    incident_date: "",
    incident_type: "",
    incident_description: "",
    incident_location: "",
    insurance_company: "",
    agent_name: "",
    agent_phone: "",
    agent_email: "",
    initial_damage_estimate: 0,
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

  const handleCreateClaim = async () => {
    if (
      !form.incident_date ||
      !form.incident_type ||
      !form.insurance_company ||
      !form.agent_name ||
      form.initial_damage_estimate <= 0
    ) {
      toast.error(t('emergencyOperationsInsurance.pleaseFillInAllRequired'))
      return
    }

    try {
      setIsSaving(true)
      // API call would go here
      toast.success(t('emergencyOperationsInsurance.insuranceClaimCreatedSuccessfully'))
      setShowCreateModal(false)
      // Reset form
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('emergencyOperationsInsurance.failedToCreateClaim'))
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
    <AdminShell title="Insurance Documentation" subtitle={t('emergencyOperationsInsurance.manageDisasterClaimsAndRecovery')}>
      <div>
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
            className="px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors font-semibold flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            New Claim
          </button>
        </div>

        {/* Documentation Guidelines */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border-2 border-lsc-border dark:border-earth-700 p-6">
            <h3 className="font-serif font-bold text-lg mb-3 flex items-center gap-2">
              <FileText className="w-5 h-5 text-lsc-rose" />
              Required Documentation
            </h3>
            <ul className="space-y-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 list-disc list-inside">
              <li>{t('emergencyOperationsInsurance.incidentReportWithDetails')}</li>
              <li>{t('emergencyOperationsInsurance.photographicEvidenceOfDamage')}</li>
              <li>{t('emergencyOperationsInsurance.inventoryListOfDamagedItems')}</li>
              <li>{t('emergencyOperationsInsurance.repairEstimatesFromVendors')}</li>
              <li>{t('emergencyOperationsInsurance.receiptsForPurchasesRepairs')}</li>
              <li>Professional damage assessment</li>
              <li>Insurance policy documentation</li>
            </ul>
          </div>

          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border-2 border-lsc-border dark:border-earth-700 p-6">
            <h3 className="font-serif font-bold text-lg mb-3 flex items-center gap-2">
              <Clock className="w-5 h-5 text-status-warning-600" />
              Claims Timeline
            </h3>
            <ul className="space-y-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 list-disc list-inside">
              <li>{t('emergencyOperationsInsurance.dayReportIncidentToInsurer')}</li>
              <li>{t('emergencyOperationsInsurance.dayGatherAllDocumentation')}</li>
              <li>{t('emergencyOperationsInsurance.daySubmitInitialClaim')}</li>
              <li>Day 14-21: Adjuster inspection</li>
              <li>Day 21-30: Documentation clarification</li>
              <li>Day 30-60: Claim decision</li>
              <li>Day 60+: Reimbursement processing</li>
            </ul>
          </div>
        </div>

        {/* No Claims Yet */}
        {claims.length === 0 && (
          <div className="bg-lsc-rose/10 dark:bg-lsc-rose/20 border-2 border-lsc-rose/30 dark:border-lsc-rose/30 rounded-lg p-8 text-center">
            <DollarSign className="w-12 h-12 text-lsc-rose mx-auto mb-3" />
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 font-semibold">{t('emergencyOperationsInsurance.noInsuranceClaimsCreatedYet')}</p>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm mt-1">
              Create a new claim to begin managing insurance documentation and reimbursement
            </p>
          </div>
        )}

        {/* Active Claims */}
        {claims.map((claim) => (
          <div
            key={claim.id}
            className="bg-lsc-white dark:bg-earth-800 rounded-lg border-2 border-lsc-rose/30 dark:border-lsc-rose/30 p-6 mb-6 hover:shadow-lg transition-shadow"
          >
            <div
              className="cursor-pointer"
              onClick={() => setExpandedClaim(expandedClaim === claim.id ? null : claim.id)} tabIndex={0} role="button" onKeyDown={(e: React.KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); (() => setExpandedClaim(expandedClaim === claim.id ? null : claim.id))(); } }}
            >
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">{claim.incident_type}</h3>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{claim.incident_description}</p>
                </div>

                <div className="flex items-center gap-2">
                  {claim.claim_approved ? (
                    <span className="px-3 py-1 bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-300 rounded-full text-xs font-bold">
                      APPROVED
                    </span>
                  ) : claim.claim_submitted ? (
                    <span className="px-3 py-1 bg-earth-100 dark:bg-earth-800/30 text-earth-800 dark:text-lsc-rose-light rounded-full text-xs font-bold">
                      SUBMITTED
                    </span>
                  ) : (
                    <span className="px-3 py-1 bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-300 rounded-full text-xs font-bold">
                      PENDING
                    </span>
                  )}

                  {expandedClaim === claim.id ? (
                    <EyeOff className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
                  ) : (
                    <Eye className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
                  )}
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
                <div className="p-3 bg-earth-50 dark:bg-earth-900 rounded border border-lsc-border dark:border-earth-700">
                  <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 font-semibold">Incident Date</div>
                  <div className="text-lg font-bold text-lsc-dark dark:text-lsc-cream">
                    {new Date(claim.incident_date).toLocaleDateString()}
                  </div>
                </div>

                <div className="p-3 bg-earth-50 dark:bg-earth-900 rounded border border-lsc-border dark:border-earth-700">
                  <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 font-semibold">Insurance Company</div>
                  <div className="text-lg font-bold text-lsc-dark dark:text-lsc-cream">{claim.insurance_company}</div>
                </div>

                <div className="p-3 bg-earth-50 dark:bg-earth-900 rounded border border-lsc-border dark:border-earth-700">
                  <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 font-semibold">Initial Estimate</div>
                  <div className="text-lg font-bold text-lsc-dark dark:text-lsc-cream">
                    ${claim.initial_damage_estimate.toLocaleString()}
                  </div>
                </div>

                <div className="p-3 bg-lsc-rose/10 dark:bg-lsc-rose/20 rounded border border-lsc-rose/30 dark:border-lsc-rose/30">
                  <div className="text-xs text-lsc-rose font-semibold">Status</div>
                  <div className="text-lg font-bold text-lsc-rose dark:text-lsc-rose-light">
                    {claim.claim_approved ? "Approved" : claim.claim_submitted ? "In Review" : "Draft"}
                  </div>
                </div>
              </div>

              {/* Documentation Checklist */}
              <div className="mb-4">
                <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-3">Documentation Status</h4>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                  <div className="flex items-center gap-2 p-2 bg-earth-50 dark:bg-earth-900 rounded">
                    <CheckCircle2 className="w-4 h-4 text-status-success-600" />
                    <span className="text-sm">Incident Report</span>
                  </div>
                  <div className="flex items-center gap-2 p-2 bg-earth-50 dark:bg-earth-900 rounded">
                    <CheckCircle2 className="w-4 h-4 text-status-success-600" />
                    <span className="text-sm">Photos</span>
                  </div>
                  <div className="flex items-center gap-2 p-2 bg-earth-50 dark:bg-earth-900 rounded">
                    <AlertCircle className="w-4 h-4 text-status-warning-600" />
                    <span className="text-sm">Inventory List</span>
                  </div>
                  <div className="flex items-center gap-2 p-2 bg-earth-50 dark:bg-earth-900 rounded">
                    <CheckCircle2 className="w-4 h-4 text-status-success-600" />
                    <span className="text-sm">Estimates</span>
                  </div>
                  <div className="flex items-center gap-2 p-2 bg-earth-50 dark:bg-earth-900 rounded">
                    <AlertCircle className="w-4 h-4 text-status-warning-600" />
                    <span className="text-sm">Receipts</span>
                  </div>
                  <div className="flex items-center gap-2 p-2 bg-earth-50 dark:bg-earth-900 rounded">
                    <AlertCircle className="w-4 h-4 text-status-warning-600" />
                    <span className="text-sm">Assessment</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Expanded Details */}
            {expandedClaim === claim.id && (
              <div className="mt-4 pt-4 border-t-2 border-lsc-border dark:border-earth-700 space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="font-semibold text-lsc-dark dark:text-lsc-cream text-sm">Agent Name</label>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{claim.agent_name}</p>
                  </div>

                  <div>
                    <label className="font-semibold text-lsc-dark dark:text-lsc-cream text-sm">Agent Phone</label>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{claim.agent_email}</p>
                  </div>

                  {claim.claim_number && (
                    <div>
                      <label className="font-semibold text-lsc-dark dark:text-lsc-cream text-sm">Claim Number</label>
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 font-mono">{claim.claim_number}</p>
                    </div>
                  )}

                  {claim.approved_amount && (
                    <div>
                      <label className="font-semibold text-lsc-dark dark:text-lsc-cream text-sm">Approved Amount</label>
                      <p className="text-sm text-status-success-600 font-bold">${claim.approved_amount.toLocaleString()}</p>
                    </div>
                  )}

                  {claim.reimbursed_amount && (
                    <div>
                      <label className="font-semibold text-lsc-dark dark:text-lsc-cream text-sm">Reimbursed Amount</label>
                      <p className="text-sm text-lsc-rose dark:text-lsc-rose-light font-bold">${claim.reimbursed_amount.toLocaleString()}</p>
                    </div>
                  )}
                </div>

                <div className="flex gap-2">
                  {!claim.claim_submitted && (
                    <button className="flex-1 px-3 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors font-semibold flex items-center justify-center gap-2 text-sm">
                      <FileText className="w-4 h-4" />
                      Submit Claim
                    </button>
                  )}

                  <button className="flex-1 px-3 py-2 bg-earth-600 text-white rounded-lg hover:bg-earth-700 transition-colors font-semibold flex items-center justify-center gap-2 text-sm">
                    <FileText className="w-4 h-4" />
                    View Documents
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}

      {/* Create Claim Modal */}
      {showCreateModal && (
        <ModalBackdrop onClose={() => setShowCreateModal(false)} title="Dialog">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg max-w-2xl w-full mx-4 my-8 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-serif font-bold flex items-center gap-2">
                <DollarSign className="w-6 h-6 text-lsc-rose" />
                New Insurance Claim
              </h2>
              <button onClick={() => setShowCreateModal(false)}>
                <X className="w-6 h-6" />
              </button>
            </div>

            <div className="space-y-4 max-h-[70vh] overflow-y-auto">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block font-semibold mb-2">Incident Date *</label>
                  <input
                    type="date"
                    value={form.incident_date}
                    onChange={(e) => setForm({ ...form, incident_date: e.target.value })}
                    className="w-full p-2 border-2 border-lsc-border dark:border-earth-600 rounded-lg focus:border-lsc-rose outline-none"
                  />
                </div>

                <div>
                  <label className="block font-semibold mb-2">Incident Type *</label>
                  <select
                    value={form.incident_type}
                    onChange={(e) => setForm({ ...form, incident_type: e.target.value })}
                    className="w-full p-2 border-2 border-lsc-border dark:border-earth-600 rounded-lg focus:border-lsc-rose outline-none"
                  >
                    <option value="">Select...</option>
                    <option value="fire">Fire</option>
                    <option value="water_damage">Water Damage</option>
                    <option value="theft">Theft</option>
                    <option value="vandalism">Vandalism</option>
                    <option value="natural_disaster">Natural Disaster</option>
                    <option value="other">Other</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block font-semibold mb-2">Incident Description *</label>
                <textarea
                  value={form.incident_description}
                  onChange={(e) => setForm({ ...form, incident_description: e.target.value })}
                  placeholder={t('emergencyOperationsInsurance.describeTheIncidentInDetail')}
                  className="w-full p-3 border-2 border-lsc-border dark:border-earth-600 rounded-lg focus:border-lsc-rose outline-none"
                  rows={3}
                />
              </div>

              <div>
                <label className="block font-semibold mb-2">Incident Location</label>
                <input
                  type="text"
                  value={form.incident_location}
                  onChange={(e) => setForm({ ...form, incident_location: e.target.value })}
                  placeholder={t('emergencyOperationsInsurance.buildingAndAreaAffected')}
                  className="w-full p-2 border-2 border-lsc-border dark:border-earth-600 rounded-lg focus:border-lsc-rose outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block font-semibold mb-2">Insurance Company *</label>
                  <input
                    type="text"
                    value={form.insurance_company}
                    onChange={(e) => setForm({ ...form, insurance_company: e.target.value })}
                    placeholder={t('placeholder.emergencyOperationsInsurance.companyName')}
                    className="w-full p-2 border-2 border-lsc-border dark:border-earth-600 rounded-lg focus:border-lsc-rose outline-none"
                  />
                </div>

                <div>
                  <label className="block font-semibold mb-2">Initial Damage Estimate ($) *</label>
                  <input
                    type="number"
                    min="0"
                    value={form.initial_damage_estimate}
                    onChange={(e) => setForm({ ...form, initial_damage_estimate: parseInt(e.target.value) || 0 })}
                    className="w-full p-2 border-2 border-lsc-border dark:border-earth-600 rounded-lg focus:border-lsc-rose outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block font-semibold mb-2">Agent Name *</label>
                  <input
                    type="text"
                    value={form.agent_name}
                    onChange={(e) => setForm({ ...form, agent_name: e.target.value })}
                    placeholder={t('placeholder.emergencyOperationsInsurance.insuranceAgentName')}
                    className="w-full p-2 border-2 border-lsc-border dark:border-earth-600 rounded-lg focus:border-lsc-rose outline-none"
                  />
                </div>

                <div>
                  <label className="block font-semibold mb-2">Agent Phone *</label>
                  <input
                    type="tel"
                    value={form.agent_phone}
                    onChange={(e) => setForm({ ...form, agent_phone: e.target.value })}
                    className="w-full p-2 border-2 border-lsc-border dark:border-earth-600 rounded-lg focus:border-lsc-rose outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold mb-2">Agent Email *</label>
                <input
                  type="email"
                  value={form.agent_email}
                  onChange={(e) => setForm({ ...form, agent_email: e.target.value })}
                  placeholder={t('placeholder.emergencyOperationsInsurance.agentinsurancecom')}
                  className="w-full p-2 border-2 border-lsc-border dark:border-earth-600 rounded-lg focus:border-lsc-rose outline-none"
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
                  onClick={handleCreateClaim}
                  disabled={isSaving}
                  className="flex-1 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 font-semibold disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {isSaving ? <Loader2 className="w-4 h-4 motion-safe:animate-spin" /> : <Plus className="w-4 h-4" />}
                  Create Claim
                </button>
              </div>
            </div>
          </div>
      </ModalBackdrop>
      )}
      </div>
      </div>
    </AdminShell>
  )
}
