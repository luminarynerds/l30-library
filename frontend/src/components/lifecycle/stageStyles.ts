/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import type { ElementType } from "react"
import {
  ListChecks,
  Package,
  BookOpen,
  ArrowRightLeft,
  Wrench,
  Clipboard,
  Trash2,
  MapPin,
  FileText,
} from "lucide-react"
import type { LifecycleStage } from "../../api/lifecycle-api"
import { getCurrentLocale } from '@/i18n'

export const STAGE_ICONS: Record<LifecycleStage, ElementType> = {
  selection: ListChecks,
  acquisition: Package,
  cataloging: BookOpen,
  circulation: ArrowRightLeft,
  condition: Wrench,
  inventory: Clipboard,
  weeding: Trash2,
  location: MapPin,
  other: FileText,
}

export const STAGE_COLORS: Record<LifecycleStage, { bg: string; text: string; border: string }> = {
  selection: { bg: "bg-teal-100 dark:bg-teal-900/30", text: "text-teal-700 dark:text-teal-400", border: "border-teal-200 dark:border-teal-800" },
  acquisition: { bg: "bg-earth-100 dark:bg-earth-800/30", text: "text-lsc-rose dark:text-lsc-rose-light", border: "border-earth-200 dark:border-earth-700" },
  cataloging: { bg: "bg-category-100 dark:bg-category-900/30", text: "text-category-700 dark:text-category-400", border: "border-category-200 dark:border-category-800" },
  circulation: { bg: "bg-status-success-100 dark:bg-status-success-900/30", text: "text-status-success-700 dark:text-status-success-400", border: "border-status-success-200 dark:border-status-success-800" },
  condition: { bg: "bg-status-warning-100 dark:bg-status-warning-900/30", text: "text-status-warning-700 dark:text-status-warning-400", border: "border-status-warning-200 dark:border-status-warning-800" },
  inventory: { bg: "bg-indigo-100 dark:bg-indigo-900/30", text: "text-indigo-700 dark:text-indigo-400", border: "border-indigo-200 dark:border-indigo-800" },
  weeding: { bg: "bg-status-danger-100 dark:bg-status-danger-900/30", text: "text-status-danger-700 dark:text-status-danger-400", border: "border-status-danger-200 dark:border-status-danger-800" },
  location: { bg: "bg-earth-100 dark:bg-earth-900/30", text: "text-earth-700 dark:text-earth-300", border: "border-earth-200 dark:border-earth-800" },
  other: { bg: "bg-earth-100 dark:bg-earth-900/30", text: "text-earth-700 dark:text-earth-300", border: "border-earth-200 dark:border-earth-800" },
}

export function formatLifecycleDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString(getCurrentLocale(), {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  })
}
