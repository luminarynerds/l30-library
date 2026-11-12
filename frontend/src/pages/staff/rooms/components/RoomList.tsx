/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Loader2, Plus, Edit2, XCircle, Check, DoorOpen, Users, MapPin } from "lucide-react"
import type { StaffRoom } from "../../../../api/staff-rooms-api"
import { ROOM_TYPES, AMENITIES } from "../constants"
import { useTranslation } from '@/i18n'

interface RoomListProps {
  rooms: StaffRoom[] | undefined
  isLoading: boolean
  roomTypeFilter: string
  includeInactive: boolean
  onRoomTypeFilterChange: (value: string) => void
  onIncludeInactiveChange: (value: boolean) => void
  onAddRoom: () => void
  onEditRoom: (room: StaffRoom) => void
  onToggleActivation: (room: StaffRoom) => void
  isDeactivating: boolean
  isActivating: boolean
}

export function RoomList({
  rooms,
  isLoading,
  roomTypeFilter,
  includeInactive,
  onRoomTypeFilterChange,
  onIncludeInactiveChange,
  onAddRoom,
  onEditRoom,
  onToggleActivation,
  isDeactivating,
  isActivating,
}: RoomListProps) {
  const { t } = useTranslation()
  return (
    <div className="space-y-4">
      {/* Filters & Actions */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={roomTypeFilter}
            onChange={(e) => onRoomTypeFilterChange(e.target.value)}
            aria-label={t('aria.rooms.filterByRoomType', 'Filter by room type')}
            className="px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-700 text-sm text-lsc-dark dark:text-lsc-cream"
          >
            <option value="">All Room Types</option>
            {ROOM_TYPES.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>

          <label className="flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream">
            <input
              type="checkbox"
              checked={includeInactive}
              onChange={(e) => onIncludeInactiveChange(e.target.checked)}
              className="w-4 h-4 rounded border-lsc-border text-lsc-rose focus:ring-lsc-rose"
            />
            Show Inactive
          </label>
        </div>

        <button
          onClick={onAddRoom}
          className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg text-sm"
        >
          <Plus className="w-4 h-4" /> Add Room
        </button>
      </div>

      {/* Content */}
      <div role="status" aria-live="polite" className="sr-only">
        {isLoading
          ? t('status.rooms.loading', 'Loading rooms…')
          : !rooms || rooms.length === 0
          ? t('status.rooms.empty', 'No rooms found')
          : t('status.rooms.count', { count: rooms.length })}
      </div>
      <div>
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" aria-hidden="true" />
        </div>
      ) : !rooms || rooms.length === 0 ? (
        <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
          <DoorOpen className="w-12 h-12 mx-auto mb-3 opacity-50" aria-hidden="true" />
          <p>No rooms found</p>
          <button
            onClick={onAddRoom}
            className="mt-3 text-lsc-rose hover:underline"
          >
            Add your first room
          </button>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {rooms.map((room) => (
            <div
              key={room.id}
              className={`bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border transition-colors ${
                room.is_active
                  ? "border-lsc-border dark:border-earth-700"
                  : "border-status-danger-200 dark:border-status-danger-900/50 bg-status-danger-50/50 dark:bg-status-danger-900/10"
              }`}
            >
              <div className="flex justify-between items-start mb-2">
                <div>
                  <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                    {room.name}
                  </h3>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    {ROOM_TYPES.find((t) => t.value === room.room_type)?.label || room.room_type}
                  </p>
                </div>
                <span
                  className={`px-2 py-0.5 rounded text-xs font-medium ${
                    room.is_active
                      ? "bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400"
                      : "bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400"
                  }`}
                >
                  {room.is_active ? "Active" : "Inactive"}
                </span>
              </div>

              {room.description && (
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60 mb-2 line-clamp-2" title={room.description}>
                  {room.description}
                </p>
              )}

              <div className="space-y-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                <div className="flex items-center gap-2">
                  <Users className="w-4 h-4" />
                  <span>Capacity: {room.capacity}</span>
                </div>
                {room.location && (
                  <div className="flex items-center gap-2">
                    <MapPin className="w-4 h-4" />
                    <span>{room.location}</span>
                  </div>
                )}
                {room.building && (
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                    {room.building}{room.floor ? ` - ${room.floor}` : ""}
                  </p>
                )}
              </div>

              {room.amenities && room.amenities.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-3">
                  {room.amenities.slice(0, 3).map((amenityId) => {
                    const amenity = AMENITIES.find((a) => a.id === amenityId)
                    if (!amenity) return null
                    const Icon = amenity.icon
                    return (
                      <span
                        key={amenityId}
                        className="flex items-center gap-1 px-2 py-0.5 bg-lsc-cream dark:bg-earth-700 rounded text-xs text-lsc-dark/70 dark:text-lsc-cream/70"
                      >
                        <Icon className="w-3 h-3" />
                        {amenity.label}
                      </span>
                    )
                  })}
                  {room.amenities.length > 3 && (
                    <span className="px-2 py-0.5 bg-lsc-cream dark:bg-earth-700 rounded text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                      +{room.amenities.length - 3} more
                    </span>
                  )}
                </div>
              )}

              <div className="flex items-center gap-2 mt-3 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                {room.requires_approval && (
                  <span className="px-2 py-0.5 bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-400 rounded">
                    Requires Approval
                  </span>
                )}
                {room.max_booking_hours && (
                  <span>Max {room.max_booking_hours}h</span>
                )}
              </div>

              <div className="flex gap-2 mt-4 pt-3 border-t border-lsc-border dark:border-earth-700">
                <button
                  onClick={() => onEditRoom(room)}
                  className="flex items-center gap-1 px-2 py-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded"
                >
                  <Edit2 className="w-3 h-3" /> Edit
                </button>
                {room.is_active ? (
                  <button
                    onClick={() => onToggleActivation(room)}
                    disabled={isDeactivating}
                    className="flex items-center gap-1 px-2 py-1 text-sm text-status-danger-600 dark:text-status-danger-400 hover:bg-status-danger-50 dark:hover:bg-status-danger-900/20 rounded"
                  >
                    <XCircle className="w-3 h-3" /> Deactivate
                  </button>
                ) : (
                  <button
                    onClick={() => onToggleActivation(room)}
                    disabled={isActivating}
                    className="flex items-center gap-1 px-2 py-1 text-sm text-status-success-600 dark:text-status-success-400 hover:bg-status-success-50 dark:hover:bg-status-success-900/20 rounded"
                  >
                    <Check className="w-3 h-3" /> Activate
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
      </div>
    </div>
  )
}
