/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useCallback } from "react"
import {
  listTerminals,
  createTerminal,
  updateTerminal,
  deleteTerminal,
  SIP2Terminal,
} from "@/api/sip2-api"
import { useTranslation } from "@/i18n"
import { clean } from "@/lib/utils"
import toast from "react-hot-toast"
import {
  PAGE_SIZE,
  EMPTY_TERMINAL_FORM,
  terminalToFormData,
  TerminalFormData,
  ModalType,
} from "../types"

export function useSIP2Terminals(token: string | null, onMutate: () => void) {
  const { t } = useTranslation()

  // List state
  const [terminals, setTerminals] = useState<SIP2Terminal[]>([])
  const [terminalSearch, setTerminalSearch] = useState("")
  const [terminalFilter, setTerminalFilter] = useState<"all" | "active" | "inactive">("all")
  const [terminalPage, setTerminalPage] = useState(1)
  const [terminalTotal, setTerminalTotal] = useState(0)
  const [isLoading, setIsLoading] = useState(true)

  // Modal state
  const [modalType, setModalType] = useState<ModalType>(null)
  const [isEditing, setIsEditing] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [selectedTerminal, setSelectedTerminal] = useState<SIP2Terminal | null>(null)

  // Form state
  const [terminalForm, setTerminalForm] = useState<TerminalFormData>(EMPTY_TERMINAL_FORM)

  // Delete state
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [deletingTerminal, setDeletingTerminal] = useState<SIP2Terminal | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)

  const terminalTotalPages = Math.ceil(terminalTotal / PAGE_SIZE)

  const fetchTerminals = useCallback(async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const isActive = terminalFilter === "all" ? undefined : terminalFilter === "active"
      const response = await listTerminals(token, clean({
        page: terminalPage,
        limit: PAGE_SIZE,
        ...(terminalSearch ? { search: terminalSearch } : {}),
        is_active: isActive,
      }))
      setTerminals(response.terminals)
      setTerminalTotal(response.total)
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : t('toast.staffSIP2.failedToLoadTerminals'))
    } finally {
      setIsLoading(false)
    }
  }, [token, terminalPage, terminalSearch, terminalFilter, t])

  const resetTerminalForm = () => {
    setTerminalForm(EMPTY_TERMINAL_FORM)
    setIsEditing(false)
    setSelectedTerminal(null)
  }

  const openCreateTerminal = () => {
    resetTerminalForm()
    setModalType("terminal")
  }

  const openEditTerminal = (terminal: SIP2Terminal) => {
    setTerminalForm(terminalToFormData(terminal))
    setSelectedTerminal(terminal)
    setIsEditing(true)
    setModalType("terminal")
  }

  const closeModal = () => {
    setModalType(null)
    resetTerminalForm()
  }

  const handleSaveTerminal = async () => {
    if (!token || !terminalForm.terminal_id.trim() || !terminalForm.name.trim()) {
      toast.error(t('staffSIP2.terminalIdAndNameAre'))
      return
    }
    setIsSaving(true)
    try {
      if (isEditing && selectedTerminal) {
        await updateTerminal(token, selectedTerminal.terminal_id, clean({
          name: terminalForm.name.trim(),
          description: terminalForm.description.trim() || undefined,
          location: terminalForm.location.trim() || undefined,
          institution_id: terminalForm.institution_id.trim() || undefined,
          password: terminalForm.password.trim() || undefined,
          is_active: terminalForm.is_active,
          allow_checkout: terminalForm.allow_checkout,
          allow_checkin: terminalForm.allow_checkin,
          allow_renewal: terminalForm.allow_renewal,
          allow_patron_info: terminalForm.allow_patron_info,
        }))
        toast.success(t('toast.staffSIP2.terminalUpdatedSuccessfully'))
      } else {
        await createTerminal(token, clean({
          terminal_id: terminalForm.terminal_id.trim(),
          name: terminalForm.name.trim(),
          description: terminalForm.description.trim() || undefined,
          location: terminalForm.location.trim() || undefined,
          institution_id: terminalForm.institution_id.trim() || undefined,
          password: terminalForm.password.trim() || undefined,
          is_active: terminalForm.is_active,
          allow_checkout: terminalForm.allow_checkout,
          allow_checkin: terminalForm.allow_checkin,
          allow_renewal: terminalForm.allow_renewal,
          allow_patron_info: terminalForm.allow_patron_info,
        }))
        toast.success(t('toast.staffSIP2.terminalCreatedSuccessfully'))
      }
      setModalType(null)
      resetTerminalForm()
      fetchTerminals()
      onMutate()
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : t('toast.staffSIP2.failedToSaveTerminal'))
    } finally {
      setIsSaving(false)
    }
  }

  const handleDeleteTerminal = async () => {
    if (!token || !deletingTerminal) return
    setIsDeleting(true)
    try {
      await deleteTerminal(token, deletingTerminal.terminal_id)
      toast.success(t('toast.staffSIP2.terminalDeletedSuccessfully'))
      setShowDeleteConfirm(false)
      setDeletingTerminal(null)
      fetchTerminals()
      onMutate()
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : t('toast.staffSIP2.failedToDeleteTerminal'))
    } finally {
      setIsDeleting(false)
    }
  }

  const handleToggleActive = async (terminal: SIP2Terminal) => {
    if (!token) return
    try {
      await updateTerminal(token, terminal.terminal_id, { is_active: !terminal.is_active })
      toast.success(terminal.is_active ? t('toast.staffSIP2.terminalDeactivated') : t('toast.staffSIP2.terminalActivated'))
      fetchTerminals()
      onMutate()
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : t('toast.staffSIP2.failedToUpdateTerminal'))
    }
  }

  const confirmDelete = (terminal: SIP2Terminal) => {
    setDeletingTerminal(terminal)
    setShowDeleteConfirm(true)
  }

  const cancelDelete = () => {
    setShowDeleteConfirm(false)
    setDeletingTerminal(null)
  }

  return {
    // List state
    terminals,
    terminalSearch,
    setTerminalSearch,
    terminalFilter,
    setTerminalFilter,
    terminalPage,
    setTerminalPage,
    terminalTotalPages,
    isLoading,
    fetchTerminals,

    // Modal state
    modalType,
    isEditing,
    isSaving,
    terminalForm,
    setTerminalForm,
    openCreateTerminal,
    openEditTerminal,
    closeModal,
    handleSaveTerminal,

    // Delete state
    showDeleteConfirm,
    deletingTerminal,
    isDeleting,
    handleDeleteTerminal,
    handleToggleActive,
    confirmDelete,
    cancelDelete,
  }
}
