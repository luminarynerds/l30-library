/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Staff queue page for resource guide flags.
 *
 * Lists open flags oldest-first (FIFO triage) with item context inline.
 * Per-row actions:
 *   - Verify still current  -> POST /items/{id}/verify (auto-resolves all
 *                              flags on that item with verified_current).
 *   - Dismiss               -> PATCH /flags/{id} status=dismissed
 *                              resolution=invalid.
 *
 * Edit / Retire actions are deferred to v2 -- they need an item edit
 * drawer that is out of scope for this PR. The spec calls them out;
 * shipping the queue UI with two working actions is more useful than
 * shipping four broken actions.
 */
import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import * as Sentry from '@/lib/sentry-lazy'
import toast from 'react-hot-toast'
import { Loader2, AlertTriangle, ExternalLink } from 'lucide-react'
import {
  listResourceGuideFlags,
  patchResourceGuideFlag,
  verifyResourceGuideItem,
  type ResourceGuideFlag,
} from '@/api/parent-onboarding-api'
import { useTranslation } from '@/i18n'
import { AdminShell } from '../components/shells/AdminShell'

const REASON_KEY_PREFIX = 'parentResources.flagModal.reason'

function ReasonLabel({ code }: { code: string }): JSX.Element {
  const { t } = useTranslation()
  // The reason_code string from the backend matches an i18n key suffix
  // 1-to-1; on miss we surface the raw code so staff aren't left blank.
  return <>{t(`${REASON_KEY_PREFIX}.${code}`) || code}</>
}

