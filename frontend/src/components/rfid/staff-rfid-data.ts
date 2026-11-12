/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Wifi, WifiOff, PlugZap, RefreshCcw } from "lucide-react"
import type { ConnectionState } from "../../hooks/useReconnectingWebSocket"

export const READER_TYPES = ["circulation_desk", "self_checkout", "security_gate", "handheld", "shelf_reader", "book_drop"]

export const READER_TYPE_LABELS: Record<string, string> = {
  circulation_desk: "Circulation Desk",
  self_checkout: "Self-Checkout",
  security_gate: "Security Gate",
  handheld: "Handheld Scanner",
  shelf_reader: "Shelf Reader",
  book_drop: "Book Drop",
}

export const STATUS_COLORS: Record<string, string> = {
  online: "bg-status-success-100 dark:bg-status-success-900/30 text-status-success-700 dark:text-status-success-300",
  offline: "bg-earth-100 dark:bg-earth-700 text-earth-700 dark:text-earth-200",
  error: "bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300",
  maintenance: "bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-300",
}

export const CONNECTION_STATUS_CONFIG: Record<ConnectionState, { color: string; bgColor: string; icon: typeof Wifi; label: string }> = {
  connecting: { color: "text-status-warning-600", bgColor: "bg-status-warning-100 dark:bg-status-warning-900/30", icon: PlugZap, label: "Connecting..." },
  connected: { color: "text-status-success-600", bgColor: "bg-status-success-100 dark:bg-status-success-900/30", icon: Wifi, label: "Connected" },
  disconnected: { color: "text-earth-600 dark:text-earth-300", bgColor: "bg-earth-100 dark:bg-earth-700", icon: WifiOff, label: "Disconnected" },
  reconnecting: { color: "text-status-warning-600", bgColor: "bg-status-warning-100 dark:bg-status-warning-900/30", icon: RefreshCcw, label: "Reconnecting" },
}
