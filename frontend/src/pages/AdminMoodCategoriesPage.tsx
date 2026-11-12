/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  CloudSun,
  Laugh,
  Heart,
  Flame,
  Sparkles,
  HandHeart,
  BookOpen,
  Compass,
  Coffee,
  Music,
  Smile,
  Sun,
  Plus,
  Pencil,
  Trash2,
  X,
  ArrowUp,
  ArrowDown,
  Eye,
  EyeOff,
} from 'lucide-react'
import { AdminShell } from '@/components/shells/AdminShell'
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import { useAdminMoodCategories } from '@/hooks/useMoodCategories'
import {
  ALLOWED_MOOD_TAGS,
  createMoodCategory,
  deleteMoodCategory,
  reorderMoodCategories,
  updateMoodCategory,
  type MoodCategory,
  type MoodCategoryCreatePayload,
  type MoodTag,
} from '@/api/domains/catalog/mood-categories-api'

// Curated lucide icon picker. Add to this list when you need more options;
// the picker is intentionally bounded so admins don't have to know lucide names.
const ICON_OPTIONS = {
  CloudSun,
  Laugh,
  Heart,
  Flame,
  Sparkles,
  HandHeart,
  BookOpen,
  Compass,
  Coffee,
  Music,
  Smile,
  Sun,
} as const

type IconName = keyof typeof ICON_OPTIONS

function MoodIconByName({ name, className }: { name: string; className?: string }) {
  const Icon = (ICON_OPTIONS as Record<string, React.FC<{ className?: string }>>)[name]
  if (!Icon) return null
  return <Icon className={className ?? 'w-5 h-5'} aria-hidden />
}

interface FormState {
  label: string
  slug: string
  icon: IconName
  tags: MoodTag[]
  keywordsText: string
  is_active: boolean
}

const EMPTY_FORM: FormState = {
  label: '',
  slug: '',
  icon: 'Sparkles',
  tags: [],
  keywordsText: '',
  is_active: true,
}

function toForm(cat: MoodCategory): FormState {
  return {
    label: cat.label,
    slug: cat.slug,
    icon: (ICON_OPTIONS as Record<string, unknown>)[cat.icon]
      ? (cat.icon as IconName)
      : 'Sparkles',
    tags: cat.tags.filter((t): t is MoodTag =>
      (ALLOWED_MOOD_TAGS as readonly string[]).includes(t)
    ),
    keywordsText: cat.keywords.join(', '),
    is_active: cat.is_active,
  }
}

function fromForm(f: FormState): MoodCategoryCreatePayload {
  const keywords = f.keywordsText
    .split(',')
    .map((k) => k.trim())
    .filter(Boolean)
  return {
    label: f.label.trim(),
    slug: f.slug.trim().toLowerCase(),
    icon: f.icon,
    tags: f.tags,
    keywords,
    is_active: f.is_active,
  }
}

