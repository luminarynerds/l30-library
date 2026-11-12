/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  listTemplates,
  getTemplate,
  deleteTemplate,
  type ProgramTemplateListItem,
  type ProgramTemplate,
} from '@/api/program-planning-api'
import {
  Plus, Copy, Trash2, FileText, Users, Search, Star, Loader2, ChevronRight,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useTranslation } from '@/i18n'
import ConfirmDialog from '@/components/ConfirmDialog'
import { clean } from '@/lib/utils'
import { TEMPLATE_CATEGORIES } from '../constants'
import CreateTemplateModal from './CreateTemplateModal'
import CopyFromProgramModal from './CopyFromProgramModal'
import TemplateDetailModal from './TemplateDetailModal'

function TemplateCard({
  template,
  onView,
  onDelete,
}: {
  template: ProgramTemplateListItem
  onView: () => void
  onDelete: () => void
}) {
  const categoryLabel = TEMPLATE_CATEGORIES.find(c => c.value === template.category)?.label || template.category

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-5 hover:shadow-md transition-shadow">
      <div className="flex justify-between items-start mb-3">
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70">
          {categoryLabel}
        </span>
        <button
          onClick={onDelete}
          className="text-lsc-dark/70 hover:text-status-danger-500 dark:text-lsc-cream/70 dark:hover:text-status-danger-400 transition-colors"
          aria-label={`Deactivate ${template.name}`}
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

      <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-1">
        {template.name}
      </h3>

      {template.description && (
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-3 line-clamp-2" title={template.description}>
          {template.description}
        </p>
      )}

      <div className="flex flex-wrap gap-2 mb-4 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
        <span className="flex items-center gap-1">
          <Users className="w-3 h-3" />
          {template.target_audience}
        </span>
        <span className="flex items-center gap-1">
          <Star className="w-3 h-3" />
          Used {template.times_used}x
        </span>
      </div>

      <button
        onClick={onView}
        className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm bg-earth-50 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-100 dark:hover:bg-earth-600 transition-colors"
      >
        View Details
        <ChevronRight className="w-4 h-4" />
      </button>
    </div>
  )
}

function TemplateLibraryTab() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const [categoryFilter, setCategoryFilter] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [selectedTemplate, setSelectedTemplate] = useState<ProgramTemplate | null>(null)
  const [showCopyFromProgramModal, setShowCopyFromProgramModal] = useState(false)

  const { data: templates, isLoading } = useQuery({
    queryKey: ['program-templates', categoryFilter, true],
    queryFn: () => listTemplates(clean({ category: categoryFilter || undefined, active_only: true })),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteTemplate(id),
    onSuccess: () => {
      toast.success(t('toast.programPlanning.templateDeactivated'))
      queryClient.invalidateQueries({ queryKey: ['program-templates'] })
    },
    onError: () => toast.error(t('programPlanning.failedToDeleteTemplate')),
  })
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [pendingAction, setPendingAction] = useState<(() => void) | null>(null)

  const filteredTemplates = templates?.filter(t =>
    !searchQuery || t.name.toLowerCase().includes(searchQuery.toLowerCase())
  ) ?? []

  return (
    <div>
      {/* Actions Bar */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
          <input
            type="text"
            placeholder={t('placeholder.programPlanning.searchTemplates')}
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
          />
        </div>
        <select
          value={categoryFilter}
          onChange={e => setCategoryFilter(e.target.value)}
          aria-label={t('aria.programPlanning.filterByCategory', 'Filter by category')}
          className="px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
        >
          {TEMPLATE_CATEGORIES.map(c => (
            <option key={c.value} value={c.value}>{c.label}</option>
          ))}
        </select>
        <button
          onClick={() => setShowCopyFromProgramModal(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-200 dark:hover:bg-earth-600 transition-colors"
        >
          <Copy className="w-4 h-4" />
          Copy from Program
        </button>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-earth-600 text-white hover:bg-earth-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          New Template
        </button>
      </div>

      {/* Templates Grid */}
      <div aria-live="polite">
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 motion-safe:animate-spin text-earth-600 dark:text-earth-200" />
        </div>
      ) : filteredTemplates.length === 0 ? (
        <div className="text-center py-12 bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700">
          <FileText className="w-12 h-12 text-lsc-dark/30 dark:text-lsc-cream/60 mx-auto mb-3" />
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('programPlanning.noTemplatesFoundCreateOne')}</p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredTemplates.map(template => (
            <TemplateCard
              key={template.id}
              template={template}
              onView={async () => {
                const full = await getTemplate(template.id)
                setSelectedTemplate(full)
              }}
              onDelete={() => {
                setPendingAction(() => () => deleteMutation.mutate(template.id))
                setConfirmOpen(true)
              }}
            />
          ))}
        </div>
      )}
      </div>

      {/* Create Template Modal */}
      {showCreateModal && (
        <CreateTemplateModal onClose={() => setShowCreateModal(false)} />
      )}

      {/* Copy From Program Modal */}
      {showCopyFromProgramModal && (
        <CopyFromProgramModal onClose={() => setShowCopyFromProgramModal(false)} />
      )}

      {/* Template Detail Modal */}
      {selectedTemplate && (
        <TemplateDetailModal
          template={selectedTemplate}
          onClose={() => setSelectedTemplate(null)}
        />
      )}
      <ConfirmDialog
        isOpen={confirmOpen}
        title="Deactivate this template?"
        message="The template will no longer be available for use."
        confirmText="Deactivate"
        confirmVariant="warning"
        onConfirm={() => { pendingAction?.(); setConfirmOpen(false); setPendingAction(null) }}
        onCancel={() => { setConfirmOpen(false); setPendingAction(null) }}
      />
    </div>
  )
}

export default TemplateLibraryTab
