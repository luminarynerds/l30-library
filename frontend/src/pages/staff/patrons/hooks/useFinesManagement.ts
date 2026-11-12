/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Hook for managing patron fines and payments
 */

import { useState, useCallback } from "react"
import {
  getPatronFineHistory,
  makePartialPayment,
  createPaymentPlan,
  getPaymentPlan,
  getReceipt,
  getPatronFineAnalytics,
  Fine,
  PaymentPlan,
  FineHistoryResponse,
  FineAnalyticsResponse,
  ReceiptData,
  PaymentMethod,
  PaymentPlanFrequency,
} from "../../../../api/staff-api"
import { getPatron } from "../../../../api/api"
import toast from "react-hot-toast"
import { FinesSubTab, PatronDetail } from "../types"

interface UseFinesManagementReturn {
  finesSubTab: FinesSubTab
  fineHistory: FineHistoryResponse | null
  fineAnalytics: FineAnalyticsResponse | null
  paymentPlan: PaymentPlan | null
  isLoadingFines: boolean
  selectedFineForPayment: Fine | null
  paymentAmount: string
  paymentMethod: PaymentMethod
  paymentNotes: string
  isProcessingPayment: boolean
  lastReceipt: ReceiptData | null
  showReceiptModal: boolean
  showPaymentPlanModal: boolean
  planAmount: string
  planInstallment: string
  planFrequency: PaymentPlanFrequency
  planReminders: boolean
  planNotes: string
  isCreatingPlan: boolean
  setFinesSubTab: (tab: FinesSubTab) => void
  setSelectedFineForPayment: (fine: Fine | null) => void
  setPaymentAmount: (amount: string) => void
  setPaymentMethod: (method: PaymentMethod) => void
  setPaymentNotes: (notes: string) => void
  setLastReceipt: (receipt: ReceiptData | null) => void
  setShowReceiptModal: (show: boolean) => void
  setShowPaymentPlanModal: (show: boolean) => void
  setPlanAmount: (amount: string) => void
  setPlanInstallment: (amount: string) => void
  setPlanFrequency: (freq: PaymentPlanFrequency) => void
  setPlanReminders: (reminders: boolean) => void
  setPlanNotes: (notes: string) => void
  loadFinesData: (token: string, patronId: number) => Promise<void>
  handlePayment: (token: string, selectedPatron: PatronDetail | null) => Promise<void>
  handleCreatePaymentPlan: (token: string, selectedPatron: PatronDetail | null) => Promise<void>
}

