/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import FocusTrap from "focus-trap-react"
import { AlertCircle, BookOpen, ExternalLink, ShoppingCart, Star, X } from "lucide-react"
import { useTranslation } from "@/i18n"
import { daysUntil, formatReleaseDate, getAgeBadgeClass, getStatusBadgeClass } from "./utils"
import type { LibrarianRelease } from "./types"

interface Props {
  release: LibrarianRelease
  onClose: () => void
  onAddToPO: () => void
  onFeature: () => void
  formatMoney: (n: number) => string
}

export default function ReleaseDetailDrawer({ release, onClose, onAddToPO, onFeature, formatMoney }: Props) {
  const { t } = useTranslation()
  const days = daysUntil(release.book.release_date)

  return (
    <FocusTrap active focusTrapOptions={{ escapeDeactivates: true }}>
      <div className="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true" aria-label={t('aria.acquisition.releaseDetails')}>
        {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events */}
        <div className="absolute inset-0 bg-black/40" onClick={onClose} />
        <div className="relative w-full max-w-lg bg-lsc-white dark:bg-earth-800 shadow-lg overflow-y-auto">
          <div className="sticky top-0 bg-lsc-white dark:bg-earth-800 border-b border-lsc-border dark:border-earth-700 px-6 py-4 flex items-center justify-between z-10">
            <h2 className="text-lg font-serif font-semibold text-lsc-dark dark:text-lsc-cream truncate pr-4" title="Release Details">
              Release Details
            </h2>
            <button
              onClick={onClose}
              className="p-2 text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream rounded-xl"
              aria-label={t('aria.acquisition.closeDetails')}
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="p-6 space-y-6">
            <div className="flex gap-4">
              {release.book.cover_url ? (
                <img
                  src={release.book.cover_url}
                  alt={`Cover of ${release.book.title}`}
                  className="w-24 h-36 object-cover rounded-lg shadow-md flex-shrink-0"
                />
              ) : (
                <div className="w-24 h-36 bg-lsc-cream dark:bg-lsc-brown rounded-lg flex items-center justify-center flex-shrink-0">
                  <BookOpen className="w-8 h-8 text-lsc-dark/20 dark:text-lsc-cream/20" />
                </div>
              )}
              <div className="min-w-0">
                <h3 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">{release.book.title}</h3>
                {release.book.subtitle && (
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60 mt-0.5">{release.book.subtitle}</p>
                )}
                <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{release.author_name}</p>
                <div className="flex flex-wrap gap-2 mt-3">
                  <span className={"px-2 py-0.5 text-xs font-medium rounded " + getStatusBadgeClass(release.library_status)}>
                    {release.library_status.replace("_", " ")}
                  </span>
                  <span className={"px-2 py-0.5 text-xs font-medium rounded capitalize " + getAgeBadgeClass(release.book.age_rating, false)}>
                    {release.book.age_rating || "—"}
                  </span>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-lsc-dark/70 dark:text-lsc-cream/60">Release Date</p>
                <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                  {formatReleaseDate(release.book.release_date, release.book.is_date_exact)}
                  {days !== null && (
                    days < 0 ? (
                      <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 ml-1">(released)</span>
                    ) : days === 0 ? (
                      <span className="text-xs text-lsc-rose ml-1">(today)</span>
                    ) : (
                      <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 ml-1">({days} days)</span>
                    )
                  )}
                </p>
              </div>
              <div>
                <p className="text-lsc-dark/70 dark:text-lsc-cream/60">List Price</p>
                <p className="font-medium text-lsc-dark dark:text-lsc-cream">
                  {release.book.list_price ? formatMoney(release.book.list_price) : "Not available"}
                </p>
              </div>
              <div>
                <p className="text-lsc-dark/70 dark:text-lsc-cream/60">ISBN-13</p>
                <p className="font-mono text-lsc-dark dark:text-lsc-cream">{release.book.isbn_13 || "-"}</p>
              </div>
              <div>
                <p className="text-lsc-dark/70 dark:text-lsc-cream/60">ISBN-10</p>
                <p className="font-mono text-lsc-dark dark:text-lsc-cream">{release.book.isbn_10 || "-"}</p>
              </div>
              {release.book.publisher && (
                <div>
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/60">Publisher</p>
                  <p className="font-medium text-lsc-dark dark:text-lsc-cream">{release.book.publisher}</p>
                </div>
              )}
              {release.book.page_count && (
                <div>
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/60">Pages</p>
                  <p className="font-medium text-lsc-dark dark:text-lsc-cream">{release.book.page_count}</p>
                </div>
              )}
              <div>
                <p className="text-lsc-dark/70 dark:text-lsc-cream/60">Patron Demand</p>
                <p className="font-medium text-lsc-rose flex items-center gap-1">
                  {release.demand_score > 0 ? (
                    <>
                      <Star className="w-4 h-4" />
                      {release.demand_score} follower{release.demand_score !== 1 ? "s" : ""} tracking
                    </>
                  ) : (
                    <span className="text-lsc-dark/70 dark:text-lsc-cream/60">No followers yet</span>
                  )}
                </p>
              </div>
              <div>
                <p className="text-lsc-dark/70 dark:text-lsc-cream/60">Source</p>
                {release.book.source === "libraryreads" && release.book.source_url ? (
                  <a
                    href={release.book.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-medium text-lsc-rose inline-flex items-center gap-1 hover:underline"
                  >
                    {release.book.blurb_credit || "LibraryReads"}
                    <ExternalLink className="w-3 h-3" />
                  </a>
                ) : (
                  <p className="font-medium text-lsc-dark dark:text-lsc-cream capitalize">
                    {release.book.source.replace(/_/g, " ")}
                  </p>
                )}
              </div>
            </div>

            {release.book.description && (
              <div>
                <p className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/60 mb-2">Description</p>
                <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80 leading-relaxed">{release.book.description}</p>
              </div>
            )}

            {release.book.raw_categories && release.book.raw_categories.length > 0 && (
              <div>
                <p className="text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/60 mb-2">Categories</p>
                <div className="flex flex-wrap gap-2">
                  {release.book.raw_categories.map((cat, i) => (
                    <span key={i} className="px-2 py-1 text-xs bg-lsc-cream dark:bg-lsc-brown rounded-lg text-lsc-dark/70 dark:text-lsc-cream/70">
                      {cat}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div className="border-t border-lsc-border dark:border-earth-700 pt-4 space-y-3">
              <button
                onClick={onFeature}
                className={
                  "w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl font-medium " +
                  (release.book.is_featured
                    ? "border border-lsc-rose text-lsc-rose hover:bg-lsc-rose/10"
                    : "bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream/80 dark:hover:bg-lsc-brown/90")
                }
              >
                <Star className={"w-4 h-4 " + (release.book.is_featured ? "fill-lsc-rose" : "")} />
                {release.book.is_featured ? "Unfeature" : "Feature this title"}
              </button>
              {release.library_status === "new" && (
                <button
                  onClick={onAddToPO}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium"
                >
                  <ShoppingCart className="w-4 h-4" />
                  Add to Purchase Order
                </button>
              )}
              {release.library_status === "owned" && release.catalog_item_id && (
                <a
                  href={`/catalog/${release.catalog_item_id}`}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2.5 border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream rounded-xl font-medium hover:bg-lsc-cream dark:hover:bg-lsc-brown"
                >
                  <ExternalLink className="w-4 h-4" />
                  View in Catalog
                </a>
              )}
              {release.library_status === "on_order" && (
                <div className="flex items-center gap-2 px-4 py-2.5 bg-lsc-cream/50 dark:bg-lsc-brown/30 rounded-xl text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  <AlertCircle className="w-4 h-4" />
                  This title is already on order
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </FocusTrap>
  )
}
