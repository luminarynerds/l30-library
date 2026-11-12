/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../contexts/AuthContext"
import { AdminShell } from '../components/shells/AdminShell'
import { Phone, ChevronLeft, Plus, Loader2 } from "lucide-react"
import toast from "react-hot-toast"
import { emergencyOperationsAPI } from "../api/emergency-operations-api"
import { useTranslation } from '@/i18n'
import {
  CascadeCard,
  CascadeContactList,
  CreateCascadeModal,
  ExecuteCascadeModal,
  AddContactModal,
} from "../components/emergency-cascade"
import {
  INITIAL_CASCADE_FORM,
  INITIAL_CONTACT_FORM,
  type CascadeContact,
  type CascadeData,
} from "../components/emergency-cascade/types"

export default function EmergencyOperationsCascadePage(): React.ReactElement {
  const { t } = useTranslation()
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { user, token: _token, isLoading: authLoading, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  const [isLoading, setIsLoading] = useState(true)
  const [cascades, setCascades] = useState<CascadeData[]>([])
  const [selectedCascade, setSelectedCascade] = useState<CascadeData | null>(null)
  const [cascadeContacts, _setCascadeContacts] = useState<CascadeContact[]>([])
  const [showCreateCascadeModal, setShowCreateCascadeModal] = useState(false)
  const [showExecuteModal, setShowExecuteModal] = useState(false)
  const [showAddContactModal, setShowAddContactModal] = useState(false)
  const [isSaving, setIsSaving] = useState(false)

  const [cascadeForm, setCascadeForm] = useState(INITIAL_CASCADE_FORM)
  const [contactForm, setContactForm] = useState(INITIAL_CONTACT_FORM)
  const [executeForm, setExecuteForm] = useState({ trigger_reason: "" })

  const loadCascades = useCallback(async () => {
    try {
      setIsLoading(true)
      const data = await emergencyOperationsAPI.emergencyContact.getActiveCascades()
      setCascades(data)
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('emergencyOperationsCascade.failedToLoadCascades'))
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

    loadCascades()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, user?.role, navigate])

  const handleCreateCascade = async () => {
    if (!cascadeForm.cascade_name.trim()) {
      toast.error(t('emergencyOperationsCascade.pleaseProvideACascadeName'))
      return
    }

    try {
      setIsSaving(true)
      const messageTemplate = `Emergency alert: {reason}. Estimated restoration: {estimated_time}.`

      await emergencyOperationsAPI.emergencyContact.createCascade({
        cascade_name: cascadeForm.cascade_name,
        auto_trigger_events: cascadeForm.auto_trigger_events,
        message_template: messageTemplate,
        manual_approval_required: cascadeForm.manual_approval_required,
        max_contact_levels: cascadeForm.max_contact_levels,
      })

      toast.success(t('emergencyOperationsCascade.emergencyCascadeCreatedSuccessfully'))
      setShowCreateCascadeModal(false)
      setCascadeForm(INITIAL_CASCADE_FORM)
      loadCascades()
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('emergencyOperationsCascade.failedToCreateCascade'))
    } finally {
      setIsSaving(false)
    }
  }

  const handleAddContact = async () => {
    if (!selectedCascade || !contactForm.contact_name || !contactForm.contact_role) {
      toast.error(t('emergencyOperationsCascade.pleaseFillInAllRequired'))
      return
    }

    if (!contactForm.contact_email && !contactForm.contact_phone) {
      toast.error(t('emergencyOperationsCascade.pleaseProvideAtLeastAn'))
      return
    }

    try {
      setIsSaving(true)
      await emergencyOperationsAPI.emergencyContact.addCascadeContact(selectedCascade.id, {
        level: contactForm.level,
        contact_role: contactForm.contact_role,
        contact_name: contactForm.contact_name,
        ...(contactForm.contact_email ? { contact_email: contactForm.contact_email } : {}),
        ...(contactForm.contact_phone ? { contact_phone: contactForm.contact_phone } : {}),
        contact_method: contactForm.contact_method,
        wait_time_seconds: contactForm.wait_time_seconds,
        retry_attempts: contactForm.retry_attempts,
      })

      toast.success(t('emergencyOperationsCascade.contactAddedToCascade'))
      setShowAddContactModal(false)
      setContactForm(INITIAL_CONTACT_FORM)
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('emergencyOperationsCascade.failedToAddContact'))
    } finally {
      setIsSaving(false)
    }
  }

  const handleExecuteCascade = async () => {
    if (!selectedCascade || !executeForm.trigger_reason.trim()) {
      toast.error(t('emergencyOperationsCascade.pleaseProvideATriggerReason'))
      return
    }

    try {
      setIsSaving(true)
      await emergencyOperationsAPI.emergencyContact.executeCascade(
        selectedCascade.id,
        executeForm.trigger_reason
      )

      toast.success(t('emergencyOperationsCascade.emergencyCascadeExecutedContactingAll'))
      setShowExecuteModal(false)
      setExecuteForm({ trigger_reason: "" })
    } catch (error: unknown) {
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
      toast.error(t('emergencyOperationsCascade.failedToExecuteCascade'))
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
    <AdminShell title="Emergency Contact Cascades" subtitle={t('emergencyOperationsCascade.multiLevelEmergencyNotificationSystem')}>
      <div>
        <div className="mb-8 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={() => navigate("/emergency-operations")} className="hover:text-lsc-rose">
              <ChevronLeft className="w-6 h-6" />
            </button>
            <div></div>
          </div>
          <button
            onClick={() => setShowCreateCascadeModal(true)}
            className="px-4 py-2 bg-category-600 text-white rounded-lg hover:bg-category-700 transition-colors font-semibold flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Create Cascade
          </button>
        </div>

        {cascades.length > 0 ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            {cascades.map((cascade) => (
              <CascadeCard
                key={cascade.id}
                cascade={cascade}
                onSelect={setSelectedCascade}
                onExecute={(c) => {
                  setSelectedCascade(c)
                  setShowExecuteModal(true)
                }}
                onAddContact={(c) => {
                  setSelectedCascade(c)
                  setShowAddContactModal(true)
                }}
              />
            ))}
          </div>
        ) : (
          <div className="bg-earth-50 dark:bg-earth-800/20 border-2 border-lsc-border dark:border-earth-700 rounded-lg p-8 text-center mb-8">
            <Phone className="w-12 h-12 text-lsc-rose dark:text-lsc-rose-light mx-auto mb-3" />
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 font-semibold">{t('emergencyOperationsCascade.noCascadesCreatedYet')}</p>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">{t('emergencyOperationsCascade.createYourFirstCascadeTo')}</p>
          </div>
        )}

        {selectedCascade && (
          <CascadeContactList cascade={selectedCascade} contacts={cascadeContacts} />
        )}

        {showCreateCascadeModal && (
          <CreateCascadeModal
            form={cascadeForm}
            isSaving={isSaving}
            onChange={setCascadeForm}
            onCancel={() => setShowCreateCascadeModal(false)}
            onSubmit={handleCreateCascade}
          />
        )}

        {showExecuteModal && selectedCascade && (
          <ExecuteCascadeModal
            cascade={selectedCascade}
            triggerReason={executeForm.trigger_reason}
            isSaving={isSaving}
            onChangeReason={(reason) => setExecuteForm({ trigger_reason: reason })}
            onCancel={() => setShowExecuteModal(false)}
            onSubmit={handleExecuteCascade}
          />
        )}

        {showAddContactModal && selectedCascade && (
          <AddContactModal
            cascade={selectedCascade}
            form={contactForm}
            isSaving={isSaving}
            onChange={setContactForm}
            onCancel={() => setShowAddContactModal(false)}
            onSubmit={handleAddContact}
          />
        )}
      </div>
    </AdminShell>
  )
}
