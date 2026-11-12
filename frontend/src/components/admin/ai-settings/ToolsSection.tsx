/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useCallback } from 'react'
import { Bot, Shield, Gauge, ScrollText } from 'lucide-react'
import api from '@/api/api'
import toast from 'react-hot-toast'
import { useTranslation } from '@/i18n'
import { SectionShell } from './SectionShell'
import { ToolsTab } from './ToolsTab'
import { GuardrailsTab } from './GuardrailsTab'
import { LimitsTab } from './LimitsTab'
import { AuditTab } from './AuditTab'
import type { AITool, Guardrail, UsageLimit, UsageLogEntry, UsageSummary } from './types'

const tabs = [
  { id: 'tools', label: 'Tools', icon: Bot },
  { id: 'guardrails', label: 'Guardrails', icon: Shield },
  { id: 'limits', label: 'Usage Limits', icon: Gauge },
  { id: 'audit', label: 'Audit Log', icon: ScrollText },
] as const

interface ToolsSectionProps {
  onBack: () => void
}

export function ToolsSection({ onBack }: ToolsSectionProps) {
  const { t } = useTranslation()

  // Data state
  const [aiTools, setAiTools] = useState<AITool[]>([])
  const [guardrails, setGuardrails] = useState<Guardrail[]>([])
  const [usageLimits, setUsageLimits] = useState<UsageLimit[]>([])
  const [usageLogs, setUsageLogs] = useState<UsageLogEntry[]>([])
  const [usageSummary, setUsageSummary] = useState<UsageSummary | null>(null)

  // Editing state
  const [editingTool, setEditingTool] = useState<AITool | null>(null)
  const [editingGuardrail, setEditingGuardrail] = useState<Partial<Guardrail> | null>(null)
  const [editingLimit, setEditingLimit] = useState<Partial<UsageLimit> | null>(null)
  const [saving, setSaving] = useState(false)

  // Track which tabs have been loaded
  const [loaded, setLoaded] = useState<Record<string, boolean>>({})
  const [activeTab, setActiveTab] = useState('tools')

  // --- Fetchers ---

  const fetchAiTools = useCallback(async () => {
    try {
      const data = await api.get('/api/v1/admin/ollama/tools')
      setAiTools(Array.isArray(data) ? data : [])
    } catch { /* tab will show empty state */ }
  }, [])

  const fetchGuardrails = useCallback(async () => {
    try {
      const data = await api.get('/api/v1/admin/ollama/guardrails')
      setGuardrails(Array.isArray(data) ? data : [])
    } catch { /* empty state */ }
  }, [])

  const fetchUsageLimits = useCallback(async () => {
    try {
      const data = await api.get('/api/v1/admin/ollama/usage-limits')
      setUsageLimits(Array.isArray(data) ? data : [])
    } catch { /* empty state */ }
  }, [])

  const fetchAuditData = useCallback(async () => {
    try {
      const [logsRes, summaryRes] = await Promise.allSettled([
        api.get('/api/v1/admin/ollama/usage-logs?limit=50'),
        api.get('/api/v1/admin/ollama/usage-logs/summary?days=7'),
      ])
      if (logsRes.status === 'fulfilled') setUsageLogs(Array.isArray(logsRes.value) ? logsRes.value : [])
      if (summaryRes.status === 'fulfilled') setUsageSummary(summaryRes.value)
    } catch { /* empty state */ }
  }, [])

  // Lazy-load data when tab becomes active
  useEffect(() => {
    if (loaded[activeTab]) return
    setLoaded((prev) => ({ ...prev, [activeTab]: true }))

    switch (activeTab) {
      case 'tools': void fetchAiTools(); break
      case 'guardrails': void fetchGuardrails(); break
      case 'limits': void fetchUsageLimits(); break
      case 'audit': void fetchAuditData(); break
    }
  }, [activeTab, loaded, fetchAiTools, fetchGuardrails, fetchUsageLimits, fetchAuditData])

  // --- Tool handlers ---

  const toggleTool = async (toolId: string, enabled: boolean) => {
    try {
      await api.put(`/api/v1/admin/ollama/tools/${toolId}/toggle?enabled=${enabled}`, {})
      toast.success(t('adminAISettings.toast.toolToggled', { action: enabled ? 'enabled' : 'disabled' }))
      void fetchAiTools()
    } catch {
      toast.error(t('admin.adminAISettings.failedToToggleTool'))
    }
  }

  const saveToolPrompt = async () => {
    if (!editingTool) return
    setSaving(true)
    try {
      await api.put(`/api/v1/ai-tools/admin/tools/${editingTool.tool_id}`, {
        system_prompt: editingTool.system_prompt,
        temperature: editingTool.temperature,
        max_tokens: editingTool.max_tokens,
        model: editingTool.model,
        name: editingTool.name,
        description: editingTool.description,
        in_library_only: editingTool.in_library_only,
        requires_auth: editingTool.requires_auth,
      })
      toast.success(t('adminAISettings.toast.toolUpdated'))
      setEditingTool(null)
      void fetchAiTools()
    } catch {
      toast.error(t('admin.adminAISettings.failedToUpdateTool'))
    } finally {
      setSaving(false)
    }
  }

  // --- Guardrail handlers ---

  const saveGuardrail = async () => {
    if (!editingGuardrail) return
    setSaving(true)
    try {
      if (editingGuardrail.id) {
        await api.put(`/api/v1/admin/ollama/guardrails/${editingGuardrail.id}`, editingGuardrail)
        toast.success(t('adminAISettings.toast.guardrailUpdated'))
      } else {
        await api.post('/api/v1/admin/ollama/guardrails', editingGuardrail)
        toast.success(t('adminAISettings.toast.guardrailCreated'))
      }
      setEditingGuardrail(null)
      void fetchGuardrails()
    } catch {
      toast.error(t('admin.adminAISettings.failedToSaveGuardrail'))
    } finally {
      setSaving(false)
    }
  }

  const deleteGuardrail = async (id: number) => {
    try {
      await api.delete(`/api/v1/admin/ollama/guardrails/${id}`)
      toast.success(t('adminAISettings.toast.guardrailDeleted'))
      void fetchGuardrails()
    } catch {
      toast.error(t('admin.adminAISettings.failedToDeleteGuardrail'))
    }
  }

  // --- Usage limit handlers ---

  const saveUsageLimit = async () => {
    if (!editingLimit) return
    setSaving(true)
    try {
      if (editingLimit.id) {
        await api.put(`/api/v1/admin/ollama/usage-limits/${editingLimit.id}`, editingLimit)
        toast.success(t('adminAISettings.toast.limitUpdated'))
      } else {
        await api.post('/api/v1/admin/ollama/usage-limits', editingLimit)
        toast.success(t('adminAISettings.toast.limitCreated'))
      }
      setEditingLimit(null)
      void fetchUsageLimits()
    } catch {
      toast.error(t('admin.adminAISettings.failedToSaveLimit'))
    } finally {
      setSaving(false)
    }
  }

  const deleteUsageLimit = async (id: number) => {
    try {
      await api.delete(`/api/v1/admin/ollama/usage-limits/${id}`)
      toast.success(t('adminAISettings.toast.limitDeleted'))
      void fetchUsageLimits()
    } catch {
      toast.error(t('admin.adminAISettings.failedToDeleteLimit'))
    }
  }

  return (
    <SectionShell
      title="AI Tools & Chatbots"
      description="AI assistants that run on your library's own server. No patron conversations leave the building."
      tabs={[...tabs]}
      onBack={onBack}
    >
      {(tab) => {
        // Sync internal tracking with SectionShell's active tab
        if (tab !== activeTab) setActiveTab(tab)

        switch (tab) {
          case 'tools':
            return (
              <ToolsTab
                aiTools={aiTools}
                editingTool={editingTool}
                setEditingTool={setEditingTool}
                saving={saving}
                onToggleTool={toggleTool}
                onSaveToolPrompt={saveToolPrompt}
              />
            )
          case 'guardrails':
            return (
              <GuardrailsTab
                guardrails={guardrails}
                editingGuardrail={editingGuardrail}
                setEditingGuardrail={setEditingGuardrail}
                saving={saving}
                onSaveGuardrail={saveGuardrail}
                onDeleteGuardrail={deleteGuardrail}
              />
            )
          case 'limits':
            return (
              <LimitsTab
                usageLimits={usageLimits}
                editingLimit={editingLimit}
                setEditingLimit={setEditingLimit}
                saving={saving}
                onSaveUsageLimit={saveUsageLimit}
                onDeleteUsageLimit={deleteUsageLimit}
              />
            )
          case 'audit':
            return (
              <AuditTab
                usageLogs={usageLogs}
                usageSummary={usageSummary}
                onRefresh={fetchAuditData}
              />
            )
          default:
            return null
        }
      }}
    </SectionShell>
  )
}
