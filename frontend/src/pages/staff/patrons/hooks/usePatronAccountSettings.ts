/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Hook for managing patron account settings
 */

import { useState, useCallback } from "react"
import {
  getPatronAccountSettings,
  updatePatronAccountSettings,
  AccountSettings,
  AccountSettingsUpdate,
} from "../../../../api/staff-api"
import toast from "react-hot-toast"

interface UsePatronAccountSettingsReturn {
  showSettingsPanel: boolean
  accountSettings: AccountSettings | null
  isLoadingSettings: boolean
  isSavingSettings: boolean
  settingsForm: AccountSettingsUpdate
  setShowSettingsPanel: (show: boolean) => void
  setSettingsForm: (form: AccountSettingsUpdate) => void
  handleLoadAccountSettings: (token: string, patronId: number) => Promise<void>
  handleSaveAccountSettings: (token: string, patronId: number) => Promise<void>
}

export function usePatronAccountSettings(): UsePatronAccountSettingsReturn {
  const [showSettingsPanel, setShowSettingsPanel] = useState(false)
  const [accountSettings, setAccountSettings] = useState<AccountSettings | null>(null)
  const [isLoadingSettings, setIsLoadingSettings] = useState(false)
  const [isSavingSettings, setIsSavingSettings] = useState(false)
  const [settingsForm, setSettingsForm] = useState<AccountSettingsUpdate>({})

  const handleLoadAccountSettings = useCallback(async (token: string, patronId: number) => {
    setIsLoadingSettings(true)
    try {
      const settings = await getPatronAccountSettings(token, patronId)
      setAccountSettings(settings)
      setSettingsForm({
        communication_preferences: settings.communication_preferences,
        display_preferences: settings.display_preferences,
      })
    } catch (_err) {
      toast.error("Failed to load account settings")
    } finally {
      setIsLoadingSettings(false)
    }
  }, [])

  const handleSaveAccountSettings = useCallback(
    async (token: string, patronId: number) => {
      setIsSavingSettings(true)
      try {
        const updated = await updatePatronAccountSettings(token, patronId, settingsForm)
        setAccountSettings(updated)
        toast.success("Settings updated successfully")
        setShowSettingsPanel(false)
      } catch (_err) {
        toast.error(_err instanceof Error ? _err.message : "Failed to save settings")
      } finally {
        setIsSavingSettings(false)
      }
    },
    [settingsForm]
  )

  return {
    showSettingsPanel,
    accountSettings,
    isLoadingSettings,
    isSavingSettings,
    settingsForm,
    setShowSettingsPanel,
    setSettingsForm,
    handleLoadAccountSettings,
    handleSaveAccountSettings,
  }
}
