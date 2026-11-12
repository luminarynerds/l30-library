/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery } from "@tanstack/react-query"
import { unifiedSearch } from "@/api/domains/catalog/unified-search-api"
import type { CatalogItem } from "@/api/api"
import { normalizeWorkKey } from "../utils/workMatch"

export interface IndieEbookMatch {
  ebookId: number
  title: string
}

/**
 * Looks for the same work as an indie (MetisLib) ebook so the item page can
 * point to it when the physical copy is checked out / on hold. This does not
 * assert the patron can borrow it now -- lending is license-gated per library
 * and the search response exposes no per-title borrowable signal -- so the
 * affordance only links out; it never promises immediacy.
 *
 * Same-work means exact normalized title AND author (workMatch.ts) -- the
 * unified search service never populates related_sources, so one targeted
 * indie-source query is the only reliable cross-source signal. A missing
 * author disables the lookup entirely: title-only matching hands patrons
 * the wrong book.
 */
export function useIndieEbookMatch(item: CatalogItem | undefined) {
  const physicalUnavailable =
    item?.status === "checked_out" || item?.status === "on_hold"
  const isEbookAlready = item?.item_type === "ebook"
  const hasAuthor = !!item?.author?.trim()

  const { data, isLoading } = useQuery({
    queryKey: ["indie-ebook-match", item?.id],
    queryFn: async (): Promise<IndieEbookMatch | null> => {
      if (!item?.title) return null
      const response = await unifiedSearch({
        query: item.title,
        sources: ["indie"],
        formats: ["ebook"],
        limit: 50,
      })

      const titleKey = normalizeWorkKey(item.title)
      const authorKey = normalizeWorkKey(item.author)

      const match = response.results.find(
        (r) =>
          r.source === "indie" &&
          r.is_available &&
          normalizeWorkKey(r.title) === titleKey &&
          normalizeWorkKey(r.author) === authorKey
      )
      if (!match) return null

      const ebookId = Number(match.source_id)
      if (!Number.isFinite(ebookId) || ebookId <= 0) return null
      return { ebookId, title: match.title }
    },
    enabled: !!item?.id && physicalUnavailable && !isEbookAlready && hasAuthor,
    staleTime: 60_000,
  })

  return { match: data ?? null, isLoading }
}
