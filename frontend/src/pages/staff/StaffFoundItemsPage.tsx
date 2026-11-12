/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { useState, useEffect, useCallback } from "react"
import { Package, MapPin, Calendar, Tag, Archive, ChevronDown, ChevronUp, Search } from "lucide-react"
import { AdminShell } from "../../components/shells/AdminShell"
import { listFoundItems, type FoundItem } from "@/api/found-items-api"
import { getCurrentLocale } from '@/i18n'

const STATUS_OPTIONS = [
  { value: "", label: "All" },
  { value: "stored", label: "Stored" },
  { value: "claimed", label: "Claimed" },
  { value: "disposed", label: "Disposed" },
  { value: "donated", label: "Donated" },
  { value: "logged", label: "Logged" },
  { value: "unclaimed", label: "Unclaimed" },
] as const

const STATUS_COLORS: Record<string, string> = {
  stored: "bg-status-info-100 text-status-info-800 dark:bg-status-info-900/30 dark:text-status-info-300",
  logged: "bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300",
  claimed: "bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300",
  verified: "bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300",
  disposed: "bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-300",
  donated: "bg-category-100 text-category-800 dark:bg-category-900/30 dark:text-category-300",
  unclaimed: "bg-earth-100 text-earth-800 dark:bg-earth-700 dark:text-earth-300",
  waiting_claim: "bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300",
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(getCurrentLocale(), {
    month: "short",
    day: "numeric",
    year: "numeric",
  })
}

function StatusBadge({ status }: { status: string }) {
  const label = status.replace(/_/g, " ")
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize ${STATUS_COLORS[status] || "bg-earth-100 text-earth-800 dark:bg-earth-700 dark:text-earth-300"}`}
    >
      {label}
    </span>
  )
}

function DetailRow({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: React.ReactNode }) {
  if (!value) return null
  return (
    <div className="flex items-start gap-2 text-sm">
      <Icon className="w-4 h-4 mt-0.5 text-earth-600 dark:text-earth-500 flex-shrink-0" aria-hidden="true" />
      <span className="text-earth-600 dark:text-earth-400 min-w-[100px]">{label}:</span>
      <span className="text-lsc-dark dark:text-lsc-cream">{value}</span>
    </div>
  )
}

function FoundItemRow({ item }: { item: FoundItem }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="border border-lsc-border dark:border-earth-700 rounded-xl overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left px-4 py-3 flex items-center gap-4 hover:bg-earth-50 dark:hover:bg-earth-800/50 transition-colors min-h-[44px]"
        aria-expanded={expanded}
      >
        <Package className="w-5 h-5 text-earth-600 dark:text-earth-500 flex-shrink-0" aria-hidden="true" />
        <div className="flex-1 min-w-0 grid grid-cols-1 sm:grid-cols-[1fr_auto_auto_auto] gap-x-4 gap-y-1 items-center">
          <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream truncate">
            {item.description}
          </span>
          <span className="text-xs text-earth-600 dark:text-earth-400 capitalize hidden sm:block">
            {item.category}
          </span>
          <span className="text-xs text-earth-600 dark:text-earth-400 hidden sm:block">
            {formatDate(item.date_found)}
          </span>
          <StatusBadge status={item.status} />
        </div>
        {expanded ? (
          <ChevronUp className="w-4 h-4 text-earth-600 flex-shrink-0" aria-hidden="true" />
        ) : (
          <ChevronDown className="w-4 h-4 text-earth-600 flex-shrink-0" aria-hidden="true" />
        )}
      </button>

      {expanded && (
        <div className="px-4 pb-4 pt-2 border-t border-earth-100 dark:border-earth-700 space-y-2 bg-earth-50/50 dark:bg-earth-800/30">
          <DetailRow icon={Tag} label="Category" value={item.category} />
          <DetailRow icon={MapPin} label="Found at" value={item.location_found} />
          {item.location_details && (
            <DetailRow icon={MapPin} label="Details" value={item.location_details} />
          )}
          <DetailRow icon={Calendar} label="Date found" value={formatDate(item.date_found)} />
          <DetailRow
            icon={Archive}
            label="Storage"
            value={item.storage_location?.location_name || "Unassigned"}
          />
          {item.color && <DetailRow icon={Tag} label="Color" value={item.color} />}
          {item.brand_or_label && <DetailRow icon={Tag} label="Brand" value={item.brand_or_label} />}
          {item.condition && <DetailRow icon={Tag} label="Condition" value={item.condition} />}
          {item.additional_details && (
            <DetailRow icon={Tag} label="Notes" value={item.additional_details} />
          )}
          {item.staff_notes && (
            <DetailRow icon={Tag} label="Staff notes" value={item.staff_notes} />
          )}
          <DetailRow
            icon={Calendar}
            label="Retention ends"
            value={formatDate(item.retention_end_date)}
          />
          {item.estimated_value && (
            <DetailRow icon={Tag} label="Est. value" value={`$${item.estimated_value}`} />
          )}
          {item.secure_storage_flag && (
            <div className="flex items-center gap-2 text-sm">
              <Archive className="w-4 h-4 text-status-warning-500 flex-shrink-0" aria-hidden="true" />
              <span className="text-status-warning-600 dark:text-status-warning-400 font-medium">Secure storage</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

const StaffFoundItemsPage: React.FC = () => {
  const [items, setItems] = useState<FoundItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState("")
  const [searchQuery, setSearchQuery] = useState("")

  const fetchItems = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await listFoundItems({
        status: statusFilter || undefined,
        limit: 100,
      })
      setItems(res.items)
      setTotal(res.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load found items")
    } finally {
      setLoading(false)
    }
  }, [statusFilter])

  useEffect(() => {
    fetchItems()
  }, [fetchItems])

  const filtered = searchQuery
    ? items.filter(
        (i) =>
          i.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
          i.category.toLowerCase().includes(searchQuery.toLowerCase()) ||
          i.location_found.toLowerCase().includes(searchQuery.toLowerCase()),
      )
    : items

  return (
    <AdminShell
      title="Lost & Found"
      subtitle={`${total} item${total !== 1 ? "s" : ""} tracked`}
      icon={<Package className="w-8 h-8 text-lsc-rose" />}
      loading={loading && items.length === 0}
      error={error}
    >
      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-earth-600" aria-hidden="true" />
          <input
            type="text"
            placeholder="Search items..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 min-h-[44px] rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream placeholder:text-earth-400 focus:outline-none focus:ring-2 focus:ring-lsc-rose/50"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-4 py-2 min-h-[44px] rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose/50"
          aria-label="Filter by status"
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Result count, announced to assistive tech */}
      <p role="status" aria-live="polite" className="sr-only">
        {!loading && `${filtered.length} item${filtered.length === 1 ? '' : 's'} match your filters`}
      </p>

      {/* Results */}
      {filtered.length === 0 && !loading ? (
        <div className="text-center py-12">
          <Package className="w-12 h-12 mx-auto text-earth-300 dark:text-earth-600 mb-3" aria-hidden="true" />
          <p className="text-earth-600 dark:text-earth-400">
            {searchQuery || statusFilter ? "No items match your filters." : "No found items recorded yet."}
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((item) => (
            <FoundItemRow key={item.id} item={item} />
          ))}
        </div>
      )}
    </AdminShell>
  )
}

export default StaffFoundItemsPage
