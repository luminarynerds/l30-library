/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from "react"
import { Loader2 } from "lucide-react"
import type { StaffEquipment, StaffEquipmentCreate } from "../../../../api/staff-rooms-api"
import { t } from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface EquipmentModalProps {
  equipment: StaffEquipment | null | undefined
  onClose: () => void
  onSave: (data: StaffEquipmentCreate) => void
  isLoading: boolean
}

export function EquipmentModal({
  equipment,
  onClose,
  onSave,
  isLoading,
}: EquipmentModalProps) {
  const [formData, setFormData] = useState<StaffEquipmentCreate>(() => ({
    name: equipment?.name || "",
    equipment_code: equipment?.equipment_code || "",
    description: equipment?.description || "",
    category: equipment?.category || "",
    ...(equipment?.room_id ? { room_id: equipment.room_id } : {}),
    is_active: equipment?.is_active ?? true,
    requires_checkout: equipment?.requires_checkout ?? false,
  }))

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSave(formData)
  }

  return (
    <ModalBackdrop onClose={onClose} title="Requires Checkout">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-md w-full">
        <div className="p-6 border-b border-lsc-border dark:border-earth-700">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            {equipment ? "Edit Equipment" : "Add Equipment"}
          </h2>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Equipment Name *
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={e => setFormData(prev => ({ ...prev, name: e.target.value }))}
              required
              className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
              placeholder={t('placeholder.staffRooms.egProjectorWhiteboard')}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Equipment Code *
            </label>
            <input
              type="text"
              value={formData.equipment_code}
              onChange={e => setFormData(prev => ({ ...prev, equipment_code: e.target.value }))}
              required
              className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
              placeholder={t('placeholder.staffRooms.egProj001')}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Category
            </label>
            <input
              type="text"
              value={formData.category}
              onChange={e => setFormData(prev => ({ ...prev, category: e.target.value }))}
              className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
              placeholder={t('placeholder.staffRooms.egAvEquipment')}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Description
            </label>
            <textarea
              value={formData.description}
              onChange={e => setFormData(prev => ({ ...prev, description: e.target.value }))}
              rows={2}
              className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
            />
          </div>

          <div className="flex gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.requires_checkout}
                onChange={e => setFormData(prev => ({ ...prev, requires_checkout: e.target.checked }))}
                className="w-4 h-4 rounded border-lsc-border text-lsc-rose focus:ring-lsc-rose"
              />
              <span className="text-sm text-lsc-dark dark:text-lsc-cream">Requires Checkout</span>
            </label>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.is_active}
                onChange={e => setFormData(prev => ({ ...prev, is_active: e.target.checked }))}
                className="w-4 h-4 rounded border-lsc-border text-lsc-rose focus:ring-lsc-rose"
              />
              <span className="text-sm text-lsc-dark dark:text-lsc-cream">Active</span>
            </label>
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg disabled:opacity-50"
            >
              {isLoading && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
              {equipment ? "Update" : "Create"}
            </button>
          </div>
        </form>
      </div>
    </ModalBackdrop>
  )
}
