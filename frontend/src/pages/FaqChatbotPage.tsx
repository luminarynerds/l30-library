/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useRef, useEffect, useCallback } from "react"
import { useOrganizationFeatures } from "@/contexts/OrganizationFeaturesContext"
import { MessageCircle, Send, HelpCircle, ThumbsUp, ThumbsDown, Loader2, UserCircle } from "lucide-react"
import StandardPageLayout from "@/components/StandardPageLayout"
import { usePageTitle } from "@/hooks/usePageTitle"
import { askChatbot, submitChatbotFeedback, requestLibrarianHandoff } from "@/api/faq-chatbot-api"
import type { ChatbotResponse } from "@/api/faq-chatbot-api"

interface Message {
  id: string
  role: "user" | "bot"
  text: string
  conversationId?: number
  hasAnswer?: boolean
  feedbackGiven?: boolean
  sourceTitle?: string
}

const SUGGESTED_QUESTIONS = [
  "How do I get a library card?",
  "Do you have Wi-Fi?",
  "How do I place a hold?",
  "Where can I print?",
  "What digital resources do you offer?",
]

const WELCOME_MESSAGE: Message = {
  id: "welcome",
  role: "bot",
  text: "Hi! I can help answer common questions about the library. Ask me anything, or try one of the suggestions below.",
}

