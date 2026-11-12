/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Create / edit a single HomeHeroPick.
 *
 * - Item picker is an inline catalog search reusing GET /catalog?q=&limit=10
 *   (same shape the catalog search uses) — no new dep.
 * - Annotation is markdown; soft 280-char limit (warn, don't block).
 * - Active window uses native datetime-local inputs; converted to ISO on save.
 */
import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Search } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import toast from 'react-hot-toast'
import { useTranslation } from '@/i18n'
import {
  CatalogPickerResult,
  createHeroPick,
  HeroPickRead,
  searchCatalogForPicker,
  updateHeroPick,
} from '@/api/home'

const ANNOTATION_SOFT_LIMIT = 280

function toLocalInput(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  // Strip seconds + tz for datetime-local
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function fromLocalInput(s: string): string | null {
  if (!s) return null
  const d = new Date(s)
  return Number.isNaN(d.getTime()) ? null : d.toISOString()
}

interface Props {
  pickId: number | null
  initial: HeroPickRead | null
  onDone: () => void
}

export function HeroPickEditor({ pickId, initial, onDone }: Props) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const isEdit = pickId !== null

  const [itemId, setItemId] = useState<number | null>(initial?.item.id ?? null)
  const [itemLabel, setItemLabel] = useState<string>(
    initial ? `${initial.item.title}${initial.item.author ? ` — ${initial.item.author}` : ''}` : ''
  )
  const [annotation, setAnnotation] = useState(initial?.annotation_md ?? '')
  const [ctaLabel, setCtaLabel] = useState(initial?.cta_label ?? '')
  const [ctaHref, setCtaHref] = useState(initial?.cta_href ?? '')
  const [activeFrom, setActiveFrom] = useState(toLocalInput(initial?.active_from))
  const [activeTo, setActiveTo] = useState(toLocalInput(initial?.active_to))
  const [showPreview, setShowPreview] = useState(false)

  const [searchQ, setSearchQ] = useState('')
  const [searching, setSearching] = useState(false)
  const [results, setResults] = useState<CatalogPickerResult[]>([])

  const runSearch = async () => {
    setSearching(true)
    try {
      setResults(await searchCatalogForPicker(searchQ))
    } catch (e) {
      toast.error((e as Error).message || t('admin.adminHomePage.toasts.searchFailed', 'Search failed'))
    } finally {
      setSearching(false)
    }
  }

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (itemId === null) {
        throw new Error(t('admin.adminHomePage.hero.errors.itemRequired', 'Choose an item first'))
      }
      const from = fromLocalInput(activeFrom)
      if (!from) {
        throw new Error(t('admin.adminHomePage.hero.errors.activeFromRequired', 'Active-from date is required'))
      }
      const body = {
        item_id: itemId,
        annotation_md: annotation,
        cta_label: ctaLabel,
        cta_href: ctaHref.trim() || null,
        active_from: from,
        active_to: fromLocalInput(activeTo),
      }
      if (isEdit && pickId !== null) {
        return updateHeroPick(pickId, body)
      }
      return createHeroPick(body)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['home-admin-hero-picks'] })
      toast.success(
        isEdit
          ? t('admin.adminHomePage.toasts.heroUpdated', 'Hero pick updated')
          : t('admin.adminHomePage.toasts.heroCreated', 'Hero pick created')
      )
      onDone()
    },
    onError: (e: Error) =>
      toast.error(e.message || t('admin.adminHomePage.toasts.saveFailed', 'Save failed')),
  })

  const overLimit = annotation.length > ANNOTATION_SOFT_LIMIT

  return (
    <div>
      <button
        onClick={onDone}
        className="inline-flex items-center gap-1 text-sm text-earth-600 dark:text-earth-300 hover:text-lsc-rose mb-4"
      >
        <ArrowLeft className="w-4 h-4" aria-hidden="true" />
        {t('common.back', 'Back')}
      </button>

      <form
        onSubmit={(e) => {
          e.preventDefault()
          saveMutation.mutate()
        }}
        className="space-y-5"
      >
        {/* Item picker */}
        <fieldset className="space-y-2">
          <legend className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
            {t('admin.adminHomePage.hero.fields.item', 'Featured item')}
          </legend>
          {itemId !== null && (
            <div className="flex items-center gap-2 p-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-earth-50 dark:bg-earth-900/30">
              <span className="text-sm text-lsc-dark dark:text-lsc-cream flex-1">{itemLabel}</span>
              <button
                type="button"
                onClick={() => {
                  setItemId(null)
                  setItemLabel('')
                }}
                className="text-xs text-earth-600 hover:text-lsc-rose"
              >
                {t('common.change', 'Change')}
              </button>
            </div>
          )}
          {itemId === null && (
            <>
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-earth-600" aria-hidden="true" />
                  <input
                    value={searchQ}
                    onChange={(e) => setSearchQ(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault()
                        runSearch()
                      }
                    }}
                    placeholder={t('admin.adminHomePage.hero.search.placeholder', 'Search the catalog...')}
                    aria-label={t('admin.adminHomePage.hero.search.placeholder', 'Search the catalog...')}
                    className="w-full pl-8 pr-3 py-1.5 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-sm"
                  />
                </div>
                <button
                  type="button"
                  onClick={runSearch}
                  disabled={searching}
                  className="px-3 py-1.5 bg-lsc-rose text-white text-sm rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50"
                >
                  {searching ? '...' : t('common.search', 'Search')}
                </button>
              </div>
              {results.length > 0 && (
                <ul className="max-h-48 overflow-y-auto rounded-lg border border-lsc-border dark:border-earth-700">
                  {results.map((r) => (
                    <li key={r.id}>
                      <button
                        type="button"
                        onClick={() => {
                          setItemId(r.id)
                          setItemLabel(`${r.title}${r.author ? ` — ${r.author}` : ''}`)
                          setResults([])
                          setSearchQ('')
                        }}
                        className="w-full text-left px-3 py-2 hover:bg-earth-50 dark:hover:bg-earth-700/50"
                      >
                        <div className="text-sm text-lsc-dark dark:text-lsc-cream truncate">{r.title}</div>
                        <div className="text-xs text-earth-600">
                          {r.author || t('admin.adminHomePage.unknownAuthor', 'Unknown author')}
                          {r.item_type ? ` · ${r.item_type}` : ''}
                        </div>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </fieldset>

        {/* Annotation */}
        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <label htmlFor="hero-annotation" className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
              {t('admin.adminHomePage.hero.fields.annotation', 'Annotation (markdown)')}
            </label>
            <button
              type="button"
              onClick={() => setShowPreview((v) => !v)}
              className="text-xs text-earth-600 hover:text-lsc-rose"
            >
              {showPreview
                ? t('common.edit', 'Edit')
                : t('admin.adminHomePage.hero.preview', 'Preview')}
            </button>
          </div>
          {showPreview ? (
            <div className="prose prose-sm dark:prose-invert max-w-none p-3 rounded-lg border border-lsc-border dark:border-earth-700 bg-earth-50 dark:bg-earth-900/30 min-h-[8rem]">
              <ReactMarkdown>{annotation || '*nothing yet*'}</ReactMarkdown>
            </div>
          ) : (
            <textarea
              id="hero-annotation"
              value={annotation}
              onChange={(e) => setAnnotation(e.target.value)}
              rows={6}
              className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-sm font-mono"
            />
          )}
          <div className={`text-xs ${overLimit ? 'text-status-warning-600' : 'text-earth-600'}`}>
            {annotation.length} / {ANNOTATION_SOFT_LIMIT}
            {overLimit
              ? ` · ${t('admin.adminHomePage.hero.annotationOver', 'Over recommended length — may truncate visually')}`
              : ''}
          </div>
        </div>

        {/* CTA */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="space-y-1">
            <label htmlFor="hero-cta-label" className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
              {t('admin.adminHomePage.hero.fields.ctaLabel', 'CTA label')}
            </label>
            <input
              id="hero-cta-label"
              value={ctaLabel}
              onChange={(e) => setCtaLabel(e.target.value)}
              maxLength={120}
              required
              className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-sm"
            />
          </div>
          <div className="space-y-1">
            <label htmlFor="hero-cta-href" className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
              {t('admin.adminHomePage.hero.fields.ctaHref', 'CTA link (optional)')}
            </label>
            <input
              id="hero-cta-href"
              value={ctaHref ?? ''}
              onChange={(e) => setCtaHref(e.target.value)}
              maxLength={500}
              placeholder="/catalog/123"
              className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-sm"
            />
          </div>
        </div>

        {/* Active window */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="space-y-1">
            <label htmlFor="hero-active-from" className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
              {t('admin.adminHomePage.hero.fields.activeFrom', 'Active from')}
            </label>
            <input
              id="hero-active-from"
              type="datetime-local"
              value={activeFrom}
              onChange={(e) => setActiveFrom(e.target.value)}
              required
              className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-sm"
            />
          </div>
          <div className="space-y-1">
            <label htmlFor="hero-active-to" className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
              {t('admin.adminHomePage.hero.fields.activeTo', 'Active to (optional)')}
            </label>
            <input
              id="hero-active-to"
              type="datetime-local"
              value={activeTo}
              onChange={(e) => setActiveTo(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-sm"
            />
          </div>
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
          <button
            type="button"
            onClick={onDone}
            className="px-3 py-2 text-sm text-earth-600 dark:text-earth-300 hover:text-lsc-dark"
          >
            {t('common.cancel', 'Cancel')}
          </button>
        </div>
      </form>
    </div>
  )
}
