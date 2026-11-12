/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from "react"
import { DollarSign } from "lucide-react"
import { Patron } from "../../../api/api"
import { useTranslation, formatCurrency } from "@/i18n"
import { FinePaymentModal } from "./FinePaymentModal"
import { WaiveFineModal } from './WaiveFineModal'
import { PatronFinesList } from './PatronFinesList'
import FineDetailPanel from './FineDetailPanel'

interface PatronFinesTabProps {
  selectedPatron: Patron | null
  onFineUpdated?: () => void
}

export function PatronFinesTab({ selectedPatron, onFineUpdated }: PatronFinesTabProps) {
  const { language } = useTranslation()
  const [isPaymentModalOpen, setIsPaymentModalOpen] = useState(false)
  const [selectedFineId, setSelectedFineId] = useState<number | null>(null)
  const [selectedFineBalance, setSelectedFineBalance] = useState<number>(0)
  const [isWaiveModalOpen, setIsWaiveModalOpen] = useState(false)
  const [selectedFineIdForWaive, setSelectedFineIdForWaive] = useState<number | null>(null)
  const [selectedFineWaiveBalance, setSelectedFineWaiveBalance] = useState<number>(0)
  const [refreshKey, setRefreshKey] = useState(0)

  if (!selectedPatron) return null

  const handleOpenPaymentModal = (fineId: number, balance: number) => {
    setSelectedFineId(fineId)
    setSelectedFineBalance(balance)
    setIsPaymentModalOpen(true)
  }

  const handlePaymentSuccess = () => {
    setIsPaymentModalOpen(false)
    setRefreshKey((current) => current + 1)
    onFineUpdated?.()
  }

  const handleOpenWaiveModal = (fineId: number, balance: number) => {
    setSelectedFineIdForWaive(fineId)
    setSelectedFineWaiveBalance(balance)
    setIsWaiveModalOpen(true)
  }

  const handleWaiveSuccess = () => {
    setIsWaiveModalOpen(false)
    setSelectedFineIdForWaive(null)
    setRefreshKey((current) => current + 1)
    onFineUpdated?.()
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
          Fines & Fees
        </h3>
        <div className="text-right">
          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Balance</p>
          <p
            className={`text-xl font-bold ${
              Number(selectedPatron.fines_balance) > 0
                ? "text-lsc-rose dark:text-lsc-rose-light"
                : "text-lsc-rose dark:text-lsc-rose-light"
            }`}
          >
            {formatCurrency(Number(selectedPatron.fines_balance ?? 0), language, 'USD')}
          </p>
        </div>
      </div>
      {Number(selectedPatron.fines_balance) === 0 ? (
        <div className="text-center py-8">
          <DollarSign aria-hidden="true" className="w-12 h-12 text-lsc-dark/70 dark:text-lsc-rose-light mx-auto mb-3" />
          <p className="text-lsc-rose dark:text-lsc-rose-light">No outstanding fines</p>
        </div>
      ) : (
        <PatronFinesList
          patronId={selectedPatron.id}
          onPayClick={handleOpenPaymentModal}
          onWaiveClick={handleOpenWaiveModal}
          refreshKey={refreshKey}
        />
      )}

      {/* Detailed fine breakdown with item context and payment history */}
      <div className="mt-6 pt-6 border-t border-lsc-border dark:border-earth-700">
        <FineDetailPanel patronId={selectedPatron.id} />
      </div>

      {selectedFineId && (
        <FinePaymentModal
          isOpen={isPaymentModalOpen}
          onClose={() => setIsPaymentModalOpen(false)}
          onPaymentSuccess={handlePaymentSuccess}
          balance={selectedFineBalance}
          patronId={selectedPatron.id}
          fineId={selectedFineId}
        />
      )}

      {selectedFineIdForWaive && (
        <WaiveFineModal
          isOpen={isWaiveModalOpen}
          onClose={() => setIsWaiveModalOpen(false)}
          onWaiveSuccess={handleWaiveSuccess}
          balance={selectedFineWaiveBalance}
          patronId={selectedPatron.id}
          fineId={selectedFineIdForWaive}
        />
      )}
    </div>
  )
}
