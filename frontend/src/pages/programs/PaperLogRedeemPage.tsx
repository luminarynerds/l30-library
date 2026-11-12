/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Plus, Trash2 } from 'lucide-react'

import {
  PaperLogRedeemEntry,
  PaperLogRedeemResponse,
  redeemPaperLog,
} from '@/api/domains/content/reading-programs-api'
import { useAuth } from '@/contexts/AuthContext'
import { isApiError } from '@/lib/api-client'
import { t } from '@/i18n'

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

function makeEmptyEntry(): PaperLogRedeemEntry {
  return {
    entry_date: todayIso(),
    title: '',
    author: '',
    books_read: 0,
    minutes_read: 0,
  }
}

export default function PaperLogRedeemPage(): React.ReactElement {
  const [searchParams] = useSearchParams()
  const initialCode = (searchParams.get('code') || '').toUpperCase().slice(0, 8)
  const { token } = useAuth()

  const [code, setCode] = useState(initialCode)
  const [entries, setEntries] = useState<PaperLogRedeemEntry[]>([makeEmptyEntry()])
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<PaperLogRedeemResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (initialCode && code === '') setCode(initialCode)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialCode])

  const canSubmit = useMemo(
    () => code.length === 8 && entries.length > 0 && !submitting,
    [code, entries, submitting],
  )

  const updateEntry = (idx: number, patch: Partial<PaperLogRedeemEntry>) => {
    setEntries((prev) => prev.map((e, i) => (i === idx ? { ...e, ...patch } : e)))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!token) {
      setError(t('programs.redeem.signInRequired') || 'Please sign in to redeem a code.')
      return
    }
    setError(null)
    setSubmitting(true)
    try {
      const res = await redeemPaperLog(token, {
        code: code.trim().toUpperCase(),
        entries: entries.map((entry) => ({
          ...entry,
          title: entry.title || undefined,
          author: entry.author || undefined,
        })),
      })
      setResult(res)
    } catch (err) {
      if (isApiError(err)) {
        if (err.status === 404) {
          setError(t('programs.redeem.codeNotFound') || 'Code not found.')
        } else if (err.status === 409) {
          setError(t('programs.redeem.alreadyRedeemed') || 'Code already redeemed.')
        } else if (err.status === 410) {
          setError(t('programs.redeem.codeExpired') || 'Code expired.')
        } else {
          setError(err.detail || 'Redemption failed.')
        }
      } else {
        setError(err instanceof Error ? err.message : 'Redemption failed.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  if (result) {
    return (
      <main className="max-w-2xl mx-auto p-6">
        <h1 className="text-2xl font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
          {t('programs.redeem.success') || 'Reading log credited'}
        </h1>
        <div className="p-4 bg-lsc-cream dark:bg-lsc-brown/30 rounded-xl space-y-2">
          <div>
            <strong>{result.entries_created}</strong>{' '}
            {t('programs.redeem.entriesCreated') || 'entries added.'}
          </div>
          <div>
            {t('programs.redeem.goalPercent') || 'Goal progress'}:{' '}
            <strong>{result.goal_percent.toFixed(1)}%</strong>
          </div>
          {result.new_achievements > 0 && (
            <div>
              <strong>{result.new_achievements}</strong>{' '}
              {t('programs.redeem.newAchievements') || 'new badge(s) earned!'}
            </div>
          )}
        </div>
      </main>
    )
  }

  return (
    <main className="max-w-2xl mx-auto p-6">
      <h1 className="text-2xl font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
        {t('programs.redeem.title') || 'Redeem a paper reading log'}
      </h1>
      <form onSubmit={handleSubmit} className="space-y-5" aria-label="Redeem reading log form">
        <div>
          <label htmlFor="paperlog-code" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
            {t('programs.redeem.codeLabel') || 'Claim code'}
          </label>
          <input
            id="paperlog-code"
            type="text"
            maxLength={8}
            value={code}
            onChange={(e) => setCode(e.target.value.toUpperCase().slice(0, 8))}
            className="w-full px-3 py-2 min-h-[44px] border-2 border-lsc-border dark:border-earth-700 rounded-xl font-mono text-lg tracking-widest bg-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
            placeholder="ABCD1234"
            required
            aria-required="true"
          />
        </div>

        <div className="space-y-4">
          {entries.map((entry, idx) => (
            <fieldset key={idx} className="p-3 border border-lsc-border dark:border-earth-700 rounded-xl space-y-2">
              <legend className="text-xs px-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                Entry {idx + 1}
              </legend>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <label className="block text-sm">
                  <span className="block text-lsc-dark/70 dark:text-lsc-cream/70">
                    {t('programs.redeem.entryDate') || 'Date'}
                  </span>
                  <input
                    type="date"
                    value={entry.entry_date}
                    onChange={(e) => updateEntry(idx, { entry_date: e.target.value })}
                    className="w-full px-2 py-1 min-h-[40px] border border-lsc-border dark:border-earth-700 rounded-lg bg-white dark:bg-earth-800"
                    required
                  />
                </label>
                <label className="block text-sm">
                  <span className="block text-lsc-dark/70 dark:text-lsc-cream/70">
                    {t('programs.redeem.entryQuantity') || 'Books / Minutes / Pages'}
                  </span>
                  <div className="flex gap-1">
                    <input
                      type="number"
                      min={0}
                      placeholder="books"
                      value={entry.books_read ?? 0}
                      onChange={(e) => updateEntry(idx, { books_read: Number(e.target.value) || 0 })}
                      aria-label={`Entry ${idx + 1} books read`}
                      className="w-full px-2 py-1 min-h-[40px] border border-lsc-border dark:border-earth-700 rounded-lg bg-white dark:bg-earth-800"
                    />
                    <input
                      type="number"
                      min={0}
                      max={120}
                      placeholder="min"
                      value={entry.minutes_read ?? 0}
                      onChange={(e) => updateEntry(idx, { minutes_read: Number(e.target.value) || 0 })}
                      aria-label={`Entry ${idx + 1} minutes read`}
                      className="w-full px-2 py-1 min-h-[40px] border border-lsc-border dark:border-earth-700 rounded-lg bg-white dark:bg-earth-800"
                    />
                    <input
                      type="number"
                      min={0}
                      placeholder="pages"
                      value={entry.pages_read ?? 0}
                      onChange={(e) => updateEntry(idx, { pages_read: Number(e.target.value) || 0 })}
                      aria-label={`Entry ${idx + 1} pages read`}
                      className="w-full px-2 py-1 min-h-[40px] border border-lsc-border dark:border-earth-700 rounded-lg bg-white dark:bg-earth-800"
                    />
                  </div>
                </label>
                <label className="block text-sm">
                  <span className="block text-lsc-dark/70 dark:text-lsc-cream/70">
                    {t('programs.redeem.entryTitle') || 'Title'}
                  </span>
                  <input
                    type="text"
                    value={entry.title ?? ''}
                    onChange={(e) => updateEntry(idx, { title: e.target.value })}
                    className="w-full px-2 py-1 min-h-[40px] border border-lsc-border dark:border-earth-700 rounded-lg bg-white dark:bg-earth-800"
                  />
                </label>
                <label className="block text-sm">
                  <span className="block text-lsc-dark/70 dark:text-lsc-cream/70">
                    {t('programs.redeem.entryAuthor') || 'Author'}
                  </span>
                  <input
                    type="text"
                    value={entry.author ?? ''}
                    onChange={(e) => updateEntry(idx, { author: e.target.value })}
                    className="w-full px-2 py-1 min-h-[40px] border border-lsc-border dark:border-earth-700 rounded-lg bg-white dark:bg-earth-800"
                  />
                </label>
              </div>
              {entries.length > 1 && (
                <button
                  type="button"
                  onClick={() => setEntries((prev) => prev.filter((_, i) => i !== idx))}
                  className="inline-flex items-center gap-1 text-sm text-status-danger-600 hover:text-status-danger-700"
                >
                  <Trash2 className="w-4 h-4" aria-hidden="true" />
                  Remove
                </button>
              )}
            </fieldset>
          ))}
        </div>

        <button
          type="button"
          onClick={() => setEntries((prev) => [...prev, makeEmptyEntry()])}
          className="inline-flex items-center gap-2 px-3 py-2 min-h-[44px] border border-lsc-border dark:border-earth-700 rounded-xl text-sm text-lsc-dark dark:text-lsc-cream"
        >
          <Plus className="w-4 h-4" aria-hidden="true" />
          {t('programs.redeem.addEntry') || 'Add another entry'}
        </button>

        {error && (
          <div role="alert" className="px-3 py-2 bg-status-danger-50 dark:bg-status-danger-900/20 text-status-danger-700 dark:text-status-danger-400 rounded-xl text-sm">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={!canSubmit}
          className="w-full px-4 py-3 min-h-[48px] bg-lsc-rose hover:bg-lsc-rose/90 disabled:opacity-60 text-white rounded-xl shadow-md hover:shadow-lg font-semibold"
        >
          {submitting
            ? '...'
            : t('programs.redeem.submit') || 'Submit reading log'}
        </button>
      </form>
    </main>
  )
}
