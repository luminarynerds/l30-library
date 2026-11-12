/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from "react-router-dom"
import { Check } from "lucide-react"
import { clsx } from "@/utils/helpers"
import type { ItemRecommendation } from "@/api/api"
import { useTranslation } from "@/i18n/I18nContext"
import CatalogItemThumbnail, { CatalogCover } from "./CatalogItemThumbnail"

interface ReadAlikesProps {
  items: ItemRecommendation[]
}

export function ReadAlikes({ items }: ReadAlikesProps): React.ReactElement {
  const { t } = useTranslation()

  if (!items.length) {
    return <></>
  }

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm p-6 md:p-8">
      <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-1">
        {t("catalog.readAlikes.title")}
      </h2>
      <p className="text-sm mb-4 text-lsc-dark/70 dark:text-lsc-cream/60">
        {t("catalog.relatedItems.availableHighlighted")}
      </p>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((rec) => (
          <Link
            key={rec.id}
            to={`/catalog/${rec.id}`}
            state={{ fromCatalog: true }}
            className={clsx(
              "flex gap-3 p-4 rounded-lg border transition-all border-l-4",
              rec.available
                ? "border-lsc-border dark:border-earth-700 border-l-green-500 dark:border-l-green-400 hover:border-lsc-rose hover:shadow-md"
                : "border-lsc-border/60 dark:border-earth-700/60 border-l-transparent opacity-75 hover:opacity-100 hover:border-lsc-rose hover:shadow-md"
            )}
          >
            {/* Cover image or icon */}
            <div className={clsx(
              "flex-shrink-0 w-16 h-24 rounded-lg flex items-center justify-center overflow-hidden",
              rec.available
                ? "bg-lsc-cream dark:bg-lsc-brown"
                : "bg-lsc-cream/60 dark:bg-lsc-brown/60"
            )}>
              {rec.cover_image ? (
                <CatalogCover
                  coverUrl={rec.cover_image}
                  itemId={rec.id}
                  alt={rec.author ? `${rec.title} by ${rec.author}` : rec.title}
                  title={rec.title}
                  size="sm"
                />
              ) : (
                <CatalogItemThumbnail title={rec.title} size="sm" />
              )}
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <p className="text-base font-medium text-lsc-dark dark:text-lsc-cream line-clamp-2 mb-1" title={rec.title}>
                {rec.title}
              </p>
              {rec.author && (
                <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80 truncate mb-2">
                  {rec.author}
                </p>
              )}
              {rec.available ? (
                <p className="text-sm font-medium text-status-success-700 dark:text-status-success-300 flex items-center gap-1">
                  <Check className="w-3 h-3" aria-hidden="true" />
                  {t("catalog.relatedItems.availableNow")}
                </p>
              ) : (
                <p className="text-sm text-lsc-dark/60 dark:text-lsc-cream/50">
                  Checked out
                </p>
              )}
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
