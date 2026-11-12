/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useRef, useCallback } from "react"
import { Download, Upload, X, AlertTriangle, CheckCircle, Loader2 } from "lucide-react"
import { createCatalogItem, CatalogItemCreate } from "../../api/staff-api/catalog"
import { CatalogItem, CatalogSearchResult } from "../../api/catalog-api"
import { ModalBackdrop } from "@/components/ui/ModalBackdrop"
import toast from "react-hot-toast"

const CSV_COLUMNS = [
  "title", "author", "isbn", "barcode", "item_type", "status",
  "location", "publisher", "publication_year", "subjects", "description",
] as const

type CsvColumn = typeof CSV_COLUMNS[number]

// Valid catalog enums (must match backend ItemType / ItemStatus). The staff
// "Add Item" form uses dropdowns, but CSV import takes free text — so normalize
// case + common aliases here and reject anything unmappable with a clear reason,
// rather than letting the backend 422 every row opaquely.
const ITEM_TYPES = new Set([
  "book", "audiobook", "ebook", "dvd", "bluray", "cd", "vinyl",
  "magazine", "game", "equipment", "kit", "tool", "other",
])
const ITEM_TYPE_LABEL =
  "book, audiobook, ebook, dvd, bluray, cd, vinyl, magazine, game, equipment, kit, tool, other"
const ITEM_TYPE_ALIASES: Record<string, string> = {
  "e-book": "ebook", "e book": "ebook",
  "audio book": "audiobook",
  "blu-ray": "bluray", "blu ray": "bluray", "blueray": "bluray",
  "video game": "game", "videogame": "game", "board game": "game", "boardgame": "game",
  "lp": "vinyl", "record": "vinyl",
  "compact disc": "cd", "audio cd": "cd",
  "periodical": "magazine",
  "hardcover": "book", "hardback": "book", "paperback": "book", "boardbook": "book",
  "movie": "dvd", "film": "dvd",
}
const ITEM_STATUSES = new Set([
  "available", "checked_out", "on_hold", "in_transit", "on_order", "in_processing",
  "missing", "lost", "damaged", "withdrawn", "reference", "restricted",
  "lost_by_patron", "lost_in_transit", "claims_returned", "damaged_repairable",
  "damaged_withdrawn", "in_mending",
])

// Canonical enum value, "" for blank (caller defaults), or null if unmappable.
export function normalizeItemType(raw: string): string | null {
  const v = raw.trim().toLowerCase()
  if (!v) return ""
  if (ITEM_TYPES.has(v)) return v
  return ITEM_TYPE_ALIASES[v] ?? null
}

// Canonical enum value, "" for blank, or null if unmappable. Spaces/hyphens
// collapse to underscores so "On Hold" and "checked-out" resolve.
export function normalizeStatus(raw: string): string | null {
  const v = raw.trim().toLowerCase().replace(/[\s-]+/g, "_")
  if (!v) return ""
  return ITEM_STATUSES.has(v) ? v : null
}

interface ParsedRow {
  data: Record<CsvColumn, string>
  errors: string[]
  isDuplicate: boolean
  rowNumber: number
}

interface ImportResults {
  imported: number
  skipped: number
  errors: number
  details: string[]
}

interface CsvImportExportPanelProps {
  searchResults: CatalogSearchResult | null
  token: string | null
  onImportComplete: () => void
}

