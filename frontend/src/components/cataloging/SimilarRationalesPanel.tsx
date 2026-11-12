/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import { useTranslation } from '@/i18n'
import { useDebounce } from '@/hooks/useDebounce'
import {
  findSimilarRationales,
  type SimilarRationaleHit,
} from '@/api/acquisitionRationale'

const MIN_QUERY_CHARS = 8

export interface SimilarRationalesPanelProps {
  query: string
}

function pickPrimaryUseCase(hit: {
  metadata?: Record<string, unknown>
  tags?: string[]
}): string | undefined {
  // Prefer structured metadata if present (cleaner contract)
  const mp = hit.metadata?.primary_use_case
  if (typeof mp === 'string' && mp.length > 0) return mp

  // Fall back to namespaced tag prefix (durable across tag-order changes)
  const META_PREFIX = 'meta:primary_use_case:'
  const fromMeta = (hit.tags ?? []).find((t) => t.startsWith(META_PREFIX))
  if (fromMeta) return fromMeta.slice(META_PREFIX.length)

  return undefined
}

export function SimilarRationalesPanel({
  query,
}: SimilarRationalesPanelProps): React.ReactElement | null {
  const { t } = useTranslation()
  const debouncedQuery = useDebounce(query, 300)
  const [hits, setHits] = useState<SimilarRationaleHit[]>([])
  const [loading, setLoading] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)

  useEffect(() => {
    const trimmed = (debouncedQuery ?? '').trim()
    if (trimmed.length < MIN_QUERY_CHARS) {
      setHits([])
      setHasSearched(false)
      return
    }

    let cancelled = false
    setLoading(true)
    findSimilarRationales(trimmed)
      .then((resp) => {
        if (cancelled) return
        setHits(Array.isArray(resp?.hits) ? resp.hits : [])
        setHasSearched(true)
      })
      .catch((err: unknown) => {
        // Backend is best-effort; a real 500 here is rare. Log + render empty.
        if (cancelled) return

        console.warn('findSimilarRationales failed:', err)
        setHits([])
        setHasSearched(true)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [debouncedQuery])

  // Hide the panel entirely until staff has typed enough to query.
  const trimmedDebounced = (debouncedQuery ?? '').trim()
  if (trimmedDebounced.length < MIN_QUERY_CHARS) return null

  return (
    <section
      aria-live="polite"
      aria-busy={loading}
      className="rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-cream/40 dark:bg-lsc-brown/40 p-3"
    >
      <h3 className="text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
        {t('acquisitionRationale.similar.title')}
      </h3>

      {loading && (
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          {t('acquisitionRationale.similar.searching')}
        </p>
      )}

      {!loading && hasSearched && hits.length === 0 && (
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          {t('acquisitionRationale.similar.empty')}
        </p>
      )}

      {!loading && hits.length > 0 && (
        <ul className="space-y-2">
          {hits.map((hit, idx) => {
            const useCase = pickPrimaryUseCase(hit)
            const key = hit.aku_id ?? `hit-${idx}`
            return (
              <li
                key={key}
                className="rounded-lg border border-lsc-border/60 dark:border-earth-700/60 bg-lsc-white dark:bg-lsc-brown p-2"
              >
                {hit.title && (
                  <strong className="block text-sm text-lsc-dark dark:text-lsc-cream">
                    {hit.title}
                  </strong>
                )}
                {hit.body && (
                  <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80 mt-1">
                    {hit.body}
                  </p>
                )}
                {useCase && (
                  <small className="block text-xs text-lsc-dark/60 dark:text-lsc-cream/60 mt-1">
                    {t('acquisitionRationale.similar.primaryUseCase', {
                      slug: useCase,
                    })}
                  </small>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
