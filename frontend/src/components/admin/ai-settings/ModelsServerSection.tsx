/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useCallback, useEffect } from "react"
import { Cpu, Sparkles, Settings, TestTube } from "lucide-react"
import toast from "react-hot-toast"
import api from "@/api/api"
import { useTranslation } from "@/i18n"
import { SectionShell } from "./SectionShell"
import { StatusTab } from "./StatusTab"
import { ModelsTab } from "./ModelsTab"
import { ConfigTab } from "./ConfigTab"
import { TestTab } from "./TestTab"
import type { OllamaStatus, AIConfig, AIStats, TestResult, AllowedModel } from "./types"

interface ModelsServerSectionProps {
  onBack: () => void
}

const formatBytes = (bytes?: number) => {
  if (!bytes) return "Unknown"
  const gb = bytes / (1024 * 1024 * 1024)
  if (gb >= 1) return `${gb.toFixed(1)} GB`
  return `${(bytes / (1024 * 1024)).toFixed(0)} MB`
}

const tabs = [
  { id: "status", label: "Server Status", icon: Cpu },
  { id: "models", label: "Model Allowlist", icon: Sparkles },
  { id: "config", label: "Fine-Tuning", icon: Settings },
  { id: "test", label: "Test Playground", icon: TestTube },
] as const

