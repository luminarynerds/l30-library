/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Cpu, BarChart3, Settings, CheckCircle, XCircle, AlertCircle, Loader2, Download, RefreshCw, Save } from "lucide-react"
import { useTranslation } from "@/i18n"
import { SectionCard, Label, InputField, SecondaryButton, AIStatCard } from "./ai-settings-primitives"
import type { OllamaStatus, AIStats } from "./types"

interface StatusTabProps {
  ollamaStatus: OllamaStatus | null
  stats: AIStats | null
  ollamaConfig: Record<string, unknown>
  setOllamaConfig: (cfg: Record<string, unknown>) => void
  pullModelName: string
  setPullModelName: (v: string) => void
  pulling: boolean
  saving: boolean
  onPullModel: () => void
  onRefresh: () => void
  onSaveConfig: (key: string, value: Record<string, unknown>) => void
  formatBytes: (bytes?: number) => string
}

export function StatusTab({
  ollamaStatus,
  stats,
  ollamaConfig,
  setOllamaConfig,
  pullModelName,
  setPullModelName,
  pulling,
  saving,
  onPullModel,
  onRefresh,
  onSaveConfig,
  formatBytes,
}: StatusTabProps) {
  const { t } = useTranslation()

  return (
    <div className="space-y-6">
      <SectionCard>
        <div className="flex items-center gap-3 mb-4">
          <Cpu className="h-5 w-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Ollama Server Status</h3>
          {ollamaStatus?.connected ? (
            <span className="flex items-center gap-1 text-status-success-600 text-sm"><CheckCircle className="h-4 w-4" /> Connected</span>
          ) : (
            <span className="flex items-center gap-1 text-status-danger-600 text-sm"><XCircle className="h-4 w-4" /> Disconnected</span>
          )}
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          <div>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Server URL</p>
            <p className="font-mono text-lsc-dark dark:text-earth-300">{ollamaStatus?.base_url}</p>
            {ollamaStatus?.error && (
              <p className="text-status-danger-600 text-sm mt-2 flex items-center gap-1">
                <AlertCircle className="h-4 w-4" /> {ollamaStatus.error}
              </p>
            )}
          </div>
          <div>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">Available Models</p>
            {ollamaStatus?.models && ollamaStatus.models.length > 0 ? (
              <ul className="space-y-1">
                {ollamaStatus.models.map((model) => (
                  <li key={model.name} className="flex items-center justify-between text-sm">
                    <span className="font-mono text-lsc-dark dark:text-lsc-cream/80">{model.name}</span>
                    <span className="text-lsc-dark/70 dark:text-lsc-cream/70">{formatBytes(model.size)}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-sm">No models installed</p>
            )}
          </div>
        </div>

        <div className="mt-4 pt-4 border-t border-lsc-border dark:border-earth-700">
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-2">Pull New Model</p>
          <div className="flex gap-2">
            <InputField
              value={pullModelName}
              onChange={(e) => setPullModelName(e.target.value)}
              placeholder={t('placeholder.adminAISettings.egLlama323bMistral7b')}
            />
            <SecondaryButton onClick={onPullModel} disabled={pulling || !pullModelName.trim()}>
              {pulling ? <Loader2 className="h-4 w-4 motion-safe:animate-spin" /> : <Download className="h-4 w-4" />}
              Pull
            </SecondaryButton>
          </div>
        </div>

        <button onClick={onRefresh} className="mt-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark flex items-center gap-1">
          <RefreshCw className="h-4 w-4" /> Refresh status
        </button>
      </SectionCard>

      {stats && (
        <SectionCard>
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-earth-600" /> Usage Statistics
          </h3>
          <div className="grid md:grid-cols-4 gap-4">
            <AIStatCard value={stats.total_generations} label="Total Generations" color="default" />
            <AIStatCard value={stats.completed} label="Completed" color="success" />
            <AIStatCard value={stats.failed} label="Failed" color="danger" />
            <AIStatCard value={`${stats.success_rate.toFixed(0)}%`} label="Success Rate" color="accent" />
          </div>
          <div className="mt-4 grid md:grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Avg Generation Time</p>
              <p className="font-semibold text-lsc-dark dark:text-earth-300">
                {stats.average_generation_time_ms > 0 ? `${(stats.average_generation_time_ms / 1000).toFixed(1)}s` : "No data"}
              </p>
            </div>
            <div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">Models Used</p>
              {Object.keys(stats.models_used).length > 0 ? (
                <ul className="text-sm text-lsc-dark dark:text-lsc-cream/80">
                  {Object.entries(stats.models_used).map(([model, count]) => (
                    <li key={model}><span className="font-mono">{model}</span>: {count} times</li>
                  ))}
                </ul>
              ) : (<p className="text-lsc-dark/70 dark:text-lsc-cream/70">No data</p>)}
            </div>
          </div>
        </SectionCard>
      )}

      <SectionCard>
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          <Settings className="h-5 w-5" /> Server Configuration
        </h3>
        <div className="grid md:grid-cols-3 gap-4 mb-4">
          <div>
            <Label>Ollama Base URL</Label>
            <InputField value={String(ollamaConfig.base_url || "")} onChange={(e) => setOllamaConfig({ ...ollamaConfig, base_url: e.target.value })} className="font-mono" />
          </div>
          <div>
            <Label>Timeout (seconds)</Label>
            <InputField type="number" value={Number(ollamaConfig.timeout_seconds || 120)} onChange={(e) => setOllamaConfig({ ...ollamaConfig, timeout_seconds: parseInt(e.target.value) })} />
          </div>
          <div>
            <Label>Retry Attempts</Label>
            <InputField type="number" value={Number(ollamaConfig.retry_attempts || 2)} onChange={(e) => setOllamaConfig({ ...ollamaConfig, retry_attempts: parseInt(e.target.value) })} />
          </div>
        </div>
        <SecondaryButton onClick={() => onSaveConfig("ollama", ollamaConfig)} disabled={saving}>
          {saving ? <Loader2 className="h-4 w-4 motion-safe:animate-spin" /> : <Save className="h-4 w-4" />}
          Save Server Settings
        </SecondaryButton>
      </SectionCard>
    </div>
  )
}
