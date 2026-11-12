/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState, useRef, useEffect } from "react"
import { X, Barcode, Loader2, AlertCircle } from "lucide-react"
import FocusTrap from "focus-trap-react"
import { PatronContextCard } from "./PatronContextCard"
import { fetchApi } from '@/lib/api-client'
import { useTranslation} from '@/i18n'

interface CardScanModalProps {
  isOpen: boolean
  onClose: () => void
}

export function CardScanModal({ isOpen, onClose }: CardScanModalProps) {
  const { t } = useTranslation()
  const [input, setInput] = useState("")
  const [foundPatronId, setFoundPatronId] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const previousActiveElement = useRef<HTMLElement | null>(null)

  // Store trigger element and restore focus on close
  useEffect(() => {
    if (isOpen) {
      previousActiveElement.current = document.activeElement as HTMLElement
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
      previousActiveElement.current?.focus()
      previousActiveElement.current = null
    }
    return () => {
      document.body.style.overflow = ''
    }
  }, [isOpen])

  // Focus input when modal opens
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isOpen])

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!input.trim()) {
      setError("Please enter a library card number or patron name")
      return
    }

    try {
      setLoading(true)
      setError(null)

      // First try to find by library card number (exact match)
      const data = await fetchApi(`/staff/patrons?search=${encodeURIComponent(input)}&limit=1`)

      if (data.patrons && data.patrons.length > 0) {
        setFoundPatronId(data.patrons[0].id)
      } else {
        setError("Patron not found. Please check the card number or name.")
        setFoundPatronId(null)
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "We couldn't process that card scan. Please try again.")
      setFoundPatronId(null)
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) {
    return null
  }

  return (
    <FocusTrap focusTrapOptions={{ escapeDeactivates: false, allowOutsideClick: true, returnFocusOnDeactivate: false, fallbackFocus: () => document.body }}>
      <div
        className="fixed inset-0 motion-safe:backdrop-blur-md bg-black/50 dark:bg-black/70 z-50 flex items-center justify-center p-4"
        role="presentation"
        onKeyDown={(e) => { if (e.key === "Escape") onClose() }}
      >
      <div
        className="bg-lsc-white dark:bg-earth-800 rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-lg"
        role="dialog"
        aria-modal="true"
        aria-labelledby="card-scan-modal-title"
      >
        {/* Header */}
        <div className="sticky top-0 bg-lsc-white dark:bg-earth-800 border-b border-lsc-border dark:border-earth-700 p-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Barcode className="w-6 h-6 text-lsc-rose" aria-hidden="true" />
            <h2 id="card-scan-modal-title" className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">
              Patron Card Scan
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-lsc-border dark:hover:bg-earth-700 rounded-lg transition-colors"
            aria-label={t('aria.authModals.close')}
          >
            <X className="w-6 h-6" aria-hidden="true" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {!foundPatronId ? (
            <form onSubmit={handleSearch} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                  Library Card Number or Patron Name
                </label>
                <input
                  ref={inputRef}
                  type="text"
                  value={input}
                  onChange={(e) => {
                    setInput(e.target.value)
                    setError(null)
                  }}
                  placeholder={t('components.staff.cardScan.scanCardOrEnterPatron')}
                  className="w-full px-4 py-3 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                  disabled={loading}
                />
              </div>

              {error && (
                <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-lg p-3 flex items-start gap-2">
                  <AlertCircle className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400 mt-0.5 flex-shrink-0" />
                  <p className="text-sm text-status-danger-700 dark:text-status-danger-300">{error}</p>
                </div>
              )}

              <button
                type="submit"
                disabled={loading || !input.trim()}
                className="w-full px-4 py-3 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 transition-colors"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                    Searching...
                  </>
                ) : (
                  <>
                    <Barcode className="w-4 h-4" />
                    Lookup Patron
                  </>
                )}
              </button>

              <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 text-center pt-2">
                💡 Tip: Most barcode scanners automatically submit when done scanning.
              </p>
            </form>
          ) : (
            <div className="space-y-4">
              <PatronContextCard patronId={foundPatronId} />

              <div className="flex gap-3 pt-4 border-t border-lsc-border dark:border-earth-700">
                <button
                  onClick={() => {
                    setFoundPatronId(null)
                    setInput("")
                    setError(null)
                    inputRef.current?.focus()
                  }}
                  className="flex-1 px-4 py-2 border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg font-medium hover:bg-lsc-border dark:hover:bg-earth-700 transition-colors"
                >
                  Scan Another Card
                </button>
                <button
                  onClick={onClose}
                  className="flex-1 px-4 py-2 bg-lsc-rose text-white rounded-lg font-medium hover:bg-lsc-rose transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
      </div>
    </FocusTrap>
  )
}