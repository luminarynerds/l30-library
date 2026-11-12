/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Public, token-gated status view of a card application (Issue #1028).
 * Reached via the link in the submission-confirmation email; not surfaced
 * in nav. NO authentication; the URL token is the gate.
 */
import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { CheckCircle, AlertCircle, Clock, XCircle, Loader2 } from 'lucide-react'

import {
  checkApplicationByToken,
  type CardApplicationPublicStatus,
} from '@/api/card-applications-api'
import { useTranslation } from '@/i18n'
import PageContainer from '@/components/layout/PageContainer'

function formatDate(iso: string | null | undefined): string {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  } catch {
    return ''
  }
}

function StatusIcon({ status }: { status: CardApplicationPublicStatus['status'] }) {
  switch (status) {
    case 'approved':
      return <CheckCircle className="h-12 w-12 text-status-success-600" aria-hidden="true" />
    case 'denied':
      return <XCircle className="h-12 w-12 text-status-danger-600" aria-hidden="true" />
    case 'under_review':
      return <Clock className="h-12 w-12 text-earth-700" aria-hidden="true" />
    case 'pending':
    default:
      return <Clock className="h-12 w-12 text-status-warning-600" aria-hidden="true" />
  }
}

function statusLabel(
  t: ReturnType<typeof useTranslation>['t'],
  status: CardApplicationPublicStatus['status'],
): string {
  switch (status) {
    case 'approved':
      return t('cardApplication.statusPage.approvedLabel', 'Approved')
    case 'denied':
      return t('cardApplication.statusPage.deniedLabel', 'Denied')
    case 'under_review':
      return t('cardApplication.statusPage.underReviewLabel', 'Under Review')
    case 'pending':
    default:
      return t('cardApplication.statusPage.pendingLabel', 'Pending Review')
  }
}

function statusBlurb(
  t: ReturnType<typeof useTranslation>['t'],
  status: CardApplicationPublicStatus['status'],
): string {
  switch (status) {
    case 'approved':
      return t(
        'cardApplication.statusPage.approvedBlurb',
        "Your application was approved. Watch your email for next steps — we'll send your card details separately.",
      )
    case 'denied':
      return t(
        'cardApplication.statusPage.deniedBlurb',
        'Your application could not be approved at this time. If you believe this is an error, please contact the library directly.',
      )
    case 'under_review':
      return t(
        'cardApplication.statusPage.underReviewBlurb',
        'A staff member is currently reviewing your application.',
      )
    case 'pending':
    default:
      return t(
        'cardApplication.statusPage.pendingBlurb',
        'Your application is in the review queue. A decision is usually made within a few business days.',
      )
  }
}

export default function CardApplicationStatusPage(): React.ReactElement {
  const { t } = useTranslation()
  const { token } = useParams<{ token: string }>()

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['card-application', 'public-status', token],
    queryFn: () => checkApplicationByToken(token || ''),
    enabled: Boolean(token),
    retry: false,
  })

  return (
    <PageContainer className="py-12">
      <h1 className="text-3xl font-bold text-earth-900 dark:text-earth-50 mb-2">
        {t('cardApplication.statusPage.title', 'Application Status')}
      </h1>
      <p className="text-earth-700 dark:text-earth-200 mb-8">
        {t(
          'cardApplication.statusPage.subtitle',
          'This page shows the current status of the library card application linked to this private link.',
        )}
      </p>

      {isLoading && (
        <div
          className="flex items-center gap-3 rounded-lg border border-earth-200 dark:border-earth-700 bg-white dark:bg-earth-900 p-6"
          role="status"
          aria-live="polite"
        >
          <Loader2 className="h-5 w-5 animate-spin text-earth-700" aria-hidden="true" />
          <span className="text-earth-800 dark:text-earth-100">
            {t('cardApplication.statusPage.loading', 'Looking up your application…')}
          </span>
        </div>
      )}

      {isError && (
        <div
          className="rounded-lg border border-status-danger-300 bg-status-danger-50 dark:bg-status-danger-900/20 p-6"
          role="alert"
        >
          <div className="flex items-start gap-3">
            <AlertCircle
              className="h-6 w-6 text-status-danger-700 dark:text-status-danger-300 flex-shrink-0"
              aria-hidden="true"
            />
            <div>
              <h2 className="text-lg font-semibold text-status-danger-800 dark:text-status-danger-200">
                {t('cardApplication.statusPage.invalidTitle', 'Link not valid')}
              </h2>
              <p className="mt-1 text-status-danger-800 dark:text-status-danger-200">
                {error instanceof Error
                  ? error.message
                  : t(
                      'cardApplication.statusPage.invalidBody',
                      'This status link is invalid or has expired. If you need help, please contact the library directly.',
                    )}
              </p>
            </div>
          </div>
        </div>
      )}

      {data && (
        <article
          className="rounded-lg border border-earth-200 dark:border-earth-700 bg-white dark:bg-earth-900 p-6"
          aria-labelledby="status-heading"
        >
          <div className="flex items-start gap-4">
            <StatusIcon status={data.status} />
            <div className="flex-1">
              <h2
                id="status-heading"
                className="text-2xl font-semibold text-earth-900 dark:text-earth-50"
              >
                {statusLabel(t, data.status)}
              </h2>
              <p className="mt-2 text-earth-800 dark:text-earth-100">
                {statusBlurb(t, data.status)}
              </p>
            </div>
          </div>

          <dl className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="font-medium text-earth-700 dark:text-earth-300">
                {t('cardApplication.statusPage.submittedAtLabel', 'Submitted')}
              </dt>
              <dd className="mt-1 text-earth-900 dark:text-earth-50">
                {formatDate(data.submitted_at)}
              </dd>
            </div>
            {data.reviewed_at && (
              <div>
                <dt className="font-medium text-earth-700 dark:text-earth-300">
                  {t('cardApplication.statusPage.reviewedAtLabel', 'Reviewed')}
                </dt>
                <dd className="mt-1 text-earth-900 dark:text-earth-50">
                  {formatDate(data.reviewed_at)}
                </dd>
              </div>
            )}
          </dl>
        </article>
      )}
    </PageContainer>
  )
}
