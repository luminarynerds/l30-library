/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * RFID Simulator API Service
 *
 * Provides functions for testing RFID functionality without physical hardware.
 * Only available in development/testing environments.
 * All endpoints require ADMIN role.
 */

import { fetchApi, isApiError } from '@/lib/api-client'
import { getAccessToken } from '../../../utils/tokenStore'
import type { components } from '@/api/generated/schema';

// ==================== Types ====================

export type RFIDReaderType =
  | 'circulation_desk'
  | 'self_checkout'
  | 'security_gate'
  | 'handheld'
  | 'shelf_reader'
  | 'book_drop'

export type RFIDReaderStatus = components['schemas']['RFIDReaderStatus'];
export interface SimulatedReader {
  id: number
  name: string
  serial_number: string
  reader_type: RFIDReaderType
  location: string
}

export interface CreateReaderRequest {
  name?: string
  reader_type?: RFIDReaderType
  location?: string
}

export interface CreateReaderResponse {
  message: string
  reader_id: number
  name: string
  serial_number: string
}

export interface SimulateTagReadRequest {
  session_id: number
  tag_id?: string
  signal_strength?: number
  found_at_location?: string
}

export interface TagReadResult {
  tag_id: string
  item_barcode: string | null
  item_title: string | null
  is_registered: boolean
  is_misplaced: boolean
  expected_location: string | null
  found_at_location: string | null
  signal_strength: number
  timestamp: string
}

export interface SimulateBatchReadRequest {
  session_id: number
  count?: number
  include_registered?: boolean
  include_unregistered?: boolean
  delay_ms?: number
}

export interface BatchReadResponse {
  message: string
  scans: TagReadResult[]
}

export interface SimulateSecurityAlertRequest {
  reader_id: number
  tag_id?: string
  use_registered_tag?: boolean
}

export interface SecurityAlertResult {
  alert_id: number
  alert_type: string
  reader_id: number
  tag_id: string | null
  item_barcode: string | null
  item_title: string | null
  timestamp: string
}

export interface SimulateReaderStatusRequest {
  reader_id: number
  status: RFIDReaderStatus
  error_message?: string
}

export interface ReaderStatusResult {
  reader_id: number
  name: string
  previous_status: RFIDReaderStatus
  new_status: RFIDReaderStatus
  error_message: string | null
  timestamp: string
}

export interface AutoScanRequest {
  session_id: number
  interval_ms?: number
  include_registered?: boolean
  include_unregistered?: boolean
}

export interface AutoScanStartResponse {
  message: string
  interval_ms: number
}

export interface AutoScanStatus {
  active_sessions: number[]
  sessions: Record<string, {
    interval_ms: number
    include_registered: boolean
    include_unregistered: boolean
    started_at: string
    scans_performed: number
  }>
}

export interface CreateTestTagsRequest {
  reader_id: number
  count?: number
}

export interface TestTag {
  tag_id: string
  item_barcode: string
}

export interface CreateTestTagsResponse {
  message: string
  tags: TestTag[]
}

// ==================== Reader Functions ====================

export async function createSimulatedReader(
  token: string,
  data: CreateReaderRequest = {}
): Promise<CreateReaderResponse> {
  try {
    return await fetchApi<CreateReaderResponse>('/rfid/simulator/readers', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create simulated reader')
    }
    throw error
  }
}

// ==================== Scan Simulation Functions ====================

export async function simulateTagRead(
  token: string,
  data: SimulateTagReadRequest
): Promise<TagReadResult> {
  try {
    return await fetchApi<TagReadResult>('/rfid/simulator/scan', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to simulate tag read')
    }
    throw error
  }
}

export async function simulateBatchRead(
  token: string,
  data: SimulateBatchReadRequest
): Promise<BatchReadResponse> {
  try {
    return await fetchApi<BatchReadResponse>('/rfid/simulator/batch-scan', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to simulate batch read')
    }
    throw error
  }
}

// ==================== Security Alert Functions ====================

export async function simulateSecurityAlert(
  token: string,
  data: SimulateSecurityAlertRequest
): Promise<SecurityAlertResult> {
  try {
    return await fetchApi<SecurityAlertResult>('/rfid/simulator/security-alert', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to simulate security alert')
    }
    throw error
  }
}

// ==================== Reader Status Functions ====================

export async function simulateReaderStatus(
  token: string,
  data: SimulateReaderStatusRequest
): Promise<ReaderStatusResult> {
  try {
    return await fetchApi<ReaderStatusResult>('/rfid/simulator/reader-status', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to simulate reader status change')
    }
    throw error
  }
}

// ==================== Auto-Scan Functions ====================

export async function startAutoScan(
  token: string,
  data: AutoScanRequest
): Promise<AutoScanStartResponse> {
  try {
    return await fetchApi<AutoScanStartResponse>('/rfid/simulator/auto-scan/start', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to start auto-scan')
    }
    throw error
  }
}

