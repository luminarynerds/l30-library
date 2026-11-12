/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'

// ==================== Library Agent Types ====================

export interface LibraryAgent {
  id: number
  name: string
  nickname: string | null
  role: string
  department: string
  bio: string
  personality: string
  tone: string | null
  specialties: string[]
  can_help_with: string[]
  avatar_color: string | null
  initials: string | null
  emoji: string | null
  greeting_message: string | null
  is_active: boolean
  email: string | null
}

export interface AgentCreateData {
  name: string
  nickname?: string | null
  role: string
  department: string
  bio: string
  personality?: string
  tone?: string | null
  specialties?: string[]
  can_help_with?: string[]
  avatar_color?: string | null
  initials?: string | null
  emoji?: string | null
  greeting_message?: string | null
}

export type AgentUpdateData = AgentCreateData

export interface AgentMessageRequest {
  message: string
  session_id?: string | null
  context?: Record<string, unknown> | null
}

export interface AgentMessageResponse {
  agent_name: string
  agent_role: string
  response: string
  session_id: string
  conversation_id: number
  detected_intent: string | null
  suggested_followups: string[] | null
  mode: 'rule_based' | 'llm'
}

export interface AgentFeedbackRequest {
  conversation_id: number
  helpful: boolean
  note?: string | null
}

export interface KnowledgeBaseEntry {
  id: number
  category: string
  question: string
  answer: string
  tags: string[]
  department: string | null
  is_frequently_asked: boolean
}

export interface KnowledgeBaseCreateData {
  category: string
  question: string
  answer: string
  tags?: string[]
  department?: string | null
}

export type KnowledgeBaseUpdateData = KnowledgeBaseCreateData

// Conversation types for admin viewing
export interface AgentConversation {
  id: number
  agent_id: number
  agent_name?: string
  user_id: number | null
  user_email?: string | null
  session_id: string
  user_message: string
  agent_response: string
  detected_intent: string | null
  helpful: boolean | null
  feedback_note: string | null
  response_time_ms: number | null
  created_at: string
}

export interface ConversationListResponse {
  conversations: AgentConversation[]
  total: number
  page: number
  per_page: number
}

// Analytics types
export interface AgentAnalytics {
  agent_id: number
  agent_name: string
  total_conversations: number
  helpful_count: number
  not_helpful_count: number
  no_feedback_count: number
  helpfulness_rate: number
  avg_response_time_ms: number
  top_intents: { intent: string; count: number }[]
  conversations_by_day: { date: string; count: number }[]
}

export interface AgentStats {
  total_agents: number
  active_agents: number
  total_conversations: number
  total_feedback: number
  avg_helpfulness_rate: number
  knowledge_base_entries: number
}

// ==================== Agent CRUD Functions ====================

export async function getAgents(
  token?: string,
  options?: { department?: string; is_active?: boolean }
): Promise<LibraryAgent[]> {
  try {
    const params = new URLSearchParams()
    if (options?.department) params.set('department', options.department)
    if (options?.is_active !== undefined) params.set('is_active', String(options.is_active))
    const queryString = params.toString() ? `?${params.toString()}` : ''
    return await fetchApi<LibraryAgent[]>(`/library-agents/${queryString}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch agents')
    }
    throw error
  }
}

export async function getAgent(agentId: number, token?: string): Promise<LibraryAgent> {
  try {
    return await fetchApi<LibraryAgent>(`/library-agents/${agentId}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch agent')
    }
    throw error
  }
}

