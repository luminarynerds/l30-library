/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { AlertTriangle, CheckCircle, XCircle, AlertOctagon } from "lucide-react"

export const STATUS_CONFIG: Record<string, { bg: string; text: string; icon: React.ReactNode }> = {
  PENDING: {
    bg: "bg-status-warning-100 dark:bg-status-warning-900/30",
    text: "text-status-warning-700 dark:text-status-warning-400",
    icon: <AlertTriangle className="w-4 h-4" />,
  },
  RESOLVED: {
    bg: "bg-status-success-100 dark:bg-status-success-900/30",
    text: "text-status-success-700 dark:text-status-success-400",
    icon: <CheckCircle className="w-4 h-4" />,
  },
  FALSE_POSITIVE: {
    bg: "bg-earth-100 dark:bg-earth-800/30",
    text: "text-lsc-rose dark:text-lsc-rose-light",
    icon: <XCircle className="w-4 h-4" />,
  },
  FALSE_NEGATIVE: {
    bg: "bg-status-danger-100 dark:bg-status-danger-900/30",
    text: "text-status-danger-700 dark:text-status-danger-400",
    icon: <AlertOctagon className="w-4 h-4" />,
  },
}

export const FLAG_TYPE_CONFIG: Record<string, { label: string; color: string }> = {
  spam: { label: "Spam", color: "bg-status-warning-500" },
  SPAM: { label: "Spam", color: "bg-status-warning-500" },
  inappropriate: { label: "Inappropriate", color: "bg-status-danger-500" },
  offensive: { label: "Offensive", color: "bg-category-500" },
  misleading: { label: "Misleading", color: "bg-status-warning-500" },
  harassment: { label: "Harassment", color: "bg-pink-500" },
  HATE_SPEECH: { label: "Hate Speech", color: "bg-status-danger-600" },
  EXCESSIVE_CAPS: { label: "Excessive Caps", color: "bg-status-warning-500" },
  SUSPICIOUS_PATTERN: { label: "Suspicious Pattern", color: "bg-status-warning-600" },
  OFF_TOPIC: { label: "Off Topic", color: "bg-earth-500" },
  DUPLICATE: { label: "Duplicate", color: "bg-earth-500" },
  other: { label: "Other", color: "bg-earth-500" },
}

export const DEFAULT_STATUS_CONFIG = {
  bg: "bg-status-warning-100 dark:bg-status-warning-900/30",
  text: "text-status-warning-700 dark:text-status-warning-400",
  icon: <AlertTriangle className="w-4 h-4" />,
}

export const DEFAULT_FLAG_TYPE_CONFIG = { label: "Other", color: "bg-earth-500" }

export const getStatusConfig = (status: string): { bg: string; text: string; icon: React.ReactNode } => {
  return STATUS_CONFIG[status] ?? DEFAULT_STATUS_CONFIG
}

export const getFlagTypeConfig = (flagType: string): { label: string; color: string } => {
  return FLAG_TYPE_CONFIG[flagType] ?? DEFAULT_FLAG_TYPE_CONFIG
}
