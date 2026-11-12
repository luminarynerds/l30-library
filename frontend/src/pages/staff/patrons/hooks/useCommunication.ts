/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Hook for managing patron communication (notes and messages)
 */

import { useState, useCallback } from "react"
import {
  getPatronNotes,
  createPatronNote,
  updatePatronNote,
  deletePatronNote,
  getPatronMessages,
  sendPatronMessage,
  getMessageTemplates,
  PatronNote,
  PatronMessage,
  MessageTemplate,
  NoteCategory,
  MessageType,
  MessageChannel,
} from "../../../../api/patron-communication-api"
import toast from "react-hot-toast"
import { CommunicationSubTab } from "../types"

interface UseCommunicationReturn {
  communicationSubTab: CommunicationSubTab
  patronNotes: PatronNote[]
  patronMessages: PatronMessage[]
  messageTemplates: MessageTemplate[]
  isLoadingCommunication: boolean
  isSendingMessage: boolean
  isSavingNote: boolean
  showNoteForm: boolean
  editingNote: PatronNote | null
  noteContent: string
  noteCategory: NoteCategory
  selectedTemplate: MessageTemplate | null
  messageSubject: string
  messageBody: string
  messageChannel: MessageChannel
  messageType: MessageType
  viewingMessage: PatronMessage | null
  setCommunicationSubTab: (tab: CommunicationSubTab) => void
  setShowNoteForm: (show: boolean) => void
  setEditingNote: (note: PatronNote | null) => void
  setNoteContent: (content: string) => void
  setNoteCategory: (category: NoteCategory) => void
  setSelectedTemplate: (template: MessageTemplate | null) => void
  setMessageSubject: (subject: string) => void
  setMessageBody: (body: string) => void
  setMessageChannel: (channel: MessageChannel) => void
  setMessageType: (type: MessageType) => void
  setViewingMessage: (message: PatronMessage | null) => void
  loadCommunicationData: (token: string, patronId: number) => Promise<void>
  handleSaveNote: (token: string, patronId: number) => Promise<void>
  handleDeleteNote: (token: string, patronId: number, noteId: number) => Promise<void>
  handleEditNote: (note: PatronNote) => void
  handleTemplateSelect: (template: MessageTemplate | null) => void
  handleSendMessage: (token: string, patronId: number) => Promise<void>
}

