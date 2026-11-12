/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useEffect, useRef, useState } from "react"
import {
  MessageSquare,
  StickyNote,
  Send,
  Plus,
  Pencil,
  Trash2,
  X,
  Mail,
  Phone,
  Clock,
  ChevronDown,
  ChevronUp,
  Loader2,
  AlertCircle,
  CheckCircle2,
  XCircle,
} from "lucide-react"
import { useAuth } from "../../../../contexts/AuthContext"
import { useCommunication } from "../hooks/useCommunication"
import {
  getNoteCategoryLabel,
  getNoteCategoryColor,
  getNoteCategories,
  getMessageTypeLabel,
  getMessageTypeColor,
  getMessageChannelLabel,
  getMessageTypes,
  getMessageChannels,
  type NoteCategory,
  type PatronMessage,
} from "../../../../api/patron-communication-api"
import type { CommunicationSubTab } from "../types"
import { useTranslation} from '@/i18n'

interface PatronCommunicationTabProps {
  patronId: number
  // Set by the page when a recent-notes strip item is clicked; the tab will
  // switch to the notes sub-tab, scroll the note into view, and call
  // onScrollComplete to clear the pending request.
  scrollToNoteId?: number | null
  onScrollComplete?: () => void
  // Incremented by the page after a note is created from the strip so this
  // tab refetches if it's currently mounted.
  refreshNonce?: number
}

