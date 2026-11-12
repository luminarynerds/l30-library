/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState } from 'react'
import {
  AlertCircle,
  CheckCircle,
  Clock,
  Globe,
  MapPin,
  MessageSquare,
  Phone,
  Users,
  X,
} from 'lucide-react'
import { useTranslation } from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import { parseDate } from '@/utils/format-utils'

interface BranchClosure {
  id: number
  branch_id: number
  start_date: string
  end_date: string
  start_time?: string
  end_time?: string
  reason: string
  description?: string
  closure_documentation?: string
  reopening_announcement?: string
  patrons_with_holds_notified: boolean
  staff_notified: boolean
  partner_organizations_notified: boolean
  website_updated: boolean
  phone_message_updated: boolean
  social_media_updated: boolean
  google_maps_updated: boolean
  apple_maps_updated: boolean
  events_canceled: boolean
  programs_rescheduled: boolean
  created_at: string
  created_by_id?: number
}

interface ClosureManagementPanelProps {
  closure: BranchClosure
  onClose: () => void
  onUpdate: (closure: BranchClosure) => void
}

export const ClosureManagementPanel: React.FC<ClosureManagementPanelProps> = ({
  closure,
  onClose,
  onUpdate: _onUpdate,
}) => {
  const { t } = useTranslation()
  const [activeTab, setActiveTab] = useState<
    'overview' | 'notifications' | 'external' | 'events' | 'reopening'
  >('overview')

  const statusItems = [
    {
      icon: Users,
      label: 'Patrons with Holds',
      completed: closure.patrons_with_holds_notified,
      description: t('components.closureManagement.closureManagementPanel.notifyPatronsWithReadyHolds'),
    },
    {
      icon: Users,
      label: 'Staff Notifications',
      completed: closure.staff_notified,
      description: t('components.closureManagement.closureManagementPanel.cascadeNotificationsToStaff'),
    },
    {
      icon: MapPin,
      label: 'Partner Organizations',
      completed: closure.partner_organizations_notified,
      description: 'Notify partner organizations',
    },
    {
      icon: Globe,
      label: 'Website Updated',
      completed: closure.website_updated,
      description: 'Update website content',
    },
    {
      icon: Phone,
      label: 'Phone Message',
      completed: closure.phone_message_updated,
      description: t('components.closureManagement.closureManagementPanel.updatePhoneSystemMessage'),
    },
    {
      icon: MessageSquare,
      label: 'Social Media',
      completed: closure.social_media_updated,
      description: t('components.closureManagement.closureManagementPanel.updateSocialMediaPosts'),
    },
    {
      icon: MapPin,
      label: 'Google Maps',
      completed: closure.google_maps_updated,
      description: t('components.closureManagement.closureManagementPanel.updateGoogleBusinessProfile'),
    },
    {
      icon: MapPin,
      label: 'Apple Maps',
      completed: closure.apple_maps_updated,
      description: 'Update Apple Maps',
    },
  ]

  const eventItems = [
    {
      label: 'Events Canceled',
      completed: closure.events_canceled,
      description: 'Cancel today\'s events',
    },
    {
      label: 'Programs Rescheduled',
      completed: closure.programs_rescheduled,
      description: 'Reschedule affected programs',
    },
  ]

  return (
    <ModalBackdrop onClose={onClose} title="Closure Management">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-gradient-to-r from-red-600 to-red-700 text-white p-6 flex justify-between items-start">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <AlertCircle className="w-6 h-6" />
              <h2 className="text-2xl font-serif font-bold">Closure Management</h2>
            </div>
            <p className="text-status-danger-100">{closure.reason}</p>
          </div>
          <button
            onClick={onClose}
            aria-label="Close closure management"
            className="text-white hover:bg-status-danger-700 p-2 rounded"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Tabs */}
        <div className="border-b border-lsc-border dark:border-earth-700 sticky top-16 bg-earth-50 dark:bg-earth-900">
          <div className="flex gap-1 p-0">
            {['overview', 'notifications', 'external', 'events', 'reopening'].map(
              (tab) => (
                <button
                  key={tab}
                  aria-pressed={activeTab === tab}
                  onClick={() =>
                    setActiveTab(
                      tab as
                        | 'overview'
                        | 'notifications'
                        | 'external'
                        | 'events'
                        | 'reopening'
                    )
                  }
                  className={`px-4 py-3 font-medium capitalize border-b-2 transition ${
                    activeTab === tab
                      ? 'border-status-danger-600 text-status-danger-600'
                      : 'border-transparent text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-earth-800 dark:hover:text-earth-200'
                  }`}
                >
                  {tab}
                </button>
              )
            )}
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {activeTab === 'overview' && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
                    Start Date
                  </label>
                  <p className="text-lg font-semibold">
                    {parseDate(closure.start_date)?.toLocaleDateString() ?? '-'}
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70">
                    End Date
                  </label>
                  <p className="text-lg font-semibold">
                    {parseDate(closure.end_date)?.toLocaleDateString() ?? '-'}
                  </p>
                </div>
              </div>

              {closure.closure_documentation && (
                <div>
                  <label className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 block mb-2">
                    Documentation
                  </label>
                  <div className="bg-earth-50 dark:bg-earth-900 p-4 rounded border border-lsc-border dark:border-earth-700">
                    {closure.closure_documentation}
                  </div>
                </div>
              )}

              <div className="bg-earth-50 dark:bg-earth-800/20 border border-lsc-border dark:border-earth-700 rounded p-4">
                <p className="text-sm text-earth-800 dark:text-lsc-rose-light">
                  <strong>Created:</strong>{' '}
                  {new Date(closure.created_at).toLocaleString()}
                </p>
              </div>
            </div>
          )}

          {activeTab === 'notifications' && (
            <div className="space-y-4">
              {statusItems.slice(0, 3).map((item, index) => (
                <div
                  key={index}
                  className="flex items-start gap-4 p-4 border border-lsc-border dark:border-earth-700 rounded-lg hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800"
                >
                  <item.icon className="w-5 h-5 mt-1 flex-shrink-0" />
                  <div className="flex-1">
                    <h4 className="font-medium">{item.label}</h4>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{item.description}</p>
                  </div>
                  {item.completed ? (
                    <CheckCircle className="w-5 h-5 text-status-success-600 flex-shrink-0" />
                  ) : (
                    <Clock className="w-5 h-5 text-status-warning-600 flex-shrink-0" />
                  )}
                </div>
              ))}
            </div>
          )}

          {activeTab === 'external' && (
            <div className="space-y-4">
              {statusItems.slice(3).map((item, index) => (
                <div
                  key={index}
                  className="flex items-start gap-4 p-4 border border-lsc-border dark:border-earth-700 rounded-lg hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800"
                >
                  <item.icon className="w-5 h-5 mt-1 flex-shrink-0" />
                  <div className="flex-1">
                    <h4 className="font-medium">{item.label}</h4>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{item.description}</p>
                  </div>
                  {item.completed ? (
                    <CheckCircle className="w-5 h-5 text-status-success-600 flex-shrink-0" />
                  ) : (
                    <Clock className="w-5 h-5 text-status-warning-600 flex-shrink-0" />
                  )}
                </div>
              ))}
            </div>
          )}

          {activeTab === 'events' && (
            <div className="space-y-4">
              {eventItems.map((item, index) => (
                <div
                  key={index}
                  className="flex items-start gap-4 p-4 border border-lsc-border dark:border-earth-700 rounded-lg hover:bg-earth-50 dark:bg-earth-900 dark:hover:bg-earth-800"
                >
                  <Clock className="w-5 h-5 mt-1 flex-shrink-0" />
                  <div className="flex-1">
                    <h4 className="font-medium">{item.label}</h4>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{item.description}</p>
                  </div>
                  {item.completed ? (
                    <CheckCircle className="w-5 h-5 text-status-success-600 flex-shrink-0" />
                  ) : (
                    <Clock className="w-5 h-5 text-status-warning-600 flex-shrink-0" />
                  )}
                </div>
              ))}
            </div>
          )}

          {activeTab === 'reopening' && (
            <div className="space-y-4">
              {closure.reopening_announcement ? (
                <div>
                  <label className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 block mb-2">
                    Reopening Announcement
                  </label>
                  <div className="bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-800 rounded p-4">
                    <p className="text-status-success-800 dark:text-status-success-300">{closure.reopening_announcement}</p>
                  </div>
                </div>
              ) : (
                <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded p-4">
                  <p className="text-status-warning-800 dark:text-status-warning-300">
                    No reopening announcement scheduled yet.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="bg-earth-50 dark:bg-earth-900 border-t border-lsc-border dark:border-earth-700 p-6 flex justify-end gap-4">
          <button
            onClick={onClose}
            className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 bg-earth-100 dark:bg-earth-700 hover:bg-earth-200 dark:hover:bg-earth-600 rounded font-medium transition"
          >
            Close
          </button>
        </div>
      </div>
    </ModalBackdrop>
  )
}
