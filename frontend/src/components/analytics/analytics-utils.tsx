/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable react-refresh/only-export-components */
import { ArrowUpRight, ArrowDownRight, Minus } from "lucide-react"
import { getCurrentLocale } from '@/i18n'

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(amount)
}

export function formatNumber(num: number): string {
  return new Intl.NumberFormat("en-US").format(num)
}

export function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString(getCurrentLocale(), {
    month: "short",
    day: "numeric",
  })
}

export function formatShortDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString(getCurrentLocale(), {
    month: "short",
    day: "numeric",
    year: "2-digit",
  })
}

export function ChangeIndicator({ value, inverse = false }: { value: number; inverse?: boolean }) {
  const isPositive = inverse ? value < 0 : value > 0
  const isNegative = inverse ? value > 0 : value < 0

  if (value === 0) {
    return (
      <span className="flex items-center text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
        <Minus className="w-4 h-4 mr-1" aria-hidden="true" />
        No change
      </span>
    )
  }

  return (
    <span
      className={`flex items-center text-sm ${
        isPositive
          ? "text-status-success-600 dark:text-status-success-400"
          : isNegative
          ? "text-status-danger-600 dark:text-status-danger-400"
          : "text-lsc-dark/70 dark:text-lsc-cream/70"
      }`}
    >
      {isPositive ? (
        <ArrowUpRight className="w-4 h-4 mr-1" aria-hidden="true" />
      ) : (
        <ArrowDownRight className="w-4 h-4 mr-1" aria-hidden="true" />
      )}
      {Math.abs(value).toFixed(1)}%
    </span>
  )
}
