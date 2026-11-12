/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useMemo, useState } from "react"
import { AlertTriangle, Loader2, ShieldAlert } from "lucide-react"
import type { StaffOverrideCreate, StaffRoom } from "../../../../api/staff-rooms-api"
import { ModalBackdrop } from "@/components/ui/ModalBackdrop"

interface StaffOverrideBookingModalProps {
  rooms: StaffRoom[] | undefined
  onClose: () => void
  onSubmit: (data: StaffOverrideCreate) => void
  isLoading: boolean
}

interface FormState {
  room_id: string
  start_time: string
  end_time: string
  purpose: string
  override_reason: string
  patron_id: string
  contact_name: string
  contact_email: string
  internal_notes: string
}

function defaultStartTime(): string {
  const d = new Date()
  d.setMinutes(0, 0, 0)
  d.setHours(d.getHours() + 1)
  return toLocalInputValue(d)
}

function defaultEndTime(): string {
  const d = new Date()
  d.setMinutes(0, 0, 0)
  d.setHours(d.getHours() + 2)
  return toLocalInputValue(d)
}

function toLocalInputValue(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0")
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export function StaffOverrideBookingModal({
  rooms,
  onClose,
  onSubmit,
  isLoading,
}: StaffOverrideBookingModalProps) {
  const activeRooms = useMemo(
    () => (rooms ?? []).filter((r) => r.is_active),
    [rooms]
  )

  const [form, setForm] = useState<FormState>({
    room_id: "",
    start_time: defaultStartTime(),
    end_time: defaultEndTime(),
    purpose: "",
    override_reason: "",
    patron_id: "",
    contact_name: "",
    contact_email: "",
    internal_notes: "",
  })

  const update = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }))

  const validationError = useMemo(() => {
    if (!form.room_id) return "Select a room"
    if (!form.start_time || !form.end_time) return "Start and end times are required"
    const start = new Date(form.start_time)
    const end = new Date(form.end_time)
    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return "Invalid date/time"
    if (end <= start) return "End time must be after start time"
    if (!form.override_reason.trim()) return "Override reason is required"
    if (form.patron_id && !/^\d+$/.test(form.patron_id)) return "Patron ID must be numeric"
    return null
  }, [form])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (validationError) return

    const payload: StaffOverrideCreate = {
      room_id: parseInt(form.room_id, 10),
      start_time: new Date(form.start_time).toISOString(),
      end_time: new Date(form.end_time).toISOString(),
      purpose: form.purpose.trim() || "Staff override booking",
      override_reason: form.override_reason.trim(),
      ...(form.patron_id ? { patron_id: parseInt(form.patron_id, 10) } : {}),
      ...(form.contact_name.trim() ? { contact_name: form.contact_name.trim() } : {}),
      ...(form.contact_email.trim() ? { contact_email: form.contact_email.trim() } : {}),
      ...(form.internal_notes.trim() ? { internal_notes: form.internal_notes.trim() } : {}),
    }

    onSubmit(payload)
  }

  const inputClass =
    "w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
  const labelClass =
    "block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1"

  return (
    <ModalBackdrop onClose={onClose} title="Create Override Booking" role="alertdialog">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-lsc-border dark:border-earth-700 flex items-start gap-3">
          <div className="p-2 bg-status-warning-100 dark:bg-status-warning-900/30 rounded-lg">
            <ShieldAlert className="w-5 h-5 text-status-warning-700 dark:text-status-warning-400" />
          </div>
          <div>
            <h2 className="text-xl font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
              Create Override Booking
            </h2>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-0.5">
              Bypass availability checks. Conflicting reservations will be cancelled and patrons notified.
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800/50 rounded-lg p-3 flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-status-warning-700 dark:text-status-warning-400 mt-0.5 flex-shrink-0" />
            <p className="text-sm text-status-warning-800 dark:text-status-warning-300">
              This action is logged. Existing reservations during the selected window will be cancelled and the affected patrons notified by email.
            </p>
          </div>

          <div>
            <label htmlFor="override-room" className={labelClass}>
              Room *
            </label>
            <select
              id="override-room"
              value={form.room_id}
              onChange={(e) => update("room_id", e.target.value)}
              required
              className={inputClass}
            >
              <option value="">Select a room…</option>
              {activeRooms.map((room) => (
                <option key={room.id} value={room.id}>
                  {room.name}
                  {room.location ? ` · ${room.location}` : ""}
                  {room.capacity ? ` · cap ${room.capacity}` : ""}
                </option>
              ))}
            </select>
          </div>

          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="override-start" className={labelClass}>
                Start *
              </label>
              <input
                id="override-start"
                type="datetime-local"
                value={form.start_time}
                onChange={(e) => update("start_time", e.target.value)}
                required
                className={inputClass}
              />
            </div>
            <div>
              <label htmlFor="override-end" className={labelClass}>
                End *
              </label>
              <input
                id="override-end"
                type="datetime-local"
                value={form.end_time}
                onChange={(e) => update("end_time", e.target.value)}
                required
                className={inputClass}
              />
            </div>
          </div>

          <div>
            <label htmlFor="override-reason" className={labelClass}>
              Override Reason *
            </label>
            <textarea
              id="override-reason"
              value={form.override_reason}
              onChange={(e) => update("override_reason", e.target.value)}
              required
              rows={2}
              maxLength={500}
              placeholder="e.g. Emergency board meeting, replacing displaced storytime"
              className={inputClass}
            />
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-1">
              Recorded on the reservation and used in cancellation notices to displaced patrons.
            </p>
          </div>

          <div>
            <label htmlFor="override-purpose" className={labelClass}>
              Purpose
            </label>
            <input
              id="override-purpose"
              type="text"
              value={form.purpose}
              onChange={(e) => update("purpose", e.target.value)}
              maxLength={500}
              placeholder="What the room is being used for"
              className={inputClass}
            />
          </div>

          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label htmlFor="override-patron-id" className={labelClass}>
                Patron ID
              </label>
              <input
                id="override-patron-id"
                type="text"
                inputMode="numeric"
                value={form.patron_id}
                onChange={(e) => update("patron_id", e.target.value)}
                placeholder="Optional"
                className={inputClass}
              />
            </div>
            <div>
              <label htmlFor="override-contact-name" className={labelClass}>
                Contact Name
              </label>
              <input
                id="override-contact-name"
                type="text"
                value={form.contact_name}
                onChange={(e) => update("contact_name", e.target.value)}
                maxLength={255}
                className={inputClass}
              />
            </div>
            <div>
              <label htmlFor="override-contact-email" className={labelClass}>
                Contact Email
              </label>
              <input
                id="override-contact-email"
                type="email"
                value={form.contact_email}
                onChange={(e) => update("contact_email", e.target.value)}
                maxLength={255}
                className={inputClass}
              />
            </div>
          </div>

          <div>
            <label htmlFor="override-internal-notes" className={labelClass}>
              Internal Notes
            </label>
            <textarea
              id="override-internal-notes"
              value={form.internal_notes}
              onChange={(e) => update("internal_notes", e.target.value)}
              rows={2}
              placeholder="Visible to staff only"
              className={inputClass}
            />
          </div>

          {validationError && (
            <p role="alert" className="text-sm text-status-danger-600 dark:text-status-danger-400">
              {validationError}
            </p>
          )}

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
              disabled={isLoading || !!validationError}
              className="flex items-center gap-2 px-4 py-2 bg-status-warning-700 hover:bg-status-warning-800 text-white rounded-lg disabled:opacity-50"
            >
              {isLoading && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
              <ShieldAlert className="w-4 h-4" />
              Create Override
            </button>
          </div>
        </form>
      </div>
    </ModalBackdrop>
  )
}
