/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { X, Loader2 } from 'lucide-react'
import { type Equipment, type MaintenanceType } from '../../api/equipment-api'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import { t } from '@/i18n'

const MAINTENANCE_TYPES: MaintenanceType[] = [
  'routine_check', 'cleaning', 'software_update', 'hardware_repair', 'battery_replacement',
  'screen_repair', 'accessory_replacement', 'calibration', 'deep_clean', 'diagnostic', 'other'
]

interface MaintenanceFormState {
  equipment_id: number
  maintenance_type: MaintenanceType
  scheduled_date: string
  description: string
}

interface MaintenanceFormModalProps {
  formData: MaintenanceFormState
  equipmentList: Equipment[] | undefined
  isPending: boolean
  onChange: (data: MaintenanceFormState) => void
  onSubmit: (e: React.FormEvent) => void
  onClose: () => void
}

export function MaintenanceFormModal({
  formData,
  equipmentList,
  isPending,
  onChange,
  onSubmit,
  onClose,
}: MaintenanceFormModalProps): React.ReactElement {
  const set = (field: keyof MaintenanceFormState, value: MaintenanceFormState[keyof MaintenanceFormState]) =>
    onChange({ ...formData, [field]: value })

  return (
    <ModalBackdrop onClose={onClose} title="Schedule Maintenance">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg w-full max-w-md">
        <div className="px-6 py-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
          <h2 className="text-xl font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
            Schedule Maintenance
          </h2>
          <button
            onClick={onClose}
            aria-label={t('aria.maintenanceFormModal.closeModal', 'Close')}
            className="p-2 text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream rounded-lg"
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>
        <form onSubmit={onSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Equipment *</label>
            <select
              value={formData.equipment_id}
              onChange={(e) => set('equipment_id', parseInt(e.target.value))}
              className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
              required
            >
              <option value={0}>Select equipment...</option>
              {equipmentList?.map((eq) => (
                <option key={eq.id} value={eq.id}>{eq.name} ({eq.barcode})</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Maintenance Type *</label>
            <select
              value={formData.maintenance_type}
              onChange={(e) => set('maintenance_type', e.target.value as MaintenanceType)}
              className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
              required
            >
              {MAINTENANCE_TYPES.map((type) => (
                <option key={type} value={type}>{type.charAt(0).toUpperCase() + type.slice(1)}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Scheduled Date</label>
            <input
              type="date"
              value={formData.scheduled_date}
              onChange={(e) => set('scheduled_date', e.target.value)}
              className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Description</label>
            <textarea
              value={formData.description}
              onChange={(e) => set('description', e.target.value)}
              rows={3}
              className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream resize-none"
            />
          </div>
          <div className="flex justify-end gap-3 pt-4 border-t border-lsc-border dark:border-earth-700">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isPending}
              className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg font-medium flex items-center gap-2"
            >
              {isPending && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
              Schedule
            </button>
          </div>
        </form>
      </div>
    </ModalBackdrop>
  )
}
