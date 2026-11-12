/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Shelf editor. Renders a dynamic params form per query_kind.
 *
 * query_kind params (mirrors backend resolver in PR #670):
 *   - new_arrivals    : { since_days?: number }
 *   - staff_picks     : {}
 *   - subject         : { subject: string }
 *   - format          : { format: string }   // matches catalog_items.media_format enum
 *   - circulation_top : { window_days?: number }
 *   - manual_list     : { item_ids: number[] }
 */
import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Search, X } from 'lucide-react'
import toast from 'react-hot-toast'
import { useTranslation } from '@/i18n'
import {
  CatalogPickerResult,
  createShelf,
  HOME_SHELF_QUERY_KINDS,
  HomeShelfQueryKind,
  searchCatalogForPicker,
  ShelfAdminRead,
  updateShelf,
} from '@/api/home'

interface Props {
  shelfId: number | null
  initial: ShelfAdminRead | null
  onDone: () => void
}

function defaultParamsFor(kind: HomeShelfQueryKind): Record<string, unknown> {
  switch (kind) {
    case 'new_arrivals':
      return { since_days: 30 }
    case 'circulation_top':
      return { window_days: 30 }
    case 'subject':
      return { subject: '' }
    case 'format':
      return { format: '' }
    case 'manual_list':
      return { item_ids: [] }
    default:
      return {}
  }
}

