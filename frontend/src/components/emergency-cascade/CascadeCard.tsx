/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Users, AlertCircle, Play, Plus } from "lucide-react"
import type { CascadeData } from "./types"

interface Props {
  cascade: CascadeData
  onSelect: (cascade: CascadeData) => void
  onExecute: (cascade: CascadeData) => void
  onAddContact: (cascade: CascadeData) => void
}

export function CascadeCard({ cascade, onSelect, onExecute, onAddContact }: Props): React.ReactElement {
  return (
    <div
      className="bg-lsc-white dark:bg-earth-800 rounded-lg border-2 border-category-200 dark:border-category-800 p-6 hover:shadow-lg transition-shadow cursor-pointer"
      onClick={() => onSelect(cascade)}
      tabIndex={0}
      role="button"
      onKeyDown={(e: React.KeyboardEvent) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onSelect(cascade)
        }
      }}
    >
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream">{cascade.cascade_name}</h3>
          {cascade.cascade_description && (
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">{cascade.cascade_description}</p>
          )}
        </div>
        <div
          className={`px-3 py-1 rounded-full text-xs font-bold ${
            cascade.is_active
              ? "bg-status-success-100 dark:bg-status-success-900/30 text-status-success-800 dark:text-status-success-300"
              : "bg-earth-100 dark:bg-earth-700 text-earth-800 dark:text-earth-100"
          }`}
        >
          {cascade.is_active ? "ACTIVE" : "INACTIVE"}
        </div>
      </div>

      <div className="space-y-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
        <p className="flex items-center gap-2">
          <Users className="w-4 h-4" />
          <strong>Max Levels:</strong> {cascade.max_contact_levels}
        </p>
        <p className="flex items-center gap-2">
          <AlertCircle className="w-4 h-4" />
          <strong>Approval Required:</strong> {cascade.manual_approval_required ? "Yes" : "No"}
        </p>

        {cascade.auto_trigger_events && cascade.auto_trigger_events.length > 0 && (
          <div className="flex items-start gap-2 mt-2">
            <span className="font-bold flex-shrink-0">Auto-Triggers:</span>
            <div className="flex flex-wrap gap-1">
              {cascade.auto_trigger_events.map((event) => (
                <span key={event} className="px-2 py-1 bg-category-100 dark:bg-category-900/30 text-category-800 dark:text-category-300 rounded text-xs">
                  {event}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="flex gap-2">
        <button
          onClick={(e) => {
            e.stopPropagation()
            onExecute(cascade)
          }}
          className="flex-1 px-3 py-2 bg-status-danger-600 text-white rounded-lg hover:bg-status-danger-700 transition-colors font-semibold flex items-center justify-center gap-2 text-sm"
        >
          <Play className="w-4 h-4" />
          Execute
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation()
            onAddContact(cascade)
          }}
          className="flex-1 px-3 py-2 bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors font-semibold flex items-center justify-center gap-2 text-sm"
        >
          <Plus className="w-4 h-4" />
          Add Contact
        </button>
      </div>
    </div>
  )
}
