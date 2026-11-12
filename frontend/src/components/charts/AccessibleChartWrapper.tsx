/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable react-refresh/only-export-components */
/**
 * Accessible Chart Wrapper Component
 *
 * Provides accessibility features for chart components:
 * - ARIA labels and roles for screen readers
 * - Accessible data tables as alternatives
 * - Summary descriptions for screen readers
 * - Proper handling of empty/zero data states
 */

import React from "react"
import { getCurrentLocale } from '@/i18n'

export interface ChartColumn {
  key: string
  label: string
  format?: (value: unknown) => string
}

export interface AccessibleChartWrapperProps {
  /** Title of the chart for accessibility */
  title: string
  /** Description of what the chart shows */
  description?: string
  /** Summary text for screen readers (auto-generated if not provided) */
  summary?: string
  /** Data to display in the accessible table */
  data: Record<string, unknown>[]
  /** Column definitions for the data table */
  columns: ChartColumn[]
  /** The visual chart component */
  children: React.ReactNode
  /** Height for empty state container */
  emptyHeight?: number
  /** Custom empty state message */
  emptyMessage?: string
  /** Additional CSS classes */
  className?: string
}

function formatValue(value: unknown, format?: (v: unknown) => string): string {
  if (format) {
    return format(value)
  }
  if (value === null || value === undefined) {
    return "N/A"
  }
  if (typeof value === "number") {
    return value.toLocaleString()
  }
  return String(value)
}

function AccessibleDataTable({
  title,
  data,
  columns,
}: {
  title: string
  data: Record<string, unknown>[]
  columns: ChartColumn[]
}) {
  if (data.length === 0) return null

  return (
    <table className="sr-only" aria-label={`${title} data table`}>
      <caption>{title} - detailed data</caption>
      <thead>
        <tr>
          {columns.map((col) => (
            <th key={col.key} scope="col">
              {col.label}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {data.map((row, rowIndex) => (
          <tr key={rowIndex}>
            {columns.map((col) => (
              <td key={col.key}>{formatValue(row[col.key], col.format)}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export function AccessibleChartWrapper({
  title,
  description,
  summary,
  data,
  columns,
  children,
  emptyHeight = 300,
  emptyMessage = "No data available",
  className = "",
}: AccessibleChartWrapperProps): React.ReactElement {
  // Generate a basic summary if not provided
  const getSummary = () => {
    if (summary) return summary
    if (data.length === 0) return `${title}: ${emptyMessage}`
    return `${title} showing ${data.length} data points. ${description || ""}`
  }

  // Handle empty data state
  if (data.length === 0) {
    return (
      <div
        className={`flex items-center justify-center text-lsc-dark/70 dark:text-lsc-cream/70 ${className}`}
        style={{ height: emptyHeight }}
        role="img"
        aria-label={`${title}: ${emptyMessage}`}
      >
        <p className="text-center">
          <span className="block text-lg font-medium">{emptyMessage}</span>
          {description && (
            <span className="block text-sm mt-1">{description}</span>
          )}
        </p>
      </div>
    )
  }

  return (
    <figure
      role="figure"
      aria-label={title}
      className={`relative ${className}`}
    >
      {/* Screen reader accessible summary */}
      <figcaption className="sr-only">
        {getSummary()}
      </figcaption>

      {/* Accessible data table for screen readers */}
      <AccessibleDataTable title={title} data={data} columns={columns} />

      {/* Visual chart - hidden from screen readers */}
      <div aria-hidden="true">
        {children}
      </div>
    </figure>
  )
}

export function generateChartSummary({
  title,
  dataLength,
  metrics,
}: {
  title: string
  dataLength: number
  metrics?: Array<{ label: string; value: string | number }>
}): string {
  if (dataLength === 0) return `${title}: No data available.`

  let summary = `${title} showing ${dataLength} data points.`

  if (metrics && metrics.length > 0) {
    const metricStrings = metrics.map((m) => `${m.label}: ${m.value}`)
    summary += ` ${metricStrings.join(". ")}.`
  }

  return summary
}

export function formatCurrency(value: unknown): string {
  if (typeof value !== "number") return "N/A"
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(value)
}

export function formatPercent(value: unknown): string {
  if (typeof value !== "number") return "N/A"
  return `${value.toFixed(1)}%`
}

export function formatDateValue(value: unknown): string {
  if (!value) return "N/A"
  const date = new Date(String(value))
  if (isNaN(date.getTime())) return String(value)
  return date.toLocaleDateString(getCurrentLocale(), {
    month: "short",
    day: "numeric",
    year: "numeric",
  })
}

export default AccessibleChartWrapper
