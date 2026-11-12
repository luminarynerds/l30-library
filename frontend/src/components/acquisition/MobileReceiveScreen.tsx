/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useRef, useMemo } from "react"
import { X, Plus, Minus, CheckCircle2, Loader2 } from "lucide-react"
import toast from "react-hot-toast"
import { fetchApi } from "@/api/fetchApi"

// Local widened item shape — the shared PurchaseOrderItem interface omits
// `received_quantity`, but the backend payload includes it. Mirroring the
// `as any` pattern in ReceivingTab to avoid polluting the shared type.
interface POItem {
  id: number
  title: string
  author: string | null
  isbn: string | null
  quantity: number
  unit_price: number
  received_quantity: number
  notes: string | null
}

interface PurchaseOrder {
  id: number
  po_number: string
  vendor_name: string | null
  fund_name: string | null
  total_items: number
  total_amount: number
  items: POItem[]
}

interface MobileReceiveScreenProps {
  po: PurchaseOrder
  token: string
  onClose: () => void
  onSuccess: () => void
}

function normalizeBarcode(raw: string): string {
  return raw.replace(/[\s-]/g, "").trim()
}

export default function MobileReceiveScreen({ po, token, onClose, onSuccess }: MobileReceiveScreenProps) {
  // `baseline` is the "already received" floor per line item -- starts at
  // `po.items[i].received_quantity` and advances after a successful Save & continue.
  // We track this locally instead of mutating the `po` prop (which is held in
  // parent state).
  const [baseline, setBaseline] = useState<Record<number, number>>({})
  const [receivedQuantities, setReceivedQuantities] = useState<Record<number, number>>({})
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [barcodeInput, setBarcodeInput] = useState("")
  const [announcement, setAnnouncement] = useState("")
  const [flashItemId, setFlashItemId] = useState<number | null>(null)
  const barcodeRef = useRef<HTMLInputElement | null>(null)
  const flashTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Initialize baseline + working quantities from the PO payload
  useEffect(() => {
    const initial: Record<number, number> = {}
    po.items.forEach((item) => {
      initial[item.id] = item.received_quantity
    })
    setBaseline(initial)
    setReceivedQuantities(initial)
  }, [po])

  // Autofocus barcode input on mount and after submit-and-continue
  useEffect(() => {
    barcodeRef.current?.focus()
  }, [])

  // Clear the flash highlight timer on unmount
  useEffect(() => {
    return () => {
      if (flashTimerRef.current) clearTimeout(flashTimerRef.current)
    }
  }, [])

  const setQuantity = (itemId: number, next: number) => {
    const item = po.items.find((i) => i.id === itemId)
    if (!item) return
    const clamped = Math.max(0, Math.min(next, item.quantity))
    setReceivedQuantities((prev) => ({ ...prev, [itemId]: clamped }))
  }

  const flash = (itemId: number) => {
    setFlashItemId(itemId)
    if (flashTimerRef.current) clearTimeout(flashTimerRef.current)
    flashTimerRef.current = setTimeout(() => setFlashItemId(null), 800)
  }

  const handleBarcodeSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const code = normalizeBarcode(barcodeInput)
    if (!code) return

    // Match against POItem.isbn (EAN-13 scans on books == ISBN-13).
    // If duplicate ISBNs exist across line items, increment the first match.
    const match = po.items.find((item) => {
      const itemIsbn = (item.isbn ?? "").replace(/[\s-]/g, "").trim()
      return itemIsbn && itemIsbn === code
    })

    if (!match) {
      toast.error("No matching line item.")
      setAnnouncement(`No matching line item for ${code}`)
      setBarcodeInput("")
      barcodeRef.current?.focus()
      return
    }

    const current = receivedQuantities[match.id] ?? baseline[match.id] ?? match.received_quantity
    if (current >= match.quantity) {
      toast(`${match.title}: already at ordered quantity (${match.quantity}).`)
      setAnnouncement(`${match.title}, already at full ordered quantity of ${match.quantity}`)
      setBarcodeInput("")
      barcodeRef.current?.focus()
      return
    }

    const next = Math.min(current + 1, match.quantity)
    setQuantity(match.id, next)
    flash(match.id)
    setAnnouncement(`${match.title}, received ${next} of ${match.quantity}`)
    setBarcodeInput("")
    barcodeRef.current?.focus()
  }

  const handleMarkFull = (item: POItem) => {
    setQuantity(item.id, item.quantity)
    flash(item.id)
    setAnnouncement(`${item.title}, marked received in full at ${item.quantity}`)
  }

  const anyChanges = useMemo(
    () => po.items.some((item) => {
      const base = baseline[item.id] ?? item.received_quantity
      const current = receivedQuantities[item.id] ?? base
      return current > base
    }),
    [po.items, receivedQuantities, baseline]
  )

  const doSubmit = async (): Promise<boolean> => {
    if (!token) return false

    // Submit shape mirrors ReceiveItemsModal: `received_quantity` is the new
    // total (not a delta). Only items whose total increased over the
    // already-saved baseline are included.
    const items = po.items
      .filter((item) => {
        const base = baseline[item.id] ?? item.received_quantity
        const current = receivedQuantities[item.id] ?? base
        return current > base
      })
      .map((item) => {
        const base = baseline[item.id] ?? item.received_quantity
        return {
          item_id: item.id,
          received_quantity: receivedQuantities[item.id] ?? base,
        }
      })

    if (items.length === 0) {
      toast.error("No items to receive yet.")
      return false
    }

    setIsSubmitting(true)
    try {
      await fetchApi(`/acquisition/purchase-orders/${po.id}/receive`, {
        method: "PATCH",
        body: JSON.stringify({ items }),
      })
      toast.success("Items received.")
      return true
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to receive items.")
      return false
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleSaveAndClose = async () => {
    const ok = await doSubmit()
    if (ok) {
      onSuccess()
      onClose()
    }
  }

  const handleSaveAndContinue = async () => {
    const ok = await doSubmit()
    if (ok) {
      // Advance the local baseline to what we just submitted so further
      // [+]/[-] and scans build on the new total. Don't mutate the `po`
      // prop -- the parent owns that state.
      const newBaseline: Record<number, number> = {}
      po.items.forEach((item) => {
        newBaseline[item.id] = receivedQuantities[item.id] ?? baseline[item.id] ?? item.received_quantity
      })
      setBaseline(newBaseline)
      setReceivedQuantities(newBaseline)
      setBarcodeInput("")
      onSuccess()
      barcodeRef.current?.focus()
      setAnnouncement("Saved. Continue receiving.")
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 bg-lsc-cream dark:bg-earth-900 flex flex-col"
      role="dialog"
      aria-modal="true"
      aria-labelledby="mobile-receive-heading"
    >
      {/* Screen reader live region for barcode matches */}
      <div role="status" aria-live="polite" aria-atomic="true" className="sr-only">
        {announcement}
      </div>

      {/* Top bar */}
      <header className="flex items-start justify-between gap-3 px-4 py-3 bg-lsc-white dark:bg-earth-800 border-b border-lsc-border dark:border-earth-700">
        <div className="min-w-0 flex-1">
          <h1
            id="mobile-receive-heading"
            className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream truncate"
          >
            {po.po_number}
          </h1>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 truncate">
            {po.vendor_name || "No vendor"}
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="inline-flex items-center justify-center gap-2 min-w-[44px] min-h-[44px] px-3 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2 dark:focus:ring-offset-earth-900"
          aria-label="Cancel and close receive screen"
        >
          <X aria-hidden="true" className="w-5 h-5" />
          <span className="font-medium">Cancel</span>
        </button>
      </header>

      {/* Barcode input */}
      <form onSubmit={handleBarcodeSubmit} className="px-4 py-3 bg-lsc-white dark:bg-earth-800 border-b border-lsc-border dark:border-earth-700">
        <label htmlFor="mobile-receive-barcode" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
          Scan or type barcode
        </label>
        <input
          id="mobile-receive-barcode"
          ref={barcodeRef}
          type="text"
          inputMode="numeric"
          autoComplete="off"
          autoFocus
          value={barcodeInput}
          onChange={(e) => setBarcodeInput(e.target.value)}
          placeholder="Scan ISBN/barcode, then ENTER"
          className="w-full min-h-[48px] px-4 py-3 text-lg border-2 border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
          aria-describedby="mobile-receive-barcode-hint"
        />
        <p id="mobile-receive-barcode-hint" className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
          USB scanner or keyboard. Press ENTER to increment received quantity.
        </p>
      </form>

      {/* Line items */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3 pb-[120px]">
        {po.items.length === 0 && (
          <p className="text-center text-lsc-dark/70 dark:text-lsc-cream/70 py-8">
            No line items on this order.
          </p>
        )}
        {po.items.map((item) => {
          const base = baseline[item.id] ?? item.received_quantity
          const received = receivedQuantities[item.id] ?? base
          const isFull = received >= item.quantity
          const isFlash = flashItemId === item.id
          return (
            <article
              key={item.id}
              className={`bg-lsc-white dark:bg-earth-800 border-2 rounded-xl p-4 shadow-sm transition-colors ${
                isFlash
                  ? "border-status-success-500 motion-safe:animate-pulse"
                  : isFull
                  ? "border-status-success-300 dark:border-status-success-700"
                  : "border-lsc-border dark:border-earth-700"
              }`}
              aria-label={`Line item: ${item.title}`}
            >
              <div className="mb-3">
                <h2 className="font-serif text-base font-semibold text-lsc-dark dark:text-lsc-cream">
                  {item.title}
                </h2>
                {item.author && (
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{item.author}</p>
                )}
                {item.isbn && (
                  <p className="text-xs font-mono text-lsc-dark/60 dark:text-lsc-cream/60">{item.isbn}</p>
                )}
              </div>

              <div className="grid grid-cols-2 gap-3 mb-3">
                <div>
                  <p className="text-xs uppercase tracking-wide text-lsc-dark/60 dark:text-lsc-cream/60">Ordered</p>
                  <p className="text-3xl font-semibold text-lsc-dark dark:text-lsc-cream tabular-nums">
                    {item.quantity}
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-lsc-dark/60 dark:text-lsc-cream/60">Received</p>
                  <p
                    className={`text-3xl font-semibold tabular-nums ${
                      isFull ? "text-status-success-600 dark:text-status-success-400" : "text-lsc-rose"
                    }`}
                    aria-live="off"
                  >
                    {received}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setQuantity(item.id, received - 1)}
                  disabled={received <= base}
                  className="inline-flex items-center justify-center w-[44px] h-[44px] rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 disabled:opacity-40 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                  aria-label={`Decrease received quantity for ${item.title}`}
                >
                  <Minus aria-hidden="true" className="w-5 h-5" />
                </button>
                <button
                  type="button"
                  onClick={() => setQuantity(item.id, received + 1)}
                  disabled={isFull}
                  className="inline-flex items-center justify-center w-[44px] h-[44px] rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 disabled:opacity-40 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                  aria-label={`Increase received quantity for ${item.title}`}
                >
                  <Plus aria-hidden="true" className="w-5 h-5" />
                </button>
                <button
                  type="button"
                  onClick={() => handleMarkFull(item)}
                  disabled={isFull}
                  className="flex-1 inline-flex items-center justify-center gap-2 min-h-[44px] px-3 py-2 rounded-lg bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-lsc-dark/30 disabled:cursor-not-allowed text-white font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2 dark:focus:ring-offset-earth-800"
                >
                  <CheckCircle2 aria-hidden="true" className="w-4 h-4" />
                  Mark received in full
                </button>
              </div>
            </article>
          )
        })}
      </div>

      {/* Sticky bottom action bar */}
      <footer className="fixed bottom-0 inset-x-0 bg-lsc-white dark:bg-earth-800 border-t border-lsc-border dark:border-earth-700 px-4 py-3 flex items-center gap-3 shadow-[0_-4px_12px_rgba(0,0,0,0.08)]">
        <button
          type="button"
          onClick={handleSaveAndContinue}
          disabled={!anyChanges || isSubmitting}
          className="flex-1 inline-flex items-center justify-center gap-2 min-h-[56px] px-4 py-3 rounded-xl border-2 border-lsc-rose text-lsc-rose font-semibold hover:bg-lsc-rose/10 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2 dark:focus:ring-offset-earth-800"
        >
          {isSubmitting ? (
            <Loader2 aria-hidden="true" className="w-5 h-5 motion-safe:animate-spin" />
          ) : null}
          Save & continue
        </button>
        <button
          type="button"
          onClick={handleSaveAndClose}
          disabled={!anyChanges || isSubmitting}
          className="flex-1 inline-flex items-center justify-center gap-2 min-h-[56px] px-4 py-3 rounded-xl bg-status-success-600 hover:bg-status-success-700 disabled:bg-lsc-dark/40 disabled:cursor-not-allowed text-white font-semibold focus:outline-none focus:ring-2 focus:ring-status-success-600 focus:ring-offset-2 dark:focus:ring-offset-earth-800"
        >
          {isSubmitting ? (
            <Loader2 aria-hidden="true" className="w-5 h-5 motion-safe:animate-spin" />
          ) : (
            <CheckCircle2 aria-hidden="true" className="w-5 h-5" />
          )}
          Save &amp; close
        </button>
      </footer>
    </div>
  )
}
