/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useCallback } from "react"
import { staffCheckoutItem } from "@/api/api"
import type { Checkout } from "@/api/api"
import toast from "react-hot-toast"
import { useTranslation } from "@/i18n"
import type { CheckoutError, CheckoutErrorType } from "../components/InlineErrorDisplay"
import type { HoldOverrideInfo, HoldDisposition } from "@/components/staff/OverrideHoldModal"

interface UseCheckoutReturn {
  itemBarcode: string
  setItemBarcode: (barcode: string) => void
  isCheckingOut: boolean
  checkoutSuccess: boolean
  pendingBarcode: string
  checkoutError: CheckoutError | null
  clearCheckoutError: () => void
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  problemModal: any
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  setProblemModal: (problem: any) => void
  showProblemModal: boolean
  openProblemModal: () => void
  handleCheckout: (e: React.FormEvent, patronId: number, onComplete: (patronId: number) => void) => void
  handleRetryCheckout: (patronId: number, onComplete: (patronId: number) => void) => void
  clearProblemModal: () => void
  holdOverride: HoldOverrideInfo | null
  handleOverrideCheckout: (patronId: number, disposition: HoldDisposition, onComplete: (patronId: number) => void) => void
  clearHoldOverride: () => void
  // Most-recent successful checkout (used by the print/email slip toolbar).
  // Persists past the 1.5s checkoutSuccess pulse so staff can still send a
  // slip after the success state has cleared.
  lastCheckout: Checkout | null
  clearLastCheckout: () => void
}

