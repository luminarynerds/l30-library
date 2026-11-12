/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useCallback } from "react"
import { getPatronCheckouts, renewAllEligible } from "@/api/api"
import toast from "react-hot-toast"
import { useTranslation } from "@/i18n"
import type { Patron, PatronCheckout } from "../types"

interface UseRenewalReturn {
  patronCheckouts: PatronCheckout[]
  setPatronCheckouts: (checkouts: PatronCheckout[]) => void
  loadingCheckouts: boolean
  isRenewingAll: boolean
  showRenewConfirm: boolean
  setShowRenewConfirm: (show: boolean) => void
  refreshCheckouts: (patronId: number) => Promise<void>
  handleRenewAll: (selectedPatron: Patron | null) => Promise<void>
}

export function useRenewal(token: string | null): UseRenewalReturn {
  const { t } = useTranslation()
  const [patronCheckouts, setPatronCheckouts] = useState<PatronCheckout[]>([])
  const [loadingCheckouts, setLoadingCheckouts] = useState(false)
  const [isRenewingAll, setIsRenewingAll] = useState(false)
  const [showRenewConfirm, setShowRenewConfirm] = useState(false)

  const refreshCheckouts = useCallback(async (patronId: number) => {
    if (!token) return
    setLoadingCheckouts(true)
    try {
      const checkouts = await getPatronCheckouts(token, patronId)
      setPatronCheckouts(checkouts)
    } catch { toast.error(t('staffCirculation.failedToLoadCheckouts')) } finally { setLoadingCheckouts(false) }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  const handleRenewAll = useCallback(async (selectedPatron: Patron | null) => {
    if (!token || !selectedPatron) {
      toast.error(t('staffCirculation.pleaseSelectAPatronFirst'))
      return
    }

    if (!selectedPatron.is_active) {
      toast.error(t('staffCirculation.cannotRenewItemsForA'))
      return
    }

    setIsRenewingAll(true)
    try {
      const result = await renewAllEligible(token, selectedPatron.id)
      if (result.renewed_count > 0) {
        toast.success(t('toast.staffCirculation.renewedRenewedcountItemrenewedcount1s', { renewedcount: result.renewed_count, renewedcount1s: result.renewed_count === 1 ? '' : 's' }))
      }
      if (result.failed_count > 0) {
        toast.error(t('toast.staffCirculation.failedToRenewFailedcountItemfailedcount1s', { failedcount: result.failed_count, failedcount1s: result.failed_count === 1 ? '' : 's' }))
      }
      const checkouts = await getPatronCheckouts(token, selectedPatron.id)
      setPatronCheckouts(checkouts)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t('staffCirculation.failedToRenewItems'))
    } finally {
      setIsRenewingAll(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  return {
    patronCheckouts,
    setPatronCheckouts,
    loadingCheckouts,
    isRenewingAll,
    showRenewConfirm,
    setShowRenewConfirm,
    refreshCheckouts,
    handleRenewAll,
  }
}
