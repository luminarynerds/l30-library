/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * RFID Management API Service
 *
 * Provides functions for RFID reader management, tag operations,
 * batch circulation, security alerts, and inventory scanning.
 * All endpoints require STAFF or ADMIN role.
 */

import { fetchApi, isApiError } from '@/lib/api-client'

// ==================== Enums ====================

export enum RFIDReaderType {
  CIRCULATION_DESK = 'circulation_desk',
  SELF_CHECKOUT = 'self_checkout',
  SECURITY_GATE = 'security_gate',
  HANDHELD = 'handheld',
  BOOK_DROP = 'book_drop',
}

export enum RFIDReaderStatus {
  ONLINE = 'online',
  OFFLINE = 'offline',
  ERROR = 'error',
  MAINTENANCE = 'maintenance',
}

export enum RFIDProtocol {
  SIP2 = 'sip2',
  NCIP = 'ncip',
  REST_API = 'rest_api',
  TCP_SOCKET = 'tcp_socket',
  SERIAL = 'serial',
}

export enum RFIDSessionType {
  BATCH_CHECKOUT = 'batch_checkout',
  BATCH_CHECKIN = 'batch_checkin',
  INVENTORY_SCAN = 'inventory_scan',
  SHELF_READ = 'shelf_read',
  TAG_PROGRAMMING = 'tag_programming',
}

export enum SecurityAlertType {
  UNAUTHORIZED_EXIT = 'unauthorized_exit',
  MISSING_TAG = 'missing_tag',
  INVALID_TAG = 'invalid_tag',
  MULTIPLE_ALERTS = 'multiple_alerts',
}

// ==================== Reader Types ====================

export interface RFIDReader {
  id: number
  name: string
  serial_number: string
  location: string | null
  reader_type: RFIDReaderType
  protocol: RFIDProtocol
  ip_address: string | null
  port: number | null
  connection_string: string | null
  antenna_count: number
  power_level: number | null
  read_interval_ms: number
  status: RFIDReaderStatus
  last_heartbeat: string | null
  last_error: string | null
  is_active: boolean
  created_at: string
  updated_at: string | null
}

export interface RFIDReaderCreate {
  name: string
  serial_number: string
  location?: string
  reader_type: RFIDReaderType
  protocol?: RFIDProtocol
  ip_address?: string
  port?: number
  connection_string?: string
  antenna_count?: number
  power_level?: number
  read_interval_ms?: number
  username?: string
  password?: string
  config_metadata?: Record<string, unknown>
}

export interface RFIDReaderUpdate {
  name?: string
  location?: string
  protocol?: RFIDProtocol
  ip_address?: string
  port?: number
  connection_string?: string
  username?: string
  password?: string
  antenna_count?: number
  power_level?: number
  read_interval_ms?: number
  config_metadata?: Record<string, unknown>
  is_active?: boolean
}

export interface RFIDReaderStatusUpdate {
  status: RFIDReaderStatus
  last_error?: string
}

export interface RFIDReaderListResponse {
  items: RFIDReader[]
  total: number
  page: number
  per_page: number
}

// ==================== Tag Types ====================

export interface RFIDTag {
  id: number
  tag_id: string
  item_barcode: string
  security_bit: boolean
  afi_byte: string | null
  eas_enabled: boolean
  tag_type: string | null
  memory_size: number | null
  manufacturer: string | null
  programmed_at: string | null
  programmed_by_id: number | null
  programmed_by_reader_id: number | null
  last_read_at: string | null
  read_count: number
  tag_data: Record<string, unknown> | null
  is_active: boolean
  deactivated_at: string | null
  deactivation_reason: string | null
  created_at: string
  updated_at: string | null
  item_title: string | null
  item_author: string | null
}

export interface RFIDTagUpdate {
  security_bit?: boolean
  afi_byte?: string
  eas_enabled?: boolean
  tag_data?: Record<string, unknown>
  is_active?: boolean
  deactivation_reason?: string
}

export interface RFIDTagProgramRequest {
  item_barcode: string
  reader_id: number
  tag_type?: string
  include_item_data?: boolean
}

export interface RFIDTagProgramResponse {
  success: boolean
  tag_id: string | null
  message: string
  tag: RFIDTag | null
}

export interface RFIDTagListResponse {
  items: RFIDTag[]
  total: number
  page: number
  per_page: number
}

// ==================== Session Types ====================

export interface RFIDSessionCreate {
  session_type: RFIDSessionType
  reader_id: number
  patron_id?: number
  inventory_audit_id?: number
  target_location?: string
}