export async function stopAutoScan(
  token: string,
  sessionId: number
): Promise<{ message: string }> {
  try {
    return await fetchApi<{ message: string }>(`/rfid/simulator/auto-scan/stop/${sessionId}`, {
      method: 'POST',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to stop auto-scan')
    }
    throw error
  }
}

export async function stopAllAutoScans(
  token: string
): Promise<{ message: string }> {
  try {
    return await fetchApi<{ message: string }>('/rfid/simulator/auto-scan/stop-all', {
      method: 'POST',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to stop all auto-scans')
    }
    throw error
  }
}

export async function getAutoScanStatus(
  token: string
): Promise<AutoScanStatus> {
  try {
    return await fetchApi<AutoScanStatus>('/rfid/simulator/auto-scan/status', {
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to get auto-scan status')
    }
    throw error
  }
}

// ==================== Test Tag Functions ====================

export async function createTestTags(
  token: string,
  data: CreateTestTagsRequest
): Promise<CreateTestTagsResponse> {
  try {
    return await fetchApi<CreateTestTagsResponse>('/rfid/simulator/test-tags', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create test tags')
    }
    throw error
  }
}

// ==================== Main RFID API Types ====================

export type RFIDProtocol = components['schemas']['RFIDProtocol'];
export type RFIDSessionType =
  | 'checkout'
  | 'checkin'
  | 'inventory'
  | 'shelf_read'
  | 'security_check'

export type SecurityAlertType =
  | 'gate_alarm'
  | 'unauthorized_removal'
  | 'tampered_tag'
  | 'invalid_checkout'

export interface RFIDReaderCreateRequest {
  name: string
  serial_number: string
  location?: string | null
  reader_type: RFIDReaderType
  protocol?: RFIDProtocol
  ip_address?: string | null
  port?: number | null
  connection_string?: string | null
  antenna_count?: number
  power_level?: number | null
  read_interval_ms?: number
  username?: string | null
  password?: string | null
  config_metadata?: Record<string, unknown> | null
}

export interface RFIDReaderResponse {
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

export interface RFIDReaderStatusUpdateRequest {
  status: RFIDReaderStatus
  last_error?: string | null
}

export interface RFIDTagProgramRequest {
  item_barcode: string
  reader_id: number
  tag_type?: string | null
  include_item_data?: boolean
}

export interface RFIDTagProgramResponse {
  success: boolean
  tag_id: string | null
  message: string
  tag: RFIDTagResponse | null
}

export interface RFIDTagResponse {
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
  item_title?: string | null
  item_author?: string | null
}

export interface RFIDSessionCreateRequest {
  session_type: RFIDSessionType
  reader_id: number
  patron_id?: number | null
  inventory_audit_id?: number | null
  target_location?: string | null
}

export interface RFIDSessionResponse {
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
  reader_name?: string | null
  operator_name?: string | null
  patron_name?: string | null
}

export interface RFIDScanCreateRequest {
  tag_id: string
  signal_strength?: number | null
  antenna_id?: number | null
  found_at_location?: string | null
}

export interface RFIDScanResponse {
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
  checkout_id?: number | null
  due_date?: string | null
}

export interface BatchCheckoutResponse {
  session_id: number
  patron_id: number
  total_items: number
  successful: number
  failed: number
  results: BatchCheckoutItemResult[]
}

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
  was_overdue?: boolean
  fine_amount?: number | null
  next_hold_patron?: string | null
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

export interface SecurityAlertCreateRequest {
  reader_id: number
  alert_type: SecurityAlertType
  tag_id?: string | null
  description?: string | null
  signal_strength?: number | null
  photo_url?: string | null
}

export interface SecurityAlertResponse {
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
  reader_name?: string | null
  reader_location?: string | null
  resolved_by_name?: string | null
}

export interface SecurityAlertResolveRequest {
  resolution_notes: string
}

export interface InventoryScanRequest {
  reader_id: number
  inventory_audit_id?: number | null
  target_location?: string | null
  create_audit?: boolean
  audit_name?: string | null
}

export interface ShelfReadRequest {
  reader_id: number
  target_location: string
}

export interface MissingItemsRequest {
  inventory_audit_id?: number | null
  location_filter?: string | null
  days_since_last_seen?: number | null
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

export interface InventoryScanResult {
  registered: boolean
  item_barcode?: string | null
  item_title?: string | null
  is_misplaced?: boolean
  expected_location?: string | null
  found_at_location?: string | null
}

// ==================== Main RFID API Functions ====================

export async function registerReader(
  data: RFIDReaderCreateRequest
): Promise<RFIDReaderResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<RFIDReaderResponse>('/rfid/readers', {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to register reader')
    }
    throw error
  }
}

export async function readerHeartbeat(
  readerId: number,
  data: RFIDReaderStatusUpdateRequest
): Promise<RFIDReaderResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<RFIDReaderResponse>(`/rfid/readers/${readerId}/heartbeat`, {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update reader heartbeat')
    }
    throw error
  }
}

export async function programTag(
  data: RFIDTagProgramRequest
): Promise<RFIDTagProgramResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<RFIDTagProgramResponse>('/rfid/tags/program', {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to program tag')
    }
    throw error
  }
}

export async function setTagSecurity(
  tagId: string,
  securityBit: boolean
): Promise<RFIDTagResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<RFIDTagResponse>(`/rfid/tags/${encodeURIComponent(tagId)}/security?security_bit=${securityBit}`, {
      method: 'POST',
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to set tag security')
    }
    throw error
  }
}

export async function createSession(
  data: RFIDSessionCreateRequest
): Promise<RFIDSessionResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<RFIDSessionResponse>('/rfid/sessions', {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create session')
    }
    throw error
  }
}

