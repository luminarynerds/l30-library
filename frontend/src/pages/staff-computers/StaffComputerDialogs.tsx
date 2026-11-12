/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Loader2, XCircle } from 'lucide-react'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import { t } from '@/i18n'
import type { MaintenanceTarget } from './model'

const inputCls = 'w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream'
const labelCls = 'block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1'

interface MaintenanceDialogProps {
  target: MaintenanceTarget
  pending: boolean
  onClose: () => void
  onConfirm: () => void
}

export function MaintenanceDialog({ target, pending, onClose, onConfirm }: MaintenanceDialogProps) {
  return (
    <ModalBackdrop onClose={onClose} title="Mark Maintenance">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-sm w-full">
        <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
          <h3 className="text-xl font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Mark Maintenance</h3>
          <button onClick={onClose} disabled={pending} aria-label={t('aria.addRoleModal.closeModal')}>
            <XCircle className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/60" />
          </button>
        </div>
        <div className="p-4 space-y-4">
          <p className="text-sm text-lsc-dark dark:text-lsc-cream">
            Take <span className="font-medium">{target.computerName}</span> offline for maintenance? Patrons won't be able to reserve it until you mark it Available again.
          </p>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={onClose} disabled={pending} className="px-4 py-2 rounded-lg text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700">Cancel</button>
            <button type="button" onClick={onConfirm} disabled={pending} className="px-4 py-2 rounded-lg bg-status-warning-600 text-white hover:bg-status-warning-700 disabled:opacity-50 flex items-center gap-2">
              {pending && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
              Mark Maintenance
            </button>
          </div>
        </div>
      </div>
    </ModalBackdrop>
  )
}

interface RescheduleDialogProps {
  status: string
  start: string
  end: string
  pending: boolean
  onStartChange: (value: string) => void
  onEndChange: (value: string) => void
  onClose: () => void
  onConfirm: () => void
}

export function RescheduleDialog({
  status, start, end, pending, onStartChange, onEndChange, onClose, onConfirm,
}: RescheduleDialogProps) {
  return (
    <ModalBackdrop onClose={onClose} title="Reschedule reservation">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-md w-full">
        <div className="p-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
          <h3 className="text-xl font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Reschedule reservation</h3>
          <button onClick={onClose} disabled={pending} aria-label={t('aria.addRoleModal.closeModal')}>
            <XCircle className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/60" />
          </button>
        </div>
        <div className="p-4 space-y-4">
          {status === 'in_session' ? (
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">This session is in progress, so only its end time can change.</p>
          ) : (
            <div>
              <label className={labelCls} htmlFor="reschedule-start">Start</label>
              <input id="reschedule-start" type="datetime-local" value={start} onChange={event => onStartChange(event.target.value)} className={inputCls} />
            </div>
          )}
          <div>
            <label className={labelCls} htmlFor="reschedule-end">End</label>
            <input id="reschedule-end" type="datetime-local" value={end} onChange={event => onEndChange(event.target.value)} className={inputCls} />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} disabled={pending} className="px-4 py-2 rounded-lg text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700">Cancel</button>
            <button type="button" onClick={onConfirm} disabled={pending} className="px-4 py-2 rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 disabled:opacity-50 flex items-center gap-2">
              {pending && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
              Save
            </button>
          </div>
        </div>
      </div>
    </ModalBackdrop>
  )
}