export function PatronCommunicationTab({
  patronId,
  scrollToNoteId,
  onScrollComplete,
  refreshNonce,
}: PatronCommunicationTabProps) {
  const { t } = useTranslation()
  const { token } = useAuth()
  const comm = useCommunication()
  const [expandedMessageId, setExpandedMessageId] = useState<number | null>(null)
  const [confirmDeleteNoteId, setConfirmDeleteNoteId] = useState<number | null>(null)
  const noteRefs = useRef<Map<number, HTMLDivElement | null>>(new Map())

  // Load data on mount + whenever the page signals a refresh (e.g. after
  // the recent-notes strip created a new note).
  useEffect(() => {
    if (token && patronId) {
      comm.loadCommunicationData(token, patronId)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, patronId, refreshNonce])

  // If the page asked us to jump to a specific note, switch to the notes
  // sub-tab and scroll once the note exists in the DOM.
  useEffect(() => {
    if (!scrollToNoteId) return
    comm.setCommunicationSubTab("notes")
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scrollToNoteId])

  useEffect(() => {
    if (!scrollToNoteId) return
    if (comm.communicationSubTab !== "notes") return
    if (comm.isLoadingCommunication) return
    const el = noteRefs.current.get(scrollToNoteId)
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" })
      el.classList.add("ring-2", "ring-lsc-rose")
      setTimeout(() => el.classList.remove("ring-2", "ring-lsc-rose"), 1500)
      onScrollComplete?.()
    }

  }, [scrollToNoteId, comm.communicationSubTab, comm.isLoadingCommunication, comm.patronNotes, onScrollComplete])

  if (!token) {
    return (
      <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
        <AlertCircle className="w-12 h-12 mx-auto mb-3 opacity-50" />
        <p>Authentication required</p>
      </div>
    )
  }

  if (comm.isLoadingCommunication) {
    return (
      <div className="text-center py-12 text-lsc-dark/70 dark:text-lsc-cream/70">
        <Loader2 className="w-8 h-8 mx-auto mb-3 motion-safe:animate-spin opacity-50" />
        <p>Loading communication data...</p>
      </div>
    )
  }

  const subTabs: { id: CommunicationSubTab; label: string; icon: React.ReactNode; count?: number }[] = [
    { id: "notes", label: "Staff Notes", icon: <StickyNote className="w-4 h-4" />, count: comm.patronNotes.length },
    { id: "messages", label: "Messages", icon: <MessageSquare className="w-4 h-4" />, count: comm.patronMessages.length },
    { id: "compose", label: "Compose", icon: <Send className="w-4 h-4" /> },
  ]

  return (
    <div className="space-y-4">
      {/* Sub-tab navigation */}
      <div className="flex gap-1 bg-earth-100 dark:bg-earth-800 rounded-lg p-1">
        {subTabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => comm.setCommunicationSubTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors flex-1 justify-center ${
              comm.communicationSubTab === tab.id
                ? "bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream shadow-sm"
                : "text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-dark dark:hover:text-lsc-cream"
            }`}
          >
            {tab.icon}
            {tab.label}
            {tab.count !== undefined && tab.count > 0 && (
              <span className="ml-1 text-xs bg-lsc-accent/20 text-lsc-accent dark:bg-lsc-accent/30 dark:text-lsc-accent px-1.5 py-0.5 rounded-full">
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Notes sub-tab */}
      {comm.communicationSubTab === "notes" && (
        <div className="space-y-4">
          {/* Add note button */}
          {!comm.showNoteForm && (
            <button
              onClick={() => {
                comm.setEditingNote(null)
                comm.setNoteContent("")
                comm.setNoteCategory("general")
                comm.setShowNoteForm(true)
              }}
              className="flex items-center gap-2 px-4 py-2 bg-lsc-accent text-white rounded-lg hover:bg-lsc-accent/90 transition-colors text-sm font-medium"
            >
              <Plus className="w-4 h-4" />
              Add Note
            </button>
          )}

          {/* Note form */}
          {comm.showNoteForm && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700 space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="font-medium text-lsc-dark dark:text-lsc-cream">
                  {comm.editingNote ? "Edit Note" : "New Note"}
                </h4>
                <button
                  onClick={() => {
                    comm.setShowNoteForm(false)
                    comm.setEditingNote(null)
                  }}
                  className="text-lsc-dark/70 dark:text-lsc-cream/50 hover:text-lsc-dark dark:hover:text-lsc-cream"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Category selector */}
              <div>
                <label htmlFor="patron-comm-note-category" className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                  Category
                </label>
                <select
                  id="patron-comm-note-category"
                  value={comm.noteCategory}
                  onChange={(e) => comm.setNoteCategory(e.target.value as NoteCategory)}
                  className="w-full px-3 py-2 bg-earth-50 dark:bg-earth-900 border border-lsc-border dark:border-earth-700 rounded-lg text-sm text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-accent focus:border-transparent"
                >
                  {getNoteCategories().map((cat) => (
                    <option key={cat.value} value={cat.value}>
                      {cat.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Content */}
              <label htmlFor="patron-comm-note-content" className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                Content
              </label>
              <textarea
                id="patron-comm-note-content"
                value={comm.noteContent}
                onChange={(e) => comm.setNoteContent(e.target.value)}
                placeholder={t('placeholder.patronCommunicationTab.enterNoteContent')}
                rows={4}
                className="w-full px-3 py-2 bg-earth-50 dark:bg-earth-900 border border-lsc-border dark:border-earth-700 rounded-lg text-sm text-lsc-dark dark:text-lsc-cream placeholder:text-lsc-dark/70 dark:placeholder:text-lsc-cream/40 focus:ring-2 focus:ring-lsc-accent focus:border-transparent resize-none"
              />

              {/* Actions */}
              <div className="flex gap-2 justify-end">
                <button
                  onClick={() => {
                    comm.setShowNoteForm(false)
                    comm.setEditingNote(null)
                  }}
                  className="px-4 py-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={() => comm.handleSaveNote(token, patronId)}
                  disabled={comm.isSavingNote || !comm.noteContent.trim()}
                  className="flex items-center gap-2 px-4 py-2 bg-lsc-accent text-white rounded-lg hover:bg-lsc-accent/90 transition-colors text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {comm.isSavingNote && <Loader2 className="w-3 h-3 motion-safe:animate-spin" />}
                  {comm.editingNote ? "Update" : "Save"}
                </button>
              </div>
            </div>
          )}

          {/* Notes list */}
          {comm.patronNotes.length === 0 ? (
            <div className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/50">
              <StickyNote className="w-10 h-10 mx-auto mb-2 opacity-40" />
              <p className="text-sm">{t('patronCommunicationTab.noStaffNotesForThis')}</p>
            </div>
          ) : (
            <div className="space-y-3">
              {comm.patronNotes.map((note) => (
                <div
                  key={note.id}
                  ref={(el) => { noteRefs.current.set(note.id, el) }}
                  data-note-id={note.id}
                  className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700 transition-shadow"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2 flex-wrap">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${getNoteCategoryColor(note.category)}`}
                        >
                          {getNoteCategoryLabel(note.category)}
                        </span>
                        <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50 flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {new Date(note.created_at).toLocaleString()}
                        </span>
                        {note.author_name && (
                          <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50">
                            by {note.author_name}
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-lsc-dark dark:text-lsc-cream whitespace-pre-wrap">
                        {note.content}
                      </p>
                      {note.updated_at && (
                        <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-2 italic">
                          Updated: {new Date(note.updated_at).toLocaleString()}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <button
                        onClick={() => comm.handleEditNote(note)}
                        title="Edit note"
                        className="p-1.5 text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-accent transition-colors rounded-lg hover:bg-earth-100 dark:hover:bg-earth-700"
                      >
                        <Pencil className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => setConfirmDeleteNoteId(note.id)}
                        title="Delete note"
                        className="p-1.5 text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-status-danger-500 transition-colors rounded-lg hover:bg-earth-100 dark:hover:bg-earth-700"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                  {confirmDeleteNoteId === note.id && (
                    <div className="flex items-center justify-between gap-3 mt-3 px-3 py-2 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800/40 rounded-lg">
                      <span className="text-sm text-status-danger-700 dark:text-status-danger-300">Delete this note?</span>
                      <div className="flex items-center gap-2 shrink-0">
                        <button
                          onClick={() => setConfirmDeleteNoteId(null)}
                          className="px-3 py-1 text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream transition-colors rounded-lg bg-lsc-white dark:bg-earth-700 border border-lsc-border dark:border-earth-600"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={() => {
                            comm.handleDeleteNote(token, patronId, note.id)
                            setConfirmDeleteNoteId(null)
                          }}
                          className="px-3 py-1 text-xs font-medium text-white bg-status-danger-600 hover:bg-status-danger-700 transition-colors rounded-lg"
                        >
                          Yes, delete
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Messages sub-tab */}
      {comm.communicationSubTab === "messages" && (
        <div className="space-y-3">
          {comm.patronMessages.length === 0 ? (
            <div className="text-center py-8 text-lsc-dark/70 dark:text-lsc-cream/50">
              <MessageSquare className="w-10 h-10 mx-auto mb-2 opacity-40" />
              <p className="text-sm">{t('patronCommunicationTab.noMessagesSentToThis')}</p>
            </div>
          ) : (
            comm.patronMessages.map((msg: PatronMessage) => {
              const isExpanded = expandedMessageId === msg.id
              return (
                <div
                  key={msg.id}
                  className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 overflow-hidden"
                >
                  {/* Message header - always visible */}
                  <button
                    onClick={() => setExpandedMessageId(isExpanded ? null : msg.id)}
                    className="w-full px-4 py-3 flex items-center justify-between gap-3 text-left hover:bg-earth-50 dark:hover:bg-earth-700/50 transition-colors"
                  >
                    <div className="flex items-center gap-3 min-w-0 flex-1">
                      <div className="shrink-0">
                        {msg.channel === "email" ? (
                          <Mail className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/50" />
                        ) : (
                          <Phone className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/50" />
                        )}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream truncate" title={msg.subject}>
                            {msg.subject}
                          </span>
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium shrink-0 ${getMessageTypeColor(msg.message_type)}`}
                          >
                            {getMessageTypeLabel(msg.message_type)}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50">
                            {new Date(msg.sent_at).toLocaleString()}
                          </span>
                          {msg.sender_name && (
                            <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/50">
                              by {msg.sender_name}
                            </span>
                          )}
                          <span className="shrink-0">
                            {msg.delivered ? (
                              <CheckCircle2 className="w-3.5 h-3.5 text-status-success-500" />
                            ) : (
                              <XCircle className="w-3.5 h-3.5 text-status-danger-500" />
                            )}
                          </span>
                        </div>
                      </div>
                    </div>
                    {isExpanded ? (
                      <ChevronUp className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/60 shrink-0" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/60 shrink-0" />
                    )}
                  </button>

                  {/* Expanded message body */}
                  {isExpanded && (
                    <div className="px-4 pb-4 border-t border-lsc-border dark:border-earth-700">
                      <div className="mt-3 space-y-2">
                        <div className="flex gap-4 text-xs text-lsc-dark/70 dark:text-lsc-cream/50">
                          <span>Channel: {getMessageChannelLabel(msg.channel)}</span>
                          {msg.recipient_email && <span>To: {msg.recipient_email}</span>}
                          {msg.recipient_phone && <span>To: {msg.recipient_phone}</span>}
                        </div>
                        <div className="bg-earth-50 dark:bg-earth-900 rounded-lg p-3 text-sm text-lsc-dark dark:text-lsc-cream whitespace-pre-wrap">
                          {msg.body}
                        </div>
                        {msg.delivery_error && (
                          <div className="flex items-center gap-2 text-xs text-status-danger-600 dark:text-status-danger-400">
                            <AlertCircle className="w-3.5 h-3.5" />
                            Delivery error: {msg.delivery_error}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )
            })
          )}
        </div>
      )}

      {/* Compose sub-tab */}
      {comm.communicationSubTab === "compose" && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-4 border border-lsc-border dark:border-earth-700 space-y-4">
          <h4 className="font-medium text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
            <Send className="w-4 h-4" />
            Send Message to Patron
          </h4>

          {/* Message template selector */}
          <div>
            <label htmlFor="patron-comm-template" className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              Template (optional)
            </label>
            <select
              id="patron-comm-template"
              value={comm.selectedTemplate?.id ?? ""}
              onChange={(e) => {
                if (e.target.value === "") {
                  comm.handleTemplateSelect(null)
                } else {
                  const template = comm.messageTemplates.find((t) => t.id === e.target.value)
                  if (template) comm.handleTemplateSelect(template)
                }
              }}
              className="w-full px-3 py-2 bg-earth-50 dark:bg-earth-900 border border-lsc-border dark:border-earth-700 rounded-lg text-sm text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-accent focus:border-transparent"
            >
              <option value="">-- No template (custom message) --</option>
              {comm.messageTemplates.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </div>

          {/* Channel and type row */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="patron-comm-channel" className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                Channel
              </label>
              <select
                id="patron-comm-channel"
                value={comm.messageChannel}
                onChange={(e) => comm.setMessageChannel(e.target.value as "email" | "sms")}
                className="w-full px-3 py-2 bg-earth-50 dark:bg-earth-900 border border-lsc-border dark:border-earth-700 rounded-lg text-sm text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-accent focus:border-transparent"
              >
                {getMessageChannels().map((ch) => (
                  <option key={ch.value} value={ch.value}>
                    {ch.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="patron-comm-type" className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
                Type
              </label>
              <select
                id="patron-comm-type"
                value={comm.messageType}
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                onChange={(e) => comm.setMessageType(e.target.value as any)}
                className="w-full px-3 py-2 bg-earth-50 dark:bg-earth-900 border border-lsc-border dark:border-earth-700 rounded-lg text-sm text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-accent focus:border-transparent"
              >
                {getMessageTypes().map((mt) => (
                  <option key={mt.value} value={mt.value}>
                    {mt.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Subject */}
          <div>
            <label htmlFor="patron-comm-subject" className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              Subject
            </label>
            <input
              id="patron-comm-subject"
              type="text"
              value={comm.messageSubject}
              onChange={(e) => comm.setMessageSubject(e.target.value)}
              placeholder={t('placeholder.staffPatronSegmentation.messageSubject')}
              className="w-full px-3 py-2 bg-earth-50 dark:bg-earth-900 border border-lsc-border dark:border-earth-700 rounded-lg text-sm text-lsc-dark dark:text-lsc-cream placeholder:text-lsc-dark/70 dark:placeholder:text-lsc-cream/40 focus:ring-2 focus:ring-lsc-accent focus:border-transparent"
            />
          </div>

          {/* Body */}
          <div>
            <label htmlFor="patron-comm-body" className="block text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 mb-1">
              Message Body
            </label>
            <textarea
              id="patron-comm-body"
              value={comm.messageBody}
              onChange={(e) => comm.setMessageBody(e.target.value)}
              placeholder={t('placeholder.askLibrarian.typeYourMessage')}
              rows={6}
              className="w-full px-3 py-2 bg-earth-50 dark:bg-earth-900 border border-lsc-border dark:border-earth-700 rounded-lg text-sm text-lsc-dark dark:text-lsc-cream placeholder:text-lsc-dark/70 dark:placeholder:text-lsc-cream/40 focus:ring-2 focus:ring-lsc-accent focus:border-transparent resize-none"
            />
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/60 mt-1">
              Use {"{patron_name}"} to insert the patron's name automatically.
            </p>
          </div>

          {/* Send button */}
          <div className="flex justify-end">
            <button
              onClick={() => comm.handleSendMessage(token, patronId)}
              disabled={comm.isSendingMessage || !comm.messageSubject.trim() || !comm.messageBody.trim()}
              className="flex items-center gap-2 px-5 py-2.5 bg-lsc-accent text-white rounded-lg hover:bg-lsc-accent/90 transition-colors text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {comm.isSendingMessage ? (
                <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
              Send Message
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
