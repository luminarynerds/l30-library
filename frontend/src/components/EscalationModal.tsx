/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect, useCallback } from 'react'
import { X, Mail, MapPin } from 'lucide-react'
import toast from 'react-hot-toast'
import { createSupportTicket } from '@/api/support-api'
import { isApiError } from '@/lib/api-client'
import { useTranslation} from '@/i18n'
import FocusTrap from 'focus-trap-react'

interface EscalationModalProps {
  /** Optional guide title. When omitted, `context` is used as the reference label. */
  guideTitle?: string
  /** Optional step number within a guide. Omit for non-guide contexts. */
  stepNumber?: number
  /** Optional total steps in a guide. Omit for non-guide contexts. */
  totalSteps?: number
  /**
   * Generic context label for non-guide callers (e.g. error alerts).
   * Used in the header subtitle and as the `guide` field on the ticket payload
   * when `guideTitle` is not provided.
   */
  context?: string
  /**
   * Controlled-open state. When provided, the parent owns the modal's open state
   * and the built-in trigger button is hidden. Pair with `onClose`.
   */
  isOpen?: boolean
  /** Called when the modal requests close in controlled mode. */
  onClose?: () => void
  /** Hide the built-in trigger button. Useful for controlled mode. */
  hideTrigger?: boolean
}

