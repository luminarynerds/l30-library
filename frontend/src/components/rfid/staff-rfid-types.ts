/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export interface StaffRFIDReader {
  id: number
  name: string
  serial_number: string
  location: string | null
  reader_type: string
  protocol: string
  ip_address: string | null
  port: number | null
  status: string
  last_heartbeat: string | null
  is_active: boolean
}

export interface RFIDTag {
  id: number
  tag_id: string
  item_barcode: string
  security_bit: boolean
  tag_type: string | null
  last_read_at: string | null
  read_count: number
  is_active: boolean
  item_title?: string
  item_author?: string
}

export interface StaffRFIDSession {
  id: number
  session_type: string
  reader_id: number
  tags_scanned: number
  tags_processed: number
  tags_failed: number
  is_active: boolean
  started_at: string
  reader_name?: string
  operator_name?: string
}

export interface SecurityAlert {
  id: number
  reader_id: number
  alert_type: string
  tag_id: string | null
  item_barcode: string | null
  item_title: string | null
  is_resolved: boolean
  created_at: string
  reader_name?: string
  reader_location?: string
}

export interface DashboardStats {
  total_readers: number
  readers_online: number
  readers_offline: number
  readers_error: number
  total_tags: number
  active_tags: number
  total_sessions_today: number
  items_processed_today: number
  security_alerts_today: number
  unresolved_alerts: number
  recent_sessions: StaffRFIDSession[]
  recent_alerts: SecurityAlert[]
}

export interface BatchResult {
  tag_id: string
  item_barcode: string | null
  item_title: string | null
  success: boolean
  message: string
  checkout_id?: number
  due_date?: string
  was_overdue?: boolean
  fine_amount?: number
  next_hold_patron?: string
}

export interface RFIDScanEvent {
  event_type: "scan"
  session_id: number
  tag_id: string
  item_barcode: string | null
  item_title: string | null
  is_registered: boolean
  is_misplaced: boolean
  expected_location: string | null
  found_at_location: string | null
  signal_strength: number | null
  timestamp: string
}

export interface SecurityAlertEvent {
  event_type: "security_alert"
  alert_id: number
  reader_id: number
  reader_name: string | null
  reader_location: string | null
  alert_type: string
  tag_id: string | null
  item_barcode: string | null
  item_title: string | null
  timestamp: string
}

export interface SessionStatusEvent {
  event_type: "session_status"
  session_id: number
  status: string
  tags_scanned: number
  tags_processed: number
  tags_failed: number
  timestamp: string
}

export interface ReaderStatusEvent {
  event_type: "reader_status"
  reader_id: number
  reader_name: string
  status: string
  last_error: string | null
  timestamp: string
}

export interface BatchProgressEvent {
  event_type: "batch_progress"
  session_id: number
  operation: string
  total_items: number
  processed: number
  successful: number
  failed: number
  current_item: Record<string, unknown> | null
  timestamp: string
}

export type RFIDWebSocketEvent = RFIDScanEvent | SecurityAlertEvent | SessionStatusEvent | ReaderStatusEvent | BatchProgressEvent
