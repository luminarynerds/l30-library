/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Hook for managing library card printing
 */

import { useState, useCallback, useRef } from "react"
import {
  getLibraryCardData,
  logCardPrinted,
  LibraryCardData,
} from "../../../../api/staff-api"
import toast from "react-hot-toast"

interface UseLibraryCardPrintingReturn {
  showCardPreviewModal: boolean
  libraryCardData: LibraryCardData | null
  isLoadingCardData: boolean
  selectedCardType: "standard" | "youth" | "senior"
  isPrintingCard: boolean
  cardPrintReason: string
  isReplacementCard: boolean
  cardPreviewRef: React.RefObject<HTMLDivElement>
  setShowCardPreviewModal: (show: boolean) => void
  setSelectedCardType: (type: "standard" | "youth" | "senior") => void
  setCardPrintReason: (reason: string) => void
  setIsReplacementCard: (replacement: boolean) => void
  handleShowCardPreview: (token: string, patronId: number) => Promise<void>
  handlePrintCard: (token: string, patronId: number) => Promise<void>
}

export function useLibraryCardPrinting(): UseLibraryCardPrintingReturn {
  const [showCardPreviewModal, setShowCardPreviewModal] = useState(false)
  const [libraryCardData, setLibraryCardData] = useState<LibraryCardData | null>(null)
  const [isLoadingCardData, setIsLoadingCardData] = useState(false)
  const [selectedCardType, setSelectedCardType] = useState<"standard" | "youth" | "senior">("standard")
  const [isPrintingCard, setIsPrintingCard] = useState(false)
  const [cardPrintReason, setCardPrintReason] = useState("")
  const [isReplacementCard, setIsReplacementCard] = useState(false)
  const cardPreviewRef = useRef<HTMLDivElement>(null)

  const handleShowCardPreview = useCallback(async (token: string, patronId: number) => {
    setIsLoadingCardData(true)
    try {
      const cardData = await getLibraryCardData(token, patronId)
      setLibraryCardData(cardData)
      setShowCardPreviewModal(true)
    } catch (_err) {
      toast.error("Failed to load card data")
    } finally {
      setIsLoadingCardData(false)
    }
  }, [])

  const handlePrintCard = useCallback(
    async (token: string, patronId: number) => {
      setIsPrintingCard(true)
      try {
        if (cardPreviewRef.current) {
          const printWindow = window.open("", "_blank")
          if (printWindow) {
            printWindow.document.write(cardPreviewRef.current.innerHTML)
            printWindow.document.close()
            printWindow.focus()
            printWindow.print()
          }
        }
        await logCardPrinted(token, patronId, {
          card_type: selectedCardType,
          ...(cardPrintReason ? { reason: cardPrintReason } : {}),
          is_replacement: isReplacementCard,
        })
        toast.success("Card printed successfully")
        setShowCardPreviewModal(false)
      } catch (_err) {
        toast.error("Failed to log card print")
      } finally {
        setIsPrintingCard(false)
      }
    },
    [selectedCardType, cardPrintReason, isReplacementCard]
  )

  return {
    showCardPreviewModal,
    libraryCardData,
    isLoadingCardData,
    selectedCardType,
    isPrintingCard,
    cardPrintReason,
    isReplacementCard,
    cardPreviewRef,
    setShowCardPreviewModal,
    setSelectedCardType,
    setCardPrintReason,
    setIsReplacementCard,
    handleShowCardPreview,
    handlePrintCard,
  }
}
