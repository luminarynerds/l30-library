/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Hook for managing patron deletion workflow
 */

import { useState, useCallback } from "react"
import {
  checkPatronDeletionEligibility,
  initiatePatronDeletion,
  cancelPatronDeletion,
  StaffDeletionEligibility,
} from "../../../../api/privacy-api"
import toast from "react-hot-toast"

interface UsePatronDeletionReturn {
  showDeletionSection: boolean
  deletionEligibility: StaffDeletionEligibility | null
  deletionEligibilityLoading: boolean
  identityVerified: boolean
  deletionNotes: string
  isInitiatingDeletion: boolean
  isCancellingDeletion: boolean
  setShowDeletionSection: (show: boolean) => void
  setIdentityVerified: (verified: boolean) => void
  setDeletionNotes: (notes: string) => void
  loadDeletionEligibility: (patronId: number) => Promise<void>
  handleInitiateDeletion: (patronId: number, verified: boolean, notes?: string) => Promise<void>
  handleCancelDeletion: (patronId: number) => Promise<void>
}

export function usePatronDeletion(): UsePatronDeletionReturn {
  const [showDeletionSection, setShowDeletionSection] = useState(false)
  const [deletionEligibility, setDeletionEligibility] = useState<StaffDeletionEligibility | null>(null)
  const [deletionEligibilityLoading, setDeletionEligibilityLoading] = useState(false)
  const [identityVerified, setIdentityVerified] = useState(false)
  const [deletionNotes, setDeletionNotes] = useState("")
  const [isInitiatingDeletion, setIsInitiatingDeletion] = useState(false)
  const [isCancellingDeletion, setIsCancellingDeletion] = useState(false)

  const loadDeletionEligibility = useCallback(async (patronId: number) => {
    setDeletionEligibilityLoading(true)
    try {
      const result = await checkPatronDeletionEligibility(patronId)
      setDeletionEligibility(result)
    } catch (_err) {
      toast.error("Failed to check deletion eligibility")
    } finally {
      setDeletionEligibilityLoading(false)
    }
  }, [])

  const handleInitiateDeletion = useCallback(
    async (patronId: number, verified: boolean, notes?: string) => {
      if (!verified) {
        toast.error("Please confirm identity verification")
        return
      }
      setIsInitiatingDeletion(true)
      try {
        const result = await initiatePatronDeletion(patronId, verified, notes)
        toast.success(result.message)
        setIdentityVerified(false)
        setDeletionNotes("")
        await loadDeletionEligibility(patronId)
      } catch (err: unknown) {
        const error = err as { message?: string }
        toast.error(error.message || "Failed to initiate deletion")
      } finally {
        setIsInitiatingDeletion(false)
      }
    },
    [loadDeletionEligibility]
  )

  const handleCancelDeletion = useCallback(async (patronId: number) => {
    setIsCancellingDeletion(true)
    try {
      const result = await cancelPatronDeletion(patronId)
      toast.success(result.message)
      await loadDeletionEligibility(patronId)
    } catch (err: unknown) {
      const error = err as { message?: string }
      toast.error(error.message || "Failed to cancel deletion")
    } finally {
      setIsCancellingDeletion(false)
    }
  }, [loadDeletionEligibility])

  return {
    showDeletionSection,
    deletionEligibility,
    deletionEligibilityLoading,
    identityVerified,
    deletionNotes,
    isInitiatingDeletion,
    isCancellingDeletion,
    setShowDeletionSection,
    setIdentityVerified,
    setDeletionNotes,
    loadDeletionEligibility,
    handleInitiateDeletion,
    handleCancelDeletion,
  }
}