function formatDateTime(iso: string, locale: string): string {
  try {
    return new Intl.DateTimeFormat(locale, {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(new Date(iso))
  } catch {
    return iso
  }
}

export default function StaffResourceFlagsPage(): JSX.Element {
  const translation = useTranslation()
  const t = translation.t
  const i18n = (translation as { i18n?: { language?: string } }).i18n
  const locale = i18n?.language ?? 'en'
  const queryClient = useQueryClient()
  const [busyFlagId, setBusyFlagId] = useState<number | null>(null)

  const {
    data: flags,
    isLoading,
    error,
  } = useQuery<ResourceGuideFlag[]>({
    queryKey: ['parent-onboarding-resource-flags', 'open'],
    queryFn: () => listResourceGuideFlags('open'),
  })

  useEffect(() => {
    if (error) Sentry.captureException(error)
  }, [error])

  async function handleVerify(flag: ResourceGuideFlag) {
    if (busyFlagId === flag.id) return
    setBusyFlagId(flag.id)
    try {
      await verifyResourceGuideItem(flag.item_id)
      toast.success(t('parentResources.queue.verified'))
      await queryClient.invalidateQueries({
        queryKey: ['parent-onboarding-resource-flags'],
      })
    } catch (err) {
      Sentry.captureException(err)
      toast.error(t('parentResources.queue.error'))
    } finally {
      setBusyFlagId(null)
    }
  }

  async function handleDismiss(flag: ResourceGuideFlag) {
    if (busyFlagId === flag.id) return
    setBusyFlagId(flag.id)
    try {
      await patchResourceGuideFlag(flag.id, {
        status: 'dismissed',
        resolution: 'invalid',
      })
      toast.success(t('parentResources.queue.dismissed'))
      await queryClient.invalidateQueries({
        queryKey: ['parent-onboarding-resource-flags'],
      })
    } catch (err) {
      Sentry.captureException(err)
      toast.error(t('parentResources.queue.error'))
    } finally {
      setBusyFlagId(null)
    }
  }

  return (
    <AdminShell title={t('parentResources.queue.title')}>
      <div className="max-w-5xl mx-auto p-6 space-y-6">
        <header className="space-y-2">
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
            {t('parentResources.queue.title')}
          </h1>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 max-w-2xl">
            {t('parentResources.queue.intro')}
          </p>
        </header>

        {isLoading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" aria-hidden="true" />
          </div>
        )}

        {error && (
          <div
            role="alert"
            className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-xl p-6 text-center"
          >
            <AlertTriangle
              className="w-8 h-8 text-status-danger-500 mx-auto mb-2"
              aria-hidden="true"
            />
            <p className="text-status-danger-700 dark:text-status-danger-300">
              {t('parentResources.queue.loadFailed')}
            </p>
          </div>
        )}

        {!isLoading && !error && (flags?.length ?? 0) === 0 && (
          <div className="text-center py-12">
            <p className="text-lsc-dark/70 dark:text-lsc-cream/60">
              {t('parentResources.queue.empty')}
            </p>
          </div>
        )}

        {flags && flags.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left text-lsc-dark dark:text-lsc-cream">
              <caption className="sr-only">
                {t('parentResources.queue.tableCaption')}
              </caption>
              <thead className="text-xs uppercase tracking-wide text-lsc-dark/60 dark:text-lsc-cream/60 bg-lsc-cream/40 dark:bg-earth-700/30">
                <tr>
                  <th scope="col" className="px-3 py-2">{t('parentResources.queue.col.filed')}</th>
                  <th scope="col" className="px-3 py-2">{t('parentResources.queue.col.item')}</th>
                  <th scope="col" className="px-3 py-2">{t('parentResources.queue.col.reason')}</th>
                  <th scope="col" className="px-3 py-2">{t('parentResources.queue.col.flaggedBy')}</th>
                  <th scope="col" className="px-3 py-2">{t('parentResources.queue.col.actions')}</th>
                </tr>
              </thead>
              <tbody>
                {flags.map((flag) => (
                  <tr
                    key={flag.id}
                    className="border-t border-lsc-border dark:border-earth-700"
                    data-testid={`flag-row-${flag.id}`}
                  >
                    <td className="px-3 py-3 whitespace-nowrap">
                      {formatDateTime(flag.created_at, locale)}
                    </td>
                    <td className="px-3 py-3">
                      <div className="font-medium">{flag.item?.title ?? `#${flag.item_id}`}</div>
                      {flag.item?.contact_info && (
                        <div className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 mt-0.5">
                          {flag.item.contact_info}
                        </div>
                      )}
                      <Link
                        to={`/staff/parent-onboarding/resources#item-${flag.item_id}`}
                        className="inline-flex items-center gap-1 text-xs text-lsc-rose hover:underline mt-1"
                      >
                        <ExternalLink className="w-3 h-3" aria-hidden="true" />
                        {t('parentResources.queue.openInContext')}
                      </Link>
                    </td>
                    <td className="px-3 py-3">
                      <ReasonLabel code={flag.reason_code} />
                      {flag.comment && (
                        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-1 italic">
                          {flag.comment}
                        </p>
                      )}
                    </td>
                    <td className="px-3 py-3">
                      {flag.flagged_by_name ?? t('parentResources.queue.unknownUser')}
                    </td>
                    <td className="px-3 py-3 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => handleVerify(flag)}
                          disabled={busyFlagId === flag.id}
                          aria-label={t('parentResources.queue.action.verifyAria', {
                            title: flag.item?.title ?? `#${flag.item_id}`,
                          })}
                          data-testid={`queue-verify-${flag.id}`}
                          className="px-3 py-1.5 rounded bg-lsc-rose text-white text-xs font-medium hover:bg-lsc-rose/90 focus:outline-none focus:ring-2 focus:ring-lsc-rose disabled:opacity-50"
                        >
                          {busyFlagId === flag.id ? (
                            <Loader2 className="w-3 h-3 motion-safe:animate-spin inline" aria-hidden="true" />
                          ) : (
                            t('parentResources.queue.action.verify')
                          )}
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDismiss(flag)}
                          disabled={busyFlagId === flag.id}
                          aria-label={t('parentResources.queue.action.dismissAria', {
                            title: flag.item?.title ?? `#${flag.item_id}`,
                          })}
                          data-testid={`queue-dismiss-${flag.id}`}
                          className="px-3 py-1.5 rounded border border-lsc-border text-xs font-medium hover:bg-lsc-cream/50 focus:outline-none focus:ring-2 focus:ring-lsc-rose disabled:opacity-50"
                        >
                          {t('parentResources.queue.action.dismiss')}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AdminShell>
  )
}
