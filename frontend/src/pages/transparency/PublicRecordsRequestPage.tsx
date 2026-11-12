/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useTranslation } from '@/i18n'
import {
  submitPublicRecordsRequest,
  getPublicDisclosureLog,
  type PublicRecordsDisclosureLogEntry,
} from '@/api/public-records-api'
import { TurnstileWidget } from "@/components/TurnstileWidget"
import PageContainer from '@/components/layout/PageContainer'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface FormState {
  requester_name: string
  requester_email: string
  description: string
  preferred_format: string
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function isValidEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  } catch {
    return iso
  }
}

// ---------------------------------------------------------------------------
// Subcomponents
// ---------------------------------------------------------------------------

function SuccessCard({
  trackingNumber,
  deadline,
  t,
}: {
  trackingNumber: string
  deadline: string
  t: (key: string, vars?: Record<string, string>) => string
}) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="rounded-lg border border-green-300 bg-green-50 p-6 dark:border-green-700 dark:bg-green-950"
    >
      <h2 className="mb-2 text-lg font-semibold text-green-800 dark:text-green-200">
        {t('publicRecords.form.successTitle')}
      </h2>
      <p className="text-green-700 dark:text-green-300">
        {t('publicRecords.form.successBody', {
          trackingNumber,
          deadline: formatDate(deadline),
        })}
      </p>
    </div>
  )
}

