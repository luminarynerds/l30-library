/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { AdminShell } from '@/components/shells/AdminShell'
import { useTranslation } from '@/i18n'
import { getErrorMessage } from '@/lib/api-client'
import {
  getContentTranslations,
  updateContentTranslation,
  type ContentTranslationRecord,
} from '@/api/admin/content-translations-api'

// Only Spanish has UI translators right now; the API itself is language-keyed
// (see backend contract), so adding a second language here is a UI-only change.
const LANGUAGE = 'es'

const LONG_FIELDS = new Set(['description', 'schedule'])

function fieldLabel(t: (key: string, fallback?: string) => string, field: string): string {
  switch (field) {
    case 'name':
      return t('contentTranslations.field.name', 'Name')
    case 'title':
      return t('contentTranslations.field.title', 'Title')
    case 'description':
      return t('contentTranslations.field.description', 'Description')
    case 'schedule':
      return t('contentTranslations.field.schedule', 'Schedule')
    default:
      return field
  }
}

interface RecordCardProps {
  contentType: string
  record: ContentTranslationRecord
}

function TranslationRecordCard({ contentType, record }: RecordCardProps): React.ReactElement {
  const { t } = useTranslation()
  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(record.fields.map((f) => [f.field, f.value ?? ''])),
  )

  const mutation = useMutation({
    mutationFn: () => updateContentTranslation(contentType, record.id, LANGUAGE, values),
    onSuccess: (updated) => {
      setValues(Object.fromEntries(updated.fields.map((f) => [f.field, f.value ?? ''])))
      toast.success(t('contentTranslations.saved', 'Saved.'))
    },
    onError: () => {
      toast.error(t('contentTranslations.saveFailed', 'Could not save this translation.'))
    },
  })

  return (
    <fieldset className="border border-lsc-border dark:border-earth-700 rounded-lg p-4">
      <legend className="px-1 font-medium text-lsc-dark dark:text-lsc-cream">
        {record.display_name}
      </legend>
      <div className="space-y-4 mt-2">
        {record.fields.map((field) => {
          const inputId = `ct-${contentType}-${record.id}-${field.field}`
          const isLong = LONG_FIELDS.has(field.field)
          const label = fieldLabel(t, field.field)
          return (
            <div key={field.field} className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <span className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  {label} — {t('contentTranslations.englishLabel', 'English')}
                </span>
                <p className="text-sm text-lsc-dark dark:text-lsc-cream px-3 py-2 bg-lsc-cream/30 dark:bg-earth-900 border border-lsc-border dark:border-earth-700 rounded whitespace-pre-wrap min-h-[2.5rem]">
                  {field.source}
                </p>
              </div>
              <div>
                <label
                  htmlFor={inputId}
                  className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1"
                >
                  {label} — {t('contentTranslations.spanishLabel', 'Spanish')}
                </label>
                {isLong ? (
                  <textarea
                    id={inputId}
                    value={values[field.field] ?? ''}
                    onChange={(e) => setValues((v) => ({ ...v, [field.field]: e.target.value }))}
                    rows={3}
                    className="w-full px-3 py-2 text-sm bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                  />
                ) : (
                  <input
                    id={inputId}
                    type="text"
                    value={values[field.field] ?? ''}
                    onChange={(e) => setValues((v) => ({ ...v, [field.field]: e.target.value }))}
                    className="w-full px-3 py-2 text-sm bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded focus:outline-none focus:ring-2 focus:ring-lsc-rose"
                  />
                )}
              </div>
            </div>
          )
        })}
      </div>
      <div className="mt-3 flex justify-end">
        <button
          type="button"
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
          className="px-3 py-2 text-sm bg-lsc-rose text-white rounded hover:bg-lsc-rose/90 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2"
        >
          {mutation.isPending
            ? t('contentTranslations.saving', 'Saving...')
            : t('contentTranslations.save', 'Save')}
        </button>
      </div>
    </fieldset>
  )
}

export default function AdminContentTranslationsPage(): React.ReactElement {
  const { t } = useTranslation()
  const { data, isLoading, error } = useQuery({
    queryKey: ['content-translations', LANGUAGE],
    queryFn: () => getContentTranslations(LANGUAGE),
  })

  const groups = data?.groups ?? []

  return (
    <AdminShell
      title={t('contentTranslations.pageTitle', 'Content translations')}
      subtitle={t(
        'contentTranslations.pageSubtitle',
        'Translate patron-facing rooms, tech help, legal topics, and discover shelves into Spanish. English is always shown for reference.',
      )}
      loading={isLoading}
      error={error ? getErrorMessage(error, t('contentTranslations.loadFailed', 'Could not load content translations.')) : null}
    >
      {groups.length === 0 ? (
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          {t('contentTranslations.noGroups', 'No translatable content found.')}
        </p>
      ) : (
        <div className="space-y-8">
          {groups.map((group) => (
            <section key={group.content_type} aria-labelledby={`ct-group-${group.content_type}`}>
              <h2
                id={`ct-group-${group.content_type}`}
                className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-3"
              >
                {group.label}
              </h2>
              {group.records.length === 0 ? (
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  {t('contentTranslations.emptyGroup', 'No records yet.')}
                </p>
              ) : (
                <div className="space-y-4">
                  {group.records.map((record) => (
                    <TranslationRecordCard
                      key={record.id}
                      contentType={group.content_type}
                      record={record}
                    />
                  ))}
                </div>
              )}
            </section>
          ))}
        </div>
      )}
    </AdminShell>
  )
}
