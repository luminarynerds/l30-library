/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useMemo } from "react"
import type { ReactElement } from "react"
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from "lucide-react"
import { PAGE_SIZE_OPTIONS, type PageSize } from "./usePatronDirectory"
import { t } from '@/i18n'

interface PatronPaginationProps {
  currentPage: number
  totalPages: number
  totalItems: number
  perPage: PageSize
  onPrevious: () => void
  onNext: () => void
  onPageChange: (page: number) => void
  onPerPageChange: (perPage: PageSize) => void
}

export function PatronPagination({
  currentPage,
  totalPages,
  totalItems,
  perPage,
  onPrevious,
  onNext,
  onPageChange,
  onPerPageChange,
}: PatronPaginationProps): ReactElement {
  // Generate page numbers to show (max 5 visible + ellipsis)
  // Must be called before any early returns (Rules of Hooks)
  const pageNumbers = useMemo(() => {
    const pages: (number | "ellipsis-start" | "ellipsis-end")[] = []
    const maxVisible = 5

    if (totalPages <= maxVisible + 2) {
      for (let i = 1; i <= totalPages; i++) pages.push(i)
    } else {
      pages.push(1)

      if (currentPage > 3) {
        pages.push("ellipsis-start")
      }

      const start = Math.max(2, currentPage - 1)
      const end = Math.min(totalPages - 1, currentPage + 1)
      for (let i = start; i <= end; i++) pages.push(i)

      if (currentPage < totalPages - 2) {
        pages.push("ellipsis-end")
      }

      if (!pages.includes(totalPages)) {
        pages.push(totalPages)
      }
    }

    return pages
  }, [currentPage, totalPages])

  if (totalItems === 0) return <></>

  const startItem = (currentPage - 1) * perPage + 1
  const endItem = Math.min(currentPage * perPage, totalItems)

  return (
    <div className="p-4 border-t border-lsc-border dark:border-earth-700 flex flex-col sm:flex-row items-center justify-between gap-3">
      {/* Result count and page size selector */}
      <div className="flex items-center gap-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
        <span>
          Showing {startItem}&ndash;{endItem} of {totalItems}
        </span>
        <select
          value={perPage}
          onChange={(e) => onPerPageChange(Number(e.target.value) as PageSize)}
          aria-label={t('aria.patronPagination.itemsPerPage')}
          className="px-2 py-1 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream text-sm focus:ring-2 focus:ring-lsc-rose focus:border-transparent cursor-pointer"
        >
          {PAGE_SIZE_OPTIONS.map((size) => (
            <option key={size} value={size}>
              {size} / page
            </option>
          ))}
        </select>
      </div>

      {/* Page navigation */}
      {totalPages > 1 && (
        <div className="flex items-center gap-1">
          {/* First page */}
          <button
            onClick={() => onPageChange(1)}
            disabled={currentPage === 1}
            className="p-1.5 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-lsc-brown/50 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            aria-label={t('aria.patronPagination.firstPage')}
          >
            <ChevronsLeft className="w-4 h-4" aria-hidden="true" />
          </button>

          {/* Previous */}
          <button
            onClick={onPrevious}
            disabled={currentPage === 1}
            className="p-1.5 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-lsc-brown/50 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            aria-label={t('aria.account.previousPage')}
          >
            <ChevronLeft className="w-4 h-4" aria-hidden="true" />
          </button>

          {/* Page numbers */}
          {pageNumbers.map((page) =>
            typeof page === "string" ? (
              <span
                key={page}
                className="px-1.5 py-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/70"
                aria-hidden="true"
              >
                &hellip;
              </span>
            ) : (
              <button
                key={page}
                onClick={() => onPageChange(page)}
                disabled={page === currentPage}
                aria-current={page === currentPage ? "page" : undefined}
                aria-label={`Page ${page}`}
                className={`min-w-[2rem] px-2 py-1 text-sm rounded-lg font-medium transition-colors ${
                  page === currentPage
                    ? "bg-lsc-rose text-white cursor-default"
                    : "text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown/50"
                }`}
              >
                {page}
              </button>
            )
          )}

          {/* Next */}
          <button
            onClick={onNext}
            disabled={currentPage === totalPages}
            className="p-1.5 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-lsc-brown/50 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            aria-label={t('aria.account.nextPage')}
          >
            <ChevronRight className="w-4 h-4" aria-hidden="true" />
          </button>

          {/* Last page */}
          <button
            onClick={() => onPageChange(totalPages)}
            disabled={currentPage === totalPages}
            className="p-1.5 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-lsc-brown/50 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            aria-label={t('aria.patronPagination.lastPage')}
          >
            <ChevronsRight className="w-4 h-4" aria-hidden="true" />
          </button>
        </div>
      )}
    </div>
  )
}
