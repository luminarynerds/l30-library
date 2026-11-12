/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useTranslation } from '@/i18n/I18nContext'
import { getAccessToken } from '@/utils/tokenStore'

const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1'

interface Result {
  matched: number
  updated: number
  skipped_invalid: number
  skipped_no_match: number
  invalid_rows: { isbn: string; lexile: string; error: string }[]
  no_match_rows: string[]
}

export default function StaffLexileBulkImportPage(): JSX.Element {
  const { t } = useTranslation()
  const [file, setFile] = useState<File | null>(null)
  const [result, setResult] = useState<Result | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!file) return
    setBusy(true)
    setError(null)
    setResult(null)
    const fd = new FormData()
    fd.append('file', file)
    try {
      const token = getAccessToken()
      // eslint-disable-next-line no-restricted-syntax -- multipart FormData upload; fetchApi forces application/json
      const r = await fetch(`${API_BASE}/catalog/lexile/bulk-import`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: fd,
      })
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      setResult(await r.json())
    } catch {
      setError(t('staff_lexile_bulk_error'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="container mx-auto px-4 py-6 max-w-2xl">
      <h1 className="text-2xl font-bold mb-2">{t('staff_lexile_bulk_title')}</h1>
      <p className="mb-4">{t('staff_lexile_bulk_intro')}</p>
      <form onSubmit={onSubmit} className="space-y-3">
        <label className="block">
          <span className="text-sm font-medium">{t('staff_lexile_bulk_upload')}</span>
          <input
            type="file"
            accept=".csv,text/csv"
            aria-label={t('staff_lexile_bulk_upload')}
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="mt-1 block"
          />
        </label>
        <button
          type="submit"
          disabled={!file || busy}
          className="rounded bg-category-600 text-white px-3 py-1 disabled:opacity-50"
        >
          {t('staff_lexile_bulk_submit')}
        </button>
      </form>
      {error && <p role="alert" className="mt-3 text-red-600">{error}</p>}
      {result && (
        <section aria-live="polite" className="mt-4">
          <p>{t('staff_lexile_bulk_result', result as unknown as Record<string, unknown>)}</p>
          {result.invalid_rows.length > 0 && (
            <details className="mt-2">
              <summary>Invalid rows ({result.invalid_rows.length})</summary>
              <ul className="text-sm">
                {result.invalid_rows.map((r) => (
                  <li key={`${r.isbn}-${r.lexile}`}>
                    {r.isbn}: {r.lexile} — {r.error}
                  </li>
                ))}
              </ul>
            </details>
          )}
          {result.no_match_rows.length > 0 && (
            <details className="mt-2">
              <summary>Unmatched ISBNs ({result.no_match_rows.length})</summary>
              <ul className="text-sm">
                {result.no_match_rows.map((i) => (
                  <li key={i}>{i}</li>
                ))}
              </ul>
            </details>
          )}
        </section>
      )}
    </main>
  )
}