export interface RFIDSession {
  id: number
  session_type: RFIDSessionType
  reader_id: number
  operator_id: number
  patron_id: number | null
  inventory_audit_id: number | null
  target_location: string | null
  started_at: string
  ended_at: string | null
  is_active: boolean
  tags_scanned: number
  tags_processed: number
  tags_failed: number
  session_metadata: Record<string, unknown> | null
  reader_name: string | null
  operator_name: string | null
  patron_name: string | null
}

// ==================== Scan Types ====================

export interface RFIDScanCreate {
  tag_id: string
  signal_strength?: number
  antenna_id?: number
  found_at_location?: string
}

export interface RFIDScan {
  id: number
  session_id: number
  tag_id: string
  rfid_tag_id: number | null
  item_barcode: string | null
  item_title: string | null
  processed: boolean
  process_result: string | null
  error_message: string | null
  signal_strength: number | null
  antenna_id: number | null
  found_at_location: string | null
  expected_location: string | null
  is_misplaced: boolean
  scanned_at: string
  processed_at: string | null
}

// ==================== Batch Checkout Types ====================

export interface BatchCheckoutRequest {
  reader_id: number
  patron_id: number
  tag_ids: string[]
}

export interface BatchCheckoutItemResult {
  tag_id: string
  item_barcode: string | null
  item_title: string | null
  success: boolean
  message: string
  checkout_id: number | null
  due_date: string | null
}

export interface BatchCheckoutResponse {
  session_id: number
  patron_id: number
  total_items: number
  successful: number
  failed: number
  results: BatchCheckoutItemResult[]
}

// ==================== Batch Checkin Types ====================

export interface BatchCheckinRequest {
  reader_id: number
  tag_ids: string[]
}

export interface BatchCheckinItemResult {
  tag_id: string
  item_barcode: string | null
  item_title: string | null
  success: boolean
  message: string
  was_overdue: boolean
  fine_amount: number | null
  next_hold_patron: string | null
}

export interface BatchCheckinResponse {
  session_id: number
  total_items: number
  successful: number
  failed: number
  items_with_holds: number
  items_with_fines: number
  results: BatchCheckinItemResult[]
}

// ==================== Security Alert Types ====================

export interface SecurityAlertCreate {
  reader_id: number
  alert_type: SecurityAlertType
  tag_id?: string
  description?: string
  signal_strength?: number
  photo_url?: string
}

export interface SecurityAlert {
  id: number
  reader_id: number
  alert_type: SecurityAlertType
  tag_id: string | null
  item_barcode: string | null
  item_title: string | null
  description: string | null
  signal_strength: number | null
  photo_url: string | null
  is_resolved: boolean
  resolved_at: string | null
  resolved_by_id: number | null
  resolution_notes: string | null
  created_at: string
  reader_name: string | null
  reader_location: string | null
  resolved_by_name: string | null
}

export interface SecurityAlertResolve {
  resolution_notes: string
}

export interface SecurityAlertListResponse {
  items: SecurityAlert[]
  total: number
  page: number
  per_page: number
}

// ==================== Inventory Types ====================

export interface InventoryScanRequest {
  reader_id: number
  inventory_audit_id?: number
  target_location?: string
  create_audit?: boolean
  audit_name?: string
}

export interface ShelfReadRequest {
  reader_id: number
  target_location: string
}

export interface ShelfReadResult {
  session_id: number
  location: string
  items_scanned: number
  items_in_correct_location: number
  items_misplaced: number
  items_not_in_catalog: number
  misplaced_items: Record<string, unknown>[]
  unknown_tags: string[]
}

export interface MissingItemsRequest {
  inventory_audit_id?: number
  location_filter?: string
  days_since_last_seen?: number
}

export interface MissingItemResponse {
  item_copy_id: number
  barcode: string
  title: string
  author: string | null
  expected_location: string | null
  last_seen_at: string | null
  last_seen_location: string | null
  days_missing: number | null
  tag_id: string | null
  checkout_status: string | null
}

// ==================== Dashboard Types ====================

export interface RFIDDashboardStats {
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
  recent_sessions: RFIDSession[]
  recent_alerts: SecurityAlert[]
}

// ==================== Reader Management Functions ====================

export async function createReader(
  token: string,
  data: RFIDReaderCreate
): Promise<RFIDReader> {
  try {
    return await fetchApi<RFIDReader>('/rfid/readers', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create reader')
    }
    throw error
  }
}