export function useCommunication(): UseCommunicationReturn {
  const [communicationSubTab, setCommunicationSubTab] = useState<CommunicationSubTab>("notes")
  const [patronNotes, setPatronNotes] = useState<PatronNote[]>([])
  const [patronMessages, setPatronMessages] = useState<PatronMessage[]>([])
  const [messageTemplates, setMessageTemplates] = useState<MessageTemplate[]>([])
  const [isLoadingCommunication, setIsLoadingCommunication] = useState(false)
  const [isSendingMessage, setIsSendingMessage] = useState(false)
  const [isSavingNote, setIsSavingNote] = useState(false)
  const [showNoteForm, setShowNoteForm] = useState(false)
  const [editingNote, setEditingNote] = useState<PatronNote | null>(null)
  const [noteContent, setNoteContent] = useState("")
  const [noteCategory, setNoteCategory] = useState<NoteCategory>("general")
  const [selectedTemplate, setSelectedTemplate] = useState<MessageTemplate | null>(null)
  const [messageSubject, setMessageSubject] = useState("")
  const [messageBody, setMessageBody] = useState("")
  const [messageChannel, setMessageChannel] = useState<MessageChannel>("email")
  const [messageType, setMessageType] = useState<MessageType>("custom")
  const [viewingMessage, setViewingMessage] = useState<PatronMessage | null>(null)

  const loadCommunicationData = useCallback(
    async (token: string, patronId: number) => {
      setIsLoadingCommunication(true)
      try {
        const [notesData, messagesData, templatesData] = await Promise.all([
          getPatronNotes(token, patronId),
          getPatronMessages(token, patronId),
          getMessageTemplates(token),
        ])
        setPatronNotes(notesData.notes)
        setPatronMessages(messagesData.messages)
        setMessageTemplates(templatesData)
      } catch (_err) {
        toast.error("Failed to load communication data")
      } finally {
        setIsLoadingCommunication(false)
      }
    },
    []
  )

  const handleSaveNote = useCallback(
    async (token: string, patronId: number) => {
      if (!noteContent.trim()) {
        toast.error("Note content cannot be empty")
        return
      }
      setIsSavingNote(true)
      try {
        if (editingNote) {
          await updatePatronNote(token, patronId, editingNote.id, {
            content: noteContent,
            category: noteCategory,
          })
          toast.success("Note updated")
        } else {
          await createPatronNote(token, patronId, {
            content: noteContent,
            category: noteCategory,
          })
          toast.success("Note created")
        }
        setNoteContent("")
        setNoteCategory("general")
        setShowNoteForm(false)
        setEditingNote(null)
        await loadCommunicationData(token, patronId)
      } catch (_err) {
        toast.error(_err instanceof Error ? _err.message : "Failed to save note")
      } finally {
        setIsSavingNote(false)
      }
    },
    [noteContent, noteCategory, editingNote, loadCommunicationData]
  )

  const handleDeleteNote = useCallback(
    async (token: string, patronId: number, noteId: number) => {
      setIsSavingNote(true)
      try {
        await deletePatronNote(token, patronId, noteId)
        toast.success("Note deleted")
        setPatronNotes((notes) => notes.filter((n) => n.id !== noteId))
      } catch (_err) {
        toast.error("Failed to delete note")
      } finally {
        setIsSavingNote(false)
      }
    },
    []
  )

  const handleEditNote = (note: PatronNote) => {
    setEditingNote(note)
    setNoteContent(note.content)
    setNoteCategory(note.category)
    setShowNoteForm(true)
  }

  const handleTemplateSelect = (template: MessageTemplate | null) => {
    setSelectedTemplate(template)
    if (template) {
      setMessageSubject(template.subject)
      setMessageBody(template.body)
    }
  }

  const handleSendMessage = useCallback(
    async (token: string, patronId: number) => {
      if (!messageSubject.trim() || !messageBody.trim()) {
        toast.error("Subject and message body are required")
        return
      }
      setIsSendingMessage(true)
      try {
        await sendPatronMessage(token, patronId, {
          subject: messageSubject,
          body: messageBody,
          channel: messageChannel,
          message_type: messageType,
        })
        toast.success("Message sent successfully")
        setMessageSubject("")
        setMessageBody("")
        setSelectedTemplate(null)
        setMessageType("custom")
        await loadCommunicationData(token, patronId)
      } catch (_err) {
        toast.error(_err instanceof Error ? _err.message : "Failed to send message")
      } finally {
        setIsSendingMessage(false)
      }
    },
    [messageSubject, messageBody, messageChannel, messageType, loadCommunicationData]
  )

  return {
    communicationSubTab,
    patronNotes,
    patronMessages,
    messageTemplates,
    isLoadingCommunication,
    isSendingMessage,
    isSavingNote,
    showNoteForm,
    editingNote,
    noteContent,
    noteCategory,
    selectedTemplate,
    messageSubject,
    messageBody,
    messageChannel,
    messageType,
    viewingMessage,
    setCommunicationSubTab,
    setShowNoteForm,
    setEditingNote,
    setNoteContent,
    setNoteCategory,
    setSelectedTemplate,
    setMessageSubject,
    setMessageBody,
    setMessageChannel,
    setMessageType,
    setViewingMessage,
    loadCommunicationData,
    handleSaveNote,
    handleDeleteNote,
    handleEditNote,
    handleTemplateSelect,
    handleSendMessage,
  }
}
