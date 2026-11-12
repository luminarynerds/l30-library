/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Plus, X } from 'lucide-react'
import { chipUnselected, type PromptTemplate } from './useAIGeneration'

interface PromptTemplatesProps {
  builtInForType: ReadonlyArray<PromptTemplate>
  customForType: PromptTemplate[]
  canSaveAsTemplate: boolean
  showSaveTemplate: boolean
  setShowSaveTemplate: (show: boolean) => void
  newTemplateLabel: string
  setNewTemplateLabel: (label: string) => void
  newTemplateLabelRef: React.RefObject<HTMLInputElement>
  onApplyTemplate: (template: PromptTemplate) => void
  onSaveTemplate: () => void
  onDeleteTemplate: (template: PromptTemplate) => void
}

export default function PromptTemplates({
  builtInForType, customForType,
  canSaveAsTemplate,
  showSaveTemplate, setShowSaveTemplate,
  newTemplateLabel, setNewTemplateLabel,
  newTemplateLabelRef,
  onApplyTemplate, onSaveTemplate, onDeleteTemplate,
}: PromptTemplatesProps) {
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span id="templates-label" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream">
          Templates
        </span>
        <button
          type="button"
          onClick={() => setShowSaveTemplate(!showSaveTemplate)}
          disabled={!canSaveAsTemplate}
          aria-disabled={!canSaveAsTemplate}
          title={
            canSaveAsTemplate
              ? 'Save the current Instructions as a reusable template'
              : 'Type some instructions first to save them as a template'
          }
          className="inline-flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-lg text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-lsc-rose motion-safe:transition-colors"
        >
          <Plus className="w-3.5 h-3.5" aria-hidden="true" />
          Save current prompt as template...
        </button>
      </div>

      <div aria-labelledby="templates-label" className="flex flex-wrap gap-2">
        {builtInForType.map((tpl) => (
          <button
            key={tpl.id}
            type="button"
            onClick={() => onApplyTemplate(tpl)}
            aria-label={`Use template: ${tpl.label}`}
            title={tpl.prompt}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium motion-safe:transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose ${chipUnselected}`}
          >
            {tpl.label}
          </button>
        ))}

        {customForType.map((tpl) => (
          <span
            key={tpl.id}
            className="inline-flex items-stretch rounded-lg overflow-hidden border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800"
          >
            <button
              type="button"
              onClick={() => onApplyTemplate(tpl)}
              aria-label={`Use template: ${tpl.label}`}
              title={tpl.prompt}
              className="px-3 py-1.5 text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 focus:outline-none focus:ring-2 focus:ring-lsc-rose motion-safe:transition-colors"
            >
              {tpl.label}
            </button>
            <button
              type="button"
              onClick={() => onDeleteTemplate(tpl)}
              aria-label={`Delete template ${tpl.label}`}
              title={`Delete template ${tpl.label}`}
              className="px-2 text-lsc-dark/50 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 focus:outline-none focus:ring-2 focus:ring-lsc-rose motion-safe:transition-colors"
            >
              <X className="w-3.5 h-3.5" aria-hidden="true" />
            </button>
          </span>
        ))}

        {builtInForType.length === 0 && customForType.length === 0 && (
          <p className="text-xs text-lsc-dark/60 dark:text-lsc-cream/70">
            No templates yet for this content type.
          </p>
        )}
      </div>

      {showSaveTemplate && (
        <div className="mt-3 flex flex-col sm:flex-row gap-2 bg-lsc-cream/50 dark:bg-earth-800 rounded-xl p-3 border border-lsc-border dark:border-earth-700">
          <label htmlFor="new-template-label" className="sr-only">
            New template label
          </label>
          <input
            id="new-template-label"
            ref={newTemplateLabelRef}
            type="text"
            value={newTemplateLabel}
            onChange={(e) => setNewTemplateLabel(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault()
                onSaveTemplate()
              } else if (e.key === 'Escape') {
                e.preventDefault()
                setShowSaveTemplate(false)
                setNewTemplateLabel('')
              }
            }}
            placeholder="Template label (e.g., Saturday teen night)"
            className="flex-1 px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-900 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent placeholder:text-lsc-dark/40 dark:placeholder:text-lsc-cream/40 text-sm"
          />
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onSaveTemplate}
              disabled={!newTemplateLabel.trim() || !canSaveAsTemplate}
              className="px-3 py-2 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-lsc-rose/40 text-white rounded-lg text-sm font-medium focus:outline-none focus:ring-2 focus:ring-lsc-rose motion-safe:transition-colors"
            >
              Save
            </button>
            <button
              type="button"
              onClick={() => {
                setShowSaveTemplate(false)
                setNewTemplateLabel('')
              }}
              className="px-3 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg text-sm font-medium focus:outline-none focus:ring-2 focus:ring-lsc-rose motion-safe:transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
