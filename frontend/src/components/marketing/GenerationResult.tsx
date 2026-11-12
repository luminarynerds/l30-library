/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import {
  CheckCircle,
  AlertCircle,
  RefreshCw,
  Copy,
  Save,
  Loader2,
} from 'lucide-react'
import type { GenerateContentResponse, SavedContent } from '@/api/marketing-hub-api'
import type { UseMutationResult } from '@tanstack/react-query'

interface GenerationResultProps {
  result: GenerateContentResponse
  copied: boolean
  generateMutation: UseMutationResult<GenerateContentResponse, Error, void, unknown>
  saveMutation: UseMutationResult<SavedContent, Error, void, unknown>
  onCopy: () => void
  onRegenerate: () => void
}

export default function GenerationResult({
  result, copied, generateMutation, saveMutation,
  onCopy, onRegenerate,
}: GenerationResultProps) {
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 bg-lsc-cream/50 dark:bg-earth-800 border-b border-lsc-border dark:border-earth-700">
        <div className="flex items-center gap-2">
          {result.success ? (
            <CheckCircle className="w-4 h-4 text-status-success-600 dark:text-status-success-400" aria-hidden="true" />
          ) : (
            <AlertCircle className="w-4 h-4 text-status-danger-600 dark:text-status-danger-400" aria-hidden="true" />
          )}
          <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
            {result.success ? 'Generated Content' : 'Generation Failed'}
          </span>
          {result.generation_time_ms && (
            <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
              ({(result.generation_time_ms / 1000).toFixed(1)}s)
            </span>
          )}
        </div>
        {result.success && (
          <div className="flex items-center gap-1">
            <button
              onClick={onRegenerate}
              disabled={generateMutation.isPending}
              className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg motion-safe:transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              title="Regenerate"
              aria-label="Regenerate"
            >
              <RefreshCw className={`w-4 h-4 ${generateMutation.isPending ? 'motion-safe:animate-spin' : ''}`} aria-hidden="true" />
            </button>
            <button
              onClick={onCopy}
              className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg motion-safe:transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              title="Copy to clipboard"
              aria-label="Copy to clipboard"
            >
              {copied ? (
                <CheckCircle className="w-4 h-4 text-status-success-600 dark:text-status-success-400" aria-hidden="true" />
              ) : (
                <Copy className="w-4 h-4" aria-hidden="true" />
              )}
            </button>
            <button
              onClick={() => saveMutation.mutate()}
              disabled={saveMutation.isPending}
              className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg motion-safe:transition-colors focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              title="Save to history"
              aria-label="Save to history"
            >
              {saveMutation.isPending ? (
                <Loader2 className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" />
              ) : (
                <Save className="w-4 h-4" aria-hidden="true" />
              )}
            </button>
          </div>
        )}
      </div>
      <div className="p-4">
        {result.success ? (
          <div className="whitespace-pre-wrap text-lsc-dark dark:text-lsc-cream leading-relaxed">
            {result.generated_text}
          </div>
        ) : (
          <p className="text-status-danger-600 dark:text-status-danger-400">{result.error}</p>
        )}
      </div>
    </div>
  )
}