export async function getAgentByName(agentName: string, token?: string): Promise<LibraryAgent> {
  try {
    return await fetchApi<LibraryAgent>(`/library-agents/name/${encodeURIComponent(agentName)}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch agent')
    }
    throw error
  }
}

export async function createAgent(token: string, data: AgentCreateData): Promise<LibraryAgent> {
  try {
    return await fetchApi<LibraryAgent>('/library-agents/', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create agent')
    }
    throw error
  }
}

export async function updateAgent(
  token: string,
  agentId: number,
  data: AgentUpdateData
): Promise<LibraryAgent> {
  try {
    return await fetchApi<LibraryAgent>(`/library-agents/${agentId}`, {
      method: 'PUT',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update agent')
    }
    throw error
  }
}

export async function toggleAgentStatus(
  token: string,
  agentId: number,
  isActive: boolean
): Promise<LibraryAgent> {
  try {
    // Get current agent data, then update with new status
    const agent = await getAgent(agentId, token)
    return await fetchApi<LibraryAgent>(`/library-agents/${agentId}`, {
      method: 'PUT',
      token,
      body: {
        name: agent.name,
        role: agent.role,
        department: agent.department,
        bio: agent.bio,
        personality: agent.personality,
        tone: agent.tone,
        specialties: agent.specialties,
        can_help_with: agent.can_help_with,
        avatar_color: agent.avatar_color,
        initials: agent.initials,
        emoji: agent.emoji,
        greeting_message: agent.greeting_message,
        is_active: isActive,
      },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to toggle agent status')
    }
    throw error
  }
}

// ==================== Chat Functions ====================

export async function chatWithAgent(
  agentId: number,
  message: string,
  sessionId?: string,
  context?: Record<string, unknown>,
  token?: string,
  followupEmail?: string,
): Promise<AgentMessageResponse> {
  try {
    return await fetchApi<AgentMessageResponse>(`/library-agents/${agentId}/chat`, {
      method: 'POST',
      timeoutMs: 120_000,
      ...(token ? { token } : {}),
      body: {
        message,
        ...(sessionId ? { session_id: sessionId } : {}),
        ...(context ? { context } : {}),
        ...(followupEmail ? { followup_email: followupEmail } : {}),
      },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to send message')
    }
    throw error
  }
}

export async function submitAgentFeedback(
  conversationId: number,
  helpful: boolean,
  note?: string
): Promise<{ message: string }> {
  try {
    return await fetchApi<{ message: string }>('/library-agents/feedback', {
      method: 'POST',
      body: {
        conversation_id: conversationId,
        helpful,
        note,
      },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to submit feedback')
    }
    throw error
  }
}

// ==================== Knowledge Base Functions ====================

export async function searchKnowledgeBase(
  query: string,
  options?: {
    category?: string
    department?: string
    limit?: number
  },
  token?: string
): Promise<KnowledgeBaseEntry[]> {
  try {
    const params = new URLSearchParams()
    params.set('query', query)
    if (options?.category) params.set('category', options.category)
    if (options?.department) params.set('department', options.department)
    if (options?.limit) params.set('limit', String(options.limit))
    return await fetchApi<KnowledgeBaseEntry[]>(`/library-agents/knowledge/search?${params}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to search knowledge base')
    }
    throw error
  }
}

export async function createKnowledgeBaseEntry(
  token: string,
  data: KnowledgeBaseCreateData
): Promise<KnowledgeBaseEntry> {
  try {
    return await fetchApi<KnowledgeBaseEntry>('/library-agents/knowledge', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create knowledge base entry')
    }
    throw error
  }
}

