/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useEffect, useRef } from 'react'
import {
  Bot, Plus, BarChart2, MessageCircle, BookOpen,
  AlertCircle, Check, X
} from 'lucide-react'
import { SUCCESS_FEEDBACK_DURATION_MS } from '@/constants/timeouts'
import {
  getAgents,
  createAgent,
  updateAgent,
  toggleAgentStatus,
  getAgentStats,
  getConversations,
} from '@/api/library-agents-api'
import type {
  LibraryAgent,
  AgentCreateData,
  AgentStats,
  AgentConversation,
} from '@/api/library-agents-api'
import { useAuth } from '@/contexts/AuthContext'
import { clean } from '@/lib/utils'
import { SectionShell } from './SectionShell'
import { AgentFormModal } from '../../library-agents/AgentFormModal'
import { AgentsTab } from '../../library-agents/AgentsTab'
import { ConversationsTab } from '../../library-agents/ConversationsTab'
import { KnowledgeTab } from '../../library-agents/KnowledgeTab'
import { AnalyticsTab } from '../../library-agents/AnalyticsTab'

const TABS = [
  { id: 'agents', label: 'Agents', icon: Bot },
  { id: 'conversations', label: 'Conversations', icon: MessageCircle },
  { id: 'knowledge', label: 'Knowledge Base', icon: BookOpen },
  { id: 'analytics', label: 'Analytics', icon: BarChart2 },
] as const

interface AgentsSectionProps {
  onBack: () => void
}

