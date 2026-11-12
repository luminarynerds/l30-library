/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Edit, Eye, EyeOff, FileText, Loader2, Plus, Save, Trash2, X } from 'lucide-react'
import { useTranslation } from '@/i18n'
import { TARGET_LEVELS, targetLevelBadgeClasses, formatDate } from './ban-tracker-data'
import type { LetterTemplate, LetterTemplateFormData } from './types'

function FormInput({
  label,
  value,
  onChange,
  type = 'text',
  required = false,
  placeholder,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  type?: string
  required?: boolean
  placeholder?: string
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
        {label}
      </label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        placeholder={placeholder}
        className="w-full px-3 py-2 text-sm rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream placeholder-lsc-dark/40 dark:placeholder-lsc-cream/40 focus:outline-none focus:ring-2 focus:ring-lsc-rose/50"
      />
    </div>
  )
}

function FormSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  options: { value: string; label: string }[]
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
        {label}
      </label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 text-sm rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose/50"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  )
}

export function LetterTemplatesTab({
  templates,
  loading,
  showForm,
  editingId,
  form,
  onFormChange,
  onToggleForm,
  onSubmit,
  onEdit,
  onDelete,
  onToggleActive,
  submitting,
  expandedId,
  onToggleExpand,
}: {
  templates: LetterTemplate[]
  loading: boolean
  showForm: boolean
  editingId: number | null
  form: LetterTemplateFormData
  onFormChange: (f: LetterTemplateFormData) => void
  onToggleForm: () => void
  onSubmit: (e: React.FormEvent) => void
  onEdit: (t: LetterTemplate) => void
  onDelete: (id: number) => void
  onToggleActive: (t: LetterTemplate) => void
  submitting: boolean
  expandedId: number | null
  onToggleExpand: (id: number) => void
}) {
  const { t } = useTranslation()
  if (loading) {
    return (
      <div className="flex items-center justify-center h-48">
        <Loader2 className="h-8 w-8 motion-safe:animate-spin text-lsc-dark/70 dark:text-lsc-cream/70" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          {templates.length} template{templates.length !== 1 ? 's' : ''}
        </p>
        <button
          onClick={onToggleForm}
          className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors text-sm font-medium"
        >
          {showForm ? <X className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
          {showForm ? 'Cancel' : 'Add Template'}
        </button>
      </div>

      {/* Template Form */}
      {showForm && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-6">
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
            {editingId ? 'Edit Template' : 'New Letter Template'}
          </h3>
          <form onSubmit={onSubmit} className="space-y-4">
            <FormInput
              label="Title *"
              value={form.title}
              onChange={(v) => onFormChange({ ...form, title: v })}
              required
            />
            <FormInput
              label="Subject Line"
              value={form.subject_line}
              onChange={(v) => onFormChange({ ...form, subject_line: v })}
            />
            <div>
              <label className="block text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                Body Template *
              </label>
              <textarea
                value={form.body_template}
                onChange={(e) => onFormChange({ ...form, body_template: e.target.value })}
                rows={8}
                required
                className="w-full px-3 py-2 text-sm rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose/50 resize-y font-mono"
                placeholder={t('admin.adminBanTracker.dearRecipientNameIAm')}
              />
            </div>
            <div className="flex flex-col sm:flex-row gap-4">
              <FormSelect
                label="Target Level"
                value={form.target_level}
                onChange={(v) =>
                  onFormChange({ ...form, target_level: v as LetterTemplateFormData['target_level'] })
                }
                options={TARGET_LEVELS.map((t) => ({ value: t.value, label: t.label }))}
              />
              <div className="flex items-center gap-2 pt-6">
                <input
                  type="checkbox"
                  id="template-active"
                  checked={form.is_active}
                  onChange={(e) => onFormChange({ ...form, is_active: e.target.checked })}
                  className="rounded border-lsc-border dark:border-earth-600 text-lsc-rose focus:ring-lsc-rose"
                />
                <label
                  htmlFor="template-active"
                  className="text-sm text-lsc-dark dark:text-lsc-cream"
                >
                  Active
                </label>
              </div>
            </div>
            <div className="flex justify-end">
              <button
                type="submit"
                disabled={submitting}
                className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50 transition-colors text-sm font-medium"
              >
                {submitting ? (
                  <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                ) : (
                  <Save className="w-4 h-4" />
                )}
                {editingId ? 'Update Template' : 'Create Template'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Template List */}
      {templates.length === 0 ? (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-8 text-center">
          <FileText className="w-8 h-8 text-lsc-dark/30 dark:text-lsc-cream/60 mx-auto mb-2" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">
            No letter templates yet. Create one to get started with advocacy.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {templates.map((template) => (
            <div
              key={template.id}
              className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden"
            >
              {/* Template header row */}
              {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events */}
              <div
                className="flex items-center justify-between p-4 cursor-pointer hover:bg-earth-50 dark:hover:bg-earth-700/30 transition-colors"
                onClick={() => onToggleExpand(template.id)}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <FileText className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/60 flex-shrink-0" />
                  <span className="font-medium text-lsc-dark dark:text-lsc-cream truncate">
                    {template.title}
                  </span>
                  <span
                    className={`text-xs font-medium px-2.5 py-0.5 rounded-full flex-shrink-0 ${targetLevelBadgeClasses(
                      template.target_level
                    )}`}
                  >
                    {template.target_level}
                  </span>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      onToggleActive(template)
                    }}
                    className="p-1.5 rounded-lg hover:bg-earth-100 dark:hover:bg-earth-700 transition-colors"
                    title={template.is_active ? 'Deactivate' : 'Activate'}
                  >
                    {template.is_active ? (
                      <Eye className="w-4 h-4 text-status-success-600 dark:text-status-success-400" />
                    ) : (
                      <EyeOff className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/60" />
                    )}
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      onEdit(template)
                    }}
                    className="p-1.5 rounded-lg hover:bg-earth-100 dark:hover:bg-earth-700 transition-colors"
                    title="Edit"
                  >
                    <Edit className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/60" />
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      onDelete(template.id)
                    }}
                    className="p-1.5 rounded-lg hover:bg-status-danger-50 dark:hover:bg-status-danger-900/20 transition-colors"
                    title="Delete"
                  >
                    <Trash2 className="w-4 h-4 text-status-danger-500" />
                  </button>
                </div>
              </div>
              {/* Expanded content */}
              {expandedId === template.id && (
                <div className="border-t border-lsc-border dark:border-earth-700 p-4 bg-earth-50/50 dark:bg-earth-800/50">
                  {template.subject_line && (
                    <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">
                      <span className="font-medium">Subject:</span> {template.subject_line}
                    </p>
                  )}
                  <pre className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80 whitespace-pre-wrap font-mono bg-lsc-white dark:bg-earth-800 p-3 rounded-lg border border-lsc-border dark:border-earth-700 max-h-64 overflow-y-auto">
                    {template.body_template}
                  </pre>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-2">
                    Updated {formatDate(template.updated_at)}
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