export default function EscalationModal({
  guideTitle,
  stepNumber,
  totalSteps,
  context,
  isOpen,
  onClose,
  hideTrigger,
}: EscalationModalProps): React.ReactElement {
  const { t } = useTranslation()
  const isControlled = isOpen !== undefined
  const [internalShow, setInternalShow] = useState(false)
  const showModal = isControlled ? isOpen : internalShow
  const setShowModal = useCallback((next: boolean) => {
    if (isControlled) {
      if (!next) onClose?.()
    } else {
      setInternalShow(next)
    }
  }, [isControlled, onClose])
  const referenceLabel = guideTitle ?? context ?? ''
  const hasGuideContext =
    typeof stepNumber === 'number' && typeof totalSteps === 'number' && Boolean(guideTitle)
  const [selectedMethod, setSelectedMethod] = useState<'email' | 'visit' | null>(null)
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    issue: '',
  })
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleClose = useCallback(() => {
    setShowModal(false)
    setSelectedMethod(null)
    setFormData({ name: '', email: '', phone: '', issue: '' })
  }, [setShowModal])

  useEffect(() => {
    if (!showModal) return
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') handleClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [showModal, handleClose])

  const handleSubmit = async () => {
    if (!formData.name || !formData.email || !formData.issue) {
      toast.error(t('components.escalation.pleaseFillInAllRequired'))
      return
    }

    if (!selectedMethod) {
      toast.error(t('components.escalation.pleaseSelectASupportMethod'))
      return
    }

    setIsSubmitting(true)
    try {
      const supportTicket = {
        name: formData.name,
        email: formData.email,
        phone: formData.phone,
        guide: guideTitle ?? context ?? 'general',
        step: stepNumber ?? 0,
        totalSteps: totalSteps ?? 0,
        issue: formData.issue,
        method: selectedMethod,
        timestamp: new Date().toISOString(),
      }

      // Create support ticket via API
      const response = await createSupportTicket(supportTicket)

      // Show success message with ticket reference
      toast.success(t('toast.escalationModal.supportRequestSubmittedReferenceReferencenumber', { referencenumber: response.reference_number }))

      // Clear form and close modal
      setShowModal(false)
      setFormData({ name: '', email: '', phone: '', issue: '' })
      setSelectedMethod(null)
    } catch (error: unknown) {
      let errorMessage = 'Failed to submit support request. Please try again.'

      if (isApiError(error)) {
        if (error.status === 400) {
          errorMessage = 'Invalid form data. Please check and try again.'
        } else if (error.status === 401) {
          errorMessage = 'Please sign in to submit a support request.'
        } else if (error.status === 429) {
          errorMessage = 'Too many requests. Please wait a moment and try again.'
        } else if (error.status >= 500) {
          errorMessage = 'Server error. Please try again later.'
        } else {
          errorMessage = error.detail || errorMessage
        }
      }

      toast.error(errorMessage)
      Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!showModal) {
    if (hideTrigger) return <></>
    return (
      <div>
        <button
          onClick={() => setShowModal(true)}
          className="px-6 py-3 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium transition-colors"
        >
          {t('components.escalation.triggerLabel')}
        </button>
      </div>
    )
  }

  return (
    <FocusTrap active={true} focusTrapOptions={{ escapeDeactivates: false, allowOutsideClick: true, returnFocusOnDeactivate: true, fallbackFocus: () => document.body }}>
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" role="dialog" aria-modal="true" aria-labelledby="escalation-modal-heading">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="border-b border-lsc-border dark:border-earth-700 p-6 flex items-center justify-between">
          <div>
            <h2 id="escalation-modal-heading" className="font-serif text-2xl font-semibold text-lsc-dark dark:text-earth-50">
              {t('components.escalation.modalTitle')}
            </h2>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              {referenceLabel
                ? `We're here to help with "${referenceLabel}"`
                : "We're here to help."}
            </p>
          </div>
          <button
            onClick={() => setShowModal(false)}
            aria-label="Close"
            className="text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-120px)]">
          {/* Support Options */}
          <div className="mb-8">
            <h3 className="font-serif font-semibold text-lsc-dark dark:text-earth-50 mb-4">
              How would you like to get help?
            </h3>
            <div className="grid gap-4">
              <button
                onClick={() => setSelectedMethod('email')}
                className={`text-left p-4 rounded-xl border-2 transition-colors ${
                  selectedMethod === 'email'
                    ? 'border-lsc-rose bg-lsc-cream dark:bg-lsc-brown/30'
                    : 'border-lsc-border dark:border-earth-700 hover:border-lsc-rose'
                }`}
              >
                <div className="flex items-start gap-3">
                  <Mail className="w-5 h-5 text-lsc-rose flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="font-medium text-lsc-dark dark:text-earth-50">Email Support</p>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      We'll respond within 24 hours
                    </p>
                  </div>
                </div>
              </button>

              <button
                onClick={() => setSelectedMethod('visit')}
                className={`text-left p-4 rounded-xl border-2 transition-colors ${
                  selectedMethod === 'visit'
                    ? 'border-lsc-rose bg-lsc-cream dark:bg-lsc-brown/30'
                    : 'border-lsc-border dark:border-earth-700 hover:border-lsc-rose'
                }`}
              >
                <div className="flex items-start gap-3">
                  <MapPin className="w-5 h-5 text-lsc-rose flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="font-medium text-lsc-dark dark:text-earth-50">Visit In Person</p>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      Tech Help Desk - Mon, Wed, Fri 2-4 PM
                    </p>
                  </div>
                </div>
              </button>
            </div>
          </div>

          {/* Form */}
          {selectedMethod && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">
                  Name *
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder={t('placeholder.escalationModal.yourName')}
                  className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-earth-50 placeholder-earth-500 dark:placeholder-earth-500 focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">
                  Email *
                </label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  placeholder={t('placeholder.authModals.youremailexamplecom')}
                  className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-earth-50 placeholder-earth-500 dark:placeholder-earth-500 focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-earth-50 mb-1">
                  Describe Your Issue *
                </label>
                <textarea
                  value={formData.issue}
                  onChange={(e) => setFormData({ ...formData, issue: e.target.value })}
                  placeholder={t('components.escalation.pleaseDescribeWhatYouRe')}
                  rows={4}
                  className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-earth-50 placeholder-earth-500 dark:placeholder-earth-500 focus:ring-2 focus:ring-lsc-rose focus:border-transparent resize-none"
                />
              </div>

              {(hasGuideContext || context) && (
                <div className="bg-lsc-cream dark:bg-lsc-brown/20 rounded-lg p-4">
                  <p className="text-sm text-lsc-dark dark:text-lsc-cream">
                    <strong>Reference:</strong>{' '}
                    {hasGuideContext
                      ? `You are on Step ${stepNumber} of ${totalSteps} for ${guideTitle}`
                      : context}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-lsc-border dark:border-earth-700 p-6 flex gap-3 justify-end">
          <button
            onClick={() => {
              setShowModal(false)
              setSelectedMethod(null)
              setFormData({ name: '', email: '', phone: '', issue: '' })
            }}
            className="px-6 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!selectedMethod || isSubmitting}
            className="px-6 py-2 rounded-lg bg-lsc-rose hover:bg-lsc-rose/90 text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isSubmitting ? 'Submitting...' : 'Submit Request'}
          </button>
        </div>
      </div>
    </div>
    </FocusTrap>
  )
}
