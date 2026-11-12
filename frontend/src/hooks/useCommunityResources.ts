/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery } from "@tanstack/react-query"
import { getCommunityResources } from "@/api/domains/services/community-resources-api"

export function useCommunityResources(pageContext: string) {
  return useQuery({
    queryKey: ["community-resources", pageContext],
    queryFn: () => getCommunityResources(pageContext),
    staleTime: 5 * 60 * 1000,
    select: (data) => data.categories,
  })
}
