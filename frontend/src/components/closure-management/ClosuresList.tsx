/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState } from 'react'
import {
  AlertCircle,
  Calendar,
  CheckCircle,
  Clock,
  Eye,
} from 'lucide-react'
import { ClosureManagementPanel } from './ClosureManagementPanel'
import { useTranslation } from '@/i18n'
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

interface ClosuresListProps {
  closures: BranchClosure[]
  isLoading?: boolean
  onRefresh?: () => void
}

export const ClosuresList: React.FC<ClosuresListProps> = ({
  closures,
  isLoading,
  onRefresh,
}) => {
  const { t } = useTranslation()
  const [selectedClosure, setSelectedClosure] = useState<BranchClosure | null>(null)

  if (isLoading) {
    return (
      <div className="p-6 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
        <Clock className="w-8 h-8 mx-auto mb-2 motion-safe:animate-spin" />
        Loading closures...
      </div>
    )
  }

  if (closures.length === 0) {
    return (
      <div className="p-6 text-center text-lsc-dark/70 dark:text-lsc-cream/70">
        <CheckCircle className="w-8 h-8 mx-auto mb-2 text-status-success-600" />
        <p>{t('components.closureManagement.closuresList.noActiveOrUpcomingClosures')}</p>
      </div>
    )
  }

  const today = new Date().toISOString().split('T')[0]!
  const activeClosure = closures.find(
    (c) => c.start_date <= today && c.end_date >= today
  )
  const upcomingClosures = closures.filter((c) => c.start_date > today)

  const getCompletionPercentage = (closure: BranchClosure): number => {
    const tasks = [
      closure.patrons_with_holds_notified,
      closure.staff_notified,
      closure.website_updated,
      closure.events_canceled,
    ]
    return Math.round((tasks.filter(Boolean).length / tasks.length) * 100)
  }

  return (
    <div className="space-y-6">
      {/* Active Closure */}
      {activeClosure && (
        <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border-2 border-status-danger-200 dark:border-status-danger-800 rounded-lg p-6">
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-6 h-6 text-status-danger-600 flex-shrink-0 mt-1" />
              <div>
                <h3 className="font-serif text-lg font-bold text-status-danger-900 dark:text-status-danger-200">
                  Active Closure Today
                </h3>
                <p className="text-status-danger-700 dark:text-status-danger-300 font-medium mt-1">
                  {activeClosure.reason}
                </p>
              </div>
            </div>
            <button
              onClick={() => setSelectedClosure(activeClosure)}
              className="px-3 py-2 bg-status-danger-600 hover:bg-status-danger-700 text-white rounded font-medium flex items-center gap-2 transition"
            >
              <Eye className="w-4 h-4" />
              Manage
            </button>
          </div>

          {/* Completion Progress */}
          <div className="mb-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-status-danger-800 dark:text-status-danger-300">
                Completion
              </span>
              <span className="text-sm font-bold text-status-danger-900 dark:text-status-danger-200">
                {getCompletionPercentage(activeClosure)}%
              </span>
            </div>
            <div className="h-2 bg-status-danger-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-status-danger-600 rounded-full transition-all"
                style={{
                  width: `${getCompletionPercentage(activeClosure)}%`,
                }}
              />
            </div>
          </div>

          {/* Status Grid */}
          <div className="grid grid-cols-2 gap-3">
            <div className="flex items-center gap-2 text-sm">
              {activeClosure.patrons_with_holds_notified ? (
                <CheckCircle className="w-4 h-4 text-status-success-600" />
              ) : (
                <Clock className="w-4 h-4 text-status-warning-600" />
              )}
              <span className="text-status-danger-800 dark:text-status-danger-200">Patrons Notified</span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              {activeClosure.staff_notified ? (
                <CheckCircle className="w-4 h-4 text-status-success-600" />
              ) : (
                <Clock className="w-4 h-4 text-status-warning-600" />
              )}
              <span className="text-status-danger-800 dark:text-status-danger-200">Staff Notified</span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              {activeClosure.website_updated ? (
                <CheckCircle className="w-4 h-4 text-status-success-600" />
              ) : (
                <Clock className="w-4 h-4 text-status-warning-600" />
              )}
              <span className="text-status-danger-800 dark:text-status-danger-200">Website Updated</span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              {activeClosure.events_canceled ? (
                <CheckCircle className="w-4 h-4 text-status-success-600" />
              ) : (
                <Clock className="w-4 h-4 text-status-warning-600" />
              )}
              <span className="text-status-danger-800 dark:text-status-danger-200">Events Canceled</span>
            </div>
          </div>
        </div>
      )}

      {/* Upcoming Closures */}
      {upcomingClosures.length > 0 && (
        <div>
          <h3 className="font-serif text-lg font-bold text-lsc-dark dark:text-lsc-cream mb-4">
            Upcoming Closures
          </h3>
          <div className="space-y-3">
            {upcomingClosures.map((closure) => (
              <div
                key={closure.id}
                className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg p-4 hover:shadow-md transition"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <Calendar className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
                      <h4 className="font-medium text-lsc-dark dark:text-lsc-cream">
                        {closure.reason}
                      </h4>
                    </div>
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                      {parseDate(closure.start_date)?.toLocaleDateString() ?? '-'} -{' '}
                      {parseDate(closure.end_date)?.toLocaleDateString() ?? '-'}
                    </p>
                    {closure.description && (
                      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                        {closure.description}
                      </p>
                    )}
                  </div>
                  <button
                    onClick={() => setSelectedClosure(closure)}
                    className="px-3 py-2 text-lsc-rose dark:text-lsc-rose-light hover:bg-earth-50 dark:bg-earth-800/20 dark:hover:bg-earth-800/20 rounded font-medium flex items-center gap-2 transition"
                  >
                    <Eye className="w-4 h-4" />
                    Details
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Management Panel */}
      {selectedClosure && (
        <ClosureManagementPanel
          closure={selectedClosure}
          onClose={() => setSelectedClosure(null)}
          onUpdate={(_closure) => {
            // Update closure data
            onRefresh?.()
          }}
        />
      )}
    </div>
  )
}