export function ModelsServerSection({ onBack }: ModelsServerSectionProps) {
  const { t } = useTranslation()

  // Core data
  const [, setLoading] = useState(true)
  const [ollamaStatus, setOllamaStatus] = useState<OllamaStatus | null>(null)
  const [, setConfigs] = useState<AIConfig[]>([])
  const [stats, setStats] = useState<AIStats | null>(null)
  const [agentChatConfig, setAgentChatConfig] = useState<Record<string, unknown>>({})
  const [ollamaConfig, setOllamaConfig] = useState<Record<string, unknown>>({})

  // Model allowlist
  const [allowedModels, setAllowedModels] = useState<AllowedModel[]>([])
  const [editingModel, setEditingModel] = useState<Partial<AllowedModel> | null>(null)

  // Test state
  const [testPrompt, setTestPrompt] = useState("")
  const [testSystemPrompt, setTestSystemPrompt] = useState("")
  const [testResult, setTestResult] = useState<TestResult | null>(null)
  const [testing, setTesting] = useState(false)

  // Pull model state
  const [pullModelName, setPullModelName] = useState("")
  const [pulling, setPulling] = useState(false)

  const [saving, setSaving] = useState(false)

  const fetchCoreData = useCallback(async () => {
    setLoading(true)
    try {
      const [statusRes, configsRes, statsRes] = await Promise.all([
        api.get("/api/v1/admin/ai/ollama/status"),
        api.get("/api/v1/admin/ai/configs"),
        api.get("/api/v1/admin/ai/stats"),
      ])
      setOllamaStatus(statusRes)
      setConfigs(configsRes)
      setStats(statsRes)
      const agentChat = configsRes.find((c: AIConfig) => c.config_key === "agent_chat")
      const ollama = configsRes.find((c: AIConfig) => c.config_key === "ollama")
      if (agentChat) setAgentChatConfig(agentChat.config_value)
      if (ollama) setOllamaConfig(ollama.config_value)
    } catch {
      toast.error(t("admin.adminAISettings.failedToLoadAiSettings"))
    } finally {
      setLoading(false)
    }
  }, [t])

  const fetchAllowedModels = useCallback(async () => {
    try {
      const res = await api.get("/api/v1/admin/ollama/models/allowlist")
      setAllowedModels(res)
    } catch {
      // Silently fail -- tab will show empty state
    }
  }, [])

  useEffect(() => {
    void fetchCoreData()
  }, [fetchCoreData])

  const saveConfig = async (configKey: string, configValue: Record<string, unknown>) => {
    setSaving(true)
    try {
      await api.put(`/api/v1/admin/ai/configs/${configKey}`, { config_value: configValue })
      toast.success(t("adminAISettings.toast.configurationSaved"))
      fetchCoreData()
    } catch {
      toast.error(t("admin.adminAISettings.failedToSaveConfiguration"))
    } finally {
      setSaving(false)
    }
  }

  const runTest = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      const result = await api.post("/api/v1/admin/ai/test-generation", {
        prompt: testPrompt,
        system_prompt: testSystemPrompt || undefined,
        model: agentChatConfig.model,
        temperature: agentChatConfig.temperature,
        max_tokens: 500,
      })
      setTestResult(result)
    } catch {
      setTestResult({ success: false, error: "Request failed" })
    } finally {
      setTesting(false)
    }
  }

  const pullModel = async () => {
    if (!pullModelName.trim()) return
    setPulling(true)
    try {
      await api.post(`/api/v1/admin/ai/ollama/pull-model?model_name=${encodeURIComponent(pullModelName)}`)
      toast.success(t("adminAISettings.toast.modelPullStarted", { model: pullModelName }))
      setPullModelName("")
      setTimeout(fetchCoreData, 5000)
    } catch (err) {
      const msg = (err as Record<string, unknown> & { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Failed to pull model"
      toast.error(msg)
    } finally {
      setPulling(false)
    }
  }

  const saveAllowedModel = async () => {
    if (!editingModel) return
    setSaving(true)
    try {
      if (editingModel.id) {
        await api.put(`/api/v1/admin/ollama/models/allowlist/${editingModel.id}`, editingModel)
        toast.success(t("adminAISettings.toast.modelUpdated"))
      } else {
        await api.post("/api/v1/admin/ollama/models/allowlist", editingModel)
        toast.success(t("admin.adminAISettings.modelAddedToAllowlist"))
      }
      setEditingModel(null)
      fetchAllowedModels()
    } catch {
      toast.error(t("admin.adminAISettings.failedToSaveModel"))
    } finally {
      setSaving(false)
    }
  }

  const deleteAllowedModel = async (id: number) => {
    try {
      await api.delete(`/api/v1/admin/ollama/models/allowlist/${id}`)
      toast.success(t("admin.adminAISettings.modelRemovedFromAllowlist"))
      fetchAllowedModels()
    } catch {
      toast.error(t("admin.adminAISettings.failedToRemoveModel"))
    }
  }

  return (
    <SectionShell
      title="Models & Server"
      description="Manage the AI server and which models are available. Everything runs on hardware you control."
      tabs={[...tabs]}
      onBack={onBack}
    >
      {(activeTab) => {
        if (activeTab === "models") {
          if (allowedModels.length === 0 && !editingModel) {
            void fetchAllowedModels()
          }
          return (
            <ModelsTab
              allowedModels={allowedModels}
              editingModel={editingModel}
              setEditingModel={setEditingModel}
              saving={saving}
              onSaveAllowedModel={saveAllowedModel}
              onDeleteAllowedModel={deleteAllowedModel}
            />
          )
        }
        if (activeTab === "config") {
          return (
            <ConfigTab
              agentChatConfig={agentChatConfig}
              setAgentChatConfig={setAgentChatConfig}
              ollamaStatus={ollamaStatus}
              saving={saving}
              onSaveConfig={saveConfig}
            />
          )
        }
        if (activeTab === "test") {
          return (
            <TestTab
              testPrompt={testPrompt}
              setTestPrompt={setTestPrompt}
              testSystemPrompt={testSystemPrompt}
              setTestSystemPrompt={setTestSystemPrompt}
              testResult={testResult}
              testing={testing}
              ollamaStatus={ollamaStatus}
              onRunTest={runTest}
            />
          )
        }
        return (
          <StatusTab
            ollamaStatus={ollamaStatus}
            stats={stats}
            ollamaConfig={ollamaConfig}
            setOllamaConfig={setOllamaConfig}
            pullModelName={pullModelName}
            setPullModelName={setPullModelName}
            pulling={pulling}
            saving={saving}
            onPullModel={pullModel}
            onRefresh={fetchCoreData}
            onSaveConfig={saveConfig}
            formatBytes={formatBytes}
          />
        )
      }}
    </SectionShell>
  )
}
