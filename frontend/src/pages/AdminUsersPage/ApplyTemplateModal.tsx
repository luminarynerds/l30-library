/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from 'react'
import {
  X,
  Loader2,
  Layers,
} from 'lucide-react'
import {
  PERMISSION_TEMPLATES,
  type PermissionTemplate,
} from '../../api/staff-api'
import { t } from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface ApplyTemplateModalProps {
  roleName: string
  isApplying: boolean
  onApply: (template: PermissionTemplate) => void
  onCancel: () => void
}

const ApplyTemplateModal: React.FC<ApplyTemplateModalProps> = ({
  roleName,
  isApplying,
  onApply,
  onCancel,
}) => {
  return (
    <ModalBackdrop onClose={onCancel} title="Apply Template">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 shadow-lg max-w-md w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-lsc-border dark:border-earth-700 sticky top-0 bg-lsc-white dark:bg-earth-800">
          <div className="flex items-center justify-between">
            <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">
              Apply Template
            </h2>
            <button
              onClick={onCancel}
              className="text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream transition-colors"
              aria-label={t('aria.addRoleModal.closeModal')}
            >
              <X className="w-6 h-6" />
            </button>
          </div>
        </div>

        <div className="p-6 space-y-4">
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            Select a template to apply to <span className="font-semibold">{roleName}</span>. This will replace all current permissions with the template's permissions.
          </p>

          <div className="space-y-2 max-h-[calc(90vh-300px)] overflow-y-auto">
            {PERMISSION_TEMPLATES.map((template) => (
              <button
                key={template.name}
                onClick={() => onApply(template)}
                disabled={isApplying}
                className="w-full text-left p-4 border border-lsc-border dark:border-earth-700 hover:border-lsc-rose hover:bg-lsc-rose/5 dark:hover:bg-lsc-rose/10 rounded-xl transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed group"
              >
                <div className="flex items-start gap-3">
                  {isApplying ? (
                    <Loader2 className="w-5 h-5 text-lsc-rose motion-safe:animate-spin flex-shrink-0 mt-0.5" />
                  ) : (
                    <Layers className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70 group-hover:text-lsc-rose flex-shrink-0 mt-0.5 transition-colors" />
                  )}
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                      {template.name}
                    </p>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                      {template.description}
                    </p>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </ModalBackdrop>
  )
}

export default ApplyTemplateModal
