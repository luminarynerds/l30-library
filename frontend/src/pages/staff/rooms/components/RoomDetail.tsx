/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from "react"
import { Loader2 } from "lucide-react"
import type { StaffRoom, StaffRoomCreate, StaffRoomUpdate } from "../../../../api/staff-rooms-api"
import { ROOM_TYPES, AMENITIES } from "../constants"
import { useTranslation} from '@/i18n'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

interface RoomDetailProps {
  room: StaffRoom | null | undefined
  onClose: () => void
  onSave: (data: StaffRoomCreate | StaffRoomUpdate) => void
  isLoading: boolean
}

export function RoomDetail({
  room,
  onClose,
  onSave,
  isLoading,
}: RoomDetailProps) {
  const { t } = useTranslation()
  const [formData, setFormData] = useState<StaffRoomCreate>({
    name: room?.name || "",
    room_type: room?.room_type || "study_room",
    capacity: room?.capacity || 4,
    description: room?.description || "",
    location: room?.location || "",
    floor: room?.floor || "",
    building: room?.building || "",
    amenities: room?.amenities || [],
    photos: room?.photos || [],
    is_active: room?.is_active ?? true,
    requires_approval: room?.requires_approval ?? false,
    max_booking_hours: room?.max_booking_hours || 2,
    advance_booking_days: room?.advance_booking_days || 14,
    min_notice_hours: room?.min_notice_hours || 1,
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSave(formData)
  }

  const toggleAmenity = (amenityId: string) => {
    setFormData(prev => ({
      ...prev,
      amenities: prev.amenities?.includes(amenityId)
        ? prev.amenities.filter(a => a !== amenityId)
        : [...(prev.amenities || []), amenityId]
    }))
  }

  return (
    <ModalBackdrop onClose={onClose} title="Booking Settings">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-lsc-border dark:border-earth-700">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            {room ? "Edit Room" : "Add New Room"}
          </h2>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Basic Info */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="room-name" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Room Name *
              </label>
              <input
                id="room-name"
                type="text"
                value={formData.name}
                onChange={e => setFormData(prev => ({ ...prev, name: e.target.value }))}
                required
                className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                placeholder={t('placeholder.roomDetail.egStudyRoomA')}
              />
            </div>

            <div>
              <label htmlFor="room-type" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Room Type *
              </label>
              <select
                id="room-type"
                value={formData.room_type}
                onChange={e => setFormData(prev => ({ ...prev, room_type: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
              >
                {ROOM_TYPES.map(type => (
                  <option key={type.value} value={type.value}>{type.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="room-capacity" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Capacity *
              </label>
              <input
                id="room-capacity"
                type="number"
                value={formData.capacity}
                onChange={e => setFormData(prev => ({ ...prev, capacity: parseInt(e.target.value) || 1 }))}
                min={1}
                max={500}
                required
                className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
              />
            </div>

            <div>
              <label htmlFor="room-location" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Location
              </label>
              <input
                id="room-location"
                type="text"
                value={formData.location}
                onChange={e => setFormData(prev => ({ ...prev, location: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                placeholder={t('placeholder.roomDetail.egMainFloorWest')}
              />
            </div>

            <div>
              <label htmlFor="room-building" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Building
              </label>
              <input
                id="room-building"
                type="text"
                value={formData.building}
                onChange={e => setFormData(prev => ({ ...prev, building: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                placeholder={t('placeholder.bookDropDetail.egMainLibrary')}
              />
            </div>

            <div>
              <label htmlFor="room-floor" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                Floor
              </label>
              <input
                id="room-floor"
                type="text"
                value={formData.floor}
                onChange={e => setFormData(prev => ({ ...prev, floor: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                placeholder={t('placeholder.roomDetail.eg2ndFloor')}
              />
            </div>
          </div>

          {/* Description */}
          <div>
            <label htmlFor="room-description" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
              Description
            </label>
            <textarea
              id="room-description"
              value={formData.description}
              onChange={e => setFormData(prev => ({ ...prev, description: e.target.value }))}
              rows={3}
              className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
              placeholder={t('roomDetail.describeTheRoomAndIts')}
            />
          </div>

          {/* Amenities */}
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
              Amenities
            </label>
            <div className="flex flex-wrap gap-2">
              {AMENITIES.map(amenity => {
                const Icon = amenity.icon
                const isSelected = formData.amenities?.includes(amenity.id)
                return (
                  <button
                    key={amenity.id}
                    type="button"
                    onClick={() => toggleAmenity(amenity.id)}
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors ${
                      isSelected
                        ? "bg-lsc-rose text-white"
                        : "bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-border dark:hover:bg-earth-600"
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    {amenity.label}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Booking Settings */}
          <div className="border-t border-lsc-border dark:border-earth-700 pt-4">
            <h3 className="font-medium text-lsc-dark dark:text-lsc-cream mb-3">Booking Settings</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  Max Booking Hours
                </label>
                <input
                  type="number"
                  value={formData.max_booking_hours}
                  onChange={e => setFormData(prev => ({ ...prev, max_booking_hours: parseInt(e.target.value) || 2 }))}
                  min={1}
                  max={24}
                  className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  Advance Booking Days
                </label>
                <input
                  type="number"
                  value={formData.advance_booking_days}
                  onChange={e => setFormData(prev => ({ ...prev, advance_booking_days: parseInt(e.target.value) || 14 }))}
                  min={1}
                  max={365}
                  className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                  Min Notice Hours
                </label>
                <input
                  type="number"
                  value={formData.min_notice_hours}
                  onChange={e => setFormData(prev => ({ ...prev, min_notice_hours: parseInt(e.target.value) || 1 }))}
                  min={0}
                  max={168}
                  className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                />
              </div>
            </div>
          </div>

          {/* Toggles */}
          <div className="flex flex-wrap gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.requires_approval}
                onChange={e => setFormData(prev => ({ ...prev, requires_approval: e.target.checked }))}
                className="w-4 h-4 rounded border-lsc-border text-lsc-rose focus:ring-lsc-rose"
              />
              <span className="text-sm text-lsc-dark dark:text-lsc-cream">Requires Staff Approval</span>
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

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-4 border-t border-lsc-border dark:border-earth-700">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg disabled:opacity-50"
            >
              {isLoading && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
              {room ? "Update Room" : "Create Room"}
            </button>
          </div>
        </form>
      </div>
    </ModalBackdrop>
  )
}
