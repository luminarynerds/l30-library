/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useMemo, useState } from 'react'
import { Quote, Plus, Trash2, Save, X, Edit2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

import { AdminShell } from '../components/shells/AdminShell'
import { useTranslation } from '@/i18n'
import {
  HomepageQuoteAdmin,
  HomepageQuoteCreate,
  adminListHomepageQuotes,
  adminCreateHomepageQuote,
  adminUpdateHomepageQuote,
  adminDeleteHomepageQuote,
} from '@/api/domains/services/homepage-quotes-api'

const LOCALES: { code: string; labelKey: string; fallback: string }[] = [
  { code: 'en', labelKey: 'admin.homepageQuotes.locale.en', fallback: 'English' },
  { code: 'es', labelKey: 'admin.homepageQuotes.locale.es', fallback: 'Spanish' },
  { code: 'fr', labelKey: 'admin.homepageQuotes.locale.fr', fallback: 'French' },
  { code: 'de', labelKey: 'admin.homepageQuotes.locale.de', fallback: 'German' },
  { code: 'zh', labelKey: 'admin.homepageQuotes.locale.zh', fallback: 'Chinese' },
  { code: 'ar', labelKey: 'admin.homepageQuotes.locale.ar', fallback: 'Arabic' },
  { code: 'ru', labelKey: 'admin.homepageQuotes.locale.ru', fallback: 'Russian' },
]

const EMPTY_FORM: HomepageQuoteCreate = {
  locale: 'en',
  quote_text: '',
  attribution: '',
  is_active: true,
  display_order: 0,
}

export default function AdminHomepageQuotesPage() {
  const { t } = useTranslation()
  const qc = useQueryClient()
  const [selectedLocale, setSelectedLocale] = useState<string>('en')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form, setForm] = useState<HomepageQuoteCreate>(EMPTY_FORM)
  const [showForm, setShowForm] = useState(false)

  const { data: quotes = [], isLoading, error } = useQuery({
    queryKey: ['admin-homepage-quotes', selectedLocale],
    queryFn: () => adminListHomepageQuotes(selectedLocale),
  })

  const createMutation = useMutation({
    mutationFn: adminCreateHomepageQuote,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin-homepage-quotes'] })
      qc.invalidateQueries({ queryKey: ['homepage-quotes'] })
      toast.success(t('admin.homepageQuotes.created', 'Quote added'))
      resetForm()
    },
    onError: () => toast.error(t('admin.homepageQuotes.createError', 'Failed to add quote')),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: HomepageQuoteCreate }) =>
      adminUpdateHomepageQuote(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin-homepage-quotes'] })
      qc.invalidateQueries({ queryKey: ['homepage-quotes'] })
      toast.success(t('admin.homepageQuotes.updated', 'Quote updated'))
      resetForm()
    },
    onError: () => toast.error(t('admin.homepageQuotes.updateError', 'Failed to update quote')),
  })

  const deleteMutation = useMutation({
    mutationFn: adminDeleteHomepageQuote,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin-homepage-quotes'] })
      qc.invalidateQueries({ queryKey: ['homepage-quotes'] })
      toast.success(t('admin.homepageQuotes.deleted', 'Quote deleted'))
    },
    onError: () => toast.error(t('admin.homepageQuotes.deleteError', 'Failed to delete quote')),
  })

  useEffect(() => {
    setForm((f) => ({ ...f, locale: selectedLocale }))
  }, [selectedLocale])

  const resetForm = () => {
    setEditingId(null)
    setForm({ ...EMPTY_FORM, locale: selectedLocale })
    setShowForm(false)
  }

  const startEdit = (q: HomepageQuoteAdmin) => {
    setEditingId(q.id)
    setForm({
      locale: q.locale,
      quote_text: q.quote_text,
      attribution: q.attribution ?? '',
      is_active: q.is_active,
      display_order: q.display_order,
    })
    setShowForm(true)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const payload: HomepageQuoteCreate = {
      ...form,
      attribution: form.attribution?.trim() ? form.attribution.trim() : null,
    }
    if (editingId !== null) {
      updateMutation.mutate({ id: editingId, data: payload })
    } else {
      createMutation.mutate(payload)
    }
  }

  const handleDelete = (id: number) => {
    if (window.confirm(t('admin.homepageQuotes.deleteConfirm', 'Delete this quote?'))) {
      deleteMutation.mutate(id)
    }
  }

  const errorMsg = useMemo(() => {
    if (!error) return null
    return (error as Error).message || t('admin.homepageQuotes.loadError', 'Failed to load quotes')
  }, [error, t])

  return (
    <AdminShell
      title={t('admin.homepageQuotes.title', 'Homepage Quotes')}
      subtitle={t('admin.homepageQuotes.subtitle', 'Curate the literary quotes shown on the patron home page')}
      icon={<Quote className="w-6 h-6" aria-hidden="true" />}
      loading={isLoading}
      error={errorMsg}
      actions={
        !showForm ? (
          <button
            type="button"
            onClick={() => {
              setEditingId(null)
              setForm({ ...EMPTY_FORM, locale: selectedLocale })
              setShowForm(true)
            }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-lsc-rose text-white text-sm font-semibold hover:bg-lsc-rose/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2"
          >
            <Plus className="w-4 h-4" aria-hidden="true" />
            {t('admin.homepageQuotes.addNew', 'Add quote')}
          </button>
        ) : null
      }
    >
      <div className="max-w-5xl mx-auto p-6 space-y-6">
        <div className="flex items-center gap-3">
          <label htmlFor="locale-select" className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
            {t('admin.homepageQuotes.localeLabel', 'Locale')}
          </label>
          <select
            id="locale-select"
            value={selectedLocale}
            onChange={(e) => setSelectedLocale(e.target.value)}
            className="px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
          >
            {LOCALES.map((l) => (
              <option key={l.code} value={l.code}>
                {t(l.labelKey, l.fallback)} ({l.code})
              </option>
            ))}
          </select>
        </div>

        {showForm && (
          <form
            onSubmit={handleSubmit}
            className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm p-6 space-y-4 border border-lsc-border dark:border-earth-700"
          >
            <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
              {editingId !== null
                ? t('admin.homepageQuotes.editTitle', 'Edit quote')
                : t('admin.homepageQuotes.addNew', 'Add quote')}
            </h2>
            <div>
              <label htmlFor="quote_text" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                {t('admin.homepageQuotes.quoteText', 'Quote text')}
              </label>
              <textarea
                id="quote_text"
                required
                value={form.quote_text}
                onChange={(e) => setForm({ ...form, quote_text: e.target.value })}
                rows={4}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
              />
            </div>
            <div>
              <label htmlFor="attribution" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                {t('admin.homepageQuotes.attribution', 'Attribution (optional)')}
              </label>
              <input
                id="attribution"
                type="text"
                value={form.attribution ?? ''}
                onChange={(e) => setForm({ ...form, attribution: e.target.value })}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
              />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label htmlFor="form_locale" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  {t('admin.homepageQuotes.localeLabel', 'Locale')}
                </label>
                <select
                  id="form_locale"
                  value={form.locale}
                  onChange={(e) => setForm({ ...form, locale: e.target.value })}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                >
                  {LOCALES.map((l) => (
                    <option key={l.code} value={l.code}>
                      {t(l.labelKey, l.fallback)} ({l.code})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="display_order" className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  {t('admin.homepageQuotes.displayOrder', 'Display order')}
                </label>
                <input
                  id="display_order"
                  type="number"
                  value={form.display_order ?? 0}
                  onChange={(e) => setForm({ ...form, display_order: parseInt(e.target.value, 10) || 0 })}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-lg bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                />
              </div>
              <div className="flex items-end">
                <label className="inline-flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream">
                  <input
                    type="checkbox"
                    checked={form.is_active ?? true}
                    onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                    className="rounded"
                  />
                  {t('admin.homepageQuotes.active', 'Active')}
                </label>
              </div>
            </div>
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={createMutation.isPending || updateMutation.isPending}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-lsc-rose text-white text-sm font-semibold hover:bg-lsc-rose/90 disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2"
              >
                <Save className="w-4 h-4" aria-hidden="true" />
                {t('admin.homepageQuotes.save', 'Save')}
              </button>
              <button
                type="button"
                onClick={resetForm}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-sm text-lsc-dark dark:text-lsc-cream hover:bg-earth-100 dark:hover:bg-earth-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2"
              >
                <X className="w-4 h-4" aria-hidden="true" />
                {t('admin.homepageQuotes.cancel', 'Cancel')}
              </button>
            </div>
          </form>
        )}

        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-sm border border-lsc-border dark:border-earth-700 overflow-hidden">
          {quotes.length === 0 ? (
            <p className="p-6 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
              {t('admin.homepageQuotes.empty', 'No quotes configured for this locale yet.')}
            </p>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-earth-100 dark:bg-earth-700">
                <tr>
                  <th scope="col" className="text-left px-4 py-2 font-semibold text-lsc-dark dark:text-lsc-cream">
                    {t('admin.homepageQuotes.quoteText', 'Quote')}
                  </th>
                  <th scope="col" className="text-left px-4 py-2 font-semibold text-lsc-dark dark:text-lsc-cream">
                    {t('admin.homepageQuotes.attribution', 'Attribution')}
                  </th>
                  <th scope="col" className="text-left px-4 py-2 font-semibold text-lsc-dark dark:text-lsc-cream w-20">
                    {t('admin.homepageQuotes.displayOrder', 'Order')}
                  </th>
                  <th scope="col" className="text-left px-4 py-2 font-semibold text-lsc-dark dark:text-lsc-cream w-20">
                    {t('admin.homepageQuotes.active', 'Active')}
                  </th>
                  <th scope="col" className="text-right px-4 py-2 font-semibold text-lsc-dark dark:text-lsc-cream w-32">
                    {t('admin.homepageQuotes.actions', 'Actions')}
                  </th>
                </tr>
              </thead>
              <tbody>
                {quotes.map((q) => (
                  <tr key={q.id} className="border-t border-lsc-border dark:border-earth-700">
                    <td className="px-4 py-2 text-lsc-dark dark:text-lsc-cream whitespace-pre-line">
                      {q.quote_text}
                    </td>
                    <td className="px-4 py-2 text-lsc-dark/80 dark:text-lsc-cream/80">
                      {q.attribution ?? ''}
                    </td>
                    <td className="px-4 py-2 text-lsc-dark/80 dark:text-lsc-cream/80">
                      {q.display_order}
                    </td>
                    <td className="px-4 py-2">
                      {q.is_active
                        ? t('admin.homepageQuotes.yes', 'Yes')
                        : t('admin.homepageQuotes.no', 'No')}
                    </td>
                    <td className="px-4 py-2 text-right space-x-2">
                      <button
                        type="button"
                        onClick={() => startEdit(q)}
                        aria-label={t('admin.homepageQuotes.edit', 'Edit quote')}
                        className="inline-flex items-center gap-1 text-lsc-rose hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 rounded"
                      >
                        <Edit2 className="w-4 h-4" aria-hidden="true" />
                        {t('admin.homepageQuotes.edit', 'Edit')}
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDelete(q.id)}
                        aria-label={t('admin.homepageQuotes.delete', 'Delete quote')}
                        className="inline-flex items-center gap-1 text-red-600 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-600 focus-visible:ring-offset-2 rounded"
                      >
                        <Trash2 className="w-4 h-4" aria-hidden="true" />
                        {t('admin.homepageQuotes.delete', 'Delete')}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </AdminShell>
  )
}