export function ShelfEditor({ shelfId, initial, onDone }: Props) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const isEdit = shelfId !== null

  const [slug, setSlug] = useState(initial?.slug ?? '')
  const [heading, setHeading] = useState(initial?.heading ?? '')
  const [description, setDescription] = useState(initial?.description ?? '')
  const [queryKind, setQueryKind] = useState<HomeShelfQueryKind>(
    (initial?.query_kind as HomeShelfQueryKind) ?? 'new_arrivals'
  )
  const [queryParams, setQueryParams] = useState<Record<string, unknown>>(
    initial?.query_params ?? defaultParamsFor((initial?.query_kind as HomeShelfQueryKind) ?? 'new_arrivals')
  )
  const [maxItems, setMaxItems] = useState<number>(initial?.max_items ?? 6)
  const [viewAllHref, setViewAllHref] = useState(initial?.view_all_href ?? '')
  const [isActive, setIsActive] = useState(initial?.is_active ?? true)

  const saveMutation = useMutation({
    mutationFn: async () => {
      const body = {
        slug,
        heading,
        description,
        query_kind: queryKind,
        query_params: queryParams,
        max_items: maxItems,
        view_all_href: viewAllHref.trim() || null,
        is_active: isActive,
      }
      if (isEdit && shelfId !== null) {
        return updateShelf(shelfId, body)
      }
      return createShelf(body)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['home-admin-shelves'] })
      toast.success(
        isEdit
          ? t('admin.adminHomePage.toasts.shelfUpdated', 'Shelf updated')
          : t('admin.adminHomePage.toasts.shelfCreated', 'Shelf created')
      )
      onDone()
    },
    onError: (e: Error) =>
      toast.error(e.message || t('admin.adminHomePage.toasts.saveFailed', 'Save failed')),
  })

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
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="space-y-1">
            <label htmlFor="shelf-slug" className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
              {t('admin.adminHomePage.shelves.fields.slug', 'Slug')}
            </label>
            <input
              id="shelf-slug"
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
              required
              maxLength={120}
              className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-sm font-mono"
            />
          </div>
          <div className="space-y-1">
            <label htmlFor="shelf-heading" className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
              {t('admin.adminHomePage.shelves.fields.heading', 'Heading')}
            </label>
            <input
              id="shelf-heading"
              value={heading}
              onChange={(e) => setHeading(e.target.value)}
              required
              maxLength={200}
              className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-sm"
            />
          </div>
        </div>

        <div className="space-y-1">
          <label htmlFor="shelf-description" className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
            {t('admin.adminHomePage.shelves.fields.description', 'Description')}
          </label>
          <input
            id="shelf-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            maxLength={500}
            className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-sm"
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="space-y-1">
            <label htmlFor="shelf-kind" className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
              {t('admin.adminHomePage.shelves.fields.queryKind', 'Query kind')}
            </label>
            <select
              id="shelf-kind"
              value={queryKind}
              onChange={(e) => {
                const next = e.target.value as HomeShelfQueryKind
                setQueryKind(next)
                setQueryParams(defaultParamsFor(next))
              }}
              className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-sm"
            >
              {HOME_SHELF_QUERY_KINDS.map((k) => (
                <option key={k} value={k}>
                  {k}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-1">
            <label htmlFor="shelf-max" className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
              {t('admin.adminHomePage.shelves.fields.maxItems', 'Max items')}
            </label>
            <input
              id="shelf-max"
              type="number"
              min={1}
              max={24}
              value={maxItems}
              onChange={(e) => setMaxItems(Number(e.target.value))}
              className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-sm"
            />
          </div>
          <div className="space-y-1">
            <label htmlFor="shelf-view-all" className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
              {t('admin.adminHomePage.shelves.fields.viewAllHref', 'View-all link (optional)')}
            </label>
            <input
              id="shelf-view-all"
              value={viewAllHref ?? ''}
              onChange={(e) => setViewAllHref(e.target.value)}
              maxLength={500}
              placeholder="/catalog?subject=Cooking"
              className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-sm"
            />
          </div>
        </div>

        <QueryParamsForm
          kind={queryKind}
          params={queryParams}
          maxItems={maxItems}
          onChange={setQueryParams}
        />

        <label className="inline-flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream">
          <input
            type="checkbox"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
          />
          {t('admin.adminHomePage.shelves.fields.isActive', 'Active')}
        </label>

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

// ---- Per-kind params form ----------------------------------------------

interface ParamsFormProps {
  kind: HomeShelfQueryKind
  params: Record<string, unknown>
  maxItems: number
  onChange: (next: Record<string, unknown>) => void
}

function QueryParamsForm({ kind, params, maxItems, onChange }: ParamsFormProps) {
  const { t } = useTranslation()

  if (kind === 'staff_picks') {
    return (
      <p className="text-xs text-earth-600 dark:text-earth-400">
        {t('admin.adminHomePage.shelves.kindHelp.staff_picks', 'No parameters — shows the newest additions across all active staff-picks lists (managed under Staff Picks).')}
      </p>
    )
  }

  if (kind === 'new_arrivals') {
    return (
      <div className="space-y-1">
        <label htmlFor="param-since-days" className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
          {t('admin.adminHomePage.shelves.fields.sinceDays', 'Since how many days (optional)')}
        </label>
        <input
          id="param-since-days"
          type="number"
          min={1}
          value={Number(params.since_days ?? '') || ''}
          onChange={(e) =>
            onChange({ ...params, since_days: e.target.value ? Number(e.target.value) : undefined })
          }
          className="w-full sm:w-48 px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-sm"
        />
      </div>
    )
  }

  if (kind === 'circulation_top') {
    return (
      <div className="space-y-1">
        <label htmlFor="param-window-days" className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
          {t('admin.adminHomePage.shelves.fields.windowDays', 'Window in days')}
        </label>
        <input
          id="param-window-days"
          type="number"
          min={1}
          value={Number(params.window_days ?? '') || ''}
          onChange={(e) =>
            onChange({ ...params, window_days: e.target.value ? Number(e.target.value) : undefined })
          }
          className="w-full sm:w-48 px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-sm"
        />
        <p className="text-xs text-earth-600 dark:text-earth-400">
          {t(
            'admin.adminHomePage.shelves.kindHelp.circulation_top',
            'Backend resolver is a stub in PR #670; will populate when circulation data is wired.'
          )}
        </p>
      </div>
    )
  }

  if (kind === 'subject') {
    return (
      <div className="space-y-1">
        <label htmlFor="param-subject" className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
          {t('admin.adminHomePage.shelves.fields.subject', 'Subject')}
        </label>
        <input
          id="param-subject"
          value={String(params.subject ?? '')}
          onChange={(e) => onChange({ ...params, subject: e.target.value })}
          required
          placeholder="Cooking"
          className="w-full sm:w-96 px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-sm"
        />
        <p className="text-xs text-earth-600 dark:text-earth-400">
          {t(
            'admin.adminHomePage.shelves.kindHelp.subject',
            'Matches catalog_items.subjects (comma- and semicolon-delimited subjects both supported by the backend).'
          )}
        </p>
      </div>
    )
  }

  if (kind === 'format') {
    return (
      <div className="space-y-1">
        <label htmlFor="param-format" className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
          {t('admin.adminHomePage.shelves.fields.format', 'Media format')}
        </label>
        <input
          id="param-format"
          value={String(params.format ?? '')}
          onChange={(e) => onChange({ ...params, format: e.target.value })}
          required
          placeholder="audiobook"
          className="w-full sm:w-96 px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-sm"
        />
        <p className="text-xs text-earth-600 dark:text-earth-400">
          {t(
            'admin.adminHomePage.shelves.kindHelp.format',
            'Matches catalog_items.media_format enum (lowercase).'
          )}
        </p>
      </div>
    )
  }

  // manual_list
  return <ManualListPicker params={params} maxItems={maxItems} onChange={onChange} />
}

// ---- Manual list picker -------------------------------------------------

interface ManualPickerProps {
  params: Record<string, unknown>
  maxItems: number
  onChange: (next: Record<string, unknown>) => void
}

interface PickedItem {
  id: number
  title: string
  author: string | null
}

function ManualListPicker({ params, maxItems, onChange }: ManualPickerProps) {
  const { t } = useTranslation()
  const itemIds: number[] = Array.isArray(params.item_ids) ? (params.item_ids as number[]) : []
  // Local denormalized cache so we can render labels for current selections.
  // First-edit case: only IDs in params; titles populate as user searches.
  const [labels, setLabels] = useState<Record<number, PickedItem>>({})
  const [q, setQ] = useState('')
  const [searching, setSearching] = useState(false)
  const [results, setResults] = useState<CatalogPickerResult[]>([])

  const runSearch = async () => {
    setSearching(true)
    try {
      setResults(await searchCatalogForPicker(q))
    } catch (e) {
      toast.error((e as Error).message || t('admin.adminHomePage.toasts.searchFailed', 'Search failed'))
    } finally {
      setSearching(false)
    }
  }

  const add = (r: CatalogPickerResult) => {
    if (itemIds.includes(r.id)) return
    if (itemIds.length >= maxItems) {
      toast.error(t('admin.adminHomePage.shelves.atMax', 'At max-items limit'))
      return
    }
    setLabels((prev) => ({ ...prev, [r.id]: { id: r.id, title: r.title, author: r.author } }))
    onChange({ ...params, item_ids: [...itemIds, r.id] })
  }

  const remove = (id: number) => {
    onChange({ ...params, item_ids: itemIds.filter((x) => x !== id) })
  }

  return (
    <div className="space-y-2">
      <div className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
        {t('admin.adminHomePage.shelves.fields.manualList', 'Items')}{' '}
        <span className="text-xs text-earth-600">
          ({itemIds.length} / {maxItems})
        </span>
      </div>
      {itemIds.length > 0 && (
        <ul className="space-y-1">
          {itemIds.map((id) => {
            const info = labels[id]
            return (
              <li
                key={id}
                className="flex items-center gap-2 p-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-earth-50 dark:bg-earth-900/30"
              >
                <span className="text-sm flex-1 truncate">
                  {info ? `${info.title}${info.author ? ` — ${info.author}` : ''}` : `#${id}`}
                </span>
                <button
                  type="button"
                  onClick={() => remove(id)}
                  className="p-1 text-status-danger-400 hover:text-status-danger-600"
                  aria-label={t('common.remove', 'Remove')}
                >
                  <X className="w-4 h-4" />
                </button>
              </li>
            )
          })}
        </ul>
      )}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-earth-600" aria-hidden="true" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
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
            <li key={r.id} className="flex items-center gap-2 px-3 py-2 hover:bg-earth-50 dark:hover:bg-earth-700/50">
              <div className="flex-1 min-w-0">
                <div className="text-sm truncate">{r.title}</div>
                <div className="text-xs text-earth-600 truncate">
                  {r.author || t('admin.adminHomePage.unknownAuthor', 'Unknown author')}
                </div>
              </div>
              <button
                type="button"
                onClick={() => add(r)}
                disabled={itemIds.includes(r.id)}
                className="px-2 py-1 text-xs bg-lsc-rose text-white rounded hover:bg-lsc-rose/90 disabled:opacity-50"
              >
                {itemIds.includes(r.id)
                  ? t('admin.adminHomePage.shelves.added', 'Added')
                  : t('common.add', 'Add')}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