/**
 * Categorize an error into a typed CheckoutError based on HTTP status and message content.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function categorizeError(err: unknown, fallbackMessage: string): { error: CheckoutError; problem?: any; holdOverride?: HoldOverrideInfo } {
  const message = err instanceof Error ? err.message : fallbackMessage
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const response = err instanceof Error ? (err as any).response : undefined
  const status: number | undefined = response?.status

  const detail0 = response?.details?.[0]

  // A hold-override block means staff can override -- surface it for the modal.
  if (detail0?.hold_override) {
    const ho = detail0.hold_override
    const holdOverride: HoldOverrideInfo = {
      holdId: ho.hold_id ?? null,
      heldPatronName: ho.held_patron_name ?? "another patron",
      patronOnWay: !!ho.patron_on_way,
      queueLength: ho.queue_length ?? 0,
    }
    const type = categorizeByStatus(status, message)
    return { error: { type, message }, holdOverride }
  }

  // Check for problem resolution details.
  if (detail0?.problem) {
    const problemData = detail0.problem
    const type = categorizeByStatus(status, message)
    return {
      error: {
        type,
        message,
        suggestion: "Staff resolution options are available.",
        hasProblemDetails: true,
      },
      problem: problemData,
    }
  }

  const type = categorizeByStatus(status, message)
  return { error: { type, message, suggestion: suggestionForType(type) } }
}

function categorizeByStatus(status: number | undefined, message: string): CheckoutErrorType {
  if (status === 404) return "not_found"
  if (status === 409) return "hold_conflict"
  if (status === 403) {
    const lower = message.toLowerCase()
    if (lower.includes("block") || lower.includes("deceased") || lower.includes("suspend")) return "blocked"
    if (lower.includes("fine") || lower.includes("expired") || lower.includes("overdue") || lower.includes("card")) return "patron_issue"
    return "blocked"
  }
  if (status === 400) return "patron_issue"

  // Fall back to message-based detection
  const lower = message.toLowerCase()
  if (lower.includes("not found") || lower.includes("no item")) return "not_found"
  if (lower.includes("block") || lower.includes("cannot")) return "blocked"
  if (lower.includes("hold")) return "hold_conflict"
  if (lower.includes("fine") || lower.includes("expired") || lower.includes("overdue")) return "patron_issue"
  return "unknown"
}

function suggestionForType(type: CheckoutErrorType): string | undefined {
  switch (type) {
    case "not_found":
      return "Check the barcode and try again, or search the catalog."
    case "blocked":
      return "This action cannot be completed. See a supervisor if an override is needed."
    case "hold_conflict":
      return "This item may be on hold or already checked out."
    case "patron_issue":
      return "The patron's account needs attention before checkout can proceed."
    default:
      return undefined
  }
}

export function useCheckout(token: string | null): UseCheckoutReturn {
  const { t } = useTranslation()
  const [itemBarcode, setItemBarcodeRaw] = useState("")
  const [isCheckingOut, setIsCheckingOut] = useState(false)
  const [checkoutSuccess, setCheckoutSuccess] = useState(false)
  const [pendingBarcode, setPendingBarcode] = useState("")
  const [checkoutError, setCheckoutError] = useState<CheckoutError | null>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [problemModal, setProblemModal] = useState<any>(null)
  const [showProblemModal, setShowProblemModal] = useState(false)
  const [lastCheckout, setLastCheckout] = useState<Checkout | null>(null)
  const [holdOverride, setHoldOverride] = useState<HoldOverrideInfo | null>(null)

  const openProblemModal = useCallback(() => {
    if (problemModal) setShowProblemModal(true)
  }, [problemModal])

  // Auto-clear error when barcode input changes (new scan attempt)
  const setItemBarcode = useCallback((barcode: string) => {
    setItemBarcodeRaw(barcode)
    if (checkoutError) setCheckoutError(null)
    if (holdOverride) setHoldOverride(null)
  }, [checkoutError, holdOverride])

  const clearCheckoutError = useCallback(() => setCheckoutError(null), [])

  const handleCheckout = async (e: React.FormEvent, patronId: number, onComplete: (patronId: number) => void) => {
    e.preventDefault()
    if (!token || !itemBarcode.trim()) return
    setIsCheckingOut(true)
    setCheckoutSuccess(false)
    setCheckoutError(null)
    setHoldOverride(null)
    setPendingBarcode(itemBarcode)
    try {
      const result = await staffCheckoutItem(token, patronId, itemBarcode)
      setLastCheckout(result)
      toast.success(t('staffCirculation.itemCheckedOut'))
      setCheckoutSuccess(true)
      setTimeout(() => setCheckoutSuccess(false), 1500)
      setItemBarcodeRaw("")
      setPendingBarcode("")
      onComplete(patronId)
    } catch (err: unknown) {
      const { error, problem, holdOverride: ho } = categorizeError(err, t('staffCirculation.checkoutFailed'))
      if (ho) {
        setHoldOverride(ho)
      } else {
        setCheckoutError(error)
        if (problem) setProblemModal(problem)
      }
    } finally {
      setIsCheckingOut(false)
    }
  }

  const handleRetryCheckout = async (patronId: number, onComplete: (patronId: number) => void) => {
    if (!pendingBarcode) return
    setIsCheckingOut(true)
    setCheckoutError(null)
    try {
      const result = await staffCheckoutItem(token!, patronId, pendingBarcode)
      setLastCheckout(result)
      toast.success(t('staffCirculation.itemCheckedOut'))
      setCheckoutSuccess(true)
      setTimeout(() => setCheckoutSuccess(false), 1500)
      setItemBarcodeRaw("")
      setPendingBarcode("")
      setProblemModal(null)
      onComplete(patronId)
    } catch (err: unknown) {
      const { error } = categorizeError(err, t('staffCirculation.checkoutFailed'))
      setCheckoutError(error)
    } finally {
      setIsCheckingOut(false)
    }
  }

  const handleOverrideCheckout = async (
    patronId: number,
    disposition: HoldDisposition,
    onComplete: (patronId: number) => void,
  ) => {
    if (!token || !pendingBarcode) return
    setIsCheckingOut(true)
    setCheckoutError(null)
    try {
      const result = await staffCheckoutItem(token, patronId, pendingBarcode, {
        override_hold: true,
        hold_disposition: disposition,
      })
      setLastCheckout(result)
      toast.success(t('staffCirculation.itemCheckedOut'))
      setCheckoutSuccess(true)
      setTimeout(() => setCheckoutSuccess(false), 1500)
      setItemBarcodeRaw("")
      setPendingBarcode("")
      setHoldOverride(null)
      onComplete(patronId)
    } catch (err: unknown) {
      // On override failure, close the modal and surface the error inline --
      // mirrors handleRetryCheckout. The operator re-scans to retry.
      const { error } = categorizeError(err, t('staffCirculation.checkoutFailed'))
      setCheckoutError(error)
      setHoldOverride(null)
    } finally {
      setIsCheckingOut(false)
    }
  }

  const clearHoldOverride = useCallback(() => {
    setHoldOverride(null)
    setItemBarcodeRaw("")
    setPendingBarcode("")
  }, [])

  const clearProblemModal = () => {
    setProblemModal(null)
    setShowProblemModal(false)
    setItemBarcodeRaw("")
    setPendingBarcode("")
  }

  const clearLastCheckout = useCallback(() => setLastCheckout(null), [])

  return {
    itemBarcode,
    setItemBarcode,
    isCheckingOut,
    checkoutSuccess,
    pendingBarcode,
    checkoutError,
    clearCheckoutError,
    problemModal,
    setProblemModal,
    showProblemModal,
    openProblemModal,
    handleCheckout,
    handleRetryCheckout,
    clearProblemModal,
    lastCheckout,
    clearLastCheckout,
    holdOverride,
    handleOverrideCheckout,
    clearHoldOverride,
  }
}