export async function updateReader(
  token: string,
  readerId: number,
  data: RFIDReaderUpdate
): Promise<RFIDReader> {
  try {
    return await fetchApi<RFIDReader>(`/rfid/readers/${readerId}`, {
      method: 'PATCH',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update reader')
    }
    throw error
  }
}

export async function readerHeartbeat(
  token: string,
  readerId: number,
  data: RFIDReaderStatusUpdate
): Promise<RFIDReader> {
  try {
    return await fetchApi<RFIDReader>(`/rfid/readers/${readerId}/heartbeat`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to send heartbeat')
    }
    throw error
  }
}

export async function deleteReader(
  token: string,
  readerId: number
): Promise<void> {
  try {
    await fetchApi<void>(`/rfid/readers/${readerId}`, {
      method: 'DELETE',
      token,
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete reader')
    }
    throw error
  }
}

// ==================== Tag Management Functions ====================

export async function programTag(
  token: string,
  data: RFIDTagProgramRequest
): Promise<RFIDTagProgramResponse> {
  try {
    return await fetchApi<RFIDTagProgramResponse>('/rfid/tags/program', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to program tag')
    }
    throw error
  }
}

export async function updateTag(
  token: string,
  tagId: string,
  data: RFIDTagUpdate
): Promise<RFIDTag> {
  try {
    return await fetchApi<RFIDTag>(`/rfid/tags/${encodeURIComponent(tagId)}`, {
      method: 'PATCH',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update tag')
    }
    throw error
  }
}

export async function setTagSecurity(
  token: string,
  tagId: string,
  securityBit: boolean
): Promise<RFIDTag> {
  try {
    return await fetchApi<RFIDTag>(
      `/rfid/tags/${encodeURIComponent(tagId)}/security?security_bit=${securityBit}`,
      {
        method: 'POST',
        token,
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to set tag security')
    }
    throw error
  }
}

// ==================== Session Management Functions ====================

export async function startSession(
  token: string,
  data: RFIDSessionCreate
): Promise<RFIDSession> {
  try {
    return await fetchApi<RFIDSession>('/rfid/sessions', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to start session')
    }
    throw error
  }
}

export async function endSession(
  token: string,
  sessionId: number
): Promise<RFIDSession> {
  try {
    return await fetchApi<RFIDSession>(`/rfid/sessions/${sessionId}/end`, {
      method: 'POST',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to end session')
    }
    throw error
  }
}

export async function recordScan(
  token: string,
  sessionId: number,
  data: RFIDScanCreate
): Promise<RFIDScan> {
  try {
    return await fetchApi<RFIDScan>(`/rfid/sessions/${sessionId}/scan`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to record scan')
    }
    throw error
  }
}

// ==================== Batch Circulation Functions ====================

export async function batchCheckout(
  token: string,
  data: BatchCheckoutRequest
): Promise<BatchCheckoutResponse> {
  try {
    return await fetchApi<BatchCheckoutResponse>('/rfid/batch-checkout', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to process batch checkout')
    }
    throw error
  }
}

export async function batchCheckin(
  token: string,
  data: BatchCheckinRequest
): Promise<BatchCheckinResponse> {
  try {
    return await fetchApi<BatchCheckinResponse>('/rfid/batch-checkin', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to process batch checkin')
    }
    throw error
  }
}

// ==================== Security Alert Functions ====================

export async function createSecurityAlert(
  token: string,
  data: SecurityAlertCreate
): Promise<SecurityAlert> {
  try {
    return await fetchApi<SecurityAlert>('/rfid/security/alerts', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create security alert')
    }
    throw error
  }
}

export async function resolveSecurityAlert(
  token: string,
  alertId: number,
  data: SecurityAlertResolve
): Promise<SecurityAlert> {
  try {
    return await fetchApi<SecurityAlert>(`/rfid/security/alerts/${alertId}/resolve`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to resolve security alert')
    }
    throw error
  }
}

// ==================== Inventory Functions ====================

export async function startInventorySession(
  token: string,
  data: InventoryScanRequest
): Promise<RFIDSession> {
  try {
    return await fetchApi<RFIDSession>('/rfid/inventory/start', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to start inventory session')
    }
    throw error
  }
}

export async function processInventoryScan(
  token: string,
  sessionId: number,
  data: RFIDScanCreate
): Promise<Record<string, unknown>> {
  try {
    return await fetchApi<Record<string, unknown>>(`/rfid/inventory/scan/${sessionId}`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to process inventory scan')
    }
    throw error
  }
}

export async function startShelfRead(
  token: string,
  data: ShelfReadRequest
): Promise<RFIDSession> {
  try {
    return await fetchApi<RFIDSession>('/rfid/shelf-read/start', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to start shelf read')
    }
    throw error
  }
}

export async function reportMissingItems(
  token: string,
  data: MissingItemsRequest
): Promise<MissingItemResponse[]> {
  try {
    return await fetchApi<MissingItemResponse[]>('/rfid/missing-items', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to report missing items')
    }
    throw error
  }
}

// ==================== WebSocket Session Functions ====================

export async function closeWebSocketSession(
  token: string,
  sessionId: string
): Promise<void> {
  try {
    await fetchApi<void>(`/rfid/ws/session/${encodeURIComponent(sessionId)}`, {
      method: 'DELETE',
      token,
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to close WebSocket session')
    }
    throw error
  }
}

// ==================== Utility Functions ====================

export function getReaderTypeLabel(readerType: RFIDReaderType): string {
  const labels: Record<RFIDReaderType, string> = {
    [RFIDReaderType.CIRCULATION_DESK]: 'Circulation Desk',
    [RFIDReaderType.SELF_CHECKOUT]: 'Self-Checkout Kiosk',
    [RFIDReaderType.SECURITY_GATE]: 'Security Gate',
    [RFIDReaderType.HANDHELD]: 'Handheld Scanner',
    [RFIDReaderType.BOOK_DROP]: 'Book Drop',
  }
  return labels[readerType] || readerType
}

export function getReaderStatusLabel(status: RFIDReaderStatus): string {
  const labels: Record<RFIDReaderStatus, string> = {
    [RFIDReaderStatus.ONLINE]: 'Online',
    [RFIDReaderStatus.OFFLINE]: 'Offline',
    [RFIDReaderStatus.ERROR]: 'Error',
    [RFIDReaderStatus.MAINTENANCE]: 'Maintenance',
  }
  return labels[status] || status
}

export function getReaderStatusColor(status: RFIDReaderStatus): string {
  const colors: Record<RFIDReaderStatus, string> = {
    [RFIDReaderStatus.ONLINE]: 'green',
    [RFIDReaderStatus.OFFLINE]: 'gray',
    [RFIDReaderStatus.ERROR]: 'red',
    [RFIDReaderStatus.MAINTENANCE]: 'yellow',
  }
  return colors[status] || 'gray'
}

export function getSessionTypeLabel(sessionType: RFIDSessionType): string {
  const labels: Record<RFIDSessionType, string> = {
    [RFIDSessionType.BATCH_CHECKOUT]: 'Batch Checkout',
    [RFIDSessionType.BATCH_CHECKIN]: 'Batch Checkin',
    [RFIDSessionType.INVENTORY_SCAN]: 'Inventory Scan',
    [RFIDSessionType.SHELF_READ]: 'Shelf Read',
    [RFIDSessionType.TAG_PROGRAMMING]: 'Tag Programming',
  }
  return labels[sessionType] || sessionType
}

export function getSecurityAlertTypeLabel(alertType: SecurityAlertType): string {
  const labels: Record<SecurityAlertType, string> = {
    [SecurityAlertType.UNAUTHORIZED_EXIT]: 'Unauthorized Exit',
    [SecurityAlertType.MISSING_TAG]: 'Missing Tag',
    [SecurityAlertType.INVALID_TAG]: 'Invalid Tag',
    [SecurityAlertType.MULTIPLE_ALERTS]: 'Multiple Alerts',
  }
  return labels[alertType] || alertType
}

export function getSecurityAlertColor(alertType: SecurityAlertType): string {
  const colors: Record<SecurityAlertType, string> = {
    [SecurityAlertType.UNAUTHORIZED_EXIT]: 'red',
    [SecurityAlertType.MISSING_TAG]: 'orange',
    [SecurityAlertType.INVALID_TAG]: 'yellow',
    [SecurityAlertType.MULTIPLE_ALERTS]: 'red',
  }
  return colors[alertType] || 'gray'
}

export function getProtocolLabel(protocol: RFIDProtocol): string {
  const labels: Record<RFIDProtocol, string> = {
    [RFIDProtocol.SIP2]: 'SIP2',
    [RFIDProtocol.NCIP]: 'NCIP',
    [RFIDProtocol.REST_API]: 'REST API',
    [RFIDProtocol.TCP_SOCKET]: 'TCP Socket',
    [RFIDProtocol.SERIAL]: 'Serial',
  }
  return labels[protocol] || protocol
}
