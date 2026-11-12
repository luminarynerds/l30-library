/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { UserX, Phone, Mail, AlertTriangle } from "lucide-react"

interface EstateManagementPanelProps {
  patronId: number
  isDeceased: boolean
  dateOfDeath?: string | null
  estateContactName?: string | null
  estateContactEmail?: string | null
  estateContactPhone?: string | null
  estateFollowupRequired?: boolean
}

export function EstateManagementPanel({
  isDeceased,
  dateOfDeath,
  estateContactName,
  estateContactEmail,
  estateContactPhone,
  estateFollowupRequired,
}: EstateManagementPanelProps) {
  if (!isDeceased) return null

  const hasEstateContact = estateContactName || estateContactEmail || estateContactPhone

  return (
    <div className="bg-earth-50 dark:bg-earth-800/50 rounded-xl p-6">
      <div className="flex items-center gap-3 mb-4">
        <UserX className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
        <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">Estate Management</h3>
        {estateFollowupRequired && (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium text-status-warning-700 dark:text-status-warning-400 bg-status-warning-100 dark:bg-status-warning-900/30 rounded-full">
            <AlertTriangle className="w-3 h-3" />
            Follow-up needed
          </span>
        )}
      </div>

      <div className="space-y-3 text-sm">
        {dateOfDeath && (
          <div className="text-lsc-dark/70 dark:text-lsc-cream/70">
            <span className="font-medium text-lsc-dark dark:text-lsc-cream">Date of death:</span>{' '}
            {new Date(dateOfDeath).toLocaleDateString()}
          </div>
        )}

        {hasEstateContact ? (
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg p-4 border border-lsc-border dark:border-earth-700">
            <div className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/50 uppercase tracking-wider mb-2">Estate Contact</div>
            {estateContactName && (
              <div className="font-medium text-lsc-dark dark:text-lsc-cream mb-1">{estateContactName}</div>
            )}
            {estateContactEmail && (
              <div className="flex items-center gap-1.5 text-lsc-dark/70 dark:text-lsc-cream/70">
                <Mail className="w-3.5 h-3.5" />
                {estateContactEmail}
              </div>
            )}
            {estateContactPhone && (
              <div className="flex items-center gap-1.5 text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">
                <Phone className="w-3.5 h-3.5" />
                {estateContactPhone}
              </div>
            )}
          </div>
        ) : (
          <p className="text-lsc-dark/70 dark:text-lsc-cream/50 italic">
            No estate contact information on file.
          </p>
        )}
      </div>
    </div>
  )
}
