/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Hook for managing patron estate/deceased handling
 */

import { useState, useCallback } from "react"
import {
  markPatronDeceased,
  getEstateOutstanding,
  updateEstateContact,
  markEstateResolved,
  MarkDeceasedRequest,
  EstateOutstandingResponse,
} from "../../../../api/staff-api"
import toast from "react-hot-toast"

interface UseEstateManagementReturn {
  showDeceasedModal: boolean
  isMarkingDeceased: boolean
  deceasedForm: MarkDeceasedRequest
  showEstatePanel: boolean
  estateData: EstateOutstandingResponse | null
  isLoadingEstateData: boolean
  estateContactForm: {
    estate_contact_name: string
    estate_contact_email: string
    estate_contact_phone: string
    notes: string
  }
  isUpdatingEstateContact: boolean
  estateResolutionNotes: string
  isResolvingEstate: boolean
  setShowDeceasedModal: (show: boolean) => void
  setDeceasedForm: (form: MarkDeceasedRequest) => void
  setShowEstatePanel: (show: boolean) => void
  setEstateContactForm: (form: { estate_contact_name: string; estate_contact_email: string; estate_contact_phone: string; notes: string }) => void
  setEstateResolutionNotes: (notes: string) => void
  handleMarkDeceased: (token: string, patronId: number) => Promise<void>
  handleLoadEstateData: (token: string, patronId: number) => Promise<void>
  handleUpdateEstateContact: (token: string, patronId: number) => Promise<void>
  handleResolveEstate: (token: string, patronId: number) => Promise<void>
}

export function useEstateManagement(): UseEstateManagementReturn {
  const [showDeceasedModal, setShowDeceasedModal] = useState(false)
  const [isMarkingDeceased, setIsMarkingDeceased] = useState(false)
  const [deceasedForm, setDeceasedForm] = useState<MarkDeceasedRequest>({})
  const [showEstatePanel, setShowEstatePanel] = useState(false)
  const [estateData, setEstateData] = useState<EstateOutstandingResponse | null>(null)
  const [isLoadingEstateData, setIsLoadingEstateData] = useState(false)
  const [estateContactForm, setEstateContactForm] = useState({
    estate_contact_name: "",
    estate_contact_email: "",
    estate_contact_phone: "",
    notes: "",
  })
  const [isUpdatingEstateContact, setIsUpdatingEstateContact] = useState(false)
  const [estateResolutionNotes, setEstateResolutionNotes] = useState("")
  const [isResolvingEstate, setIsResolvingEstate] = useState(false)

  const handleMarkDeceased = useCallback(async (token: string, patronId: number) => {
    setIsMarkingDeceased(true)
    try {
      await markPatronDeceased(token, patronId, deceasedForm)
      toast.success("Patron marked as deceased")
      setShowDeceasedModal(false)
      setDeceasedForm({})
    } catch (_err) {
      toast.error("Failed to mark patron as deceased")
    } finally {
      setIsMarkingDeceased(false)
    }
  }, [deceasedForm])

  const handleLoadEstateData = useCallback(async (token: string, patronId: number) => {
    setIsLoadingEstateData(true)
    try {
      const data = await getEstateOutstanding(token, patronId)
      setEstateData(data)
    } catch (_err) {
      toast.error("Failed to load estate data")
    } finally {
      setIsLoadingEstateData(false)
    }
  }, [])

  const handleUpdateEstateContact = useCallback(async (token: string, patronId: number) => {
    setIsUpdatingEstateContact(true)
    try {
      await updateEstateContact(token, patronId, estateContactForm)
      toast.success("Estate contact updated")
      await handleLoadEstateData(token, patronId)
    } catch (_err) {
      toast.error("Failed to update estate contact")
    } finally {
      setIsUpdatingEstateContact(false)
    }
  }, [estateContactForm, handleLoadEstateData])

  const handleResolveEstate = useCallback(async (token: string, patronId: number) => {
    setIsResolvingEstate(true)
    try {
      await markEstateResolved(token, patronId, estateResolutionNotes || '')
      toast.success("Estate marked as resolved")
      setShowEstatePanel(false)
      setEstateResolutionNotes("")
    } catch (_err) {
      toast.error("Failed to resolve estate")
    } finally {
      setIsResolvingEstate(false)
    }
  }, [estateResolutionNotes])

  return {
    showDeceasedModal,
    isMarkingDeceased,
    deceasedForm,
    showEstatePanel,
    estateData,
    isLoadingEstateData,
    estateContactForm,
    isUpdatingEstateContact,
    estateResolutionNotes,
    isResolvingEstate,
    setShowDeceasedModal,
    setDeceasedForm,
    setShowEstatePanel,
    setEstateContactForm,
    setEstateResolutionNotes,
    handleMarkDeceased,
    handleLoadEstateData,
    handleUpdateEstateContact,
    handleResolveEstate,
  }
}
