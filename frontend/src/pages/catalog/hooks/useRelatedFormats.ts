/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery } from '@tanstack/react-query'
import { searchCatalog, type CatalogItem, type ItemType } from '@/api/api'
import { normalizeWorkKey as normalize } from '../utils/workMatch'

export interface FormatVariant {
  id: number
  item_type: ItemType
  status: string
  is_large_print: boolean
  location: string | null
  label: string
  isCurrent: boolean
  page_count: number | null
  runtime_minutes: number | null
}

const FORMAT_LABELS: Record<string, string> = {
  book: 'Book',
  ebook: 'E-Book',
  audiobook: 'Audiobook',
  dvd: 'DVD',
  bluray: 'Blu-ray',
  cd: 'CD',
  vinyl: 'Vinyl',
  magazine: 'Magazine',
  game: 'Video Game',
  equipment: 'Equipment',
  kit: 'Kit',
  other: 'Other',
}

export function useRelatedFormats(item: CatalogItem | undefined) {
  const hasAuthor = !!item?.author?.trim()

  const { data, isLoading } = useQuery({
    queryKey: ['related-formats', item?.id],
    queryFn: async () => {
      if (!item?.title) return []
      const result = await searchCatalog({ query: item.title, per_page: 20 })
      return result.items
    },
    enabled: !!item?.id && hasAuthor,
    staleTime: 60_000,
  })

  // Filter to same work by matching author, then group by item_type
  const formats: FormatVariant[] = []
  const seenTypes = new Set<string>()

  if (item) {
    // Always include current item first
    seenTypes.add(item.item_type)
    formats.push({
      id: item.id,
      item_type: item.item_type,
      status: item.status,
      is_large_print: item.is_large_print,
      location: item.location,
      label: FORMAT_LABELS[item.item_type] || item.item_type,
      isCurrent: true,
      page_count: item.page_count ?? null,
      runtime_minutes: item.runtime_minutes ?? null,
    })

    if (data && hasAuthor) {
      // No work-level id is exposed on CatalogItem, so "same work" means
      // exact normalized title AND author. Substring matching here previously
      // fed wrong-work formats into the hold modal.
      const titleKey = normalize(item.title)
      const authorKey = normalize(item.author)

      // Group by item_type, pick best per type (prefer available)
      const byType = new Map<string, CatalogItem[]>()
      for (const candidate of data) {
        if (candidate.id === item.id) continue
        if (normalize(candidate.title) !== titleKey) continue
        if (normalize(candidate.author) !== authorKey) continue

        const existing = byType.get(candidate.item_type) || []
        existing.push(candidate)
        byType.set(candidate.item_type, existing)
      }

      for (const [type, candidates] of byType) {
        if (seenTypes.has(type)) continue
        seenTypes.add(type)

        // Prefer available copies
        const sorted = candidates.sort((a, b) => {
          if (a.status === 'available' && b.status !== 'available') return -1
          if (b.status === 'available' && a.status !== 'available') return 1
          return 0
        })

        const best = sorted[0]
        if (best) {
          formats.push({
            id: best.id,
            item_type: best.item_type as ItemType,
            status: best.status,
            is_large_print: best.is_large_print,
            location: best.location,
            label: FORMAT_LABELS[best.item_type] || best.item_type,
            isCurrent: false,
            page_count: best.page_count ?? null,
            runtime_minutes: best.runtime_minutes ?? null,
          })
        }
      }
    }
  }

  return {
    formats,
    isLoading,
    currentFormat: formats.find((f) => f.isCurrent) ?? null,
  }
}
