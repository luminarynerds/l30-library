/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery } from '@tanstack/react-query'
import {
  X, Layers, Package, BookOpen, Tag, Globe, Clock, Hash, Database, AlertTriangle, Loader2
} from 'lucide-react'
import {
  getBibframeWork,
  type BibframeWorkDetail,
} from '@/api/domains/catalog/bibframe-api'

import { formatGenre } from '@/utils/format-utils'
import { t } from '@/i18n'
import { BibframeTooltip } from './BibframeTooltip'
import { InstancePanel } from './InstancePanel'
import FocusTrap from 'focus-trap-react'

interface WorkDetailPanelProps {
  workId: number
  onClose: () => void
}

export function WorkDetailPanel({ workId, onClose }: WorkDetailPanelProps): React.ReactElement {
  const { data: work, isLoading, error } = useQuery<BibframeWorkDetail>({
    queryKey: ['bibframe-work', workId],
    queryFn: () => getBibframeWork(workId),
    staleTime: 1000 * 60 * 30,
  })

  return (
    <FocusTrap active={true} focusTrapOptions={{ escapeDeactivates: false, allowOutsideClick: true, returnFocusOnDeactivate: true, fallbackFocus: () => document.body }}>
    <div
      role="dialog"
      aria-modal="true"
      aria-label={work ? `BIBFRAME details for ${work.title}` : 'Loading work details'}
      className="fixed inset-0 z-50 flex items-start justify-end"
    >
      <button
        type="button"
        className="absolute inset-0 bg-black/40 dark:bg-black/60 cursor-default"
        onClick={onClose}
        aria-label={t('aria.bibframeCatalog.closeWorkDetails')}
        tabIndex={-1}
      />

      <div className="relative z-10 h-full w-full max-w-2xl bg-lsc-white dark:bg-earth-900 shadow-lg overflow-y-auto">
        <div className="sticky top-0 z-10 flex items-center justify-between gap-3 px-5 py-4 bg-lsc-white dark:bg-earth-900 border-b border-lsc-border dark:border-earth-700">
          <div className="flex items-center gap-2 text-lsc-rose dark:text-lsc-rose-light">
            <Layers className="w-5 h-5" aria-hidden="true" />
            <span className="font-semibold text-sm uppercase tracking-wide">BIBFRAME Work Detail</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
            aria-label={t('aria.bibframeCatalog.closePanel')}
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>

        {isLoading && (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose" aria-label={t('aria.bibframeCatalog.loadingWorkDetails')} />
          </div>
        )}

        {error && (
          <div className="px-5 py-10 text-center space-y-3">
            <AlertTriangle className="w-10 h-10 mx-auto text-status-warning-500" aria-hidden="true" />
            <p className="text-lsc-dark/80 dark:text-lsc-cream/80">Could not load work details. Please try again.</p>
          </div>
        )}

        {work && (
          <div className="px-5 py-6 space-y-8">
            <section aria-labelledby="work-heading">
              <div className="flex items-center gap-2 mb-4">
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-lsc-rose text-white text-xs font-semibold uppercase tracking-wide">
                  <Layers className="w-3.5 h-3.5" aria-hidden="true" />
                  <BibframeTooltip
                    term="Work"
                    definition="A Work is the abstract intellectual or artistic content — the story, ideas, or music — independent of any particular edition or format. Think of it as 'Hamlet the play' rather than any specific book."
                  />
                </span>
              </div>

              <h2 id="work-heading" className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream leading-snug">
                {work.title}
                {work.subtitle && (
                  <span className="block text-lg font-normal text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                    {work.subtitle}
                  </span>
                )}
              </h2>

              {work.summary && (
                <p className="mt-4 text-lsc-dark/80 dark:text-lsc-cream/80 leading-relaxed text-sm">
                  {work.summary}
                </p>
              )}

              <dl className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-3">
                {work.genre_form && (
                  <div className="flex items-start gap-2">
                    <Tag className="w-4 h-4 text-lsc-rose mt-0.5 flex-shrink-0" aria-hidden="true" />
                    <div>
                      <dt className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wide">Genre / Form</dt>
                      <dd className="text-sm text-lsc-dark dark:text-lsc-cream">{formatGenre(work.genre_form)}</dd>
                    </div>
                  </div>
                )}
                {work.language && (
                  <div className="flex items-start gap-2">
                    <Globe className="w-4 h-4 text-lsc-rose mt-0.5 flex-shrink-0" aria-hidden="true" />
                    <div>
                      <dt className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wide">Language</dt>
                      <dd className="text-sm text-lsc-dark dark:text-lsc-cream">{work.language}</dd>
                    </div>
                  </div>
                )}
                {work.origin_date && (
                  <div className="flex items-start gap-2">
                    <Clock className="w-4 h-4 text-lsc-rose mt-0.5 flex-shrink-0" aria-hidden="true" />
                    <div>
                      <dt className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wide">Origin Date</dt>
                      <dd className="text-sm text-lsc-dark dark:text-lsc-cream">{work.origin_date}</dd>
                    </div>
                  </div>
                )}
                {work.dewey_classification && (
                  <div className="flex items-start gap-2">
                    <Hash className="w-4 h-4 text-lsc-rose mt-0.5 flex-shrink-0" aria-hidden="true" />
                    <div>
                      <dt className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wide">Dewey Classification</dt>
                      <dd className="text-sm font-mono text-lsc-dark dark:text-lsc-cream">{work.dewey_classification}</dd>
                    </div>
                  </div>
                )}
                {work.lc_classification && (
                  <div className="flex items-start gap-2">
                    <Hash className="w-4 h-4 text-lsc-rose mt-0.5 flex-shrink-0" aria-hidden="true" />
                    <div>
                      <dt className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wide">LC Classification</dt>
                      <dd className="text-sm font-mono text-lsc-dark dark:text-lsc-cream">{work.lc_classification}</dd>
                    </div>
                  </div>
                )}
                {work.series_title && (
                  <div className="flex items-start gap-2 sm:col-span-2">
                    <BookOpen className="w-4 h-4 text-lsc-rose mt-0.5 flex-shrink-0" aria-hidden="true" />
                    <div>
                      <dt className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wide">Series</dt>
                      <dd className="text-sm text-lsc-dark dark:text-lsc-cream">
                        {work.series_title}
                        {work.series_number && ` (vol. ${work.series_number})`}
                      </dd>
                    </div>
                  </div>
                )}
              </dl>
            </section>

            <section aria-labelledby="instances-heading">
              <div className="flex items-center gap-2 mb-3">
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-lsc-rose text-white text-xs font-semibold uppercase tracking-wide">
                  <Package className="w-3.5 h-3.5" aria-hidden="true" />
                  <BibframeTooltip
                    term="Instances"
                    definition="An Instance is a specific published edition or format of a Work — for example, the 2019 paperback edition or the audiobook version. One Work can have many Instances."
                  />
                </span>
                <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                  {work.instances.length} edition{work.instances.length !== 1 ? 's' : ''}
                </span>
              </div>
              <h3 id="instances-heading" className="sr-only">Editions and Formats</h3>

              {work.instances.length === 0 ? (
                <div className="rounded-lg border border-lsc-border dark:border-earth-700 px-5 py-6 text-center text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">
                  No editions recorded for this work yet.
                </div>
              ) : (
                <div className="space-y-3">
                  {work.instances.map((instance, idx) => (
                    <InstancePanel key={instance.id} instance={instance} index={idx} />
                  ))}
                </div>
              )}
            </section>

            <div className="flex items-center gap-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70 border-t border-lsc-border dark:border-earth-700 pt-4">
              <Database className="w-3.5 h-3.5 flex-shrink-0" aria-hidden="true" />
              <span>
                Metadata sourced from BIBFRAME catalog. Results are cached for up to 1 hour to ensure fast loading.
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
    </FocusTrap>
  )
}
