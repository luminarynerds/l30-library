/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useRef, useCallback, useEffect } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createTemplate } from '@/api/program-planning-api'
import { X, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { useTranslation } from '@/i18n'
import FocusTrap from 'focus-trap-react'
import { TEMPLATE_CATEGORIES, AUDIENCES, PROGRAM_TYPES } from '../constants'
import FormSection from './FormSection'

function CreateTemplateModal({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient()
  const previousActiveElement = useRef<HTMLElement | null>(null)

  useEffect(() => {
    previousActiveElement.current = document.activeElement as HTMLElement
    return () => { previousActiveElement.current?.focus() }
  }, [])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Escape') onClose()
  }, [onClose])

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    category: 'workshop',
    target_audience: 'all_ages',
    program_type: 'workshop',
    default_duration_minutes: 60,
    recommended_capacity: '',
    registration_required: false,
    estimated_budget: '',
    volunteers_needed: 0,
    marketing_lead_days: 14,
  })

  const createMutation = useMutation({
    mutationFn: (data: Parameters<typeof createTemplate>[0]) => createTemplate(data),
    onSuccess: () => {
      toast.success(t('toast.adminBanTracker.templateCreated'))
      queryClient.invalidateQueries({ queryKey: ['program-templates'] })
      onClose()
    },
    onError: () => toast.error(t('programPlanning.failedToCreateTemplate')),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    createMutation.mutate({
      ...formData,
      recommended_capacity: formData.recommended_capacity ? parseInt(formData.recommended_capacity) : null,
      estimated_budget: formData.estimated_budget ? parseFloat(formData.estimated_budget) : null,
    } as Parameters<typeof createTemplate>[0])
  }

  return (
    <FocusTrap
      focusTrapOptions={{
        allowOutsideClick: false,
        escapeDeactivates: false,
        returnFocusOnDeactivate: true,
      }}
    >
    <div
      className="fixed inset-0 z-50"
      role="presentation"
      onKeyDown={handleKeyDown}
    >
      <div className="fixed inset-0 bg-black/50" aria-hidden="true" onClick={onClose} />
      <div className="fixed inset-0 flex items-center justify-center z-50 p-4">
      {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="create-template-title"
        className="bg-lsc-white dark:bg-earth-800 rounded-xl w-full max-w-lg max-h-[85vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        <div className="sticky top-0 bg-lsc-white dark:bg-earth-800 px-6 py-4 border-b border-lsc-border dark:border-earth-700 flex justify-between items-center">
          <h2 id="create-template-title" className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">New Template</h2>
          <button onClick={onClose} aria-label={t('aria.authModals.close')} className="p-1 rounded hover:bg-earth-100 dark:hover:bg-earth-700">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Section 1: Basic Info (always visible) */}
          <div className="space-y-4">
            <div>
              <label htmlFor="template-name" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Name *</label>
              <input
                id="template-name"
                type="text"
                required
                value={formData.name}
                onChange={e => setFormData(d => ({ ...d, name: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
              />
            </div>

            <div>
              <label htmlFor="template-description" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Description</label>
              <textarea
                id="template-description"
                rows={3}
                value={formData.description}
                onChange={e => setFormData(d => ({ ...d, description: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
              />
            </div>

            <div>
              <label htmlFor="template-category" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Category *</label>
              <select
                id="template-category"
                value={formData.category}
                onChange={e => setFormData(d => ({ ...d, category: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
              >
                {TEMPLATE_CATEGORIES.filter(c => c.value).map(c => (
                  <option key={c.value} value={c.value}>{c.label}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Section 2: Audience & Type (collapsible, default open) */}
          <FormSection title="Audience & Type" defaultOpen={true}>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="template-audience" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Audience</label>
                <select
                  id="template-audience"
                  value={formData.target_audience}
                  onChange={e => setFormData(d => ({ ...d, target_audience: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                >
                  {AUDIENCES.map(a => (
                    <option key={a} value={a}>{a.replace('_', ' ')}</option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="template-program-type" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Program Type</label>
                <select
                  id="template-program-type"
                  value={formData.program_type}
                  onChange={e => setFormData(d => ({ ...d, program_type: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                >
                  {PROGRAM_TYPES.map(t => (
                    <option key={t} value={t}>{t.replace('_', ' ')}</option>
                  ))}
                </select>
              </div>
            </div>
            <div>
              <label htmlFor="template-duration" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Duration (min)</label>
              <input
                id="template-duration"
                type="number"
                min={15}
                max={480}
                value={formData.default_duration_minutes}
                onChange={e => setFormData(d => ({ ...d, default_duration_minutes: parseInt(e.target.value) || 60 }))}
                className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
              />
            </div>
          </FormSection>

          {/* Section 3: Capacity & Resources (collapsible, default collapsed) */}
          <FormSection title="Capacity & Resources" defaultOpen={false}>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label htmlFor="template-capacity" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Capacity</label>
                <input
                  id="template-capacity"
                  type="number"
                  min={1}
                  value={formData.recommended_capacity}
                  onChange={e => setFormData(d => ({ ...d, recommended_capacity: e.target.value }))}
                  placeholder={t('placeholder.programPlanning.unlimited')}
                  className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                />
              </div>
              <div>
                <label htmlFor="template-budget" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Est. Budget ($)</label>
                <input
                  type="number"
                  min={0}
                  step="0.01"
                  value={formData.estimated_budget}
                  onChange={e => setFormData(d => ({ ...d, estimated_budget: e.target.value }))}
                  placeholder={t('placeholder.staff.000')}
                  className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                />
              </div>
              <div>
                <label htmlFor="template-volunteers" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Volunteers</label>
                <input
                  id="template-volunteers"
                  type="number"
                  min={0}
                  value={formData.volunteers_needed}
                  onChange={e => setFormData(d => ({ ...d, volunteers_needed: parseInt(e.target.value) || 0 }))}
                  className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                />
              </div>
            </div>

            <div className="flex items-center gap-2">
              <input
                id="template-registration-required"
                type="checkbox"
                checked={formData.registration_required}
                onChange={e => setFormData(d => ({ ...d, registration_required: e.target.checked }))}
                className="rounded border-lsc-border text-earth-600 dark:text-earth-200"
              />
              <label htmlFor="template-registration-required" className="text-sm text-lsc-dark dark:text-lsc-cream">Registration required</label>
            </div>

            <div>
              <label htmlFor="template-marketing-lead-days" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">Marketing lead days</label>
              <input
                id="template-marketing-lead-days"
                type="number"
                min={0}
                value={formData.marketing_lead_days}
                onChange={e => setFormData(d => ({ ...d, marketing_lead_days: parseInt(e.target.value) || 14 }))}
                className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
              />
            </div>
          </FormSection>

          <div className="flex justify-end gap-3 pt-4 border-t border-lsc-border dark:border-earth-700">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-earth-50 dark:hover:bg-earth-700"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-earth-600 text-white hover:bg-earth-700 disabled:opacity-50"
            >
              {createMutation.isPending && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
              Create Template
            </button>
          </div>
        </form>
      </div>
      </div>
    </div>
    </FocusTrap>
  )
}

export default CreateTemplateModal
