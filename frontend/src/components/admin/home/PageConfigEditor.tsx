/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Edit the singleton `home_page_config` row.
 */
import { useEffect, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { useTranslation } from '@/i18n'
import {
  getHomeConfig,
  HomePageConfigRead,
  HomePageConfigUpdate,
  updateHomeConfig,
} from '@/api/home'

export function PageConfigEditor() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const { data, isLoading, error } = useQuery({
    queryKey: ['home-admin-config'],
    queryFn: getHomeConfig,
  })

  const [form, setForm] = useState<HomePageConfigUpdate>({})

  useEffect(() => {
    if (data) {
      setForm({
        eyebrow: data.eyebrow,
        hero_visible: data.hero_visible,
        picks_link_label: data.picks_link_label,
        picks_link_href: data.picks_link_href,
        empty_state_message: data.empty_state_message,
      })
    }
  }, [data])

  const saveMutation = useMutation({
    mutationFn: (body: HomePageConfigUpdate) => updateHomeConfig(body),
    onSuccess: (saved: HomePageConfigRead) => {
      queryClient.setQueryData(['home-admin-config'], saved)
      toast.success(t('admin.adminHomePage.toasts.configSaved', 'Page config saved'))
    },
    onError: (e: Error) =>
      toast.error(e.message || t('admin.adminHomePage.toasts.saveFailed', 'Save failed')),
  })

  if (isLoading) {
    return <div className="text-center py-12 text-earth-600">{t('common.loading', 'Loading...')}</div>
  }
  if (error) {
    return <div className="text-center py-12 text-status-danger-600">{(error as Error).message}</div>
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        saveMutation.mutate(form)
      }}
      className="space-y-5 max-w-2xl"
    >
      <div className="space-y-1">
        <label htmlFor="config-eyebrow" className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
          {t('admin.adminHomePage.config.fields.eyebrow', 'Eyebrow text')}
        </label>
        <input
          id="config-eyebrow"
          value={form.eyebrow ?? ''}
          onChange={(e) => setForm((f) => ({ ...f, eyebrow: e.target.value }))}
          maxLength={280}
          className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-sm"
        />
      </div>

      <label className="inline-flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream">
        <input
          type="checkbox"
          checked={form.hero_visible ?? true}
          onChange={(e) => setForm((f) => ({ ...f, hero_visible: e.target.checked }))}
        />
        {t('admin.adminHomePage.config.fields.heroVisible', 'Show hero pick on home page')}
      </label>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="space-y-1">
          <label htmlFor="config-picks-label" className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
            {t('admin.adminHomePage.config.fields.picksLinkLabel', '"More picks" link label')}
          </label>
          <input
            id="config-picks-label"
            value={form.picks_link_label ?? ''}
            onChange={(e) => setForm((f) => ({ ...f, picks_link_label: e.target.value }))}
            maxLength={120}
            className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-sm"
          />
        </div>
        <div className="space-y-1">
          <label htmlFor="config-picks-href" className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
            {t('admin.adminHomePage.config.fields.picksLinkHref', '"More picks" link URL')}
          </label>
          <input
            id="config-picks-href"
            value={form.picks_link_href ?? ''}
            onChange={(e) => setForm((f) => ({ ...f, picks_link_href: e.target.value }))}
            maxLength={500}
            placeholder="/staff-picks"
            className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-sm"
          />
        </div>
      </div>

      <div className="space-y-1">
        <label htmlFor="config-empty" className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
          {t('admin.adminHomePage.config.fields.emptyStateMessage', 'Empty-state message')}
        </label>
        <textarea
          id="config-empty"
          value={form.empty_state_message ?? ''}
          onChange={(e) => setForm((f) => ({ ...f, empty_state_message: e.target.value }))}
          rows={3}
          className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-sm"
        />
        <p className="text-xs text-earth-600 dark:text-earth-400">
          {t(
            'admin.adminHomePage.config.fields.emptyStateHelp',
            'Shown when no hero pick is active and all shelves resolved empty.'
          )}
        </p>
      </div>

      <div className="flex items-center gap-2 pt-2">
        <button
          type="submit"
          disabled={saveMutation.isPending}
          className="px-4 py-2 bg-lsc-rose text-white rounded-lg text-sm font-medium hover:bg-lsc-rose/90 disabled:opacity-50"
        >
          {saveMutation.isPending
            ? t('common.saving', 'Saving...')
            : t('common.save', 'Save')}
        </button>
      </div>
    </form>
  )
}
