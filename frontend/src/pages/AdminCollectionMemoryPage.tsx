/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import { useTranslation } from '@/i18n'
import { api, isApiError } from '@/lib/api-client'

interface Row {
  year_acquired: string | null
  primary_use_case_slug: string
  weeding_condition: string
  item_count: number
  anticipated_count: number
  patron_visible_count: number
}

interface CollectionMemoryResponse {
  rows: Row[]
}

export default function AdminCollectionMemoryPage(): React.ReactElement {
  const { t } = useTranslation()
  const [rows, setRows] = useState<Row[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    api
      .get<CollectionMemoryResponse>('/staff/collection-memory/annual')
      .then((body) => {
        if (!cancelled) setRows(body.rows)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setError(isApiError(err) ? err.message : String(err))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <main>
      <h1>{t('collectionMemory.title')}</h1>
      <p>{t('collectionMemory.subtitle')}</p>
      {/* Persistent live region: survives the loading/results swap below so
          screen readers get one announcement instead of a torn-down node */}
      <p role="status" aria-live="polite" className="sr-only">
        {loading ? t('collectionMemory.loading') : t('collectionMemory.resultCount', { count: String(rows.length) })}
      </p>
      {loading && <p>{t('collectionMemory.loading')}</p>}
      {error && <p role="alert">{error}</p>}
      {!loading && rows.length === 0 && !error && (
        <p>{t('collectionMemory.empty')}</p>
      )}
      {rows.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>{t('collectionMemory.colYear')}</th>
              <th>{t('collectionMemory.colUseCase')}</th>
              <th>{t('collectionMemory.colWeeding')}</th>
              <th>{t('collectionMemory.colItems')}</th>
              <th>{t('collectionMemory.colAnticipated')}</th>
              <th>{t('collectionMemory.colPatronVisible')}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                <td>{r.year_acquired ?? '--'}</td>
                <td>{r.primary_use_case_slug}</td>
                <td>{r.weeding_condition}</td>
                <td>{r.item_count}</td>
                <td>{r.anticipated_count}</td>
                <td>{r.patron_visible_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  )
}
