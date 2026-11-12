/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import toast from "react-hot-toast"
import { t } from "@/i18n"

export function exportToCSV(data: Record<string, unknown>[], filename: string): void {
  if (data.length === 0) {
    toast.error(t("roomReservationReports.noDataToExport"))
    return
  }
  const firstRow = data[0]
  if (!firstRow) return
  const headers = Object.keys(firstRow).join(",")
  const rows = data.map((row) => Object.values(row).join(",")).join("\n")
  const csv = `${headers}\n${rows}`
  const blob = new Blob([csv], { type: "text/csv" })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
  toast.success(t("toast.roomReservationReports.reportExported"))
}