export async function endSession(
  sessionId: number
): Promise<RFIDSessionResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<RFIDSessionResponse>(`/rfid/sessions/${sessionId}/end`, {
      method: 'POST',
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to end session')
    }
    throw error
  }
}

export async function scanTag(
  sessionId: number,
  data: RFIDScanCreateRequest
): Promise<RFIDScanResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<RFIDScanResponse>(`/rfid/sessions/${sessionId}/scan`, {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to record scan')
    }
    throw error
  }
}

export async function batchCheckout(
  data: BatchCheckoutRequest
): Promise<BatchCheckoutResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<BatchCheckoutResponse>('/rfid/batch-checkout', {
      method: 'POST',
      ...(token ? { token } : {}),
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
  data: BatchCheckinRequest
): Promise<BatchCheckinResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<BatchCheckinResponse>('/rfid/batch-checkin', {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to process batch checkin')
    }
    throw error
  }
}

export async function createSecurityAlert(
  data: SecurityAlertCreateRequest
): Promise<SecurityAlertResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<SecurityAlertResponse>('/rfid/security/alerts', {
      method: 'POST',
      ...(token ? { token } : {}),
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
  alertId: number,
  data: SecurityAlertResolveRequest
): Promise<SecurityAlertResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<SecurityAlertResponse>(`/rfid/security/alerts/${alertId}/resolve`, {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to resolve security alert')
    }
    throw error
  }
}

export async function startInventorySession(
  data: InventoryScanRequest
): Promise<RFIDSessionResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<RFIDSessionResponse>('/rfid/inventory/start', {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to start inventory session')
    }
    throw error
  }
}

export async function scanInventory(
  sessionId: number,
  data: RFIDScanCreateRequest
): Promise<InventoryScanResult> {
  const token = getAccessToken()
  try {
    return await fetchApi<InventoryScanResult>(`/rfid/inventory/scan/${sessionId}`, {
      method: 'POST',
      ...(token ? { token } : {}),
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
  data: ShelfReadRequest
): Promise<RFIDSessionResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<RFIDSessionResponse>('/rfid/shelf-read/start', {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to start shelf read session')
    }
    throw error
  }
}

export async function reportMissingItems(
  data: MissingItemsRequest
): Promise<MissingItemResponse[]> {
  const token = getAccessToken()
  try {
    return await fetchApi<MissingItemResponse[]>('/rfid/missing-items', {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to report missing items')
    }
    throw error
  }
}

// ==================== Utility Functions ====================

export function getReaderTypeLabel(type: RFIDReaderType): string {
  const labels: Record<RFIDReaderType, string> = {
    circulation_desk: 'Circulation Desk',
    self_checkout: 'Self-Checkout',
    security_gate: 'Security Gate',
    handheld: 'Handheld Scanner',
    shelf_reader: 'Shelf Reader',
    book_drop: 'Book Drop',
  }
  return labels[type] || type
}

export function getStatusColorClass(status: RFIDReaderStatus): string {
  const colors: Record<RFIDReaderStatus, string> = {
    online: 'bg-status-success-100 text-status-success-700',
    offline: 'bg-earth-100 text-earth-700 dark:text-earth-200',
    error: 'bg-status-danger-100 text-status-danger-700',
    maintenance: 'bg-status-warning-100 text-status-warning-700',
  }
  return colors[status] || 'bg-earth-100 text-earth-700 dark:text-earth-200'
}

/**
 * Reader type options for forms
 */
export const READER_TYPE_OPTIONS: { value: RFIDReaderType; label: string }[] = [
  { value: 'circulation_desk', label: 'Circulation Desk' },
  { value: 'self_checkout', label: 'Self-Checkout' },
  { value: 'security_gate', label: 'Security Gate' },
  { value: 'handheld', label: 'Handheld Scanner' },
  { value: 'shelf_reader', label: 'Shelf Reader' },
  { value: 'book_drop', label: 'Book Drop' },
]

/**
 * Reader status options for forms
 */
export const READER_STATUS_OPTIONS: { value: RFIDReaderStatus; label: string }[] = [
  { value: 'online', label: 'Online' },
  { value: 'offline', label: 'Offline' },
  { value: 'error', label: 'Error' },
  { value: 'maintenance', label: 'Maintenance' },
]
