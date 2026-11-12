/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Hook for managing patron merge operations
 */

import { useState, useCallback } from "react"
import {
  findDuplicatePatrons,
  previewPatronMerge,
  mergePatronRecords,
  getPatronMergeHistory,
  getMergeAuditDetails,
  DuplicatePatron,
  MergePreview,
  MergeHistoryResponse,
  MergeAuditDetails,
  MergeRequest,
} from "../../../../api/staff-api"
import toast from "react-hot-toast"

interface UsPatronMergeReturn {
  showDuplicatesModal: boolean
  duplicates: DuplicatePatron[]
  isLoadingDuplicates: boolean
  selectedDuplicate: DuplicatePatron | null
  showMergePreviewModal: boolean
  mergePreview: MergePreview | null
  isLoadingMergePreview: boolean
  isMerging: boolean
  mergeOptions: {
    merge_checkouts: boolean
    merge_holds: boolean
    merge_fines: boolean
    merge_history: boolean
  }
  showMergeHistoryModal: boolean
  mergeHistory: MergeHistoryResponse | null
  isLoadingMergeHistory: boolean
  selectedMergeAudit: MergeAuditDetails | null
  isLoadingAuditDetails: boolean
  setShowDuplicatesModal: (show: boolean) => void
  setSelectedDuplicate: (duplicate: DuplicatePatron | null) => void
  setShowMergePreviewModal: (show: boolean) => void
  setMergeOptions: (options: { merge_checkouts: boolean; merge_holds: boolean; merge_fines: boolean; merge_history: boolean }) => void
  setShowMergeHistoryModal: (show: boolean) => void
  handleFindDuplicates: (token: string, patronId: number) => Promise<void>
  handleSelectDuplicateForMerge: (token: string, duplicate: DuplicatePatron) => Promise<void>
  handleExecuteMerge: (token: string, primaryId: number, duplicateId: number) => Promise<void>
  handleLoadMergeHistory: (token: string, patronId: number) => Promise<void>
  handleViewMergeAuditDetails: (token: string, auditId: number) => Promise<void>
}

export function usePatronMerge(): UsPatronMergeReturn {
  const [showDuplicatesModal, setShowDuplicatesModal] = useState(false)
  const [duplicates, setDuplicates] = useState<DuplicatePatron[]>([])
  const [isLoadingDuplicates, setIsLoadingDuplicates] = useState(false)
  const [primaryPatronId, setPrimaryPatronId] = useState<number | null>(null)
  const [selectedDuplicate, setSelectedDuplicate] = useState<DuplicatePatron | null>(null)
  const [showMergePreviewModal, setShowMergePreviewModal] = useState(false)
  const [mergePreview, setMergePreview] = useState<MergePreview | null>(null)
  const [isLoadingMergePreview, setIsLoadingMergePreview] = useState(false)
  const [isMerging, setIsMerging] = useState(false)
  const [mergeOptions, setMergeOptions] = useState({
    merge_checkouts: true,
    merge_holds: true,
    merge_fines: true,
    merge_history: true,
  })
  const [showMergeHistoryModal, setShowMergeHistoryModal] = useState(false)
  const [mergeHistory, setMergeHistory] = useState<MergeHistoryResponse | null>(null)
  const [isLoadingMergeHistory, setIsLoadingMergeHistory] = useState(false)
  const [selectedMergeAudit, setSelectedMergeAudit] = useState<MergeAuditDetails | null>(null)
  const [isLoadingAuditDetails, setIsLoadingAuditDetails] = useState(false)

  const handleFindDuplicates = useCallback(async (token: string, patronId: number) => {
    setIsLoadingDuplicates(true)
    try {
      const response = await findDuplicatePatrons(token, patronId)
      setDuplicates(response.duplicates)
      setPrimaryPatronId(response.patron_id)
      setShowDuplicatesModal(true)
    } catch (_err) {
      toast.error("Failed to find duplicate patrons")
    } finally {
      setIsLoadingDuplicates(false)
    }
  }, [])

  const handleSelectDuplicateForMerge = useCallback(
    async (token: string, duplicate: DuplicatePatron) => {
      if (!primaryPatronId) return
      setIsLoadingMergePreview(true)
      try {
        const request: MergeRequest = {
          primary_patron_id: primaryPatronId,
          secondary_patron_id: duplicate.id,
        }
        const preview = await previewPatronMerge(token, request)
        setMergePreview(preview)
        setSelectedDuplicate(duplicate)
        setShowMergePreviewModal(true)
      } catch (_err) {
        toast.error("Failed to load merge preview")
      } finally {
        setIsLoadingMergePreview(false)
      }
    },
    [primaryPatronId]
  )

  const handleExecuteMerge = useCallback(async (token: string, primaryId: number, duplicateId: number) => {
    setIsMerging(true)
    try {
      const request: MergeRequest = {
        primary_patron_id: primaryId,
        secondary_patron_id: duplicateId,
        ...mergeOptions,
      }
      await mergePatronRecords(token, request)
      toast.success("Patrons merged successfully")
      setShowMergePreviewModal(false)
      setShowDuplicatesModal(false)
      setSelectedDuplicate(null)
    } catch (_err) {
      toast.error(_err instanceof Error ? _err.message : "Failed to merge patrons")
    } finally {
      setIsMerging(false)
    }
  }, [mergeOptions])

  const handleLoadMergeHistory = useCallback(async (token: string, patronId: number) => {
    setIsLoadingMergeHistory(true)
    try {
      const history = await getPatronMergeHistory(token, patronId)
      setMergeHistory(history)
      setShowMergeHistoryModal(true)
    } catch (_err) {
      toast.error("Failed to load merge history")
    } finally {
      setIsLoadingMergeHistory(false)
    }
  }, [])

  const handleViewMergeAuditDetails = useCallback(async (token: string, auditId: number) => {
    setIsLoadingAuditDetails(true)
    try {
      const details = await getMergeAuditDetails(token, auditId)
      setSelectedMergeAudit(details)
    } catch (_err) {
      toast.error("Failed to load audit details")
    } finally {
      setIsLoadingAuditDetails(false)
    }
  }, [])

  return {
    showDuplicatesModal,
    duplicates,
    isLoadingDuplicates,
    selectedDuplicate,
    showMergePreviewModal,
    mergePreview,
    isLoadingMergePreview,
    isMerging,
    mergeOptions,
    showMergeHistoryModal,
    mergeHistory,
    isLoadingMergeHistory,
    selectedMergeAudit,
    isLoadingAuditDetails,
    setShowDuplicatesModal,
    setSelectedDuplicate,
    setShowMergePreviewModal,
    setMergeOptions,
    setShowMergeHistoryModal,
    handleFindDuplicates,
    handleSelectDuplicateForMerge,
    handleExecuteMerge,
    handleLoadMergeHistory,
    handleViewMergeAuditDetails,
  }
}
