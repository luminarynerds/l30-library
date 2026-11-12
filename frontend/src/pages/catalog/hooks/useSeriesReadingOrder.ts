/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery } from '@tanstack/react-query'
import { getSeriesReadingOrder, type CatalogItem, type SeriesReadingOrder } from '@/api/api'

/**
 * Fetch the ordered list of titles we hold in this item's series.
 *
 * Only enabled when the item actually has a parsed numeric position
 * (`series_position`), since that's the precondition for showing reading-order
 * context. Items with a series_name but no parseable number fall back to the
 * plain "Part of [series]" chip in ItemHeader and never hit this endpoint.
 */
export function useSeriesReadingOrder(item: CatalogItem | undefined) {
  const enabled = !!item?.id && item.series_position != null

  const { data, isLoading } = useQuery<SeriesReadingOrder>({
    queryKey: ['series-reading-order', item?.id],
    queryFn: () => getSeriesReadingOrder(item!.id),
    enabled,
    staleTime: 60_000,
  })

  return { series: data, isLoading: enabled && isLoading }
}
