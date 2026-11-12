/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useCallback, type RefObject } from "react"
import { staffCheckinItem } from "@/api/api"
import { reportCheckinCondition, type NextHoldInfo } from "@/api/staff-api/circulation"
import toast from "react-hot-toast"
import { useTranslation } from "@/i18n"

export type ConditionType = "damaged" | "lost_by_patron" | "claims_returned" | "returned_damaged"

export interface LastCheckinResult {
  checkoutId: number
  itemTitle: string | null
}

interface UseCheckinReturn {
  checkinBarcode: string
  setCheckinBarcode: (barcode: string) => void
  isCheckingIn: boolean
  checkinSuccess: boolean
  handleCheckin: (e: React.FormEvent, onComplete?: () => void) => void
  lastCheckinResult: LastCheckinResult | null
  lastNextHold: NextHoldInfo | null
  dismissNextHold: () => void
  showConditionPanel: boolean
  setShowConditionPanel: (show: boolean) => void
  isSubmittingCondition: boolean
  conditionSubmitted: boolean
  submitConditionReport: (conditionType: ConditionType, notes: string) => Promise<void>
  dismissConditionPanel: () => void
}

export function useCheckin(
  token: string | null,
  options?: { inputRef?: RefObject<HTMLInputElement> },
): UseCheckinReturn {
  const { t } = useTranslation()
  const [checkinBarcode, setCheckinBarcode] = useState("")
  const [isCheckingIn, setIsCheckingIn] = useState(false)
  const [checkinSuccess, setCheckinSuccess] = useState(false)
  const [lastCheckinResult, setLastCheckinResult] = useState<LastCheckinResult | null>(null)
  const [lastNextHold, setLastNextHold] = useState<NextHoldInfo | null>(null)
  const [showConditionPanel, setShowConditionPanel] = useState(false)
  const [isSubmittingCondition, setIsSubmittingCondition] = useState(false)
  const [conditionSubmitted, setConditionSubmitted] = useState(false)

  const handleCheckin = async (e: React.FormEvent, onComplete?: () => void) => {
    e.preventDefault()
    if (!token || !checkinBarcode.trim()) return
    setIsCheckingIn(true)
    setCheckinSuccess(false)
    setLastCheckinResult(null)
    setLastNextHold(null)
    setShowConditionPanel(false)
    setConditionSubmitted(false)
    try {
      const result = await staffCheckinItem(token, checkinBarcode)
      toast.success(result.message || t("staffCirculation.itemCheckedIn"))
      setCheckinSuccess(true)
      setLastCheckinResult({
        checkoutId: result.checkout.id,
        itemTitle: result.checkout.item_title ?? null,
      })
      setLastNextHold(result.next_hold ?? null)
      setTimeout(() => setCheckinSuccess(false), 3000)
      setCheckinBarcode("")
      if (onComplete) onComplete()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : t("staffCirculation.checkinFailed"))
    } finally {
      setIsCheckingIn(false)
      // Refocus the barcode input so the next scan registers without a click.
      // BatchCheckinSection already does this; QuickCheckinSection didn't.
      setCheckinBarcode("")
      setTimeout(() => options?.inputRef?.current?.focus(), 50)
    }
  }

  const submitConditionReport = useCallback(async (conditionType: ConditionType, notes: string) => {
    if (!token || !lastCheckinResult) return
    setIsSubmittingCondition(true)
    try {
      await reportCheckinCondition(token, lastCheckinResult.checkoutId, conditionType, notes)
      setConditionSubmitted(true)
      toast.success("Condition report submitted")
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to submit condition report")
    } finally {
      setIsSubmittingCondition(false)
    }
  }, [token, lastCheckinResult])

  const dismissConditionPanel = useCallback(() => {
    setShowConditionPanel(false)
    setLastCheckinResult(null)
    setConditionSubmitted(false)
  }, [])

  const dismissNextHold = useCallback(() => {
    setLastNextHold(null)
  }, [])

  return {
    checkinBarcode,
    setCheckinBarcode,
    isCheckingIn,
    checkinSuccess,
    handleCheckin,
    lastCheckinResult,
    lastNextHold,
    dismissNextHold,
    showConditionPanel,
    setShowConditionPanel,
    isSubmittingCondition,
    conditionSubmitted,
    submitConditionReport,
    dismissConditionPanel,
  }
}
