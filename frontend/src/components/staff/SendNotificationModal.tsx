/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * SendNotificationModal Component
 *
 * A modal for sending notifications to patrons.
 * Supports different notification types and templates.
 */

import { useState, useRef, useEffect } from 'react'
import { Loader2, Send, Mail, MessageSquare, AlertCircle } from 'lucide-react'
import type { Patron } from '@/api/staff-api'
import type { NotificationTemplate } from '@/api/staff-api'
import toast from 'react-hot-toast'
import { Modal } from '../ui/Modal'
import { t } from '@/i18n'

// ==================== Types ====================

interface SendNotificationModalProps {
  isOpen: boolean
  patron: Patron | null
  onClose: () => void
  onSend?: (patron: Patron, data: NotificationData) => Promise<void>
  availableTemplates?: NotificationTemplate[]
}

interface NotificationData {
  type: 'email' | 'sms'
  template: string
  subject?: string
  message: string
}

type NotificationType = 'email' | 'sms'

const NOTIFICATION_TEMPLATES: Array<{ id: string; name: string; notification_types: string[]; subject?: string; body: string }> = [
  { id: 'overdue', name: 'Overdue Notice', notification_types: ['email', 'sms'], subject: 'Overdue Items', body: 'You have overdue items. Please return them as soon as possible.' },
  { id: 'hold_ready', name: 'Hold Ready', notification_types: ['email', 'sms'], subject: 'Hold Ready for Pickup', body: 'Your held item is ready for pickup.' },
  { id: 'account_update', name: 'Account Update', notification_types: ['email'], subject: 'Account Update', body: 'Your account has been updated.' },
]

// ==================== Component ====================

