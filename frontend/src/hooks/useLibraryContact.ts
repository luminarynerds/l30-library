/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery } from '@tanstack/react-query'
import { listBranches } from '@/api/branch-api'
import { useBranding } from '@/contexts/BrandingContext'
import { resolveLibraryContact } from '@/utils/libraryContact'

/** One cached operational contact profile for the homepage and footer. */
export function useLibraryContact() {
  const branding = useBranding()
  const { data: branches } = useQuery({
    queryKey: ['branches-main'],
    queryFn: () => listBranches({ active_only: true }),
    staleTime: 300_000,
  })
  return resolveLibraryContact(branding, branches)
}
