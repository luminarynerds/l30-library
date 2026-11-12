import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { ChevronDown, ChevronUp, MapPin } from "lucide-react"
import { useTranslation } from "@/i18n/I18nContext"
import { fetchApi } from "@/lib/api-client"

export interface BranchAvailabilityData {
  branch_id: number | null
  branch_name: string
  total_copies: number
  available: number
  call_number: string | null
}

/**
 * Per-branch copy availability for a catalog item. Fetched eagerly (react-query,
 * shared key) so the copy-count summary can render without expanding the panel.
 */
export function useItemBranchAvailability(itemId: number) {
  return useQuery({
    queryKey: ["item-branch-availability", itemId],
    queryFn: () => fetchApi<BranchAvailabilityData[]>(`/catalog/items/${itemId}/availability`),
    staleTime: 60 * 1000,
  })
}

interface BranchAvailabilityProps {
  itemId: number
}

export function BranchAvailability({ itemId }: BranchAvailabilityProps) {
  const { t } = useTranslation()
  const [isOpen, setIsOpen] = useState(false)
  const { data: branches = [], isLoading, isError } = useItemBranchAvailability(itemId)

  const totalCopies = branches.reduce((sum, b) => sum + b.total_copies, 0)
  const availableCopies = branches.reduce((sum, b) => sum + b.available, 0)

  return (
    <div className="mb-6">
      {/* Copy-count summary for multi-copy titles. The single item.status word
          elsewhere on the page can read "Checked Out" while other copies sit on
          the shelf; this is the corrective. Single-copy items stay quiet. */}
      {totalCopies > 1 && (
        <p className="mb-2 text-sm font-medium text-lsc-dark dark:text-lsc-cream">
          {t('catalog.availableCopies', { available: availableCopies, total: totalCopies })}
        </p>
      )}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 text-sm font-medium text-lsc-dark dark:text-lsc-cream hover:text-lsc-rose dark:hover:text-lsc-rose transition-colors"
        aria-expanded={isOpen}
      >
        <MapPin className="w-4 h-4" aria-hidden="true" />
        Check other locations
        {isOpen ? (
          <ChevronUp className="w-4 h-4" aria-hidden="true" />
        ) : (
          <ChevronDown className="w-4 h-4" aria-hidden="true" />
        )}
      </button>

      {isOpen && (
        <div className="mt-3 p-4 bg-lsc-cream/60 dark:bg-lsc-dark/60 border border-lsc-border dark:border-earth-700 rounded-xl">
          {isLoading && (
            <p className="text-sm text-lsc-dark/60 dark:text-lsc-cream/60">Loading...</p>
          )}
          {isError && (
            <p className="text-sm text-status-danger-600 dark:text-status-danger-400">Could not load branch availability</p>
          )}
          {!isLoading && !isError && branches.length === 0 && (
            <p className="text-sm text-lsc-dark/60 dark:text-lsc-cream/60">No copy information available.</p>
          )}
          {!isLoading && !isError && branches.length > 0 && (
            <table className="min-w-full text-sm text-left">
              <caption className="sr-only">Copy availability by branch</caption>
              <thead className="text-xs uppercase text-lsc-dark/70 dark:text-lsc-cream/70">
                <tr>
                  <th scope="col" className="px-3 py-2">Location</th>
                  <th scope="col" className="px-3 py-2">Copies</th>
                  <th scope="col" className="px-3 py-2">Status</th>
                  <th scope="col" className="px-3 py-2">Call number</th>
                </tr>
              </thead>
              <tbody>
                {branches.map((b) => (
                  <tr
                    key={b.branch_id ?? b.branch_name}
                    className="border-t border-lsc-border dark:border-earth-700"
                  >
                    <td className="px-3 py-2 font-medium text-lsc-dark dark:text-lsc-cream">
                      {b.branch_name}
                    </td>
                    <td className="px-3 py-2 text-lsc-dark/80 dark:text-lsc-cream/80">
                      {b.available}/{b.total_copies}
                    </td>
                    <td className="px-3 py-2">
                      <span className="inline-flex items-center gap-1.5">
                        <span
                          className={`w-2 h-2 rounded-full ${
                            b.available > 0
                              ? "bg-status-success-500"
                              : "bg-status-danger-500"
                          }`}
                          aria-hidden="true"
                        />
                        <span className="text-lsc-dark/80 dark:text-lsc-cream/80">
                          {b.available > 0 ? "Available" : "Checked out"}
                        </span>
                      </span>
                    </td>
                    <td className="px-3 py-2 text-lsc-dark/60 dark:text-lsc-cream/60 font-mono text-xs">
                      {b.call_number ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  )
}
