/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Sparkles, Save, Loader2 } from "lucide-react"
import { SectionCard, Label, InputField, PrimaryButton } from "./ai-settings-primitives"
import type { OllamaStatus } from "./types"

interface ConfigTabProps {
  agentChatConfig: Record<string, unknown>
  setAgentChatConfig: (cfg: Record<string, unknown>) => void
  ollamaStatus: OllamaStatus | null
  saving: boolean
  onSaveConfig: (key: string, value: Record<string, unknown>) => void
}

export function ConfigTab({
  agentChatConfig,
  setAgentChatConfig,
  ollamaStatus,
  saving,
  onSaveConfig,
}: ConfigTabProps) {
  return (
    <div className="space-y-6">
      <SectionCard>
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-lsc-rose" /> Agent Chat Configuration
        </h3>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          Model and generation settings used by the patron-facing Ask-a-Librarian chat when Ollama is available. The admin test-generation endpoint uses the same model as its default.
        </p>
        <div className="space-y-4">
          <div className="grid md:grid-cols-3 gap-4">
            <div>
              <Label htmlFor="ai-model-select">Model</Label>
              <select
                id="ai-model-select"
                value={String(agentChatConfig.model || "")}
                onChange={(e) => setAgentChatConfig({ ...agentChatConfig, model: e.target.value })}
                className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-earth-100"
              >
                {ollamaStatus?.models?.map((m) => (<option key={m.name} value={m.name}>{m.name}</option>))}
                <option value="llama3.2:3b">llama3.2:3b (default)</option>
              </select>
            </div>
            <div>
              <Label>Temperature ({Number(agentChatConfig.temperature || 0.7)})</Label>
              <input type="range" min="0" max="1" step="0.1" value={Number(agentChatConfig.temperature || 0.7)}
                onChange={(e) => setAgentChatConfig({ ...agentChatConfig, temperature: parseFloat(e.target.value) })} className="w-full" />
            </div>
            <div>
              <Label>Max Tokens</Label>
              <InputField type="number" value={Number(agentChatConfig.max_tokens || 500)}
                onChange={(e) => setAgentChatConfig({ ...agentChatConfig, max_tokens: parseInt(e.target.value) })} />
            </div>
          </div>
          <PrimaryButton onClick={() => onSaveConfig("agent_chat", agentChatConfig)} disabled={saving}>
            {saving ? <Loader2 className="h-4 w-4 motion-safe:animate-spin" /> : <Save className="h-4 w-4" />}
            Save Configuration
          </PrimaryButton>
        </div>
      </SectionCard>
    </div>
  )
}
