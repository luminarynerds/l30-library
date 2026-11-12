/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Save, Loader2, Plus, Trash2, Edit3 } from "lucide-react"
import { useTranslation } from "@/i18n"
import { SectionCard, Label, InputField, PrimaryButton, DangerButton } from "./ai-settings-primitives"
import type { UsageLimit } from "./types"

interface LimitsTabProps {
  usageLimits: UsageLimit[]
  editingLimit: Partial<UsageLimit> | null
  setEditingLimit: (l: Partial<UsageLimit> | null) => void
  saving: boolean
  onSaveUsageLimit: () => void
  onDeleteUsageLimit: (id: number) => void
}

export function LimitsTab({
  usageLimits,
  editingLimit,
  setEditingLimit,
  saving,
  onSaveUsageLimit,
  onDeleteUsageLimit,
}: LimitsTabProps) {
  const { t } = useTranslation()

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-2">
        <div>
          <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{t('admin.adminAISettings.usageLimitsByRole')}</h3>
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('admin.adminAISettings.setDailyHourlyRequestLimits')}</p>
        </div>
        <PrimaryButton onClick={() => setEditingLimit({ role: "", daily_limit: 50, hourly_limit: 10, max_tokens_per_request: 2000, enabled: true })}>
          <Plus className="h-4 w-4" /> Add Limit
        </PrimaryButton>
      </div>

      {editingLimit && (
        <SectionCard className="border-2 border-lsc-rose">
          <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
            {editingLimit.id ? "Edit Limit" : "New Usage Limit"}
          </h4>
          <div className="space-y-4">
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <Label>Role</Label>
                <select
                  value={editingLimit.role || ""}
                  onChange={(e) => setEditingLimit({ ...editingLimit, role: e.target.value })}
                  disabled={!!editingLimit.id}
                  className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-earth-100"
                >
                  <option value="">Select role...</option>
                  <option value="patron">Patron</option>
                  <option value="staff">Staff (Librarian)</option>
                  <option value="admin">Admin</option>
                  <option value="child">Child</option>
                </select>
              </div>
              <div>
                <Label>{t('admin.adminAISettings.maxTokensPerRequest')}</Label>
                <InputField type="number" value={editingLimit.max_tokens_per_request || 2000}
                  onChange={(e) => setEditingLimit({ ...editingLimit, max_tokens_per_request: parseInt(e.target.value) })} />
              </div>
            </div>
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <Label>{t('admin.adminAISettings.dailyLimitRequestsDay')}</Label>
                <InputField type="number" value={editingLimit.daily_limit || 50}
                  onChange={(e) => setEditingLimit({ ...editingLimit, daily_limit: parseInt(e.target.value) })} />
              </div>
              <div>
                <Label>{t('admin.adminAISettings.hourlyLimitRequestsHour')}</Label>
                <InputField type="number" value={editingLimit.hourly_limit || 10}
                  onChange={(e) => setEditingLimit({ ...editingLimit, hourly_limit: parseInt(e.target.value) })} />
              </div>
            </div>
            <div className="flex gap-2">
              <PrimaryButton onClick={onSaveUsageLimit} disabled={saving || !editingLimit.role}>
                {saving ? <Loader2 className="h-4 w-4 motion-safe:animate-spin" /> : <Save className="h-4 w-4" />}
                {editingLimit.id ? "Update" : "Create"}
              </PrimaryButton>
              <button onClick={() => setEditingLimit(null)} className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark">Cancel</button>
            </div>
          </div>
        </SectionCard>
      )}

      <div className="grid gap-3">
        {usageLimits.map((l) => (
          <SectionCard key={l.id}>
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">{l.role}</h4>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                  {l.daily_limit} requests/day | {l.hourly_limit} requests/hour | {l.max_tokens_per_request} max tokens
                </p>
              </div>
              <div className="flex items-center gap-1">
                <button onClick={() => setEditingLimit(l)} className="p-2 rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700">
                  <Edit3 className="h-4 w-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
                </button>
                <DangerButton onClick={() => onDeleteUsageLimit(l.id)}><Trash2 className="h-4 w-4" /></DangerButton>
              </div>
            </div>
          </SectionCard>
        ))}
      </div>

      {usageLimits.length === 0 && !editingLimit && (
        <SectionCard>
          <p className="text-center text-lsc-dark/70 dark:text-lsc-cream/60 py-8">
            No usage limits configured. All roles have unlimited AI access.
            Add limits to control costs and prevent abuse.
          </p>
        </SectionCard>
      )}
    </div>
  )
}