export default function AdminMoodCategoriesPage(): React.ReactElement {
  const { data: categories, isLoading, error } = useAdminMoodCategories()
  const qc = useQueryClient()
  const [editing, setEditing] = useState<MoodCategory | null>(null)
  const [creating, setCreating] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['mood-categories'] })
  }

  const createMut = useMutation({
    mutationFn: createMoodCategory,
    onSuccess: () => {
      invalidate()
      setCreating(false)
      setNotice('Bucket created')
    },
  })
  const updateMut = useMutation({
    mutationFn: (vars: { id: number; payload: MoodCategoryCreatePayload }) =>
      updateMoodCategory(vars.id, vars.payload),
    onSuccess: () => {
      invalidate()
      setEditing(null)
      setNotice('Bucket updated')
    },
  })
  const deleteMut = useMutation({
    mutationFn: deleteMoodCategory,
    onSuccess: () => {
      invalidate()
      setNotice('Bucket deleted')
    },
  })
  const reorderMut = useMutation({
    mutationFn: reorderMoodCategories,
    onSuccess: () => invalidate(),
  })

  const handleMove = (cat: MoodCategory, dir: -1 | 1) => {
    if (!categories) return
    const idx = categories.findIndex((c) => c.id === cat.id)
    const target = idx + dir
    if (idx < 0 || target < 0 || target >= categories.length) return
    const ids = categories.map((c) => c.id)
    const tmp = ids[idx]!; ids[idx] = ids[target]!; ids[target] = tmp
    reorderMut.mutate(ids)
  }

  const handleDelete = (cat: MoodCategory) => {
    if (!window.confirm(`Delete "${cat.label}"? This cannot be undone.`)) return
    deleteMut.mutate(cat.id)
  }

  const mutationError =
    (createMut.error as Error | null)?.message ||
    (updateMut.error as Error | null)?.message ||
    (deleteMut.error as Error | null)?.message ||
    (reorderMut.error as Error | null)?.message ||
    null

  return (
    <AdminShell
      title="Mood categories"
      subtitle='The "I want X" buckets shown on the catalog landing page'
      loading={isLoading}
      error={error ? String(error) : null}
      actions={
        <button
          onClick={() => setCreating(true)}
          className="inline-flex items-center gap-1 px-3 py-2 bg-lsc-rose text-white text-sm font-medium rounded-lg hover:bg-lsc-rose/90"
        >
          <Plus className="w-4 h-4" /> Add bucket
        </button>
      }
    >
      {notice && (
        <div role="status" aria-live="polite" className="mb-4 text-sm text-status-success-700 dark:text-status-success-200 bg-status-success-100 dark:bg-status-success-900 px-3 py-2 rounded">
          {notice}
        </div>
      )}
      {mutationError && (
        <div role="alert" className="mb-4 text-sm text-status-danger-700 dark:text-status-danger-200 bg-status-danger-100 dark:bg-status-danger-900 px-3 py-2 rounded">
          {mutationError}
        </div>
      )}

      <div className="bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-lsc-cream/40 dark:bg-earth-900 text-left text-xs uppercase tracking-wide text-lsc-dark/60 dark:text-lsc-cream/60">
            <tr>
              <th className="px-3 py-2 w-16">Order</th>
              <th className="px-3 py-2 w-10">Icon</th>
              <th className="px-3 py-2">Label</th>
              <th className="px-3 py-2">Slug</th>
              <th className="px-3 py-2">Tags</th>
              <th className="px-3 py-2 w-24">Active</th>
              <th className="px-3 py-2 w-32 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {(categories ?? []).map((cat, idx) => (
              <tr
                key={cat.id}
                className="border-t border-lsc-border dark:border-earth-700"
              >
                <td className="px-3 py-2">
                  <div className="flex flex-col gap-1">
                    <button
                      onClick={() => handleMove(cat, -1)}
                      disabled={idx === 0 || reorderMut.isPending}
                      className="w-7 h-7 rounded hover:bg-lsc-cream dark:hover:bg-earth-700 disabled:opacity-30"
                      aria-label={`Move "${cat.label}" up`}
                    >
                      <ArrowUp className="w-4 h-4 mx-auto" />
                    </button>
                    <button
                      onClick={() => handleMove(cat, 1)}
                      disabled={idx === (categories?.length ?? 0) - 1 || reorderMut.isPending}
                      className="w-7 h-7 rounded hover:bg-lsc-cream dark:hover:bg-earth-700 disabled:opacity-30"
                      aria-label={`Move "${cat.label}" down`}
                    >
                      <ArrowDown className="w-4 h-4 mx-auto" />
                    </button>
                  </div>
                </td>
                <td className="px-3 py-2">
                  <MoodIconByName name={cat.icon} className="w-5 h-5 text-lsc-rose" />
                </td>
                <td className="px-3 py-2 text-lsc-dark dark:text-lsc-cream">{cat.label}</td>
                <td className="px-3 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 font-mono text-xs">
                  /{cat.slug}
                </td>
                <td className="px-3 py-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                  {cat.tags.join(', ')}
                </td>
                <td className="px-3 py-2">
                  {cat.is_active ? (
                    <span className="inline-flex items-center gap-1 text-status-success-700 dark:text-status-success-200 text-xs">
                      <Eye className="w-3.5 h-3.5" /> Visible
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-lsc-dark/50 dark:text-lsc-cream/50 text-xs">
                      <EyeOff className="w-3.5 h-3.5" /> Hidden
                    </span>
                  )}
                </td>
                <td className="px-3 py-2 text-right">
                  <button
                    onClick={() => setEditing(cat)}
                    className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded hover:bg-lsc-cream dark:hover:bg-earth-700"
                  >
                    <Pencil className="w-3.5 h-3.5" /> Edit
                  </button>
                  <button
                    onClick={() => handleDelete(cat)}
                    className="ml-1 inline-flex items-center gap-1 px-2 py-1 text-xs rounded text-status-danger-700 dark:text-status-danger-200 hover:bg-status-danger-100 dark:hover:bg-status-danger-900"
                  >
                    <Trash2 className="w-3.5 h-3.5" /> Delete
                  </button>
                </td>
              </tr>
            ))}
            {categories && categories.length === 0 && (
              <tr>
                <td colSpan={7} className="px-3 py-8 text-center text-lsc-dark/60 dark:text-lsc-cream/60 text-sm">
                  No mood buckets defined yet. Click "Add bucket" to create one.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {(creating || editing) && (
        <EditModal
          initial={editing ? toForm(editing) : EMPTY_FORM}
          title={editing ? `Edit "${editing.label}"` : 'Add mood bucket'}
          onClose={() => {
            setCreating(false)
            setEditing(null)
          }}
          onSave={(f) => {
            const payload = fromForm(f)
            if (editing) {
              updateMut.mutate({ id: editing.id, payload })
            } else {
              createMut.mutate(payload)
            }
          }}
          pending={createMut.isPending || updateMut.isPending}
        />
      )}
    </AdminShell>
  )
}

interface EditModalProps {
  initial: FormState
  title: string
  pending: boolean
  onClose: () => void
  onSave: (f: FormState) => void
}