function DisclosureLog({
  t,
}: {
  t: (key: string, vars?: Record<string, string>) => string
}) {
  const currentYear = new Date().getFullYear()
  const [year, setYear] = useState(currentYear)
  const [entries, setEntries] = useState<PublicRecordsDisclosureLogEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [expanded, setExpanded] = useState<number | null>(null)

  useEffect(() => {
    setLoading(true)
    getPublicDisclosureLog(year)
      .then(setEntries)
      .catch(() => setEntries([]))
      .finally(() => setLoading(false))
  }, [year])

  const years = Array.from({ length: 5 }, (_, i) => currentYear - i)

  return (
    <section aria-labelledby="log-heading" className="mt-12">
      <div className="mb-4 flex items-center gap-4">
        <h2 id="log-heading" className="text-xl font-semibold">
          {t('publicRecords.log.heading')}
        </h2>
        <label className="flex items-center gap-2 text-sm">
          {t('publicRecords.log.yearLabel')}
          <select
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
            className="rounded border px-2 py-1 text-sm dark:bg-gray-800"
          >
            {years.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </label>
      </div>

      {loading && (
        <p className="text-sm text-gray-600 dark:text-gray-400" aria-live="polite">
          Loading…
        </p>
      )}

      {!loading && entries.length === 0 && (
        <p className="text-sm text-gray-600 dark:text-gray-400" aria-live="polite">
          {t('publicRecords.log.noRecords', { year: String(year) })}
        </p>
      )}

      {!loading && entries.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b text-xs uppercase text-gray-600 dark:text-gray-400">
                <th scope="col" className="py-2 pr-4">
                  {t('publicRecords.log.columns.tracking')}
                </th>
                <th scope="col" className="py-2 pr-4">
                  {t('publicRecords.log.columns.dateReceived')}
                </th>
                <th scope="col" className="py-2 pr-4">
                  {t('publicRecords.log.columns.status')}
                </th>
                <th scope="col" className="py-2">
                  {t('publicRecords.log.columns.description')}
                </th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <>
                  <tr
                    key={entry.id}
                    className="border-b hover:bg-gray-50 dark:hover:bg-gray-800/50"
                  >
                    <td className="py-2 pr-4 font-mono text-xs">
                      {entry.tracking_number}
                    </td>
                    <td className="py-2 pr-4 whitespace-nowrap">
                      {formatDate(entry.date_received)}
                    </td>
                    <td className="py-2 pr-4 capitalize">
                      {entry.status.replace(/_/g, ' ')}
                    </td>
                    <td className="py-2">
                      <span className="line-clamp-2">
                        {entry.description}
                      </span>
                      {entry.description.length > 100 && (
                        <button
                          type="button"
                          onClick={() =>
                            setExpanded(expanded === entry.id ? null : entry.id)
                          }
                          className="ml-2 text-xs text-blue-600 underline dark:text-blue-400"
                          aria-expanded={expanded === entry.id}
                        >
                          {expanded === entry.id
                            ? t('publicRecords.log.collapseRow')
                            : t('publicRecords.log.expandRow')}
                        </button>
                      )}
                    </td>
                  </tr>
                  {expanded === entry.id && (
                    <tr key={`${entry.id}-expand`} className="border-b bg-gray-50 dark:bg-gray-800/30">
                      <td colSpan={4} className="px-4 py-3 text-sm">
                        <p className="whitespace-pre-wrap">{entry.description}</p>
                        {entry.response_summary && (
                          <p className="mt-2 text-gray-600 dark:text-gray-400">
                            <strong>Summary:</strong> {entry.response_summary}
                          </p>
                        )}
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function PublicRecordsRequestPage() {
  const { t } = useTranslation()
  const [searchParams] = useSearchParams()

  const meetingId = searchParams.get('meeting_id')
    ? Number(searchParams.get('meeting_id'))
    : null
  const committeeId = searchParams.get('committee_id')
    ? Number(searchParams.get('committee_id'))
    : null

  const [form, setForm] = useState<FormState>({
    requester_name: '',
    requester_email: '',
    description: '',
    preferred_format: 'digital',
  })
  const [errors, setErrors] = useState<Partial<FormState>>({})
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [submitted, setSubmitted] = useState<{
    trackingNumber: string
    deadline: string
  } | null>(null)
  const [turnstileToken, setTurnstileToken] = useState('')

  function validate(): boolean {
    const next: Partial<FormState> = {}
    if (!form.requester_name.trim()) next.requester_name = 'Required'
    if (!isValidEmail(form.requester_email)) next.requester_email = 'Valid email required'
    if (form.description.trim().length < 10)
      next.description = 'Please provide at least 10 characters'
    setErrors(next)
    return Object.keys(next).length === 0
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!validate()) return
    setSubmitting(true)
    setSubmitError(null)
    try {
      const ack = await submitPublicRecordsRequest({
        ...form,
        meeting_id: meetingId,
        committee_id: committeeId,
        turnstile_token: turnstileToken || 'unverified',
      })
      setSubmitted({ trackingNumber: ack.tracking_number, deadline: ack.response_deadline })
    } catch (err: unknown) {
      const msg =
        err && typeof err === 'object' && 'message' in err
          ? String((err as { message: unknown }).message)
          : 'Unexpected error'
      setSubmitError(msg)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <PageContainer className="py-8">
      <h1 className="mb-2 text-2xl font-bold">{t('publicRecords.pageTitle')}</h1>
      <p className="mb-8 text-gray-600 dark:text-gray-400">{t('publicRecords.pageIntro')}</p>

      {/* Context chip for meeting/committee link */}
      {(meetingId || committeeId) && !submitted && (
        <div className="mb-6 flex items-center gap-3 rounded-lg bg-blue-50 px-4 py-3 text-sm dark:bg-blue-950">
          {meetingId && (
            <span>
              {t('publicRecords.form.fromMeetingPrefix')} meeting #{meetingId}
            </span>
          )}
          {committeeId && (
            <span>
              {t('publicRecords.form.fromCommitteePrefix')} committee #{committeeId}
            </span>
          )}
        </div>
      )}

      {/* Success state */}
      {submitted ? (
        <SuccessCard
          trackingNumber={submitted.trackingNumber}
          deadline={submitted.deadline}
          t={t}
        />
      ) : (
        <form onSubmit={handleSubmit} noValidate aria-label="Public records request form">
          {/* Global error */}
          {submitError && (
            <div
              role="alert"
              aria-live="assertive"
              className="mb-4 rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-700 dark:bg-red-950 dark:text-red-300"
            >
              {t('publicRecords.form.errorTitle')}: {submitError}
            </div>
          )}

          {/* Name */}
          <div className="mb-4">
            <label htmlFor="requester_name" className="mb-1 block text-sm font-medium">
              {t('publicRecords.form.nameLabel')}
            </label>
            <input
              id="requester_name"
              type="text"
              value={form.requester_name}
              onChange={(e) => setForm((f) => ({ ...f, requester_name: e.target.value }))}
              aria-describedby={errors.requester_name ? 'name-error' : undefined}
              aria-invalid={!!errors.requester_name}
              className="w-full rounded border px-3 py-2 dark:bg-gray-800"
              autoComplete="name"
            />
            {errors.requester_name && (
              <p id="name-error" className="mt-1 text-xs text-red-600" role="alert">
                {errors.requester_name}
              </p>
            )}
          </div>

          {/* Email */}
          <div className="mb-4">
            <label htmlFor="requester_email" className="mb-1 block text-sm font-medium">
              {t('publicRecords.form.emailLabel')}
            </label>
            <input
              id="requester_email"
              type="email"
              value={form.requester_email}
              onChange={(e) => setForm((f) => ({ ...f, requester_email: e.target.value }))}
              aria-describedby={errors.requester_email ? 'email-error' : undefined}
              aria-invalid={!!errors.requester_email}
              className="w-full rounded border px-3 py-2 dark:bg-gray-800"
              autoComplete="email"
            />
            {errors.requester_email && (
              <p id="email-error" className="mt-1 text-xs text-red-600" role="alert">
                {errors.requester_email}
              </p>
            )}
          </div>

          {/* Description */}
          <div className="mb-4">
            <label htmlFor="description" className="mb-1 block text-sm font-medium">
              {t('publicRecords.form.descriptionLabel')}
            </label>
            <p className="mb-1 text-xs text-gray-600 dark:text-gray-400">{t('publicRecords.form.descriptionHelp')}</p>
            <textarea
              id="description"
              rows={5}
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
              aria-describedby={
                errors.description ? 'desc-error' : 'desc-help'
              }
              aria-invalid={!!errors.description}
              className="w-full rounded border px-3 py-2 dark:bg-gray-800"
              maxLength={4000}
            />
            {errors.description && (
              <p id="desc-error" className="mt-1 text-xs text-red-600" role="alert">
                {errors.description}
              </p>
            )}
          </div>

          {/* Preferred format */}
          <fieldset className="mb-6">
            <legend className="mb-2 text-sm font-medium">
              {t('publicRecords.form.preferredFormatLabel')}
            </legend>
            {[
              { value: 'digital', label: t('publicRecords.form.preferredFormatDigital') },
              { value: 'paper', label: t('publicRecords.form.preferredFormatPaper') },
              { value: 'either', label: t('publicRecords.form.preferredFormatEither') },
            ].map(({ value, label }) => (
              <label key={value} className="mb-1 flex items-center gap-2 text-sm">
                <input
                  type="radio"
                  name="preferred_format"
                  value={value}
                  checked={form.preferred_format === value}
                  onChange={() => setForm((f) => ({ ...f, preferred_format: value }))}
                />
                {label}
              </label>
            ))}
          </fieldset>

          <div className="mb-4">
            <TurnstileWidget onVerify={setTurnstileToken} />
          </div>

          <button
            type="submit"
            disabled={submitting || !turnstileToken}
            className="rounded bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {submitting
              ? t('publicRecords.form.submitting')
              : t('publicRecords.form.submitButton')}
          </button>
        </form>
      )}

      <DisclosureLog t={t} />
    </PageContainer>
  )
}
