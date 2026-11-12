/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from "react"
import { CatalogItem, CatalogSearchResult } from "../../api/catalog-api"
import { Edit, Trash2, Loader2, ChevronLeft, ChevronRight, Package, Search } from "lucide-react"
import { ITEM_TYPES, ITEM_STATUSES } from "./constants"

interface CatalogResultsTableProps {
  searchResults: CatalogSearchResult | null
  currentPage: number
  isSearching: boolean
  selectedCount: number
  isSelected: (id: number) => boolean
  toggleSelection: (id: number) => void
  setSelectedIds: (ids: number[]) => void
  onEdit: (item: CatalogItem) => void
  onDelete: (item: CatalogItem) => void
  onPageChange: (page: number) => void
}

const getTypeIcon = (type: string) => {
  const f = ITEM_TYPES.find((t) => t.value === type)
  const I = f?.icon || Package
  return <I aria-hidden="true" className="w-4 h-4" />
}

const getStatusBadge = (status: string) => {
  const f = ITEM_STATUSES.find((s) => s.value === status)
  const label = f?.label || status
  const group = f?.group || "Available"
  const c = group === "Available" ? "bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-400"
    : group === "Circulation" ? "bg-earth-100 text-lsc-rose dark:bg-earth-800/30 dark:text-lsc-rose-light"
    : group === "Acquisitions" ? "bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-400"
    : group === "Lost" ? "bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900/30 dark:text-status-danger-400"
    : group === "Collection" ? "bg-lsc-rose/10 text-lsc-rose dark:bg-lsc-rose/20 dark:text-lsc-rose-light"
    : "bg-status-warning-100 text-status-warning-700 dark:bg-status-warning-900/30 dark:text-status-warning-400"
  return <span className={`px-2 py-0.5 text-xs font-medium rounded ${c}`}>{label}</span>
}

const CatalogResultsTable: React.FC<CatalogResultsTableProps> = ({
  searchResults,
  currentPage,
  isSearching,
  selectedCount,
  isSelected,
  toggleSelection,
  setSelectedIds,
  onEdit,
  onDelete,
  onPageChange,
}) => {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-lsc-cream dark:bg-lsc-brown/50">
            <tr>
              <th className="px-4 py-3 text-left w-10">
                <input type="checkbox"
                  aria-label="Select all items"
                  checked={searchResults?.items.length === selectedCount && selectedCount > 0}
                  onChange={(e) => {
                    if (e.target.checked && searchResults) {
                      setSelectedIds(searchResults.items.map(i => i.id))
                    } else {
                      setSelectedIds([])
                    }
                  }}
                  className="rounded border-lsc-border dark:border-earth-700"
                />
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Title</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Author</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Type</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Status</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">ISBN/Barcode</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
            {isSearching ? (
              <tr><td colSpan={7} className="px-4 py-12 text-center"><Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose mx-auto" /></td></tr>
            ) : !searchResults ? (
              <tr><td colSpan={7} className="px-4 py-16 text-center">
                <Search aria-hidden="true" className="w-8 h-8 text-lsc-dark/30 dark:text-lsc-cream/30 mx-auto mb-3" />
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70 font-medium">Search the catalog to get started</p>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/50 mt-1">Search by title, author, ISBN, or barcode</p>
              </td></tr>
            ) : searchResults.items.length === 0 ? (
              <tr><td colSpan={7} className="px-4 py-12 text-center text-lsc-dark/70 dark:text-lsc-cream/70">No items found</td></tr>
            ) : searchResults.items.map((item) => (
              <tr key={item.id} className={`hover:bg-lsc-cream dark:hover:bg-lsc-brown/30 ${isSelected(item.id) ? 'bg-lsc-rose/5 dark:bg-lsc-rose/10' : ''}`}>
                <td className="px-4 py-3">
                  <input type="checkbox" aria-label={`Select ${item.title}`} checked={isSelected(item.id)} onChange={() => toggleSelection(item.id)}
                    className="rounded border-lsc-border dark:border-earth-700" />
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-3">
                    {item.cover_url && (
                      <img src={item.cover_url} alt={`Cover of ${item.title}`} className="w-8 h-10 object-cover rounded shadow-sm" />
                    )}
                    <div>
                      <p className="font-medium text-lsc-dark dark:text-lsc-cream truncate max-w-xs" title={item.title}>{item.title}</p>
                      {item.publication_year && <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">{item.publication_year}</p>}
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3 text-lsc-dark/70 dark:text-lsc-cream/70 truncate max-w-xs" title={item.author || "-"}>{item.author || "-"}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                    {getTypeIcon(item.item_type)}
                    <span className="text-sm">{ITEM_TYPES.find((t) => t.value === item.item_type)?.label || item.item_type}</span>
                  </div>
                </td>
                <td className="px-4 py-3">{getStatusBadge(item.status)}</td>
                <td className="px-4 py-3 font-mono text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{item.isbn || item.barcode || "-"}</td>
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <button onClick={() => onEdit(item)} aria-label={`Edit ${item.title}`} className="inline-flex items-center justify-center min-w-[36px] min-h-[44px] p-2 text-lsc-dark/70 hover:text-lsc-rose dark:text-lsc-cream/70 dark:hover:text-lsc-rose hover:bg-lsc-cream dark:hover:bg-lsc-dark/20 rounded-xl">
                      <Edit aria-hidden="true" className="w-4 h-4" />
                    </button>
                    <button onClick={() => onDelete(item)} aria-label={`Delete ${item.title}`} className="inline-flex items-center justify-center min-w-[36px] min-h-[44px] p-2 text-lsc-dark/70 hover:text-status-danger-600 dark:text-lsc-cream/70 dark:hover:text-status-danger-400 hover:bg-status-danger-50 dark:bg-status-danger-900/20 dark:hover:bg-status-danger-900/20 rounded-xl">
                      <Trash2 aria-hidden="true" className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {searchResults && searchResults.pages > 1 && (
        <div className="px-4 py-3 border-t border-lsc-border dark:border-earth-700 flex items-center justify-between">
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Page {currentPage} of {searchResults.pages} ({searchResults.total} items)</p>
          <div className="flex items-center gap-2">
            <button onClick={() => onPageChange(currentPage - 1)} disabled={currentPage <= 1} aria-label="Previous page" className="inline-flex items-center justify-center min-w-[44px] min-h-[44px] p-2 text-lsc-dark/70 dark:text-lsc-cream/70 disabled:opacity-50 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-lg">
              <ChevronLeft aria-hidden="true" className="w-5 h-5" />
            </button>
            <button onClick={() => onPageChange(currentPage + 1)} disabled={currentPage >= searchResults.pages} aria-label="Next page" className="inline-flex items-center justify-center min-w-[44px] min-h-[44px] p-2 text-lsc-dark/70 dark:text-lsc-cream/70 disabled:opacity-50 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-lg">
              <ChevronRight aria-hidden="true" className="w-5 h-5" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default CatalogResultsTable