function EditModal({ initial, title, pending, onClose, onSave }: EditModalProps) {
  const [form, setForm] = useState<FormState>(initial)

  const toggleTag = (tag: MoodTag) => {
    setForm((f) => ({
      ...f,
      tags: f.tags.includes(tag) ? f.tags.filter((t) => t !== tag) : [...f.tags, tag],
    }))
  }

  const canSubmit = form.label.trim() && form.slug.trim() && form.tags.length > 0

  return (
    <ModalBackdrop onClose={onClose} labelledBy="mood-category-modal-title">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-5 py-3 border-b border-lsc-border dark:border-earth-700">
          <h2 id="mood-category-modal-title" className="text-base font-semibold text-lsc-dark dark:text-lsc-cream">{title}</h2>
          <button onClick={onClose} aria-label="Close" className="text-lsc-dark/60 dark:text-lsc-cream/60 hover:text-lsc-dark dark:hover:text-lsc-cream">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <div>
            <label htmlFor="mood-cat-label" className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Label (shown to patrons)</label>
            <input
              id="mood-cat-label"
              type="text"
              value={form.label}
              onChange={(e) => setForm({ ...form, label: e.target.value })}
              placeholder="I want something quiet"
              className="w-full px-3 py-2 text-sm bg-lsc-cream/30 dark:bg-earth-900 border border-lsc-border dark:border-earth-700 rounded focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              maxLength={120}
            />
          </div>

          <div>
            <label htmlFor="mood-cat-slug" className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Slug (URL: /catalog/mood/<em>slug</em>)</label>
            <input
              id="mood-cat-slug"
              type="text"
              value={form.slug}
              onChange={(e) => setForm({ ...form, slug: e.target.value })}
              placeholder="quiet"
              className="w-full px-3 py-2 text-sm font-mono bg-lsc-cream/30 dark:bg-earth-900 border border-lsc-border dark:border-earth-700 rounded focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              maxLength={60}
              pattern="[a-z0-9-]+"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">Icon</label>
            <div className="grid grid-cols-6 gap-2">
              {Object.entries(ICON_OPTIONS).map(([name, Icon]) => (
                <button
                  key={name}
                  type="button"
                  onClick={() => setForm({ ...form, icon: name as IconName })}
                  className={`flex items-center justify-center h-12 rounded border ${
                    form.icon === name
                      ? 'border-lsc-rose bg-lsc-rose/10'
                      : 'border-lsc-border dark:border-earth-700 hover:bg-lsc-cream dark:hover:bg-earth-700'
                  }`}
                  aria-label={name}
                  aria-pressed={form.icon === name}
                >
                  <Icon className="w-5 h-5 text-lsc-rose" />
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
              Mood tags (which per-item moods this bucket aggregates)
            </label>
            <div className="flex flex-wrap gap-2">
              {ALLOWED_MOOD_TAGS.map((tag) => (
                <button
                  key={tag}
                  type="button"
                  onClick={() => toggleTag(tag as MoodTag)}
                  className={`px-3 py-1 text-xs rounded-full border ${
                    form.tags.includes(tag as MoodTag)
                      ? 'border-lsc-rose bg-lsc-rose/10 text-lsc-rose'
                      : 'border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700'
                  }`}
                  aria-pressed={form.tags.includes(tag as MoodTag)}
                >
                  {tag}
                </button>
              ))}
            </div>
            <p className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50 mt-2">
              At least one tag is required. These match the per-item mood values used by the catalog.
            </p>
          </div>

          <div>
            <label htmlFor="mood-cat-keywords" className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              Subject keywords (comma-separated)
            </label>
            <textarea
              id="mood-cat-keywords"
              value={form.keywordsText}
              onChange={(e) => setForm({ ...form, keywordsText: e.target.value })}
              placeholder="poetry, nature, mindfulness, gardening"
              rows={3}
              className="w-full px-3 py-2 text-sm bg-lsc-cream/30 dark:bg-earth-900 border border-lsc-border dark:border-earth-700 rounded focus:outline-none focus:ring-2 focus:ring-lsc-rose"
            />
            <p className="text-xs text-lsc-dark/50 dark:text-lsc-cream/50 mt-1">
              Items whose Subjects field contains any of these keywords will appear under this bucket.
            </p>
          </div>

          <label className="flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
              className="w-4 h-4"
            />
            Visible to patrons
          </label>
        </div>

        <div className="flex items-center justify-end gap-2 px-5 py-3 border-t border-lsc-border dark:border-earth-700">
          <button
            onClick={onClose}
            className="px-3 py-2 text-sm text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 rounded"
          >
            Cancel
          </button>
          <button
            onClick={() => onSave(form)}
            disabled={!canSubmit || pending}
            className="px-3 py-2 text-sm bg-lsc-rose text-white rounded hover:bg-lsc-rose/90 disabled:opacity-50"
          >
            {pending ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </ModalBackdrop>
  )
}
