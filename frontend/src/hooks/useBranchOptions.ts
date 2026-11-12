/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Shared branch dropdown data for FairScheduling pages. Branch listing is
 * token-free (api-client injects the access token), so this hook needs no
 * auth wiring from callers.
 */
import { useEffect, useState } from 'react'
import { listBranches, type Branch } from '@/api/branch-api'

export interface UseBranchOptionsResult {
  branches: Branch[]
  loading: boolean
  error: string | null
}

export function useBranchOptions(): UseBranchOptionsResult {
  const [branches, setBranches] = useState<Branch[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    listBranches({ active_only: true })
      .then(data => {
        if (cancelled) return
        setBranches(Array.isArray(data) ? data : [])
      })
      .catch((e: unknown) => {
        if (cancelled) return
        setError(e instanceof Error ? e.message : 'Failed to load branches')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  return { branches, loading, error }
}
