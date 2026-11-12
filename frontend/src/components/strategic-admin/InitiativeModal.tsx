/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from "react";
import { Plus, X } from "lucide-react";
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'
import {
  StrategicInitiative,
  InitiativeStatus,
} from '@/api/domains/admin/strategic-api'

interface Props {
  editing: Partial<StrategicInitiative> & { title: string }
  setEditing: (v: Partial<StrategicInitiative> & { title: string }) => void
  onSave: () => void
  onClose: () => void
}

const statusOptions: { value: InitiativeStatus; label: string }[] = [
  { value: 'planning', label: 'Planning' },
  { value: 'approved', label: 'Approved' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'on_hold', label: 'On Hold' },
  { value: 'completed', label: 'Completed' },
  { value: 'cancelled', label: 'Cancelled' },
]

export default function InitiativeModal({ editing, setEditing, onSave, onClose }: Props) {
  const [newOutcome, setNewOutcome] = useState('')

  const addOutcome = () => {
    const trimmed = newOutcome.trim()
    if (!trimmed) return
    setEditing({ ...editing, expected_outcomes: [...(editing.expected_outcomes || []), trimmed] })
    setNewOutcome('')
  }

  const removeOutcome = (idx: number) => {
    const outcomes = [...(editing.expected_outcomes || [])]
    outcomes.splice(idx, 1)
    setEditing({ ...editing, expected_outcomes: outcomes })
  }

  const isEdit = !!editing.id

  return (
    <ModalBackdrop onClose={onClose} title={isEdit ? "Edit Initiative" : "Add Initiative"}>
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
            {isEdit ? "Edit Initiative" : "Add Initiative"}
          </h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Title *</label>
              <input
                type="text"
                value={editing.title}
                onChange={(e) => setEditing({ ...editing, title: e.target.value })}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
              />
            </div>
            <div>
              <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Description</label>
              <textarea
                value={editing.description || ''}
                onChange={(e) => setEditing({ ...editing, description: e.target.value })}
                rows={3}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream resize-none"
              />
            </div>
            <div>
              <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Business Case</label>
              <textarea
                value={editing.business_case || ''}
                onChange={(e) => setEditing({ ...editing, business_case: e.target.value })}
                rows={3}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream resize-none"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Status</label>
                <select
                  value={editing.status || 'planning'}
                  onChange={(e) => setEditing({ ...editing, status: e.target.value as InitiativeStatus })}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
                >
                  {statusOptions.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Priority</label>
                <select
                  value={editing.priority ?? 3}
                  onChange={(e) => setEditing({ ...editing, priority: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
                >
                  <option value={1}>1 - Highest</option>
                  <option value={2}>2 - High</option>
                  <option value={3}>3 - Medium</option>
                  <option value={4}>4 - Low</option>
                  <option value={5}>5 - Lowest</option>
                </select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Start Date</label>
                <input
                  type="date"
                  value={editing.start_date?.split('T')[0] || ''}
                  onChange={(e) => setEditing({ ...editing, start_date: e.target.value })}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
                />
              </div>
              <div>
                <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Target Completion</label>
                <input
                  type="date"
                  value={editing.target_completion_date?.split('T')[0] || ''}
                  onChange={(e) => setEditing({ ...editing, target_completion_date: e.target.value })}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Estimated Budget ($)</label>
                <input
                  type="number"
                  value={editing.estimated_budget || ''}
                  onChange={(e) => setEditing({ ...editing, estimated_budget: e.target.value })}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
                  placeholder="0.00"
                />
              </div>
              <div>
                <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Alignment Score (1-10)</label>
                <input
                  type="number"
                  min={1}
                  max={10}
                  value={editing.strategic_alignment_score || ''}
                  onChange={(e) => setEditing({ ...editing, strategic_alignment_score: parseInt(e.target.value) || undefined })}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Expected Outcomes</label>
              <div className="space-y-1 mb-2">
                {(editing.expected_outcomes || []).map((outcome, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <span className="flex-1 text-sm text-lsc-dark dark:text-lsc-cream px-2 py-1 bg-lsc-cream dark:bg-lsc-brown rounded">
                      {outcome}
                    </span>
                    <button
                      type="button"
                      onClick={() => removeOutcome(idx)}
                      className="text-status-danger-600 hover:text-status-danger-700"
                      aria-label="Remove outcome"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newOutcome}
                  onChange={(e) => setNewOutcome(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addOutcome() } }}
                  placeholder="Add an expected outcome"
                  className="flex-1 px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream text-sm"
                />
                <button
                  type="button"
                  onClick={addOutcome}
                  className="px-3 py-2 bg-lsc-rose text-white rounded-xl text-sm hover:bg-lsc-rose"
                >
                  <Plus className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
          <div className="flex justify-end gap-2 mt-6">
            <button
              onClick={onClose}
              className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-xl"
            >
              Cancel
            </button>
            <button
              onClick={onSave}
              disabled={!editing.title}
              className="px-4 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose disabled:opacity-50"
            >
              Save Initiative
            </button>
          </div>
        </div>
      </div>
    </ModalBackdrop>
  )
}
