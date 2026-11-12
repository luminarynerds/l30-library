/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useRef, useCallback, useEffect } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createPlan, type ProgramTemplate } from '@/api/program-planning-api'
import {
  X, Users, Clock, Target, DollarSign, Package,
  Calendar, ClipboardCheck, Loader2,
} from 'lucide-react'
import toast from 'react-hot-toast'
import FocusTrap from 'focus-trap-react'
import InfoCard from './InfoCard'
import { t } from '@/i18n'

function TemplateDetailModal({
  template,
  onClose,
}: {
  template: ProgramTemplate
  onClose: () => void
}) {
  const previousActiveElement = useRef<HTMLElement | null>(null)

  useEffect(() => {
    previousActiveElement.current = document.activeElement as HTMLElement
    return () => { previousActiveElement.current?.focus() }
  }, [])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Escape') onClose()
  }, [onClose])

  const queryClient = useQueryClient()
  const [showUseForm, setShowUseForm] = useState(false)
  const [programId, setProgramId] = useState('')
  const [planningNotes, setPlanningNotes] = useState('')

  const useTemplateMutation = useMutation({
    mutationFn: (data: { program_id: number; template_id: number; planning_notes?: string }) =>
      createPlan(data),
    onSuccess: () => {
      toast.success('Plan created from template')
      queryClient.invalidateQueries({ queryKey: ['program-templates'] })
      onClose()
    },
    onError: () => toast.error('Failed to create plan from template'),
  })

  const handleUseTemplate = (e: React.FormEvent) => {
    e.preventDefault()
    if (!programId) return
    useTemplateMutation.mutate({
      program_id: parseInt(programId),
      template_id: template.id,
      ...(planningNotes.trim() ? { planning_notes: planningNotes.trim() } : {}),
    })
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
        aria-labelledby="template-detail-title"
        className="bg-lsc-white dark:bg-earth-800 rounded-xl w-full max-w-3xl max-h-[85vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        <div className="sticky top-0 bg-lsc-white dark:bg-earth-800 px-6 py-4 border-b border-lsc-border dark:border-earth-700 flex justify-between items-center">
          <h2 id="template-detail-title" className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">{template.name}</h2>
          <button onClick={onClose} aria-label={t('aria.addRoleModal.closeModal')} className="p-1 rounded hover:bg-earth-100 dark:hover:bg-earth-700">
            <X className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Overview */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <InfoCard icon={Users} label="Audience" value={template.target_audience} />
            <InfoCard icon={Clock} label="Duration" value={`${template.default_duration_minutes} min`} />
            <InfoCard icon={Target} label="Capacity" value={template.recommended_capacity?.toString() ?? 'No limit'} />
            <InfoCard icon={DollarSign} label="Est. Budget" value={template.estimated_budget ? `$${template.estimated_budget}` : 'N/A'} />
          </div>

          {template.description && (
            <div>
              <h3 className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase mb-1">Description</h3>
              <p className="text-lsc-dark dark:text-lsc-cream">{template.description}</p>
            </div>
          )}

          {/* Budget Items */}
          {template.template_budget_items.length > 0 && (
            <div>
              <h3 className="flex items-center gap-2 text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase mb-2">
                <DollarSign className="w-4 h-4" /> Budget Items ({template.template_budget_items.length})
              </h3>
              <div className="space-y-1">
                {template.template_budget_items.map(item => (
                  <div key={item.id} className="flex justify-between items-center py-2 px-3 bg-earth-50 dark:bg-earth-700 rounded">
                    <span className="text-sm text-lsc-dark dark:text-lsc-cream">{item.description}</span>
                    <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">${item.estimated_amount}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Supply Items */}
          {template.template_supply_items.length > 0 && (
            <div>
              <h3 className="flex items-center gap-2 text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase mb-2">
                <Package className="w-4 h-4" /> Supply Checklist ({template.template_supply_items.length})
              </h3>
              <div className="space-y-1">
                {template.template_supply_items.map(item => (
                  <div key={item.id} className="flex justify-between items-center py-2 px-3 bg-earth-50 dark:bg-earth-700 rounded">
                    <span className="text-sm text-lsc-dark dark:text-lsc-cream">
                      {item.item_name} (x{item.quantity})
                    </span>
                    {item.estimated_cost && (
                      <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">~${item.estimated_cost}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Marketing Milestones */}
          {template.template_marketing_milestones.length > 0 && (
            <div>
              <h3 className="flex items-center gap-2 text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase mb-2">
                <Calendar className="w-4 h-4" /> Marketing Timeline ({template.template_marketing_milestones.length})
              </h3>
              <div className="space-y-1">
                {template.template_marketing_milestones.map(m => (
                  <div key={m.id} className="flex justify-between items-center py-2 px-3 bg-earth-50 dark:bg-earth-700 rounded">
                    <span className="text-sm text-lsc-dark dark:text-lsc-cream">{m.description}</span>
                    <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{m.days_before_program}d before</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Equipment & Volunteers */}
          <div className="grid grid-cols-2 gap-4">
            {template.equipment_needed && template.equipment_needed.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase mb-2">Equipment Needed</h3>
                <div className="flex flex-wrap gap-1">
                  {template.equipment_needed.map(e => (
                    <span key={e} className="px-2 py-0.5 rounded-full text-xs bg-earth-100 dark:bg-earth-800 text-lsc-rose dark:text-lsc-rose-light/80">
                      {e}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {template.volunteer_roles_needed && template.volunteer_roles_needed.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70 uppercase mb-2">
                  Volunteer Roles ({template.volunteers_needed} needed)
                </h3>
                <div className="flex flex-wrap gap-1">
                  {template.volunteer_roles_needed.map(r => (
                    <span key={r} className="px-2 py-0.5 rounded-full text-xs bg-status-success-100 dark:bg-status-success-900 text-status-success-700 dark:text-status-success-200">
                      {r}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Use This Template */}
          <div className="border-t border-lsc-border dark:border-earth-700 pt-4">
            {!showUseForm ? (
              <button
                type="button"
                onClick={() => setShowUseForm(true)}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-earth-600 text-white hover:bg-earth-700 transition-colors font-medium"
              >
                <ClipboardCheck className="w-5 h-5" />
                Use This Template
              </button>
            ) : (
              <form onSubmit={handleUseTemplate} className="space-y-3">
                <div>
                  <label htmlFor="use-template-program-id" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                    Program to apply this template to *
                  </label>
                  <input
                    id="use-template-program-id"
                    type="number"
                    required
                    min={1}
                    value={programId}
                    onChange={e => setProgramId(e.target.value)}
                    placeholder="Program ID"
                    className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
                <div>
                  <label htmlFor="use-template-planning-notes" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-1">
                    Planning Notes
                  </label>
                  <textarea
                    id="use-template-planning-notes"
                    rows={2}
                    value={planningNotes}
                    onChange={e => setPlanningNotes(e.target.value)}
                    placeholder="Optional notes for this plan..."
                    className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
                <div className="flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => { setShowUseForm(false); setProgramId(''); setPlanningNotes('') }}
                    className="px-4 py-2 rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-earth-50 dark:hover:bg-earth-700"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={!programId || useTemplateMutation.isPending}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-earth-600 text-white hover:bg-earth-700 disabled:opacity-50"
                  >
                    {useTemplateMutation.isPending && <Loader2 className="w-4 h-4 motion-safe:animate-spin" />}
                    <ClipboardCheck className="w-4 h-4" />
                    Create Plan
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      </div>
      </div>
    </div>
    </FocusTrap>
  )
}

export default TemplateDetailModal
