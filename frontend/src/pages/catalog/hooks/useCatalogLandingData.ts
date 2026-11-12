/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery } from '@tanstack/react-query'
import { fetchApi } from '@/api/fetchApi'

export interface ReadingListSummary {
  id: number
  name: string
  description?: string
  item_count?: number
  creator?: { name: string }
}

export function useCatalogLandingData() {
  const { data: readingLists } = useQuery({
    queryKey: ['public-reading-lists'],
    queryFn: async () => {
      const json = await fetchApi('/reading-lists/public?sort=alphabetical&per_page=10')
      return json.data as ReadingListSummary[]
    },
    staleTime: 300_000,
  })

  return { readingLists }
}
