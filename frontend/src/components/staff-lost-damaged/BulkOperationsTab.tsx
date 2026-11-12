/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import {
  Archive, Wrench, Clock, Users, AlertCircle,
} from "lucide-react"
import { useTranslation } from '@/i18n'

interface BulkOperationsTabProps {
  setShowBulkWriteOffModal: (v: boolean) => void
  setShowBulkAssignModal: (v: boolean) => void
  setShowAutoConvertModal: (v: boolean) => void
}

export function BulkOperationsTab({
  setShowBulkWriteOffModal,
  setShowBulkAssignModal,
  setShowAutoConvertModal,
}: BulkOperationsTabProps): React.ReactElement {
  const { t } = useTranslation()
  return (
    <div className="space-y-6">
      <div className="grid md:grid-cols-3 gap-6">
        {/* Bulk Write-Off */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2 flex items-center gap-2">
            <Archive className="w-5 h-5" /> Bulk Write-Off
          </h3>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
            Write off multiple lost items that will not be recovered.
          </p>
          <button
            onClick={() => setShowBulkWriteOffModal(true)}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-earth-600 hover:bg-earth-700 text-white rounded-lg"
          >
            <Archive className="w-4 h-4" /> Open Bulk Write-Off
          </button>
        </div>

        {/* Bulk Mending Assignment */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2 flex items-center gap-2">
            <Wrench className="w-5 h-5" /> Bulk Mending Assign
          </h3>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
            Assign multiple mending queue items to a staff member.
          </p>
          <button
            onClick={() => setShowBulkAssignModal(true)}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-category-600 hover:bg-category-700 text-white rounded-lg"
          >
            <Users className="w-4 h-4" /> Open Bulk Assign
          </button>
        </div>

        {/* Auto-Convert Overdue */}
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 border border-lsc-border dark:border-earth-700">
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-2 flex items-center gap-2">
            <Clock className="w-5 h-5" /> Auto-Convert Overdue
          </h3>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
            Automatically mark overdue items as lost after threshold.
          </p>
          <button
            onClick={() => setShowAutoConvertModal(true)}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg"
          >
            <Clock className="w-4 h-4" /> Configure Auto-Convert
          </button>
        </div>
      </div>

      {/* Instructions */}
      <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-xl p-6">
        <h4 className="font-medium text-status-warning-800 dark:text-status-warning-400 mb-2 flex items-center gap-2">
          <AlertCircle className="w-5 h-5" /> Bulk Operations Guidelines
        </h4>
        <ul className="text-sm text-status-warning-700 dark:text-status-warning-500 space-y-1 list-disc list-inside">
          <li>{t('components.staffLostDamaged.bulkOperationsTab.alwaysPreviewChangesBeforeExecuting')}</li>
          <li>{t('components.staffLostDamaged.bulkOperationsTab.bulkWriteOffsArePermanent')}</li>
          <li>{t('components.staffLostDamaged.bulkOperationsTab.autoConvertUsesADry')}</li>
          <li>{t('components.staffLostDamaged.bulkOperationsTab.maximumItemsCanBeProcessed')}</li>
        </ul>
      </div>
    </div>
  )
}
