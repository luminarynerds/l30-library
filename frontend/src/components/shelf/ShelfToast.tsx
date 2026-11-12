/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable react-refresh/only-export-components */
import { useState } from 'react'
import toast from 'react-hot-toast'
import { Bookmark } from 'lucide-react'
import ShelfStatusPicker from './ShelfStatusPicker'
import type { ShelfStatus } from '@/api/domains/content/reading-status-api'

const STATUS_LABELS: Record<ShelfStatus, string> = {
  want_to_read: 'Want to Read',
  currently_reading: 'Currently Reading',
  on_hold: 'On Hold',
  finished: 'Finished',
  did_not_finish: 'Did Not Finish',
}

interface ShelfToastOptions {
  status: ShelfStatus
  onUndo: () => void
  onChange: (newStatus: ShelfStatus) => void
}

export function showShelfToast({ status, onUndo, onChange }: ShelfToastOptions) {
  toast.custom(
    (t) => (
      <ShelfToastContent
        toastId={t.id}
        visible={t.visible}
        status={status}
        onUndo={() => { onUndo(); toast.dismiss(t.id) }}
        onChange={(s) => { onChange(s); toast.dismiss(t.id) }}
      />
    ),
    { duration: 4000 },
  )
}

function ShelfToastContent({
  visible,
  status,
  onUndo,
  onChange,
}: {
  toastId: string
  visible: boolean
  status: ShelfStatus
  onUndo: () => void
  onChange: (s: ShelfStatus) => void
}) {
  const [showPicker, setShowPicker] = useState(false)

  return (
    <div
      role="status"
      aria-live="polite"
      className={`${
        visible ? 'animate-enter' : 'animate-leave'
      } max-w-sm w-full bg-lsc-white dark:bg-earth-800 shadow-lg rounded-xl pointer-events-auto flex items-center gap-3 px-4 py-3 border border-lsc-border dark:border-earth-700`}
    >
      <Bookmark className="w-4 h-4 text-lsc-rose flex-shrink-0" aria-hidden="true" />
      <span className="flex-1 text-sm text-lsc-dark dark:text-lsc-cream">
        Added to {STATUS_LABELS[status]}
      </span>
      <div className="flex items-center gap-2 flex-shrink-0 relative">
        <button
          onClick={() => setShowPicker(true)}
          className="text-xs font-semibold text-lsc-rose dark:text-lsc-rose-light hover:underline"
        >
          Change
        </button>
        <span className="text-lsc-border dark:text-earth-600" aria-hidden="true">·</span>
        <button
          onClick={onUndo}
          className="text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-dark dark:hover:text-lsc-cream"
        >
          Undo
        </button>
        {showPicker && (
          <ShelfStatusPicker
            currentStatus={status}
            onSelect={onChange}
            onClose={() => setShowPicker(false)}
          />
        )}
      </div>
    </div>
  )
}
