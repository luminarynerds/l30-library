/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useId, useRef, useState } from "react"
import { Modal } from "@/components/ui/Modal"

export interface ImageAltModalProps {
  isOpen: boolean
  imageUrl: string
  /** Initial alt text suggestion (e.g. derived from filename). */
  initialAlt?: string
  onConfirm: (result: { alt: string; decorative: boolean }) => void
  onCancel: () => void
}

export default function ImageAltModal({
  isOpen,
  imageUrl,
  initialAlt = "",
  onConfirm,
  onCancel,
}: ImageAltModalProps): React.ReactElement | null {
  // State is seeded from props at mount. The parent component keys the modal
  // (renders only when there's a pending image), so each open is a fresh mount.
  const [alt, setAlt] = useState(initialAlt)
  const [decorative, setDecorative] = useState(false)
  const [touched, setTouched] = useState(false)
  const altInputRef = useRef<HTMLInputElement>(null)
  const altId = useId()
  const decorativeId = useId()
  const helpId = useId()
  const errId = useId()

  // Move keyboard focus into the alt input after the modal mounts so screen
  // reader users land on the editable description immediately.
  useEffect(() => {
    if (!isOpen) return
    const t = setTimeout(() => altInputRef.current?.focus(), 50)
    return () => clearTimeout(t)
  }, [isOpen])

  if (!isOpen) return null

  const trimmedAlt = alt.trim()
  const altRequiredButMissing = !decorative && trimmedAlt.length === 0
  const showError = altRequiredButMissing && touched

  const submit = () => {
    setTouched(true)
    if (altRequiredButMissing) {
      altInputRef.current?.focus()
      return
    }
    onConfirm({
      alt: decorative ? "" : trimmedAlt,
      decorative,
    })
  }

  const handleAltKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault()
      submit()
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onCancel}
      title="Image alt text"
      size="md"
      footer={
        <div className="flex justify-end gap-3 w-full">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 text-sm rounded-xl border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 focus:outline-none focus:ring-2 focus:ring-lsc-rose"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={submit}
            disabled={altRequiredButMissing}
            className="px-4 py-2 text-sm rounded-xl bg-lsc-rose text-white font-medium hover:bg-lsc-rose/90 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-lsc-rose"
          >
            Insert image
          </button>
        </div>
      }
    >
      <div className="space-y-4">
        <div className="rounded-lg overflow-hidden border border-lsc-border dark:border-earth-700 bg-lsc-cream/40 dark:bg-earth-900/40 flex items-center justify-center max-h-48">
          {/* Preview deliberately uses empty alt -- the modal IS the description UI */}
          <img
            src={imageUrl}
            alt=""
            role="presentation"
            className="max-h-48 max-w-full object-contain"
          />
        </div>

        <div>
          <label
            htmlFor={altId}
            className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream"
          >
            Alt text {!decorative && <span aria-hidden="true" className="text-status-danger-600">*</span>}
            {!decorative && <span className="sr-only">(required)</span>}
          </label>
          <p id={helpId} className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-1">
            Describe what the image shows for screen reader users and when the image fails to load.
          </p>
          <input
            ref={altInputRef}
            id={altId}
            type="text"
            value={alt}
            onChange={(e) => setAlt(e.target.value)}
            onBlur={() => setTouched(true)}
            onKeyDown={handleAltKeyDown}
            disabled={decorative}
            required={!decorative}
            aria-required={!decorative}
            aria-invalid={showError}
            aria-describedby={`${helpId}${showError ? ` ${errId}` : ""}`}
            className="mt-2 w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-lsc-rose"
            placeholder={decorative ? "(decorative -- no description needed)" : "e.g. Children reading at the library"}
          />
          {showError && (
            <p id={errId} role="alert" className="mt-1 text-xs text-status-danger-700">
              Alt text is required. Toggle "Decorative image" if this image is purely decorative.
            </p>
          )}
        </div>

        <div className="flex items-start gap-3 pt-2 border-t border-lsc-border dark:border-earth-700">
          <input
            id={decorativeId}
            type="checkbox"
            checked={decorative}
            onChange={(e) => setDecorative(e.target.checked)}
            className="mt-1 h-4 w-4 rounded border-lsc-border dark:border-earth-700 text-lsc-rose focus:ring-lsc-rose"
          />
          <div className="flex-1">
            <label
              htmlFor={decorativeId}
              className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream cursor-pointer"
            >
              Decorative image
            </label>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-0.5">
              The image is purely decorative and adds no information. Screen readers will skip it.
            </p>
          </div>
        </div>
      </div>
    </Modal>
  )
}
