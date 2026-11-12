/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useMemo } from "react"
import { Package, PackageOpen, Loader2 } from "lucide-react"
import toast from "react-hot-toast"
import StatusBadge from "../../components/acquisition/StatusBadge"
import ReceiveItemsModal from "../../components/acquisition/ReceiveItemsModal"
import MobileReceiveScreen from "../../components/acquisition/MobileReceiveScreen"
import { type Fund, type Vendor, type PurchaseOrder, type PurchaseOrderDetail, apiFetch, formatMoney } from "./types"

// TODO(edi-provenance): Per-ItemCopy "received via EDI" badge.
// ItemCopy doesn't carry an acquired_via_edi column. Deriving it client-side
// would require: (a) fetching every DESADV transaction for the parent PO,
// (b) parsing each DESADV's line items by ISBN, (c) cross-referencing each
// ItemCopy ISBN against the union. That's O(items * desadv-lines) per render
// across all visible POs — not justified without first observing whether the
// signal would change clerk behavior. Revisit with a backend-supplied field
// or a single bulk endpoint if/when staff requests this distinction.

interface ReceivingTabProps {
  token: string
  vendors: Vendor[]
  funds: Fund[]
  orders: PurchaseOrder[]
  loadData: () => void
}

const RECEIVING_STATUSES = new Set(["submitted", "shipped", "partially_received"])
const MOBILE_QUERY = "(max-width: 767px)"

// Some backend payloads include expected_delivery; the list type doesn't declare it
// so we widen here for the card without polluting the shared interface.
interface PurchaseOrderWithDelivery extends PurchaseOrder {
  expected_delivery?: string | null
}

function formatDate(iso: string | null | undefined): string | null {
  if (!iso) return null
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return null
  return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })
}

// Tiny inline media-query hook -- keeps the desktop-vs-tablet branch live on
// resize so DevTools toggling actually flips the experience without close+reopen.
function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState<boolean>(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return false
    return window.matchMedia(query).matches
  })
  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return
    const mql = window.matchMedia(query)
    const handler = (e: MediaQueryListEvent) => setMatches(e.matches)
    // Safari < 14 uses addListener/removeListener; modern uses addEventListener.
    if (typeof mql.addEventListener === "function") {
      mql.addEventListener("change", handler)
      return () => mql.removeEventListener("change", handler)
    }
    mql.addListener(handler)
    return () => mql.removeListener(handler)
  }, [query])
  return matches
}

export default function ReceivingTab(props: ReceivingTabProps) {
  const { token: authToken, orders, loadData } = props
  const [selectedPO, setSelectedPO] = useState<PurchaseOrderDetail | null>(null)
  const [showReceiveModal, setShowReceiveModal] = useState(false)
  const [loadingId, setLoadingId] = useState<number | null>(null)
  const isMobile = useMediaQuery(MOBILE_QUERY)

  const receivable = useMemo(
    () => orders.filter((o) => RECEIVING_STATUSES.has(o.status)),
    [orders]
  )

  const handleOpenReceive = async (po: PurchaseOrder) => {
    if (!authToken) return
    setLoadingId(po.id)
    try {
      const detail = await apiFetch<PurchaseOrderDetail>(authToken, `/purchase-orders/${po.id}`)
      setSelectedPO(detail)
      setShowReceiveModal(true)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to load order details")
    } finally {
      setLoadingId(null)
    }
  }

  if (receivable.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <PackageOpen aria-hidden="true" className="w-12 h-12 text-lsc-dark/40 dark:text-lsc-cream/40 mb-3" />
        <p className="text-lsc-dark/70 dark:text-lsc-cream/70">No purchase orders awaiting receiving.</p>
        <p className="text-sm text-lsc-dark/50 dark:text-lsc-cream/50 mt-1">
          Submitted, shipped, and partially received POs will appear here.
        </p>
      </div>
    )
  }

  return (
    <>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
            Receiving Queue
          </h2>
          <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            {receivable.length} {receivable.length === 1 ? "order" : "orders"} awaiting
          </span>
        </div>

        <ul
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
          role="list"
          aria-label="Purchase orders awaiting receiving"
        >
          {receivable.map((order) => {
            const expected = formatDate((order as PurchaseOrderWithDelivery).expected_delivery)
            const isLoading = loadingId === order.id
            return (
              <li
                key={order.id}
                className="flex flex-col bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between gap-2 mb-3">
                  <h3 className="font-mono text-base font-semibold text-lsc-dark dark:text-lsc-cream break-all">
                    {order.po_number}
                  </h3>
                  <StatusBadge status={order.status} size="sm" />
                </div>

                <dl className="space-y-1.5 text-sm flex-1">
                  <div className="flex justify-between gap-2">
                    <dt className="text-lsc-dark/70 dark:text-lsc-cream/70">Vendor</dt>
                    <dd className="text-right text-lsc-dark dark:text-lsc-cream truncate max-w-[60%]">
                      {order.vendor_name || "-"}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt className="text-lsc-dark/70 dark:text-lsc-cream/70">Fund</dt>
                    <dd className="text-right text-lsc-dark dark:text-lsc-cream truncate max-w-[60%]">
                      {order.fund_name || "-"}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt className="text-lsc-dark/70 dark:text-lsc-cream/70">Items</dt>
                    <dd className="text-right text-lsc-dark dark:text-lsc-cream">
                      {order.total_items}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt className="text-lsc-dark/70 dark:text-lsc-cream/70">Total</dt>
                    <dd className="text-right font-semibold text-lsc-dark dark:text-lsc-cream">
                      {formatMoney(order.total_amount)}
                    </dd>
                  </div>
                  {expected && (
                    <div className="flex justify-between gap-2">
                      <dt className="text-lsc-dark/70 dark:text-lsc-cream/70">Expected by</dt>
                      <dd className="text-right text-lsc-dark dark:text-lsc-cream">{expected}</dd>
                    </div>
                  )}
                </dl>

                <button
                  type="button"
                  onClick={() => handleOpenReceive(order)}
                  disabled={isLoading}
                  className="mt-4 inline-flex items-center justify-center gap-2 w-full min-h-[44px] px-4 py-2.5 bg-lsc-rose hover:bg-lsc-rose/90 disabled:opacity-60 disabled:cursor-not-allowed text-white rounded-xl font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2 dark:focus:ring-offset-earth-800"
                  aria-label={`Receive items for order ${order.po_number}`}
                >
                  {isLoading ? (
                    <Loader2 aria-hidden="true" className="w-4 h-4 motion-safe:animate-spin" />
                  ) : (
                    <Package aria-hidden="true" className="w-4 h-4" />
                  )}
                  Receive items
                </button>
              </li>
            )
          })}
        </ul>
      </div>

      {showReceiveModal && selectedPO && (
        isMobile ? (
          <MobileReceiveScreen
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            po={selectedPO as any}
            token={authToken}
            onClose={() => {
              setShowReceiveModal(false)
              setSelectedPO(null)
            }}
            onSuccess={() => {
              // Refresh data without forcing close -- MobileReceiveScreen
              // controls its own close lifecycle (Save & close vs Save & continue).
              loadData()
            }}
          />
        ) : (
          <ReceiveItemsModal
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            po={selectedPO as any}
            token={authToken}
            onClose={() => {
              setShowReceiveModal(false)
              setSelectedPO(null)
            }}
            onSuccess={() => {
              setShowReceiveModal(false)
              setSelectedPO(null)
              loadData()
            }}
          />
        )
      )}
    </>
  )
}
