/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useState } from 'react'
import { useTranslation } from '@/i18n'
import { listSignalCandidates } from '@/api/acquisitionRationale'
import type { SignalCandidate } from '@/types/acquisitionRationale'

export interface SignalLinkSelectorProps {
  catalogItemId: number
  allowedTable: string
  selectedTable: string | null
  selectedId: number | null
  onSelect: (table: string | null, id: number | null) => void
}

export function SignalLinkSelector({
  catalogItemId,
  allowedTable,
  selectedTable,
  selectedId,
  onSelect,
}: SignalLinkSelectorProps): React.ReactElement {
  const { t } = useTranslation()
  const [candidates, setCandidates] = useState<SignalCandidate[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    listSignalCandidates(catalogItemId)
      .then((c) => {
        if (cancelled) return
        setCandidates(c.filter((x) => x.table_name === allowedTable))
      })
      .catch(() => {
        /* swallow; render no-candidates state */
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [catalogItemId, allowedTable])

  return (
    <fieldset className="border border-lsc-border dark:border-earth-700 rounded-xl p-3">
      <legend className="px-2 text-sm font-medium text-lsc-dark dark:text-lsc-cream/80">
        {t('acquisitionRationale.signalCandidatesHeader')}
      </legend>
      {loading && (
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          {t('acquisitionRationale.saving')}
        </p>
      )}
      {!loading && candidates.length === 0 && (
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          {t('acquisitionRationale.noCandidates')}
        </p>
      )}
      <div className="space-y-1">
        {candidates.map((c) => (
          <label
            key={`${c.table_name}-${c.record_id}`}
            className="flex items-start gap-2 text-sm text-lsc-dark dark:text-lsc-cream py-1 cursor-pointer"
          >
            <input
              type="radio"
              name="signal-ref"
              checked={selectedTable === c.table_name && selectedId === c.record_id}
              onChange={() => onSelect(c.table_name, c.record_id)}
              className="mt-1 w-4 h-4 border-lsc-border text-lsc-rose focus:ring-2 focus:ring-lsc-rose"
            />
            <span>
              {c.summary} ({c.matched_on})
            </span>
          </label>
        ))}
      </div>
      {selectedId !== null && (
        <button
          type="button"
          onClick={() => onSelect(null, null)}
          className="mt-2 text-sm text-lsc-rose hover:underline"
        >
          {t('acquisitionRationale.clearSignal')}
        </button>
      )}
    </fieldset>
  )
}
