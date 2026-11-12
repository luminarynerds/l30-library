/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { X, Check } from "lucide-react"
import { useTranslation } from "@/i18n"
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface Props {
  resolveNotes: string
  setResolveNotes: (notes: string) => void
  onResolve: () => void
  onClose: () => void
}

export function ResolveAlertModal({ resolveNotes, setResolveNotes, onResolve, onClose }: Props) {
  const { t } = useTranslation()

  return (
    <ModalBackdrop onClose={onClose} title="Resolve Security Alert">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg w-full max-w-md">
        <div className="px-6 py-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
          <h2 className="text-xl font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Resolve Security Alert</h2>
          <button onClick={onClose} className="inline-flex items-center justify-center min-w-[44px] min-h-[44px] p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark/70 dark:text-lsc-cream/70 rounded-xl" aria-label={t('staffRFID.closeResolveAlertForm')}><X aria-hidden="true" className="w-5 h-5" /></button>
        </div>
        <div className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Resolution Notes *</label>
            <textarea
              value={resolveNotes}
              onChange={(e) => setResolveNotes(e.target.value)}
              rows={3}
              placeholder={t('staffRFID.describeHowTheAlertWas')}
              className="w-full px-4 py-2 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream resize-none"
              required
            />
          </div>
          <div className="flex justify-end gap-3 pt-4 border-t border-lsc-border dark:border-earth-700">
            <button onClick={onClose} className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream rounded-xl font-medium">Cancel</button>
            <button onClick={onResolve} disabled={!resolveNotes.trim()} className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-earth-300 text-white rounded-xl font-medium flex items-center gap-2"><Check className="w-4 h-4" />Resolve</button>
          </div>
        </div>
      </div>
    </ModalBackdrop>
  )
}
