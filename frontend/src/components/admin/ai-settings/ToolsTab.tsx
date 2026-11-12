/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useRef } from "react"
import { Bot, Save, Loader2, ToggleLeft, ToggleRight, Edit3, Lock, MapPin } from "lucide-react"
import { useTranslation } from "@/i18n"
import { SectionCard, Label, InputField, TextArea, PrimaryButton } from "./ai-settings-primitives"
import type { AITool } from "./types"

interface ToolsTabProps {
  aiTools: AITool[]
  editingTool: AITool | null
  setEditingTool: (tool: AITool | null) => void
  saving: boolean
  onToggleTool: (toolId: string, enabled: boolean) => void
  onSaveToolPrompt: () => void
}

export function ToolsTab({
  aiTools,
  editingTool,
  setEditingTool,
  saving,
  onToggleTool,
  onSaveToolPrompt,
}: ToolsTabProps) {
  const { t } = useTranslation()
  const editHeadingRef = useRef<HTMLHeadingElement>(null)

  // When the edit form opens (or switches to a different tool), move focus into
  // it. Keyed on tool_id so editing a field doesn't re-fire on every keystroke.
  const editingId = editingTool?.tool_id
  useEffect(() => {
    if (editingId) editHeadingRef.current?.focus()
  }, [editingId])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">AI Tool Personalities</h3>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('admin.adminAISettings.managePromptsModelsAndAccess')}</p>
      </div>

      {editingTool && (
        <div
          onKeyDown={(e) => {
            // Escape cancels the edit before SectionShell's Escape (which exits
            // the whole AI settings section) can fire. Not while a save is in flight.
            if (e.key === "Escape" && !saving) {
              e.stopPropagation()
              setEditingTool(null)
            }
          }}
        >
          <SectionCard className="border-2 border-lsc-rose">
            <h4 ref={editHeadingRef} tabIndex={-1} className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 outline-none">Editing: {editingTool.name}</h4>
          <div className="space-y-4">
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <Label>Name</Label>
                <InputField value={editingTool.name} onChange={(e) => setEditingTool({ ...editingTool, name: e.target.value })} />
              </div>
              <div>
                <Label>Model</Label>
                <InputField value={editingTool.model} onChange={(e) => setEditingTool({ ...editingTool, model: e.target.value })} />
              </div>
            </div>
            <div>
              <Label>Description</Label>
              <InputField value={editingTool.description || ""} onChange={(e) => setEditingTool({ ...editingTool, description: e.target.value })} />
            </div>
            <div>
              <Label>{t('admin.adminAISettings.systemPromptControlsTheAi')}</Label>
              <TextArea
                value={editingTool.system_prompt}
                onChange={(e) => setEditingTool({ ...editingTool, system_prompt: e.target.value })}
                rows={6}
                className="font-mono text-sm"
              />
            </div>
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <Label>Temperature ({editingTool.temperature})</Label>
                <input type="range" min="0" max="2" step="0.1" value={editingTool.temperature}
                  aria-label={`Temperature: ${editingTool.temperature}`}
                  onChange={(e) => setEditingTool({ ...editingTool, temperature: parseFloat(e.target.value) })}
                  className="w-full" />
              </div>
              <div>
                <Label>Max Tokens</Label>
                <InputField type="number" value={editingTool.max_tokens} onChange={(e) => setEditingTool({ ...editingTool, max_tokens: parseInt(e.target.value) })} />
              </div>
            </div>
            <div className="flex items-center gap-6 flex-wrap">
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={editingTool.in_library_only} onChange={(e) => setEditingTool({ ...editingTool, in_library_only: e.target.checked })} className="rounded" />
                In-library only
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={editingTool.requires_auth} onChange={(e) => setEditingTool({ ...editingTool, requires_auth: e.target.checked })} className="rounded" />
                Requires authentication
              </label>
            </div>

            <div className="border-t border-lsc-border dark:border-earth-700 pt-4 space-y-3">
              <div>
                <h5 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Minor &amp; patron-type gating</h5>
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                  Tools that gate by age automatically require sign-in so the user&apos;s status can be checked.
                </p>
              </div>
              <div className="flex items-center gap-6 flex-wrap">
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={editingTool.block_for_minors}
                    onChange={(e) => setEditingTool({ ...editingTool, block_for_minors: e.target.checked })}
                    className="rounded"
                  />
                  Block users under 13 (COPPA)
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={editingTool.requires_parental_consent}
                    onChange={(e) => setEditingTool({ ...editingTool, requires_parental_consent: e.target.checked })}
                    className="rounded"
                  />
                  Require parental consent
                </label>
              </div>
              <div>
                <Label>Block patron types</Label>
                <div className="flex items-center gap-4 mt-1 flex-wrap">
                  {(["child", "teen", "adult"] as const).map((pt) => {
                    const checked = (editingTool.block_for_patron_types || []).includes(pt)
                    return (
                      <label key={pt} className="flex items-center gap-2 text-sm capitalize">
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={(e) => {
                            const current = editingTool.block_for_patron_types || []
                            const next = e.target.checked
                              ? Array.from(new Set([...current, pt]))
                              : current.filter((v) => v !== pt)
                            setEditingTool({ ...editingTool, block_for_patron_types: next })
                          }}
                          className="rounded"
                        />
                        {pt}
                      </label>
                    )
                  })}
                </div>
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                  Selected types are blocked even if the COPPA flag is off (e.g. block teens but not children).
                </p>
              </div>
            </div>
            <div className="flex gap-2">
              <PrimaryButton onClick={onSaveToolPrompt} disabled={saving}>
                {saving ? <Loader2 className="h-4 w-4 motion-safe:animate-spin" /> : <Save className="h-4 w-4" />}
                Save Tool
              </PrimaryButton>
              <button onClick={() => setEditingTool(null)} disabled={saving} className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark disabled:opacity-50">Cancel</button>
            </div>
          </div>
          </SectionCard>
        </div>
      )}

      {!editingTool && aiTools.map((tool) => (
        <SectionCard key={tool.tool_id} className={tool.enabled ? undefined : "opacity-70"}>
          {/* Identity + status + actions */}
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3 min-w-0">
              <span aria-hidden="true" className="flex-none grid place-items-center w-10 h-10 rounded-xl bg-lsc-rose/10 text-lsc-rose">
                <Bot className="h-5 w-5" />
              </span>
              <div className="min-w-0">
                <h4 className="font-serif font-semibold text-xl leading-tight text-lsc-dark dark:text-lsc-cream">{tool.name}</h4>
                <p className="mt-0.5 text-xs font-mono text-lsc-dark/60 dark:text-lsc-cream/60">{tool.tool_id}</p>
                <div className="mt-2 flex flex-wrap items-center gap-1.5">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${tool.enabled ? "bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300" : "bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300"}`}>
                    {tool.enabled ? "Active" : "Disabled"}
                  </span>
                  {tool.block_for_minors && (
                    <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-200">Adults only</span>
                  )}
                  {tool.requires_parental_consent && (
                    <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-200">Parental consent</span>
                  )}
                  {(tool.block_for_patron_types?.length ?? 0) > 0 && (
                    <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-200">Blocks: {tool.block_for_patron_types.join(", ")}</span>
                  )}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2 flex-none">
              <button
                onClick={() => onToggleTool(tool.tool_id, !tool.enabled)}
                className="p-2 rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700"
                aria-label={tool.enabled ? `Disable ${tool.name}` : `Enable ${tool.name}`}
                title={tool.enabled ? "Disable" : "Enable"}
              >
                {tool.enabled ? <ToggleRight aria-hidden="true" className="h-5 w-5 text-status-success-600" /> : <ToggleLeft aria-hidden="true" className="h-5 w-5 text-lsc-dark/70 dark:text-lsc-cream/60" />}
              </button>
              <button
                onClick={() => setEditingTool(tool)}
                className="p-2 rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700"
                aria-label={`Edit ${tool.name}`}
                title="Edit"
              >
                <Edit3 aria-hidden="true" className="h-4 w-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
              </button>
            </div>
          </div>

          {/* Labeled metric cells; 1px gaps reveal the border color as dividers */}
          <dl className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-px overflow-hidden rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-border dark:bg-earth-700">
            <div className="bg-lsc-white dark:bg-earth-800 px-4 py-3">
              <dt className="text-[10px] uppercase tracking-wider font-semibold text-lsc-dark/50 dark:text-lsc-cream/50">Model</dt>
              <dd className="mt-0.5 text-sm font-mono text-lsc-dark dark:text-lsc-cream">{tool.model}</dd>
            </div>
            <div className="bg-lsc-white dark:bg-earth-800 px-4 py-3">
              <dt className="text-[10px] uppercase tracking-wider font-semibold text-lsc-dark/50 dark:text-lsc-cream/50">Temperature</dt>
              <dd className="mt-0.5 text-sm font-mono tabular-nums text-lsc-dark dark:text-lsc-cream">{tool.temperature}</dd>
            </div>
            <div className="bg-lsc-white dark:bg-earth-800 px-4 py-3">
              <dt className="text-[10px] uppercase tracking-wider font-semibold text-lsc-dark/50 dark:text-lsc-cream/50">Max tokens</dt>
              <dd className="mt-0.5 text-sm font-mono tabular-nums text-lsc-dark dark:text-lsc-cream">{tool.max_tokens}</dd>
            </div>
            <div className="bg-lsc-white dark:bg-earth-800 px-4 py-3">
              <dt className="text-[10px] uppercase tracking-wider font-semibold text-lsc-dark/50 dark:text-lsc-cream/50">Usage</dt>
              <dd className="mt-0.5 text-sm tabular-nums text-lsc-dark dark:text-lsc-cream">{tool.usage_count} {tool.usage_count === 1 ? "chat" : "chats"}</dd>
            </div>
          </dl>

          {/* Access + description */}
          {(tool.requires_auth || tool.in_library_only) && (
            <div className="mt-4 flex flex-wrap gap-2">
              {tool.requires_auth && (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs bg-lsc-cream dark:bg-earth-900 border border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70">
                  <Lock aria-hidden="true" className="h-3.5 w-3.5" />
                  Requires sign-in
                </span>
              )}
              {tool.in_library_only && (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs bg-lsc-cream dark:bg-earth-900 border border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70">
                  <MapPin aria-hidden="true" className="h-3.5 w-3.5" />
                  In-library only
                </span>
              )}
            </div>
          )}
          {tool.description && (
            <p className="mt-3 max-w-prose text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{tool.description}</p>
          )}
        </SectionCard>
      ))}

      {!editingTool && aiTools.length === 0 && (
        <SectionCard>
          <p className="text-center text-lsc-dark/70 dark:text-lsc-cream/60 py-8">
            No AI tools configured yet. Create tools using the AI Tools API.
          </p>
        </SectionCard>
      )}
    </div>
  )
}
