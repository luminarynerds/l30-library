/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React from "react"
import { Z3950SearchResult } from "../../api/cataloging-api"
import { Check, ArrowRight, Minus, X } from "lucide-react"
import { t } from "@/i18n"
import type { FormData } from "./constants"

interface FieldComparison {
  label: string
  formKey: keyof FormData
  currentValue: string
  z3950Value: string
}

type MatchStatus = "identical" | "different" | "empty"

function getMatchStatus(current: string, z3950: string): MatchStatus {
  if (!z3950) return "empty"
  if (current.trim().toLowerCase() === z3950.trim().toLowerCase()) return "identical"
  return "different"
}

function MatchIndicator({ status }: { status: MatchStatus }) {
  switch (status) {
    case "identical":
      return <span role="img" aria-label={t('staff.cataloging.z3950.matches', 'Matches')} className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-status-success-100 dark:bg-status-success-900/40"><Check className="w-3 h-3 text-status-success-600 dark:text-status-success-400" /></span>
    case "different":
      return <span role="img" aria-label={t('staff.cataloging.z3950.differs', 'Differs')} className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-status-warning-100 dark:bg-status-warning-900/40"><ArrowRight className="w-3 h-3 text-status-warning-600 dark:text-status-warning-400" /></span>
    case "empty":
      return <span role="img" aria-label={t('staff.cataloging.z3950.empty', 'Not in record')} className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-earth-100 dark:bg-earth-700"><Minus className="w-3 h-3 text-earth-600 dark:text-earth-500" /></span>
  }
}

function extractZ3950Value(record: Z3950SearchResult, key: keyof FormData): string {
  switch (key) {
    case "title": return record.title || ""
    case "author": return record.author || ""
    case "isbn": return record.isbn || ""
    case "publisher": return record.publisher || ""
    case "publication_year": return record.publication_year?.toString() || ""
    case "subjects": return record.subjects?.join(", ") || ""
    case "description": return record.description || ""
    default: return ""
  }
}

interface Z3950PreviewPanelProps {
  record: Z3950SearchResult
  formData: FormData
  onUseField: (key: keyof FormData, value: string) => void
  onUseAll: () => void
  onClose: () => void
}

const COMPARE_FIELDS: { label: string; formKey: keyof FormData }[] = [
  { label: "Title", formKey: "title" },
  { label: "Author", formKey: "author" },
  { label: "ISBN", formKey: "isbn" },
  { label: "Publisher", formKey: "publisher" },
  { label: "Year", formKey: "publication_year" },
  { label: "Subjects", formKey: "subjects" },
  { label: "Description", formKey: "description" },
]

const Z3950PreviewPanel: React.FC<Z3950PreviewPanelProps> = ({
  record,
  formData,
  onUseField,
  onUseAll,
  onClose,
}) => {
  const fields: FieldComparison[] = COMPARE_FIELDS.map(f => ({
    ...f,
    currentValue: String(formData[f.formKey] ?? ""),
    z3950Value: extractZ3950Value(record, f.formKey),
  }))

  const hasDifferences = fields.some(f => getMatchStatus(f.currentValue, f.z3950Value) === "different")

  return (
    <div className="px-6 py-5 bg-earth-50 dark:bg-earth-800/20 border-b border-lsc-border dark:border-earth-700">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-serif text-lg font-semibold text-earth-800 dark:text-lsc-rose-light/80">
          Review Z39.50 Record
        </h3>
        <button onClick={onClose} aria-label="Close preview"
          className="inline-flex items-center justify-center min-w-[44px] min-h-[44px] p-2 text-lsc-dark/70 hover:text-lsc-dark dark:text-lsc-cream/70 dark:hover:text-lsc-cream rounded-xl focus:outline-none focus:ring-2 focus:ring-lsc-rose">
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Column headers */}
      <div className="grid grid-cols-[5rem_1fr_1.5rem_1fr_4rem] gap-x-3 items-center text-xs font-semibold text-lsc-dark/60 dark:text-lsc-cream/60 uppercase tracking-wide mb-2 px-2">
        <span></span>
        <span>Current Form</span>
        <span></span>
        <span>Z39.50 Record</span>
        <span></span>
      </div>

      {/* Field rows */}
      <div className="space-y-1">
        {fields.map(field => {
          const status = getMatchStatus(field.currentValue, field.z3950Value)
          const showUseButton = status === "different"

          return (
            <div key={field.formKey}
              className={`grid grid-cols-[5rem_1fr_1.5rem_1fr_4rem] gap-x-3 items-start px-2 py-1.5 rounded-lg ${
                status === "different" ? "bg-status-warning-50/60 dark:bg-status-warning-900/10" :
                status === "identical" ? "bg-status-success-50/40 dark:bg-status-success-900/10" :
                ""
              }`}
            >
              {/* Field label */}
              <span className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 text-right pt-0.5">
                {field.label}
              </span>

              {/* Current value */}
              <span className={`text-sm break-words min-w-0 ${
                field.currentValue ? "text-lsc-dark dark:text-lsc-cream" : "text-lsc-dark/40 dark:text-lsc-cream/40 italic"
              }`}>
                {field.currentValue || "empty"}
              </span>

              {/* Match indicator */}
              <div className="flex-shrink-0 pt-0.5">
                <MatchIndicator status={status} />
              </div>

              {/* Z39.50 value */}
              <span className={`text-sm break-words min-w-0 ${
                field.z3950Value ? "text-lsc-dark dark:text-lsc-cream font-medium" : "text-lsc-dark/40 dark:text-lsc-cream/40 italic"
              }`}>
                {field.z3950Value || "empty"}
              </span>

              {/* Use button */}
              <div className="flex-shrink-0">
                {showUseButton && (
                  <button
                    type="button"
                    onClick={() => onUseField(field.formKey, field.z3950Value)}
                    className="px-2 py-0.5 text-xs bg-lsc-rose/10 hover:bg-lsc-rose/20 text-lsc-rose dark:text-lsc-rose-light rounded font-medium transition-colors"
                  >
                    Use this
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Action buttons */}
      <div className="flex items-center gap-3 mt-4 pt-3 border-t border-lsc-border/50 dark:border-earth-700/50">
        {hasDifferences && (
          <button
            type="button"
            onClick={onUseAll}
            className="px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg flex items-center gap-2 font-medium text-sm transition-colors"
          >
            <Check className="w-4 h-4" />
            Use All Z39.50 Data
          </button>
        )}
        <button
          type="button"
          onClick={onClose}
          className="px-4 py-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-lsc-brown rounded-lg font-medium transition-colors"
        >
          Keep current values
        </button>
      </div>
    </div>
  )
}

export default Z3950PreviewPanel
