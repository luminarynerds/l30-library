/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useMemo } from "react"
import { Link } from "react-router-dom"
import { Check } from "lucide-react"
import { clsx } from "@/utils/helpers"
import type { CatalogItem } from "@/api/api"
import { buildCoverAlt } from "@/pages/catalog/utils/catalogHelpers"
import { useTranslation } from "@/i18n/I18nContext"
import { formatItemType } from "./ItemOverview"
import CatalogItemThumbnail, { CatalogCover } from "./CatalogItemThumbnail"

interface RelatedItemsProps {
  items: CatalogItem[]
}

export function RelatedItems({ items }: RelatedItemsProps): React.ReactElement {
  const { t } = useTranslation()

  const sortedItems = useMemo(
    () => [...items].sort((a, b) => {
      if (a.status === "available" && b.status !== "available") return -1
      if (b.status === "available" && a.status !== "available") return 1
      return 0
    }),
    [items]
  )

  const availableCount = useMemo(
    () => sortedItems.filter((i) => i.status === "available").length,
    [sortedItems]
  )

  if (!sortedItems.length) {
    return <></>
  }

  const allCheckedOut = availableCount === 0
  const someAvailable = availableCount > 0

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-6 md:p-8">
      <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-1">
        {t("catalog.relatedItems.title")}
      </h2>
      <p className={clsx(
        "text-sm mb-4",
        allCheckedOut
          ? "text-status-warning-700 dark:text-status-warning-300"
          : "text-lsc-dark/70 dark:text-lsc-cream/60"
      )}>
        {allCheckedOut
          ? t("catalog.relatedItems.allCheckedOut")
          : someAvailable
            ? t("catalog.relatedItems.availableHighlighted")
            : t("catalog.relatedItems.title")}
      </p>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {sortedItems.map((candidate: CatalogItem) => {
          const isAvailable = candidate.status === "available"
          return (
            <Link
              key={candidate.id}
              to={`/catalog/${candidate.id}`}
              state={{ fromCatalog: true }}
              className={clsx(
                "flex gap-3 p-4 rounded-lg border transition-all border-l-4",
                isAvailable
                  ? "border-lsc-border dark:border-earth-700 border-l-green-500 dark:border-l-green-400 hover:border-lsc-rose hover:shadow-md"
                  : "border-lsc-border/60 dark:border-earth-700/60 border-l-transparent hover:border-lsc-rose hover:shadow-md"
              )}
            >
              {/* Cover image or icon */}
              <div className={clsx(
                "flex-shrink-0 w-16 h-24 rounded-lg flex items-center justify-center overflow-hidden",
                isAvailable
                  ? "bg-lsc-cream dark:bg-lsc-brown"
                  : "bg-lsc-cream/60 dark:bg-lsc-brown/60"
              )}>
                {(() => {
                const pi = candidate.images?.find((img) => img.is_primary) ?? candidate.images?.[0]
                const src = pi?.image_url || candidate.cover_url
                return src ? (
                  <CatalogCover
                    coverUrl={src}
                    itemId={candidate.id}
                    alt={buildCoverAlt(candidate.title, candidate.author, candidate.item_type)}
                    title={candidate.title}
                    itemType={candidate.item_type}
                    size="sm"
                  />
                ) : (
                  <CatalogItemThumbnail title={candidate.title} itemType={candidate.item_type} size="sm" />
                )
                })()}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-start gap-2 mb-1">
                  <span className="text-xs px-2 py-0.5 bg-lsc-cream dark:bg-lsc-dark text-lsc-rose dark:text-earth-300 rounded-full font-medium flex-shrink-0">
                    {formatItemType(candidate.item_type)}
                  </span>
                </div>
                <p className="text-base font-medium text-lsc-dark dark:text-lsc-cream line-clamp-2 mb-1" title={candidate.title}>
                  {candidate.title}
                </p>
                {candidate.author && (
                  <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80 truncate mb-2">
                    {candidate.author}
                  </p>
                )}
                {isAvailable ? (
                  <p className="text-sm font-medium text-status-success-700 dark:text-status-success-300 flex items-center gap-1">
                    <Check className="w-3 h-3" aria-hidden="true" />
                    {t("catalog.relatedItems.availableNow")}
                  </p>
                ) : (
                  <p className="text-sm text-lsc-dark dark:text-lsc-cream">
                    Checked out
                  </p>
                )}
              </div>
            </Link>
          )
        })}
      </div>
    </div>
  )
}