function escapeCsvField(value: string): string {
  if (value.includes(",") || value.includes('"') || value.includes("\n")) {
    return '"' + value.replace(/"/g, '""') + '"'
  }
  return value
}

function parseCsvLine(line: string): string[] {
  const fields: string[] = []
  let current = ""
  let inQuotes = false

  for (let i = 0; i < line.length; i++) {
    const ch = line[i]
    if (inQuotes) {
      if (ch === '"') {
        if (i + 1 < line.length && line[i + 1] === '"') {
          current += '"'
          i++
        } else {
          inQuotes = false
        }
      } else {
        current += ch
      }
    } else {
      if (ch === '"') {
        inQuotes = true
      } else if (ch === ",") {
        fields.push(current.trim())
        current = ""
      } else {
        current += ch
      }
    }
  }
  fields.push(current.trim())
  return fields
}

function parseCsv(text: string): { headers: string[]; rows: Record<string, string>[] } {
  const lines = text.split(/\r?\n/).filter((l) => l.trim())
  if (lines.length === 0) return { headers: [], rows: [] }
  const headers = parseCsvLine(lines[0] ?? '').map((h) => h.toLowerCase().replace(/\s+/g, "_"))
  const rows = lines.slice(1).map((line) => {
    const values = parseCsvLine(line)
    const row: Record<string, string> = {}
    headers.forEach((h, i) => {
      row[h] = values[i] || ""
    })
    return row
  })
  return { headers, rows }
}

function exportToCsv(items: CatalogItem[], filename: string) {
  const header = CSV_COLUMNS.map(escapeCsvField).join(",")
  const rows = items.map((item) =>
    CSV_COLUMNS.map((col) => {
      const val = item[col as keyof CatalogItem]
      return escapeCsvField(val != null ? String(val) : "")
    }).join(",")
  )
  const csv = [header, ...rows].join("\n")
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

// A correct-by-construction starter file: right headers + one example row.
// Prevents the common mistakes (no header row, genre in item_type, capitalized
// status) that make the backend reject every row.
function downloadCsvTemplate() {
  const example: Record<CsvColumn, string> = {
    title: "The Great Gatsby", author: "F. Scott Fitzgerald", isbn: "9780743273565",
    barcode: "", item_type: "book", status: "available", location: "",
    publisher: "Scribner", publication_year: "1925", subjects: "Fiction", description: "",
  }
  const header = CSV_COLUMNS.map(escapeCsvField).join(",")
  const row = CSV_COLUMNS.map((c) => escapeCsvField(example[c])).join(",")
  const blob = new Blob([[header, row].join("\n")], { type: "text/csv;charset=utf-8;" })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = "catalog-import-template.csv"
  a.click()
  URL.revokeObjectURL(url)
}

export default function CsvImportExportPanel({
  searchResults,
  token,
  onImportComplete,
}: CsvImportExportPanelProps) {
  const [showImportModal, setShowImportModal] = useState(false)
  const [parsedRows, setParsedRows] = useState<ParsedRow[]>([])
  const [isImporting, setIsImporting] = useState(false)
  const [importProgress, setImportProgress] = useState(0)
  const [importResults, setImportResults] = useState<ImportResults | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleExport = () => {
    if (!searchResults?.items.length) {
      toast.error("No items to export")
      return
    }
    const date = new Date().toISOString().slice(0, 10)
    exportToCsv(searchResults.items, `catalog-export-${date}.csv`)
    toast.success(`Exported ${searchResults.items.length} items`)
  }

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (ev) => {
      const text = ev.target?.result as string
      if (!text) return

      const { headers, rows } = parseCsv(text)

      if (!headers.includes("title")) {
        toast.error("CSV must have a 'title' column")
        return
      }

      const seenIsbns = new Set<string>()
      const parsed: ParsedRow[] = rows.map((row, i) => {
        const errors: string[] = []
        const data = {} as Record<CsvColumn, string>

        for (const col of CSV_COLUMNS) {
          data[col] = row[col] || ""
        }

        if (!data.title.trim()) {
          errors.push("Missing title")
        }

        const normalizedType = normalizeItemType(data.item_type)
        if (normalizedType === null) {
          errors.push(`Invalid item_type "${data.item_type.trim()}" (use: ${ITEM_TYPE_LABEL})`)
        } else {
          data.item_type = normalizedType
        }

        const normalizedStatus = normalizeStatus(data.status)
        if (normalizedStatus === null) {
          errors.push(`Invalid status "${data.status.trim()}" (use: available, checked_out, on_hold, in_transit, ...)`)
        } else {
          data.status = normalizedStatus
        }

        let isDuplicate = false
        if (data.isbn.trim()) {
          if (seenIsbns.has(data.isbn.trim())) {
            isDuplicate = true
          }
          seenIsbns.add(data.isbn.trim())
        }

        return { data, errors, isDuplicate, rowNumber: i + 2 }
      })

      setParsedRows(parsed)
      setImportResults(null)
      setImportProgress(0)
      setShowImportModal(true)
    }
    reader.readAsText(file)
    e.target.value = ""
  }, [])

  const handleConfirmImport = async () => {
    if (!token) return

    const validRows = parsedRows.filter((r) => r.errors.length === 0 && !r.isDuplicate)
    if (validRows.length === 0) {
      toast.error("No valid rows to import")
      return
    }

    setIsImporting(true)
    setImportProgress(0)

    const results: ImportResults = { imported: 0, skipped: 0, errors: 0, details: [] }
    const total = validRows.length

    for (let i = 0; i < validRows.length; i++) {
      const row = validRows[i]
      if (!row) continue
      try {
        const payload: CatalogItemCreate = {
          title: row.data.title.trim(),
          item_type: row.data.item_type.trim() || "book",
        }
        if (row.data.author.trim()) payload.author = row.data.author.trim()
        if (row.data.isbn.trim()) payload.isbn = row.data.isbn.trim()
        if (row.data.barcode.trim()) payload.barcode = row.data.barcode.trim()
        if (row.data.status.trim()) payload.status = row.data.status.trim()
        if (row.data.location.trim()) payload.location = row.data.location.trim()
        if (row.data.publisher.trim()) payload.publisher = row.data.publisher.trim()
        if (row.data.publication_year.trim()) {
          const yr = parseInt(row.data.publication_year.trim())
          if (!isNaN(yr)) payload.publication_year = yr
        }
        if (row.data.subjects.trim()) payload.subjects = row.data.subjects.trim()
        if (row.data.description.trim()) payload.description = row.data.description.trim()

        await createCatalogItem(token, payload)
        results.imported++
      } catch (err) {
        results.errors++
        results.details.push(`Row ${row.rowNumber}: ${err instanceof Error ? err.message : "Unknown error"}`)
      }
      setImportProgress(Math.round(((i + 1) / total) * 100))
    }

    results.skipped = parsedRows.filter((r) => r.isDuplicate).length

    setImportResults(results)
    setIsImporting(false)

    if (results.imported > 0) {
      onImportComplete()
    }
  }

  const errorCount = parsedRows.filter((r) => r.errors.length > 0).length
  const duplicateCount = parsedRows.filter((r) => r.isDuplicate).length
  const validCount = parsedRows.filter((r) => r.errors.length === 0 && !r.isDuplicate).length

  return (
    <>
      <div className="flex items-center gap-2">
        <button
          onClick={handleExport}
          disabled={!searchResults?.items.length}
          className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 disabled:opacity-50 rounded-xl transition-colors border border-lsc-border dark:border-earth-700"
        >
          <Download aria-hidden="true" className="w-4 h-4" />
          Export CSV
        </button>
        <button
          onClick={() => fileInputRef.current?.click()}
          className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-xl transition-colors border border-lsc-border dark:border-earth-700"
        >
          <Upload aria-hidden="true" className="w-4 h-4" />
          Import CSV
        </button>
        <button
          onClick={downloadCsvTemplate}
          className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-xl transition-colors border border-lsc-border dark:border-earth-700"
        >
          <Download aria-hidden="true" className="w-4 h-4" />
          Template
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,text/csv"
          onChange={handleFileSelect}
          className="hidden"
          aria-label="Select CSV file to import"
        />
      </div>

      {showImportModal && (
        <ModalBackdrop onClose={() => !isImporting && setShowImportModal(false)} title="Import CSV">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg w-full max-w-3xl my-8">
            <div className="px-6 py-4 border-b border-lsc-border dark:border-earth-700 flex items-center justify-between">
              <h2 className="text-xl font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                Import CSV Preview
              </h2>
              {!isImporting && (
                <button
                  onClick={() => setShowImportModal(false)}
                  className="p-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark dark:hover:text-lsc-cream rounded-xl"
                  aria-label="Close import dialog"
                >
                  <X aria-hidden="true" className="w-5 h-5" />
                </button>
              )}
            </div>

            <div className="p-6 space-y-4 max-h-[70vh] overflow-y-auto">
              {/* Summary badges */}
              <div className="flex flex-wrap gap-3 text-sm">
                <span className="px-3 py-1 rounded-lg bg-lsc-cream dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream font-medium">
                  {parsedRows.length} total rows
                </span>
                <span className="px-3 py-1 rounded-lg bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-400 font-medium">
                  {validCount} valid
                </span>
                {duplicateCount > 0 && (
                  <span className="px-3 py-1 rounded-lg bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-400 font-medium">
                    {duplicateCount} duplicates
                  </span>
                )}
                {errorCount > 0 && (
                  <span className="px-3 py-1 rounded-lg bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-400 font-medium">
                    {errorCount} errors
                  </span>
                )}
              </div>

              {/* Preview table */}
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-lsc-cream dark:bg-lsc-brown/50">
                    <tr>
                      <th className="px-3 py-2 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">Row</th>
                      <th className="px-3 py-2 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">Title</th>
                      <th className="px-3 py-2 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">Author</th>
                      <th className="px-3 py-2 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">ISBN</th>
                      <th className="px-3 py-2 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">Type</th>
                      <th className="px-3 py-2 text-left text-xs font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
                    {parsedRows.slice(0, 10).map((row) => (
                      <tr
                        key={row.rowNumber}
                        className={
                          row.errors.length > 0
                            ? "bg-status-danger-50 dark:bg-status-danger-900/10"
                            : row.isDuplicate
                            ? "bg-status-warning-50 dark:bg-status-warning-900/10"
                            : ""
                        }
                      >
                        <td className="px-3 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 font-mono">
                          {row.rowNumber}
                          {row.errors.length > 0 && (
                            <AlertTriangle className="inline w-3 h-3 ml-1 text-status-danger-500" />
                          )}
                          {row.isDuplicate && (
                            <span className="ml-1 text-xs text-status-warning-600 dark:text-status-warning-400">dup</span>
                          )}
                        </td>
                        <td className="px-3 py-2 text-lsc-dark dark:text-lsc-cream truncate max-w-[200px]">
                          {row.data.title || <span className="text-status-danger-500 italic">missing</span>}
                        </td>
                        <td className="px-3 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 truncate max-w-[150px]">
                          {row.data.author || "-"}
                        </td>
                        <td className="px-3 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 font-mono text-xs">
                          {row.data.isbn || "-"}
                        </td>
                        <td className="px-3 py-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                          {row.data.item_type || "book"}
                        </td>
                        <td className="px-3 py-2 text-lsc-dark/70 dark:text-lsc-cream/70">
                          {row.data.status || "available"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {parsedRows.length > 10 && (
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-2 px-3">
                    ...and {parsedRows.length - 10} more rows
                  </p>
                )}
              </div>

              {/* Error details */}
              {errorCount > 0 && (
                <div className="rounded-xl border border-status-danger-200 dark:border-status-danger-800 p-3">
                  <p className="text-sm font-medium text-status-danger-700 dark:text-status-danger-400 mb-1">Validation Errors</p>
                  <ul className="text-xs text-status-danger-600 dark:text-status-danger-400 space-y-0.5">
                    {parsedRows
                      .filter((r) => r.errors.length > 0)
                      .slice(0, 5)
                      .map((r) => (
                        <li key={r.rowNumber}>Row {r.rowNumber}: {r.errors.join(", ")}</li>
                      ))}
                  </ul>
                </div>
              )}

              {/* Progress bar */}
              {isImporting && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    <Loader2 className="w-4 h-4 motion-safe:animate-spin text-lsc-rose" />
                    Importing... {importProgress}%
                  </div>
                  <div className="w-full bg-lsc-cream dark:bg-lsc-brown rounded-full h-2">
                    <div
                      className="bg-lsc-rose h-2 rounded-full transition-all duration-300"
                      style={{ width: `${importProgress}%` }}
                    />
                  </div>
                </div>
              )}

              {/* Results summary */}
              {importResults && (
                <div className="rounded-xl border border-lsc-border dark:border-earth-700 p-4 space-y-2">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-5 h-5 text-status-success-600" />
                    <p className="font-medium text-lsc-dark dark:text-lsc-cream">Import Complete</p>
                  </div>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                    Imported {importResults.imported} items
                    {importResults.skipped > 0 && `, ${importResults.skipped} skipped (duplicates)`}
                    {importResults.errors > 0 && `, ${importResults.errors} errors`}
                  </p>
                  {importResults.details.length > 0 && (
                    <ul className="text-xs text-status-danger-600 dark:text-status-danger-400 space-y-0.5 mt-1">
                      {importResults.details.slice(0, 5).map((d, i) => (
                        <li key={i}>{d}</li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="px-6 py-4 border-t border-lsc-border dark:border-earth-700 flex justify-end gap-3">
              {!importResults ? (
                <>
                  <button
                    onClick={() => setShowImportModal(false)}
                    disabled={isImporting}
                    className="px-4 py-2 text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-xl font-medium disabled:opacity-50"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleConfirmImport}
                    disabled={isImporting || validCount === 0}
                    className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-lsc-rose/50 text-white rounded-xl font-medium flex items-center gap-2"
                  >
                    {isImporting ? (
                      <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                    ) : (
                      <Upload aria-hidden="true" className="w-4 h-4" />
                    )}
                    Confirm Import ({validCount} items)
                  </button>
                </>
              ) : (
                <button
                  onClick={() => {
                    setShowImportModal(false)
                    setParsedRows([])
                    setImportResults(null)
                  }}
                  className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium"
                >
                  Done
                </button>
              )}
            </div>
          </div>
        </ModalBackdrop>
      )}
    </>
  )
}
