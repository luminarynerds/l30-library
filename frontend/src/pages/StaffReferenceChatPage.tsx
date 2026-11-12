/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useCallback, useEffect, useState } from "react"
import { MessageSquare, Send, RefreshCw, Clock, User, CheckCircle } from "lucide-react"
import toast from "react-hot-toast"
import { useAuth } from "../contexts/AuthContext"
import { usePageTitle } from "@/hooks/usePageTitle"
import { getUserMessage } from "../lib/api-client"
import {
  getChatSessions,
  getSessionMessages,
  staffReplyToSession,
  type ChatSessionSummary,
  type SessionDetail,
} from "../api/library-agents-api"
import { AdminShell } from "../components/shells/AdminShell"
import { t } from '@/i18n'

const QUESTION_TYPES = [
  { value: "directional", label: "Directional" },
  { value: "ready_reference", label: "Ready Reference" },
  { value: "research", label: "Research" },
  { value: "readers_advisory", label: "Reader's Advisory" },
  { value: "technical", label: "Technical" },
]

export default function StaffReferenceChatPage() {
  usePageTitle("Reference Chat")
  const { token } = useAuth()

  const [sessions, setSessions] = useState<ChatSessionSummary[]>([])
  const [selectedSession, setSelectedSession] = useState<SessionDetail | null>(null)
  const [isLoadingSessions, setIsLoadingSessions] = useState(true)
  const [isLoadingMessages, setIsLoadingMessages] = useState(false)
  const [isSending, setIsSending] = useState(false)

  // Reply form
  const [replyMessage, setReplyMessage] = useState("")
  const [questionType, setQuestionType] = useState("ready_reference")
  const [subjectArea, setSubjectArea] = useState("")

  const fetchSessions = useCallback(async () => {
    if (!token) return
    setIsLoadingSessions(true)
    try {
      const data = await getChatSessions(token)
      setSessions(data)
    } catch (err) {
      toast.error(getUserMessage(err, "Failed to load chat sessions"))
    } finally {
      setIsLoadingSessions(false)
    }
  }, [token])

  useEffect(() => {
    fetchSessions()
  }, [fetchSessions])

  const openSession = async (sessionId: string) => {
    if (!token) return
    setIsLoadingMessages(true)
    try {
      const data = await getSessionMessages(token, sessionId)
      setSelectedSession(data)
      setReplyMessage("")
      setSubjectArea("")
    } catch (err) {
      toast.error(getUserMessage(err, "Failed to load messages"))
    } finally {
      setIsLoadingMessages(false)
    }
  }

  const sendReply = async () => {
    if (!token || !selectedSession || !replyMessage.trim()) return
    setIsSending(true)
    try {
      const result = await staffReplyToSession(token, selectedSession.session_id, {
        message: replyMessage.trim(),
        question_type: questionType,
        subject_area: subjectArea || undefined,
      })
      toast.success(t('toast.staffReferenceChat.replySentLoggedAsReference', { referencequestionid: result.reference_question_id }))
      setReplyMessage("")
      // Refresh the session messages
      await openSession(selectedSession.session_id)
      // Refresh sessions list
      await fetchSessions()
    } catch (err) {
      toast.error(getUserMessage(err, "Failed to send reply"))
    } finally {
      setIsSending(false)
    }
  }

  return (

    <AdminShell title="Reference Chat">    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <MessageSquare className="h-8 w-8 text-lsc-rose" />
          <div>
            <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              Reference Chat
            </h1>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/60">
              Answer patron chat questions and log them for reference statistics
            </p>
          </div>
        </div>
        <button
          onClick={fetchSessions}
          disabled={isLoadingSessions}
          className="flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose-dark text-white rounded-lg transition disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${isLoadingSessions ? "motion-safe:animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Sessions List */}
        <div className="lg:col-span-1 bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 overflow-hidden">
          <div className="p-4 border-b border-lsc-border dark:border-earth-700">
            <h2 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
              Chat Sessions ({sessions.length})
            </h2>
          </div>
          <div className="max-h-[600px] overflow-y-auto divide-y divide-lsc-border dark:divide-earth-700">
            {isLoadingSessions ? (
              <div className="p-4 space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-16 bg-lsc-border dark:bg-earth-700 rounded motion-safe:animate-pulse" />
                ))}
              </div>
            ) : sessions.length === 0 ? (
              <div className="p-6 text-center text-lsc-dark/70 dark:text-lsc-cream/60">
                No active chat sessions
              </div>
            ) : (
              sessions.map((session) => (
                <button
                  key={session.session_id}
                  onClick={() => openSession(session.session_id)}
                  className={`w-full text-left p-4 hover:bg-lsc-border/30 dark:hover:bg-earth-700/50 transition ${
                    selectedSession?.session_id === session.session_id
                      ? "bg-lsc-rose/10 dark:bg-lsc-rose/20 border-l-4 border-l-lsc-rose"
                      : ""
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-medium text-sm text-lsc-dark dark:text-lsc-cream truncate" title={session.agent_name}>
                          {session.agent_name}
                        </span>
                        {session.has_staff_reply && (
                          <CheckCircle className="h-3.5 w-3.5 text-status-success-500 shrink-0" />
                        )}
                      </div>
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 line-clamp-2" title={session.last_message}>
                        {session.last_message}
                      </p>
                    </div>
                    <div className="text-right shrink-0">
                      <div className="flex items-center gap-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/50">
                        <Clock className="h-3 w-3" />
                        {new Date(session.last_message_at).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </div>
                      <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50">
                        {session.message_count} msg{session.message_count !== 1 ? "s" : ""}
                      </span>
                    </div>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Chat Detail + Reply */}
        <div className="lg:col-span-2 bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 overflow-hidden flex flex-col">
          {selectedSession ? (
            <>
              {/* Chat Header */}
              <div className="p-4 border-b border-lsc-border dark:border-earth-700 bg-lsc-rose/5 dark:bg-lsc-rose/10">
                <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                  {selectedSession.agent_name} - Session
                </h3>
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 font-mono">
                  {selectedSession.session_id}
                </p>
              </div>

              {/* Messages */}
              <div className="flex-1 max-h-[350px] overflow-y-auto p-4 space-y-4">
                {isLoadingMessages ? (
                  <div className="flex justify-center py-8">
                    <RefreshCw className="h-6 w-6 motion-safe:animate-spin text-lsc-rose" />
                  </div>
                ) : (
                  selectedSession.messages.map((msg) => (
                    <div key={msg.id} className="space-y-2">
                      {/* Patron message */}
                      {!msg.is_staff_reply && (
                        <div className="flex justify-start">
                          <div className="max-w-[80%]">
                            <div className="flex items-center gap-1 mb-1">
                              <User className="h-3 w-3 text-status-info-500" />
                              <span className="text-xs font-medium text-status-info-600 dark:text-status-info-400">
                                Patron
                              </span>
                              <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 ml-2">
                                {new Date(msg.created_at).toLocaleString()}
                              </span>
                            </div>
                            <div className="bg-status-info-50 dark:bg-status-info-900/20 text-lsc-dark dark:text-lsc-cream px-4 py-2 rounded-lg rounded-bl-none">
                              {msg.user_message}
                            </div>
                          </div>
                        </div>
                      )}
                      {/* Agent/Staff response */}
                      <div className="flex justify-end">
                        <div className="max-w-[80%]">
                          <div className="flex items-center justify-end gap-1 mb-1">
                            <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mr-2">
                              {new Date(msg.created_at).toLocaleString()}
                            </span>
                            <span className={`text-xs font-medium ${msg.is_staff_reply ? "text-status-success-600 dark:text-status-success-400" : "text-lsc-rose"}`}>
                              {msg.is_staff_reply ? "Staff" : msg.agent_name}
                            </span>
                            {msg.is_staff_reply && <CheckCircle className="h-3 w-3 text-status-success-500" />}
                          </div>
                          <div className={`px-4 py-2 rounded-lg rounded-br-none ${
                            msg.is_staff_reply
                              ? "bg-status-success-50 dark:bg-status-success-900/20 text-lsc-dark dark:text-lsc-cream"
                              : "bg-lsc-rose/10 dark:bg-lsc-rose/20 text-lsc-dark dark:text-lsc-cream"
                          }`}>
                            {msg.agent_response}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>

              {/* Reply Form */}
              <div className="border-t border-lsc-border dark:border-earth-700 p-4 space-y-3">
                <div className="flex gap-3">
                  <label htmlFor="question-type" className="sr-only">{t('label.staffReferenceChat.questionType', 'Question type')}</label>
                  <select
                    id="question-type"
                    value={questionType}
                    onChange={(e) => setQuestionType(e.target.value)}
                    className="px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg text-sm bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  >
                    {QUESTION_TYPES.map((qt) => (
                      <option key={qt.value} value={qt.value}>
                        {qt.label}
                      </option>
                    ))}
                  </select>
                  <input
                    type="text"
                    value={subjectArea}
                    onChange={(e) => setSubjectArea(e.target.value)}
                    placeholder={t('placeholder.staffReferenceChat.subjectAreaOptional')}
                    className="flex-1 px-3 py-2 border border-lsc-border dark:border-earth-600 rounded-lg text-sm bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream"
                  />
                </div>
                <div className="flex gap-2">
                  <textarea
                    value={replyMessage}
                    onChange={(e) => setReplyMessage(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault()
                        sendReply()
                      }
                    }}
                    placeholder={t('placeholder.staffReferenceChat.typeYourReplyTo')}
                    rows={2}
                    className="flex-1 px-4 py-2 border border-lsc-border dark:border-earth-600 rounded-lg resize-none bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:outline-none focus:border-lsc-rose"
                    disabled={isSending}
                  />
                  <button
                    onClick={sendReply}
                    disabled={isSending || !replyMessage.trim()}
                    className="self-end bg-lsc-rose hover:bg-lsc-rose-dark disabled:opacity-50 text-white p-3 rounded-lg transition"
                  >
                    <Send className="h-5 w-5" />
                  </button>
                </div>
                <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50">
                  Your reply will be sent to the patron and automatically logged as a reference question for IMLS/PLA statistics.
                </p>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center p-8 text-center">
              <div>
                <MessageSquare className="h-12 w-12 text-lsc-dark/20 dark:text-lsc-cream/20 mx-auto mb-3" />
                <p className="text-lsc-dark/70 dark:text-lsc-cream/60">
                  Select a chat session to view the conversation and reply
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  </AdminShell>
  )
}
