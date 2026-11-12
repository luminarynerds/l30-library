/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from "@/lib/api-client"

export interface ChatbotQuestion {
  question: string
  device_type?: string
  location?: string
}

export interface ChatbotResponse {
  id: number
  question: string
  answer: string | null
  category: string | null
  confidence_score: number
  faq_id: number | null
  has_answer: boolean
  source_title: string | null
  source_id: number | null
}

export interface ChatbotFeedback {
  was_helpful: boolean
  escalate?: boolean
}

export async function askChatbot(data: ChatbotQuestion): Promise<ChatbotResponse> {
  return fetchApi<ChatbotResponse>("/faq-chatbot/chat", {
    method: "POST",
    body: data,
  })
}

export async function submitChatbotFeedback(
  conversationId: number,
  feedback: ChatbotFeedback
): Promise<void> {
  return fetchApi<void>(`/faq-chatbot/chat/${conversationId}/feedback`, {
    method: "POST",
    body: feedback,
    skipJsonParse: true,
  })
}

export interface TrendingQuestion {
  question: string
  ask_count: number
}

export async function getTrendingQuestions(limit = 5): Promise<TrendingQuestion[]> {
  return fetchApi<TrendingQuestion[]>(`/faq-chatbot/trending?days=7&limit=${limit}`)
}

export interface SeasonalFAQ {
  id: number
  knowledge_entry_id: number
  season: string
  start_date: string
  end_date: string
  seasonal_note: string | null
  is_active: boolean
}

export async function getSeasonalFAQs(): Promise<SeasonalFAQ[]> {
  return fetchApi<SeasonalFAQ[]>("/faq-chatbot/seasonal")
}

export interface LibrarianHandoffRequest {
  message: string
  contact_method: "email" | "phone" | "in_person"
  patron_name?: string
  conversation_context: Array<{ role: string; text: string }>
}

export interface LibrarianHandoffResponse {
  success: boolean
  message: string
  estimated_wait: string
}

export async function requestLibrarianHandoff(
  data: LibrarianHandoffRequest
): Promise<LibrarianHandoffResponse> {
  return fetchApi<LibrarianHandoffResponse>("/faq-chatbot/handoff", {
    method: "POST",
    body: data,
  })
}
