/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export const STATUS_OPTIONS = [
  { value: "", label: "All Statuses" },
  { value: "pending", label: "Pending" },
  { value: "RESOLVED", label: "Resolved" },
  { value: "FALSE_POSITIVE", label: "False Positive" },
  { value: "FALSE_NEGATIVE", label: "False Negative" },
]

export const REVIEW_TYPE_OPTIONS = [
  { value: "", label: "All Types" },
  { value: "event_review", label: "Event Reviews" },
  { value: "indie_review", label: "Indie Reviews" },
  { value: "book_review", label: "Book Reviews" },
  { value: "comment", label: "Comments" },
]

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

export const DEFAULT_FLAG_TYPE_CONFIG = { label: "Other", color: "bg-earth-500" }

export const getFlagTypeConfig = (flagType: string): { label: string; color: string } => {
  return FLAG_TYPE_CONFIG[flagType] ?? DEFAULT_FLAG_TYPE_CONFIG
}
