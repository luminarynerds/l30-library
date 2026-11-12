/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { TestTube, Loader2, CheckCircle, XCircle } from "lucide-react"
import { useTranslation } from "@/i18n"
import { SectionCard, Label, TextArea } from "./ai-settings-primitives"
import type { OllamaStatus, TestResult } from "./types"

interface TestTabProps {
  testPrompt: string
  setTestPrompt: (v: string) => void
  testSystemPrompt: string
  setTestSystemPrompt: (v: string) => void
  testResult: TestResult | null
  testing: boolean
  ollamaStatus: OllamaStatus | null
  onRunTest: () => void
}

export function TestTab({
  testPrompt,
  setTestPrompt,
  testSystemPrompt,
  setTestSystemPrompt,
  testResult,
  testing,
  ollamaStatus,
  onRunTest,
}: TestTabProps) {
  const { t } = useTranslation()

  return (
    <SectionCard>
      <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
        <TestTube className="h-5 w-5 text-category-500" /> Test Generation
      </h3>
      <div className="space-y-4">
        <div>
          <Label>Test Prompt</Label>
          <TextArea value={testPrompt} onChange={(e) => setTestPrompt(e.target.value)} rows={3} placeholder={t('admin.adminAISettings.enterATestPrompt')} />
        </div>
        <div>
          <Label>{t('admin.adminAISettings.systemPromptOverrideOptional')}</Label>
          <TextArea value={testSystemPrompt} onChange={(e) => setTestSystemPrompt(e.target.value)} rows={2} placeholder={t('admin.adminAISettings.leaveEmptyToUseConfigured')} />
        </div>
        <button
          onClick={onRunTest}
          disabled={testing || !ollamaStatus?.connected}
          className="px-4 py-2 bg-category-600 text-white rounded-xl hover:bg-category-700 disabled:opacity-50 flex items-center gap-2"
        >
          {testing ? <Loader2 className="h-4 w-4 motion-safe:animate-spin" /> : <TestTube className="h-4 w-4" />}
          Run Test
        </button>
        {testResult && (
          <div className={`p-4 rounded-xl ${testResult.success ? "bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-800" : "bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800"}`}>
            {testResult.success ? (
              <>
                <div className="flex items-center gap-2 text-status-success-700 dark:text-status-success-300 mb-2">
                  <CheckCircle className="h-4 w-4" />
                  <span className="font-medium">Generation successful</span>
                  <span className="text-sm text-status-success-600 dark:text-status-success-400">({testResult.model}, {testResult.generation_time_ms}ms)</span>
                </div>
                <p className="text-lsc-dark dark:text-lsc-cream/80 whitespace-pre-wrap text-sm">{testResult.response}</p>
              </>
            ) : (
              <div className="flex items-center gap-2 text-status-danger-700 dark:text-status-danger-300">
                <XCircle className="h-4 w-4" />
                <span>{testResult.error}</span>
              </div>
            )}
          </div>
        )}
      </div>
    </SectionCard>
  )
}