export default function FaqChatbotPage(): React.ReactElement {
  usePageTitle("FAQ Chat")
  const { isFeatureEnabled } = useOrganizationFeatures()

  const [messages, setMessages] = useState<Message[]>([WELCOME_MESSAGE])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [showHandoff, setShowHandoff] = useState(false)
  const [handoffMessage, setHandoffMessage] = useState("")
  const [handoffContact, setHandoffContact] = useState<"email" | "phone" | "in_person">("email")
  const [handoffSubmitting, setHandoffSubmitting] = useState(false)
  const [handoffSent, setHandoffSent] = useState(false)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const isInitialMount = useRef(true)

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" })
  }, [])

  useEffect(() => {
    if (isInitialMount.current) {
      isInitialMount.current = false
      return
    }
    scrollToBottom()
  }, [messages, scrollToBottom])

  const sendQuestion = useCallback(
    async (question: string) => {
      if (!question.trim() || isLoading) return

      const userMsg: Message = {
        id: `user-${Date.now()}`,
        role: "user",
        text: question.trim(),
      }

      setMessages((prev) => [...prev, userMsg])
      setInput("")
      setIsLoading(true)

      try {
        const response: ChatbotResponse = await askChatbot({
          question: question.trim(),
          device_type: "web",
          location: "faq-chat",
        })

        const botMsg: Message = {
          id: `bot-${Date.now()}`,
          role: "bot",
          text: response.has_answer && response.answer
            ? response.answer
            : "I don\u0027t have an answer for that yet. You can ask a librarian for help at the front desk or through our Ask a Librarian page.",
          conversationId: response.id,
          hasAnswer: response.has_answer,
          sourceTitle: response.has_answer && response.source_title ? response.source_title : undefined,
        }

        setMessages((prev) => [...prev, botMsg])
      } catch {
        const errorMsg: Message = {
          id: `error-${Date.now()}`,
          role: "bot",
          text: "Sorry, something went wrong. Please try again or visit the front desk for help.",
        }
        setMessages((prev) => [...prev, errorMsg])
      } finally {
        setIsLoading(false)
        inputRef.current?.focus()
      }
    },
    [isLoading]
  )

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    sendQuestion(input)
  }

  const handleFeedback = async (msg: Message, wasHelpful: boolean) => {
    if (!msg.conversationId || msg.feedbackGiven) return

    setMessages((prev) =>
      prev.map((m) =>
        m.id === msg.id ? { ...m, feedbackGiven: true } : m
      )
    )

    try {
      await submitChatbotFeedback(msg.conversationId, {
        was_helpful: wasHelpful,
        escalate: !wasHelpful,
      })
    } catch {
      // Feedback is best-effort
    }
  }

  const userMessageCount = messages.filter((m) => m.role === "user").length
  const showHandoffOption = userMessageCount >= 3 && !handoffSent

  const handleHandoff = async () => {
    if (!handoffMessage.trim()) return
    setHandoffSubmitting(true)
    try {
      const context = messages.slice(-6).map((m) => ({ role: m.role, text: m.text }))
      await requestLibrarianHandoff({
        message: handoffMessage.trim(),
        contact_method: handoffContact,
        conversation_context: context,
      })
      setHandoffSent(true)
      setShowHandoff(false)
      const confirmMsg: Message = {
        id: `handoff-${Date.now()}`,
        role: "bot",
        text: "Your request has been sent to our librarians. Someone will follow up within 1 business day.",
      }
      setMessages((prev) => [...prev, confirmMsg])
    } catch {
      const errorMsg: Message = {
        id: `handoff-err-${Date.now()}`,
        role: "bot",
        text: "Sorry, we could not send your request right now. Please try again or visit the front desk.",
      }
      setMessages((prev) => [...prev, errorMsg])
    } finally {
      setHandoffSubmitting(false)
    }
  }

  if (!isFeatureEnabled("faq_chatbot_enabled")) {
    return (
      <StandardPageLayout title="FAQ Chat" subtitle="This feature is not currently available." icon={MessageCircle}>
        <p className="text-earth-600 dark:text-earth-400">The FAQ chatbot is not enabled for this library.</p>
      </StandardPageLayout>
    )
  }

  return (
    <StandardPageLayout
      title="FAQ Chat"
      subtitle="Get quick answers to common library questions"
      icon={HelpCircle}
    >
      <div className="flex flex-col max-w-2xl mx-auto">
        {/* Messages */}
        <div
          className="flex flex-col gap-4 min-h-[300px] max-h-[500px] overflow-y-auto p-4 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800"
          role="log"
          aria-label="Chat messages"
          aria-live="polite"
        >
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-xl px-4 py-3 text-sm leading-relaxed ${
                  msg.role === "user"
                    ? "bg-lsc-rose text-white dark:bg-lsc-rose"
                    : "bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70"
                }`}
              >
                {msg.role === "bot" && (
                  <MessageCircle
                    className="inline-block w-4 h-4 mr-1.5 -mt-0.5 opacity-60"
                    aria-hidden="true"
                  />
                )}
                {msg.text}
                {msg.role === "bot" && msg.sourceTitle && (
                  <p className="text-xs opacity-60 mt-2">Source: {msg.sourceTitle}</p>
                )}
                {msg.role === "bot" && msg.conversationId && !msg.feedbackGiven && (
                  <div className="flex gap-2 mt-2 pt-2 border-t border-lsc-border dark:border-earth-600">
                    <span className="text-xs opacity-60 mr-auto self-center">Was this helpful?</span>
                    <button
                      type="button"
                      onClick={() => handleFeedback(msg, true)}
                      className="min-h-[44px] min-w-[44px] flex items-center justify-center rounded-lg hover:bg-earth-200 dark:hover:bg-earth-600 transition-colors"
                      aria-label="Yes, this was helpful"
                    >
                      <ThumbsUp className="w-4 h-4" aria-hidden="true" />
                    </button>
                    <button
                      type="button"
                      onClick={() => handleFeedback(msg, false)}
                      className="min-h-[44px] min-w-[44px] flex items-center justify-center rounded-lg hover:bg-earth-200 dark:hover:bg-earth-600 transition-colors"
                      aria-label="No, this was not helpful"
                    >
                      <ThumbsDown className="w-4 h-4" aria-hidden="true" />
                    </button>
                  </div>
                )}
                {msg.feedbackGiven && (
                  <p className="text-xs opacity-60 mt-2 pt-2 border-t border-lsc-border dark:border-earth-600">
                    Thanks for your feedback!
                  </p>
                )}
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-earth-100 dark:bg-earth-700 rounded-xl px-4 py-3 text-sm text-earth-600 dark:text-earth-300 flex items-center gap-2">
                <Loader2 className="w-4 h-4 motion-safe:animate-spin" aria-hidden="true" />
                Thinking...
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Suggested questions */}
        <div className="flex flex-wrap gap-2 mt-4" role="group" aria-label="Suggested questions">
          {SUGGESTED_QUESTIONS.map((q) => (
            <button
              key={q}
              type="button"
              onClick={() => sendQuestion(q)}
              disabled={isLoading}
              className="min-h-[44px] px-3 py-2 text-sm rounded-lg border border-lsc-border dark:border-earth-600 bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 hover:border-lsc-rose dark:hover:border-lsc-rose hover:text-lsc-rose dark:hover:text-lsc-rose-light transition-colors disabled:opacity-50"
            >
              {q}
            </button>
          ))}
        </div>

        {/* Librarian Handoff */}
        {showHandoffOption && !showHandoff && (
          <button
            type="button"
            onClick={() => setShowHandoff(true)}
            className="mt-4 flex items-center gap-2 text-sm text-lsc-rose hover:underline"
          >
            <UserCircle className="w-4 h-4" aria-hidden="true" />
            Not finding what you need? Talk to a librarian
          </button>
        )}

        {showHandoff && (
          <div className="mt-4 p-4 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 space-y-3">
            <h3 className="font-medium text-sm text-lsc-dark dark:text-lsc-cream">Request librarian help</h3>
            <textarea
              value={handoffMessage}
              onChange={(e) => setHandoffMessage(e.target.value)}
              placeholder="Briefly describe what you need help with..."
              rows={3}
              maxLength={1000}
              className="w-full px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-sm text-lsc-dark dark:text-lsc-cream placeholder:text-earth-400 focus:outline-none focus:ring-2 focus:ring-lsc-rose"
            />
            <div className="flex items-center gap-4">
              <label className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Preferred contact:</label>
              <select
                value={handoffContact}
                onChange={(e) => setHandoffContact(e.target.value as "email" | "phone" | "in_person")}
                className="text-sm px-2 py-1 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream"
              >
                <option value="email">Email</option>
                <option value="phone">Phone</option>
                <option value="in_person">In person</option>
              </select>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handleHandoff}
                disabled={handoffSubmitting || !handoffMessage.trim()}
                className="px-4 py-2 text-sm rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 disabled:opacity-50 transition-colors"
              >
                {handoffSubmitting ? "Sending..." : "Send to librarian"}
              </button>
              <button
                type="button"
                onClick={() => setShowHandoff(false)}
                className="px-4 py-2 text-sm rounded-lg border border-lsc-border dark:border-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-earth-100 dark:hover:bg-earth-700 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Input */}
        <form onSubmit={handleSubmit} className="flex gap-2 mt-4">
          <label htmlFor="chat-input" className="sr-only">
            Ask a question
          </label>
          <input
            ref={inputRef}
            id="chat-input"
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your question..."
            disabled={isLoading}
            maxLength={500}
            className="flex-1 min-h-[44px] px-4 rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark/70 dark:text-lsc-cream/70 placeholder:text-earth-400 dark:placeholder:text-earth-500 focus:outline-none focus:ring-2 focus:ring-lsc-rose disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="min-h-[44px] min-w-[44px] flex items-center justify-center rounded-xl bg-lsc-rose text-white hover:bg-lsc-rose/90 transition-colors disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2"
            aria-label="Send question"
          >
            <Send className="w-5 h-5" aria-hidden="true" />
          </button>
        </form>
      </div>
    </StandardPageLayout>
  )
}
