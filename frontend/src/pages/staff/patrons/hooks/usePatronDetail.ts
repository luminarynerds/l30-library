/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Hook for managing patron detail view
 */

import { useState, useCallback, type Dispatch, type SetStateAction } from "react"
import {
  getPatron,
  getPatronCheckouts,
  getPatronHolds,
  Patron,
} from "../../../../api/api"
import {
  getPatronFamily,
  PatronFamilyResponse,
} from "../../../../api/staff-api"
import toast from "react-hot-toast"
import { PatronDetail } from "../types"

interface UsePatronDetailReturn {
  selectedPatron: PatronDetail | null
  isLoadingPatron: boolean
  familyData: PatronFamilyResponse | null
  activeTab: "profile" | "checkouts" | "holds" | "fines" | "history" | "communication"
  isEditing: boolean
  editForm: Partial<Patron>
  isSaving: boolean
  isTogglingBlock: boolean
  isRefreshing: boolean
  setSelectedPatron: Dispatch<SetStateAction<PatronDetail | null>>
  setActiveTab: (tab: "profile" | "checkouts" | "holds" | "fines" | "history" | "communication") => void
  setIsEditing: (editing: boolean) => void
  setEditForm: (form: Partial<Patron>) => void
  selectPatron: (patron: Patron) => Promise<void>
  setIsSaving: (saving: boolean) => void
  setIsTogglingBlock: (toggling: boolean) => void
  refreshPatron: () => Promise<void>
}

export function usePatronDetail(token: string | null): UsePatronDetailReturn {
  const [selectedPatron, setSelectedPatron] = useState<PatronDetail | null>(null)
  const [isLoadingPatron, setIsLoadingPatron] = useState(false)
  const [familyData, setFamilyData] = useState<PatronFamilyResponse | null>(null)
  const [activeTab, setActiveTab] = useState<"profile" | "checkouts" | "holds" | "fines" | "history" | "communication">("profile")
  const [isEditing, setIsEditing] = useState(false)
  const [editForm, setEditForm] = useState<Partial<Patron>>({})
  const [isSaving, setIsSaving] = useState(false)
  const [isTogglingBlock, setIsTogglingBlock] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)

  const selectPatron = useCallback(
    async (patron: Patron) => {
      if (!token) return
      setIsLoadingPatron(true)
      setSelectedPatron(null)
      setActiveTab("profile")
      setIsEditing(false)
      setFamilyData(null)

      try {
        const [patronData, checkouts, holds, family] = await Promise.all([
          getPatron(token, patron.id),
          getPatronCheckouts(token, patron.id),
          getPatronHolds(token, patron.id),
          getPatronFamily(token, patron.id),
        ])

        setSelectedPatron({
          ...patronData,
          checkouts,
          holds,
          fines: [],
          reading_history: [],
        })
        setFamilyData(family)
        setEditForm({
          first_name: patronData.first_name,
          last_name: patronData.last_name,
          phone: patronData.phone,
          address: patronData.address,
        })
      } catch {
        toast.error("Failed to load patron details")
      } finally {
        setIsLoadingPatron(false)
      }
    },
    [token]
  )

  const refreshPatron = useCallback(
    async () => {
      if (!token || !selectedPatron) return
      setIsRefreshing(true)

      try {
        const [patronData, checkouts, holds, family] = await Promise.all([
          getPatron(token, selectedPatron.id),
          getPatronCheckouts(token, selectedPatron.id),
          getPatronHolds(token, selectedPatron.id),
          getPatronFamily(token, selectedPatron.id),
        ])

        setSelectedPatron({
          ...patronData,
          checkouts,
          holds,
          fines: [],
          reading_history: [],
        })
        setFamilyData(family)
        setEditForm({
          first_name: patronData.first_name,
          last_name: patronData.last_name,
          phone: patronData.phone,
          address: patronData.address,
        })
      } catch {
        toast.error("Failed to refresh patron details")
      } finally {
        setIsRefreshing(false)
      }
    },
    [token, selectedPatron]
  )

  return {
    selectedPatron,
    isLoadingPatron,
    familyData,
    activeTab,
    isEditing,
    editForm,
    isSaving,
    isTogglingBlock,
    setSelectedPatron,
    setActiveTab,
    setIsEditing,
    setEditForm,
    selectPatron,
    setIsSaving,
    setIsTogglingBlock,
    refreshPatron,
    isRefreshing,
  }
}
