/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from "react"
import {
  Loader2,
  Users,
  Package,
  DollarSign,
  Clock,
  TrendingUp,
  BarChart3,
  CheckCircle,
  ShoppingCart,
  Calendar,
} from "lucide-react"
import toast from "react-hot-toast"
import { fetchApi } from '@/api/fetchApi'
import { t } from '@/i18n'
import type { components } from '@/api/generated/schema'
import { formatDate } from '@/utils/format-utils'

interface Vendor {
  id: number
  name: string
  contact_name: string | null
  email: string | null
  phone: string | null
  is_active: boolean
}

type VendorPerformance = components['schemas']['VendorPerformanceResponse']

interface Props {
  token: string
  vendors: Vendor[]
  formatMoney: (n: number) => string
}

export default function VendorComparison({ token, vendors, formatMoney }: Props) {
  const [performances, setPerformances] = useState<Record<number, VendorPerformance>>({})
  const [loading, setLoading] = useState<Record<number, boolean>>({})
  const [compareMode, setCompareMode] = useState(false)
  const [selectedVendors, setSelectedVendors] = useState<number[]>([])
  const [activeVendorId, setActiveVendorId] = useState<number | null>(null)

  const fetchPerformance = useCallback(
    async (vendorId: number) => {
      if (performances[vendorId]) return
      setLoading((prev) => ({ ...prev, [vendorId]: true }))
      try {
        const data: VendorPerformance = await fetchApi(`/acquisition/vendors/${vendorId}/performance`)
        setPerformances((prev) => ({ ...prev, [vendorId]: data }))
      } catch (err) {
        toast.error(err instanceof Error ? err.message : t('toast.acquisition.failedToLoadVendorPerformance'))
      } finally {
        setLoading((prev) => ({ ...prev, [vendorId]: false }))
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [performances, token]
  )

  useEffect(() => {
    vendors.filter((v) => v.is_active).forEach((v) => fetchPerformance(v.id))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vendors])

  const toggleVendorCompare = (vendorId: number) => {
    setSelectedVendors((prev) =>
      prev.includes(vendorId)
        ? prev.filter((id) => id !== vendorId)
        : prev.length < 4
          ? [...prev, vendorId]
          : prev
    )
  }

  const getRatingColor = (rate: number | null | undefined, thresholds: [number, number] = [0.8, 0.95]) => {
    if (rate == null) return "text-lsc-dark/70 dark:text-lsc-cream/60"
    if (rate >= thresholds[1]) return "text-status-success-600 dark:text-status-success-400"
    if (rate >= thresholds[0]) return "text-status-warning-600 dark:text-status-warning-400"
    return "text-status-danger-600 dark:text-status-danger-400"
  }

  const getRatingBadge = (rate: number | null | undefined, thresholds: [number, number] = [0.8, 0.95]) => {
    if (rate == null) return "bg-earth-100 text-earth-600 dark:bg-earth-700 dark:text-earth-300"
    if (rate >= thresholds[1])
      return "bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-300"
    if (rate >= thresholds[0])
      return "bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-300"
    return "bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900/30 dark:text-status-danger-300"
  }

  const activeVendors = vendors.filter((v) => v.is_active)
  const allLoaded = activeVendors.every(
    (v) => performances[v.id] !== undefined || loading[v.id] === false
  )
  const anyLoading = activeVendors.some((v) => loading[v.id])

  const comparedPerformances = selectedVendors
    .map((id) => performances[id])
    .filter(Boolean) as VendorPerformance[]

  const activePerformance = activeVendorId ? performances[activeVendorId] : null
  const deliveryDays = comparedPerformances
    .map((p) => p.average_delivery_days)
    .filter((days): days is number => days != null)
  const fillRates = comparedPerformances
    .map((p) => p.fill_rate)
    .filter((rate): rate is number => rate != null)
  const onTimeRates = comparedPerformances
    .map((p) => p.on_time_rate)
    .filter((rate): rate is number => rate != null)
  const bestDeliveryDays = deliveryDays.length ? Math.min(...deliveryDays) : null
  const bestFillRate = fillRates.length ? Math.max(...fillRates) : null
  const bestOnTimeRate = onTimeRates.length ? Math.max(...onTimeRates) : null

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
          Vendor Performance
        </h3>
        <button
          onClick={() => {
            setCompareMode((prev) => !prev)
            if (compareMode) setSelectedVendors([])
          }}
          className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl font-medium text-sm transition-colors ${
            compareMode
              ? "bg-lsc-rose text-white hover:bg-lsc-rose/90"
              : "border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-earth-50 dark:hover:bg-earth-700"
          }`}
        >
          <BarChart3 className="w-4 h-4" />
          {compareMode ? "Exit Compare" : "Compare Vendors"}
        </button>
      </div>

      {anyLoading && !allLoaded && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" />
        </div>
      )}

      {activeVendors.length === 0 && (
        <div className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/60">
          <Users className="w-10 h-10 mx-auto mb-2 opacity-40" />
          <p>No active vendors found.</p>
        </div>
      )}

      {compareMode && (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {activeVendors.map((vendor) => {
              const isSelected = selectedVendors.includes(vendor.id)
              return (
                <button
                  key={vendor.id}
                  onClick={() => toggleVendorCompare(vendor.id)}
                  disabled={!isSelected && selectedVendors.length >= 4}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-xl transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${
                    isSelected
                      ? "bg-lsc-rose text-white"
                      : "border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-earth-50 dark:hover:bg-earth-700"
                  }`}
                >
                  {isSelected && <CheckCircle className="w-3.5 h-3.5" />}
                  {vendor.name}
                </button>
              )
            })}
          </div>
          {selectedVendors.length < 2 && (
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
              Select at least 2 vendors to compare (max 4).
            </p>
          )}

          {comparedPerformances.length >= 2 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-lsc-border dark:border-earth-700">
                    <th className="text-left py-2 px-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/60 text-xs uppercase tracking-wide">
                      Metric
                    </th>
                    {comparedPerformances.map((p) => (
                      <th
                        key={p.vendor_id}
                        className="text-right py-2 px-3 font-medium text-lsc-dark dark:text-lsc-cream text-xs uppercase tracking-wide"
                      >
                        {p.vendor_name}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b border-lsc-border/50 dark:border-earth-700/50">
                    <td className="py-2.5 px-3 text-lsc-dark/70 dark:text-lsc-cream/70 flex items-center gap-1.5">
                      <ShoppingCart className="w-3.5 h-3.5" />
                      Total Orders
                    </td>
                    {comparedPerformances.map((p) => (
                      <td
                        key={p.vendor_id}
                        className="py-2.5 px-3 text-right font-medium text-lsc-dark dark:text-lsc-cream"
                      >
                        {p.total_orders}
                      </td>
                    ))}
                  </tr>
                  <tr className="border-b border-lsc-border/50 dark:border-earth-700/50">
                    <td className="py-2.5 px-3 text-lsc-dark/70 dark:text-lsc-cream/70 flex items-center gap-1.5">
                      <DollarSign className="w-3.5 h-3.5" />
                      Total Spent
                    </td>
                    {comparedPerformances.map((p) => (
                      <td
                        key={p.vendor_id}
                        className="py-2.5 px-3 text-right font-medium text-lsc-dark dark:text-lsc-cream"
                      >
                        {formatMoney(p.total_spent)}
                      </td>
                    ))}
                  </tr>
                  <tr className="border-b border-lsc-border/50 dark:border-earth-700/50">
                    <td className="py-2.5 px-3 text-lsc-dark/70 dark:text-lsc-cream/70 flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5" />
                      Avg Delivery Days
                    </td>
                    {comparedPerformances.map((p) => {
                      return (
                        <td
                          key={p.vendor_id}
                          className={`py-2.5 px-3 text-right font-medium ${
                            p.average_delivery_days != null && p.average_delivery_days === bestDeliveryDays
                              ? "text-status-success-600 dark:text-status-success-400"
                              : "text-lsc-dark dark:text-lsc-cream"
                          }`}
                        >
                          {p.average_delivery_days == null ? "No delivery data" : `${p.average_delivery_days.toFixed(1)} days`}
                        </td>
                      )
                    })}
                  </tr>
                  <tr className="border-b border-lsc-border/50 dark:border-earth-700/50">
                    <td className="py-2.5 px-3 text-lsc-dark/70 dark:text-lsc-cream/70 flex items-center gap-1.5">
                      <Package className="w-3.5 h-3.5" />
                      Fill Rate
                    </td>
                    {comparedPerformances.map((p) => {
                      return (
                        <td
                          key={p.vendor_id}
                          className={`py-2.5 px-3 text-right font-medium ${
                            p.fill_rate != null && p.fill_rate === bestFillRate
                              ? "text-status-success-600 dark:text-status-success-400"
                              : getRatingColor(p.fill_rate)
                          }`}
                        >
                          {p.fill_rate == null ? "No fill data" : `${(p.fill_rate * 100).toFixed(1)}%`}
                        </td>
                      )
                    })}
                  </tr>
                  <tr className="border-b border-lsc-border/50 dark:border-earth-700/50">
                    <td className="py-2.5 px-3 text-lsc-dark/70 dark:text-lsc-cream/70 flex items-center gap-1.5">
                      <TrendingUp className="w-3.5 h-3.5" />
                      On-Time Rate
                    </td>
                    {comparedPerformances.map((p) => {
                      return (
                        <td
                          key={p.vendor_id}
                          className={`py-2.5 px-3 text-right font-medium ${
                            p.on_time_rate != null && p.on_time_rate === bestOnTimeRate
                              ? "text-status-success-600 dark:text-status-success-400"
                              : getRatingColor(p.on_time_rate)
                          }`}
                        >
                          {p.on_time_rate == null ? "No delivery data" : `${(p.on_time_rate * 100).toFixed(1)}%`}
                        </td>
                      )
                    })}
                  </tr>
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {!compareMode && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {activeVendors.map((vendor) => {
              const perf = performances[vendor.id]
              const isLoading = loading[vendor.id]
              const isActive = activeVendorId === vendor.id

              return (
                <button
                  key={vendor.id}
                  onClick={() => setActiveVendorId(isActive ? null : vendor.id)}
                  className={`text-left border rounded-xl p-4 transition-colors ${
                    isActive
                      ? "border-lsc-rose bg-lsc-rose/5 dark:bg-lsc-rose/10"
                      : "border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 hover:bg-earth-50 dark:hover:bg-earth-700/50"
                  }`}
                >
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="font-medium text-lsc-dark dark:text-lsc-cream truncate" title={vendor.name}>
                      {vendor.name}
                    </h4>
                    {isLoading && (
                      <Loader2 className="w-4 h-4 motion-safe:animate-spin text-lsc-rose flex-shrink-0" />
                    )}
                  </div>

                  {perf ? (
                    <div className="space-y-2">
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div>
                          <span className="text-lsc-dark/70 dark:text-lsc-cream/60">Orders</span>
                          <p className="font-semibold text-lsc-dark dark:text-lsc-cream">
                            {perf.total_orders}
                          </p>
                        </div>
                        <div>
                          <span className="text-lsc-dark/70 dark:text-lsc-cream/60">Spent</span>
                          <p className="font-semibold text-lsc-dark dark:text-lsc-cream">
                            {formatMoney(perf.total_spent)}
                          </p>
                        </div>
                        <div>
                          <span className="text-lsc-dark/70 dark:text-lsc-cream/60">Avg Delivery</span>
                          <p className="font-semibold text-lsc-dark dark:text-lsc-cream">
                            {perf.average_delivery_days == null ? "No delivery data" : `${perf.average_delivery_days.toFixed(1)} days`}
                          </p>
                        </div>
                        <div>
                          <span className="text-lsc-dark/70 dark:text-lsc-cream/60">Fill Rate</span>
                          <p className={`font-semibold ${getRatingColor(perf.fill_rate)}`}>
                            {perf.fill_rate == null ? "No fill data" : `${(perf.fill_rate * 100).toFixed(1)}%`}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 pt-1">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full ${getRatingBadge(perf.on_time_rate)}`}
                        >
                          On-time: {perf.on_time_rate == null ? "No delivery data" : `${(perf.on_time_rate * 100).toFixed(0)}%`}
                        </span>
                      </div>
                    </div>
                  ) : !isLoading ? (
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
                      No performance data available.
                    </p>
                  ) : null}
                </button>
              )
            })}
          </div>

          {activePerformance && activePerformance.recent_orders && activePerformance.recent_orders.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
                <ShoppingCart className="w-4 h-4 text-lsc-rose" />
                Order History — {activePerformance.vendor_name}
              </h4>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-lsc-border dark:border-earth-700">
                      <th className="text-left py-2 px-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/60 text-xs uppercase tracking-wide">
                        PO #
                      </th>
                      <th className="text-left py-2 px-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/60 text-xs uppercase tracking-wide">
                        Date
                      </th>
                      <th className="text-right py-2 px-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/60 text-xs uppercase tracking-wide">
                        Total
                      </th>
                      <th className="text-center py-2 px-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/60 text-xs uppercase tracking-wide">
                        Status
                      </th>
                      <th className="text-right py-2 px-3 font-medium text-lsc-dark/70 dark:text-lsc-cream/60 text-xs uppercase tracking-wide">
                        Delivery
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {activePerformance.recent_orders.map((order) => (
                      <tr
                        key={order.po_number}
                        className="border-b border-lsc-border/50 dark:border-earth-700/50 hover:bg-earth-50 dark:hover:bg-earth-700/30 transition-colors"
                      >
                        <td className="py-2.5 px-3 font-medium text-lsc-dark dark:text-lsc-cream">
                          {order.po_number}
                        </td>
                        <td className="py-2.5 px-3 text-lsc-dark/70 dark:text-lsc-cream/70">
                          <span className="inline-flex items-center gap-1">
                            <Calendar className="w-3.5 h-3.5" />
                            {formatDate(order.order_date)}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-right text-lsc-dark dark:text-lsc-cream">
                          {formatMoney(order.total_amount)}
                        </td>
                        <td className="py-2.5 px-3 text-center">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full ${
                              order.status === "received"
                                ? "bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-300"
                                : order.status === "submitted"
                                  ? "bg-category-100 text-category-700 dark:bg-category-900/30 dark:text-category-300"
                                  : order.status === "cancelled"
                                    ? "bg-earth-200 text-earth-600 dark:bg-earth-600 dark:text-earth-300"
                                    : "bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-300"
                            }`}
                          >
                            {order.status.charAt(0).toUpperCase() + order.status.slice(1).replace(/_/g, " ")}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-right text-lsc-dark/70 dark:text-lsc-cream/70">
                          {order.delivery_days != null ? `${order.delivery_days} days` : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {activePerformance && (!activePerformance.recent_orders || activePerformance.recent_orders.length === 0) && (
            <div className="border border-lsc-border dark:border-earth-700 rounded-xl p-6 text-center">
              <ShoppingCart className="w-8 h-8 text-lsc-dark/30 dark:text-lsc-cream/60 mx-auto mb-2" />
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
                No order history available for {activePerformance.vendor_name}.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
