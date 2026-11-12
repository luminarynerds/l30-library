/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export const ROOM_TYPES = [
  { value: "study_room", label: "Study Room" },
  { value: "meeting_room", label: "Meeting Room" },
  { value: "computer_lab", label: "Computer Lab" },
  { value: "event_space", label: "Event Space" },
  { value: "quiet_room", label: "Quiet Room" },
  { value: "group_study", label: "Group Study" },
  { value: "recording_studio", label: "Recording Studio" },
  { value: "makerspace", label: "Makerspace" },
]

import {
  Wifi, Projector, Monitor, Phone, Coffee, Accessibility,
} from "lucide-react"

export const AMENITIES = [
  { id: "wifi", label: "WiFi", icon: Wifi },
  { id: "projector", label: "Projector", icon: Projector },
  { id: "whiteboard", label: "Whiteboard", icon: Monitor },
  { id: "monitor", label: "Display Monitor", icon: Monitor },
  { id: "phone", label: "Conference Phone", icon: Phone },
  { id: "coffee", label: "Coffee/Refreshments", icon: Coffee },
  { id: "accessible", label: "Wheelchair Accessible", icon: Accessibility },
]

export const getStatusColor = (status: string) => {
  switch (status) {
    case "pending":
      return "bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400"
    case "confirmed":
      return "bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400"
    case "checked_in":
      return "bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light"
    case "completed":
      return "bg-earth-100 text-earth-800 dark:bg-earth-700 dark:text-earth-300"
    case "cancelled":
      return "bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400"
    case "no_show":
      return "bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400"
    case "rejected":
      return "bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400"
    default:
      return "bg-earth-100 text-earth-800 dark:bg-earth-700 dark:text-earth-300"
  }
}

export const formatStatus = (status: string) => {
  return status.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase())
}

export type RejectionReasonCode =
  | "schedule_conflict"
  | "capacity_exceeded"
  | "incomplete_information"
  | "prior_policy_violation"
  | "fee_unpaid"
  | "out_of_hours"
  | "other"

// Mirrors backend RejectionReason StrEnum (app/models/room.py). "other" stays
// last and is the picker's default so staff always send a valid code even if
// they don't pick one.
export const REJECTION_REASON_CODES: {
  value: RejectionReasonCode
  i18nKey: string
  fallback: string
}[] = [
  { value: "schedule_conflict", i18nKey: "scheduleConflict", fallback: "Scheduling conflict" },
  { value: "capacity_exceeded", i18nKey: "capacityExceeded", fallback: "Capacity exceeded" },
  { value: "incomplete_information", i18nKey: "incompleteInformation", fallback: "Incomplete information" },
  { value: "prior_policy_violation", i18nKey: "priorPolicyViolation", fallback: "Prior policy violation" },
  { value: "fee_unpaid", i18nKey: "feeUnpaid", fallback: "Unpaid fee" },
  { value: "out_of_hours", i18nKey: "outOfHours", fallback: "Outside operating hours" },
  { value: "other", i18nKey: "other", fallback: "Other" },
]

export const formatDateTime = (dateStr: string, locale: string = "en-US") => {
  const date = new Date(dateStr)
  return date.toLocaleString(locale, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  })
}
