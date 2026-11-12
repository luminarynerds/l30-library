/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Link } from "react-router-dom"
import { BookOpen } from "lucide-react"
import { t } from "@/i18n"
import type { CatalogItem } from "@/api"
import { useIndieEbookMatch } from "../hooks/useIndieEbookMatch"
import { catalogItemLink } from "../utils/catalogHelpers"

/**
 * Compact "this work also exists as an indie ebook on MetisLib" affordance
 * shown near the hold CTA when the physical copy is checked out / on hold.
 * The hook gates the lookup (unavailable physical item + author present).
 *
 * The copy never promises immediate borrowability: l30<->MetisLib lending is
 * license-gated per library and the catalog search response carries no
 * per-title licensed/borrowable signal we could verify here, so "Available
 * now" would over-promise. We link out to the MetisLib detail page, where the
 * real borrow/license state resolves. noFOMO drops even the MetisLib mention.
 */
export function IndieEbookAvailability({
  item,
  noFOMO,
}: {
  item: CatalogItem
  noFOMO: boolean
}): React.ReactElement | null {
  const { match } = useIndieEbookMatch(item)

  if (!match) return null

  return (
    <p className="text-xs mt-1">
      <Link
        to={catalogItemLink(match.ebookId, match.title, "indie")}
        className="inline-flex items-center gap-1 text-status-success-700 dark:text-status-success-400 hover:underline font-medium"
      >
        <BookOpen className="w-3.5 h-3.5" aria-hidden="true" />
        {noFOMO
          ? t("catalog.alsoAvailableAsEbook")
          : t("catalog.alsoAvailableAsEbookViaMetisLib")}
      </Link>
    </p>
  )
}
