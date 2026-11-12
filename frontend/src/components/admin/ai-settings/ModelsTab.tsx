/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Save, Loader2, Plus, Trash2, Edit3 } from "lucide-react"
import { useTranslation } from "@/i18n"
import { SectionCard, Label, InputField, PrimaryButton, DangerButton } from "./ai-settings-primitives"
import type { AllowedModel } from "./types"

interface ModelsTabProps {
  allowedModels: AllowedModel[]
  editingModel: Partial<AllowedModel> | null
  setEditingModel: (m: Partial<AllowedModel> | null) => void
  saving: boolean
  onSaveAllowedModel: () => void
  onDeleteAllowedModel: (id: number) => void
}

export function ModelsTab({
  allowedModels,
  editingModel,
  setEditingModel,
  saving,
  onSaveAllowedModel,
  onDeleteAllowedModel,
}: ModelsTabProps) {
  const { t } = useTranslation()

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-2">
        <div>
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">Model Allowlist</h3>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('admin.adminAISettings.controlWhichModelsLibrariansCan')}</p>
        </div>
        <PrimaryButton onClick={() => setEditingModel({ model_name: "", display_name: "", max_tokens_limit: 4000, allowed_temperature_min: 0, allowed_temperature_max: 1.5, enabled: true })}>
          <Plus className="h-4 w-4" /> Add Model
        </PrimaryButton>
      </div>

      {editingModel && (
        <SectionCard className="border-2 border-lsc-rose">
          <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
            {editingModel.id ? "Edit Model" : "Add Model to Allowlist"}
          </h4>
          <div className="space-y-4">
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <Label>{t('admin.adminAISettings.modelNameAsSeenIn')}</Label>
                <InputField value={editingModel.model_name || ""} onChange={(e) => setEditingModel({ ...editingModel, model_name: e.target.value })} placeholder={t('placeholder.adminAISettings.llama323b')} disabled={!!editingModel.id} />
              </div>
              <div>
                <Label>Display Name</Label>
                <InputField value={editingModel.display_name || ""} onChange={(e) => setEditingModel({ ...editingModel, display_name: e.target.value })} placeholder={t('placeholder.adminAISettings.llama323b1')} />
              </div>
            </div>
            <div>
              <Label>Description</Label>
              <InputField value={editingModel.description || ""} onChange={(e) => setEditingModel({ ...editingModel, description: e.target.value })} placeholder={t('admin.adminAISettings.goodForGeneralLibraryQueries')} />
            </div>
            <div className="grid md:grid-cols-3 gap-4">
              <div>
                <Label>Max Tokens Limit</Label>
                <InputField type="number" value={editingModel.max_tokens_limit || 4000} onChange={(e) => setEditingModel({ ...editingModel, max_tokens_limit: parseInt(e.target.value) })} />
              </div>
              <div>
                <Label>Min Temperature</Label>
                <InputField type="number" value={editingModel.allowed_temperature_min || 0} onChange={(e) => setEditingModel({ ...editingModel, allowed_temperature_min: parseFloat(e.target.value) })} step="0.1" min="0" max="2" />
              </div>
              <div>
                <Label>Max Temperature</Label>
                <InputField type="number" value={editingModel.allowed_temperature_max || 1.5} onChange={(e) => setEditingModel({ ...editingModel, allowed_temperature_max: parseFloat(e.target.value) })} step="0.1" min="0" max="2" />
              </div>
            </div>
            <div className="flex gap-2">
              <PrimaryButton onClick={onSaveAllowedModel} disabled={saving || !editingModel.model_name}>
                {saving ? <Loader2 className="h-4 w-4 motion-safe:animate-spin" /> : <Save className="h-4 w-4" />}
                {editingModel.id ? "Update" : "Add"}
              </PrimaryButton>
              <button onClick={() => setEditingModel(null)} className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark">Cancel</button>
            </div>
          </div>
        </SectionCard>
      )}

      <div className="grid gap-3">
        {allowedModels.map((m) => (
          <SectionCard key={m.id}>
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-serif font-semibold font-mono text-lsc-dark dark:text-lsc-cream">{m.model_name}</h4>
                {m.display_name && <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{m.display_name}</p>}
              </div>
              <div className="flex items-center gap-1">
                <button onClick={() => setEditingModel(m)} className="p-2 rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700">
                  <Edit3 className="h-4 w-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
                </button>
                <DangerButton onClick={() => onDeleteAllowedModel(m.id)}><Trash2 className="h-4 w-4" /></DangerButton>
              </div>
            </div>
            <div className="mt-2 text-xs text-lsc-dark/70 dark:text-lsc-cream/60">
              Max tokens: {m.max_tokens_limit} | Temperature: {m.allowed_temperature_min} - {m.allowed_temperature_max}
              {m.description && ` | ${m.description}`}
            </div>
          </SectionCard>
        ))}
      </div>

      {allowedModels.length === 0 && !editingModel && (
        <SectionCard>
          <p className="text-center text-lsc-dark/70 dark:text-lsc-cream/60 py-8">
            No model allowlist configured. All installed Ollama models are currently available.
            Add models here to restrict which ones can be used.
          </p>
        </SectionCard>
      )}
    </div>
  )
}