export default function SendNotificationModal({
  isOpen,
  patron,
  onClose,
  onSend,
  // kept for API compatibility; templates are sourced from NOTIFICATION_TEMPLATES below
  availableTemplates: _availableTemplates = [],
}: SendNotificationModalProps): React.ReactElement | null {
  const [notificationType, setNotificationType] = useState<NotificationType>('email')
  const [selectedTemplate, setSelectedTemplate] = useState<string>('')
  const [subject, setSubject] = useState('')
  const [message, setMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const closeButtonRef = useRef<HTMLButtonElement>(null)
  const previousActiveElement = useRef<HTMLElement | null>(null)

  // Store and restore focus
  useEffect(() => {
    if (isOpen) {
      previousActiveElement.current = document.activeElement as HTMLElement
      const timer = setTimeout(() => {
        closeButtonRef.current?.focus()
      }, 100)
      return () => clearTimeout(timer)
    } else {
      // Reset state when closing
      setNotificationType('email')
      setSelectedTemplate('')
      setSubject('')
      setMessage('')
      if (previousActiveElement.current) {
        previousActiveElement.current.focus()
      }
    }
  }, [isOpen])

  // Update message when template changes
  useEffect(() => {
    const template = NOTIFICATION_TEMPLATES.find(t => t.id === selectedTemplate)
    if (template) {
      setSubject(template.subject || '')
      setMessage(template.body)
    }
  }, [selectedTemplate])

  // Handle send
  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!patron || !message.trim() || isLoading) return

    setIsLoading(true)
    try {
      const data: NotificationData = {
        type: notificationType,
        template: selectedTemplate,
        ...(notificationType === 'email' ? { subject } : {}),
        message: message.trim(),
      }

      if (onSend) {
        await onSend(patron, data)
      } else {
        // Simulate sending notification
        await new Promise(resolve => setTimeout(resolve, 1000))
      }

      toast.success(t('toast.staff.notificationSentToFirstnameLastname', { firstname: patron.first_name, lastname: patron.last_name }))
      onClose()
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : t('toast.staff.failedToSendNotification'))
    } finally {
      setIsLoading(false)
    }
  }

  // Filter templates by notification type
  const filteredTemplates = NOTIFICATION_TEMPLATES.filter((t: { notification_types: string[]; id: string; name: string }) =>
    t.notification_types.includes(notificationType)
  )

  if (!isOpen || !patron) return null

  const getTypeIcon = (type: NotificationType) => {
    switch (type) {
      case 'email':
        return Mail
      case 'sms':
        return MessageSquare
    }
  }

  const modalTitle = `Send Notification - ${patron.first_name} ${patron.last_name}`

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={modalTitle}
      size="lg"
    >
      {/* Content */}
      <form onSubmit={handleSend} className="space-y-4" style={{maxHeight: 'calc(85vh - 200px)', overflowY: 'auto'}}>
              {/* Notification Type */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                  Notification Type
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {(['email', 'sms'] as NotificationType[]).map((type) => {
                    const Icon = getTypeIcon(type)
                    const isDisabled = type === 'sms' && !patron.phone
                    return (
                      <button
                        key={type}
                        type="button"
                        disabled={isDisabled}
                        onClick={() => {
                          setNotificationType(type)
                          // Reset template if not available for this type
                          const template = NOTIFICATION_TEMPLATES.find(t => t.id === selectedTemplate)
                          if (template && !template.notification_types.includes(type)) {
                            setSelectedTemplate('')
                          }
                        }}
                        className={`flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl border text-sm font-medium transition-colors ${
                          notificationType === type
                            ? 'bg-lsc-rose text-white border-lsc-rose'
                            : 'bg-lsc-white dark:bg-lsc-brown border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:border-lsc-rose'
                        } ${isDisabled ? 'opacity-50 cursor-not-allowed' : ''}`}
                      >
                        <Icon className="w-4 h-4" aria-hidden="true" />
                        <span className="capitalize">{type.toUpperCase()}</span>
                      </button>
                    )
                  })}
                </div>
                {notificationType === 'sms' && !patron.phone && (
                  <p className="mt-2 text-xs text-status-warning-700 dark:text-status-warning-400 flex items-center gap-1">
                    <AlertCircle className="w-3 h-3" aria-hidden="true" />
                    No phone number on file
                  </p>
                )}
              </div>

              {/* Template Selection */}
              <div className="mb-4">
                <label
                  htmlFor="notification-template"
                  className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2"
                >
                  Template
                </label>
                <select
                  id="notification-template"
                  value={selectedTemplate}
                  onChange={(e) => setSelectedTemplate(e.target.value)}
                  className="w-full px-3 py-2.5 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                >
                  {filteredTemplates.map((template: { id: string; name: string }) => (
                    <option key={template.id} value={template.id}>
                      {template.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Subject (email only) */}
              {notificationType === 'email' && (
                <div className="mb-4">
                  <label
                    htmlFor="notification-subject"
                    className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2"
                  >
                    Subject
                  </label>
                  <input
                    id="notification-subject"
                    type="text"
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                    placeholder={t('placeholder.staff.emailSubject')}
                    className="w-full px-3 py-2.5 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                  />
                </div>
              )}

              {/* Message */}
              <div className="mb-4">
                <label
                  htmlFor="notification-message"
                  className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2"
                >
                  Message
                </label>
                <textarea
                  id="notification-message"
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder={t('placeholder.staff.enterYourMessage')}
                  rows={4}
                  className="w-full px-3 py-2.5 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent resize-none"
                />
                <p className="mt-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                  {message.length} / 500 characters
                </p>
              </div>

              {/* Recipient Info */}
              <div className="p-3 bg-lsc-cream/50 dark:bg-lsc-brown/30 rounded-xl mb-4">
                <h3 className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                  Recipient
                </h3>
                <div className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 space-y-1">
                  <p>
                    <span className="font-medium">Name:</span> {patron.first_name} {patron.last_name}
                  </p>
                  <p>
                    <span className="font-medium">Email:</span> {patron.email}
                  </p>
                  {patron.phone && (
                    <p>
                      <span className="font-medium">Phone:</span> {patron.phone}
                    </p>
                  )}
                </div>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={!message.trim() || isLoading}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-lsc-rose/50 text-white rounded-xl font-medium transition-colors disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-5 h-5 motion-safe:animate-spin" aria-hidden="true" />
                    <span>Sending...</span>
                  </>
                ) : (
                  <>
                    <Send className="w-5 h-5" aria-hidden="true" />
                    <span>Send Notification</span>
                  </>
                )}
              </button>
      </form>
    </Modal>
  )
}
