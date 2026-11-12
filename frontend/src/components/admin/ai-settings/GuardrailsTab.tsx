/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Shield, Save, Loader2, Plus, Trash2, Edit3 } from "lucide-react"
import { useTranslation } from "@/i18n"
import { SectionCard, Label, InputField, TextArea, PrimaryButton, DangerButton } from "./ai-settings-primitives"
import type { Guardrail } from "./types"

const ruleTypeLabels: Record<string, string> = {
  blocked_topic: "Blocked Topic",
  required_disclaimer: "Required Disclaimer",
  content_filter: "Content Filter",
  response_prefix: "Response Prefix",
}

interface GuardrailsTabProps {
  guardrails: Guardrail[]
  editingGuardrail: Partial<Guardrail> | null
  setEditingGuardrail: (g: Partial<Guardrail> | null) => void
  saving: boolean
  onSaveGuardrail: () => void
  onDeleteGuardrail: (id: number) => void
}

export function GuardrailsTab({
  guardrails,
  editingGuardrail,
  setEditingGuardrail,
  saving,
  onSaveGuardrail,
  onDeleteGuardrail,
}: GuardrailsTabProps) {
  const { t } = useTranslation()

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-2">
        <div>
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Content Guardrails</h3>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('admin.adminAISettings.setBoundariesForWhatAi')}</p>
        </div>
        <PrimaryButton onClick={() => setEditingGuardrail({ name: "", rule_type: "blocked_topic", rule_config: { keywords: [], message: "I'm not able to discuss that topic." }, applies_to_tools: [], audience_minor: "all", audience_patron_types: [], priority: 0, enabled: true })}>
          <Plus className="h-4 w-4" /> Add Guardrail
        </PrimaryButton>
      </div>

      {editingGuardrail && (
        <SectionCard className="border-2 border-lsc-rose">
          <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
            {editingGuardrail.id ? "Edit Guardrail" : "New Guardrail"}
          </h4>
          <div className="space-y-4">
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <Label>Name</Label>
                <InputField value={editingGuardrail.name || ""} onChange={(e) => setEditingGuardrail({ ...editingGuardrail, name: e.target.value })} placeholder={t('placeholder.adminAISettings.egBlockPoliticalTopics')} />
              </div>
              <div>
                <Label>Rule Type</Label>
                <select
                  value={editingGuardrail.rule_type || "blocked_topic"}
                  onChange={(e) => {
                    const newType = e.target.value;
                    const defaults: Record<string, Record<string, unknown>> = {
                      blocked_topic: { keywords: [], message: "I'm not able to discuss that topic." },
                      required_disclaimer: { text: t('admin.adminAISettings.thisIsAiGeneratedContent'), position: "append" },
                      content_filter: { max_length: 2000, block_urls: true, block_code: false },
                      response_prefix: { text: t('admin.adminAISettings.asALibraryAiAssistant') },
                    };
                    setEditingGuardrail({ ...editingGuardrail, rule_type: newType, rule_config: defaults[newType] || {} });
                  }}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-earth-100"
                >
                  <option value="blocked_topic">Blocked Topic</option>
                  <option value="required_disclaimer">Required Disclaimer</option>
                  <option value="content_filter">Content Filter</option>
                  <option value="response_prefix">Response Prefix</option>
                </select>
              </div>
            </div>
            <div>
              <Label>Description</Label>
              <InputField value={editingGuardrail.description || ""} onChange={(e) => setEditingGuardrail({ ...editingGuardrail, description: e.target.value })} placeholder={t('admin.adminAISettings.whatDoesThisGuardrailDo')} />
            </div>

            {editingGuardrail.rule_type === "blocked_topic" && (
              <>
                <div>
                  <Label>Blocked Keywords (comma-separated)</Label>
                  <InputField
                    value={((editingGuardrail.rule_config as Record<string, unknown>)?.keywords as string[] || []).join(", ")}
                    onChange={(e) => setEditingGuardrail({
                      ...editingGuardrail,
                      rule_config: { ...editingGuardrail.rule_config, keywords: e.target.value.split(",").map(k => k.trim()).filter(Boolean) }
                    })}
                    placeholder={t('placeholder.adminAISettings.politicsReligionViolence')}
                  />
                </div>
                <div>
                  <Label>{t('admin.adminAISettings.blockMessageShownToUser')}</Label>
                  <InputField
                    value={String((editingGuardrail.rule_config as Record<string, unknown>)?.message || "")}
                    onChange={(e) => setEditingGuardrail({ ...editingGuardrail, rule_config: { ...editingGuardrail.rule_config, message: e.target.value } })}
                  />
                </div>
              </>
            )}

            {editingGuardrail.rule_type === "required_disclaimer" && (
              <>
                <div>
                  <Label>Disclaimer Text</Label>
                  <TextArea
                    value={String((editingGuardrail.rule_config as Record<string, unknown>)?.text || "")}
                    onChange={(e) => setEditingGuardrail({ ...editingGuardrail, rule_config: { ...editingGuardrail.rule_config, text: e.target.value } })}
                    rows={2}
                  />
                </div>
                <div>
                  <Label>Position</Label>
                  <select
                    value={String((editingGuardrail.rule_config as Record<string, unknown>)?.position || "append")}
                    onChange={(e) => setEditingGuardrail({ ...editingGuardrail, rule_config: { ...editingGuardrail.rule_config, position: e.target.value } })}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-earth-100"
                  >
                    <option value="prepend">Before response</option>
                    <option value="append">After response</option>
                  </select>
                </div>
              </>
            )}

            {editingGuardrail.rule_type === "content_filter" && (
              <div className="grid md:grid-cols-3 gap-4">
                <div>
                  <Label>Max Response Length</Label>
                  <InputField type="number" value={Number((editingGuardrail.rule_config as Record<string, unknown>)?.max_length || 2000)}
                    onChange={(e) => setEditingGuardrail({ ...editingGuardrail, rule_config: { ...editingGuardrail.rule_config, max_length: parseInt(e.target.value) } })} />
                </div>
                <label className="flex items-center gap-2 text-sm mt-6">
                  <input type="checkbox" checked={Boolean((editingGuardrail.rule_config as Record<string, unknown>)?.block_urls)}
                    onChange={(e) => setEditingGuardrail({ ...editingGuardrail, rule_config: { ...editingGuardrail.rule_config, block_urls: e.target.checked } })} className="rounded" />
                  Block URLs in responses
                </label>
                <label className="flex items-center gap-2 text-sm mt-6">
                  <input type="checkbox" checked={Boolean((editingGuardrail.rule_config as Record<string, unknown>)?.block_code)}
                    onChange={(e) => setEditingGuardrail({ ...editingGuardrail, rule_config: { ...editingGuardrail.rule_config, block_code: e.target.checked } })} className="rounded" />
                  Block code blocks
                </label>
              </div>
            )}

            {editingGuardrail.rule_type === "response_prefix" && (
              <div>
                <Label>{t('admin.adminAISettings.prefixTextAddedToStart')}</Label>
                <InputField
                  value={String((editingGuardrail.rule_config as Record<string, unknown>)?.text || "")}
                  onChange={(e) => setEditingGuardrail({ ...editingGuardrail, rule_config: { ...editingGuardrail.rule_config, text: e.target.value } })}
                />
              </div>
            )}

            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <Label>{t('admin.adminAISettings.priorityLowerAppliedFirst')}</Label>
                <InputField type="number" value={editingGuardrail.priority || 0}
                  onChange={(e) => setEditingGuardrail({ ...editingGuardrail, priority: parseInt(e.target.value) })} />
              </div>
              <label className="flex items-center gap-2 text-sm mt-6">
                <input type="checkbox" checked={editingGuardrail.enabled !== false}
                  onChange={(e) => setEditingGuardrail({ ...editingGuardrail, enabled: e.target.checked })} className="rounded" />
                Enabled
              </label>
            </div>

            <div className="border-t border-lsc-border dark:border-earth-700 pt-4 space-y-3">
              <div>
                <h5 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">Audience scoping</h5>
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
                  Limit when this rule fires. Defaults apply to everyone.
                </p>
              </div>
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <Label>Apply to</Label>
                  <select
                    value={editingGuardrail.audience_minor || "all"}
                    onChange={(e) => setEditingGuardrail({ ...editingGuardrail, audience_minor: e.target.value as "all" | "minors_only" | "adults_only" })}
                    className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-earth-100 focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                  >
                    <option value="all">All users</option>
                    <option value="minors_only">Minors only (under 13)</option>
                    <option value="adults_only">Adults only</option>
                  </select>
                </div>
                <div>
                  <Label>Limit to patron types</Label>
                  <div className="flex items-center gap-4 mt-2 flex-wrap">
                    {(["child", "teen", "adult"] as const).map((pt) => {
                      const checked = (editingGuardrail.audience_patron_types || []).includes(pt)
                      return (
                        <label key={pt} className="flex items-center gap-2 text-sm capitalize">
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={(e) => {
                              const current = editingGuardrail.audience_patron_types || []
                              const next = e.target.checked
                                ? Array.from(new Set([...current, pt]))
                                : current.filter((v) => v !== pt)
                              setEditingGuardrail({ ...editingGuardrail, audience_patron_types: next })
                            }}
                            className="rounded"
                          />
                          {pt}
                        </label>
                      )
                    })}
                  </div>
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                    Leave all unchecked to apply to every patron type.
                  </p>
                </div>
              </div>
            </div>

            <div className="flex gap-2">
              <PrimaryButton onClick={onSaveGuardrail} disabled={saving || !editingGuardrail.name}>
                {saving ? <Loader2 className="h-4 w-4 motion-safe:animate-spin" /> : <Save className="h-4 w-4" />}
                {editingGuardrail.id ? "Update" : "Create"}
              </PrimaryButton>
              <button onClick={() => setEditingGuardrail(null)} className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark">Cancel</button>
            </div>
          </div>
        </SectionCard>
      )}

      {guardrails.map((g) => (
        <SectionCard key={g.id}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Shield className={`h-5 w-5 ${g.enabled ? "text-status-success-600" : "text-lsc-dark/30 dark:text-lsc-cream/60"}`} />
              <div>
                <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{g.name}</h4>
                <span className="text-xs px-2 py-0.5 rounded-full bg-lsc-cream dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70">
                  {ruleTypeLabels[g.rule_type] || g.rule_type}
                </span>
              </div>
              {!g.enabled && <span className="text-xs text-status-danger-500">Disabled</span>}
            </div>
            <div className="flex items-center gap-1">
              <button onClick={() => setEditingGuardrail(g)} className="p-2 rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700">
                <Edit3 className="h-4 w-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
              </button>
              <DangerButton onClick={() => onDeleteGuardrail(g.id)}>
                <Trash2 className="h-4 w-4" />
              </DangerButton>
            </div>
          </div>
          {g.description && <p className="mt-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/60">{g.description}</p>}
          {(g.audience_minor && g.audience_minor !== "all") || (g.audience_patron_types?.length ?? 0) > 0 ? (
            <div className="mt-2 flex items-center gap-2 flex-wrap">
              {g.audience_minor === "minors_only" && (
                <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-200">
                  Minors only
                </span>
              )}
              {g.audience_minor === "adults_only" && (
                <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-200">
                  Adults only
                </span>
              )}
              {(g.audience_patron_types?.length ?? 0) > 0 && (
                <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-800 dark:text-status-warning-200">
                  Types: {g.audience_patron_types.join(", ")}
                </span>
              )}
            </div>
          ) : null}
          <div className="mt-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/60 font-mono">
            Priority: {g.priority} | Config: {JSON.stringify(g.rule_config).slice(0, 100)}...
          </div>
        </SectionCard>
      ))}

      {guardrails.length === 0 && !editingGuardrail && (
        <SectionCard>
          <p className="text-center text-lsc-dark/70 dark:text-lsc-cream/60 py-8">
            No guardrails configured. Add guardrails to control AI behavior and protect patrons.
          </p>
        </SectionCard>
      )}
    </div>
  )
}
