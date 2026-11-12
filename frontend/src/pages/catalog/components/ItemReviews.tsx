/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from "react"
import { Link } from "react-router-dom"
import { Settings, X, BookOpen, Loader2, Star, Pencil } from "lucide-react"
import { clsx } from "@/utils/helpers"
import { useTranslation } from "@/i18n/I18nContext"
import { useAuth } from "@/contexts/AuthContext"
import { useItemReviews, type SimilarItemsPreferences, type RecommendationItem } from "../hooks/useItemReviews"
import { Button } from "@/components/ui/Button"
import { CurationPanel } from "./CurationPanel"

const STAFF_ROLES = ["staff", "admin", "super_admin"]

interface ItemReviewsProps {
  item: { id: number; item_type: string; subjects?: string | null; author?: string | null }
}

export function ItemReviews({ item }: ItemReviewsProps): React.ReactElement {
  const { t } = useTranslation()
  const { user } = useAuth()
  const { preferences, showSettings, setShowSettings, similarItems, availableCount, isLoading, handlePreferenceChange } = useItemReviews(item)
  const [showCuration, setShowCuration] = useState(false)

  const isStaff = user && STAFF_ROLES.includes(user.role)
  const allCheckedOut = similarItems.length > 0 && availableCount === 0
  const someAvailable = availableCount > 0

  const similarItemStrategies: Array<{ value: SimilarItemsPreferences["strategy"]; label: string; desc: string }> = [
    { value: "mixed", label: t("catalog.similarItems.strategyMixed"), desc: t("catalog.similarItems.strategyMixedDesc") },
    { value: "subject", label: t("catalog.similarItems.strategySubject"), desc: t("catalog.similarItems.strategySubjectDesc") },
    { value: "author", label: t("catalog.similarItems.strategyAuthor"), desc: t("catalog.similarItems.strategyAuthorDesc") },
    { value: "type", label: t("catalog.similarItems.strategyType"), desc: t("catalog.similarItems.strategyTypeDesc") },
  ]

  const renderSettingsPanel = () => (
    <div className="mb-4 p-4 bg-lsc-cream dark:bg-lsc-dark rounded-xl border border-lsc-border dark:border-earth-700">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">{t("catalog.similarItems.similarItemsSettings")}</h3>
        <Button variant="tertiary" size="sm"
          onClick={() => setShowSettings(false)}
          aria-label={t("catalog.closeFilters")}
        >
          <X className="w-4 h-4" />
        </Button>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
            {t("catalog.similarItems.numberOfItems")}
          </label>
          <div className="flex gap-2">
            {[3, 6, 9].map((count) => (
              <Button variant={preferences.count === count ? "primary" : "secondary"}
                key={count}
                onClick={() => handlePreferenceChange({ count: count as 3 | 6 | 9 })}
              >
                {count}
              </Button>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
            {t("catalog.similarItems.matchingStrategy")}
          </label>
          <div className="grid grid-cols-2 gap-2">
            {similarItemStrategies.map((strategy) => (
              <Button variant={preferences.strategy === strategy.value ? "primary" : "secondary"}
                key={strategy.value}
                onClick={() => handlePreferenceChange({ strategy: strategy.value })}
              >
                <div className="font-medium">{strategy.label}</div>
                <div className={clsx(
                  "text-sm mt-1",
                  preferences.strategy === strategy.value
                    ? "text-white/90"
                    : "text-lsc-dark/80 dark:text-lsc-cream/80"
                )}>
                  {strategy.desc}
                </div>
              </Button>
            ))}
          </div>
        </div>

        <div className="pt-4 border-t border-lsc-border dark:border-earth-700">
          <Button variant="danger"
            onClick={() => handlePreferenceChange({ enabled: false })}
          >
            {t("catalog.similarItems.hideSimilarItems")}
          </Button>
        </div>
      </div>
    </div>
  )

  if (!preferences.enabled) {
    return (
      <div className="text-center py-4">
        <button
          onClick={() => handlePreferenceChange({ enabled: true })}
          className="text-sm text-earth-600 dark:text-earth-400 hover:text-lsc-rose dark:hover:text-lsc-rose transition-colors underline underline-offset-2"
        >
          {t("catalog.similarItems.showSimilarItems")}
        </button>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" aria-label={t("catalogItem.loadingSimilarItems")} />
      </div>
    )
  }

  if (!similarItems?.length) {
    return (
      <div>
        <div className="flex items-center justify-between mb-4">
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            {t("catalog.similarItems.noSimilarItems")}
          </p>
          <div className="flex items-center gap-2">
            {isStaff && (
              <Button variant="secondary" size="sm"
                onClick={() => setShowCuration(!showCuration)}
                aria-label="Edit recommendations"
                title="Curate recommendations for this item"
              >
                <Pencil className="w-4 h-4" aria-hidden="true" />
              </Button>
            )}
            <Button variant="secondary" size="sm"
              onClick={() => setShowSettings(!showSettings)}
              aria-label={t("catalog.similarItems.similarItemsSettings")}
              title="Customize how similar items are matched and displayed"
            >
              <Settings className="w-4 h-4" aria-hidden="true" />
              <span className="text-xs">Customize</span>
            </Button>
          </div>
        </div>
        {showSettings && renderSettingsPanel()}
        {showCuration && (
          <CurationPanel itemId={item.id} onClose={() => setShowCuration(false)} />
        )}
      </div>
    )
  }

  const helperText = allCheckedOut
    ? t("catalog.similarItems.allCheckedOut")
    : someAvailable
      ? t("catalog.similarItems.availableHighlighted")
      : t("catalog.similarItems.foundSimilar", { count: similarItems.length })

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <p className={clsx(
          "text-sm",
          allCheckedOut
            ? "text-status-warning-700 dark:text-status-warning-300"
            : "text-lsc-dark/80 dark:text-lsc-cream/80"
        )}>
          {helperText}
        </p>
        <div className="flex items-center gap-2">
          {isStaff && (
            <Button variant="secondary" size="sm"
              onClick={() => setShowCuration(!showCuration)}
              aria-label="Edit recommendations"
              title="Curate recommendations for this item"
            >
              <Pencil className="w-4 h-4" aria-hidden="true" />
            </Button>
          )}
          <Button variant="secondary" size="sm"
            onClick={() => setShowSettings(!showSettings)}
            aria-label={t("catalog.similarItems.similarItemsSettings")}
            title="Customize how similar items are matched and displayed"
          >
            <Settings className="w-4 h-4" aria-hidden="true" />
            <span className="text-xs">Customize</span>
          </Button>
        </div>
      </div>

      {showSettings && renderSettingsPanel()}

      <div className={clsx(
        "grid gap-4",
        preferences.count === 3 && "grid-cols-1 sm:grid-cols-3",
        preferences.count === 6 && "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3",
        preferences.count === 9 && "grid-cols-1 sm:grid-cols-3"
      )}>
        {similarItems.map((recItem: RecommendationItem) => (
          <Link
            key={recItem.id}
            to={`/catalog/${recItem.id}`}
            className={clsx(
              "block p-4 rounded-xl transition-shadow focus:outline-none focus:ring-2 focus:ring-lsc-rose relative border-l-4",
              recItem.available
                ? "bg-lsc-cream dark:bg-lsc-dark border-l-green-500 dark:border-l-green-400 hover:shadow-md"
                : "bg-lsc-cream/60 dark:bg-lsc-dark/60 border-l-transparent opacity-75 hover:opacity-100 hover:shadow-md"
            )}
          >
            {recItem.is_pinned && (
              <span className="absolute top-2 right-2 inline-flex items-center gap-1 px-1.5 py-0.5 bg-status-warning-100 dark:bg-status-warning-900/40 text-status-warning-700 dark:text-status-warning-300 rounded text-xs font-medium">
                <Star className="w-3 h-3 fill-current" aria-hidden="true" />
                Staff Pick
              </span>
            )}
            <div className="flex items-start gap-3">
              <div className={clsx(
                "w-10 h-10 rounded flex items-center justify-center flex-shrink-0",
                recItem.available
                  ? "bg-lsc-white dark:bg-earth-800"
                  : "bg-lsc-white/60 dark:bg-earth-800/60"
              )}>
                {recItem.cover_image ? (
                  <img src={recItem.cover_image} alt="" className="w-10 h-10 rounded object-cover" />
                ) : (
                  <BookOpen className="w-5 h-5 text-lsc-rose" aria-hidden="true" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="font-medium text-base text-lsc-dark dark:text-lsc-cream truncate">
                  {recItem.title}
                </h3>
                {recItem.author && (
                  <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80 truncate">
                    {recItem.author}
                  </p>
                )}
                <span className={clsx(
                  "inline-block mt-1 text-sm px-2 py-0.5 rounded",
                  recItem.available
                    ? "bg-status-success-100 text-status-success-700 dark:bg-status-success-900/30 dark:text-status-success-300"
                    : "bg-lsc-cream text-lsc-rose dark:bg-lsc-brown dark:text-lsc-rose-light"
                )}>
                  {recItem.available ? t("catalog.available") : "Checked out"}
                </span>
              </div>
            </div>
          </Link>
        ))}
      </div>

      {showCuration && (
        <CurationPanel itemId={item.id} onClose={() => setShowCuration(false)} />
      )}
    </div>
  )
}
