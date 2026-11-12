/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { X } from 'lucide-react'
import { useTranslation } from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface Props {
  onExport: (type: string) => void
  onClose: () => void
}

export function ExportModal({ onExport, onClose }: Props) {
  const { t } = useTranslation()
  return (
    <ModalBackdrop onClose={onClose} title="Export Data">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg max-w-md w-full">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">Export Data</h2>
            <button onClick={onClose} className="text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream">
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="space-y-3">
            {[
              { key: 'partners', label: 'Partners', desc: t('staffOutreach.exportAllPartnerData') },
              { key: 'visits', label: 'Visits', desc: 'Export visit history' },
              { key: 'checkouts', label: 'Bulk Checkouts', desc: 'Export checkout data' },
              { key: 'deposits', label: 'Deposits', desc: 'Export deposit records' },
              { key: 'cards', label: 'Institutional Cards', desc: 'Export card data' },
            ].map((item) => (
              <button
                key={item.key}
                onClick={() => onExport(item.key)}
                className="w-full p-3 text-left bg-lsc-cream dark:bg-earth-700 hover:bg-lsc-border dark:hover:bg-earth-600 rounded-lg transition-colors"
              >
                <p className="font-medium text-lsc-dark dark:text-lsc-cream">{item.label}</p>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{item.desc}</p>
              </button>
            ))}
          </div>
        </div>
      </div>
    </ModalBackdrop>
  )
}