export async function updateKnowledgeBaseEntry(
  token: string,
  entryId: number,
  data: KnowledgeBaseUpdateData
): Promise<KnowledgeBaseEntry> {
  try {
    return await fetchApi<KnowledgeBaseEntry>(`/library-agents/knowledge/${entryId}`, {
      method: 'PUT',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update knowledge base entry')
    }
    throw error
  }
}

export async function deleteKnowledgeBaseEntry(token: string, entryId: number): Promise<void> {
  try {
    await fetchApi<void>(`/library-agents/knowledge/${entryId}`, {
      method: 'DELETE',
      token,
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete knowledge base entry')
    }
    throw error
  }
}

// ==================== Admin Analytics Functions ====================

export async function getAgentStats(token: string): Promise<AgentStats> {
  try {
    return await fetchApi<AgentStats>('/library-agents/admin/stats', { token })
  } catch (error: unknown) {
    // Return default stats if endpoint doesn't exist yet
    if (isApiError(error) && error.status === 404) {
      const agents = await getAgents(token)
      return {
        total_agents: agents.length,
        active_agents: agents.filter(a => a.is_active).length,
        total_conversations: 0,
        total_feedback: 0,
        avg_helpfulness_rate: 0,
        knowledge_base_entries: 0,
      }
    }
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch agent stats')
    }
    throw error
  }
}

export async function getAgentAnalytics(
  token: string,
  agentId: number,
  options?: { days?: number }
): Promise<AgentAnalytics> {
  try {
    const params = new URLSearchParams()
    if (options?.days) params.set('days', String(options.days))
    const queryString = params.toString() ? `?${params.toString()}` : ''
    return await fetchApi<AgentAnalytics>(`/library-agents/admin/${agentId}/analytics${queryString}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch agent analytics')
    }
    throw error
  }
}

export async function getConversations(
  token: string,
  options?: {
    agent_id?: number
    user_id?: number
    page?: number
    per_page?: number
    helpful?: boolean
    start_date?: string
    end_date?: string
  }
): Promise<ConversationListResponse> {
  try {
    const params = new URLSearchParams()
    if (options?.agent_id) params.set('agent_id', String(options.agent_id))
    if (options?.user_id) params.set('user_id', String(options.user_id))
    if (options?.page) params.set('page', String(options.page))
    if (options?.per_page) params.set('per_page', String(options.per_page))
    if (options?.helpful !== undefined) params.set('helpful', String(options.helpful))
    if (options?.start_date) params.set('start_date', options.start_date)
    if (options?.end_date) params.set('end_date', options.end_date)
    const queryString = params.toString() ? `?${params.toString()}` : ''
    return await fetchApi<ConversationListResponse>(`/library-agents/admin/conversations${queryString}`, { token })
  } catch (error: unknown) {
    // Return empty list if endpoint doesn't exist yet
    if (isApiError(error) && error.status === 404) {
      return { conversations: [], total: 0, page: 1, per_page: 20 }
    }
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch conversations')
    }
    throw error
  }
}

export async function getConversation(
  token: string,
  conversationId: number
): Promise<AgentConversation> {
  try {
    return await fetchApi<AgentConversation>(`/library-agents/admin/conversations/${conversationId}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch conversation')
    }
    throw error
  }
}

// ==================== Staff Reference Chat Types ====================

export interface ChatSessionSummary {
  session_id: string
  agent_id: number
  agent_name: string
  patron_user_id: number | null
  last_message: string
  last_message_at: string
  message_count: number
  has_staff_reply: boolean
  unread_staff_reply_count: number
}

export interface SessionMessage {
  id: number
  user_message: string
  agent_response: string
  agent_name: string
  detected_intent: string | null
  created_at: string
  is_staff_reply: boolean
  staff_id: number | null
}

export interface SessionDetail {
  session_id: string
  agent_id: number
  agent_name: string
  messages: SessionMessage[]
}

export interface StaffReplyRequest {
  message: string
  question_type?: string | undefined
  subject_area?: string | undefined
  branch_location?: string | undefined
}

export interface StaffReplyResponse {
  conversation_id: number
  session_id: string
  staff_message: string
  reference_question_id: number
  agent_name: string
}

// ==================== Staff Reference Chat Functions ====================

export async function getChatSessions(
  token: string,
  options?: { limit?: number }
): Promise<ChatSessionSummary[]> {
  try {
    const params = new URLSearchParams()
    if (options?.limit) params.set('limit', String(options.limit))
    const queryString = params.toString() ? `?${params.toString()}` : ''
    return await fetchApi<ChatSessionSummary[]>(`/library-agents/chat-sessions${queryString}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch chat sessions')
    }
    throw error
  }
}

export async function getSessionMessages(
  token: string,
  sessionId: string
): Promise<SessionDetail> {
  try {
    return await fetchApi<SessionDetail>(`/library-agents/chat-sessions/${encodeURIComponent(sessionId)}/messages`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch session messages')
    }
    throw error
  }
}

export async function staffReplyToSession(
  token: string,
  sessionId: string,
  data: StaffReplyRequest
): Promise<StaffReplyResponse> {
  try {
    return await fetchApi<StaffReplyResponse>(`/library-agents/chat-sessions/${encodeURIComponent(sessionId)}/staff-reply`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to send staff reply')
    }
    throw error
  }
}


// ==================== Patron Chat Session Types ====================

export interface ChatSessionMessage {
  conversation_id: number
  user_message: string
  agent_response: string
  is_staff_reply: boolean
  staff_id?: number | null
  staff_name?: string | null
  created_at: string
}

export interface ChatSessionDetail {
  session_id: string
  agent_id: number
  agent_name: string
  messages: ChatSessionMessage[]
}

// Patron-facing session list entry — same shape as staff ChatSessionSummary; patron_user_id absent/null for non-staff callers
export type MyChatSession = ChatSessionSummary

// ==================== Patron Chat Session Functions ====================

export async function getMyChatSessions(token: string): Promise<MyChatSession[]> {
  try {
    return await fetchApi<MyChatSession[]>('/library-agents/chat-sessions', { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch chat sessions')
    }
    throw error
  }
}

export async function getChatSessionMessages(
  sessionId: string,
  token: string,
): Promise<ChatSessionDetail> {
  try {
    return await fetchApi<ChatSessionDetail>(
      `/library-agents/chat-sessions/${encodeURIComponent(sessionId)}/messages`,
      { token },
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch session messages')
    }
    throw error
  }
}

// ==================== Utility Constants ====================

export const AGENT_DEPARTMENTS = [
  'Administration',
  'Adult Services',
  'Children\'s Services',
  'Teen Services',
  'Technology',
  'Reference',
  'Circulation',
  'Community Outreach',
  'Makerspace',
  'Special Collections',
] as const

export const AGENT_PERSONALITIES = [
  { value: 'friendly', label: 'Friendly', description: 'Warm and approachable' },
  { value: 'professional', label: 'Professional', description: 'Formal and efficient' },
  { value: 'enthusiastic', label: 'Enthusiastic', description: 'Energetic and excited' },
  { value: 'calm', label: 'Calm', description: 'Relaxed and reassuring' },
  { value: 'witty', label: 'Witty', description: 'Clever with a sense of humor' },
  { value: 'quirky', label: 'Quirky', description: 'Unique and playful' },
] as const

export const KNOWLEDGE_CATEGORIES = [
  'Hours & Locations',
  'Library Cards',
  'Borrowing & Returns',
  'Programs & Events',
  'Digital Resources',
  'Research Help',
  'Makerspace',
  'Accessibility',
  'Policies',
  'General Information',
] as const
