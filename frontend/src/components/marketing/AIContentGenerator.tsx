/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import {
  Sparkles,
  Loader2,
  AlertCircle,
  Sliders,
  ChevronDown,
} from 'lucide-react'
import { useAIGeneration, getPlaceholder } from './useAIGeneration'
import ContentTypeSelector from './ContentTypeSelector'
import ContextPickers from './ContextPickers'
import PromptTemplates from './PromptTemplates'
import ToneSelector from './ToneSelector'
import GenerationResult from './GenerationResult'

interface AIContentGeneratorProps {
  onContentGenerated?: (text: string, contentType: string) => void
}

export default function AIContentGenerator({ onContentGenerated }: AIContentGeneratorProps) {
  const gen = useAIGeneration({ onContentGenerated })

  return (
    <div className="space-y-6">
      {/* AI Status Banner */}
      {gen.aiStatus && !gen.aiStatus.available && (
        <div className="bg-status-warning-50 dark:bg-status-warning-900/20 border border-status-warning-200 dark:border-status-warning-800 rounded-xl p-4 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-status-warning-600 dark:text-status-warning-400 mt-0.5 flex-shrink-0" aria-hidden="true" />
          <div>
            <p className="font-medium text-status-warning-800 dark:text-status-warning-200">AI Service Unavailable</p>
            <p className="text-sm text-status-warning-700 dark:text-status-warning-300 mt-1">
              The AI service is not currently running. Content generation requires Ollama to be active.
            </p>
          </div>
        </div>
      )}

      <form onSubmit={gen.handleGenerate} className="space-y-5">
        <ContentTypeSelector
          contentType={gen.contentType}
          setContentType={gen.setContentType}
          description={gen.selectedContentOption?.description}
        />

        <ContextPickers
          selectedProgramId={gen.selectedProgramId}
          setSelectedProgramId={gen.setSelectedProgramId}
          selectedEventId={gen.selectedEventId}
          setSelectedEventId={gen.setSelectedEventId}
          programs={gen.programs}
          events={gen.events}
          t={gen.t}
        />

        {/* Instructions */}
        <div>
          <label htmlFor="ai-instructions" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
            Instructions *
          </label>
          <textarea
            id="ai-instructions"
            ref={gen.instructionsRef}
            required
            rows={4}
            value={gen.instructions}
            onChange={(e) => gen.setInstructions(e.target.value)}
            placeholder={getPlaceholder(gen.contentType)}
            className="w-full px-4 py-3 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent resize-none placeholder:text-lsc-dark/70 dark:placeholder:text-lsc-cream/40"
          />
        </div>

        <PromptTemplates
          builtInForType={gen.builtInForType}
          customForType={gen.customForType}
          canSaveAsTemplate={gen.canSaveAsTemplate}
          showSaveTemplate={gen.showSaveTemplate}
          setShowSaveTemplate={gen.setShowSaveTemplate}
          newTemplateLabel={gen.newTemplateLabel}
          setNewTemplateLabel={gen.setNewTemplateLabel}
          newTemplateLabelRef={gen.newTemplateLabelRef}
          onApplyTemplate={gen.handleApplyTemplate}
          onSaveTemplate={gen.handleSaveTemplate}
          onDeleteTemplate={gen.handleDeleteTemplate}
        />

        <ToneSelector tone={gen.tone} setTone={gen.setTone} />

        {/* Advanced Options */}
        <button
          type="button"
          onClick={() => gen.setShowAdvanced(!gen.showAdvanced)}
          aria-expanded={gen.showAdvanced}
          aria-controls="advanced-options"
          className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-rose motion-safe:transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose rounded-lg"
        >
          <Sliders className="w-4 h-4" aria-hidden="true" />
          Advanced Options
          <ChevronDown
            className={`w-4 h-4 motion-safe:transition-transform ${gen.showAdvanced ? 'rotate-180' : ''}`}
            aria-hidden="true"
          />
        </button>

        {gen.showAdvanced && (
          <div id="advanced-options" className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-lsc-cream/50 dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700">
            <div>
              <label htmlFor="creativity-slider" className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                Creativity: {gen.temperature.toFixed(1)}
              </label>
              <input
                id="creativity-slider"
                type="range"
                min="0"
                max="1.5"
                step="0.1"
                value={gen.temperature}
                onChange={(e) => gen.setTemperature(Number(e.target.value))}
                className="w-full accent-lsc-rose focus:outline-none focus:ring-2 focus:ring-lsc-rose rounded-lg"
              />
              <div className="flex justify-between text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                <span>Precise</span>
                <span>Creative</span>
              </div>
            </div>
          </div>
        )}

        {/* Generate Button */}
        <button
          type="submit"
          disabled={gen.generateMutation.isPending || !gen.instructions.trim() || (gen.aiStatus !== undefined && !gen.aiStatus.available)}
          className="w-full px-6 py-3 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-lsc-rose/40 text-white rounded-xl font-medium motion-safe:transition-colors flex items-center justify-center gap-2 focus:outline-none focus:ring-2 focus:ring-lsc-rose"
        >
          {gen.generateMutation.isPending ? (
            <>
              <Loader2 className="w-5 h-5 motion-safe:animate-spin" aria-hidden="true" />
              Generating...
            </>
          ) : (
            <>
              <Sparkles className="w-5 h-5" aria-hidden="true" />
              Generate Content
            </>
          )}
        </button>
      </form>

      {gen.result && (
        <GenerationResult
          result={gen.result}
          copied={gen.copied}
          generateMutation={gen.generateMutation}
          saveMutation={gen.saveMutation}
          onCopy={gen.handleCopy}
          onRegenerate={gen.handleRegenerate}
        />
      )}
    </div>
  )
}
