/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useCallback } from "react"
import toast from "react-hot-toast"
import {
  bulkBlockPatrons,
  bulkMessagePatrons,
  bulkWaiveFines,
  exportPatrons,
  type BulkMessageChannel,
  type BulkMessageResponse,
} from "../../../../api/staff-api"
import { BulkOperationResult } from "../../../../components/staff"

interface UseBulkOperationsProps {
  token: string | null
  onOperationComplete?: () => void
}

interface BulkMessagePayload {
  patron_ids: number[]
  subject: string | null
  body: string
  channels: BulkMessageChannel[]
}

interface UseBulkOperationsReturn {
  handleBulkBlock: (ids: number[]) => Promise<BulkOperationResult>
  handleBulkUnblock: (ids: number[]) => Promise<BulkOperationResult>
  handleBulkWaiveFines: (ids: number[], reason: string) => Promise<BulkOperationResult>
  handleBulkExport: (ids: number[]) => Promise<BulkOperationResult>
  handleBulkMessage: (payload: BulkMessagePayload) => Promise<BulkMessageResponse>
}

export function useBulkOperations({
  token,
  onOperationComplete,
}: UseBulkOperationsProps): UseBulkOperationsReturn {
  const handleBulkBlock = useCallback(
    async (ids: number[]): Promise<BulkOperationResult> => {
      if (!token) throw new Error("Not authenticated")
      const result = await bulkBlockPatrons(token, {
        patron_ids: ids,
        blocked: true,
        reason: "Bulk operation by staff",
      })
      if (result.success) {
        toast.success(result.message)
        onOperationComplete?.()
      }
      return {
        success: result.success,
        successCount: result.processed_count,
        failureCount: result.failed_ids.length,
        message: result.message,
        failedIds: result.failed_ids,
      }
    },
    [token, onOperationComplete]
  )

  const handleBulkUnblock = useCallback(
    async (ids: number[]): Promise<BulkOperationResult> => {
      if (!token) throw new Error("Not authenticated")
      const result = await bulkBlockPatrons(token, {
        patron_ids: ids,
        blocked: false,
      })
      if (result.success) {
        toast.success(result.message)
        onOperationComplete?.()
      }
      return {
        success: result.success,
        successCount: result.processed_count,
        failureCount: result.failed_ids.length,
        message: result.message,
        failedIds: result.failed_ids,
      }
    },
    [token, onOperationComplete]
  )

  const handleBulkWaiveFines = useCallback(
    async (ids: number[], reason: string): Promise<BulkOperationResult> => {
      if (!token) throw new Error("Not authenticated")
      const trimmed = (reason ?? "").trim()
      if (trimmed.length < 5) {
        const msg = "A reason of at least 5 characters is required to waive fines in bulk."
        toast.error(msg)
        return {
          success: false,
          successCount: 0,
          failureCount: ids.length,
          message: msg,
          failedIds: ids,
        }
      }
      const result = await bulkWaiveFines(token, {
        patron_ids: ids,
        reason: trimmed,
      })
      if (result.success) {
        toast.success(`Waived ${result.fines_waived} fines totaling $${result.total_amount_waived.toFixed(2)}`)
        onOperationComplete?.()
      }
      return {
        success: result.success,
        successCount: result.patrons_processed,
        failureCount: result.failed_ids.length,
        message: result.message,
        failedIds: result.failed_ids,
      }
    },
    [token, onOperationComplete]
  )

  const handleBulkExport = useCallback(
    async (ids: number[]): Promise<BulkOperationResult> => {
      if (!token) throw new Error("Not authenticated")
      const blob = await exportPatrons(token, { patronIds: ids, format: "csv" })
      if (blob instanceof Blob) {
        const url = window.URL.createObjectURL(blob)
        const link = document.createElement("a")
        link.href = url
        link.download = `patrons-export-${new Date().toISOString().split("T")[0]}.csv`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        window.URL.revokeObjectURL(url)
      }
      toast.success(`Exported ${ids.length} patrons`)
      return {
        success: true,
        successCount: ids.length,
        failureCount: 0,
        message: `Exported ${ids.length} patrons`,
      }
    },
    [token]
  )

  const handleBulkMessage = useCallback(
    async (payload: BulkMessagePayload): Promise<BulkMessageResponse> => {
      if (!token) throw new Error("Not authenticated")
      const result = await bulkMessagePatrons(token, payload)
      // Always surface a status toast; the modal renders the per-recipient detail.
      const summary = `${result.sent} sent, ${result.capped} capped, ${result.failed} failed`
      if (result.failed === 0 && result.capped === 0) {
        toast.success(summary)
      } else {
        toast(summary, { icon: result.failed > 0 ? "warning" : "info" })
      }
      onOperationComplete?.()
      return result
    },
    [token, onOperationComplete]
  )

  return {
    handleBulkBlock,
    handleBulkUnblock,
    handleBulkWaiveFines,
    handleBulkExport,
    handleBulkMessage,
  }
}
