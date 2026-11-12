/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Staff-side modal for checking a child out of a childcare session.
 *
 * Shows the parent-authorized pickup list as a radio group. Submit POSTs to
 * /parent-onboarding/childcare/registrations/{id}/checkout, which validates
 * the chosen entry server-side. If no entry is on file (legacy registration)
 * or staff is overriding, the modal collects a free-text pickup name + phone
 * and requires a non-empty `staff_override_reason`.
 */
import { useId, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { X } from 'lucide-react'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import {
  checkoutChildcareRegistration,
  type AuthorizedPickupEntry,
  type ChildcareRegistration,
} from '@/api/parent-onboarding-api'

interface Props {
  registration: ChildcareRegistration
  open: boolean
  onClose: () => void
  onCheckedOut?: (reg: ChildcareRegistration) => void
}

export default function StaffChildcareCheckoutModal({
  registration,
  open,
  onClose,
  onCheckedOut,
}: Props) {
  const queryClient = useQueryClient()
  const nameInputId = useId()
  const phoneInputId = useId()
  const reasonInputId = useId()

  const authorized: AuthorizedPickupEntry[] = registration.authorized_pickup ?? []
  const hasList = authorized.length > 0

  // When the parent has set up a list, the user picks an entry by index.
  // When the list is empty (legacy registration), they must enter free-text
  // name + phone AND provide an override reason.
  const [selectedIdx, setSelectedIdx] = useState<number | null>(
    hasList ? 0 : null,
  )
  const [overrideName, setOverrideName] = useState('')
  const [overridePhone, setOverridePhone] = useState('')
  const [overrideReason, setOverrideReason] = useState('')
  const [error, setError] = useState<string | null>(null)

  const usingOverride = !hasList || selectedIdx === -1

  const mutation = useMutation({
    mutationFn: async () => {
      let name = overrideName
      let phone = overridePhone
      if (!usingOverride && selectedIdx !== null) {
        const e = authorized[selectedIdx]
        if (e) {
          name = e.name
          phone = e.phone
        }
      }
      return checkoutChildcareRegistration(registration.id, {
        picked_up_by_name: name,
        picked_up_by_phone: phone,
        staff_override_reason: usingOverride ? overrideReason : undefined,
      })
    },
    onSuccess: (reg) => {
      toast.success(`Checked out ${reg.child_name}`)
      queryClient.invalidateQueries({ queryKey: ['childcare-roster', registration.session_id] })
      onCheckedOut?.(reg)
      onClose()
    },
    onError: (err: unknown) => {
      // Error shape from FastAPI HTTPException(detail={...}); fall back to a string
      const e = err as { response?: { data?: { detail?: unknown } }; message?: string }
      const detail = e?.response?.data?.detail
      if (typeof detail === 'object' && detail && 'message' in detail) {
        setError(String((detail as { message: unknown }).message))
      } else if (typeof detail === 'string') {
        setError(detail)
      } else {
        setError(e?.message ?? 'Checkout failed')
      }
    },
  })

  if (!open) return null

  const canSubmit = usingOverride
    ? overrideName.trim().length > 0 &&
      overridePhone.trim().length >= 7 &&
      overrideReason.trim().length >= 3
    : selectedIdx !== null && selectedIdx >= 0

  return (
    <ModalBackdrop onClose={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label={`Check out ${registration.child_name}`}
        className="bg-white dark:bg-earth-900 rounded-lg p-6 max-w-md w-full"
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">
            Check out {registration.child_name}
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="p-1"
          >
            <X aria-hidden className="h-4 w-4" />
          </button>
        </div>

        {hasList ? (
          <fieldset className="mb-3">
            <legend className="text-sm font-medium mb-2">
              Who is picking up?
            </legend>
            {authorized.map((entry, idx) => (
              <label key={idx} className="flex items-start gap-2 py-1 cursor-pointer">
                <input
                  type="radio"
                  name="pickup-choice"
                  value={idx}
                  checked={selectedIdx === idx}
                  onChange={() => setSelectedIdx(idx)}
                />
                <span>
                  <strong>{entry.name}</strong>{' '}
                  <span className="text-sm text-earth-700 dark:text-earth-300">
                    ({entry.relationship}) -- {entry.phone}
                    {entry.id_required ? ' -- ID required' : ''}
                  </span>
                </span>
              </label>
            ))}
            <label className="flex items-start gap-2 py-1 cursor-pointer">
              <input
                type="radio"
                name="pickup-choice"
                value={-1}
                checked={selectedIdx === -1}
                onChange={() => setSelectedIdx(-1)}
              />
              <span>Not on the list (staff override)</span>
            </label>
          </fieldset>
        ) : (
          <p className="text-sm mb-3">
            This registration has no authorized pickup list on file. Record
            the pickup details and a reason below.
          </p>
        )}

        {usingOverride && (
          <div className="space-y-2 mb-3">
            <div>
              <label htmlFor={nameInputId} className="block text-sm font-medium">
                Pickup name
              </label>
              <input
                id={nameInputId}
                type="text"
                value={overrideName}
                onChange={(e) => setOverrideName(e.target.value)}
                className="w-full rounded border px-2 py-1 dark:bg-earth-800"
              />
            </div>
            <div>
              <label htmlFor={phoneInputId} className="block text-sm font-medium">
                Pickup phone
              </label>
              <input
                id={phoneInputId}
                type="tel"
                value={overridePhone}
                onChange={(e) => setOverridePhone(e.target.value)}
                className="w-full rounded border px-2 py-1 dark:bg-earth-800"
              />
            </div>
            <div>
              <label htmlFor={reasonInputId} className="block text-sm font-medium">
                Override reason (required)
              </label>
              <textarea
                id={reasonInputId}
                value={overrideReason}
                onChange={(e) => setOverrideReason(e.target.value)}
                rows={2}
                className="w-full rounded border px-2 py-1 dark:bg-earth-800"
              />
            </div>
          </div>
        )}

        {error && (
          <p role="alert" className="text-sm text-status-danger-700 mb-2">
            {error}
          </p>
        )}

        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1 rounded border"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => {
              setError(null)
              mutation.mutate()
            }}
            disabled={!canSubmit || mutation.isPending}
            className="px-3 py-1 rounded bg-lsc-rose text-white disabled:opacity-50"
          >
            {mutation.isPending ? 'Checking out...' : 'Check out'}
          </button>
        </div>
      </div>
    </ModalBackdrop>
  )
}