export function useFinesManagement(): UseFinesManagementReturn {
  const [finesSubTab, setFinesSubTab] = useState<FinesSubTab>("unpaid")
  const [fineHistory, setFineHistory] = useState<FineHistoryResponse | null>(null)
  const [fineAnalytics, setFineAnalytics] = useState<FineAnalyticsResponse | null>(null)
  const [paymentPlan, setPaymentPlan] = useState<PaymentPlan | null>(null)
  const [isLoadingFines, setIsLoadingFines] = useState(false)
  const [selectedFineForPayment, setSelectedFineForPayment] = useState<Fine | null>(null)
  const [paymentAmount, setPaymentAmount] = useState("")
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>("cash")
  const [paymentNotes, setPaymentNotes] = useState("")
  const [isProcessingPayment, setIsProcessingPayment] = useState(false)
  const [lastReceipt, setLastReceipt] = useState<ReceiptData | null>(null)
  const [showReceiptModal, setShowReceiptModal] = useState(false)
  const [showPaymentPlanModal, setShowPaymentPlanModal] = useState(false)
  const [planAmount, setPlanAmount] = useState("")
  const [planInstallment, setPlanInstallment] = useState("")
  const [planFrequency, setPlanFrequency] = useState<PaymentPlanFrequency>("monthly")
  const [planReminders, setPlanReminders] = useState(true)
  const [planNotes, setPlanNotes] = useState("")
  const [isCreatingPlan, setIsCreatingPlan] = useState(false)

  const loadFinesData = useCallback(async (token: string, patronId: number) => {
    setIsLoadingFines(true)
    try {
      const [historyData, planData, analyticsData] = await Promise.all([
        getPatronFineHistory(token, patronId),
        getPaymentPlan(token, patronId),
        getPatronFineAnalytics(token, patronId),
      ])
      setFineHistory(historyData)
      setPaymentPlan(planData)
      setFineAnalytics(analyticsData)
    } catch (_err) {
      toast.error("Failed to load fines data")
    } finally {
      setIsLoadingFines(false)
    }
  }, [])

  const handlePayment = useCallback(
    async (token: string, selectedPatron: PatronDetail | null) => {
      if (!selectedFineForPayment) return
      const amount = parseFloat(paymentAmount)
      if (isNaN(amount) || amount <= 0) {
        toast.error("Please enter a valid payment amount")
        return
      }
      if (amount > selectedFineForPayment.balance) {
        toast.error("Payment amount exceeds remaining balance")
        return
      }
      setIsProcessingPayment(true)
      try {
        const result = await makePartialPayment(token, selectedFineForPayment.id, {
          amount,
          payment_method: paymentMethod,
          ...(paymentNotes && { notes: paymentNotes }),
        })
        toast.success(`Payment of $${amount.toFixed(2)} processed successfully`)
        setSelectedFineForPayment(null)
        setPaymentAmount("")
        setPaymentNotes("")
        // Get receipt data
        const receiptData = await getReceipt(token, selectedFineForPayment.id, result.payment.id)
        setLastReceipt(receiptData)
        setShowReceiptModal(true)
        // Reload fines data
        if (selectedPatron) {
          await loadFinesData(token, selectedPatron.id)
          await getPatron(token, selectedPatron.id)
        }
      } catch (_err) {
        toast.error(_err instanceof Error ? _err.message : "Payment failed")
      } finally {
        setIsProcessingPayment(false)
      }
    },
    [selectedFineForPayment, paymentAmount, paymentMethod, paymentNotes, loadFinesData]
  )

  const handleCreatePaymentPlan = useCallback(
    async (token: string, selectedPatron: PatronDetail | null) => {
      if (!selectedPatron) return
      const totalAmt = parseFloat(planAmount)
      const installmentAmt = parseFloat(planInstallment)
      if (isNaN(totalAmt) || totalAmt <= 0) {
        toast.error("Please enter a valid total amount")
        return
      }
      if (isNaN(installmentAmt) || installmentAmt <= 0) {
        toast.error("Please enter a valid installment amount")
        return
      }
      if (installmentAmt > totalAmt) {
        toast.error("Installment amount cannot exceed total amount")
        return
      }
      setIsCreatingPlan(true)
      try {
        const plan = await createPaymentPlan(token, selectedPatron.id, {
          total_amount: totalAmt,
          installment_amount: installmentAmt,
          frequency: planFrequency,
          reminder_enabled: planReminders,
          ...(planNotes && { notes: planNotes }),
        })
        setPaymentPlan(plan)
        setShowPaymentPlanModal(false)
        setPlanAmount("")
        setPlanInstallment("")
        setPlanNotes("")
        toast.success("Payment plan created successfully")
      } catch (_err) {
        toast.error(_err instanceof Error ? _err.message : "Failed to create payment plan")
      } finally {
        setIsCreatingPlan(false)
      }
    },
    [planAmount, planInstallment, planFrequency, planReminders, planNotes]
  )

  return {
    finesSubTab,
    fineHistory,
    fineAnalytics,
    paymentPlan,
    isLoadingFines,
    selectedFineForPayment,
    paymentAmount,
    paymentMethod,
    paymentNotes,
    isProcessingPayment,
    lastReceipt,
    showReceiptModal,
    showPaymentPlanModal,
    planAmount,
    planInstallment,
    planFrequency,
    planReminders,
    planNotes,
    isCreatingPlan,
    setFinesSubTab,
    setSelectedFineForPayment,
    setPaymentAmount,
    setPaymentMethod,
    setPaymentNotes,
    setLastReceipt,
    setShowReceiptModal,
    setShowPaymentPlanModal,
    setPlanAmount,
    setPlanInstallment,
    setPlanFrequency,
    setPlanReminders,
    setPlanNotes,
    loadFinesData,
    handlePayment,
    handleCreatePaymentPlan,
  }
}
