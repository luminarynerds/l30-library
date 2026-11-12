/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { X, Loader2 } from 'lucide-react'
import { useTranslation } from '@/i18n'
import {
  formatEquipmentType,
  formatCondition,
  type EquipmentType,
  type EquipmentCondition,
} from '../../api/equipment-api'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

const EQUIPMENT_TYPES: EquipmentType[] = [
  'laptop', 'hotspot', 'projector', 'tablet', 'e_reader', 'camera',
  'audio_recorder', 'calculator', 'charger', 'headphones', 'keyboard', 'mouse',
  'webcam', 'microphone', 'tripod', 'light_kit', 'gaming_console', 'vr_headset', 'telescope', 'other'
]

const EQUIPMENT_CONDITIONS: EquipmentCondition[] = [
  'excellent', 'good', 'fair', 'poor', 'needs_repair', 'non_functional'
]

interface EquipmentFormState {
  name: string
  equipment_type: EquipmentType
  description: string
  barcode: string
  serial_number: string
  manufacturer: string
  model: string
  condition: EquipmentCondition
  location: string
  loan_period_days: number
  max_renewals: number
  deposit_required: string
  included_accessories: string
  return_instructions: string
  notes: string
}

interface EquipmentFormModalProps {
  editingEquipment: { id: number } | null
  formData: EquipmentFormState
  onChange: (data: EquipmentFormState) => void
  onSubmit: (e: React.FormEvent) => void
  onClose: () => void
  isPending: boolean
}

export function EquipmentFormModal({
  editingEquipment,
  formData,
  onChange,
  onSubmit,
  onClose,
  isPending,
}: EquipmentFormModalProps): React.ReactElement {
  const { t } = useTranslation()
  const set = (field: keyof EquipmentFormState, value: EquipmentFormState[keyof EquipmentFormState]) =>
    onChange({ ...formData, [field]: value })

  return (
    <ModalBackdrop onClose={onClose} title="Add New Equipment">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg w-full max-w-2xl my-8">
        <div className="px-6 py-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
          <h2 className="text-xl font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
            {editingEquipment ? "Edit Equipment" : "Add New Equipment"}
          </h2>
          <button
            onClick={onClose}
            aria-label={t('aria.equipmentFormModal.close', 'Close')}
            className="p-2 text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream rounded-lg"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <form onSubmit={onSubmit} className="p-6 space-y-4 max-h-[70vh] overflow-y-auto">
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label htmlFor="equipment-form-name" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Name *</label>
              <input
                id="equipment-form-name"
                type="text"
                value={formData.name}
                onChange={(e) => set('name', e.target.value)}
                className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                required
              />
            </div>
            <div>
              <label htmlFor="equipment-form-type" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Type *</label>
              <select
                id="equipment-form-type"
                value={formData.equipment_type}
                onChange={(e) => set('equipment_type', e.target.value as EquipmentType)}
                className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                required
              >
                {EQUIPMENT_TYPES.map((type) => (
                  <option key={type} value={type}>{formatEquipmentType(type)}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="equipment-form-condition" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Condition</label>
              <select
                id="equipment-form-condition"
                value={formData.condition}
                onChange={(e) => set('condition', e.target.value as EquipmentCondition)}
                className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
              >
                {EQUIPMENT_CONDITIONS.map((cond) => (
                  <option key={cond} value={cond}>{formatCondition(cond)}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="equipment-form-barcode" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Barcode</label>
              <input
                id="equipment-form-barcode"
                type="text"
                value={formData.barcode}
                onChange={(e) => set('barcode', e.target.value)}
                placeholder={t('placeholder.staffEquipment.autogeneratedIfEmpty')}
                className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream font-mono"
              />
            </div>
            <div>
              <label htmlFor="equipment-form-serial" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Serial Number</label>
              <input
                id="equipment-form-serial"
                type="text"
                value={formData.serial_number}
                onChange={(e) => set('serial_number', e.target.value)}
                className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
              />
            </div>
            <div>
              <label htmlFor="equipment-form-manufacturer" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Manufacturer</label>
              <input
                id="equipment-form-manufacturer"
                type="text"
                value={formData.manufacturer}
                onChange={(e) => set('manufacturer', e.target.value)}
                className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
              />
            </div>
            <div>
              <label htmlFor="equipment-form-model" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Model</label>
              <input
                id="equipment-form-model"
                type="text"
                value={formData.model}
                onChange={(e) => set('model', e.target.value)}
                className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
              />
            </div>
            <div>
              <label htmlFor="equipment-form-location" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Location</label>
              <input
                id="equipment-form-location"
                type="text"
                value={formData.location}
                onChange={(e) => set('location', e.target.value)}
                placeholder={t('placeholder.staffEquipment.egTechDesk')}
                className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
              />
            </div>
            <div>
              <label htmlFor="equipment-form-loan-period" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Loan Period (days)</label>
              <input
                id="equipment-form-loan-period"
                type="number"
                value={formData.loan_period_days}
                onChange={(e) => set('loan_period_days', parseInt(e.target.value) || 14)}
                className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                min={1}
              />
            </div>
            <div>
              <label htmlFor="equipment-form-max-renewals" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Max Renewals</label>
              <input
                id="equipment-form-max-renewals"
                type="number"
                value={formData.max_renewals}
                onChange={(e) => set('max_renewals', parseInt(e.target.value) || 0)}
                className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                min={0}
              />
            </div>
            <div>
              <label htmlFor="equipment-form-deposit-required" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Deposit Required ($)</label>
              <input
                id="equipment-form-deposit-required"
                type="text"
                value={formData.deposit_required}
                onChange={(e) => set('deposit_required', e.target.value)}
                placeholder={t('placeholder.staff.000')}
                className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
              />
            </div>
            <div className="col-span-2">
              <label htmlFor="equipment-form-description" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Description</label>
              <textarea
                id="equipment-form-description"
                value={formData.description}
                onChange={(e) => set('description', e.target.value)}
                rows={2}
                className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream resize-none"
              />
            </div>
            <div className="col-span-2">
              <label htmlFor="equipment-form-accessories" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Included Accessories</label>
              <input
                id="equipment-form-accessories"
                type="text"
                value={formData.included_accessories}
                onChange={(e) => set('included_accessories', e.target.value)}
                placeholder={t('placeholder.staffEquipment.egChargerCaseMouse')}
                className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
              />
            </div>
            <div className="col-span-2">
              <label htmlFor="equipment-form-return-instructions" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Return Instructions</label>
              <textarea
                id="equipment-form-return-instructions"
                value={formData.return_instructions}
                onChange={(e) => set('return_instructions', e.target.value)}
                rows={2}
                placeholder={t('staffEquipment.specialInstructionsForReturningThis')}
                className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream resize-none"
              />
            </div>
            <div className="col-span-2">
              <label htmlFor="equipment-form-notes" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Notes</label>
              <textarea
                id="equipment-form-notes"
                value={formData.notes}
                onChange={(e) => set('notes', e.target.value)}
                rows={2}
                className="w-full px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream resize-none"
              />
            </div>
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
              {editingEquipment ? "Update Equipment" : "Create Equipment"}
            </button>
          </div>
        </form>
      </div>
    </ModalBackdrop>
  )
}
