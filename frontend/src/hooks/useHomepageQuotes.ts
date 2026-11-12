/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery } from "@tanstack/react-query"
import { getHomepageQuotes } from "@/api/domains/services/homepage-quotes-api"

export function useHomepageQuotes(locale: string) {
  return useQuery({
    queryKey: ["homepage-quotes", locale],
    queryFn: () => getHomepageQuotes(locale),
    staleTime: 5 * 60 * 1000,
  })
}