export function AgentsSection({ onBack }: AgentsSectionProps) {
  const { token: authToken } = useAuth()
  const [activeTab, setActiveTab] = useState('agents')
  const activeTabRef = useRef(activeTab)
  const [agents, setAgents] = useState<LibraryAgent[]>([])
  const [isLoadingAgents, setIsLoadingAgents] = useState(true)
  const [agentsError, setAgentsError] = useState<string | null>(null)
  const [editingAgent, setEditingAgent] = useState<LibraryAgent | null>(null)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [isSavingAgent, setIsSavingAgent] = useState(false)
  const [isTogglingId, setIsTogglingId] = useState<number | null>(null)
  const [conversations, setConversations] = useState<AgentConversation[]>([])
  const [isLoadingConvs, setIsLoadingConvs] = useState(false)
  const [convFilter, setConvFilter] = useState('all')
  const [stats, setStats] = useState<AgentStats | null>(null)
  const [isLoadingStats, setIsLoadingStats] = useState(false)
  const [globalError, setGlobalError] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  const showSuccess = (msg: string) => {
    setSuccessMsg(msg)
    setTimeout(() => setSuccessMsg(null), SUCCESS_FEEDBACK_DURATION_MS)
  }

  // Load agents on mount
  useEffect(() => {
    if (!authToken) return
    const load = async () => {
      try {
        const data = await getAgents(authToken, clean({ is_active: undefined }))
        setAgents(data)
      } catch {
        setAgentsError('Unable to load agents.')
      } finally {
        setIsLoadingAgents(false)
      }
    }
    void load()
  }, [authToken])

  // Lazy-load analytics when tab becomes active
  useEffect(() => {
    if (activeTab !== 'analytics' || !authToken) return
    const load = async () => {
      setIsLoadingStats(true)
      try {
        const s = await getAgentStats(authToken)
        setStats(s)
      } catch {
        // non-critical
      } finally {
        setIsLoadingStats(false)
      }
    }
    void load()
  }, [activeTab, authToken])

  // Lazy-load conversations when tab becomes active (or filter changes)
  useEffect(() => {
    if (activeTab !== 'conversations' || !authToken) return
    const load = async () => {
      setIsLoadingConvs(true)
      try {
        const filter: { helpful?: boolean } = {}
        if (convFilter === 'helpful') filter.helpful = true
        else if (convFilter === 'not_helpful') filter.helpful = false
        const result = await getConversations(authToken, { per_page: 50, ...filter })
        let convs = result.conversations
        if (convFilter === 'no_feedback') {
          convs = convs.filter(c => c.helpful === null)
        }
        setConversations(convs)
      } catch {
        setConversations([])
      } finally {
        setIsLoadingConvs(false)
      }
    }
    void load()
  }, [activeTab, authToken, convFilter])

  const handleSaveAgent = async (data: AgentCreateData) => {
    if (!authToken) return
    setIsSavingAgent(true)
    setGlobalError(null)
    try {
      if (editingAgent) {
        const updated = await updateAgent(authToken, editingAgent.id, data)
        setAgents(prev => prev.map(a => a.id === editingAgent.id ? updated : a))
        showSuccess(`${updated.name} updated successfully.`)
      } else {
        const created = await createAgent(authToken, data)
        setAgents(prev => [...prev, created])
        showSuccess(`${created.name} created successfully.`)
      }
      setEditingAgent(null)
      setShowCreateForm(false)
    } catch {
      setGlobalError('Failed to save agent. Please try again.')
    } finally {
      setIsSavingAgent(false)
    }
  }

  const handleToggle = async (agent: LibraryAgent) => {
    if (!authToken) return
    setIsTogglingId(agent.id)
    try {
      const updated = await toggleAgentStatus(authToken, agent.id, !agent.is_active)
      setAgents(prev => prev.map(a => a.id === agent.id ? { ...a, is_active: updated.is_active } : a))
      showSuccess(`${agent.name} ${updated.is_active ? 'enabled' : 'disabled'}.`)
    } catch {
      setGlobalError(`Failed to toggle ${agent.name}'s status.`)
    } finally {
      setIsTogglingId(null)
    }
  }

  return (
    <>
      <SectionShell
        title="Library Agents"
        description="Specialized AI personalities for your library. Fully private -- all conversations stay on your server."
        tabs={[...TABS]}
        onBack={onBack}
      >
        {(tab) => {
          // Sync SectionShell's active tab with our state for lazy-loading effects
          if (tab !== activeTabRef.current) {
            activeTabRef.current = tab
            // Defer state update to avoid setState during render
            queueMicrotask(() => setActiveTab(tab))
          }

          return (
            <div className="space-y-4">
              {globalError && (
                <div className="bg-status-danger-50 dark:bg-status-danger-900/20 text-status-danger-600 dark:text-status-danger-400 text-sm px-4 py-3 rounded-xl flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
                  {globalError}
                  <button onClick={() => setGlobalError(null)} className="ml-auto text-status-danger-400 hover:text-status-danger-600" aria-label="Dismiss error">
                    <X className="w-4 h-4" aria-hidden="true" />
                  </button>
                </div>
              )}
              {successMsg && (
                <div className="bg-status-success-50 dark:bg-status-success-900/20 text-status-success-700 dark:text-status-success-300 text-sm px-4 py-3 rounded-xl flex items-center gap-2">
                  <Check className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
                  {successMsg}
                </div>
              )}

              {tab === 'agents' && (
                <>
                  <div className="flex justify-end">
                    <button
                      onClick={() => { setEditingAgent(null); setShowCreateForm(true) }}
                      className="px-4 py-2 bg-lsc-rose text-white rounded-xl font-medium hover:bg-lsc-rose/90 transition-colors flex items-center gap-2"
                    >
                      <Plus className="w-4 h-4" aria-hidden="true" />
                      New Agent
                    </button>
                  </div>
                  {isLoadingAgents ? (
                    <div className="space-y-3">
                      {[1, 2, 3].map(i => (
                        <div key={i} className="h-28 bg-lsc-cream dark:bg-earth-800 rounded-xl motion-safe:animate-pulse" aria-hidden="true" />
                      ))}
                    </div>
                  ) : agentsError ? (
                    <div className="bg-status-danger-50 dark:bg-status-danger-900/20 text-status-danger-600 dark:text-status-danger-400 text-sm px-4 py-3 rounded-xl">
                      {agentsError}
                    </div>
                  ) : (
                    <AgentsTab
                      agents={agents}
                      onEdit={(a: LibraryAgent) => { setEditingAgent(a); setShowCreateForm(true) }}
                      onToggle={handleToggle}
                      isTogglingId={isTogglingId}
                      token={authToken || ''}
                    />
                  )}
                </>
              )}

              {tab === 'conversations' && (
                <ConversationsTab
                  conversations={conversations}
                  isLoading={isLoadingConvs}
                  onFilterChange={setConvFilter}
                  currentFilter={convFilter}
                />
              )}

              {tab === 'knowledge' && authToken && (
                <KnowledgeTab
                  token={authToken}
                  onEntryAdded={() => {
                    // Could refresh stats
                  }}
                />
              )}

              {tab === 'analytics' && (
                <AnalyticsTab stats={stats} isLoading={isLoadingStats} />
              )}
            </div>
          )
        }}
      </SectionShell>

      {(showCreateForm || editingAgent) && (
        <AgentFormModal
          agent={editingAgent}
          onSave={handleSaveAgent}
          onClose={() => { setShowCreateForm(false); setEditingAgent(null) }}
          isSaving={isSavingAgent}
        />
      )}
    </>
  )
}
